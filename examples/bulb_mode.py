"""
Example script to capture multiple images at once
"""

from datetime import timedelta

from pydslr import Camera
from pydslr.config.r6m2 import CaptureSettings, ImageSettings, R6M2Config, Settings

if __name__ == "__main__":
    with Camera[R6M2Config]() as c:
        with c.config_context(
            R6M2Config(
                imgsettings=ImageSettings(iso="100", imageformat="cRAW"),
                settings=Settings(capturetarget="Memory card"),
                capturesettings=CaptureSettings(
                    aperture="22",
                    shutterspeed="bulb",
                    autoexposuremodedial="Bulb",
                    exposurecompensation="0",
                    drivemode="Single",
                ),
            )
        ):
            c.bulb_capture(shutter_press_time=timedelta(seconds=0.5), keep_on_camera=False)
