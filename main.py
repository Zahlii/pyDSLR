from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.config.r6m2 import Settings, Config
from app.tools.camera import Camera

camera: Optional[Camera] = None


@asynccontextmanager
async def lifespan(_):
    global camera
    with Camera() as c:
        camera = c
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/stream")
def index():
    return StreamingResponse(
        camera.stream(), media_type="multipart/x-mixed-replace;boundary=frame"
    )


@app.get("/config", response_model=Config)
def config():
    return camera.get_config()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
