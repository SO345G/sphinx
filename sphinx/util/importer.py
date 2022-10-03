from __future__ import annotations

from importlib import import_module
from typing import Any

from sphinx.errors import ExtensionError


def import_object(objname: str, source: str | None = None) -> Any:
    """Import python object by qualname."""
    try:
        objpath = objname.split('.')
        modname = objpath.pop(0)
        obj = import_module(modname)
        for name in objpath:
            modname += '.' + name
            try:
                obj = getattr(obj, name)
            except AttributeError:
                obj = import_module(modname)

        return obj
    except (AttributeError, ImportError) as exc:
        if source:
            msg = f'Could not import {objname} (needed for {source})'
            raise ExtensionError(msg, exc) from exc
        msg = f'Could not import {objname}'
        raise ExtensionError(msg, exc) from exc
