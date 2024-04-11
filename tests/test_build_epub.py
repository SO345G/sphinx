"""Test the HTML builder and check output against XPath."""
import shutil
import subprocess
from pathlib import Path

from sphinx.testing.util import SphinxTestApp

TEST_ROOTS = Path(__file__).resolve().parent / 'roots' / 'test-root'


def test_run_epubcheck(tmp_path):
    shutil.copytree(TEST_ROOTS, tmp_path / 'root')
    app_ = SphinxTestApp(
        'epub',
        srcdir=tmp_path / 'root',
    )
    app_.build()

    try:
        subprocess.run(
            ('java', '-jar', '/usr/share/java/epubcheck.jar', app_.outdir / 'SphinxTests.epub'),
            check=True
        )
    except subprocess.CalledProcessError as exc:
        msg = f'epubcheck exited with return code {exc.returncode}'
        raise AssertionError(msg) from exc
