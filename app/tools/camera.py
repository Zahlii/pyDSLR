import datetime
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Set, Tuple, Optional

import gphoto2 as gp
import psutil
import pytz

from app.config.r6m2 import Config, ImageSettings, CaptureSettings, Settings
from app.tools.exif import get_exif
from app.utils import timed, GPWidgetItem

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG
)


class Camera:
    def __init__(self):
        self._maybe_kill_ptp()
        self.camera = gp.Camera()

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

    @property
    def is_raw(self):
        return "raw" in self._get_config_value("imageformat").lower()

    @property
    def camera_time(self):
        return pytz.utc.localize(
            datetime.datetime.fromtimestamp(self._get_config_value("datetimeutc"))
        )

    @timed
    def preview_as_bytes(self) -> bytes:
        file = gp.check_result(gp.gp_camera_capture_preview(self.camera))
        return gp.check_result(gp.gp_file_get_data_and_size(file))

    @timed
    def capture_preview(self, path: Path = None):
        """
        Capture a preview. If settings were recently updated, this may not yet fully reflect it, as the
        camera usually keeps the preview buffered.
        :param path:
        :return:
        """
        if path is not None:
            assert (
                ".jpg" in path.suffixes or ".jpeg" in path.suffixes
            ), "Capture Preview should be stores as JPG."
        else:
            path = Path("preview.jpg")
        data = self.preview_as_bytes()

        with path.open("wb") as fp:
            fp.write(data)

    def stream(self, max_fps=60, max_time: datetime.timedelta = None):
        """
        Yield images as part of a media stream
        :param max_fps
        :param max_time
        :return:
        """
        last = None
        first = datetime.datetime.utcnow()
        delay = datetime.timedelta(milliseconds=1000 / max_fps)  #
        while True:
            if last is not None:
                remaining_delay = last + delay - datetime.datetime.utcnow()
                if remaining_delay.total_seconds() > 0:
                    time.sleep(remaining_delay.total_seconds())
            last = datetime.datetime.utcnow()
            if max_time is not None and (last - first) > max_time:
                return
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + bytearray(self.preview_as_bytes())
                + b"\r\n"
            )

    @timed
    def capture(self, path: Path = None, keep_on_camera: bool = False):
        """
        Capture a full image to disk.
        :param keep_on_camera:
        :param path:
        :return:
        """
        if path is not None:
            if self.is_raw:
                assert (
                    ".cr3" in path.suffixes
                ), "RAW format enabled, file format should be cr3"
            else:
                assert (
                    ".jpg" in path.suffixes or ".jpeg" in path.suffixes
                ), "RAW format disabled, image should be stores as JPG."
        else:
            if self.is_raw:
                path = Path("image.cr3")
            else:
                path = Path("image.jpg")

        file = gp.check_result(gp.gp_camera_capture(self.camera, gp.GP_CAPTURE_IMAGE))
        c_file = gp.check_result(
            gp.gp_camera_file_get(
                self.camera, file.folder, file.name, gp.GP_FILE_TYPE_NORMAL
            )
        )
        c_file.save(str(path))

        if (
            not keep_on_camera
            or self.get_config().settings.capturetarget == "Internal RAM"
        ):
            gp.gp_camera_file_delete(self.camera, file.folder, file.name)

        exif_data = get_exif(path)
        logging.info("Got picture with EXIF: %s", exif_data)
        return exif_data

    @timed
    def _get_config_value(self, name: str):
        """
        Read one value from config
        :param name:
        :return:
        """
        config = gp.check_result(gp.gp_camera_get_config(self.camera))
        image_format = gp.check_result(gp.gp_widget_get_child_by_name(config, name))
        return gp.check_result(gp.gp_widget_get_value(image_format))

    def get_config(self) -> "Config":
        """
        Get the current configuration of the camera.
        :return:
        """

        response = self.get_json_config()

        def _get_kwargs(node):
            if "children" not in node:
                return node["value"]
            return {n["name"]: _get_kwargs(n) for n in node["children"]}

        return Config(**_get_kwargs(response))

    @contextmanager
    def config_context(self, new_config: "Config"):
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
    def set_config(
        self, new_config: "Config", only_fields: Optional[Set[Tuple[str, str]]] = None
    ) -> Set[Tuple[str, str]]:
        """
        Set the config, optionally limited to a set of named fields.
        Returns those fields that actually were modified.

        :param new_config:
        :param only_fields:
        :return:
        """
        updated_settings = set()
        old_config = self.get_config()

        gp_config = gp.check_result(gp.gp_camera_get_config(self.camera))

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
                        gp_field = gp.check_result(
                            gp.gp_widget_get_child_by_name(gp_config, field2)
                        )
                        gp.check_result(gp.gp_widget_set_value(gp_field, new_value))

        if updated_settings:
            gp.check_result(gp.gp_camera_set_config(self.camera, gp_config))
        return updated_settings

    def get_json_config(self):
        """
        Get the current config including all options and accessible fields
        :return:
        """
        config_tree = self.camera.get_config()

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
                    "children": [
                        _traverse(node.get_child(i), depth + 1)
                        for i in range(node.count_children())
                    ],
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
                    for j in range(node.count_choices()):
                        config["options"].append(node.get_choice(j))

                    if value not in config["options"]:
                        config["options"].append(value)
            return config

        return _traverse(config_tree)


if __name__ == "__main__":
    with Camera() as c:
        c.set_config(
            Config(
                imgsettings=ImageSettings(iso="400"),
                settings=Settings(capturetarget="Memory card"),
                capturesettings=CaptureSettings(aperture="2.8", shutterspeed="bulb"),
            )
        )
        print(c.capture(keep_on_camera=True))
