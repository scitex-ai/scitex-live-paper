"""Validate command: fuller pre-flight check than info."""

from __future__ import annotations

try:
    import click
except ImportError as exc:  # pragma: no cover - defensive
    raise RuntimeError(
        "scitex-live-paper CLI requires click — install the package "
        "(or `pip install click>=8.0`)"
    ) from exc

from scitex_live_paper import bundle as bundle_module
from .spec import spec_command_kwargs

__all__ = ["validate_cmd", "_validate_bundle", "_KNOWN_CLAIM_STATUSES", "_looks_hex", "register"]


# Mirrors scitex-clew's claim-status vocabulary (palette v1.3,
# clew 0.7.0; ``unsourced`` added by clew 0.8.1 / claims.json 1.4).
# Used by `validate` to flag claims whose status isn't a
# recognised lifecycle value (a common operator footgun: a hand-edit
# typo like ``"verfied"``). Legacy "partial" never reaches this check —
# ``bundle.load()`` normalizes it to "suspect" at ingest. ``not_found``
# is a lookup verdict, never a resting claims.json status, so it is
# deliberately absent.
#
# ``unsourced`` IS a resting status and so belongs here. It renders in
# the amber/suspect colour, but that fold happens purely in the colour
# layer — the status string itself stays "unsourced" everywhere,
# including in this validation set. Normalizing it to "suspect" at
# ingest (the way "partial" is) would be wrong: "partial" was a rename
# with no surviving concept, whereas "unsourced" is a distinct state
# the operator still needs to read.
_KNOWN_CLAIM_STATUSES = frozenset({
    "registered",
    "verified",
    "suspect",
    "mismatch",
    "missing",
    "unsourced",
})
@click.command(
    "validate",
    **spec_command_kwargs(
        summary="Run a fuller pre-flight check than info.",
        description=(
            "On top of bundle.load()'s syntactic checks, validate runs "
            "claim integrity (duplicate claim_ids, known lifecycle "
            "statuses, hex-shaped source_hashes) and PaperState sanity "
            "(accepted/published stages need a pinned_commit). Reports "
            "every issue as <file>: <reason>; exits 0 on clean, non-zero "
            "(issue count) otherwise.",
        ),
        examples=(
            ("{prog} validate bundle/", "Check before render or serve."),
            (
                "{prog} validate bundle/; echo $?",
                "Count issues via the exit code.",
            ),
        ),
    ),
)
@click.argument(
    "bundle_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
)
def validate_cmd(bundle_path: str) -> None:
    """Run a fuller pre-flight check than ``info``.

    On top of ``bundle.load()``'s syntactic checks, ``validate`` runs:

    - **Claim integrity**: no duplicate ``claim_id``s, every
      ``status`` string is a known scitex-clew lifecycle value, every
      ``source_hash`` looks hex-shaped.
    - **PaperState sanity**: ``accepted`` / ``published`` stages
      without a ``pinned_commit`` are flagged (badge would show but
      re-verify would be ungated).

    Reports every issue with a clear "<file>: <reason>" line. Exits 0
    on clean, non-zero (count of issues) otherwise. Use this BEFORE
    ``render`` or ``serve`` against an unfamiliar bundle.
    """
    try:
        bundle = bundle_module.load(bundle_path)
    except bundle_module.BundleError as exc:
        # The load itself failed — surface as a ClickException so the
        # exit code is non-zero with no traceback.
        raise click.ClickException(str(exc)) from exc

    issues = _validate_bundle(bundle)

    if not issues:
        click.echo(f"ok: {bundle_path} (no issues found)")
        return

    for issue in issues:
        click.echo(f"warn: {issue}")
    click.echo(f"\n{len(issues)} issue{'' if len(issues) == 1 else 's'} found")

    # Non-zero exit signalling the count, capped at 125 (POSIX
    # convention: exit codes above 125 reserve for shell-level errors).
    raise click.exceptions.Exit(code=min(len(issues), 125))


def _validate_bundle(bundle: "bundle_module.Bundle") -> list[str]:
    """Run every check and return a list of "<file>: <reason>" strings."""
    issues: list[str] = []

    seen_ids: set[str] = set()
    for claim in bundle.claims:
        if claim.claim_id in seen_ids:
            issues.append(
                f"claims.json: duplicate claim_id {claim.claim_id!r} "
                f"(file_path={claim.file_path!r})"
            )
        else:
            seen_ids.add(claim.claim_id)

        if claim.status not in _KNOWN_CLAIM_STATUSES:
            issues.append(
                f"claims.json: claim {claim.claim_id!r} has unknown status "
                f"{claim.status!r} (expected one of "
                f"{sorted(_KNOWN_CLAIM_STATUSES)!r})"
            )

        if claim.source_hash is not None and not _looks_hex(claim.source_hash):
            issues.append(
                f"claims.json: claim {claim.claim_id!r} source_hash "
                f"{claim.source_hash!r} doesn't look hex-shaped"
            )

    ps = bundle.paper_state
    if ps.stage in {"accepted", "published"} and not ps.pinned_commit:
        issues.append(
            f"state.yaml: stage is {ps.stage!r} but no pinned_commit set — "
            "verification badge will show but re-verify is ungated"
        )

    return issues


def _looks_hex(value: str) -> bool:
    """Return True iff `value` is a non-empty string of hex chars."""
    if not value:
        return False
    return all(c in "0123456789abcdefABCDEF" for c in value)


def register(group) -> None:
    """Attach the ``validate`` command to ``group``."""
    group.add_command(validate_cmd)
