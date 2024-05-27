"""
Helper functions
"""

import enum
import logging
import os
import string
import time
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydslr.tools.camera import Camera


def timed(f):
    """

    :param f:
    :return:
    """

    @wraps(f)
    def wrap(*args, **kw):
        ts = time.perf_counter()
        result = f(*args, **kw)
        te = time.perf_counter()
        logging.info("%s took: %2.4f sec", f.__name__, te - ts)
        return result

    return wrap


class GPWidgetItem(enum.IntEnum):
    """
    GP Widget State Enum
    """

    GP_WIDGET_BUTTON = 7
    GP_WIDGET_DATE = 8
    GP_WIDGET_MENU = 6
    GP_WIDGET_RADIO = 5
    GP_WIDGET_RANGE = 3
    GP_WIDGET_SECTION = 1
    GP_WIDGET_TEXT = 2
    GP_WIDGET_TOGGLE = 4
    GP_WIDGET_WINDOW = 0

    def get_value_type(self):
        """
        Return the data type returned by various widget types
        :return:
        """
        try:
            return {
                self.GP_WIDGET_DATE: int,
                self.GP_WIDGET_TEXT: str,
                self.GP_WIDGET_TOGGLE: int,
                self.GP_WIDGET_RADIO: str,
            }[self]
        except KeyError:
            return None


def generate_pydantic_config(camera: "Camera", file_name: str, class_prefix: str):
    """
    Generate a new config file
    :param camera:
    :param file_name:
    :param class_prefix:
    :return:
    """
    config_nodes = [
        [
            "# pylint: skip-file",
            "from typing import Literal, Optional",
            "from pydantic import BaseModel",
            "from pydslr.config.base import BaseConfig",
        ]
    ]
    tree = camera.get_json_config()

    def _handle(node, depth=0):
        current_node = []

        if "children" in node:
            name = node["name"]
            if depth > 0:
                current_node.append(f"class P_{name}(BaseModel):")
            else:
                current_node.append(f"class {class_prefix}Config(BaseConfig):")
            for child_node in node["children"]:
                if child_node["name"][0] in string.digits:
                    continue
                _handle(child_node, depth=depth + 1)

                if child_node["value_type"] is None:
                    current_node.append(f"\t{child_node['name']}: Optional[P_{child_node['name']}] = None")
                else:
                    # if child_node["value_type"] == str:
                    #     default_value = f"'{child_node['value'].encode('unicode_escape').decode('utf8')}'"
                    # else:
                    #     default_value = child_node["value"]

                    if "options" in child_node and child_node["options"]:
                        ov = "', '".join(child_node["options"])
                        type_val = f"Literal['{ov}']"
                    else:
                        type_val = child_node["value_type"].__name__
                    current_node.append(f"\t{child_node['name']}: Optional[{type_val}] = None")

        if current_node:
            config_nodes.append(current_node)

    _handle(tree)

    target_path = Path(__file__).parent / "config" / file_name
    with target_path.open("w", encoding="utf-8") as f:
        for cfg in config_nodes:
            f.write("\n".join(cfg))
            f.write("\n")

    os.system(f"black {target_path}")
