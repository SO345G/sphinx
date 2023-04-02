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

The entire ``sphinx._cli`` namespace is private, only the command line interface
has backwards-compatability guarantees.
"""

from __future__ import annotations

import locale
import sys

import click

import sphinx
from sphinx._cli.util.colour import color_terminal, nocolor
from sphinx.locale import __, init_console

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Sequence

# Command name -> import path
_COMMANDS: dict[str, str] = {
}


def _load_subcommand(self, cmd_name):
    import importlib

    module = importlib.import_module(_COMMANDS[cmd_name])
    try:
        command = module.command
    except AttributeError:
        msg = __('Subcommand not found')
        raise AttributeError(msg) from None
    if isinstance(command, click.BaseCommand):
        return command
    msg = __('Subcommand not a ``click.BaseCommand``.')
    raise ValueError(msg)


class _LazyLoader(click.Group):
    def list_commands(self, ctx: click.Context):
        return super().list_commands(ctx) + [*_COMMANDS]

    def get_command(self, ctx: click.Context, command_name: str):
        if command_name not in _COMMANDS:
            ctx.fail(__(f'sphinx: {command_name!r} is not a sphinx command. '
                        "See 'sphinx --help'.\n"))
        return _load_subcommand(command_name)


@click.group(
    cls=_LazyLoader,
    help=__('Manage documentation with Sphinx.'),
    epilog=__('For more information, visit <https://www.sphinx-doc.org/en/master/man/>.'),
    no_args_is_help=True,
    # subcommand_metavar='<command> [ARGS]...',
)
@click.version_option(sphinx.__display_version__, '-V', '--version',
                      prog_name='sphinx', message='sphinx %(version)s')
@click.help_option('-h', '-?', '--help')
@click.option('-v', '--verbose', 'verbosity', count=True, default=0,
              help=__('increase verbosity (can be repeated)'))
@click.option('-q', '--quiet', count=True, default=0,
              help=__('Only print errors and warnings.'))
@click.option('--silent', is_flag=True, help=__('No output at all'))
@click.option('--colour/--no-colour', default=True,
              help=__('Emit coloured output to the terminal, if supported'))
def command(verbosity: int, quiet: bool, silent: bool, colour: bool):
    if not color_terminal() or not colour:
        nocolor()


def run(__argv: Sequence[str] = ()) -> int:
    locale.setlocale(locale.LC_ALL, '')
    init_console()

    argv = __argv or sys.argv[1:]
    return command.main(args=argv, prog_name='sphinx')


if __name__ == '__main__':
    raise SystemExit(run())
