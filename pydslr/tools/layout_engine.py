from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import ujson as json
from pydantic import BaseModel

from pydslr.tools.camera import OpenCVCaptureDevice, OverlayCaptureDevice

layout_path = Path(__file__).parent.parent / "layouts"


class Layout(BaseModel):
    file: str | None = None
    layout: Literal["1", "2x2"] = "1"

    @property
    def path(self):
        return layout_path / self.file if self.file else None


class LayoutEngine:
    _camera: OverlayCaptureDevice | None = None
    _active_layout: Layout = Layout(file=None, layout="1")

    @staticmethod
    def available_layouts():
        with (layout_path / "layouts.json").open("r", encoding="utf8") as f:
            return [Layout.model_validate(o) for o in json.load(f)]

    @staticmethod
    def get_image(filename: str):
        return layout_path / filename

    @staticmethod
    def set_layout(layout: Layout):
        assert LayoutEngine._camera is not None, "Camera not initialized"
        LayoutEngine._active_layout = layout
        if layout.layout != "1" or layout.file is None:
            LayoutEngine._camera.set_overlay(None)
        else:
            LayoutEngine._camera.set_overlay(LayoutEngine.get_image(layout.file))

    @staticmethod
    @contextmanager
    def get_capture_device():
        # with Camera[R6M2Config]() as c:
        #     with c.config_context(R6M2Config(imgsettings=ImageSettings(imageformat="Large Fine JPEG"))):
        #         camera = OverlayCaptureDevice(c, overlay_path="/Users/niklas.fruehauf/Downloads/example_1.png")
        #         yield
        with OverlayCaptureDevice(OpenCVCaptureDevice(), overlay_path=None) as LayoutEngine._camera:
            yield LayoutEngine._camera
