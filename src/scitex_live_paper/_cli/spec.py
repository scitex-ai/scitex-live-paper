"""Guarded imports of scitex-dev's CLI-standardization helpers (+ fallbacks).

Mirrors the ``scitex-cards`` ``_compat`` slice: when the installed
scitex-dev exposes ``CliHelp`` / ``Example`` / ``SpecCommand`` /
``SpecGroup`` (and ``make_categorized_group``), the real helpers are
re-exported (single source of truth). On older releases the doctrine
contract is rendered as plain click help text so the CLI surface stays
identical — help content, examples, and config-resolution docs never
depend on which scitex-dev release is installed.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

import click

try:  # scitex-dev with the CLI-standardization slices
    from scitex_dev.ecosystem import (
        CliHelp,
        Example,
        SpecCommand,
        SpecGroup,
        make_categorized_group,
    )

    HAS_SPEC_HELP = True
except ImportError:  # released scitex-dev without the slice helpers
    CliHelp = Example = SpecCommand = SpecGroup = None  # type: ignore[assignment]
    make_categorized_group = None  # type: ignore[assignment]
    HAS_SPEC_HELP = False

try:  # present in released scitex-dev >= 0.21 (categorized root help)
    from scitex_dev.ecosystem import make_categorized_group as _mcg

    if make_categorized_group is None:  # pragma: no cover - belt and braces
        make_categorized_group = _mcg
    HAS_CATEGORIZED_GROUP = True
except ImportError:  # pragma: no cover - old scitex-dev
    HAS_CATEGORIZED_GROUP = False

__all__ = [
    "HAS_SPEC_HELP",
    "spec_command_kwargs",
    "spec_group_kwargs",
]


def _render_fallback_help(
    summary: str,
    description: tuple[str, ...],
    examples: tuple[tuple[str, str], ...],
    config_resolution: tuple[str, ...],
    version_of: str | None,
    prog: str = "scitex-live-paper",
) -> str:
    """Plain help body matching the doctrine section order (fallback only)."""
    if version_of:
        try:
            first = f"{version_of} (v{_dist_version(version_of)}) — {summary}"
        except PackageNotFoundError:
            # Source-tree run without an installed dist (e.g. PYTHONPATH
            # tests): the summary still renders; only the version is absent.
            first = f"{version_of} — {summary}"
    else:
        first = summary
    blocks: list[str] = [first, *description]
    # "\b" marks the block as pre-formatted so click keeps the line breaks.
    if examples:
        lines = ["\b", "Examples:"]
        lines.extend(
            f"  $ {cmd.replace('{prog}', prog)}" + (f"  {note}" if note else "")
            for cmd, note in examples
        )
        blocks.append("\n".join(lines))
    if config_resolution:
        blocks.append("\n".join(["\b", "Config resolution:", *config_resolution]))
    return "\n\n".join(blocks)


def spec_command_kwargs(
    *,
    summary: str,
    description: str | tuple[str, ...] = (),
    examples: tuple[tuple[str, str], ...] = (),
) -> dict:
    """``click.command`` kwargs for a spec-built leaf.

    ``examples`` is a tuple of ``(cmd, note)`` pairs; ``cmd`` uses the
    ``{prog}`` placeholder per the CliHelp contract.
    """
    if isinstance(description, str):
        description = (description,)
    if HAS_SPEC_HELP:
        return {
            "cls": SpecCommand,
            "help_spec": CliHelp(
                summary=summary,
                description=description,
                examples=tuple(Example(cmd, note) for cmd, note in examples),
            ),
        }
    return {
        "help": _render_fallback_help(
            summary, tuple(description), tuple(examples), (), None
        ),
        "short_help": summary,
    }


def spec_group_kwargs(
    *,
    summary: str,
    description: str | tuple[str, ...] = (),
    config_resolution: tuple[str, ...] = (),
    version_of: str | None = None,
    command_categories: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> dict:
    """``click.group`` kwargs for the spec-built categorized root group."""
    if isinstance(description, str):
        description = (description,)
    if HAS_SPEC_HELP:
        return {
            "cls": SpecGroup,
            "help_spec": CliHelp(
                summary=summary,
                description=description,
                config_resolution=config_resolution,
                version_of=version_of,
            ),
            "command_categories": command_categories,
        }
    kwargs: dict = {
        "help": _render_fallback_help(
            summary, tuple(description), (), tuple(config_resolution), version_of
        ),
        "short_help": summary,
    }
    if HAS_CATEGORIZED_GROUP:
        kwargs["cls"] = make_categorized_group(command_categories)
    return kwargs
