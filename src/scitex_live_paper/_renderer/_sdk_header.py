"""SDK AppHeader assets for the static export (operator header-parity rule).

The Django shell (``viewer.html``) mounts the canonical SDK AppHeader via
``data-stx-app-header``. The static export (``viewer/claims/dag/index.html``)
must render the SAME header — never the old custom
``<header class="live-paper-header"><h1>`` duplicate.

The SDK header component (``app-header.js``) is pure client-side: it reads
``data-app-title`` / ``data-app-version`` off the mount div and builds the
``<header class="stx-app-header">`` row (title span — never an h1 — version
badge, project slot, actions). It needs no backend, but as an ES module it
only executes over ``http(s)`` (module scripts don't run from ``file://``
— see ``docs/dev-quickstart.md``). From ``file://`` the pages keep a
static fallback title line that hides the moment the component mounts.

This helper locates the two SDK files inside the installed ``scitex_sdk``
package, copies them into the exported site (``assets/sdk-app-header.*``),
and builds the template context the four ``.j2`` templates share.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import shutil
from pathlib import Path

__all__ = [
    "SDK_HEADER_CSS_DEST",
    "SDK_HEADER_JS_DEST",
    "SDK_HEADER_SLOT_JS_DEST",
    "copy_sdk_header_assets",
    "header_context",
]

_RENDERER_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _RENDERER_DIR / "assets"
_SDK_HEADER_CSS_SRC = (
    "ui/static/scitex_sdk/ui/css/app/app-header.css"
)
_SDK_HEADER_JS_SRC = "ui/static/scitex_sdk/ui/js/app/app-header.js"
_SLOT_JS_SRC = _ASSETS_DIR / "sdk-header-slot.js"

SDK_HEADER_CSS_DEST = "assets/sdk-app-header.css"
SDK_HEADER_JS_DEST = "assets/sdk-app-header.js"
SDK_HEADER_SLOT_JS_DEST = "assets/sdk-header-slot.js"


def _sdk_static_root() -> Path:
    """Root of the installed SDK's collected static tree."""
    spec = importlib.util.find_spec("scitex_sdk")
    if spec is None or not spec.origin:
        raise RuntimeError(
            "SDK AppHeader unavailable: scitex_sdk is not installed. "
            "Install the package (or `pip install scitex-sdk`) so the "
            "static export can mount the canonical header."
        )
    return Path(spec.origin).resolve().parent


def _copy_into(out_dir: Path, rel_dest: str, source: Path) -> Path:
    dest = out_dir / rel_dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    return dest


def _package_version() -> str:
    """Installed leaf version for the header badge (stats pattern)."""
    try:
        return importlib.metadata.version("scitex-live-paper")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+local"


def copy_sdk_header_assets(out_dir: str | Path) -> dict[str, Path]:
    """Copy the SDK header CSS/JS + slot helper into the exported site.

    Returns the ``{rel_dest: path}`` mapping so renderers stay honest
    about what they wrote.
    """
    out = Path(out_dir).expanduser().resolve()
    (out / "assets").mkdir(parents=True, exist_ok=True)
    sdk_root = _sdk_static_root()
    written = {
        SDK_HEADER_CSS_DEST: _copy_into(
            out, SDK_HEADER_CSS_DEST, sdk_root / _SDK_HEADER_CSS_SRC
        ),
        SDK_HEADER_JS_DEST: _copy_into(
            out, SDK_HEADER_JS_DEST, sdk_root / _SDK_HEADER_JS_SRC
        ),
        SDK_HEADER_SLOT_JS_DEST: _copy_into(
            out, SDK_HEADER_SLOT_JS_DEST, _SLOT_JS_SRC
        ),
    }
    return written


def header_context(*, project_label: str | None = None) -> dict[str, str | None]:
    """Template context shared by the four static pages' SDK header."""
    return {
        "sdk_header_css_url": SDK_HEADER_CSS_DEST,
        "sdk_header_js_url": SDK_HEADER_JS_DEST,
        "sdk_header_slot_js_url": SDK_HEADER_SLOT_JS_DEST,
        "app_version": _package_version(),
        # Static export has no project provider: the slot shows a plain
        # label when the caller knows the project, else stays empty.
        "project_label": project_label,
    }
