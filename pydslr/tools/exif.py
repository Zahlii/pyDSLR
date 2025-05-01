"""
Quick EXIF tools
"""

import logging
from pathlib import Path
from typing import Type

from pydantic import BaseModel

try:
    import exiftool  # type: ignore

    e_tool = exiftool.ExifToolHelper()
except (ModuleNotFoundError, FileNotFoundError) as exc:
    logging.warning("ExifTool not found, not reporting any exif information: %s", exc)
    e_tool = None


class ExifInfo(BaseModel):
    iso: int | None = None
    fstop: float | None = None
    exposure_time: float | None = None
    width: int
    height: int


def get_exif(path: Path | str) -> ExifInfo | None:
    """
    Return the key EXIF infos for a freshly taken picture
    :param path:
    :return:
    """
    if e_tool is None:
        return None

    meta = e_tool.get_metadata([path])[0]

    def get_field(*keys: str, default=None, cls: Type = str):
        for k in keys:
            val = meta.get(k, None)
            if val is not None:
                return cls(val)
        return default

    return ExifInfo(
        iso=get_field("EXIF:ISO", cls=int),
        fstop=get_field("EXIF:FNumber", cls=float),
        exposure_time=get_field("EXIF:ExposureTime", cls=float),
        width=get_field("File:ImageWidth", "EXIF:ImageWidth", cls=int),
        height=get_field("File:ImageHeight", "EXIF:ImageHeight", cls=int),
    )
