from __future__ import annotations

from sphinx.locale import _

ADMONITION_TYPES = frozenset({
    'attention',
    'caution',
    'danger',
    'error',
    'hint',
    'important',
    'note',
    'seealso',
    'tip',
    'warning',
})


def translated_label(label_name: str, /) -> str:
    try:
        return {
            'attention': _('Attention'),
            'caution': _('Caution'),
            'danger': _('Danger'),
            'error': _('Error'),
            'hint': _('Hint'),
            'important': _('Important'),
            'note': _('Note'),
            'seealso': _('See also'),
            'tip': _('Tip'),
            'warning': _('Warning'),
        }[label_name]
    except KeyError:
        raise ValueError(f'Unsupported admonition type {label_name!r}! '
                         f'Supported types are: {sorted(ADMONITION_TYPES)}')
