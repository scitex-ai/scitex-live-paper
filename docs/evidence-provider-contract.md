# Evidence-provider contract

scitex-live-paper shows a reviewer, at a glance, which **registered claims** in
a manuscript are supported by evidence and which need inspection, and gives each
claim its minimal evidence graph. It does not compute any of this itself. An
**evidence provider** computes it, and live-paper renders whatever a conforming
provider supplies. live-paper imports no provider and depends on none. With no
provider it renders the claims without a state, and that is not an error.

Scope rule: only registered claims are assessed. Text that is not a registered
claim is never marked as supported or as unsupported. It may be supported, but
no graph connects it, so there is nothing to say about it.

## Versioning

| Artifact | id | version | file |
|---|---|---|---|
| Evidence report (provider to live-paper) | `scitex-live-paper.evidence-report` | `1.0.0` | `src/scitex_live_paper/evidence/evidence-report.schema.json` (shipped in the wheel) |
| Review packet (live-paper to human or AI reviewer) | `scitex-live-paper.review-packet` | `1.0.0` | produced by `export-review`, documented below |

Both carry `schema` + `schema_version` (semver). A **minor** bump only adds
optional fields, so a consumer of `1.x` keeps working. A **major** bump changes
or removes fields. live-paper accepts any `1.x.y` report and rejects other
majors with a clear error. Providers should vendor a version-pinned copy of
the schema and validate their output against it in their own tests, without
importing live-paper.

## State vocabulary (provider-neutral)

| state | label shown | meaning |
|---|---|---|
| `supported` | ✓ Supported by evidence | The stated value was checked against its source, and the source against its recorded computation. Both hold. |
| `not_supported` | ✗ Not supported | Something the provider checked does not hold. `reason` says what (e.g. "value in source differs: 2 in source vs 3 stated", "source changed after the run"). |
| `not_checkable` | ? Registered, not checkable | The claim is registered and connected, but its value could not be checked (e.g. "no locator, value not checked"). |
| `no_evidence_graph` | ∅ No evidence graph | The claim is registered, but no recorded computation connects it to a source. |

Each state also has its own colour-blind-safe hue, underline style and symbol,
so colour is never the only cue. "Needs inspection" means every state except
`supported`. It is ordered `not_supported`, then `not_checkable`, then
`no_evidence_graph`, and within a state by manuscript position.

## Evidence report (what a provider supplies)

```json
{
  "schema": "scitex-live-paper.evidence-report",
  "schema_version": "1.0.0",
  "provider": {"name": "example-provider", "version": "1.2.3"},
  "project_root": "/abs/path/to/project",
  "claims": [
    {
      "claim_id": "n_rows",
      "location": {"file": "paper/paper.tex", "line": 3, "label": "paper.tex:L3"},
      "claim_type": "value",
      "stated_text": "n = 3",
      "stated_value": 3,
      "state": "not_supported",
      "reason": "value in source differs: 2 in source vs 3 stated",
      "source": {"file": "results/results.json", "locator": {".": {"pointer": "/n_rows"}}},
      "details": ["claimed 3 vs source 2"],
      "provider_status": {"name": "VALUE_MISMATCH", "code": 21},
      "graph": {
        "nodes": [
          {"id": "f1", "kind": "input", "label": "data/input.csv", "hash": "2a2b…"},
          {"id": "p1", "kind": "process", "label": "run 2026-11-18 19:38"},
          {"id": "f2", "kind": "output", "label": "results/results.json", "hash": "2c38…"},
          {"id": "c", "kind": "claim", "label": "n_rows"}
        ],
        "edges": [
          {"source": "f1", "target": "p1", "kind": "input"},
          {"source": "p1", "target": "f2", "kind": "output"},
          {"source": "f2", "target": "c", "kind": "supports"}
        ],
        "summary": "1 process, 2 files"
      }
    }
  ]
}
```

Required per claim: `claim_id`, `location`, `state`, `reason`. Everything else is
optional. `provider_status` is the provider's raw verdict. It is opaque to
live-paper and shown verbatim. `graph` is the minimal evidence graph: the nodes
and edges the claim rests on, and nothing else. Node `kind` is one of `claim`,
`process`, `input`, `output`, `other`. If the key is **omitted**, live-paper
asks the provider for the graph on demand. If it is `null`, the claim has no
graph, and `graph_error` may say why.

## Connecting a provider

**1. Python entry point (in-process).** Publish an object in the existing
`scitex.livepaper.renderers` group (the ports seam) with `port = "evidence"`,
a `name`, and an `adapter` that implements `EvidencePort`
(`scitex_live_paper.ports.protocols`):

```toml
[project.entry-points."scitex.livepaper.renderers"]
my-provider = "my_package.live_paper_adapter:EvidenceEntry"
```

```python
class EvidenceAdapter:
    def evidence_report(self, project_root, claim_ids, options) -> dict: ...
    # optional, used when a report omits a claim's "graph":
    def evidence_graph(self, project_root, claim_id, options) -> dict | None: ...

class EvidenceEntry:
    port = "evidence"
    name = "my-provider"
    adapter = EvidenceAdapter()
```

**2. Report file (out-of-process).** The provider writes an evidence report
with its own tooling, and live-paper reads the file. Use this when the
provider is not installed beside live-paper.

## Using it

```bash
# provider by entry-point name, run in the project the claims belong to
scitex-live-paper render bundle/ --out site/ --evidence-provider my-provider --evidence-root /path/to/project
# or a report file the provider produced
scitex-live-paper render bundle/ --out site/ --evidence-report report.json
# machine-readable review packet for an AI reviewer (JSON, or --format text)
scitex-live-paper export-review --evidence-report report.json --out review.json
```

The rendered site adds `paper.html`, the manuscript with each registered claim
marked by its state. Hovering a mark shows the reason, and clicking it opens
the claim's minimal-graph page. `claims.html` opens with the **Needs
inspection** list, followed by the supported claims. `review.json` and
`review.txt` hold the review packet. MCP tools
`live_paper_evidence_review` and `live_paper_evidence_claim` serve the same
packet to agents. Every human view and the machine adapter are rendered from
one review packet, so they cannot disagree. A test enforces this.

## Review packet (what a reviewer reads)

`scitex-live-paper.review-packet` 1.0.0 is the evidence report re-ordered for
review: `needs_inspection` (ordered as above) and `supported`. Each entry adds
`label`, `symbol`, `needs_inspection`, and `graph_url` (the claim's page in the
rendered site). The packet also includes `scope`, `states` (state to label),
`counts`, and `provider`.

## Known providers (examples only)

- scitex-clew ships an adapter that maps its claim verification and per-claim
  provenance slice to this contract. It is documented in the scitex-clew
  repository.
