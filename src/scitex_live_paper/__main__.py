"""``python -m scitex_live_paper`` — module entry that calls the CLI entry."""

import sys

from scitex_live_paper._cli import main

if __name__ == "__main__":
    sys.exit(main())
