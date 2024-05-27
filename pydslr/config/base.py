"""
Base interface for configurations
"""

import datetime
from abc import ABC, abstractmethod
from typing import Optional, Self

from pydantic import BaseModel


class BaseConfig(BaseModel, ABC):
    """
    Basic interface used by camera module
    """

    @abstractmethod
    def get_camera_time(self) -> Optional[datetime.datetime]:
        """
        Return timezone aware camera time

        :return:
        """

    @abstractmethod
    def is_raw(self) -> bool:
        """
        Return whether capture is set to raw format

        :return:
        """

    @abstractmethod
    def is_sdcard_capture_enabled(self):
        """
        Return whether sdcard capture is enabled (or internal memory is used)

        :return:
        """

    @abstractmethod
    def press_shutter(self) -> Self:
        """
        Return a config modified to press the shutter
        :return:
        """

    @abstractmethod
    def release_shutter(self) -> Self:
        """
        Return a config modified to press the shutter
        :return:
        """

    @abstractmethod
    def get_sd_root_folder(self) -> str:
        """
        Return the root folder to be used with gp_list_files to retrieve SD card contents
        :return:
        """
