#!/usr/bin/env python
# -*- coding= utf-8 -*-

"""UI stylesheet, HEX colors and others.

Examples:
    >>> import style
    >>> colors = style.load_colors_from_jsonc()
    >>> houdini_orange = colors["houdini"]["main"]
    #3cc0fd
"""

# Built-in
import os
import re
import json

# Metadatas
__author__ = "Valentin Beaumont"
__email__ = "valentin.onze@gmail.com"


###### CODE ####################################################################


STYLE_FILE = os.path.join(os.path.dirname(__file__), "qss", "style.qss")
COLORS_FILE = os.path.join(os.path.dirname(__file__), "style.jsonc")


def _remove_comments(text: str) -> str:
    """Remove single-line and multi-line comments from the input text.

    Args:
        text (str): The input text containing comments.

    Returns:
        str: The input text with comments removed.
    """

    # Regular expression to remove single-line and multi-line comments
    pattern = r"(\"(?:\\\"|.)*?\"|\'.*?\'|//.*?$|/\*.*?\*/)"
    return re.sub(
        pattern,
        lambda m: "" if m.group(0).startswith("/") else m.group(0),
        text,
        flags=re.DOTALL | re.MULTILINE,
    )


def load_colors_from_jsonc(jsonc_file: str = COLORS_FILE) -> dict:
    """Load colors from a JSONC (JSON with comments) file.

    Args:
        jsonc_file (str): The path to the JSONC file. Defaults to `COLORS_FILE`.

    Returns:
        dict: A dictionary containing color definitions.
    """

    with open(jsonc_file, "r") as f:
        jsonc_content = f.read()
        json_content = _remove_comments(jsonc_content)
        return json.loads(json_content)


def replace_colors(
    stylesheet: str,
    colors_dict: dict = load_colors_from_jsonc(COLORS_FILE),
    prefix="",
) -> str:
    """_summary_

    Args:
        stylesheet (str): The stylesheet to replace the colors in.
        colors_dict (dict, optional): The dict to use to search for colors to be
            replaced. Defaults to `load_colors_from_jsonc(COLORS_FILE)`.
        prefix (str, optional): The identifier prefix for colors to be replaced.
            Defaults to `""`.

    Returns:
        str: The stylesheet with replaced colors.
    """

    placeholders = {f"@{prefix}{key}": value for key, value in colors_dict.items() if not isinstance(value, dict)}
    for placeholder, color in placeholders.items():
        stylesheet = stylesheet.replace(placeholder, color)
    return stylesheet
