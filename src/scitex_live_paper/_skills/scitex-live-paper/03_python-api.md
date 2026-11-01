---
description: |
  [TOPIC] Python API
  [DETAILS] Source-backed LivePaper python api.
tags: [scitex-live-paper-python-api]
---

# Python API

`scitex_live_paper.bundle.load(path)` loads a bundle directory and returns
`Bundle` with manuscript, claims, graph, provenance and paper lifecycle state.
`BundleSource` supports a directory, existing Bundle or resolver callable.
`BundleContext` carries that source, API base, `RendererOptions`, `PaperState`
and optional renderer registry for a per-request host mount.

`scitex_live_paper.ports.Registry` maps `figure`, `snippet` and `claim-graph`
to adapters. `FigzFigureAdapter` is the bundled figure provider; other adapters
are injected by consumers. `translate_consumer_payload` normalizes port aliases
or anchored comment payloads without importing Writer or Journal. `EventBus`
provides the Python-side event interface. See `ports/protocols.py` and
`docs/dev/ports-events-contract.md` in the checkout for adapter contracts.

Static rendering is currently exposed by
`scitex_live_paper._cli.render.render_site(bundle_path, out_dir, project_label=...)`;
this module path is internal and may change. Prefer the CLI for a stable render
entry point. Do not invent a top-level `render()` API.
