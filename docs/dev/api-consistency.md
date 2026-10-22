# API consistency rules (leaf scope)

`scitex-live-paper` speaks through five surfaces. They must agree:
one capability, one name, one behavior, whichever door the caller
uses. `scitex-dev` dispatches the ecosystem auditors
(`audit-cli`, `audit-mcp-tools`, `audit-python-apis`,
`audit-skills`, `audit-django`); **this file is the leaf's own
scope** — the naming and parity rules those auditors grade, plus
where each rule is enforced in-tree.

## Surfaces

| # | Surface | Entry | Contract |
|---|---------|-------|----------|
| 1 | Python | `scitex_live_paper/__init__.py` (`__all__` + PEP 562 lazy `MountResolver`) | stable import names; Django stays lazy |
| 2 | CLI | `scitex-live-paper` (`_cli/`, spec-built via `spec_command_kwargs`) | noun-verb convention; custom vocabulary in `.scitex/dev/cli-audit-dict.yaml` |
| 3 | MCP | `_mcp_server.py` (`_TOOL_FUNCS`, FastMCP `mcp`) | §6 parity: every tool projects a real Python API |
| 4 | Skills | `_skills/` leaves via `skills_list` / `skills_get` | §5 pair ships together; empty registry reported honestly, never stubbed |
| 5 | Web | `_django/handlers/HANDLERS` (`api/*` dispatcher) | registry is the single source of truth; no endpoint logic in `views.py` |

## Rules

**R1 — One capability, one name.** A capability keeps its name
across surfaces: `bundle.load` (Python) → `live_paper_bundle_load`
(MCP) → `render`/`info` (CLI verbs on the same bundle). MCP tool
names use the `live_paper_` prefix. Enforced by
`tests/scitex_live_paper/test__mcp_server.py`.

**R2 — No orphan tools, no uncovered APIs (§6).** Every MCP tool
docstring names its projection target (`Projects ...`), and every
target resolves to an importable callable. Enforced by
`test__mcp_server.py::test_tool_projects_importable_python_api`.

**R3 — Skills ship as a pair (§5).** `skills_list` without
`skills_get` (or vice versa) is a violation. The package currently
ships no `_skills/` leaves; the registry reports empty honestly.
Enforced by `test__mcp_server.py::test_skills_pair_ships_together`;
`audit-skills` skips until `_skills/` lands.

**R4 — CLI vocabulary is declared.** Tokens the noun-verb
classifier misreads are allowlisted in
`.scitex/dev/cli-audit-dict.yaml` with a why-comment
(`serve`, `info`, `hub-manifest`). New subcommands that trip §1
extend that file — never rename an established command for the
auditor. Enforced by `audit-cli` (warn-only) + `tests/smoke/test_cli_help.py`.

**R5 — Web endpoints live in the registry.** New endpoints extend
`HANDLERS` with a docstring line in the module header; `views.py`
only dispatches. `api/*` prefix; bulk verbs nest under the
resource (`api/claim/verify`, `api/claims/verify`).

**R6 — Python surface stays import-cheap.** No Django/FastMCP
import at `import scitex_live_paper` time (`MountResolver` is
PEP 562 lazy; `mcp` is `None` without the `[mcp]` extra).
Pinned by `tests/scitex_live_paper/_django/test_apps_sdk_only.py`
(SDK-only surface pins) and the import-smoke CI job.

**R7 — Docs follow the code.** README status (M1–M5), mount
path, extras, and fixture paths are pinned by
`tests/custom/test_m2_docs.py` and
`tests/custom/test_goal_docs_sync.py`. Update prose and pins
together.

## Audit map (run from the repo root)

```bash
scitex-dev ecosystem audit-project scitex-live-paper --severity error  # PS-xxx, gate
scitex-dev ecosystem audit-cli scitex-live-paper                       # §1 noun-verb (warn-only)
scitex-dev ecosystem audit-mcp-tools scitex-live-paper                 # § MCP convention
scitex-dev ecosystem audit-python-apis scitex-live-paper               # §1–§5 PA checklist
scitex-dev ecosystem audit-skills scitex-live-paper                    # SK checklist (skips: no _skills/)
```

Known environment notes (not code defects): `audit-cli` reports
"no console script" inside containers whose editable install
points at another checkout; `install-cross-package-gate` refuses
with `'scitex-live-paper' not in ECOSYSTEM` — the PS-140 gate file
is then updated by hand to the auditor's computed list (see its
header). When serving or testing a worktree here, pin it
explicitly — `PYTHONPATH=<worktree>/src` (absolute; background
shells do not inherit a foreground `export`) — and verify with
`python -c "import scitex_live_paper; print(scitex_live_paper.__file__)"`
before believing any browser or curl result. All recorded, not
worked around in code.
