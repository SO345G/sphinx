"""Test the HTML builder and check output against XPath."""
import shutil
import subprocess


def test_run_epubcheck(make_app, rootdir, sphinx_test_tempdir):
    kwargs = {}

    # ##### prepare Application params

    testroot = kwargs.pop('testroot', 'root')
    kwargs['srcdir'] = srcdir = sphinx_test_tempdir / kwargs.get('srcdir', testroot)

    # special support for sphinx/tests
    if rootdir and not srcdir.exists():
        testroot_path = rootdir / ('test-' + testroot)
        shutil.copytree(testroot_path, srcdir)
    app_ = make_app(
        'epub',
        **kwargs,
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
