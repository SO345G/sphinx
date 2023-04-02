"""Format colored console output."""

from __future__ import annotations

import os
import sys

if sys.platform == 'win32':
    import colorama

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Callable

_COLOURING_DISABLED = False


def color_terminal() -> bool:
    """Return True if coloured terminal output is supported."""
    if 'NO_COLOR' in os.environ:
        return False
    if 'FORCE_COLOR' in os.environ:
        return True
    try:
        if not sys.stdout.isatty():
            return False
    except (AttributeError, ValueError):
        # Handle cases where .isatty() is not defined, or where e.g.
        # "ValueError: I/O operation on closed file" is raised
        return False
    if os.environ.get("TERM", "").lower() in {"dumb", "unknown"}:
        # Do not colour output if on a dumb terminal
        return False
    if sys.platform == 'win32':
        colorama.init()
    return True


def nocolor() -> None:
    global _COLOURING_DISABLED
    _COLOURING_DISABLED = True
    if sys.platform == 'win32':
        colorama.deinit()


def coloron() -> None:
    global _COLOURING_DISABLED
    _COLOURING_DISABLED = False
    if sys.platform == 'win32':
        colorama.init()


def colorize(name: str, text: str, input_mode: bool = False) -> str:
    if _COLOURING_DISABLED:
        return text

    if sys.platform == 'win32' or not input_mode:
        return globals()[name](text)

    # Wrap escape sequence with ``\1`` and ``\2`` to let readline know
    # it is non-printable characters
    # ref: https://tiswww.case.edu/php/chet/readline/readline.html
    #
    # Note: This does not work well in Windows (see
    # https://github.com/sphinx-doc/sphinx/pull/5059)
    escape_code = getattr(globals()[name], '__escape_code', '39;49;00')
    return f'\1\x1b[{escape_code}m\2{text}\1\x1b[39;49;00m\2'


def _create_colour_func(
    __escape_code: str,
) -> Callable[[str], str]:
    def inner(text: str) -> str:
        if _COLOURING_DISABLED:
            return text
        return f'\x1b[{__escape_code}m{text}\x1b[39;49;00m'
    # private attribute, only for ``colorize()``
    inner.__escape_code = __escape_code
    return inner


reset = _create_colour_func('39;49;00')
bold = _create_colour_func('01')
# faint = _create_colour_func('02')
# standout = _create_colour_func('03')
# underline = _create_colour_func('04')
# blink = _create_colour_func('05')

black = _create_colour_func('30')
darkgray = _create_colour_func('90')
darkred = _create_colour_func('31')
red = _create_colour_func('91')
darkgreen = _create_colour_func('32')
green = _create_colour_func('92')
brown = _create_colour_func('33')
yellow = _create_colour_func('93')
darkblue = _create_colour_func('34')
blue = _create_colour_func('94')
purple = _create_colour_func('35')
fuchsia = _create_colour_func('95')
turquoise = _create_colour_func('36')
teal = _create_colour_func('96')
lightgray = _create_colour_func('37')
white = _create_colour_func('97')
