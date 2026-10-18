"""Cross-package import gate (PS-140) for scitex-live-paper.

Every module listed here is imported by this package's source but
OWNED by a peer standalone. A rename or move on the other side of
that boundary is invisible to this package's unit tests and
surfaces as ModuleNotFoundError in a user's process.

Hand-written to the generator's shape: this package is not in the
auditor's ECOSYSTEM registry, so `scitex-dev ecosystem
install-cross-package-gate scitex-live-paper` refuses with
`'scitex-live-paper' not in ECOSYSTEM`. The list below matches what
the generator computes (the same function the PS-140 auditor grades
against): `scitex_app._django` (optional hub-manifest base class in
`_django/apps.py`) + `scitex_logging` (diagnostic logging in the
Django surface).

generated-by: scitex-dev 0.60.2.dev25+g4b298ce60 (manual transcription)

Regenerate with:

    scitex-dev ecosystem install-cross-package-gate scitex-live-paper --force

(once the package is registered; until then update by hand).

Do not hand-edit the list: the PS-140 auditor recomputes it from
source on every run and fails on any drift in either direction
(a missing entry OR a stale one).

Hand-written cases go BELOW the second sentinel. Everything there
is preserved byte-identically across regeneration; everything
between the sentinels is overwritten.
"""

import importlib

import pytest

# ===== AUTO-GENERATED: cross-package imports =====
CROSS_PACKAGE_IMPORTS = [
    'scitex_app._django',
    'scitex_dev.ecosystem',
    'scitex_logging',
]
# ===== END AUTO-GENERATED =====


@pytest.mark.parametrize("module_name", CROSS_PACKAGE_IMPORTS)
def test_cross_package_import_resolves_to_real_module(module_name):
    """Importing scitex-live-paper's declared cross-package dependency must succeed."""
    # Arrange -- skip on the ROOT distribution only (a lean install where
    # the peer is genuinely absent must SKIP, not fail); two statements on
    # purpose so the root/full-path distinction stays visible (PS-140 s2).
    root = module_name.split(".")[0]
    pytest.importorskip(root)
    # Act -- hard-import the FULL dotted path, so a renamed submodule
    # FAILS instead of being skipped as an absence.
    mod = importlib.import_module(module_name)
    # Assert
    assert mod.__name__ == module_name
