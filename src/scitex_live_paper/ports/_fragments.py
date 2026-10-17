"""Fragment envelopes (§4 evidence-popup surface contract).

The core positions the popup and draws the chrome; the FRAGMENT
inside comes from the port. Provenance links
(figure-to-data/code) are MANDATORY on popups — a fragment without
provenance is a rendering bug, and :func:`popup_fragment` raises
for it instead of emitting a dead-end popup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ProvenanceLink:
    """One figure-to-data/code trace entry."""

    label: str
    href: str


def popup_fragment(
    title: str,
    html: str,
    provenance: Sequence[ProvenanceLink | Mapping[str, str]],
) -> Mapping[str, Any]:
    """Build the ``{title, html, provenance}`` popup envelope."""
    links = [
        link if isinstance(link, ProvenanceLink) else ProvenanceLink(**link)
        for link in provenance
    ]
    if not links:
        raise ValueError("popup_fragment requires at least one provenance link")
    return {
        "title": title,
        "html": html,
        "provenance": [
            {"label": link.label, "href": link.href} for link in links
        ],
    }


def figure_fragment(
    figure_id: str,
    svg_or_html: str,
    provenance: Sequence[ProvenanceLink | Mapping[str, str]],
    *,
    mime: str = "image/svg+xml",
) -> Mapping[str, Any]:
    """Build the figure-port fragment envelope."""
    popup = popup_fragment(
        title=f"figure:{figure_id}", html=svg_or_html, provenance=provenance
    )
    return {"figure_id": figure_id, "mime": mime, **popup}
