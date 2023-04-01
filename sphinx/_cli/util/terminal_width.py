"""Format colored console output."""

from __future__ import annotations

import sys


def get_terminal_width() -> int:
    """Return the width of the terminal in columns."""
    import os

    try:
        columns = int(os.environ.get('COLUMNS', 0))
    except ValueError:
        columns = 0
    if columns > 1:
        return columns - 1
    try:
        return os.get_terminal_size(sys.__stdout__.fileno()).columns - 1
    except (AttributeError, ValueError, OSError):
        # fallback
        return 80 - 1


_tw: int = get_terminal_width()


def term_width_line(formatted_text: str, raw_text: str) -> str:
    if formatted_text == raw_text:
        # if no coloring, don't output fancy backspaces
        return formatted_text + '\n'
    else:
        # codes are not displayed, this must be taken into account
        return formatted_text.ljust(_tw + len(formatted_text) - len(raw_text)) + '\r'
