# M2 re-verify — operator runbook

How to bootstrap, exercise, and embed the M2 live re-verify path
end-to-end. M1 is the read-only renderer; M2 is the *live* surface:
the SPA's Re-verify (and Re-verify-all) button asks the installed
**evidence provider** for the current evidence state of each registered
claim, through the provider-neutral contract in
[`docs/evidence-provider-contract.md`](../evidence-provider-contract.md),
and updates the badge. live-paper imports and depends on no provider.

---

## 1. Install

```bash
pip install 'scitex-live-paper[django]'
# plus any package that implements the evidence-provider contract
```

- Live re-verify needs an evidence provider installed beside live-paper
  (an entry point in the `scitex.livepaper.renderers` group with
  `port = "evidence"`). Without one, the endpoints stay reachable but
  degrade gracefully: every per-claim response carries
  `"fallback": true`, `"status": "unassessed"` and the reason
  `"no evidence provider is installed"` (no 500s).
- `[django]` is needed for the live Django mount (`serve` CLI + hub
  plugin). The read-only CLI render path works without Django.

Configuration (environment, read per request):

| Variable | Default | Meaning |
|---|---|---|
| `SCITEX_LIVE_PAPER_EVIDENCE_PROVIDER` | the single installed provider | entry-point name of the provider to ask |
| `SCITEX_LIVE_PAPER_EVIDENCE_ROOT` | the bundle root | project root handed to the provider |

The provider assesses the CURRENT on-disk state of that project.
`pinned_commit` is metadata only: it is echoed as `verified_against`
and never passed to the provider. The host/deployment that wants a
specific revision assessed prepares that revision on disk before
serving; these handlers never mutate the working tree.

---

## 2. The four M2 surfaces

Every M2 endpoint mounts under the same prefix as the rest of
`scitex_live_paper._django.urls` — standalone mounts at `"/"`;
hub-mounted under `apps/live-paper/<paper_id>/` (or whatever your
`mount(resolver=...)` mount prefix is).

| Endpoint              | Method | Body                                  | Returns                      |
|-----------------------|--------|---------------------------------------|------------------------------|
| `api/claim/verify`    | POST   | `{"claim_id": "...", "pinned_commit"?: "..."}` | Single verify envelope        |
| `api/claims/verify`   | POST   | `{"claim_ids"?: ["..."], "pinned_commit"?: "..."}` | Bulk: `{ok, count, results[]}` |
| `api/claims`          | GET    | —                                     | Full claim list + `re_verify_enabled` |
| `api/bundle-info`     | GET    | —                                     | Bundle summary + `paper_state` |

### Single verify

```bash
curl -X POST -H 'Content-Type: application/json' \
     -d '{"claim_id":"claim_a1b2c3d4e5f6"}' \
     http://localhost:8765/api/claim/verify
```

Response (provider installed, claim assessed):

```json
{
  "ok": true,
  "claim_id": "claim_a1b2c3d4e5f6",
  "verified_against": "deadbeefcafef00d12345678",
  "status": "not_supported",
  "state": "not_supported",
  "label": "Not supported",
  "reason": "value in source differs: 2 in source vs 3 stated",
  "verified_at": null,
  "details": { "...": "the claim's evidence-report entry, incl. its graph" }
}
```

`status` is one of the four evidence states `supported`,
`not_supported`, `not_checkable`, `no_evidence_graph`. `ok` means the
claim was assessed, not that it is supported. A claim the provider does
not report comes back `ok: false`, `status: "not_found"`.

Response (no provider installed):

```json
{
  "ok": false,
  "claim_id": "claim_a1b2c3d4e5f6",
  "status": "unassessed",
  "reason": "no evidence provider is installed",
  "fallback": true
}
```

`pinned_commit` is optional in the body — falls back to
`bundle.paper_state.pinned_commit` (loaded from `state.yaml`).

### Bulk verify

```bash
curl -X POST -H 'Content-Type: application/json' -d '{}' \
     http://localhost:8765/api/claims/verify
```

Empty body = verify *every* claim. Or filter:

```bash
curl -X POST -H 'Content-Type: application/json' \
     -d '{"claim_ids":["claim_a","claim_b"]}' \
     http://localhost:8765/api/claims/verify
```

Response:

```json
{
  "ok": false,
  "verified_against": "deadbeef...",
  "count": 3,
  "results": [
    { "ok": true,  "claim_id": "claim_a", "status": "supported", ... },
    { "ok": false, "claim_id": "claim_b", "status": "not_found", ... },
    { "ok": false, "claim_id": "claim_c", "status": "unknown", "reason": "claim_id not found in bundle" }
  ]
}
```

The bulk endpoint asks the provider ONCE, for every target claim.
Top-level `ok` is `true` iff *every* per-claim result is `ok: true`.
Per-claim failures (unknown claim id, claim missing from the report,
fallback) stay in the array, and a provider failure becomes an `error`
on every result — the sweep never 500s.

