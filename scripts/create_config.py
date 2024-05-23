"""
Helper to create new config files
"""
import argparse

from app.tools.camera import Camera
from app.utils import generate_pydantic_config

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a new config entry for your camera.")

    parser.add_argument("file_name", type=str, help="The name of the typed file to create, ideally linked to your camera name, without .py suffix.")
    parser.add_argument("--class_name", type=str, default=None, help="The optional class name prefix (e.g. R6M2). Defaults to file_name.upper()")

    args = parser.parse_args()

    with Camera() as c:
        generate_pydantic_config(
            c,
            file_name=args.file_name.rstrip(".py"),
            class_prefix=args.class_name or args.file_name.rstrip(".py").upper(),
        )
