import os.path, sys

sys.path.append(os.path.abspath('./demo/'))

project = 'Sphinx Themes QA Testing'
slug = 'sphinx-themes-qa-testing'
version = '1.0.0'
author = 'The Author'
copyright = 'Copyright, 1901--Present'
language = 'en'

extensions = [
    'sphinx.ext.intersphinx',
    'sphinx.ext.autodoc',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinxcontrib.httpdomain',
]

source_suffix = '.rst'
exclude_patterns = []
gettext_compact = False

master_doc = 'index'
suppress_warnings = ['image.nonlocal_uri']
pygments_style = 'default'

intersphinx_mapping = {
    'rtd': ('https://docs.readthedocs.io/en/stable/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

html_theme_options = {
    'logo_only': True,
    'navigation_depth': 5,
}
html_context = {}

html_logo = "demo/static/logo-wordmark-light.svg"
html_show_sourcelink = True
