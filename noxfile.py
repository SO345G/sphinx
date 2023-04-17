from __future__ import annotations

import sys

import nox

PYTHON_VERSIONS = (
    '3.8',
    '3.9',
    '3.10',
    '3.11',
    # '3.12',
)
DOCUTILS_VERSIONS = (
    '0.18',
    '0.19',
    'HEAD',
    'default'
)
COMMON_ENV_VARS = {
    'FORCE_COLOR': '1',
    'PYTHONDEVMODE': '1',
    'PYTHONWARNDEFAULTENCODING': '1',
    'PYTHONWARNINGS': 'error,always:unclosed:ResourceWarning',
}

nox.needs_version = '>=2022.8.7'
nox.options.sessions = (
    "tests",
)
nox.options.reuse_existing_virtualenvs = True
nox.options.error_on_external_run = True

parametrise_docutils = nox.parametrize(
    'docutils',
    [nox.param(a, id=f'docutils-{a}') for a in DOCUTILS_VERSIONS],
)


@nox.session(python=PYTHON_VERSIONS)
@parametrise_docutils
def tests(session: nox.Session, docutils: str):
    """Run tests in a virtual environment."""
    _run_tests(session, 'python', docutils)


@nox.session(python=False, name='tests-ci')
@parametrise_docutils
def tests_current_python(session: nox.Session, docutils: str):
    """Run tests with the current Python."""
    _run_tests(session, sys.executable, docutils)


def _run_tests(session: nox.Session, python_executable: str, docutils: str):
    session.run(python_executable, '-m', 'pip', 'install', '.[test]')

    du_version = _get_docutils_version_specifier(docutils)
    if du_version:
        session.run(python_executable, '-m', 'pip', 'install', du_version)

    session.run(
        'python', '-m', 'pytest',
        '--durations=25',
        '--color=yes',
        '-vv',
        *session.posargs,
    )


def _get_docutils_version_specifier(docutils: str) -> str:
    if docutils == 'default':
        return ''
    if docutils == 'HEAD':
        return 'git+https://repo.or.cz/docutils.git#subdirectory=docutils'
    return f'docutils~={docutils}.0'


@nox.session()
def docs(session: nox.Session):
    """Build documentation."""
    session.install('.[docs]')
    session.run(
        'sphinx-build',
        '-M', 'html', './doc', './build/sphinx',
        '--jobs=auto',
        '-n',
        '-E',
        '-T',
        '-W', '--keep-going',
        env=COMMON_ENV_VARS,
    )


@nox.session(name='docs-live')
def docs_live(session: nox.Session):
    """Build documentation."""
    session.install('sphinx-autobuild')
    session.install('.[docs]')
    session.run(
        'sphinx-autobuild', './doc', './build/sphinx/',
        env=COMMON_ENV_VARS,
    )


@nox.session()
def bindep(session: nox.Session):
    """Install binary dependencies."""
    session.install('bindep')
    # session.install('.')
    session.run('bindep', 'test')
