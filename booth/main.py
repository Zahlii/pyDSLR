"""
REST Server to communicate with Camera
"""

from contextlib import asynccontextmanager
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from booth.capture_device import OverlayCaptureDevice
from booth.layout_engine import Layout, LayoutEngine, SnapshotResponse, booth_config, img_path
from booth.printer import PrinterService, PrintRequest

camera: Optional[OverlayCaptureDevice] = None


root_path = Path(__file__).parent.parent


@asynccontextmanager
async def lifespan(_):
    """
    Handle camera context manager behind FastAPI pydslr
    :param _:
    :return:
    """
    # pylint: disable=global-statement
    global camera
    with LayoutEngine.get_capture_device() as c:
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
    return StreamingResponse(camera.stream_preview(max_fps=60, max_time=timedelta(seconds=35)), media_type="multipart/x-mixed-replace;boundary=frame")


@backend_router.get("/config")
def config():
    """
    Return the complete configuration

    :return:
    """
    return booth_config


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


@backend_router.get("/camera_config")
def camera_config():
    """

    :return:
    """
    return camera.get_config()


@backend_router.get("/snapshot")
def create_snapshot() -> SnapshotResponse:
    """
    Take and save a snapshot with current settings

    :return:
    """
    assert camera is not None, "Camera not initialized"

    result_paths = camera.capture(folder=img_path)
    result_path = result_paths[0]

    camera_raw: Path | None = None
    for pth in result_paths[1:]:
        if pth.suffix.lower() not in {".jpg", ".jpeg"}:
            camera_raw = pth
            break

    if LayoutEngine.has_overlay():
        result_path_raw = result_path.with_name(result_path.name.replace("_overlay", ""))
    else:
        result_path_raw = result_path

    return SnapshotResponse.from_file(
        image=result_path,
        image_raw=result_path_raw,
        image_camera_raw=camera_raw,
    )


@backend_router.delete("/snapshots")
def delete_snapshot(snapshot_names: List[str]):
    """
    Delete a list of snapshots
    :param snapshot_names:
    :return:
    """
    for snapshot_name in set(snapshot_names):
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
    """
    Issue a print command
    :param print_request:
    :return:
    """
    full_path = img_path / print_request.image_path
    assert full_path.exists(), f"Image {full_path} does not exist"
    assert img_path in full_path.parents, f"Image {full_path} is not in {img_path}"

    return PrinterService.print_image(
        image_path=full_path,
        request=print_request,
        border=75,
    )


@backend_router.get("/available_layouts")
def available_layouts() -> List[Layout]:
    """
    Retrieve available layouts
    :return:
    """
    return LayoutEngine.available_layouts()


@backend_router.get("/layout/image/{filename}")
def get_layout_image(filename: str):
    """
    Resolve and download a layout image
    :param filename:
    :return:
    """
    return FileResponse(LayoutEngine.get_image(filename))


@backend_router.post("/layout")
def set_layout(layout: Layout) -> bool:
    """
    Update the active layout
    :param layout:
    :return:
    """
    LayoutEngine.set_layout(layout)
    return True


@backend_router.post("/layout/render")
def render_layout(image_names: List[str]) -> SnapshotResponse:
    """
    Given a list of image names, render the layout
    :param image_names:
    :return:
    """
    return LayoutEngine.render_layout(image_names)


app.mount("/api", backend_router)

ui_path = root_path / "booth-ui"
app.mount("/", StaticFiles(directory=ui_path / "dist" / "photo-booth-ui" / "browser", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
