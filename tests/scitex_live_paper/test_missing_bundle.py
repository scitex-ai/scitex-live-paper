"""Missing bundle members have a typed public error; malformed content does not."""

import pytest

from scitex_live_paper import BundleError, BundleMissingError
from scitex_live_paper.bundle import load


@pytest.mark.parametrize("missing", ["directory", "manuscript", "claims"])
def test_missing_bundle_members_raise_the_public_missing_subclass(tmp_path, missing):
    root = tmp_path / "paper"
    if missing != "directory":
        root.mkdir()
        if missing != "manuscript":
            (root / "manuscript.tex").write_text(
                r"\documentclass{article}\begin{document}Test\end{document}"
            )
        if missing != "claims":
            (root / "claims.json").write_text("[]")
    with pytest.raises(BundleMissingError) as error:
        load(root)
    assert isinstance(error.value, BundleError)


def test_malformed_existing_claims_are_not_classified_as_missing(tmp_path):
    (tmp_path / "manuscript.tex").write_text(
        r"\documentclass{article}\begin{document}Test\end{document}"
    )
    (tmp_path / "claims.json").write_text("not-json")
    with pytest.raises(BundleError) as error:
        load(tmp_path)
    assert not isinstance(error.value, BundleMissingError)
