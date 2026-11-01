"""Missing bundle members have a typed public error; malformed content does not."""

import pytest

from scitex_live_paper import BundleError, BundleMissingError
from scitex_live_paper.bundle import load


@pytest.fixture(params=["directory", "manuscript", "claims"])
def missing_bundle(tmp_path, request):
    root = tmp_path / "paper"
    if request.param != "directory":
        root.mkdir()
        if request.param != "manuscript":
            (root / "manuscript.tex").write_text(
                r"\documentclass{article}\begin{document}Test\end{document}"
            )
        if request.param != "claims":
            (root / "claims.json").write_text("[]")
    return root


def test_missing_bundle_members_raise_the_public_missing_subclass(missing_bundle):
    # Arrange
    root = missing_bundle
    # Act
    # Assert
    with pytest.raises(BundleMissingError):
        load(root)


def test_missing_public_error_preserves_bundle_error_compatibility():
    # Arrange
    missing_error = BundleMissingError
    # Act
    compatible = issubclass(missing_error, BundleError)
    # Assert
    assert compatible


def test_malformed_existing_claims_keep_the_ordinary_bundle_error(tmp_path):
    # Arrange
    (tmp_path / "manuscript.tex").write_text(
        r"\documentclass{article}\begin{document}Test\end{document}"
    )
    (tmp_path / "claims.json").write_text("not-json")
    # Act
    try:
        load(tmp_path)
    except BundleError as error:
        actual_type = type(error)
    else:
        actual_type = None
    # Assert
    assert actual_type is BundleError
