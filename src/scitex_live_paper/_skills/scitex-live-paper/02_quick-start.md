---
description: |
  [TOPIC] Bundle rendering
  [DETAILS] Source-backed LivePaper bundle rendering.
tags: [scitex-live-paper-quick-start]
---

# Bundle rendering

A bundle is a **directory** containing `manuscript.pdf` (or `.tex`) and
`claims.json`; optional `dag.mmd`, `provenance.yaml`, `state.yaml` and `figz/`
carry graph, provenance, lifecycle and figures. Claims mirror the upstream claim registry's fields.

An optional `self-proof.json` is a reproduction receipt written by the paper
project's `make self-proof` (every claim re-derived from a fresh clone with a
throwaway store). Only the versioned contract keys are read: `schema` (any
string ending in `/self-proof/v1`), `verdict` (`PASS`/`FAIL`), `finished_at`,
`source.commit`, `source.ref`, `claims.{ok,committed,verified}` and `failures`.
It is exposed as `Bundle.self_proof` and as `self_proof` in the review packet,
and the reader shows it as one line under the claim summary ("self-proof:
ok/committed claims re-derived from a fresh checkout on DATE", or a warning
naming the first failure). Absent → nothing is shown; malformed → ignored with a
logged warning, never an error.

From a source checkout, use the committed demo without downloading/training:

```bash
scitex-live-paper validate examples/example-project-mnist
scitex-live-paper render examples/example-project-mnist --out /tmp/mnist-live-paper-site
```

Use a new output directory: rendering overwrites its generated pages. Open
`index.html` or serve that output directory locally. The demo's registered
claims and computed sample numbers are not certified research findings.
