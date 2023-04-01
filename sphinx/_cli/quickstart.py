"""Quickly setup documentation source to work with Sphinx."""

from __future__ import annotations

import sys
from os import path
from typing import TYPE_CHECKING

from sphinx.locale import __
from sphinx.util.console import bold, color_terminal, colorize, nocolor, red  # type: ignore
from sphinx.util.colour import bold, color_terminal, colorize, nocolor, red  # type: ignore
from sphinx.util.template import SphinxRenderer

if TYPE_CHECKING:
    import argparse
    from typing import Any, Callable

EXTENSIONS = {
    'autodoc': __('automatically insert docstrings from modules'),
    'doctest': __('automatically test code snippets in doctest blocks'),
    'intersphinx': __('link between Sphinx documentation of different projects'),
    'todo': __('write "todo" entries that can be shown or hidden on build'),
    'coverage': __('checks for documentation coverage'),
    'imgmath': __('include math, rendered as PNG or SVG images'),
    'mathjax': __('include math, rendered in the browser by MathJax'),
    'ifconfig': __('conditional inclusion of content based on config values'),
    'viewcode': __('include links to the source code of documented Python objects'),
    'githubpages': __('create .nojekyll file to publish the document on GitHub pages'),
}

DEFAULTS = {
    'path': '.',
    'sep': False,
    'dot': '_',
    'language': None,
    'suffix': '.rst',
    'master': 'index',
    'makefile': True,
    'batchfile': True,
}

USE_READLINE = False
PROMPT_PREFIX = '> '


# function to get input from terminal -- overridden by the test suite
def term_input(prompt: str) -> str:
    if sys.platform == 'win32':
        # Important: On windows, readline is not enabled by default.  In these
        #            environment, escape sequences have been broken.  To avoid the
        #            problem, quickstart uses ``print()`` to show prompt.
        print(prompt, end='')
        return input('')
    else:
        return input(prompt)


class ValidationError(Exception):
    """Raised for validation errors."""


def _check_readline():
    """Try to import readline, unix specific enhancement"""

    if sys.platform == "win32":
        return
    try:
        import readline
    except ImportError:
        return

    if readline.__doc__ and 'libedit' in readline.__doc__:
        # Note: libedit has a problem for combination of ``input()`` and escape
        # sequence (see #5335).  To avoid the problem, all prompts are not colored
        # on libedit.
        readline.parse_and_bind("bind ^I rl_complete")  # type: ignore
        return

    global USE_READLINE
    readline.parse_and_bind("tab: complete")  # type: ignore
    USE_READLINE = True


def is_path(x: str) -> str:
    x = path.expanduser(x)
    if path.isdir(x):
        return x
    raise ValidationError(__("Please enter a valid path name."))


def is_path_or_empty(x: str) -> str:
    if x == '':
        return x
    return is_path(x)


def allow_empty(x: str) -> str:
    return x


def nonempty(x: str) -> str:
    if x:
        return x
    raise ValidationError(__("Please enter some text."))


def choice(*l: str) -> Callable[[str], str]:
    choices = frozenset(l)
    choices_str = ', '.join(l)

    def validate(x: str) -> str:
        if x in choices:
            return x
        raise ValidationError(__('Please enter one of %s.') % choices_str)
    return validate


def boolean(x: str) -> bool:
    x = x.lower()
    if x in {'y', 'yes'}:
        return True
    if x in {'n', 'no'}:
        return False
    raise ValidationError(__("Please enter either 'y' or 'n'."))


def suffix(x: str) -> str:
    if len(x) > 1 and x[0] == '.':
        return x
    raise ValidationError(__("Please enter a file suffix, e.g. '.rst' or '.txt'."))


def do_prompt(
    text: str, default: str | None = None,
    validator: Callable[[str], Any] = nonempty,
) -> str | bool:
    while True:
        if default is not None:
            prompt = f'{text} [{default}]: '
        else:
            prompt = f'{text}: '
        prompt = colorize('teal', PROMPT_PREFIX + prompt, input_mode=USE_READLINE)
        x = term_input(prompt).strip()
        if default and not x:
            x = default
        try:
            x = validator(x)
        except ValidationError as err:
            print(red('* ' + str(err)))
            continue
        break
    return x


