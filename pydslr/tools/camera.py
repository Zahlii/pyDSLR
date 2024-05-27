"""
Main Camera class
"""

# pylint: disable=no-member
import datetime
import io
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Generic, Optional, Set, Tuple, TypeVar, get_args

import gphoto2 as gp  # type: ignore
import numpy as np
import psutil
from PIL import Image

from pydslr.config.base import BaseConfig
from pydslr.config.r6m2 import CaptureSettings, ImageSettings, R6M2Config, Settings
from pydslr.tools.exif import get_exif
from pydslr.utils import GPWidgetItem, PyDSLRException, timed

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG)

T = TypeVar("T", bound=BaseConfig)


class Camera(Generic[T]):
    """
    Generic wrapper around gphoto2 to allow python access to your camera config and capture modes
    """

    def __init__(self):
        self._maybe_kill_ptp()
        # pylint: disable=not-callable
        self.camera = gp.Camera()
        self._config = None

    def __enter__(self):
        self.camera.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        gp.gp_camera_exit(self.camera)

    @staticmethod
    def _maybe_kill_ptp():
        """
        Make sure device not claimed by ptpcamerad on macOS, otherwise we get errors running as non-root
        :return:
        """
        for proc in psutil.process_iter():
            name = proc.name()
            if "ptpcamerad" in name:
                logging.info("Found ptpcamerad as PID %s, killing...", proc.pid)
                proc.kill()

    @timed
    def preview_as_bytes(self) -> bytes:
        """
        Load the current preview/LiveView image as byte array in JPEG format. If settings were recently updated,
        this may not yet fully reflect it, as the camera usually keeps the preview buffered.
        :return:
        """
        _, file = gp.gp_camera_capture_preview(self.camera)
        data = bytearray(gp.gp_file_get_data_and_size(file)[1])
        return data

    def preview_as_numpy(self) -> np.ndarray:
        """
        Load the current preview/LiveView image as numpy array via Image.open()
        :return:
        """
        with io.BytesIO() as buffer:
            buffer.write(self.preview_as_bytes())
            buffer.seek(0)
            return np.asarray(Image.open(buffer))

    @timed
    def preview_to_file(self, path: Optional[Path] = None):
        """
        Load the current preview/LiveView image as a file.
        :param path:
        :return:
        """
        if path is not None:
            assert ".jpg" in path.suffixes or ".jpeg" in path.suffixes, "Capture Preview should be stores as JPG."
        else:
            path = Path("preview.jpg")
        data = self.preview_as_bytes()
        with path.open("wb") as fp:
            fp.write(data)

    def stream_preview(
        self,
        max_fps: Optional[int] = None,
        max_time: Optional[datetime.timedelta] = None,
        max_images: Optional[int] = None,
        as_numpy=False,
    ) -> Generator[bytes | np.ndarray, None, None]:
        """
        Yield images as part of a media stream
        :param max_images: Max number of images to return.
        :param as_numpy: Return data as a numpy array
        :param max_fps: Maximum FPS
        :param max_time: Maximum time to stream images
        :return:
        """
        last = None
        first = datetime.datetime.utcnow()
        delay = None if max_fps is None else datetime.timedelta(milliseconds=1000 / max_fps)
        count = 0
        while True:
            if last is not None and delay is not None:
                remaining_delay = last + delay - datetime.datetime.utcnow()
                if remaining_delay.total_seconds() > 0:
                    time.sleep(remaining_delay.total_seconds())
            last = datetime.datetime.utcnow()
            if max_time is not None and (last - first) > max_time:
                return

            if max_images is not None and count >= max_images:
                return

            count += 1
            if not as_numpy:
                yield b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + self.preview_as_bytes() + b"\r\n"
            else:
                yield self.preview_as_numpy()

    @timed
    def capture(self, path: Optional[Path] = None, keep_on_camera: bool = False):
        """
        Capture a full image to disk.
        :param keep_on_camera:
        :param path:
        :return:
        """
        if path is not None:
            if self.get_config().is_raw():
                assert ".cr3" in path.suffixes, "RAW format enabled, file format should be cr3"
            else:
                assert ".jpg" in path.suffixes or ".jpeg" in path.suffixes, "RAW format disabled, image should be stores as JPG."
        else:
            if self.get_config().is_raw():
                path = Path("image.cr3")
            else:
                path = Path("image.jpg")

        _, file = gp.gp_camera_capture(self.camera, gp.GP_CAPTURE_IMAGE)
        _, c_file = gp.gp_camera_file_get(self.camera, file.folder, file.name, gp.GP_FILE_TYPE_NORMAL)
        c_file.save(str(path))

        if not keep_on_camera or self.get_config().is_sdcard_capture_enabled():
            gp.gp_camera_file_delete(self.camera, file.folder, file.name)

        if os.stat(path).st_size == 0:
            path.unlink()
            raise PyDSLRException("Got zero-byte image during capture(). Make sure auto focus is possible.")

        exif_data = get_exif(path)
        logging.info("Got picture with EXIF: %s", exif_data)
        return exif_data

    def get_config(self) -> "T":
        """
        Get the current configuration of the camera.
        :return:
        """

        response = self.get_json_config()

        def _get_kwargs(node):
            if "children" not in node:
                return node["value"]
            return {n["name"]: _get_kwargs(n) for n in node["children"]}

        return get_args(self.__orig_class__)[0](**_get_kwargs(response))  # type: ignore

    @contextmanager
    def config_context(self, new_config: T):
        """
        Context manager around settings to only shortly update settings.
        :param new_config:
        :return:
        """
        old_config = self.get_config()
        changed_fields = self.set_config(new_config)
        yield
        self.set_config(old_config, only_fields=changed_fields)

    @timed
    def set_config(self, new_config: T, only_fields: Optional[Set[Tuple[str, str]]] = None) -> Set[Tuple[str, str]]:
        """
        Set the config, optionally limited to a set of named fields.
        Returns those fields that actually were modified.

        :param new_config:
        :param only_fields:
        :return:
        """
        updated_settings = set()
        old_config = self.get_config()
        gp_config = self._gp_get_camera_config_cached()

        for field in new_config.model_fields_set:
            if getattr(new_config, field, None) is not None:
                for field2 in getattr(new_config, field).model_fields_set:
                    if only_fields is not None and (field, field2) not in only_fields:
                        continue
                    new_value = getattr(getattr(new_config, field), field2)
                    old_value = getattr(getattr(old_config, field), field2)
                    if new_value != old_value and new_value is not None:
                        logging.info(
                            "Updating %s from %s -> %s",
                            (field, field2),
                            old_value,
                            new_value,
                        )
                        updated_settings.add((field, field2))
                        _, gp_field = gp.gp_widget_get_child_by_name(gp_config, field2)
                        gp.gp_widget_set_value(gp_field, new_value)

        if updated_settings:
            # this may throw I/O errors, but works
            gp.gp_camera_set_config(self.camera, gp_config)
            self._config = gp_config

        return updated_settings

    @timed
    def _gp_get_camera_config_cached(self):
        if self._config is None:
            self._config = self.camera.get_config()
        return self._config

    def get_json_config(self):
        """
        Get the current config including all options and accessible fields
        :return:
        """
        config_tree = self._gp_get_camera_config_cached()

        def _traverse(node, depth=0):
            c_type = node.get_type()
            c_name = node.get_name()
            c_label = node.get_label()

            if c_type in (
                GPWidgetItem.GP_WIDGET_SECTION,
                GPWidgetItem.GP_WIDGET_WINDOW,
            ):
                config = {
                    "type": GPWidgetItem(c_type).name,
                    "label": c_label,
                    "name": c_name,
                    "children": [_traverse(node.get_child(i), depth + 1) for i in range(node.count_children())],
                    "value_type": None,
                }
            else:
                value = node.get_value()
                config = {
                    "label": c_label,
                    "name": c_name,
                    "value": value,
                    "options": [],
                    "type": GPWidgetItem(c_type).name,
                    "value_type": GPWidgetItem(c_type).get_value_type(),
                }
                if c_type in (
                    GPWidgetItem.GP_WIDGET_MENU,
                    GPWidgetItem.GP_WIDGET_RADIO,
                ):
                    for k in range(node.count_choices()):
                        config["options"].append(node.get_choice(k))

                    if value not in config["options"]:
                        config["options"].append(value)
            return config

        return _traverse(config_tree)


if __name__ == "__main__":
    with Camera[R6M2Config]() as c:
        c.set_config(
            R6M2Config(
                imgsettings=ImageSettings(iso="400"),
                settings=Settings(capturetarget="Internal RAM"),
                capturesettings=CaptureSettings(aperture="5.6", shutterspeed="2"),
            )
        )
        for j in zip(range(20), c.stream_preview()):

            print(c.capture(keep_on_camera=True))
