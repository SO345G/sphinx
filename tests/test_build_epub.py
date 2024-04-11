"""Test the HTML builder and check output against XPath."""

import os
import subprocess

import pytest


@pytest.mark.sphinx('epub')
def test_run_epubcheck(app):
    app.build()

    epubcheck = os.environ.get('EPUBCHECK_PATH', '/usr/share/java/epubcheck.jar')
    if not os.path.exists(epubcheck):
        pytest.skip("Could not find epubcheck; skipping test")

    try:
        subprocess.run(['java', '-jar', epubcheck, app.outdir / 'SphinxTests.epub'],
                       check=True)
    except subprocess.CalledProcessError as exc:
        msg = f'epubcheck exited with return code {exc.returncode}'
        raise AssertionError(msg) from exc
