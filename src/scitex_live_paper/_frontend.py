"""Public installed-wheel frontend package discovery, without Django startup."""

from __future__ import annotations

import json
from pathlib import Path


def get_frontend_package_dir() -> Path:
    """Return the npm file-dependency root or fail for an incomplete/old wheel.

    The package is private and consumed via npm file dependency/pack; no npm
    publication or source checkout is required. All exports remain in this root.
    """
    root = Path(__file__).resolve().parent
    manifest = root / "package.json"
    if not manifest.is_file():
        raise RuntimeError(
            "Installed LivePaper lacks the rich PDF frontend package; upgrade to a provider-capable build"
        )
    metadata = json.loads(manifest.read_text())
    if metadata.get("scitexRichPdfContract") != "scitex-live-paper.rich-pdf/v1":
        raise RuntimeError("Installed LivePaper rich PDF contract is unsupported")
    export = metadata.get("exports", {}).get("./pdf-provider", {})
    members = {kind: export.get(kind) for kind in ("types", "import")}
    members["styles"] = metadata.get("exports", {}).get("./pdf-provider.css")
    for kind, member in members.items():
        if not isinstance(member, str):
            raise TypeError(f"LivePaper rich PDF {kind} export is missing")
        target = (root / member).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise RuntimeError(f"LivePaper rich PDF {kind} export is unavailable")
    return root
