"""
REST Server to communicate with Camera
"""

import base64
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pydslr.tools.camera import CaptureDevice, OpenCVCaptureDevice
from pydslr.tools.exif import ExifInfo, get_exif
from pydslr.tools.printer import PrinterService

camera: Optional[CaptureDevice] = None
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
    with OpenCVCaptureDevice() as c:
        camera = c
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/stream")
def stream():
    """
    Display a live stream from the camera
    :return:
    """
    return StreamingResponse(camera.stream_preview(max_fps=30), media_type="multipart/x-mixed-replace;boundary=frame")


@app.get("/config")
def config():
    """

    :return:
    """
    return camera.get_config()


@app.get("/snapshot")
def snapshot():
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


@app.post("/print")
def do_print(print_request: PrintRequest):
    full_path = img_path / print_request.image_path
    assert full_path.exists(), f"Image {full_path} does not exist"
    assert img_path in full_path.parents, f"Image {full_path} is not in {img_path}"

    return PrinterService.print_image(
        image_path=full_path, copies=print_request.copies, printer_name=print_request.printer_name, landscape=print_request.landscape
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
