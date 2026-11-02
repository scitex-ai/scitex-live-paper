---
description: |
  [TOPIC] Bundle rendering
  [DETAILS] Source-backed LivePaper bundle rendering.
tags: [scitex-live-paper-quick-start]
---

# Bundle rendering

A bundle is a **directory** containing `manuscript.pdf` (or `.tex`) and
`claims.json`; optional `dag.mmd`, `provenance.yaml`, `state.yaml` and `figz/`
carry graph, provenance, lifecycle and figures. Claims mirror Clew fields.

From a source checkout, use the committed demo without downloading/training:

```bash
scitex-live-paper validate examples/example-project-mnist
scitex-live-paper render examples/example-project-mnist --out /tmp/mnist-live-paper-site
```

Use a new output directory: rendering overwrites its generated pages. Open
`index.html` or serve that output directory locally. The demo's registered
claims and computed sample numbers are not certified research findings.
