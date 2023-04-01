"""The Sphinx documentation toolchain."""

# Keep this file executable as-is in Python 3!
# (Otherwise getting the version out of it when packaging is impossible.)

from os import path

__version__ = '6.2.0'
__display_version__ = __version__  # used for command line version

#: Version info for better programmatic use.
#:
#: A tuple of five elements; for Sphinx version 1.2.1 beta 3 this would be
#: ``(1, 2, 1, 'beta', 3)``. The fourth element can be one of: ``alpha``,
#: ``beta``, ``rc``, ``final``. ``final`` always has 0 as the last element.
#:
#: .. versionadded:: 1.2
#:    Before version 1.2, check the string ``sphinx.__version__``.
version_info = (6, 2, 0, 'beta', 0)

package_dir = path.abspath(path.dirname(__file__))

_in_development = False
if _in_development:
    # Only import subprocess if needed
    import subprocess

    try:
        ret = subprocess.run(
            ['git', 'show', '-s', '--pretty=format:%h'],
            cwd=package_dir,
            capture_output=True,
            encoding='ascii',
        ).stdout
        if ret:
            __display_version__ += '+/' + ret.strip()
        del ret
    finally:
        del subprocess
del _in_development
