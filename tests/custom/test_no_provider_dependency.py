"""live-paper depends on no specific evidence provider.

Coupling to providers is through the evidence-provider contract only, so
``pyproject.toml`` declares no provider extra and no provider dependency,
and the hub-app manifest pulls none. Real file IO — no mocks.
"""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib  # py3.11+
except ImportError:  # pragma: no cover - py3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[2]
#: The only SciTeX distributions live-paper may name as requirements —
#: none of them is an evidence provider.
KNOWN_SCITEX_DEPS = {
    "scitex-live-paper",
    "scitex-logging",
    "scitex-dev",
    "scitex-io",
    "scitex-sdk",
}


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _dist_name(req: str) -> str:
    name = req.split(";")[0].split("[")[0]
    for sep in ("<", ">", "=", "!", "~", " "):
        name = name.split(sep)[0]
    return name.strip().lower()


def _every_requirement() -> list[str]:
    project = _pyproject()["project"]
    reqs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        reqs.extend(extra)
    return reqs


def test_pyproject_declares_no_provider_extra():
    # Arrange
    # Act
    extras = set(_pyproject()["project"]["optional-dependencies"])
    # Assert
    assert extras <= {"django", "server", "mcp", "test", "all", "dev"}


def test_pyproject_requirements_name_no_unknown_scitex_package():
    # Arrange
    # Act
    scitex_deps = {
        _dist_name(r)
        for r in _every_requirement()
        if _dist_name(r).startswith("scitex-")
    }
    # Assert
    assert scitex_deps <= KNOWN_SCITEX_DEPS


def test_all_extra_is_closed_over_public_extras():
    # Arrange
    # Act
    all_extra = _pyproject()["project"]["optional-dependencies"]["all"]
    # Assert
    assert all_extra == ["scitex-live-paper[django,server,mcp,test]"]


def test_hub_manifest_requires_no_unknown_scitex_package():
    # Arrange
    from scitex_live_paper import HUB_APP_MANIFEST

    # Act
    scitex_reqs = {
        _dist_name(r)
        for r in HUB_APP_MANIFEST["requires"]
        if _dist_name(r).startswith("scitex-")
    }
    # Assert
    assert scitex_reqs <= KNOWN_SCITEX_DEPS


def test_evidence_schema_is_shipped_as_package_data():
    # Arrange
    # Act
    package_data = _pyproject()["tool"]["setuptools"]["package-data"][
        "scitex_live_paper"
    ]
    # Assert
    assert "evidence/*.json" in package_data
