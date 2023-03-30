"""Format colored console output."""

from __future__ import annotations

import re
import shutil

_ansi_re: re.Pattern = re.compile('\x1b\\[(\\d\\d;){0,2}\\d\\dm')


def get_terminal_width() -> int:
    """Return the width of the terminal in columns."""
    return shutil.get_terminal_size().columns - 1


_tw: int = get_terminal_width()


def term_width_line(text: str) -> str:
    if not codes:
        # if no coloring, don't output fancy backspaces
        return text + '\n'
    else:
        # codes are not displayed, this must be taken into account
        return text.ljust(_tw + len(text) - len(_ansi_re.sub('', text))) + '\r'
