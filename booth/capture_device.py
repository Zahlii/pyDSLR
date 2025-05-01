"""
Additional capture device implementations
"""

import datetime
import io
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
from PIL import Image

from pydslr.tools.camera import CaptureDevice, ImageBunch, T
from pydslr.tools.exif import get_exif
from pydslr.utils import PyDSLRException


class OpenCVCaptureDevice(CaptureDevice[T]):
    """
    Capture device using opencv-python to read from webcam
    """

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
        """
        Close the webcam capture device
        :return:
        """
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None

    def get_lr_coords(self, frame: np.ndarray) -> tuple[int, int]:
        """
        Get the left/right coords so that image is cropped to 3:2 aspect ratio
        :param frame:
        :return:
        """
        height, width = frame.shape[:2]
        target_width = int(height * 3 / 2)
        # Otherwise crop width to match target ratio
        crop_width = (width - target_width) // 2
        return crop_width, width - crop_width

    def preview_as_numpy(self) -> np.ndarray | None:
        if not self._cap or not self._cap.isOpened():
            self._initialize_capture()

        import cv2

        assert self._cap is not None
        ret, frame = self._cap.read()
        if not ret:
            raise PyDSLRException("Failed to read frame from webcam")

        # Get crop dimensions
        left, right = self.get_lr_coords(frame)

        # Crop and convert BGR to RGB
        cropped_frame = frame[:, left:right]
        rgb_frame = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2RGB)
        return rgb_frame

    def preview_as_bytes(self) -> bytes | None:
        import cv2

        # Get RGB frame from preview_as_numpy
        rgb_frame = self.preview_as_numpy()
        if rgb_frame is None:
            return None

        # Convert RGB back to BGR for cv2.imencode which expects BGR
        bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

        success, buffer = cv2.imencode(".jpg", bgr_frame)
        if not success:
            raise PyDSLRException("Failed to encode frame as JPEG")

        return buffer.tobytes()

    def capture(self, folder: Optional[Path] = None, keep_on_camera: bool = False) -> ImageBunch:
        if folder is None:
            folder = Path().parent

        if not folder.exists():
            raise ValueError(f"Folder {folder} does not exist")

        # Get frame in RGB format with 3:2 aspect ratio
        frame = self.preview_as_numpy()
        assert frame is not None

        # Generate filename with timestamp if not provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = folder / f"webcam_{timestamp}.jpg"

        import cv2

        # Convert RGB to BGR for cv2.imwrite which expects BGR
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Write the image to disk
        success = cv2.imwrite(str(filename), bgr_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not success:
            raise PyDSLRException(f"Failed to save image to {filename}")

        logging.info("Got picture with EXIF: %s in %s", get_exif(filename), filename)
        return [filename]


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
        """
        Update the overlay image
        :param overlay_path:
        :return:
        """
        if overlay_path is not None:
            self._overlay_path = Path(overlay_path)
            if not self._overlay_path.exists():
                raise PyDSLRException(f"Overlay image not found at {self._overlay_path}")

            # Load the overlay image
            self._overlay_image = Image.open(self._overlay_path).convert("RGBA")
            prev = self._inner_device.preview_as_numpy()
            if prev is None:
                raise ValueError(f"Failed getting preview frame from {self._inner_device}.")
            self._last_preview = Image.fromarray(prev)
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
            if self._overlay_image_resized.size != base_image:
                assert self._overlay_image is not None
                # can happen if preview and real image have differing sizes
                self._overlay_image_resized = self._overlay_image.resize(base_image.size, Image.Resampling.LANCZOS)
            # Composite the images
            result = Image.alpha_composite(base_image, self._overlay_image_resized).convert("RGB")
        else:
            result = base_image.convert("RGB")
        self._last_preview = result
        return np.array(base_image.convert("RGB")), np.array(result)

    def placeholder(self) -> Image.Image | None:
        """
        Get the placeholder image, i.e. last available one
        :return:
        """
        return self._last_preview

    def preview_as_numpy(self) -> np.ndarray | None:
        base_image = self._inner_device.preview_as_numpy()
        return self._apply_overlay(base_image)[1] if base_image is not None else None

    def preview_as_bytes(self) -> bytes | None:
        overlay_array = self.preview_as_numpy()
        if overlay_array is None:
            return None

        # Convert to bytes
        buffer = io.BytesIO()
        Image.fromarray(overlay_array).save(buffer, format="JPEG")
        return buffer.getvalue()

    def get_config(self, ignore_cache: bool = False) -> Optional["T"]:
        return self._inner_device.get_config(ignore_cache=ignore_cache)

    def capture(self, folder: Optional[Path] = None, keep_on_camera: bool = False) -> ImageBunch:
        # Get original capture from inner device
        original_paths = self._inner_device.capture(folder=folder, keep_on_camera=keep_on_camera)
        jpeg_path = [p for p in original_paths if p.suffix.lower() in {".jpg", ".jpeg"}][0]

        # Read the captured image
        with Image.open(jpeg_path) as img:
            base_image = np.array(img)

        # Apply overlay and potentially mirror
        base_image, result_image = self._apply_overlay(base_image)
        if self.mirror_image:
            Image.fromarray(base_image).save(jpeg_path, format="JPEG", quality=95, optimize=True)

        # Create a path for the overlay version
        stem = jpeg_path.stem
        suffix = jpeg_path.suffix
        overlay_path = jpeg_path.with_name(f"{stem}_overlay{suffix}")
        Image.fromarray(result_image).save(overlay_path, format="JPEG", quality=95, optimize=True)

        # Return the overlay path
        return [overlay_path] + original_paths