class QuickstartRenderer(SphinxRenderer):
    def __init__(self, templatedir: str = '') -> None:
        self.templatedir = templatedir or ''
        super().__init__()

    def _has_custom_template(self, template_name: str) -> bool:
        """Check if custom template file exists.

        Note: Please don't use this function from extensions.
              It will be removed in the future without deprecation period.
        """
        template = path.join(self.templatedir, path.basename(template_name))
        return bool(self.templatedir) and path.exists(template)

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        if self._has_custom_template(template_name):
            custom_template = path.join(self.templatedir, path.basename(template_name))
            return self.render_from_file(custom_template, context)
        else:
            return super().render(template_name, context)


def ask_user(d: dict[str, Any]) -> None:
    """Ask the user for quickstart values missing from *d*.

    Values are:

    * path:      root path
    * sep:       separate source and build dirs (bool)
    * dot:       replacement for dot in _templates etc.
    * project:   project name
    * author:    author names
    * version:   version of project
    * release:   release of project
    * language:  document language
    * suffix:    source file suffix
    * master:    master document name
    * extensions:  extensions to use (list)
    * makefile:  make Makefile
    * batchfile: make command file
    """
    from sphinx import __display_version__

    # potentially import and set up readline
    _check_readline()

    print(__('Welcome to the Sphinx %s quickstart utility.') % __display_version__)
    print()
    print(__('Please enter values for the following settings (just press Enter to\n'
             'accept a default value, if one is given in brackets).'))

    if 'path' in d:
        print()
        print(bold(__('Selected root path: %s')) % d['path'])
    else:
        print()
        print(__('Enter the root path for documentation.'))
        d['path'] = do_prompt(__('Root path for the documentation'), '.', is_path)

    while not valid_dir(d):
        print()
        print(bold(__('Error: existing Sphinx files have been found in the '
                      'selected root path.')))
        print(__('sphinx-quickstart will not overwrite existing Sphinx projects.'))
        print()
        d['path'] = do_prompt(__('Please enter a new root path (or just Enter to exit)'),
                              '', is_path_or_empty)
        if not d['path']:
            raise SystemExit(1)

    if 'sep' not in d:
        print()
        print(__('You have two options for placing the build directory for Sphinx output.\n'
                 'Either, you use a directory "_build" within the root path, or you separate\n'
                 '"source" and "build" directories within the root path.'))
        d['sep'] = do_prompt(__('Separate source and build directories (y/n)'), 'n', boolean)

    if 'dot' not in d:
        print()
        print(__('Inside the root directory, two more directories will be created; "_templates"\n'      # noqa: E501
                 'for custom HTML templates and "_static" for custom stylesheets and other static\n'    # noqa: E501
                 'files. You can enter another prefix (such as ".") to replace the underscore.'))       # noqa: E501
        d['dot'] = do_prompt(__('Name prefix for templates and static dir'), '_', allow_empty)

    if 'project' not in d:
        print()
        print(__('The project name will occur in several places in the built documentation.'))
        d['project'] = do_prompt(__('Project name'))
    if 'author' not in d:
        d['author'] = do_prompt(__('Author name(s)'))

    if 'version' not in d:
        print()
        print(__('Sphinx has the notion of a "version" and a "release" for the\n'
                 'software. Each version can have multiple releases. For example, for\n'
                 'Python the version is something like 2.5 or 3.0, while the release is\n'
                 "something like 2.5.1 or 3.0a1. If you don't need this dual structure,\n"
                 'just set both to the same value.'))
        d['version'] = do_prompt(__('Project version'), '', allow_empty)
    if 'release' not in d:
        d['release'] = do_prompt(__('Project release'), d['version'], allow_empty)

    if 'language' not in d:
        print()
        print(__(
            'If the documents are to be written in a language other than English,\n'
            'you can select a language here by its language code. Sphinx will then\n'
            'translate text that it generates into that language.\n'
            '\n'
            'For a list of supported codes, see\n'
            'https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-language.',
        ))
        d['language'] = do_prompt(__('Project language'), 'en')
        if d['language'] == 'en':
            d['language'] = None

    if 'suffix' not in d:
        print()
        print(__('The file name suffix for source files. Commonly, this is either ".txt"\n'
                 'or ".rst". Only files with this suffix are considered documents.'))
        d['suffix'] = do_prompt(__('Source file suffix'), '.rst', suffix)

    if 'master' not in d:
        print()
        print(__('One document is special in that it is considered the top node of the\n'
                 '"contents tree", that is, it is the root of the hierarchical structure\n'
                 'of the documents. Normally, this is "index", but if your "index"\n'
                 'document is a custom template, you can also set this to another filename.'))
        d['master'] = do_prompt(__('Name of your master document (without suffix)'), 'index')

    while path.isfile(path.join(d['path'], d['master'] + d['suffix'])) or \
            path.isfile(path.join(d['path'], 'source', d['master'] + d['suffix'])):
        print()
        print(bold(__('Error: the master file %s has already been found in the '
                      'selected root path.') % (d['master'] + d['suffix'])))
        print(__('sphinx-quickstart will not overwrite the existing file.'))
        print()
        d['master'] = do_prompt(__('Please enter a new file name, or rename the '
                                   'existing file and press Enter'), d['master'])

    if 'extensions' not in d:
        print(__('Indicate which of the following Sphinx extensions should be enabled:'))
        d['extensions'] = []
        for name, description in EXTENSIONS.items():
            if do_prompt(f'{name}: {description} (y/n)', 'n', boolean):
                d['extensions'].append('sphinx.ext.%s' % name)

        # Handle conflicting options
        if {'sphinx.ext.imgmath', 'sphinx.ext.mathjax'}.issubset(d['extensions']):
            print(__('Note: imgmath and mathjax cannot be enabled at the same time. '
                     'imgmath has been deselected.'))
            d['extensions'].remove('sphinx.ext.imgmath')

    if 'makefile' not in d:
        print()
        print(__('A Makefile and a Windows command file can be generated for you so that you\n'
                 "only have to run e.g. `make html' instead of invoking sphinx-build\n"
                 'directly.'))
        d['makefile'] = do_prompt(__('Create Makefile? (y/n)'), 'y', boolean)

    if 'batchfile' not in d:
        d['batchfile'] = do_prompt(__('Create Windows command file? (y/n)'), 'y', boolean)
    print()


