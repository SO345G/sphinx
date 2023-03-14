from __future__ import annotations

import gettext
import os
import shutil

import docutils
import pytest

import sphinx
import sphinx.locale
from sphinx.testing import comparer
from sphinx.testing.path import path


def _locale_init(locale_dirs, language, catalog='sphinx', namespace='general'):
    """Monkeypatch ``sphinx.locale.init`` to skip its action.

    Some tests rely on warning messages in English. We don't want
    CLI tests to bleed over those tests and make their warnings
    translated.
    """
    translator = gettext.NullTranslations()
    sphinx.locale.translators[namespace, catalog] = translator
    return translator, False


sphinx.locale._original_init = sphinx.locale.init
sphinx.locale.init = _locale_init

pytest_plugins = 'sphinx.testing.fixtures'

# Exclude 'roots' dirs for pytest test collector
collect_ignore = ['roots']


@pytest.fixture(scope='session')
def rootdir():
    return path(__file__).parent.abspath() / 'roots'


def pytest_report_header(config):
    header = ("libraries: Sphinx-%s, docutils-%s" %
              (sphinx.__display_version__, docutils.__version__))
    if hasattr(config, '_tmp_path_factory'):
        header += "\nbase tempdir: %s" % config._tmp_path_factory.getbasetemp()

    return header


def pytest_assertrepr_compare(op, left, right):
    comparer.pytest_assertrepr_compare(op, left, right)


def _initialize_test_directory(session):
    if 'SPHINX_TEST_TEMPDIR' in os.environ:
        tempdir = os.path.abspath(os.getenv('SPHINX_TEST_TEMPDIR'))
        print('Temporary files will be placed in %s.' % tempdir)

        if os.path.exists(tempdir):
            shutil.rmtree(tempdir)

        os.makedirs(tempdir)


def pytest_sessionstart(session):
    _initialize_test_directory(session)
