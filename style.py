#!/usr/bin/env python
# -*- coding= utf-8 -*-

"""UI stylesheet, HEX colors and others.

Example:
    >>> import style
    >>> colors = style.load_colors_from_jsonc()
    >>> houdini_orange = colors["houdini"]["main"]
    '#3cc0fd'
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


def _remove_comments(text):
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


def load_colors_from_jsonc(jsonc_file=COLORS_FILE):
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
    stylesheet, colors_dict=load_colors_from_jsonc(COLORS_FILE), prefix=""
):
    placeholders = {
        f"@{prefix}{key}": value
        for key, value in colors_dict.items()
        if not isinstance(value, dict)
    }
    for placeholder, color in placeholders.items():
        stylesheet = stylesheet.replace(placeholder, color)
    return stylesheet


def _invert_color(hex_color):
    """Invert a hex color value by subtracting each RGB component from 255."""
    rgb_values = [255 - int(hex_color[i : i + 2], 16) for i in (1, 3, 5)]
    inverted_color = "#{:02X}{:02X}{:02X}".format(*rgb_values)
    return inverted_color


def _invert_icons(stylesheet):
    replacements = {
        "_light.png": "_dark.png",
        "_lighter.png": "_darker.png",
    }

    for old_string, new_string in replacements.items():
        stylesheet = stylesheet.replace(old_string, new_string)

    return stylesheet


def load_stylesheet(light_theme=False):
    """Load and process the stylesheet.

    This function loads a stylesheet from a `style.qss` file and applies color
    replacements based on the definitions in `style.jsonc` file. It also
    replaces certain placeholders with their corresponding values.

    Returns:
        str: The processed stylesheet content.
    """

    if not os.path.exists(STYLE_FILE):
        return None

    if not os.path.exists(COLORS_FILE):
        return None

    with open(STYLE_FILE, "r") as in_file:
        stylesheet = in_file.read()

    colors_dict = load_colors_from_jsonc(COLORS_FILE)

    if light_theme:
        # Invert colors for dark theme
        for key, value in colors_dict.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str) and sub_value.startswith("#"):
                        inverted_color = _invert_color(sub_value)
                        value[sub_key] = inverted_color
            elif isinstance(value, str) and value.startswith("#"):
                inverted_color = _invert_color(value)
                colors_dict[key] = inverted_color
        # Invert icons
        stylesheet = _invert_icons(stylesheet)

    # Perform color replacements
    stylesheet = replace_colors(stylesheet, colors_dict)

    # Replace icons path
    stylesheet = stylesheet.replace(
        "qss:", os.path.dirname(__file__).replace("\\", "/") + "/"
    )

    return stylesheet
