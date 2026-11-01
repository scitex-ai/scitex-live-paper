---
name: scitex-live-paper
description: |
  [WHAT] Render manuscript bundles as PDF viewers with claim overlays, comments, provenance pages and injectable evidence ports.
  [WHEN] Use for LivePaper bundle validation/rendering, mounted viewer context, PDF overlays/comments, or integrating figure/snippet/claim-graph adapters. Scientific verification remains owned by Clew.
  [HOW] Install scitex-live-paper; use the bundle and renderer APIs or CLI. Add [server] for the Django viewer and [mcp] for agent tools. Follow the linked task-specific notes.
tags: [scitex-live-paper]
primary_interface: python
interfaces:
  python: 2
  cli: 1
  mcp: 2
  django: 3
  skills: 2
---

# SciTeX Live Paper

The renderer consumes Clew claims and preserves unknown fields; it does not
create another claim schema or establish that a claim is verified.

- [01_installation.md](01_installation.md) — extras and import checks
- [02_quick-start.md](02_quick-start.md) — validate and render a real bundle
- [03_python-api.md](03_python-api.md) — public bundle, context and port APIs
- [04_cli-reference.md](04_cli-reference.md) — CLI commands and output boundaries
- [05_mcp-tools.md](05_mcp-tools.md) — tool and packaged skill discovery
- [10_mounted-viewer.md](10_mounted-viewer.md) — host authorization, URL context, overlays and comments
- [20_env-vars.md](20_env-vars.md) — runtime settings actually read by the standalone server

The source checkout includes `examples/example-project-mnist`, a labeled
three-page demo with registered claims and regeneration provenance. A Journal
submission `bundle.yaml` by itself is not a LivePaper bundle directory.
