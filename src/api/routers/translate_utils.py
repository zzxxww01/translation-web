"""
Translate router shared helpers.
"""

import re


def validate_path_component(value: str) -> bool:
    """
    Validate path component and block traversal.

    Only allow letters, numbers, underscore and hyphen.
    """
    return bool(re.match(r"^[\w\-]+$", value))
