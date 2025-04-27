"""
Quick EXIF tools
"""

import logging
from pathlib import Path

from pydantic import BaseModel

try:
    import exiftool  # type: ignore

    e_tool = exiftool.ExifToolHelper()
except (ModuleNotFoundError, FileNotFoundError) as exc:
    logging.warning("ExifTool not found, not reporting any exif information: %s", exc)
    e_tool = None


class ExifInfo(BaseModel):
    iso: int | None = None
    fstop: str | None = None
    exposure_time: str | None = None
    width: int
    height: int


def get_exif(path: Path) -> ExifInfo | None:
    """
    Return the key EXIF infos for a freshly taken picture
    :param path:
    :return:
    """
    if e_tool is None:
        return None

    meta = e_tool.get_metadata([path])[0]

    def get_field(k: str):
        return meta.get(k, None)

    return ExifInfo(
        iso=get_field("EXIF:ISO"),
        fstop=get_field("EXIF:FNumber"),
        exposure_time=get_field("EXIF:ExposureTime"),
        width=get_field("File:ImageWidth"),
        height=get_field("File:ImageHeight"),
    )
