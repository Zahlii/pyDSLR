"""
Base interface for configurations
"""

import datetime
from abc import ABC, abstractmethod
from typing import Optional

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
