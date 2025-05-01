"""
Main Camera class
"""

# pylint: disable=no-member
import datetime
import io
import logging
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Generic, List, Optional, Set, TypeVar, get_args

import gphoto2 as gp  # type: ignore
import numpy as np
import psutil
from PIL import Image, UnidentifiedImageError
from retry import retry
from tqdm import trange

from pydslr.config.base import BaseConfig
from pydslr.config.r6m2 import CaptureSettings, ImageSettings, R6M2Config, Settings
from pydslr.tools.exif import get_exif
from pydslr.utils import GPWidgetItem, PyDSLRException, timed

T = TypeVar("T", bound=BaseConfig)


class GImage:
    name: str
    folder: str


ImageBunch = List[Path]


class CaptureDevice(ABC, Generic[T]):
    @abstractmethod
    def preview_as_numpy(self) -> np.ndarray | None:
        """
        Load the current preview/LiveView image as numpy array via Image.open()
        :return:
        """

    @abstractmethod
    def preview_as_bytes(self) -> bytes | None:
        """
        Load the current preview/LiveView image as byte array in JPEG format. If settings were recently updated,
        this may not yet fully reflect it, as the camera usually keeps the preview buffered.
        :return:
        """

    @abstractmethod
    def get_config(self, ignore_cache: bool = False) -> Optional["T"]:
        """
        Get the current configuration of the device.
        :return:
        """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def stream_preview(
        self,
        max_fps: Optional[int] = None,
        max_time: Optional[datetime.timedelta] = None,
        max_images: Optional[int] = None,
        as_numpy=False,
    ) -> Generator[bytes | np.ndarray | None, None, None]:
        """
        Yield images as part of a media stream
        :param max_images: Max number of images to return.
        :param as_numpy: Return data as a numpy array
        :param max_fps: Maximum FPS
        :param max_time: Maximum time to stream images
        :return:
        """
        last = None
        first = datetime.datetime.now()
        delay = None if max_fps is None else datetime.timedelta(milliseconds=1000 / max_fps)
        count = 0
        while True:
            if last is not None and delay is not None:
                remaining_delay = last + delay - datetime.datetime.now()
                if remaining_delay.total_seconds() > 0:
                    time.sleep(remaining_delay.total_seconds())
            last = datetime.datetime.now()
            if max_time is not None and (last - first) > max_time:
                return

            if max_images is not None and count >= max_images:
                return

            count += 1
            if not as_numpy:
                preview = self.preview_as_bytes()
                if preview is None:
                    break
                yield b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + preview + b"\r\n"
            else:
                yield self.preview_as_numpy()

    @abstractmethod
    def capture(self, folder: Optional[Path] = None, keep_on_camera: bool = False) -> ImageBunch:
        """
        Capture a full image to disk.
        :param folder: If set, image will be put into this folder with the camera image name.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :return: The final path.
        """


