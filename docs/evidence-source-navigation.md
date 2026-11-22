# Preview the script behind a PDF claim

**Status** Proposed

The first release answers one question: **Which script produced this figure or value?** Hover over a claim rectangle to see the script name and recorded run ID. Hover over the script row for a short inline preview. Click the rectangle to pin the popup, or tap to open it on a touch screen. **Open current file** opens the project file when available. **Open full evidence graph** lets the reader inspect the chain. The feed still works for browsing the paper.

Use one panel as the reader drills down. The claim summary leads to the script preview, and the preview can expose the recorded run ID and graph link. Keep the claim label visible so the reader can trace a detail back to its place in the paper. Semantic Reader's citation cards show the entry point from a paper. VS Code's Peek Definition shows how to inspect the next layer in place. [Semantic Reader research](https://arxiv.org/abs/2303.14334) · [VS Code Peek](https://code.visualstudio.com/docs/editing/editingevolved#_peek)

## Three package responsibilities

- **Clew** identifies the producing run and supplies one optional script record on its process node. That record carries the run ID, script name, recorded hash, and Clew's icon and color roles. The same cues can appear on the corresponding node in the full graph. [Clew graph projection](https://github.com/scitex-ai/scitex-clew/blob/57ad743/src/scitex_clew/_evidence_provider/_graph.py)
- **Live Paper** displays the existing claim status, one script row, and the full-graph link. It loads the preview on demand. The existing graph handles claims with multiple or unclear producers and reports without script information. [Claim DAG endpoint](../src/scitex_live_paper/_django/handlers/dag.py)
- **Rich PDF** anchors the popup to the existing overlay button and keeps it open while the pointer moves from the rectangle into the popup. Click, tap, or keyboard activation pins it. Escape dismisses it and returns focus to the rectangle. A host content hook supplies what appears inside. [Rich PDF provider](https://github.com/scitex-ai/scitex-rich-pdf/blob/v0.1.1/src/scitex_rich_pdf/frontend/pdf-provider.js)

## One preview request

After a brief hover or keyboard focus on the script row, the browser requests the script for the claim in the current project and evidence revision. Tapping the row uses the same request. Ignore a response if the reader has already moved to another claim or closed the popup. On the server, Live Paper validates the revision and uses a host-supplied, project-scoped lookup for Clew's recorded run. The claim determines the run and script. The host authorizes the file and the existing bounded reader opens it beneath the authorized root.

Compare the bytes to the recorded hash before showing a plain-text excerpt labeled **Matches recorded hash**. A changed, missing, or unauthorized script gets an unavailable message. Exported reports can still show their graph and any recorded script label. They offer a preview only when the host has a resolver for that evidence. [Evidence request](../src/scitex_live_paper/_django/_evidence_request.py) · [Resource reader](../src/scitex_live_paper/_django/_evidence_files.py)

The same lookup can return an **Open current file** link when Hub can resolve the recorded path to a readable file in the authorized project. Hub builds the link using its existing project file viewer. A working copy may change after the run, so the link stays labeled **Open current file** even when the inline preview matches. When Clew has only a text label or database record, retain the recorded details and graph. [Hub file viewer](https://github.com/scitex-ai/scitex-hub/blob/3d700fcd6/apps/infra/project_app/views/directory_views/file_view.py)

## First acceptance check

Use a FigRecipe output from a recorded run in a Writer-compiled PDF. Hover over its figure rectangle, move into the popup, and hover over the script to preview it. Verify keyboard and touch access. Confirm that the file link opens the same path in Hub. Edit the script and verify that the popup reports the mismatch while the current file remains openable. Check a metadata-only source, a legacy report, and a Scholar document-only PDF.

Further source types and richer run details can build on the first working path. The [ecosystem audit](research/evidence-ecosystem-audit.md) documents the wider package relationships. The [reader integration rules](rich-pdf-provider.md#reader-integration-rules) cover shared ownership, revision binding, and host authorization.

Use JATS figure and reference IDs when a publisher already supplies JATS XML. PubMed Central prefers JATS for full-text article submissions. Stable manuscript IDs give an HTML reader a way to find the same figure or citation across layouts. Live Paper can map those IDs to Clew claims and render the evidence graph from the existing Clew report. The graph connects a claim to its output, producing run, and recorded inputs. Readers can follow input nodes to a hash-checked data preview and open the full file through the authorized project. Keep PDF rectangles tied to the exact PDF revision. [PMC submission specifications](https://pmc.ncbi.nlm.nih.gov/pub/filespec/)
