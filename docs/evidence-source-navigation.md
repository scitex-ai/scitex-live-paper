# Preview the script behind a PDF claim

**Status** Proposed

The first release answers one question: **Where did this figure or value come from?** Hover over a claim rectangle to see the Clew graph. Move onto the script node for an inline code preview, or onto an input for a sample of the recorded data. Click the rectangle to pin the popup, or tap to open it on a touch screen. The feed still works for browsing the paper.

Use one panel as the reader drills down. Keep the claim label and a compact Clew graph visible. Hovering or focusing a graph node shows its contents in the same panel. For inputs, show the recorded files and preview one immediately. Give readers a format-appropriate sample for large files, with the full file available through project tools. Semantic Reader's citation cards show the entry point from a paper. VS Code's Peek Definition shows how to inspect the next layer in place. [Semantic Reader research](https://arxiv.org/abs/2303.14334) · [VS Code Peek](https://code.visualstudio.com/docs/editing/editingevolved#_peek)

## Three package responsibilities

- **Clew** identifies the producing run and supplies one optional script record on its process node. That record carries the run ID, script name, recorded hash, and Clew's icon and color roles. The same cues can appear on the corresponding node in the full graph. [Clew graph projection](https://github.com/scitex-ai/scitex-clew/blob/57ad743/src/scitex_clew/_evidence_provider/_graph.py)
- **Live Paper** displays the existing claim status, one script row, and the full-graph link. It loads the preview on demand. The existing graph handles claims with multiple or unclear producers and reports without script information. [Claim DAG endpoint](../src/scitex_live_paper/_django/handlers/dag.py)
- **Rich PDF** anchors the popup to the existing overlay button and keeps it open while the pointer moves from the rectangle into the popup. Click, tap, or keyboard activation pins it. Escape dismisses it and returns focus to the rectangle. A host content hook supplies what appears inside. [Rich PDF provider](https://github.com/scitex-ai/scitex-rich-pdf/blob/v0.1.1/src/scitex_rich_pdf/frontend/pdf-provider.js)

## One preview request

After a brief hover or keyboard focus on the script row, the browser requests the script for the claim in the current project and evidence revision. Tapping the row uses the same request. Ignore a response if the reader has already moved to another claim or closed the popup. On the server, Live Paper validates the revision and uses a host-supplied, project-scoped lookup for Clew's recorded run. The claim determines the run and script. The host authorizes the file and the existing bounded reader opens it beneath the authorized root.

Compare the bytes to the recorded hash before showing the script as plain text labeled **Matches recorded hash**. A changed, missing, or unauthorized script gets an unavailable message. Exported reports can still show their graph and any recorded script label. They offer a preview only when the host has a resolver for that evidence. [Evidence request](../src/scitex_live_paper/_django/_evidence_request.py) · [Resource reader](../src/scitex_live_paper/_django/_evidence_files.py)

Use the same file selector and preview for inputs and outputs. Show full content for small text files. For supported binary data, preview images, rows, or array slices with the file's shape and type. Show a small initial window for large files, with record ranges and the total when known. Load further windows on demand when the format supports it. For supported archives, show a bounded member list and decode a selected member under size and time limits. Unsupported formats can show the recorded identity, size, hash, and authorized original file. Verify the recorded archive bytes before identifying a preview as evidence.

The same lookup can offer **Open current file** and **Open containing folder** when Hub can resolve the recorded path in the authorized project. A working copy may change after the run, so the file action keeps its current-version label even when the inline preview matches. A future local desktop host could handle these actions through the OS file viewer, such as Explorer or Finder. When Clew has only a text label or database record, retain the recorded details and graph. [Hub file viewer](https://github.com/scitex-ai/scitex-hub/blob/3d700fcd6/apps/infra/project_app/views/directory_views/file_view.py)

Offer **Run in Hub** as a secondary script action when the host confirms both project execution permission and a ready runtime. The user chooses the script revision and starts the job explicitly. Hub's Console owns execution and returns a new run ID. Show the new output separately from the run that supported the published claim. [Hub Console](https://github.com/scitex-ai/scitex-hub/blob/3d700fcd6/apps/workspace/console_app/urls/pages.py)

## First acceptance check

Use a FigRecipe output from a recorded run in a Writer-compiled PDF. Hover over its figure rectangle, move into the popup, and hover over the script to preview it. Verify keyboard and touch access. Confirm that the file link opens the same path in Hub. Edit the script and verify that the popup reports the mismatch while the current file remains openable. Check a metadata-only source, a legacy report, and a Scholar document-only PDF.

Further source types and richer run details can build on the first working path. The [ecosystem audit](research/evidence-ecosystem-audit.md) documents the wider package relationships. The [reader integration rules](rich-pdf-provider.md#reader-integration-rules) cover shared ownership, revision binding, and host authorization.

Use JATS figure and reference IDs when a publisher already supplies JATS XML. PubMed Central prefers JATS for full-text article submissions. Stable manuscript IDs give an HTML reader a way to find the same figure or citation across layouts. Live Paper can map those IDs to Clew claims and render the evidence graph from the existing Clew report. The graph connects a claim to its output, producing run, and recorded inputs. Readers can follow input nodes to a hash-checked data preview and open the full file through the authorized project. Keep PDF rectangles tied to the exact PDF revision. [PMC submission specifications](https://pmc.ncbi.nlm.nih.gov/pub/filespec/)
