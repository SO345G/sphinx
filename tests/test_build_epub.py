"""Test the HTML builder and check output against XPath."""

import shutil
import subprocess

from sphinx.testing.util import SphinxTestApp


def test_run_epubcheck(tmp_path, rootdir):
    shutil.copytree((rootdir / 'test-root'), tmp_path)

    app = SphinxTestApp(
        'epub',
        srcdir=tmp_path,
    )
    app.build()

    try:
        subprocess.run(
            ('java', '-jar', '/usr/share/java/epubcheck.jar', app.outdir / 'SphinxTests.epub'),
            check=True
        )
    except subprocess.CalledProcessError as exc:
        msg = f'epubcheck exited with return code {exc.returncode}'
        raise AssertionError(msg) from exc
    finally:
        app.cleanup()