def generate(
    d: dict, overwrite: bool = True, silent: bool = False, templatedir: str | None = None,
) -> None:
    """Generate project based on values in *d*."""
    import time

    from docutils.utils import column_width

    from sphinx import package_dir
    from sphinx._cli.console_utilities import bold, colorize  # type: ignore
    from sphinx.util.osutil import ensuredir

    template = QuickstartRenderer(templatedir or '')

    if 'mastertoctree' not in d:
        d['mastertoctree'] = ''
    if 'mastertocmaxdepth' not in d:
        d['mastertocmaxdepth'] = 2

    d['root_doc'] = d['master']
    d['now'] = time.asctime()
    d['project_underline'] = column_width(d['project']) * '='
    d.setdefault('extensions', [])
    d['copyright'] = time.strftime('%Y') + ', ' + d['author']

    d["path"] = path.abspath(d['path'])
    ensuredir(d['path'])

    srcdir = path.join(d['path'], 'source') if d['sep'] else d['path']

    ensuredir(srcdir)
    if d['sep']:
        builddir = path.join(d['path'], 'build')
        d['exclude_patterns'] = ''
    else:
        builddir = path.join(srcdir, d['dot'] + 'build')
        exclude_patterns = map(repr, [
            d['dot'] + 'build',
            'Thumbs.db', '.DS_Store',
        ])
        d['exclude_patterns'] = ', '.join(exclude_patterns)
    ensuredir(builddir)
    ensuredir(path.join(srcdir, d['dot'] + 'templates'))
    ensuredir(path.join(srcdir, d['dot'] + 'static'))

    def write_file(fpath: str, content: str, newline: str | None = None) -> None:
        if overwrite or not path.isfile(fpath):
            if 'quiet' not in d:
                print(__('Creating file %s.') % fpath)
            with open(fpath, 'w', encoding='utf-8', newline=newline) as f:
                f.write(content)
        else:
            if 'quiet' not in d:
                print(__('File %s already exists, skipping.') % fpath)

    conf_path = path.join(templatedir, 'conf.py_t') if templatedir else None
    if not conf_path or not path.isfile(conf_path):
        conf_path = path.join(package_dir, 'templates', 'quickstart', 'conf.py_t')
    with open(conf_path, encoding="utf-8") as f:
        conf_text = f.read()

    write_file(path.join(srcdir, 'conf.py'), template.render_string(conf_text, d))

    masterfile = path.join(srcdir, d['master'] + d['suffix'])
    if template._has_custom_template('quickstart/master_doc.rst_t'):
        msg = ('A custom template `master_doc.rst_t` found. It has been renamed to '
               '`root_doc.rst_t`.  Please rename it on your project too.')
        print(red(msg))
        write_file(masterfile, template.render('quickstart/master_doc.rst_t', d))
    else:
        write_file(masterfile, template.render('quickstart/root_doc.rst_t', d))

    if d.get('make_mode') is True:
        makefile_template = 'quickstart/Makefile.new_t'
        batchfile_template = 'quickstart/make.bat.new_t'
    else:
        makefile_template = 'quickstart/Makefile_t'
        batchfile_template = 'quickstart/make.bat_t'

    if d['makefile'] is True:
        d['rsrcdir'] = 'source' if d['sep'] else '.'
        d['rbuilddir'] = 'build' if d['sep'] else d['dot'] + 'build'
        # use binary mode, to avoid writing \r\n on Windows
        write_file(path.join(d['path'], 'Makefile'),
                   template.render(makefile_template, d), '\n')

    if d['batchfile'] is True:
        d['rsrcdir'] = 'source' if d['sep'] else '.'
        d['rbuilddir'] = 'build' if d['sep'] else d['dot'] + 'build'
        write_file(path.join(d['path'], 'make.bat'),
                   template.render(batchfile_template, d), '\r\n')

    if silent:
        return
    print()
    print(__('Finished: An initial directory structure has been created.'))
    print()
    print(__('You should now populate your master file %s and create other documentation\n'
             'source files. ') % masterfile, end='')
    if d['makefile'] or d['batchfile']:
        print(__('Use the Makefile to build the docs, like so:\n'
                 '   make builder'))
    else:
        print(__('Use the sphinx-build command to build the docs, like so:\n'
                 '   sphinx-build -b builder %s %s') % (srcdir, builddir))
    print(__('where "builder" is one of the supported builders, '
             'e.g. html, latex or linkcheck.'))
    print()


