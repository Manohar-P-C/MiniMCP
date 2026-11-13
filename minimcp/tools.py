"""Built-in tools registered on the application registry.

All tools avoid filesystem access, arbitrary code execution, shell execution,
and unrestricted network access. The URL validator inspects structure only.
"""

import datetime
import json
import re
from urllib.parse import urlparse

from .registry import Registry

registry = Registry()


# --------------------------------------------------------------------------- #
# Calculator
# --------------------------------------------------------------------------- #
@registry.tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@registry.tool
def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b


@registry.tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b


@registry.tool
def divide(a: float, b: float) -> float:
    """Divide a by b. Raises an error on division by zero."""
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


# --------------------------------------------------------------------------- #
# Text analyzer
# --------------------------------------------------------------------------- #
@registry.tool
def word_count(text: str) -> int:
    """Count the number of words in the given text."""
    return len(text.split())


@registry.tool
def char_count(text: str) -> int:
    """Count the number of characters in the given text."""
    return len(text)


@registry.tool
def char_count_no_spaces(text: str) -> int:
    """Count characters excluding spaces."""
    return len(text.replace(" ", ""))


# --------------------------------------------------------------------------- #
# URL validator
# --------------------------------------------------------------------------- #
@registry.tool
def validate_url(url: str) -> dict:
    """Validate the structure of an HTTP/HTTPS URL. No network request is made."""
    parsed = urlparse(url)
    valid = parsed.scheme in ("http", "https") and bool(parsed.netloc)
    return {
        "valid": valid,
        "url": url,
        "scheme": parsed.scheme,
        "host": parsed.hostname,
        "path": parsed.path,
    }


# --------------------------------------------------------------------------- #
# Date and time
# --------------------------------------------------------------------------- #
@registry.tool
def current_utc_time(format: str = "iso") -> str:
    """Return the current UTC time in ISO 8601 format."""
    now = datetime.datetime.now(datetime.timezone.utc)
    if format == "iso":
        return now.isoformat()
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")


# --------------------------------------------------------------------------- #
# String utility
# --------------------------------------------------------------------------- #
@registry.tool
def reverse_text(text: str) -> str:
    """Reverse the given text."""
    return text[::-1]


@registry.tool
def uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()


@registry.tool
def lowercase(text: str) -> str:
    """Convert text to lowercase."""
    return text.lower()


# --------------------------------------------------------------------------- #
# JSON utility
# --------------------------------------------------------------------------- #
@registry.tool
def parse_json(json_text: str) -> dict:
    """Parse a JSON string and return structured validation errors on failure."""
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as exc:
        return {
            "valid": False,
            "error": "Invalid JSON",
            "message": str(exc),
            "line": exc.lineno,
            "column": exc.colno,
        }
