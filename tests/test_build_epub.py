"""Test the HTML builder and check output against XPath."""
import shutil
from pathlib import Path

from sphinx.testing.util import SphinxTestApp

TEST_ROOTS = Path(__file__).resolve().parent / 'roots' / 'test-root'
TMP_PATH = Path(__file__).resolve().parent.parent / 'tmp'
TMP_PATH.mkdir(exist_ok=True)


def test_run_epubcheck(tmp_path):
    shutil.copytree(TEST_ROOTS, tmp_path / 'root')
    app_ = SphinxTestApp(
        'epub',
        srcdir=tmp_path / 'root',
    )
    app_.build(force_all=True)

    print(tmp_path / 'root/_build/epub/SphinxTests.epub')
