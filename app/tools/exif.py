from pathlib import Path

import exiftool

e_tool = exiftool.ExifToolHelper()


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
    return {k: e_tool.get_metadata([path])[0].get(k, None) for k in return_values}
