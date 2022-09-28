"""Build documentation from a provided source."""

import argparse
import sys
from os import path

from sphinx.locale import __

if False:
    # NoQA
    from typing import Optional, TextIO, Union

    from sphinx.application import Sphinx


def jobs_argument(value: str) -> int:
    """Special type to handle 'auto' flags passed to 'sphinx-build' via -j flag."""

    if value == 'auto':
        from os import cpu_count

        return cpu_count()

    jobs = int(value)
    if jobs > 0:
        return jobs
    raise argparse.ArgumentTypeError(__('job number should be a positive number'))


parser_description = __("""\
Generate documentation from source files.

sphinx-build generates documentation from the files in SOURCEDIR and places it
in OUTPUTDIR. It looks for 'conf.py' in SOURCEDIR for the configuration
settings. The 'sphinx-quickstart' tool may be used to generate template files,
including 'conf.py'

sphinx-build can create documentation in different formats. A format is
selected by specifying the builder name on the command line; it defaults to
HTML. Builders can also perform other tasks related to documentation
processing.

By default, everything that is outdated is built. Output only for selected
files can be built by specifying individual filenames.
""")


def set_up_parser(parser: "argparse.ArgumentParser") -> "argparse.ArgumentParser":
    # TODO handle `-b` option
    parser.add_argument('builder', nargs='?', metavar='BUILDER',
                        default='html',
                        help=__('Builder to use (default: html)'))
    parser.add_argument('source_dir', metavar='SOURCE_DIR',
                        help=__('Path to documentation source files'))
    parser.add_argument('output_dir', metavar='OUTPUT_DIR',
                        help=__('Path to the output directory'))

    parser.add_argument('--files', nargs='*', metavar='FILENAMES',
                        type=argparse.FileType('r', encoding='utf-8'),
                        default=[],
                        help=__('Specific files to rebuild. '
                                'Ignored if --force-all is specified'))
    parser.add_argument('--write-all', '-a', action='store_true',
                       help=__('Write all files '
                               '(default: only write new and changed files)'))
    parser.add_argument('--fresh-env', '-E', action='store_true',
                       help=__("Read all files, don't use a saved environment"))
    parser.add_argument('--jobs', '-j', metavar='N', default=1, type=jobs_argument,
                        help=__('Run in parallel with N processes. '
                                '"auto" uses the number of CPU cores'))

    group = parser.add_argument_group(__('path options'))
    group.add_argument('--doctree-dir', metavar='PATH',
                       help=__('Directory for doctree and environment files '
                               '(default: OUTPUTDIR/.doctrees)'))
    group.add_argument('--conf-dir', metavar='PATH',
                       help=__('Directory for the configuration file (conf.py) '
                               '(default: SOURCEDIR)'))

    group = parser.add_argument_group('build configuration options')
    group.add_argument('--no-config', action='store_true',
                       help=__('Use no config file at all, only -D options'))
    group.add_argument('--define', '-D', metavar='setting=value', action='append',
                       dest='define', default=[],
                       help=__('Override a setting in configuration file'))
    group.add_argument('--define-html', '-A', metavar='name=value', action='append',
                       dest='htmldefine', default=[],
                       help=__('Pass a value into HTML templates'))
    group.add_argument('--tag', '-t', metavar='TAG', action='append',
                       dest='tags', default=[],
                       help=__('Define tag: include "only" blocks with TAG'))
    group.add_argument('--nitpicky', '-n', action='store_true',
                       help=__('nit-picky mode, warn about all missing '
                               'references'))

    group = parser.add_argument_group(__('console output options'))
    group.add_argument('--verbose', '-v', action='count', dest='verbosity', default=0,
                       help=__('increase verbosity (can be repeated)'))
    group.add_argument('--quiet', '-q', action='store_true', dest='quiet',
                       help=__('no output on stdout, just warnings on stderr'))
    group.add_argument('--silent', '-Q', action='store_true', dest='really_quiet',
                       help=__('no output at all, not even warnings'))
    group.add_argument('--color', action='store_const', const='yes',
                       default='auto',
                       help=__('do emit colored output (default: auto-detect)'))
    group.add_argument('--no-color', '-N', dest='color', action='store_const',
                       const='no',
                       help=__('do not emit colored output (default: auto-detect)'))

    group = parser.add_argument_group(__('warning control options'))
    group.add_argument('--warning-file', metavar='FILE', dest='warnfile',
                       help=__('write warnings (and errors) to given file'))
    group.add_argument('--fail-on-warning', '-W', action='store_true',
                       help=__('turn warnings into errors'))
    group.add_argument('--keep-going', action='store_true', dest='keep_going',
                       help=__("with --fail-on-warning, keep going when getting warnings"))
    group.add_argument('--show-traceback', '-T', action='store_true', dest='traceback',
                       help=__('show full traceback on exception'))
    group.add_argument('--run-debugger-on-error', '-P', action='store_true', dest='pdb',
                       help=__('run Pdb on exception'))

    return parser


