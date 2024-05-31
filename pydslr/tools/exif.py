"""
Quick EXIF tools
"""
import logging
from pathlib import Path

try:
    import exiftool  # type: ignore

    e_tool = exiftool.ExifToolHelper()
except (ModuleNotFoundError, FileNotFoundError) as exc:
    logging.warning("ExifTool not found, not reporting any exif information.")
    e_tool = None


def get_exif(path: Path):
    """
    Return the key EXIF infos for a freshly taken picture
    :param path:
    :return:
    """
    return_values = [
        "EXIF:ISO",
        "EXIF:FNumber",
        "EXIF:ExposureTime",
        "EXIF:ImageWidth",
        "EXIF:ImageHeight",
    ]

    if e_tool is None:
        return None
    return {k: e_tool.get_metadata([path])[0].get(k, None) for k in return_values}