def valid_dir(d: dict) -> bool:
    from os import listdir

    dir = d['path']
    if not path.exists(dir):
        return True
    if not path.isdir(dir):
        return False

    if {'Makefile', 'make.bat'} & set(listdir(dir)):
        return False

    if d['sep']:
        dir = path.join('source', dir)
        if not path.exists(dir):
            return True
        if not path.isdir(dir):
            return False

    reserved_names = [
        'conf.py',
        d['dot'] + 'static',
        d['dot'] + 'templates',
        d['master'] + d['suffix'],
    ]
    if set(reserved_names) & set(listdir(dir)):
        return False

    return True


parser_description = __("""
Generate required files for a Sphinx project.

'sphinx init' is an interactive tool that asks some questions about your
project and then generates a complete documentation directory and sample
Makefile to be used with 'sphinx build'.
""")


def set_up_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument('-q', '--quiet', action='store_true', dest='quiet',
                        default=None,
                        help=__('quiet mode'))

    parser.add_argument('path', metavar='PROJECT_DIR', default='.', nargs='?',
                        help=__('project root'))

    group = parser.add_argument_group(__('Structure options'))
    group.add_argument('--sep', action='store_true', dest='sep', default=None,
                       help=__('if specified, separate source and build dirs'))
    group.add_argument('--no-sep', action='store_false', dest='sep',
                       help=__('if specified, create build dir under source dir'))
    group.add_argument('--dot', metavar='DOT', default='_',
                       help=__('replacement for dot in _templates etc.'))

    group = parser.add_argument_group(__('Project basic options'))
    group.add_argument('-p', '--project', metavar='PROJECT', dest='project',
                       help=__('project name'))
    group.add_argument('-a', '--author', metavar='AUTHOR', dest='author',
                       help=__('author names'))
    group.add_argument('-v', metavar='VERSION', dest='version', default='',
                       help=__('version of project'))
    group.add_argument('-r', '--release', metavar='RELEASE', dest='release',
                       help=__('release of project'))
    group.add_argument('-l', '--language', metavar='LANGUAGE', dest='language',
                       help=__('document language'))
    group.add_argument('--suffix', metavar='SUFFIX', default='.rst',
                       help=__('source file suffix'))
    group.add_argument('--master', metavar='MASTER', default='index',
                       help=__('master document name'))
    group.add_argument('--epub', action='store_true', default=False,
                       help=__('use epub'))

    group = parser.add_argument_group(__('Extension options'))
    for ext in EXTENSIONS:
        group.add_argument('--ext-%s' % ext, action='append_const',
                           const='sphinx.ext.%s' % ext, dest='extensions',
                           help=__('enable %s extension') % ext)
    group.add_argument('--extensions', metavar='EXTENSIONS', dest='extensions',
                       action='append', help=__('enable arbitrary extensions'))

    group = parser.add_argument_group(__('Makefile and Batchfile creation'))
    group.add_argument('--makefile', action='store_true', dest='makefile', default=True,
                       help=__('create makefile'))
    group.add_argument('--no-makefile', action='store_false', dest='makefile',
                       help=__('do not create makefile'))
    group.add_argument('--batchfile', action='store_true', dest='batchfile', default=True,
                       help=__('create batchfile'))
    group.add_argument('--no-batchfile', action='store_false',
                       dest='batchfile',
                       help=__('do not create batchfile'))
    group.add_argument('-m', '--use-make-mode', action='store_true',
                       dest='make_mode', default=True,
                       help=__('use make-mode for Makefile/make.bat'))
    group.add_argument('-M', '--no-use-make-mode', action='store_false',
                       dest='make_mode',
                       help=__('do not use make-mode for Makefile/make.bat'))

    group = parser.add_argument_group(__('Project templating'))
    group.add_argument('-t', '--templatedir', metavar='TEMPLATEDIR',
                       dest='templatedir',
                       help=__('template directory for template files'))
    group.add_argument('-d', metavar='NAME=VALUE', action='append',
                       dest='variables',
                       help=__('define a template variable'))

    return parser


