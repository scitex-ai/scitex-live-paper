"""Update the Live Paper compatibility exports from a released Rich PDF wheel."""

from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path
from shutil import copyfile

from scitex_rich_pdf import get_frontend_package_dir

RICH_PDF_VERSION = "0.1.1"
ASSETS = {
    "pdf-provider.js": "js",
    "pdf-provider.d.ts": "js",
    "pdf-provider.css": "css",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    installed = version("scitex-rich-pdf")
    if installed != RICH_PDF_VERSION:
        parser.error(f"expected scitex-rich-pdf=={RICH_PDF_VERSION}, found {installed}")
    root = Path(__file__).resolve().parents[1]
    static = root / "src/scitex_live_paper/_django/static/live_paper"
    source = get_frontend_package_dir()
    for name, directory in ASSETS.items():
        destination = static / directory / name
        if args.check:
            if (source / name).read_bytes() != destination.read_bytes():
                parser.error(f"{destination.relative_to(root)} differs from Rich PDF")
        else:
            copyfile(source / name, destination)


if __name__ == "__main__":
    main()
