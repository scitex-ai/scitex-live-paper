# Monday looks-only mock (static demo for the Monday meeting)
<!-- open in any browser, no server: -->
<!--   xdg-open docs/demo/monday-mock.html            # linux -->
<!--   open docs/demo/monday-mock.html                # mac -->

`monday-mock.html` is a single-file, zero-dependency, looks-only mock of
the Live Paper viewer: styled paper sheet, three claim anchors in the clew
palette (verified green / suspect amber / registered gray) with pure-CSS
hover popups, an inline-SVG provenance mini-graph per sourced claim, a
labeled figure placeholder, and the claims sidebar.

Claim data is hand-baked from `tests/scitex_live_paper/fixtures/bundle-accepted/`:

- `claim_a1b2c3d4e5f6` — verified — "Fig 1 shows p<0.05" (anchor p.3)
- `claim_f6e5d4c3b2a1` — suspect — "p = 0.003" (anchor p.5)
- `claim_999888777666` — registered, unsourced — "n = 15"
- DOI `10.7554/eLife.99999` (eLife, accepted 2026-06-01) from `state.yaml`

Status: **looks-only, NOT product UI.** The real viewer is served by
`scitex-live-paper serve` (SDK workspace shell) and the static renderer
(`scitex_live_paper._renderer`). The ports/events API serves the same
popup content dynamically; this layout matches that contract so visuals
carry over. The leaf app is live at `/apps/live-paper/` (0.2.x) — this
mock is kept as the Monday-meeting record.
