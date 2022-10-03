from __future__ import annotations

import re

# Generally useful regular expressions.
WHITESPACE_RE: re.Pattern[str] = re.compile(r'\s+')
URL_RE: re.Pattern[str] = re.compile(r'(?P<schema>.+)://.*')
