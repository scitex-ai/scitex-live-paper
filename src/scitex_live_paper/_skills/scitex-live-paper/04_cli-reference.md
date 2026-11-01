---
description: |
  [TOPIC] CLI reference
  [DETAILS] Source-backed LivePaper cli reference.
tags: [scitex-live-paper-cli-reference]
---

# CLI reference

Use `scitex-live-paper --help` and each command's `--help` for the installed
version. The main workflows are:

- `validate BUNDLE` checks a directory's loadable shape.
- `render BUNDLE --out DIRECTORY` emits index, viewer, claims and graph pages.
- `serve BUNDLE --host 127.0.0.1 --port 8765` starts the local Django viewer;
  keep this local unless the user authorized wider exposure.
- `info` reports package metadata; `hub-manifest` exposes the host manifest.
- `mcp list-tools --json` lists real tool projections; `mcp start` serves them.

`render` overwrites generated output pages. `serve` pins one process-wide
bundle; multi-user hosts should instead use the per-request mount resolver.
Run `examples/make_example_project_mnist.py --help` before regeneration;
actual generation needs optional training/plotting dependencies and a dataset.
