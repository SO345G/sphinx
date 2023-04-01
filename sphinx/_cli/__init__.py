"""Base 'sphinx' command.

Subcommands are loaded lazily from the ``_COMMANDS`` table for performance.

All subcommand modules must define three attributes:

- ``parser_description``, a description of the subcommand. The first paragraph
  is taken as the short description for the command.
- ``set_up_parser``, a callable taking and returning an ``ArgumentParser``. This
  function is responsible for adding options and arguments to the subcommand's
  parser..
- ``run``, a callable taking parsed arguments and returning an exit code. This
  function is responsible for running the main body of the subcommand and
  returning the exit status.

.. caution:: The entire ``sphinx._cli`` namespace is private. Only the command
             line interface has backwards-compatability guarantees.
"""

from __future__ import annotations

import argparse
import locale
import sys

from sphinx.locale import __, init_console

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Callable, Iterator, Sequence

    _PARSER_SETUP = Callable[[argparse.ArgumentParser], argparse.ArgumentParser]
    _RUNNER = Callable[[argparse.Namespace], int]

    from typing import Protocol

    class _SubcommandModule(Protocol):
        parser_description: str
        set_up_parser: _PARSER_SETUP  # takes and returns argument parser
        run: _RUNNER  # takes parsed args, returns exit code


# Command name -> import path
_COMMANDS: dict[str, str] = {
    'init': 'sphinx.cli.quickstart',
    'build': 'sphinx.cli.build',
}


class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = __('Usage: ')
        return super()._format_usage(usage, actions, groups, prefix)

    def _format_args(self, action, default_metavar):
        if action.nargs == argparse.REMAINDER:
            return __('<command> [<args>]')
        return super()._format_args(action, default_metavar)


class _RootArgumentParser(argparse.ArgumentParser):
    @staticmethod
    def _load_subcommands() -> Iterator[tuple[str, str]]:
        import importlib

        for command, module_name in _COMMANDS.items():
            module: _SubcommandModule = importlib.import_module(module_name)
            try:
                yield command, module.parser_description.partition('\n\n')[0]
            except AttributeError:
                continue

    def format_help(self):
        formatter = self._get_formatter()
        formatter.add_usage(self.usage, self._actions, [])
        formatter.add_text(self.description)

        formatter.start_section(__('Commands'))
        for command_name, command_desc in self._load_subcommands():
            formatter.add_argument(argparse.Action((), command_name, help=command_desc))
        formatter.end_section()

        formatter.start_section(__('Options'))
        formatter.add_arguments(self._optionals._group_actions)
        formatter.end_section()

        formatter.add_text(self.epilog)
        return formatter.format_help()


def _create_parser() -> _RootArgumentParser:
    parser = _RootArgumentParser(
        prog='sphinx',
        description=__('   Manage documentation with Sphinx.'),
        epilog=__('For more information, visit <https://www.sphinx-doc.org/en/master/man/>.'),
        formatter_class=_HelpFormatter,
        add_help=False,
        allow_abbrev=False,
    )
    parser.add_argument('--version', '-V', action='store_true',
                        default=argparse.SUPPRESS,
                        help=__('Show the version and exit.'))
    parser.add_argument('--help', '-h', '-?', action='store_true',
                        default=argparse.SUPPRESS,
                        help=__('Show this message and exit.'))
    parser.add_argument('--verbose', '-v', action='count', dest='verbosity', default=0,
                        help=__('increase verbosity (can be repeated)'))
    parser.add_argument('--quiet', '-q', action='store_true',
                        help=__('Only print errors and warnings.'))
    parser.add_argument('--silent', '-Q', action='store_true', dest='really_quiet',
                        help=__('no output at all, not even warnings'))
    parser.add_argument('--colour', action=argparse.BooleanOptionalAction,
                        default=True,
                        help=__('Emit coloured output to the terminal, if supported'))

    parser.add_argument('COMMAND', nargs='...', metavar=__('<command>'))
    return parser


def _parse_command(argv: Sequence[str] = ()) -> tuple[str, Sequence[str]]:
    parser = _create_parser()
    args = parser.parse_args(argv)
    command_name, *command_argv = args.COMMAND or ['help']
    command_name = command_name.lower()

    if 'version' in args or {'-V', '--version'}.intersection(command_argv):
        from sphinx import __display_version__
        sys.stdout.write(f'sphinx {__display_version__}\n')
        raise SystemExit(0)

    if 'help' in args or command_name == 'help':
        sys.stdout.write(parser.format_help())
        raise SystemExit(0)

    if command_name not in _COMMANDS:
        sys.stderr.write(__(f'sphinx: {command_name!r} is not a sphinx command. '
                            "See 'sphinx --help'.\n"))
        raise SystemExit(2)

    from sphinx._cli.util.colour import color_terminal, nocolor

    if not color_terminal() or not args.colour:
        nocolor()

    return command_name, command_argv


def _load_subcommand(command_name: str) -> tuple[str, _PARSER_SETUP, _RUNNER]:
    import importlib

    module: _SubcommandModule = importlib.import_module(_COMMANDS[command_name])
    return module.parser_description, module.set_up_parser, module.run


def _create_sub_parser(
    command_name: str,
    description: str,
    parser_setup: _PARSER_SETUP,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f'sphinx {command_name}',
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    return parser_setup(parser)


def run(__argv: Sequence[str] = ()) -> int:
    locale.setlocale(locale.LC_ALL, '')
    init_console()

    argv = __argv or sys.argv[1:]
    try:
        cmd_name, cmd_argv = _parse_command(argv)
        cmd_description, set_up_parser, runner = _load_subcommand(cmd_name)
        cmd_parser = _create_sub_parser(cmd_name, cmd_description, set_up_parser)
        cmd_args = cmd_parser.parse_args(cmd_argv)
        return runner(cmd_args)
    except SystemExit as exc:
        return exc.code  # type: ignore[return-value]
    except Exception:
        return 2


if __name__ == '__main__':
    raise SystemExit(run())