class Camera(CaptureDevice[T]):
    """
    Generic wrapper around gphoto2 to allow python access to your camera config and capture modes
    """

    def __init__(self):
        self._maybe_kill_ptp()
        # pylint: disable=not-callable
        self.camera = gp.Camera()
        self._config = None
        self._lock = threading.RLock()

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
    def preview_as_bytes(self) -> bytes | None:
        with self._lock:
            err, file = gp.gp_camera_capture_preview(self.camera)
            if err:
                return None
            data = bytearray(gp.gp_file_get_data_and_size(file)[1])
            return data

    def preview_as_numpy(self) -> np.ndarray | None:
        with io.BytesIO() as buffer:
            res = self.preview_as_bytes()
            if not res:
                return None
            buffer.write(res)
            buffer.seek(0)
            return np.asarray(Image.open(buffer))

    @timed
    def preview_to_file(self, path: Optional[Path] = None):
        """
        Load the current preview/LiveView image as a file.
        :param path: target path, set to current working directory / preview.jpg per default.
        :return:
        """
        if path is not None:
            assert ".jpg" in path.suffixes or ".jpeg" in path.suffixes, "Capture Preview should be stores as JPG."
        else:
            path = Path("preview.jpg")
        data = self.preview_as_bytes()
        with path.open("wb") as fp:
            fp.write(data)

    def _press_and_release(self, shutter_press_time: datetime.timedelta) -> List[GImage]:
        with self._lock:
            self.set_config(self.get_config().press_shutter())
            logging.info("Pressing shutter")
            start_at = datetime.datetime.now()

            _backlog = []

            while True:
                elapsed = datetime.datetime.now() - start_at
                remaining = (shutter_press_time - elapsed).total_seconds()
                if remaining > 0:
                    evt = tuple(gp.gp_camera_wait_for_event(self.camera, int(1000 * remaining)))
                    if evt[1] == gp.GP_EVENT_FILE_ADDED:
                        _backlog.append(evt[2])
                else:
                    break

            self.set_config(self.get_config().release_shutter())
            logging.info("Released shutter")
            return _backlog + self._collect_images_added()

    def _collect_images_added(self, max_wait_seconds=20) -> List[GImage]:
        """
        Collects a list of images added to the camera within the specified time frame.

        This method waits for camera events and gathers images that are added during
        the specified waiting period. If no "file added" events are captured and the
        time expires, it raises a PyDSLRException.

        :param max_wait_seconds: Maximum time to wait for image addition events, in seconds
            (default is 20).
        :return: A list of added images.
        :rtype: List[GImage]
        :raises PyDSLRException: If no capture event or file addition is detected
            within the allowed timeframe.
        """
        with self._lock:
            _images = []
            start_wait_at = datetime.datetime.now()
            while (datetime.datetime.now() - start_wait_at).total_seconds() < max_wait_seconds:
                evt = gp.gp_camera_wait_for_event(self.camera, 100)
                if evt[1] == gp.GP_EVENT_FILE_ADDED:
                    _images.append(evt[2])
                elif evt[1] == gp.GP_EVENT_CAPTURE_COMPLETE:
                    return _images

            if not _images:
                raise PyDSLRException("No capture event detected")

            return _images

    def _download_images(self, images: List[GImage], keep_on_camera=False, folder: Optional[Path] = None) -> List[Path]:
        """
        Downloads images from a camera to a specified folder. It retrieves each image, saves it
        to local storage, and optionally deletes the image from the camera based on the provided
        configuration and flag.

        :param images: List of GImage objects to download.
        :param keep_on_camera: Whether to keep the images on the camera after download. Defaults to False.
        :param folder: Optional local folder where the images will be saved. Defaults to the parent of the current
            directory if not specified.
        :return: A list of Paths representing the locations of the saved images.

        :raises ValueError: If the specified folder does not exist.
        """
        if folder is None:
            folder = Path().parent

        if not folder.exists():
            raise ValueError(f"Folder {folder} does not exist")

        with self._lock:
            paths = []
            for image in images:
                c_file = gp.check_result(gp.gp_camera_file_get(self.camera, image.folder, image.name, gp.GP_FILE_TYPE_NORMAL))
                c_path = folder / image.name
                c_file.save(str(c_path))

                if c_path.stat().st_size == 0:
                    c_path.unlink()
                    logging.warning("Got zero-byte image during capture(). Make sure auto focus is possible.")
                    continue

                paths.append(c_path)
                logging.info("Got picture with EXIF: %s in %s", get_exif(c_path), c_path)

                if not keep_on_camera or not self.get_config().is_sdcard_capture_enabled():
                    gp.check_result(gp.gp_camera_file_delete(self.camera, image.folder, image.name))

        return paths

    @timed
    def highspeed_capture(self, shutter_press_time: datetime.timedelta, folder: Optional[Path] = None, keep_on_camera: bool = False) -> List[Path]:
        """
        Keeps the shutter button pressed fully for the given time, downloading all captured images.

        :param shutter_press_time: Time for the shutter to stay pressed
        :param folder: Target folder, defaults to current working directory. Images will be named as on camera.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :return: All paths captured.
        """
        return self._download_images(self._press_and_release(shutter_press_time), folder=folder, keep_on_camera=keep_on_camera)

    @timed
    def bulb_capture(self, shutter_press_time: datetime.timedelta, folder: Optional[Path] = None, keep_on_camera: bool = False) -> List[Path]:
        """
        Keeps the shutter button pressed fully for the given time, taking just one image

        :param shutter_press_time: Time for the shutter to stay pressed
        :param folder: target path, set to current working directory / camera image name per default.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :return:
        """
        return self._download_images(self._press_and_release(shutter_press_time), folder=folder, keep_on_camera=keep_on_camera)

    @retry(tries=5, delay=0.1, backoff=2, logger=logging.root)
    @timed
    def capture(self, folder: Optional[Path] = None, keep_on_camera: bool = False) -> List[Path]:
        """
        Capture a full image to disk.
        :param folder: If set, image will be put into this folder with the camera image name.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :return: The final path.
        """
        with self._lock:
            logging.info("Triggering capture")
            gp.check_result(gp.gp_camera_trigger_capture(self.camera))
            return self._download_images(self._collect_images_added(), keep_on_camera=keep_on_camera, folder=folder)

    def focus_stack(self, n_images: int = 10, distance: int = 1, folder: Optional[Path] = None, keep_on_camera: bool = False) -> List[Path]:
        """
        Perform focus stacking, from near to far.
        :param distance: Focus step. See also :meth:`BaseConfig.focus_step`
        :param n_images: Number of steps/images.
        :param folder: Folder to save images to, defaults to current folder.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :return: All paths captured.
        """
        with self._lock:
            results = []
            for _ in trange(n_images, desc="Performing focus stack"):
                results.extend(self.capture(path=folder, keep_on_camera=keep_on_camera))
                self.set_config(self.get_config().focus_step(distance=distance), ignore_cache=True)
            return results

    def get_config(self, ignore_cache: bool = False) -> "T":
        """
        Get the current configuration of the camera.
        :return:
        """
        with self._lock:
            response = self.get_json_config(ignore_cache=ignore_cache)

            def _get_kwargs(node):
                if "children" not in node:
                    return node["value"]
                return {n["name"]: _get_kwargs(n) for n in node["children"]}

            return get_args(self.__orig_class__)[0](**_get_kwargs(response))  # type: ignore

    @contextmanager
    def config_context(self, new_config: T):
        """
        Context manager around settings to only shortly update settings.
        :param new_config: New config to be set temporarily
        :return:
        """
        with self._lock:
            old_config = self.get_config()
            changed_fields = self.set_config(new_config)
        yield
        with self._lock:
            self.set_config(old_config, only_fields=changed_fields)

    @timed
    def set_config(self, new_config: T, only_fields: Optional[Set[str]] = None, ignore_cache: bool = False) -> Set[str]:
        """
        Set the config, optionally limited to a set of named fields.
        Returns those fields that actually were modified.

        :param ignore_cache: Forces a new copy of the config to be created. Useful when issuing one-time actions, such as focus control.
        :param new_config: New (partial) config to set.
        :param only_fields: Exhaustive list of names of fields that should be set.
        :return:
        """
        with self._lock:
            updated_settings = set()
            old_config = self.get_config(ignore_cache=ignore_cache)
            gp_config = self._gp_get_camera_config_cached(ignore_cache=ignore_cache)

            for field in new_config.model_fields_set:
                if getattr(new_config, field, None) is not None:
                    for field2 in getattr(new_config, field).model_fields_set:
                        if only_fields is not None and field2 not in only_fields:
                            logging.debug("Skipping over %s.%s, as not in only_fields", field, field2)
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
                            updated_settings.add(field2)
                            _, gp_field = gp.gp_widget_get_child_by_name(gp_config, field2)
                            gp.check_result(gp.gp_widget_set_value(gp_field, new_value))

            if updated_settings:
                time.sleep(0.05)
                # this may throw I/O errors, but works
                gp.check_result(gp.gp_camera_set_config(self.camera, gp_config))
                self._config = gp_config

            return updated_settings

    @timed
    def _gp_get_camera_config_cached(self, ignore_cache: bool = False):
        with self._lock:
            if self._config is None or ignore_cache:
                self._config = self.camera.get_config()
            return self._config

    def get_json_config(self, ignore_cache: bool = False):
        """
        Get the current config including all options and accessible fields
        :return:
        """
        config_tree = self._gp_get_camera_config_cached(ignore_cache=ignore_cache)

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
                settings=Settings(capturetarget="Memory card"),
                capturesettings=CaptureSettings(aperture="5.6"),
            )
        )
        for j in range(5):
            print(c.capture(keep_on_camera=True))
