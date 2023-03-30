"""Format colored console output."""

from __future__ import annotations

import re


def terminal_safe(s: str) -> str:
    """Safely encode a string for printing to the terminal."""
    return s.encode('ascii', 'backslashreplace').decode('ascii')


def strip_colors(s: str) -> str:
    return re.compile('\x1b.*?m').sub('', s)