---

## 3. SPA UI gates

The `re_verify_enabled` flag drives Re-verify button visibility. It
comes from `PaperState`:

| `paper_state.stage`           | `re_verify_enabled` | Why                                     |
|-------------------------------|--------------------|-----------------------------------------|
| `"draft"` / `"preprint"` / `"in_review"` | `false`         | No commit pinned yet to verify against  |
| `"accepted"` / `"published"`  | depends             | True iff `pinned_commit` is set         |

So a preprint bundle's SPA sidebar shows claim rows but no buttons; an
accepted bundle with a `state.yaml` carrying `pinned_commit` shows the
per-claim button + the sticky "Re-verify all" at the top. The badge
shows the returned `status` verbatim and the `reason` as its tooltip;
each evidence state has its own colour-blind-safe hue.

---

## 4. Local end-to-end (standalone server)

```bash
# 1. Set up a bundle. Real ones live under tests/scitex_live_paper/fixtures/.
export BUNDLE_DIR=$PWD/tests/scitex_live_paper/fixtures/bundle-accepted

# 2. Boot the server (optionally pointing the provider at the project).
SCITEX_LIVE_PAPER_EVIDENCE_ROOT=/path/to/project \
  scitex-live-paper serve "$BUNDLE_DIR" --port 8765

# 3. In another terminal, hit the endpoints.
curl -s http://localhost:8765/api/bundle-info | jq .paper_state
curl -s http://localhost:8765/api/claims      | jq '{re_verify_enabled, count: .claim_count}'
curl -s -X POST -H 'Content-Type: application/json' -d '{}' \
     http://localhost:8765/api/claims/verify | jq .

# 4. In the browser:
xdg-open http://localhost:8765/    # full page with chrome
xdg-open 'http://localhost:8765/?embed=1'  # chromeless (hub iframe variant)
```

With no evidence provider installed, step 3's bulk verify returns one
`"fallback": true`, `"status": "unassessed"` entry per claim — that's
the documented contract.

---

## 5. Hub mount (multi-tenant)

Hub plugs the live-paper app under `apps/live-paper/<paper_id>/`. The
hub-side resolver translates `paper_id` + `request.user.current_project`
into a `BundleContext`; the M2 endpoints then read the right bundle
without any per-handler branching:

```python
# hub-side: apps/workspace/live_paper_app/urls.py
from django.urls import include, path
from scitex_live_paper import (
    mount, BundleContext, BundleSource, PaperState, RendererOptions,
)

def hub_resolver(request, paper_id, **url_kwargs) -> BundleContext:
    project = request.user.current_project
    return BundleContext(
        source=BundleSource.from_resolver(
            lambda: load_paper(paper_id, project.id),
        ),
        paper_state=PaperState.from_db(paper_id),
        api_base=request.path.rstrip("/").rsplit("/", 1)[0] + "/api/",
        options=RendererOptions(embed_mode=True),
    )

urlpatterns = [
    path("apps/live-paper/<paper_id>/",
         include(mount(resolver=hub_resolver))),
]
```

Hub side already targets these public names (PR #27 onwards); the
resolver flip is on hub's follow-up PR after PR #265.

---

## 6. Graceful-degradation cheatsheet

| Scenario                              | Endpoint behaviour                          | SPA badge   |
|---------------------------------------|---------------------------------------------|-------------|
| No evidence provider installed        | 200 + `fallback: true` + "no evidence provider is installed" | "unassessed" (grey) |
| Configured provider name not installed | 200 + `fallback: true` + reason naming it  | "unassessed" |
| Provider raises / breaks the contract | 500 (single) / per-result error (bulk)      | "error" (red) |
| Claim absent from the provider report | 200 + `ok: false`, `status: "not_found"`    | "not_found" (grey) |
| Bundle has no `pinned_commit`         | 400 with clear message                      | (button is hidden — `re_verify_enabled=false`) |
| Network error in the SPA              | (client-side) badge → "error", button retries | "error"   |

The badge stays meaningful in every scenario — no 500-then-???
gap for the operator to puzzle over.

---

## 7. Ownership boundary

This package **does not** define or extend the claim model, and it does
not compute evidence. Upstream owns:

- the `Claim` shape (mirrored in `scitex_live_paper.bundle.Claim`) and
  the status strings carried in `claims.json` — owned by the claim
  registry that produced `claims.json`;
- the evidence state of each claim — computed by the evidence provider
  and handed over through the evidence-provider contract.

The live-paper-owned bits are render-time only:

- `PaperState` (lifecycle stage, journal, DOI, pinned commit)
- `BundleSource` / `BundleContext` / `RendererOptions` (render-time options)
- The HTTP envelope (`{ok, claim_id, status, ...}`)
- The provider-neutral evidence contract (`scitex_live_paper.evidence`)

If you need a new claim field, open the upstream issue against the claim
registry — never invent fields here.
