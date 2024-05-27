"""
Example script to capture multiple images at once
"""

from datetime import timedelta
from pathlib import Path

from pydslr import Camera
from pydslr.config.r6m2 import CaptureSettings, ImageSettings, R6M2Config, Settings

if __name__ == "__main__":
    OUT_FOLDER = Path(__file__).parent / "out"
    OUT_FOLDER.mkdir(exist_ok=True)

    with Camera[R6M2Config]() as c:
        with c.config_context(
            R6M2Config(
                imgsettings=ImageSettings(iso="3200", imageformat="cRAW"),
                settings=Settings(capturetarget="Memory card"),
                capturesettings=CaptureSettings(
                    aperture="4",
                    shutterspeed="auto",
                    autoexposuremodedial="AV",
                    exposurecompensation="0",
                    drivemode="Continuous low speed",
                ),
            )
        ):
            c.highspeed_capture(shutter_press_time=timedelta(seconds=1), keep_on_camera=False)
