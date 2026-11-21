# Preview the script behind a PDF claim

**Status** Proposed

The first release answers one question: **Which script produced this figure or value?** Open a claim rectangle to see the script name and recorded run ID. Preview the script in the popup or open it in the project file viewer when available. Use **Open full evidence graph** to inspect the chain. The feed still works for browsing the paper.

## Three package responsibilities

- **Clew** identifies the producing run and supplies one optional script record on its process node. That record carries the run ID, script name, recorded hash, and Clew's icon and color roles. The same cues can appear on the corresponding node in the full graph. [Clew graph projection](https://github.com/scitex-ai/scitex-clew/blob/57ad743/src/scitex_clew/_evidence_provider/_graph.py)
- **Live Paper** displays the existing claim status, one script row, and the full-graph link. It loads the preview on demand. The existing graph handles claims with multiple or unclear producers and reports without script information. [Claim DAG endpoint](../src/scitex_live_paper/_django/handlers/dag.py)
- **Rich PDF** opens and dismisses the popup beside the existing overlay button. A host content hook supplies what appears inside. Click, tap, or keyboard activation opens it. Escape closes it and returns focus to the rectangle. [Rich PDF provider](https://github.com/scitex-ai/scitex-rich-pdf/blob/v0.1.1/src/scitex_rich_pdf/frontend/pdf-provider.js)

## One preview request

The browser requests the script for the claim in the current project and evidence revision. On the server, Live Paper validates the revision and uses a host-supplied, project-scoped lookup for Clew's recorded run. The claim determines the run and script. The host authorizes the file and the existing bounded reader opens it beneath the authorized root.

Compare the bytes to the recorded hash before showing a plain-text excerpt labeled **Matches recorded hash**. A changed, missing, or unauthorized script gets an unavailable message. Exported reports can still show their graph and any recorded script label. They offer a preview only when the host has a resolver for that evidence. [Evidence request](../src/scitex_live_paper/_django/_evidence_request.py) · [Resource reader](../src/scitex_live_paper/_django/_evidence_files.py)

The same lookup can return an **Open current file** link when Hub can resolve the recorded path to a readable file in the authorized project. Hub builds the link using its existing project file viewer. A working copy may change after the run, so the link stays labeled **Open current file** even when the inline preview matches. When Clew has only a text label or database record, retain the recorded details and graph. [Hub file viewer](https://github.com/scitex-ai/scitex-hub/blob/3d700fcd6/apps/infra/project_app/views/directory_views/file_view.py)

## First acceptance check

Use a FigRecipe output from a recorded run in a Writer-compiled PDF. Open its figure rectangle, preview the matching script, and confirm that the file link opens the same path in Hub. Edit the script and verify that the popup reports the mismatch while the current file remains openable. Check a metadata-only source, a legacy report, and a Scholar document-only PDF.

Further source types, hover previews, and richer run details can build on the first working path. The [ecosystem audit](research/evidence-ecosystem-audit.md) documents the wider package relationships. The [reader integration rules](rich-pdf-provider.md#reader-integration-rules) cover shared ownership, revision binding, and host authorization.
