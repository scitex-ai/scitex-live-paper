"""Read page coordinates produced for the exact PDF bytes in a bundle."""

import hashlib
import json
import os
import stat
from math import isfinite


def _valid_anchor(anchor):
    if not isinstance(anchor, dict):
        return False
    page, box = anchor.get("page"), anchor.get("bbox")
    if type(page) is not int or page < 1 or not isinstance(box, list) or len(box) != 4:
        return False
    if not all(type(value) in (int, float) and abs(value) <= 1_000_000 and isfinite(value)
               for value in box):
        return False
    x0, y0, x1, y1 = box
    return x0 < x1 and y0 < y1


def read_pdf_anchors(bundle):
    """Return usable anchors, with absent or stale coordinates treated as optional."""
    sidecar = bundle.root / "pdf-anchors.json"
    pdf = bundle.manuscript_path
    if pdf.suffix.lower() != ".pdf" or sidecar.is_symlink():
        return {}
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(sidecar, flags), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return {}
            data = stream.read(1_048_577)
        if len(data) > 1_048_576:
            return {}
        payload = json.loads(data)
        if not isinstance(payload, dict) or not isinstance(payload.get("anchors"), dict):
            return {}
        if not pdf.resolve().is_relative_to(bundle.root.resolve()):
            return {}
        digest = hashlib.sha256()
        with pdf.open("rb") as stream:
            for chunk in iter(lambda: stream.read(131_072), b""):
                digest.update(chunk)
        if payload.get("pdf_sha256") != digest.hexdigest():
            return {}
    except (OSError, ValueError):
        return {}

    return {key: {"page": anchor["page"], "bbox": anchor["bbox"]}
            for key, anchor in payload["anchors"].items() if _valid_anchor(anchor)}
