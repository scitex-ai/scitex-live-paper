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
| Evidence report (provider to live-paper) | `scitex-live-paper.evidence-report` | `1.2.0` | `src/scitex_live_paper/evidence/evidence-report.schema.json` (shipped in the wheel) |
| Review packet (live-paper to human or AI reviewer) | `scitex-live-paper.review-packet` | `1.2.0` | `src/scitex_live_paper/evidence/review-packet.schema.json` (shipped in the wheel; produced by `export-review`, documented below) |

Both carry `schema` + `schema_version` (semver). A **minor** bump only adds
optional fields, so a consumer of `1.x` keeps working. A **major** bump changes
or removes fields. live-paper accepts any `1.x.y` report and rejects other
majors with a clear error.

| version | adds |
|---|---|
| 1.0.0 | states, reasons, sources, minimal graph |
| 1.1.0 | optional per-node `failure` (where the evidence broke); packet `failing_nodes` |
| 1.2.0 | optional `source.value` (the value the provider read at the locator); packet `source.value` + `source.value_reported` |

Every 1.0.0 and 1.1.0 report is a valid 1.2.0 report. Providers should vendor a version-pinned copy of
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
  "schema_version": "1.2.0",
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
      "source": {"file": "results/results.json", "locator": {".": {"pointer": "/n_rows"}}, "value": 2},
      "details": ["claimed 3 vs source 2"],
      "provider_status": {"name": "VALUE_MISMATCH", "code": 21},
      "graph": {
        "nodes": [
          {"id": "f1", "kind": "input", "label": "data/input.csv", "hash": "2a2b…"},
          {"id": "p1", "kind": "process", "label": "run 2026-11-18 19:38"},
          {"id": "f2", "kind": "output", "label": "results/results.json", "hash": "2c38…",
           "failure": {"kind": "mismatched", "detail": "2 in source vs 3 stated"}},
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

### Where the evidence broke (1.1.0)

A provider may mark a graph node with `failure: {kind, detail}` to show a
reviewer **where** a `not_supported` claim's evidence broke. `kind` is a
short lowercase token. The recommended ones are:

| kind | label shown | meaning |
|---|---|---|
| `changed` | ⚠ CHANGED | the node's content differs from what the recorded computation (or registration) saw |
| `missing` | ⚠ MISSING | the node is absent |
| `mismatched` | ⚠ MISMATCHED | the node holds a value other than the claim states |

Any other token (e.g. `failed`) is accepted and shown verbatim, so a later
1.x can add kinds without breaking 1.1 consumers. `detail` is one optional
plain-language line. Omitting `failure` (or `null`) means the provider
marks nothing on that node; it does not claim the node is fine.

The graph page draws a failing node with a thick dash-dot outline that no
other node uses, a colour-blind-safe vermillion, **and** a `⚠ KIND` text
line, so colour is never the only cue. It also lists the failing nodes in
words above the graph. `review.json` carries them per claim as
`failing_nodes` and `review.txt` prints `evidence broke at: …` lines.

### The value read at the source (1.2.0)

`source.value` is the value the provider read at the locator, any JSON type.
Omit the key when the provider did not read a value (no locator, unreadable
source); `null` means the source holds `null`. The paper's evidence panel and
the graph page then show the stated value beside the source value and say in
words when they differ. Without it the panel says the source value was not
reported by the provider; the reason line still explains the state.

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
marked by its state. Hovering a mark shows the reason. Selecting it (click,
tap, or Enter) opens the claim's **evidence panel** in place: state and reason,
stated vs source value, source and locator, where the evidence broke, and the
minimal evidence graph drawn inline (the graph page's mermaid source, failing
nodes marked the same way). Selecting a graph node shows its file, hash, run
and failure mark. The panel steps to the previous/next claim or the next claim
needing inspection and links to the full graph page. A **claims navigator**
lists the claims needing inspection first; `paper.html#claim-<id>` opens a
claim directly, and back/forward step through the claims opened. Esc closes
the panel. The page works from `file://` (classic scripts, data embedded), and
without JavaScript each mark still links to its graph page. `claims.html` opens with the **Needs
inspection** list, followed by the supported claims. `review.json` and
`review.txt` hold the review packet. MCP tools
`live_paper_evidence_review` and `live_paper_evidence_claim` serve the same
packet to agents. Every human view and the machine adapter are rendered from
one review packet, so they cannot disagree. A test enforces this.

## Review packet (what a reviewer reads)

`scitex-live-paper.review-packet` 1.2.0 is the evidence report re-ordered for
review: `needs_inspection` (ordered as above) and `supported`. Each entry adds
`label`, `symbol`, `needs_inspection`, `graph_url` (the claim's page in the
rendered site), and (1.1.0) `failing_nodes`: one
`{id, kind, label, failure, failure_label, detail}` per marked graph node,
in graph order (empty when none is marked). Each entry's `source` carries
(1.2.0) `value` and `value_reported` (whether the report gave a value). The packet also includes `scope`, `states` (state to label),
`counts`, and `provider`.

The packet's JSON Schema (draft 2020-12, `$id`
`https://scitex.ai/schemas/scitex-live-paper/review-packet/1.2.0`) is
self-contained (no external `$ref`), so a consumer can vendor a copy pinned by
commit and validate packets offline. The test suite validates packets built
from the reference provider against it.

## Known providers (examples only)

- scitex-clew ships an adapter that maps its claim verification and per-claim
  provenance slice to this contract. It is documented in the scitex-clew
  repository.

## Reading evidence from another application

The same mounted Live Paper instance serves the human viewer and external clients.
Send `GET review.json` for the versioned review packet, with unresolved registered
claims first. Send `GET claim.json?claim_id=<id>` for one packet entry with its
source locator, graph, and failure reasons. The response includes the packet
`schema`, `schema_version`, and a `claim` object. An omitted ID returns 400 and an
unknown ID returns 404. Use the host's authorized project and revision selectors
when requesting either URL.

Local clients can generate the packet through `scitex-live-paper export-review`
or `scitex_live_paper.evidence.build_review_packet`. The browser, CLI, and HTTP
API use the same claim entries and provider states. A provider's supported state
describes the recorded trace. Authors own the claim wording and source selection.

### Files recorded in a claim graph

A Clew process node may carry a provider extension, `script`, with `file`
(project-relative path) and `hash` (recorded script digest). Input and output
nodes use their existing path label and hash. Clew sets `author_registered: true`
only when the recorded file hash matches a verified pin in the project's source
manifest. Live Paper marks it as **Author-registered source**. To preview a
file the authorized host can still read, send
`GET preview.json?claim_id=<id>&node_id=<graph-node-id>`.
The response gives the recorded file, stored size, and hash. Its `kind` can be
`text`, `image`, `archive`, or `metadata`. Gzip files return metadata.
ZIP and uncompressed TAR files can be listed or browsed with a returned
integer `member` ID. Small UTF-8, PNG, and JPEG content uses the same file
preview rules inside supported archives. Preview limits apply to the
original bytes and to archive members. A current file that differs from the recorded digest
returns 409. An unavailable file leaves the inspected graph usable.

Python clients can generate the same bounded preview from bytes without a web
server. Callers resolve storage permissions and check the recorded digest
before passing the bytes to this library. Web clients can use the mounted
endpoint to perform those checks through the host.

```python
from scitex_live_paper.evidence.preview import preview_byte_limit, preview_file

name = "inputs/archive.zip"
with open(name, "rb") as source:
    content = source.read(preview_byte_limit(name) + 1)

listing = preview_file(name, content)
if listing["kind"] == "archive" and listing["members"]:
    first = preview_file(name, content, member=listing["members"][0]["id"])
```

`PreviewError.code` lets clients handle a size limit, unavailable member, or
invalid window without parsing the message.

### Citation marks in the PDF reader

Live Paper matches Writer's named PDF citation destinations to Clew verdicts by
BibTeX key. The same verdict colors the inline link and its bibliography entry.
The viewer treats a missing verdict as unknown.

To package a verification run, pass the final PDF and the per-key output of
`scitex_clew.verify_citations` to
`scitex_live_paper.evidence.citations.citation_verification`. Save the returned
object as `citation-verification.json` next to the bundle's `manuscript.pdf`.
The reader checks the PDF digest before applying the verdicts. Optional
`resolver_source` and `provenance` strings carry Scholar's reported attribution.
An optional `claim_id` points to an existing claim-specific Clew retrieval
graph. Include it only when that graph traces the same citation.

A sentence uses Clew's existing `text` claim type. An incoming edge to the
claim node can carry `"relation": "author_interpretation"` when the author
uses the result as the basis for an interpretation. Claims that can be
compared directly to recorded results can use the same type without that
edge label. Live Paper marks the interpreted claim with a pen and the label
**Author interpretation**. The verification state describes the linked trace.


## Manuscript HTML and statistics previews

The hosted reader accepts a UTF-8 `manuscript-html.json` sidecar with schema
`scitex-live-paper.manuscript-html/v1`, the compiled manuscript in `html`,
and the corresponding PDF's full `pdf_sha256`. Use a self-contained HTML
article with links of the form `#lp-claim-<id>` for registered claims. Live
Paper checks the PDF binding, sanitizes the markup, and derives navigation
from the article headings.

On file preview, Live Paper checks the evidence node's recorded file hash
before passing recognized JSON to the optional SciTeX Stats preview provider.
The provider supplies the reported quantities and APA formatting. Plot
previews use image files recorded in the same claim graph.
