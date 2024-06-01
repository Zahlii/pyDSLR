"""
Example script to capture multiple images at once
"""

from pydslr import Camera
from pydslr.config.r6m2 import R6M2Config

if __name__ == "__main__":
    with Camera[R6M2Config]() as c:
        c.focus_stack(n_images=5, distance=3)
