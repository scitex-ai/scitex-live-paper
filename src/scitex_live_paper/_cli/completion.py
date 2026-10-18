"""§1a shell-completion commands: install + print.

``print-shell-completion`` emits the click-generated completion script;
``install-shell-completion`` wires it into the user's shell rc so
``<pkg> <TAB>`` produces completions. Spec-built (doctrine §4) so the
§4b auditor sees CliHelp specs, not free-form text.
"""

from __future__ import annotations

import os
from pathlib import Path

import click

from .spec import spec_command_kwargs

__all__ = ["register_completion_commands"]

_SHELLS = ("bash", "zsh", "fish")

_COMPLETION_DIR = Path("~/.scitex/live-paper/runtime/completion").expanduser()


def _drop_in_path(shell: str) -> Path:
    """Static per-shell completion script path (cache-file pattern, §11)."""
    return _COMPLETION_DIR / f"scitex-live-paper.{shell}"


def _complete_var(prog_name: str) -> str:
    return "_" + prog_name.upper().replace("-", "_").replace(".", "_") + "_COMPLETE"


def _generate_script(root: click.Group, shell: str, prog_name: str) -> str:
    """Render click's completion script for ``shell`` (no subprocess)."""
    from click.shell_completion import BashComplete, FishComplete, ZshComplete

    cls = {"bash": BashComplete, "zsh": ZshComplete, "fish": FishComplete}[shell]
    return cls(root, {}, prog_name, _complete_var(prog_name)).source()


def register_completion_commands(group: click.Group, prog_name: str) -> None:
    """Attach ``print-shell-completion`` + ``install-shell-completion``."""

    @group.command(
        "print-shell-completion",
        **spec_command_kwargs(
            summary="Print the click-generated completion script to stdout.",
            description=(
                "Emit the completion script for --shell (default: bash) "
                "so it can be eval'd or redirected into an rc file.",
            ),
            examples=(
                ("{prog} print-shell-completion --shell bash", "Print the bash script."),
                ("{prog} print-shell-completion --shell zsh", "Print the zsh script."),
                (
                    'eval "$({prog} print-shell-completion --shell bash)"',
                    "Activate it in the current shell.",
                ),
            ),
        ),
    )
    @click.option(
        "--shell",
        type=click.Choice(list(_SHELLS)),
        default="bash",
        show_default=True,
        help="Target shell.",
    )
    def print_shell_completion(shell: str) -> None:
        """Print the completion script for SHELL to stdout."""
        click.echo(_generate_script(group, shell, prog_name))

    @group.command(
        "install-shell-completion",
        **spec_command_kwargs(
            summary="Install the static completion drop-in script.",
            description=(
                "Writes the click-generated completion script once to "
                "~/.scitex/live-paper/runtime/completion/ (cache-file "
                "pattern — no per-shell-start subprocess) and prints the "
                "installed path. Source that path from your shell rc to "
                "enable tab-completion. Idempotent — re-running never "
                "rewrites an identical script.",
            ),
            examples=(
                (
                    "{prog} install-shell-completion --shell bash",
                    "Write the bash drop-in script and print its path.",
                ),
                (
                    "{prog} install-shell-completion --dry-run",
                    "Print the target path without writing.",
                ),
            ),
        ),
    )
    @click.option(
        "--shell",
        type=click.Choice(list(_SHELLS)),
        default="bash",
        show_default=True,
        help="Target shell.",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="Print the target path that would be written; change nothing.",
    )
    @click.option(
        "-y",
        "--yes",
        is_flag=True,
        help="Proceed without confirmation (this command never prompts anyway).",
    )
    def install_shell_completion(shell: str, dry_run: bool, yes: bool) -> None:
        """Install the static completion drop-in script for SHELL."""
        _ = yes  # accepted for §2 compliance; install never prompts.
        target = _drop_in_path(shell)
        if dry_run:
            click.echo(f"[dry-run] would write completion script -> {target}")
            return
        script = _generate_script(group, shell, prog_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            existing = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            existing = None
        if existing != script:
            target.write_text(script, encoding="utf-8")
        click.echo(str(target))
        click.echo(f"source that path from your shell rc ({shell}) to enable tab-completion.")
