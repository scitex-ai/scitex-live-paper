"""Evidence-provider options shared by ``render`` and ``export-review``,
and the ``export-review`` command (the machine-readable review adapter)."""

from __future__ import annotations

import json
from pathlib import Path

import click

from .spec import spec_command_kwargs

__all__ = ["evidence_options", "export_review_cmd", "register"]


def evidence_options(fn):
    """Attach --evidence-report / --evidence-provider / --evidence-root."""
    fn = click.option(
        "--evidence-root",
        "evidence_root",
        default=None,
        type=click.Path(file_okay=False, dir_okay=True, resolve_path=True),
        help="Project the evidence provider assesses (default: the bundle directory).",
    )(fn)
    fn = click.option(
        "--evidence-provider",
        "evidence_provider",
        default=None,
        help="Installed evidence provider (entry-point name, port 'evidence'). "
        "Omit with --evidence-root to use the only installed one.",
    )(fn)
    fn = click.option(
        "--evidence-report",
        "evidence_report",
        default=None,
        type=click.Path(exists=True, dir_okay=False, resolve_path=True),
        help="Evidence report JSON a provider produced "
        "(contract scitex-live-paper.evidence-report v1).",
    )(fn)
    return fn


@click.command(
    "export-review",
    **spec_command_kwargs(
        summary="Export the registered-claim review packet (JSON or text).",
        description=(
            "Builds the review packet (scitex-live-paper.review-packet v1) — "
            "every registered claim with its evidence state, reason, source, "
            "locator and minimal evidence graph, needs-inspection first — from "
            "an evidence report or an installed evidence provider. The same "
            "packet the rendered site is built from.",
        ),
        examples=(
            (
                "{prog} export-review --evidence-report report.json --out review.json",
                "Packet from a provider's report file.",
            ),
            (
                "{prog} export-review bundle/ --evidence-root proj/ --format text",
                "Plain-text packet from the installed provider.",
            ),
        ),
    ),
)
@click.argument(
    "bundle_path",
    required=False,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
)
@evidence_options
@click.option("--format", "fmt", type=click.Choice(["json", "text"]), default="json")
@click.option(
    "--out",
    "out_path",
    default=None,
    type=click.Path(dir_okay=False, resolve_path=True),
    help="Write here instead of stdout.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Build the packet and report what would be written; write nothing.",
)
@click.option(
    "-y",
    "--yes",
    "yes",
    is_flag=True,
    help="Overwrite an existing --out file without asking.",
)
def export_review_cmd(
    bundle_path,
    evidence_report,
    evidence_provider,
    evidence_root,
    fmt,
    out_path,
    dry_run,
    yes,
) -> None:
    """Export the review packet for BUNDLE_PATH (optional with --evidence-report)."""
    from scitex_live_paper import bundle as bundle_module
    from scitex_live_paper._renderer.evidence_site import (
        EvidenceError,
        resolve_evidence_report,
    )
    from scitex_live_paper.evidence import (
        build_review_packet,
        load_report,
        review_text,
    )

    try:
        if bundle_path is None:
            if evidence_report is None:
                raise click.UsageError("give BUNDLE_PATH or --evidence-report")
            report = load_report(evidence_report)
        else:
            loaded = bundle_module.load(bundle_path)
            report = resolve_evidence_report(
                loaded,
                report_path=evidence_report,
                provider=evidence_provider,
                project_root=evidence_root,
            )
            if report is None:
                raise click.UsageError(
                    "no evidence source: pass --evidence-report, "
                    "--evidence-provider or --evidence-root"
                )
    except (bundle_module.BundleError, EvidenceError) as exc:
        raise click.ClickException(str(exc)) from exc

    packet = build_review_packet(report)
    text = (
        json.dumps(packet, indent=2, default=str)
        if fmt == "json"
        else review_text(packet)
    )
    if not out_path:
        click.echo(text)
        return
    target = Path(out_path)
    if dry_run:
        n = len(packet["needs_inspection"]) + len(packet["supported"])
        click.echo(f"DRY RUN — would write {target} ({n} registered claims, {fmt})")
        return
    if target.exists() and not yes:
        raise click.ClickException(f"{target} exists; pass --yes to overwrite it")
    target.write_text(text + "\n", encoding="utf-8")
    click.echo(f"wrote {target}")


def register(group) -> None:
    group.add_command(export_review_cmd)
