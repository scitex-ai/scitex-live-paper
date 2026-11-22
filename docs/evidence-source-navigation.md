# Preview the script behind a PDF claim

**Status** The inline reader MVP is implemented in the package branches. The sections below describe additional source types and actions.

The first release answers one question: **Where did this figure or value come from?** Hover over a highlighted value or the edge marker on a figure to see the Clew graph. Move onto the script node for an inline code preview, or onto an input for a sample of the recorded data. Activate the mark to pin the popup, or tap to open it on a touch screen. The feed still works for browsing the paper.

Use one panel as the reader drills down. Keep the claim label and a compact Clew graph visible. Hovering or focusing a graph node shows its contents in the same panel. For inputs, show the recorded files and preview one immediately. Give readers a format-appropriate sample for large files, with the full file available through project tools. Semantic Reader's citation cards show the entry point from a paper. VS Code's Peek Definition shows how to inspect the next layer in place. [Semantic Reader research](https://arxiv.org/abs/2303.14334) · [VS Code Peek](https://code.visualstudio.com/docs/editing/editingevolved#_peek)

## Reader components and package responsibilities

Rich PDF offers a highlight for text and a small edge marker for figures.
Live Paper uses its preview port to draw the claim graph beside either mark.
The mounted HTTP API uses the same authorized graph for the reader and for
external programs. `preview.json?claim_id=…&node_id=…` selects a recorded node
within that claim. The server checks its file hash and previews small text,
PNG, and JPEG files from the authorized resource root.

Clew publishes an optional `script` record on its process nodes with the
recorded relative file name and hash. The process ID and relationships stay
stable. Older exports can still show their graph. Live Paper renders the
recorded kind and source metadata regardless of whether the bytes are
available. The SDK remains responsible for PDF rendering and page geometry.

The next features reuse these boundaries. Cross-page relationships need
explicit manuscript relationship records. Opening a current file or running
a script uses capabilities supplied and authorized by the host.

## Repository files as the evidence surface

Authors register claims. The Clew graph and the authorized project repository
supply the file identities and hashes. Live Paper selects a format reader from
the recorded bytes and file type and generates previews at request time. The
viewer uses the filename from the graph. It accepts no per-article thumbnail
or display-name manifest. An unknown format still has a file identity.

Gzip files show their original name, size, and recorded hash. The viewer
displays native image files and known text formats directly. ZIP and
uncompressed TAR views list stored member names and let readers open one
bounded member. Members remain in the archive.

The PDF and browser views point back to the same repository. The mounted host
owns file navigation and execution authorization. A new run has its own identity
and can inform a new paper revision.

## Details for the selected item

Use **Selection** for the current manuscript mark and **All claims** to browse
the paper. Keep the graph and the associated source, statistical result, or
citation record under the current selection. Use **Open full evidence graph**
for a larger view of that same graph. Add a paper-wide tab only when there is
paper-wide content to browse.

| Selected item | Details | Record owner |
| --- | --- | --- |
| Claim or figure | Calculation trace, verification state, and drill-down into recorded inputs and outputs | Clew evidence report |
| Citation | Bibliography record, identifier, resolver, verification state, and available citation provenance | Scholar verification record, with optional Clew trace |
| Statistical result | Full result for the selected analysis, including sample sizes, estimates, effect sizes, intervals, assumptions, and corrections whenever the analysis reports them | Stats bundle, linked through the recorded Clew output |

Connect a Writer citation key to the Scholar record for that key. Show the
publication link and the metadata resolver as separate fields. A DOI link can
coexist with a Scholar record resolved through another service. Clew can
ingest Scholar's existing `scitex-clew/citations/v1` artifact when configured.
Render citation provenance as citation evidence, with its own status, so the
calculation verification totals retain their meaning.

Connect a statistical selection to a versioned, hash-checked Stats artifact
using the graph's output identity and selector. Use the Stats bundle API and
retain the complete machine-readable result alongside the human-readable
sections. A plain number or an arbitrary JSON file with similar keys carries
no Stats type by inference. Generic archives retain the regular file preview
behavior. Missing package records leave the graph or native citation link
available.

Live Paper owns selection, layout, and navigation. Each producing package
owns its fields and their interpretation. The SDK supplies shared controls
and the PDF layer. Expose the same authorized, revision-bound records to the
pane and to programmatic readers.

## Relationships on the paper

When a text claim and its supporting statistic both have anchors in the same PDF revision, hover or focus either one to highlight the other and draw a single labeled connector. Point a support arrow from the recorded result toward the statement it supports. Live Paper chooses the label and visibility from the relationship, and Rich PDF draws the connector from the existing SDK page geometry. Keep the rest of the page clear. If the result is on another page, offer its label and a jump to that page. If it lives in a separate artifact, open it in the evidence popup.

Use a recorded relationship or an explicit author annotation. Equal numbers or a shared producing run alone carry no support verdict. In the laptop demo, the line relates the two occurrences of the same reported accuracy. The Clew graph continues to trace the actual supporting output and inputs. [Clew graph projection](https://github.com/scitex-ai/scitex-clew/blob/57ad743/src/scitex_clew/_evidence_provider/_graph.py)

## Standalone and hosted use

Use the same Live Paper reader with a standalone local project, a self-hosted Hub, or SciTeX Cloud. Use the SDK's mount context and mount-aware browser URLs for the reader's own endpoints. The host supplies the project and file access. For evidence reads, use `scitex_sdk.host.project_access(request, remember=False)` so opening a resource in one paper preserves the active project in other tabs. Standalone uses the configured local provider. Hub uses the requesting user's project permissions. [SDK mounting contract](https://github.com/scitex-ai/scitex-sdk/blob/7df1114/src/scitex_sdk/ui/_skills/scitex-ui/41_dual-mode-mounting.md) · [SDK project access](https://github.com/scitex-ai/scitex-sdk/blob/7df1114/src/scitex_sdk/host.py)

File and folder navigation follow the host. Hub can open its browser workspace, and a future local desktop host can reveal a file through Explorer or Finder. Execution needs its own host capability and a ready runtime. The SDK project-access API supplies project identity and storage access, so launching a job requires a separate grant. A mounted reader and a standalone reader should pass the same inline evidence checks. [SDK standalone entry point](https://github.com/scitex-ai/scitex-sdk/blob/7df1114/src/scitex_sdk/app/_skills/scitex-app/05_standalone.md)

## One preview request

After a brief hover or keyboard focus on the script row, the browser requests the script for the claim in the current project and evidence revision. Tapping the row uses the same request. Ignore a response if the reader has already moved to another claim or closed the popup. On the server, Live Paper validates the revision and uses a host-supplied, project-scoped lookup for Clew's recorded run. The claim determines the run and script. The host authorizes the file and the existing bounded reader opens it beneath the authorized root.

Compare the bytes to the recorded hash before showing the script as plain text labeled **Matches recorded hash**. A changed, missing, or unauthorized script gets an unavailable message. Exported reports can still show their graph and any recorded script label. They offer a preview only when the host has a resolver for that evidence. [Evidence request](../src/scitex_live_paper/_django/_evidence_request.py) · [Resource reader](../src/scitex_live_paper/_django/_evidence_files.py)

Use the same file selector and preview for inputs and outputs. Show full content for small text files. For supported binary data, preview images, rows, or array slices with the file's shape and type. Show a small initial window for large files, with record ranges and the total when known. Load further windows on demand when the format supports it. For supported archives, show a bounded member list and decode a selected member under size and time limits. Unsupported formats can show the recorded identity, size, hash, and authorized original file. Verify the recorded archive bytes before identifying a preview as evidence.

The same lookup can offer **Open current file** and **Open containing folder** when the host can resolve the recorded path in the authorized project. A working copy may change after the run, so the file action keeps its current-version label even when the inline preview matches. When Clew has only a text label or database record, retain the recorded details and graph. [Hub file viewer](https://github.com/scitex-ai/scitex-hub/blob/3d700fcd6/apps/infra/project_app/views/directory_views/file_view.py)

Offer **Run script** as a secondary action when the host confirms both project execution permission and a ready runtime. The user chooses the script revision and starts the job explicitly. In Hub, Console owns execution and returns a new run ID. Show the new output separately from the run that supported the published claim. [Hub Console](https://github.com/scitex-ai/scitex-hub/blob/3d700fcd6/apps/workspace/console_app/urls/pages.py)

## First acceptance check

Use a FigRecipe output from a recorded run in a Writer-compiled PDF. Hover over its figure edge marker, move into the popup, and hover over the script to preview it. Verify keyboard and touch access. Confirm that the file link opens the same path in Hub. Edit the script and verify that the popup reports the mismatch while the current file remains openable. Check a metadata-only source, a legacy report, and a Scholar document-only PDF.

Further source types and richer run details can build on the first working path. The [ecosystem audit](research/evidence-ecosystem-audit.md) documents the wider package relationships. The [reader integration rules](rich-pdf-provider.md#reader-integration-rules) cover shared ownership, revision binding, and host authorization.

Use JATS figure and reference IDs when a publisher already supplies JATS XML. PubMed Central prefers JATS for full-text article submissions. Stable manuscript IDs give an HTML reader a way to find the same figure or citation across layouts. Live Paper can map those IDs to Clew claims and render the evidence graph from the existing Clew report. The graph connects a claim to its output, producing run, and recorded inputs. Readers can follow input nodes to a hash-checked data preview and open the full file through the authorized project. Keep PDF rectangles tied to the exact PDF revision. [PMC submission specifications](https://pmc.ncbi.nlm.nih.gov/pub/filespec/)
