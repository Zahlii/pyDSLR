"""
REST Server to communicate with Camera
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from pydslr.tools.camera import CaptureDevice, OpenCVCaptureDevice

camera: Optional[CaptureDevice] = None
img_path = Path("~").expanduser() / "dslr-tool"
img_path.mkdir(exist_ok=True)
logging.info("Saving pictures to %s", img_path)


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


@app.post("/snapshot")
def snapshot():
    """
    Take and save a snapshot with current settings

    :return:
    """
    camera.capture()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
