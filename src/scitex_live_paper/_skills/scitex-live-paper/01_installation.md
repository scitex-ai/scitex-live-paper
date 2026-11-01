---
description: |
  [TOPIC] Installation
  [DETAILS] Source-backed LivePaper installation.
tags: [scitex-live-paper-installation]
---

# Installation

Install `scitex-live-paper` for library/static rendering, `[server]` for the
Django viewer, `[mcp]` for MCP, or `[all]` for all public extras. `[clew]`
enables the optional live verification integration. Plotting/training packages
are generator-only dependencies, not needed to read the committed demo.

```bash
pip install 'scitex-live-paper[server,mcp]'
python -c 'import scitex_live_paper; print(scitex_live_paper.__version__)'
scitex-live-paper --help
```

Installation does not configure a host's project storage or authorization.
