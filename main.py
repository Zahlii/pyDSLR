"""
REST Server to communicate with Camera
"""

import base64
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pydslr.config.r6m2 import ImageSettings, R6M2Config
from pydslr.tools.camera import Camera, CaptureDevice, OpenCVCaptureDevice, OverlayCaptureDevice
from pydslr.tools.exif import ExifInfo, get_exif
from pydslr.tools.printer import PrinterService

camera: Optional[OverlayCaptureDevice] = None
img_path = Path("~").expanduser() / "dslr-tool"
img_path.mkdir(exist_ok=True)
logging.info("Saving pictures to %s", img_path)


class SnapshotResponse(BaseModel):
    image_path: str
    image_b64: str
    exif: ExifInfo | None = None


class PrintRequest(BaseModel):
    image_path: str
    copies: int = 1
    landscape: bool = True
    printer_name: str | None = None


@asynccontextmanager
async def lifespan(_):
    """
    Handle camera context manager behind FastAPI pydslr
    :param _:
    :return:
    """
    # pylint: disable=global-statement
    global camera
    # with Camera[R6M2Config]() as c:
    #     with c.config_context(R6M2Config(imgsettings=ImageSettings(imageformat="Large Fine JPEG"))):
    #         camera = OverlayCaptureDevice(c, overlay_path="/Users/niklas.fruehauf/Downloads/Ein Bild V1 (2).png")
    #         yield
    with OverlayCaptureDevice(OpenCVCaptureDevice(), overlay_path="/Users/niklas.fruehauf/Downloads/Ein Bild V1 (2).png") as c:
        # with OverlayCaptureDevice(OpenCVCaptureDevice(), overlay_path=None) as c:
        camera = c
        yield


backend_router = FastAPI()
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@backend_router.get("/stream")
def stream():
    """
    Display a live stream from the camera
    :return:
    """
    return StreamingResponse(camera.stream_preview(max_fps=30, max_time=timedelta(seconds=15)), media_type="multipart/x-mixed-replace;boundary=frame")


@backend_router.get("/last")
def last_image():
    """
    Return last captured image or placeholder if available
    :return: JPEG image response
    """
    if camera and camera.placeholder():
        with BytesIO() as bio:
            camera.placeholder().save(bio, format="JPEG")
            bio.seek(0)
            return Response(content=bio.getvalue(), media_type="image/jpeg")
    return None


@backend_router.get("/config")
def config():
    """

    :return:
    """
    return camera.get_config()


@backend_router.get("/snapshot")
def create_snapshot():
    """
    Take and save a snapshot with current settings

    :return:
    """
    result_path = camera.capture(folder=img_path)

    # Read the image file and encode it as base64
    with result_path.open("rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    return SnapshotResponse(
        image_path=str(result_path.relative_to(img_path)), exif=get_exif(result_path), image_b64=f"data:image/jpeg;base64,{encoded_image}"
    )


@backend_router.delete("/snapshot")
def delete_snapshot(snapshot_name: str):
    full_path = img_path / snapshot_name
    assert img_path in full_path.parents, f"Image {full_path} is not in {img_path}"

    raw_path = full_path.with_name(full_path.name.replace("_overlay", ""))
    if raw_path.exists():
        raw_path.unlink()
    if full_path.exists():
        full_path.unlink()
    return True


@backend_router.post("/print")
def do_print(print_request: PrintRequest):
    full_path = img_path / print_request.image_path
    assert full_path.exists(), f"Image {full_path} does not exist"
    assert img_path in full_path.parents, f"Image {full_path} is not in {img_path}"

    return PrinterService.print_image(
        image_path=full_path, copies=print_request.copies, printer_name=print_request.printer_name, landscape=print_request.landscape
    )


app.mount("/api", backend_router)

ui_path = Path(__file__).parent / "booth-ui"
app.mount("/", StaticFiles(directory=ui_path / "dist" / "photo-booth-ui" / "browser", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
