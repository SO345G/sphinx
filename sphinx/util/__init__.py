"""Utility functions for Sphinx."""

from __future__ import annotations

import hashlib
import os
import posixpath
import re
from importlib import import_module
from os import path
from typing import IO, Any, Iterable
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

from sphinx.errors import ExtensionError, FiletypeNotFoundError
from sphinx.locale import __
from sphinx.util import display as _display
from sphinx.util import exceptions as _exceptions
from sphinx.util import http_date as _http_date
from sphinx.util import index_entries as _index_entries
from sphinx.util import logging
from sphinx.util import osutil as _osutil
from sphinx.util.console import strip_colors  # NoQA: F401
from sphinx.util.matching import patfilter  # noqa: F401
from sphinx.util.nodes import (  # noqa: F401
    caption_ref_re,
    explicit_title_re,
    nested_parse_with_titles,
    split_explicit_title,
)

# import other utilities; partly for backwards compatibility, so don't
# prune unused ones indiscriminately
from sphinx.util.osutil import (  # noqa: F401
    SEP,
    copyfile,
    copytimes,
    ensuredir,
    make_filename,
    mtimes_of_files,
    os_path,
    relative_uri,
)

logger = logging.getLogger(__name__)

# High-level utility functions.

def docname_join(basedocname: str, docname: str) -> str:
    return posixpath.normpath(posixpath.join('/' + basedocname, '..', docname))[1:]


def get_filetype(source_suffix: dict[str, str], filename: str) -> str:
    for suffix, filetype in source_suffix.items():
        if filename.endswith(suffix):
            # If default filetype (None), considered as restructuredtext.
            return filetype or 'restructuredtext'
    raise FiletypeNotFoundError


def _md5(data=b'', **_kw):
    """Deprecated wrapper around hashlib.md5

    To be removed in Sphinx 9.0
    """
    return hashlib.md5(data, usedforsecurity=False)


def _sha1(data=b'', **_kw):
    """Deprecated wrapper around hashlib.sha1

    To be removed in Sphinx 9.0
    """
    return hashlib.sha1(data, usedforsecurity=False)


class UnicodeDecodeErrorHandler:
    """Custom error handler for open() that warns and replaces."""

    def __init__(self, docname: str) -> None:
        self.docname = docname

    def __call__(self, error: UnicodeDecodeError) -> tuple[str, int]:
        linestart = error.object.rfind(b'\n', 0, error.start)
        lineend = error.object.find(b'\n', error.start)
        if lineend == -1:
            lineend = len(error.object)
        lineno = error.object.count(b'\n', 0, error.start) + 1
        logger.warning(__('undecodable source characters, replacing with "?": %r'),
                       (error.object[linestart + 1:error.start] + b'>>>' +
                        error.object[error.start:error.end] + b'<<<' +
                        error.object[error.end:lineend]),
                       location=(self.docname, lineno))
        return ('?', error.end)


# Low-level utility functions and classes.

def _xml_name_checker():
    # to prevent import cycles
    from sphinx.builders.epub3 import _XML_NAME_PATTERN

    return _XML_NAME_PATTERN


# deprecated name -> (object to return, canonical path or empty string)
_DEPRECATED_OBJECTS = {
    'path_stabilize': (_osutil.path_stabilize, 'sphinx.util.osutil.path_stabilize'),
    'display_chunk': (_display.display_chunk, 'sphinx.util.display.display_chunk'),
    'status_iterator': (_display.status_iterator, 'sphinx.util.display.status_iterator'),
    'SkipProgressMessage': (_display.SkipProgressMessage,
                            'sphinx.util.display.SkipProgressMessage'),
    'progress_message': (_display.progress_message, 'sphinx.http_date.epoch_to_rfc1123'),
    'epoch_to_rfc1123': (_http_date.epoch_to_rfc1123, 'sphinx.http_date.rfc1123_to_epoch'),
    'rfc1123_to_epoch': (_http_date.rfc1123_to_epoch, 'sphinx.http_date.rfc1123_to_epoch'),
    'save_traceback': (_exceptions.save_traceback, 'sphinx.exceptions.save_traceback'),
    'format_exception_cut_frames': (_exceptions.format_exception_cut_frames,
                                    'sphinx.exceptions.format_exception_cut_frames'),
    'xmlname_checker': (_xml_name_checker, 'sphinx.builders.epub3._XML_NAME_PATTERN'),
    'split_index_msg': (_index_entries.split_index_msg,
                        'sphinx.util.index_entries.split_index_msg'),
    'split_into': (_index_entries.split_index_msg, 'sphinx.util.index_entries.split_into'),
    'md5': (_md5, ''),
    'sha1': (_sha1, ''),
}


def __getattr__(name):
    if name not in _DEPRECATED_OBJECTS:
        msg = f'module {__name__!r} has no attribute {name!r}'
        raise AttributeError(msg)

    from sphinx.deprecation import _deprecation_warning

    deprecated_object, canonical_name = _DEPRECATED_OBJECTS[name]
    _deprecation_warning(__name__, name, canonical_name, remove=(8, 0))
    return deprecated_object
