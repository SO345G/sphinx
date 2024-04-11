"""Test the HTML builder and check output against XPath."""
import shutil
import subprocess


def test_run_epubcheck(make_app, rootdir, tmp_path):
    srcdir = tmp_path / 'root'
    shutil.copytree(rootdir / 'test-root', srcdir)
    app_ = make_app(
        'epub',
        srcdir=srcdir,
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
