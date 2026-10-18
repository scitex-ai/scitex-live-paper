#!/usr/bin/env python3
"""Example: load an accepted manuscript bundle and summarise it.

Run:
    python example_live_paper.py
    python example_live_paper.py --bundle <path-to-bundle>

Loads the in-tree fixture bundle by default and prints the claim
summary to stdout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scitex_live_paper import bundle as bundle_module

HERE = Path(__file__).resolve().parent
DEFAULT_BUNDLE = (
    HERE.parent
    / "tests"
    / "scitex_live_paper"
    / "fixtures"
    / "bundle-min"
)


def main(argv: list[str] | None = None) -> int:
    """Load a bundle and print a claim summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle",
        default=str(DEFAULT_BUNDLE),
        help="Path to the accepted manuscript bundle directory.",
    )
    args = parser.parse_args(argv)

    loaded = bundle_module.load(args.bundle)
    lines = [
        f"bundle: {loaded.root.name}",
        f"claims: {len(loaded.claims)}",
        f"manuscript: {loaded.manuscript_path.name}",
        f"paper stage: {loaded.paper_state.stage}",
    ]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