def build_main(args: 'argparse.Namespace') -> int:
    """Sphinx build "main" command-line entry."""
    from sphinx.application import Sphinx
    from sphinx.util.console import color_terminal, nocolor
    from sphinx.util.docutils import docutils_namespace, patch_docutils

    if args.no_config:
        args.conf_dir = None
    elif not args.conf_dir:
        args.conf_dir = args.source_dir

    if not args.doctree_dir:
        args.doctree_dir = path.join(args.output_dir, '.doctrees')

    # handle remaining filename arguments
    if args.write_all and len(args.files) > 0:
        parser.error(__('cannot combine -a option and filenames'))

    if args.color == 'no' or (args.color == 'auto' and not color_terminal()):
        nocolor()

    status_stream: 'Optional[TextIO]' = sys.stdout
    warning_stream: 'Optional[TextIO]' = sys.stderr
    error_stream = sys.stderr

    if args.quiet:
        status_stream = None

    if args.really_quiet:
        status_stream = warning_stream = None

    if warning_stream and args.warnfile:
        from sphinx.util import Tee
        from sphinx.util.osutil import abspath, ensuredir

        try:
            warnfile = abspath(args.warnfile)
            ensuredir(path.dirname(warnfile))
            warnfp = open(args.warnfile, 'w', encoding="utf-8")
        except Exception as exc:
            parser.error(__('cannot open warning file %r: %s') % (
                args.warnfile, exc))
        warning_stream = Tee(warning_stream, warnfp)  # type: ignore
        error_stream = warning_stream

    confoverrides = {}
    for val in args.define:
        try:
            key, val = val.split('=', 1)
        except ValueError:
            parser.error(__('-D option argument must be in the form name=value'))
        confoverrides[key] = val

    for val in args.htmldefine:
        try:
            key, val = val.split('=')
        except ValueError:
            parser.error(__('-A option argument must be in the form name=value'))
        try:
            val = int(val)
        except ValueError:
            pass
        confoverrides[f'html_context.{key}'] = val

    if args.nitpicky:
        confoverrides['nitpicky'] = True

    app = None
    try:
        conf_dir = args.conf_dir or args.source_dir
        with patch_docutils(conf_dir), docutils_namespace():
            app = Sphinx(args.source_dir, args.conf_dir, args.output_dir,
                         args.doctree_dir, args.builder, confoverrides, status_stream,
                         warning_stream, args.fresh_env, args.fail_on_warning,
                         args.tags, args.verbosity, args.jobs, args.keep_going,
                         args.pdb)
            app.build(args.write_all, args.files)
            return app.statuscode
    except (Exception, KeyboardInterrupt) as exc:
        handle_exception(exc, error_stream, args.pdb or args.verbosity, args.traceback, app)
        return 2


def run(args: 'argparse.Namespace') -> int:
    print(args)
    return 0

    from sphinx.cmd import make_mode
    return make_mode.run_make_mode(args)
