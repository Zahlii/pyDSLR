"""
REST Server to communicate with Camera
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from pydslr.tools.camera import Camera, T

camera: Optional[Camera] = None


@asynccontextmanager
async def lifespan(_):
    """
    Handle camera context manager behind FastAPI pydslr
    :param _:
    :return:
    """
    # pylint: disable=global-statement
    global camera
    with Camera() as c:
        camera = c
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/stream")
def stream():
    """
    Display a live stream from the camera
    :return:
    """
    return StreamingResponse(camera.stream_preview(), media_type="multipart/x-mixed-replace;boundary=frame")


@app.get("/config", response_model=T)
def config():
    """

    :return:
    """
    return camera.config


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
