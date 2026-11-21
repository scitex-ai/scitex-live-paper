# Browse Clew evidence from a PDF claim

**Status** Proposed

The first workflow is figure → source script → inline preview → run details. A reader can stay on the figure while checking which script produced it. Numeric claims use the same flow. The feed remains the place to browse claims across the paper, and the full evidence graph remains available for tracing the complete chain.

The [ecosystem audit](research/evidence-ecosystem-audit.md) traces FigRecipe, Writer, Scholar, Session, IO, Hub, and publication mounts. Follow the [reader integration rules](rich-pdf-provider.md#reader-integration-rules) when joining those surfaces.

## What the packages already provide

| Package | Existing behavior and implications |
| --- | --- |
| Clew | Run records contain `script_path` and `script_hash`. The native Clew graph already uses script labels, file icons, and status colors. The evidence provider builds a path-pruned graph whose process node currently carries a session ID as its label. It can attach the script identity from the same run record. [Run schema](https://github.com/scitex-ai/scitex-clew/blob/57ad743/src/scitex_clew/_db/_schema.py) · [Evidence graph projection](https://github.com/scitex-ai/scitex-clew/blob/57ad743/src/scitex_clew/_evidence_provider/_graph.py) · [Clew graph styling](https://github.com/scitex-ai/scitex-clew/blob/57ad743/src/scitex_clew/_viz/_mermaid_nodes.py) |
| Live Paper | Its claim DAG endpoint returns Mermaid and a list of references. The inspector already highlights a node when a reference is selected. Request-bound evidence resolution validates the report and obtains a resource root from the host. `ResourceReader` provides bounded reads of regular files beneath that root with symlink protection. [DAG handler](../src/scitex_live_paper/_django/handlers/dag.py) · [Evidence request](../src/scitex_live_paper/_django/_evidence_request.py) · [Resource reader](../src/scitex_live_paper/_django/_evidence_files.py) |
| Rich PDF | The viewer emits overlay preview and selection events and has a comment panel. It already positions overlay buttons through SDK PDF geometry. The evidence popover can reuse those buttons as anchors. [Rich PDF provider at 0.1.1](https://github.com/scitex-ai/scitex-rich-pdf/blob/v0.1.1/src/scitex_rich_pdf/frontend/pdf-provider.js) |

## What each package owns

- **Clew** supplies the evidence objects and their presentation. It defines source types, label conventions, icon identifiers, and color roles. It supplies the run or artifact identity and the actions that the recorded data supports. Reuse Clew's visual conventions across the popup and full graph. A label conveys each status or type alongside its color and icon.
- **Live Paper** owns the claim inspector, the order of sources, and the navigation from source to preview and run details. The host supplies project and resource authorization. Live Paper turns provider actions into same-origin requests, using the same inspector content in the popup and full graph.
- **Rich PDF** owns popover geometry and interaction. Add an optional host content hook to the existing overlay flow. Rich PDF places it beside the rectangle, tracks its position, and manages pinning, dismissal, and focus. The hook receives a document revision, overlay ID, and preview or pinned state. Rich PDF stays independent of evidence providers.

## Evidence contract

Extend the existing provider-neutral [evidence report contract](evidence-provider-contract.md) with an optional `resources` list on each graph node. Keep existing node kinds, edges, and verification outcomes. A process can offer both a script and a run detail action without adding an edge or changing the topology of the recorded graph. The example shows one proposed descriptor attached to a process node.

```json
{
  "id": "script-1",
  "type": "script",
  "label": "analysis.py",
  "icon": "code",
  "color_role": "script",
  "actions": ["preview_script", "open_run"],
  "recorded_sha256": "<64 lowercase hex digits>"
}
```

Resource IDs are opaque to the browser and unique within the claim snapshot. A provider associates them with the recorded run and artifact on the server. Live Paper joins resources to graph nodes by the owning node ID and maps that ID to the rendered node for highlighting. Ranking uses graph distance from the claim, with the nearest recorded producing run first. Where sources tie, display both in a stable order. Older reports and providers without resources keep their existing references and graph. Unrecognized icons or color roles fall back to a labeled generic source, and unrecognized actions are omitted.

Keep the association in a host-supplied resolver separate from the serializable evidence report. Clew resolves a source against the recorded run in the authorized project. The resolver returns a project-relative script path and hash or a curated run record. A mounted reader with only an exported report can display resource labels and graph highlights. Preview and run-detail controls require a host resolver that can verify the association. This lets Live Paper continue reading existing snapshots without invoking Clew on every claim load.

Start with scripts and run details. Add databases and parameters when Clew has explicit records identifying them. A file with no further type information gets the file icon. Color roles and icon identifiers are allowlisted UI tokens. The report carries no HTML, executable UI, arbitrary CSS, or browser navigation URLs.

## Interaction and content delivery

1. Hover or focus the figure rectangle to see its verification status and closest sources. Click or tap to pin the popup. A pinned popup supports keyboard navigation, `Escape` dismissal, and focus return. On narrow screens it becomes a bottom sheet. The feed selects and scrolls to the same rectangle, and dismissal preserves the reader's place.
2. Hover or focus a script row in the popup to load a short preview after a brief delay. A click or keyboard activation keeps the preview open and offers **Run details**. Clicking a reference also highlights its graph node when the compact graph is open. Render the source list first and load graph details on demand.
3. Request a preview with the project or bundle selector, claim ID, report revision, and resource ID. Reauthorize the current project and match the resource against that claim in the current snapshot. A stale revision triggers a refresh. Cache completed responses only in the viewer for that project and revision. Cancel pending requests when the reader switches claims, documents, or projects.
4. Serve a short, size-bounded text excerpt. Use the host-authorized resource root and confined file reader. Resolve the script through the stored evidence association and apply the host's file-read permission. Keep external paths and symlinks outside this preview flow. Hash the same bounded bytes used to render the excerpt. Run details expose a curated set of fields such as run ID, time, and outcome, with an authorized link to a project-scoped Clew view when available.

For the first release, preview the project copy only when its bytes match the recorded script hash and label it **Matches recorded hash**. If the file is missing, has changed, lacks a recorded hash, or fails authorization, explain that the recorded script cannot be previewed and keep **Run details** available when authorized. A later version may show **Recorded snapshot** when a host-approved archive or revision store supplies matching bytes. Any later current-version view should be labeled **Current version** and opened explicitly. A script preview is read-only, and launching a run is a separate project action.

## Implementation order and acceptance

1. Add the optional schema fields and document legacy fallback. Have Clew populate a script descriptor from the producing run and publish the small visual vocabulary. Verify older reports and older run records still render.
2. Add the Rich PDF popover hook and browser coverage for keyboard, pointer, touch, PDF zoom/scroll, and document replacement. Keep the comment panel and feed behavior intact.
3. Wire the Live Paper inspector to the popover and the read-only preview and run-detail requests. Test changed and missing scripts, stale revisions, cross-project IDs, and confined reads. Keep the full graph and check that its source icons and highlights agree with the popover.
4. Qualify a recorded FigRecipe output included as a claim in a Writer-compiled PDF and verify the flow on compute-03. A figure and a numeric claim should both show their sources, a matching script should preview without leaving the PDF, and the run details should match the evidence record. Verify a changed script, a legacy report with no resource descriptors, and a Scholar PDF with only a document port.
