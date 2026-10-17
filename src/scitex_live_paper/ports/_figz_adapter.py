"""Default figure-port adapter over bundle ``figz/`` blobs.

The bundled DEFAULT for the ``figure`` port. Serves
``<bundle>/figz/<figure_id>.svg`` (preferred) or ``.png`` as the
fragment HTML, with provenance lifted from the claim's
``source_file`` / ``source_hash`` record. Unknown figure id,
missing file, or no claim carrying the id raise
:class:`PortNotFound` (the dispatcher maps it to 404). Binary
``.png`` is inlined as a data URI so the fragment stays JSON-plain.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Mapping

from ..bundle import Bundle
from . import _fragments as fragments
from ._registry import PortNotFound


def _claim_for_figure(bundle: Bundle, figure_id: str):
    """Return the first claim whose ``figure_id`` extra matches."""
    for claim in bundle.claims:
        if claim.extras.get("figure_id") == figure_id:
            return claim
    return None


class FigzFigureAdapter:
    """Serve figure fragments from the bundle's ``figz/`` directory."""

    def render_figure(
        self,
        bundle: Bundle,
        figure_id: str,
        options: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        claim = _claim_for_figure(bundle, figure_id)
        if claim is None:
            raise PortNotFound(
                f"no claim carries figure_id {figure_id!r}"
            )
        figz = Path(bundle.figz_dir)
        svg = figz / f"{figure_id}.svg"
        png = figz / f"{figure_id}.png"
        if svg.is_file():
            html = svg.read_text(encoding="utf-8")
        elif png.is_file():
            data = base64.b64encode(png.read_bytes()).decode("ascii")
            html = f'<img src="data:image/png;base64,{data}" alt="{figure_id}"/>'
        else:
            raise PortNotFound(
                f"no blob for figure_id {figure_id!r} in {figz}"
            )
        provenance = []
        if claim.source_file:
            provenance.append(
                {
                    "label": f"code: {claim.source_file}",
                    "href": claim.source_file,
                }
            )
        if claim.source_hash:
            provenance.append(
                {
                    "label": f"hash: {claim.source_hash}",
                    "href": f"#session-{claim.source_session or 'unknown'}",
                }
            )
        return fragments.figure_fragment(figure_id, html, provenance)
