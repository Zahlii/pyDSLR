"""
Using the live view image, triggers a capture when sudden brightness increase is noticed.
"""

from datetime import timedelta
from pathlib import Path

import numpy as np

from pydslr import Camera
from pydslr.config.r6m2 import CaptureSettings, ImageSettings, R6M2Config

if __name__ == "__main__":
    OUT_FOLDER = Path(__file__).parent / "out"
    OUT_FOLDER.mkdir(exist_ok=True)

    QUEUE_SIZE = 10
    THRESHOLD = 20

    with Camera[R6M2Config]() as c:
        # set to low-ISO, f5.6 for sharpness & longer exposure, Av mode with auto shutter speed
        # we also set -1 EV to preserve lightning strike highlights
        with c.config_context(
            R6M2Config(
                imgsettings=ImageSettings(iso="100", imageformat="cRAW"),
                capturesettings=CaptureSettings(aperture="5.6", shutterspeed="bulb", autoexposuremode="AV", exposurecompensation="-1"),
            )
        ):
            IMG_TENSOR = None
            ACTIVE = False
            for j, img in enumerate(c.stream_preview(as_numpy=True, max_time=timedelta(minutes=1))):
                if IMG_TENSOR is None:
                    IMG_TENSOR = np.zeros((QUEUE_SIZE, img.shape[0], img.shape[1])) + np.nan
                else:
                    IMG_TENSOR[1:] = IMG_TENSOR[0:-1]
                mean_img = img.mean(axis=-1)
                IMG_TENSOR[0] = mean_img

                delta = (np.nanmean(IMG_TENSOR, axis=0) - IMG_TENSOR[0]).mean()
                if delta < -1 * THRESHOLD and not ACTIVE:
                    ACTIVE = True
                    c.capture(OUT_FOLDER / f"img_{j}.cr3")
                elif delta > THRESHOLD and ACTIVE:
                    ACTIVE = False
