"""
Helpers to render different layouts
"""

import base64
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import List, Literal, Optional

import ujson as json
from PIL import Image
from pydantic import BaseModel, computed_field

from booth.capture_device import OverlayCaptureDevice
from pydslr.tools.camera import Camera
from pydslr.tools.exif import ExifInfo, get_exif

img_path = Path("~").expanduser() / "dslr-tool"
img_path.mkdir(exist_ok=True)
logging.info("Saving pictures to %s", img_path)


class SnapshotResponse(BaseModel):
    """
    Contains a snapshot response
    """

    image_path: str
    image_b64: str
    image_path_raw: str
    image_b64_raw: str
    image_path_camera_raw: Optional[str]
    all_paths: List[str]
    exif: ExifInfo | None = None

    @classmethod
    def from_file(cls, image: Path, image_raw: Path, image_camera_raw: Optional[Path] = None) -> "SnapshotResponse":
        """
        Create a snapshot response from a file
        :param image_camera_raw:
        :param image:
        :param image_raw:
        :return:
        """
        assert image.exists(), f"Image {image} does not exist"
        assert image_raw.exists(), f"Image {image_raw} does not exist"

        image_path = str(image.relative_to(img_path))
        image_path_raw = str(image_raw.relative_to(img_path))
        image_path_camera_raw = str(image_camera_raw.relative_to(img_path)) if image_camera_raw is not None else None

        return SnapshotResponse(
            image_path=image_path,
            image_path_raw=image_path_raw,
            image_b64=f"data:image/jpeg;base64,{base64.b64encode(image.read_bytes()).decode('utf-8')}",
            image_b64_raw=f"data:image/jpeg;base64,{base64.b64encode(image_raw.read_bytes()).decode('utf-8')}",
            image_path_camera_raw=image_path_camera_raw,
            exif=get_exif(image),
            all_paths=[image_path, image_path_raw] + ([image_path_camera_raw] if image_path_camera_raw is not None else []),
        )


layout_path = Path(__file__).parent / "layouts"


class Layout(BaseModel):
    """
    Definition for a specific layout as used in layout.json
    """

    file: str | None = None
    layout: Literal["1", "2x2"] = "1"

    @property
    def path(self):
        """
        Get the path to the layout image
        :return:
        """
        return layout_path / self.file if self.file else None

    @computed_field  # type: ignore
    @property
    def n_images(self) -> int:
        """
        How many images are required for this layout?
        :return:
        """
        if self.layout == "1":
            return 1
        if self.layout == "2x2":
            return 4
        raise ValueError("Only layout 1 and 2x2 are supported")


class LayoutEngine:
    """
    Handles the rendering of different layouts
    """

    _camera: OverlayCaptureDevice | None = None
    _active_layout: Layout = Layout(file=None, layout="1")

    @staticmethod
    def available_layouts():
        """
        Load available layouts from disk
        :return:
        """
        with (layout_path / "layouts.json").open("r", encoding="utf8") as f:
            return [Layout.model_validate(o) for o in json.load(f)]

    @staticmethod
    def get_image(filename: str):
        """
        Resolve a file name to a full path
        :param filename:
        :return:
        """
        return layout_path / filename

    @staticmethod
    def set_layout(layout: Layout):
        """
        Sets the active layout
        :param layout:
        :return:
        """
        assert LayoutEngine._camera is not None, "Camera not initialized"
        LayoutEngine._active_layout = layout
        if layout.layout != "1" or layout.file is None:
            LayoutEngine._camera.set_overlay(None)
        else:
            LayoutEngine._camera.set_overlay(LayoutEngine.get_image(layout.file))

    @staticmethod
    @contextmanager
    def get_capture_device():
        """
        Initiates the used capture device
        :return:
        """
        from pydslr.config.r6m2 import R6M2Config

        with Camera[R6M2Config]() as c:
            LayoutEngine._camera = OverlayCaptureDevice(c, overlay_path=None)
            yield LayoutEngine._camera

        # with OverlayCaptureDevice(OpenCVCaptureDevice(), overlay_path=None) as LayoutEngine._camera:
        #     yield LayoutEngine._camera

    @staticmethod
    def render_layout(image_names: List[str]) -> SnapshotResponse:
        """
        Given a list of image names, render the layout
        :param image_names:
        :return:
        """
        # pylint: disable=too-many-locals
        if LayoutEngine._active_layout.layout == "1":
            file = image_names[-1]
            raw_file = file.replace("_overlay", "") if LayoutEngine._active_layout.file else file

            return SnapshotResponse.from_file(
                image=img_path / file,
                image_raw=img_path / raw_file,
            )
        if LayoutEngine._active_layout.layout == "2x2":
            # Get the last 4 images
            raw_files = [name.replace("_overlay", "") for name in image_names[-4:]]

            # Load all images
            images = [Image.open(img_path / f) for f in raw_files]

            # Get dimensions of first image (assuming all are same size)
            width, height = images[0].size

            # Resize images to 25% of original size
            scaled_width = width // 2
            scaled_height = height // 2
            images = [img.resize((scaled_width, scaled_height)) for img in images]

            # Create a new image with original dimensions
            combined = Image.new("RGB", (width, height))

            # Paste images in 2x2 grid
            positions = [(0, 0), (scaled_width, 0), (0, scaled_height), (scaled_width, scaled_height)]
            for img, pos in zip(images, positions):
                combined.paste(img, pos)

            # Save the combined image
            output_path = img_path / f"combined_{raw_files[-1]}"
            combined.save(output_path, "JPEG", quality=95, optimize=True)

            if LayoutEngine._active_layout.file:
                # Add overlay if specified
                overlay = Image.open(LayoutEngine.get_image(LayoutEngine._active_layout.file))
                overlay = overlay.resize((width, height))
                combined = Image.alpha_composite(combined.convert("RGBA"), overlay).convert("RGB")
                overlay_path = img_path / f"combined_overlay_{raw_files[-1]}"
                combined.save(overlay_path, "JPEG", quality=95, optimize=True)
                return SnapshotResponse.from_file(image=overlay_path, image_raw=output_path)

            return SnapshotResponse.from_file(image=output_path, image_raw=output_path)

        raise ValueError("Only layout 1 and 2x2 are supported")

    @classmethod
    def has_overlay(cls):
        """
        Check if the active layout has an overlay
        :return:
        """
        return LayoutEngine._active_layout.file is not None
