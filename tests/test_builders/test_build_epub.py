"""Test the HTML builder and check output against XPath."""

import os
import subprocess
from subprocess import CalledProcessError

import pytest


# check given command is runnable
def runnable(command):
    try:
        subprocess.run(command, capture_output=True, check=True)
        return True
    except (OSError, CalledProcessError):
        return False  # command not found or exit with non-zero


@pytest.mark.skipif('DO_EPUBCHECK' not in os.environ,
                    reason='Skipped because DO_EPUBCHECK is not set')
@pytest.mark.sphinx('epub')
def test_run_epubcheck(app):
    app.build()

    if not runnable(['java', '-version']):
        pytest.skip("Unable to run Java; skipping test")

    epubcheck = os.environ.get('EPUBCHECK_PATH', '/usr/share/java/epubcheck.jar')
    if not os.path.exists(epubcheck):
        pytest.skip("Could not find epubcheck; skipping test")

    try:
        subprocess.run(['java', '-jar', epubcheck, app.outdir / 'SphinxTests.epub'],
                       capture_output=True, check=True)
    except CalledProcessError as exc:
        print(exc.stdout.decode('utf-8'))
        print(exc.stderr.decode('utf-8'))
        msg = f'epubcheck exited with return code {exc.returncode}'
        raise AssertionError(msg) from exc
