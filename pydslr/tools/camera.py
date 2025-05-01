"""
Main Camera class
"""

# pylint: disable=no-member
import datetime
import io
import logging
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Generic, List, Optional, Set, Tuple, TypeVar, Union, get_args

import gphoto2 as gp  # type: ignore
import numpy as np
import psutil
from PIL import Image
from tqdm import trange

from pydslr.config.base import BaseConfig
from pydslr.config.r6m2 import CaptureSettings, ImageSettings, R6M2Config, Settings
from pydslr.tools.exif import get_exif
from pydslr.utils import GPWidgetItem, PyDSLRException, timed

T = TypeVar("T", bound=BaseConfig)


class CaptureDevice(ABC, Generic[T]):
    @abstractmethod
    def preview_as_numpy(self) -> np.ndarray:
        """
        Load the current preview/LiveView image as numpy array via Image.open()
        :return:
        """

    @abstractmethod
    def preview_as_bytes(self) -> bytes:
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

    @abstractmethod
    def capture(self, path: Optional[Path] = None, folder: Optional[Path] = None, keep_on_camera: bool = False) -> Path:
        """
        Capture a full image to disk.
        :param folder: can be set instead of target path. If set, image will be put into this folder with the camera image name.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :param path: target path, set to current working directory / camera image name per default.
        :return: The final path.
        """