def run(args: argparse.Namespace) -> int:
    # delete None or False value
    d = {k: v for k, v in args.__dict__.items() if v is not None}

    # handle use of CSV-style extension values
    d['extensions'] = ','.join(d.get('extensions', ())).split(',')

    try:
        if 'quiet' not in d:
            ask_user(d)
        elif 'project' not in d:
            print(__('"quiet" is specified, but "project" is missing.'))
            return 1
        elif 'author' not in d:
            print(__('"quiet" is specified, but "author" is missing.'))
            return 1
        else:
            # quiet mode with all required params satisfied, use default
            d = {'version': '', 'release': d['version'], **DEFAULTS, **d}
            if not valid_dir(d):
                print()
                print(__('Error: specified path is not a directory, or sphinx'
                         ' files already exist.'))
                print(__('sphinx-quickstart requires an empty directory.'
                         ' Please specify a new root path.'))
                return 1
    except (KeyboardInterrupt, EOFError):
        print()
        print('[Interrupted.]')
        return 130  # 128 + SIGINT

    for variable in d.get('variables', ()):
        try:
            name, value = variable.split('=')
            d[name] = value
        except ValueError:
            print(__('Invalid template variable: %s') % variable)

    generate(d, overwrite=False, templatedir=args.templatedir)
    return 0