class OpenCVCaptureDevice(CaptureDevice[T]):
    def get_config(self, ignore_cache: bool = False) -> Optional["T"]:
        return None

    def __init__(self, camera_index: int = 0):
        """
        Initialize a webcam capture device

        :param camera_index: Index of the camera to use (default 0 for primary webcam)
        """
        self.camera_index = camera_index
        self._cap = None
        self._initialize_capture()

    def _initialize_capture(self):
        import cv2

        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            raise PyDSLRException(f"Failed to open webcam at index {self.camera_index}")

    def __enter__(self):
        if not self._cap or not self._cap.isOpened():
            self._initialize_capture()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None

    def preview_as_numpy(self) -> np.ndarray:
        if not self._cap or not self._cap.isOpened():
            self._initialize_capture()

        import cv2

        assert self._cap is not None
        ret, frame = self._cap.read()
        if not ret:
            raise PyDSLRException("Failed to read frame from webcam")

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return rgb_frame

    def preview_as_bytes(self) -> bytes:
        import cv2

        # Get RGB frame from preview_as_numpy
        rgb_frame = self.preview_as_numpy()

        # Convert RGB back to BGR for cv2.imencode which expects BGR
        bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

        success, buffer = cv2.imencode(".jpg", bgr_frame)
        if not success:
            raise PyDSLRException("Failed to encode frame as JPEG")

        return buffer.tobytes()

    def capture(self, path: Optional[Path] = None, folder: Optional[Path] = None, keep_on_camera: bool = False) -> Path:
        # Get frame in RGB format
        frame = self.preview_as_numpy()

        # Generate filename with timestamp if not provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webcam_{timestamp}.jpg"

        if path is None:
            if folder is None:
                path = Path(filename)
            else:
                path = folder / filename

        # Make sure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        import cv2

        # Convert RGB to BGR for cv2.imwrite which expects BGR
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Write the image to disk
        success = cv2.imwrite(str(path), bgr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not success:
            raise PyDSLRException(f"Failed to save image to {path}")

        logging.info("Got picture with EXIF: %s in %s", get_exif(path), path)
        return path


class OverlayCaptureDevice(CaptureDevice[T]):
    """
    A capture device that applies an overlay image on top of another capture device's output.
    """

    def __init__(self, inner_device: CaptureDevice[T], overlay_path: Union[str, Path] | None = None, mirror_image: bool = True):
        """
        Initialize an overlay capture device

        :param inner_device: The base capture device to wrap
        :param overlay_path: Path to the overlay image (PNG with transparency recommended)
        :param mirror_image: If True, mirror the base image left/right before applying overlay
        """
        self._inner_device = inner_device
        self._overlay_path: Union[str, Path] | None = None
        self._overlay_image: Image.Image | None = None
        self._last_preview: Image.Image | None = None
        self._overlay_image_resized: Image.Image | None = None

        self.mirror_image = mirror_image
        self.set_overlay(overlay_path)

    def set_overlay(self, overlay_path: Union[str, Path] | None):
        if overlay_path is not None:
            self._overlay_path = Path(overlay_path)
            if not self._overlay_path.exists():
                raise PyDSLRException(f"Overlay image not found at {self._overlay_path}")

            # Load the overlay image
            self._overlay_image = Image.open(self._overlay_path).convert("RGBA")
            self._last_preview = Image.fromarray(self._inner_device.preview_as_numpy())
            assert self._last_preview is not None
            if self._overlay_image.size != self._last_preview.size:
                self._overlay_image_resized = self._overlay_image.resize(self._last_preview.size, Image.Resampling.LANCZOS)
            else:
                self._overlay_image_resized = self._overlay_image
        else:
            self._overlay_image = None
            self._overlay_image_resized = None

    def __enter__(self):
        self._inner_device.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._inner_device.__exit__(exc_type, exc_val, exc_tb)

    def _apply_overlay(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply the overlay to a numpy array image

        :param image: Base image as numpy array
        :return: Image with overlay applied
        """
        # Handle other formats
        base_image = Image.fromarray(image)
        base_image = base_image.convert("RGBA")

        # Mirror the image if requested
        if self.mirror_image:
            base_image = base_image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        if self._overlay_image_resized is not None:
            # Composite the images
            result = Image.alpha_composite(base_image, self._overlay_image_resized).convert("RGB")
        else:
            result = base_image.convert("RGB")
        self._last_preview = result
        return np.array(base_image.convert("RGB")), np.array(result)

    def placeholder(self) -> Image.Image | None:
        return self._last_preview

    def preview_as_numpy(self) -> np.ndarray:
        base_image = self._inner_device.preview_as_numpy()
        return self._apply_overlay(base_image)[1]

    def preview_as_bytes(self) -> bytes:
        overlay_array = self.preview_as_numpy()

        # Convert to bytes
        buffer = io.BytesIO()
        Image.fromarray(overlay_array).save(buffer, format="JPEG")
        return buffer.getvalue()

    def get_config(self, ignore_cache: bool = False) -> Optional["T"]:
        return self._inner_device.get_config(ignore_cache=ignore_cache)

    def capture(self, path: Optional[Path] = None, folder: Optional[Path] = None, keep_on_camera: bool = False) -> Path:
        # Get original capture from inner device
        original_path = self._inner_device.capture(path=path, folder=folder, keep_on_camera=keep_on_camera)

        # Read the captured image
        with Image.open(original_path) as img:
            base_image = np.array(img)

        # Apply overlay and potentially mirror
        base_image, result_image = self._apply_overlay(base_image)
        if self.mirror_image:
            Image.fromarray(base_image).save(original_path, format="JPEG", quality=95, optimize=True)

        # Create a path for the overlay version
        stem = original_path.stem
        suffix = original_path.suffix
        overlay_path = original_path.with_name(f"{stem}_overlay{suffix}")
        Image.fromarray(result_image).save(overlay_path, format="JPEG", quality=95, optimize=True)

        # Return the overlay path
        return overlay_path


class Camera(CaptureDevice[T]):
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
        _, file = gp.gp_camera_capture_preview(self.camera)
        data = bytearray(gp.gp_file_get_data_and_size(file)[1])
        return data

    def preview_as_numpy(self) -> np.ndarray:
        with io.BytesIO() as buffer:
            buffer.write(self.preview_as_bytes())
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

    @timed
    def bulb_capture(self, shutter_press_time: datetime.timedelta, path: Optional[Path] = None, keep_on_camera: bool = False) -> Path:
        """
        Keeps the shutter button pressed fully for the given time, taking just one image

        :param shutter_press_time: Time for the shutter to stay pressed
        :param path: target path, set to current working directory / camera image name per default.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :return:
        """
        self.set_config(self.get_config().press_shutter())
        time.sleep(shutter_press_time.total_seconds())
        self.set_config(self.get_config().release_shutter())

        _image = None
        start_wait_at = datetime.datetime.now()
        while (datetime.datetime.now() - start_wait_at).total_seconds() < 20:
            evt = gp.gp_camera_wait_for_event(self.camera, 100)
            if evt[1] == gp.GP_EVENT_FILE_ADDED:
                _image = evt[2]
            elif evt[1] == gp.GP_EVENT_CAPTURE_COMPLETE:
                break

        if _image is None:
            raise PyDSLRException("No capture event detected")

        _, c_file = gp.gp_camera_file_get(self.camera, _image.folder, _image.name, gp.GP_FILE_TYPE_NORMAL)
        c_path = Path(_image.name) if path is None else path
        c_file.save(str(c_path))

        logging.info("Got picture with EXIF: %s in %s", get_exif(c_path), c_path)

        if not keep_on_camera or not self.get_config().is_sdcard_capture_enabled():
            gp.gp_camera_file_delete(self.camera, _image.folder, _image.name)

        return c_path

    @timed
    def highspeed_capture(self, shutter_press_time: datetime.timedelta, folder: Optional[Path] = None, keep_on_camera: bool = False) -> List[Path]:
        """
        Keeps the shutter button pressed fully for the given time, downloading all captured images.

        :param shutter_press_time: Time for the shutter to stay pressed
        :param folder: Target folder, defaults to current working directory. Images will be named as on camera.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :return: All paths captured.
        """

        if folder is None:
            folder = Path().parent

        if not folder.exists():
            raise ValueError(f"Folder {folder} does not exist")

        self.set_config(self.get_config().press_shutter())
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

        start_wait_at = datetime.datetime.now()
        while (datetime.datetime.now() - start_wait_at).total_seconds() < 20:
            evt = gp.gp_camera_wait_for_event(self.camera, 100)
            if evt[1] == gp.GP_EVENT_FILE_ADDED:
                _backlog.append(evt[2])
            elif evt[1] == gp.GP_EVENT_CAPTURE_COMPLETE:
                break

        paths = []
        for file in _backlog:
            _, c_file = gp.gp_camera_file_get(self.camera, file.folder, file.name, gp.GP_FILE_TYPE_NORMAL)
            c_path = folder / file.name
            paths.append(c_path)
            c_file.save(str(c_path))

            logging.info("Got picture with EXIF: %s in %s", get_exif(c_path), c_path)

            if not keep_on_camera or not self.get_config().is_sdcard_capture_enabled():
                gp.gp_camera_file_delete(self.camera, file.folder, file.name)

        return paths

    @timed
    def capture(self, path: Optional[Path] = None, folder: Optional[Path] = None, keep_on_camera: bool = False) -> Path:
        """
        Capture a full image to disk.
        :param folder: can be set instead of target path. If set, image will be put into this folder with the camera image name.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :param path: target path, set to current working directory / camera image name per default.
        :return: The final path.
        """
        if path is not None:
            if self.get_config().is_raw():
                assert ".cr3" in path.suffixes, "RAW format enabled, file format should be cr3"
            else:
                assert ".jpg" in path.suffixes or ".jpeg" in path.suffixes, "RAW format disabled, image should be stores as JPG."

        _, file = gp.gp_camera_capture(self.camera, gp.GP_CAPTURE_IMAGE)
        if path is None:
            if folder is None:
                path = Path(file.name)
            else:
                path = folder / file.name
        _, c_file = gp.gp_camera_file_get(self.camera, file.folder, file.name, gp.GP_FILE_TYPE_NORMAL)
        c_file.save(str(path))

        if not keep_on_camera or not self.get_config().is_sdcard_capture_enabled():
            gp.gp_camera_file_delete(self.camera, file.folder, file.name)

        if path.stat().st_size == 0:
            path.unlink()
            raise PyDSLRException("Got zero-byte image during capture(). Make sure auto focus is possible.")

        logging.info("Got picture with EXIF: %s in %s", get_exif(path), path)
        return path

    def focus_stack(self, n_images: int = 10, distance: int = 1, folder: Optional[Path] = None, keep_on_camera: bool = False) -> List[Path]:
        """
        Perform focus stacking, from near to far.
        :param distance: Focus step. See also :meth:`BaseConfig.focus_step`
        :param n_images: Number of steps/images.
        :param folder: Folder to save images to, defaults to current folder.
        :param keep_on_camera: If capture is to SD Card, keeps the images after downloading.
        :return: All paths captured.
        """
        results = []
        for _ in trange(n_images, desc="Performing focus stack"):
            results.append(self.capture(path=folder, keep_on_camera=keep_on_camera))
            self.set_config(self.get_config().focus_step(distance=distance), ignore_cache=True)
        return results

    def get_config(self, ignore_cache: bool = False) -> "T":
        """
        Get the current configuration of the camera.
        :return:
        """

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
        old_config = self.get_config()
        changed_fields = self.set_config(new_config)
        yield
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
                    update = True
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
            # this may throw I/O errors, but works
            gp.check_result(gp.gp_camera_set_config(self.camera, gp_config))
            self._config = gp_config

        return updated_settings

    @timed
    def _gp_get_camera_config_cached(self, ignore_cache: bool = False):
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
                settings=Settings(capturetarget="Internal RAM"),
                capturesettings=CaptureSettings(aperture="5.6", shutterspeed="2"),
            )
        )
        for j in zip(range(20), c.stream_preview()):
            print(c.capture(keep_on_camera=True))
