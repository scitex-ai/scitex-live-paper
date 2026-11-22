import { withBundleContext } from "./_utils.js";

// Claim detail pane + DAG pane for the sidebar (slice D).
// Vanilla ES module.
//
// Row click (not on a button) renders a detail pane under the list:
// claim id/value/status, provenance (source file/hash/session, anchor),
// the bundle DAG via `api/dag` rendered with the vendored mermaid
// UMD bundle (`window.mermaid`), then the anchored-comments section
// (`api/comments` list + add form). Everything degrades to a message —
// never an empty pane.

import { renderCommentSection } from "./comments.js";
import { graphControls } from "../../../../_renderer/assets/graph-controls.js";

let graphSequence = 0;
const detailRequests = new WeakMap();

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

export function renderClaimDetail(sidebarEl, claim, apiBase, { refresh = false, goToPdf } = {}) {
  const selection = sidebarEl.querySelector("#lp-selection-panel");
  sidebarEl.querySelector("#lp-selection-tab").click();
  const active = selection.querySelector(".lp-claim-detail");
  if (!refresh && active?.dataset.claimId === claim.claim_id) return active;
  removeClaimDetail(sidebarEl);
  const pane = el("div", "lp-claim-detail");
  pane.dataset.claimId = claim.claim_id;
  pane.setAttribute("role", "region");
  pane.setAttribute("aria-label", "Claim detail");

  const header = el("div", "lp-claim-detail-header");
  header.appendChild(el("code", "lp-claim-detail-id", claim.claim_id || "(no id)"));
  const close = el("button", "lp-claim-detail-close", "Close");
  close.type = "button";
  close.addEventListener("click", () => closeClaimDetail(sidebarEl));
  header.appendChild(close);
  pane.appendChild(header);

  pane.appendChild(el("p", "lp-claim-detail-value",
    claim.claim_value || claim.file_path || "(no value)"));
  const relation = claim.extras?.evidence_relation ?? claim.extras?.metadata?.evidence_relation;
  if (relation === "author_interpretation") {
    pane.append(el("p", "lp-claim-detail-status", "Author interpretation"));
  }

  const status = el("p", "lp-claim-detail-status",
    "status: " + (claim.status || "registered"));
  status.dataset.status = claim.status || "registered";
  pane.appendChild(status);

  if (goToPdf) {
    const jump = el("button", "stx-button", "Show in PDF");
    jump.type = "button";
    jump.addEventListener("click", goToPdf);
    pane.append(jump);
  }

  const prov = el("ul", "lp-claim-detail-provenance");
  const rows = [
    ["source", claim.source_file],
    ["hash", claim.source_hash],
    ["session", claim.source_session],
    ["location", claim.file_path && claim.line_number != null
      ? claim.file_path + ":" + claim.line_number : claim.file_path],
  ];
  for (const [label, value] of rows) {
    if (!value) continue;
    const item = el("li");
    item.appendChild(el("span", "lp-claim-detail-prov-label", label + ": "));
    item.appendChild(el("code", null, String(value)));
    prov.appendChild(item);
  }
  if (claim.extras && claim.extras.figure_id) {
    const item = el("li");
    item.appendChild(el("span", "lp-claim-detail-prov-label", "figure: "));
    item.appendChild(el("code", null, String(claim.extras.figure_id)));
    prov.appendChild(item);
  }
  pane.appendChild(prov);

  const controller = new AbortController();
  detailRequests.set(pane, controller);
  pane.ownerDocument.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !event.defaultPrevented) closeClaimDetail(sidebarEl);
  }, { signal: controller.signal });
  renderEvidenceDetails(pane, claim, apiBase, controller.signal);

  // Anchored comments (provider item 4): list + add form for this
  // claim. Best-effort — a comments outage must not break the pane.
  try {
    const commentsBox = el("div", "lp-claim-comments-slot");
    pane.appendChild(commentsBox);
    void renderCommentSection(commentsBox, claim.claim_id, apiBase);
  } catch (err) {
    console.warn("[live-paper] comments section failed:", err);
  }

  selection.append(pane);
  sidebarEl.scrollTop = 0;
  return pane;
}

export function renderCitationDetail(sidebar, key, citation, apiBase, goToReference) {
  delete sidebar.dataset.pinnedClaim;
  removeClaimDetail(sidebar);
  sidebar.querySelector("#lp-selection-tab").click();
  const pane = el("div", "lp-claim-detail");
  pane.setAttribute("role", "region");
  pane.setAttribute("aria-label", "Citation evidence");
  pane.append(el("h3", "lp-evidence-preview-title", key));
  const badge = el("p", "lp-citation-status", "Clew status · " + citation.status);
  badge.dataset.status = citation.status;
  pane.append(badge);
  if (citation.reason) pane.append(el("p", "", citation.reason));
  if (citation.resolver_source) pane.append(el("p", "", "Scholar provider · " + citation.resolver_source));
  if (citation.provenance) pane.append(el("p", "", citation.provenance));
  if (citation.doi) pane.append(el("p", "", "DOI · " + citation.doi));
  if (citation.link) {
    try {
      const url = new URL(citation.link);
      if (url.protocol === "https:" || url.protocol === "http:") {
        const source = el("a", "stx-button", "Open source");
        source.href = url.href;
        source.target = "_blank";
        source.rel = "noopener noreferrer";
        pane.append(source);
      }
    } catch { /* The provider did not supply an absolute web URL. */ }
  }
  if (goToReference) {
    const jump = el("button", "stx-button", "Go to bibliography entry");
    jump.type = "button";
    jump.addEventListener("click", goToReference);
    pane.append(jump);
  }
  if (citation.claim_id) {
    const controller = new AbortController();
    detailRequests.set(pane, controller);
    renderEvidenceDetails(pane, { claim_id: citation.claim_id }, apiBase, controller.signal, true);
  } else {
    pane.append(el("p", "lp-claim-dag-empty", "No Clew retrieval graph is recorded for this citation."));
  }
  const close = el("button", "stx-button", "Close");
  close.type = "button";
  close.addEventListener("click", () => closeClaimDetail(sidebar));
  pane.append(close);
  sidebar.querySelector("#lp-selection-panel").append(pane);
  sidebar.scrollTop = 0;
}

function removeClaimDetail(sidebarEl) {
  const open = sidebarEl.querySelector("#lp-selection-panel > .lp-claim-detail");
  if (open) {
    detailRequests.get(open)?.abort();
    open.remove();
  }
}

export function closeClaimDetail(sidebarEl) {
  delete sidebarEl.dataset.pinnedClaim;
  removeClaimDetail(sidebarEl);
  sidebarEl.querySelector("#lp-all-claims-tab").click();
}

export function renderEvidencePreview(panel, claim, apiBase, signal) {
  panel.append(el("h2", "lp-evidence-preview-title", claim.claim_value ?? claim.claim_id));
  renderEvidenceDetails(panel, claim, apiBase, signal);
}

function renderEvidenceDetails(panel, claim, apiBase, signal, requireClaim = false) {
  const graph = el("div", "lp-claim-dag");
  graph.append(el("p", "lp-claim-dag-loading", "Loading evidence graph…"));
  panel.append(graph);
  const preview = el("div", "lp-source-preview");
  preview.setAttribute("aria-live", "polite");
  preview.hidden = true;
  panel.append(preview);
  let request = null;

  renderDagPane(graph, claim.claim_id, apiBase, {
    signal,
    selectReference: (reference) => load(reference),
    requireClaim,
  });

  function load(reference, { member } = {}) {
    request?.abort();
    request = new AbortController();
    const current = request;
    preview.hidden = false;
    preview.replaceChildren(el("p", null, "Loading file preview…"));
    const url = new URL("../preview.json", new URL(apiBase, location.href));
    url.searchParams.set("claim_id", claim.claim_id);
    url.searchParams.set("node_id", reference.node_id);
    if (member !== undefined) url.searchParams.set("member", member);
    fetch(withBundleContext(url.href), {
      signal: AbortSignal.any([signal, current.signal]),
      headers: { Accept: "application/json" },
    }).then(async (response) => {
      const result = await response.json();
      if (current.signal.aborted || signal.aborted) return;
      if (!response.ok) {
        preview.replaceChildren(
          el("code", null, reference.script_file || reference.label),
          el("p", null, result.error || "File preview unavailable."),
        );
        appendSourceLinks(preview, result.links, { current: true });
        return;
      }
      preview.replaceChildren(
        el("code", null, result.file),
        el("span", "lp-source-preview-status", result.truncated
          ? "Matches recorded hash · excerpt" : "Matches recorded hash"),
      );
      appendSourceLinks(preview, result.links);
      if (result.member) {
        const back = previewButton("Archive contents", () => load(reference));
        preview.append(el("p", null, result.member), back);
      }
      renderSourceContent(preview, result, (options) => load(reference, options));
    }).catch((error) => {
      if (!current.signal.aborted && !signal.aborted) {
        preview.replaceChildren(
          el("code", null, reference.script_file || reference.label),
          el("p", null, error.message || "File preview unavailable."),
        );
      }
    });
  }
}

function appendSourceLinks(preview, links, { current = false } = {}) {
  const actions = el("div", "lp-source-actions");
  const choices = [
    [links?.file, current ? "Open current file" : "Open file"],
    [links?.folder, "Open containing folder"],
  ];
  for (const [url, label] of choices) {
    if (typeof url !== "string" || !url.startsWith("/") || url.startsWith("//") || url.includes("\\")) continue;
    const action = el("a", "stx-button", label);
    action.href = url;
    action.target = "_blank";
    action.rel = "noopener";
    actions.append(action);
  }
  if (actions.childElementCount) preview.append(actions);
}

function previewButton(label, action) {
  const button = el("button", null, label);
  button.type = "button";
  button.addEventListener("click", action);
  return button;
}

function renderSourceContent(panel, result, load) {
  if (result.kind === "image") {
    const image = el("img");
    image.src = `data:${result.media_type};base64,${result.data}`;
    image.alt = result.file;
    panel.append(image);
  } else if (result.kind === "text") {
    const code = el("code", result.language ? "language-" + result.language : null, result.text);
    const block = el("pre");
    block.append(code);
    panel.append(block);
    if (result.language) window.hljs?.highlightElement(code);
  } else if (result.kind === "archive") {
    const list = el("ul", "lp-archive-preview");
    for (const item of result.members) {
      const row = el("li");
      row.append(previewButton(item.name, () => load({ member: item.id })));
      list.append(row);
    }
    panel.append(el("p", null, "First archive entries"), list);
  } else if (result.kind === "metadata") {
    const size = result.size.toLocaleString();
    const identity = el("details");
    identity.append(el("summary", null, "Recorded hash"), el("code", null, result.hash));
    panel.append(el("p", null, `${result.description} · ${size} bytes`), identity);
  }
}

const graphLayouts = new Map();
const maxLayouts = 32;

export function invalidateEvidenceGraphs() {
  graphLayouts.clear();
}

function cachedLayout(hash, render) {
  const hit = graphLayouts.get(hash);
  if (hit) {
    graphLayouts.delete(hash);
    graphLayouts.set(hash, hit);
    return hit;
  }
  const rendered = Promise.resolve().then(render).catch((error) => {
    if (graphLayouts.get(hash) === rendered) graphLayouts.delete(hash);
    throw error;
  });
  graphLayouts.set(hash, rendered);
  if (graphLayouts.size > maxLayouts) graphLayouts.delete(graphLayouts.keys().next().value);
  return rendered;
}

export async function renderDagPane(dagBox, claimId, apiBase, { signal, selectReference, requireClaim } = {}) {
  let body;
  try {
    const selector = new URLSearchParams({ claim_id: claimId });
    const url = withBundleContext(apiBase + "dag?" + selector);
    const res = await fetch(url, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal,
    });
    body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || ("dag request failed: " + res.status));
    if (requireClaim && body.scope !== "claim") throw new Error("No Clew retrieval graph is recorded for this citation.");
  } catch (err) {
    if (signal?.aborted) return;
    dagBox.replaceChildren(el("p", "lp-claim-dag-empty",
      String((err && err.message) || "Evidence graph unavailable.")));
    return;
  }
  if (signal?.aborted) return;
  if (!body.mermaid) {
    dagBox.innerHTML = "";
    dagBox.appendChild(el("p", "lp-claim-dag-empty", "DAG unavailable (empty)."));
    return;
  }
  if (!window.mermaid) {
    dagBox.innerHTML = "";
    const pre = el("pre", "lp-claim-dag-source", body.mermaid);
    dagBox.appendChild(pre);
    return;
  }
  try {
    const render = () => {
      window.mermaid.initialize?.({ startOnLoad: false, securityLevel: "strict", htmlLabels: false });
      return window.mermaid.render("lp-dag-" + (++graphSequence), body.mermaid);
    };
    const { svg } = body.graph_sha256
      ? await cachedLayout(body.graph_sha256, render)
      : await render();
    if (signal?.aborted) return;
    const title = body.scope === "claim" ? "Evidence graph" : "Bundle graph";
    const heading = el("h3", "lp-claim-graph-title", title);
    if (body.provider) heading.append(" (" + body.provider + ")");
    const wrap = el("div", "lp-claim-dag-svg");
    wrap.dataset.evidenceState = body.state || "";
    wrap.innerHTML = svg;
    dagBox.replaceChildren(heading);
    if (selectReference && body.reason) {
      const status = el("p", "lp-claim-trace-status", body.state === "supported"
        ? "Recorded trace verified" : body.reason);
      status.dataset.state = body.state;
      dagBox.append(status);
    }
    dagBox.append(graphControls(wrap, signal), wrap);
    if (body.scope === "claim") {
      const graphPage = new URL("../graph.html", new URL(apiBase, location.href));
      graphPage.searchParams.set("claim_id", claimId);
      const link = el("a", "lp-claim-graph-link", "Open full evidence graph");
      function updateGraphLink() {
        const theme = document.documentElement.dataset.theme;
        if (theme === "light" || theme === "dark") graphPage.searchParams.set("theme", theme);
        else graphPage.searchParams.delete("theme");
        link.href = withBundleContext(graphPage.href);
      }
      updateGraphLink();
      link.addEventListener("click", updateGraphLink);
      dagBox.append(link);
      bindReferences(dagBox, wrap, body.references, selectReference);
    }
  } catch (err) {
    if (signal?.aborted) return;
    dagBox.innerHTML = "";
    dagBox.appendChild(el("p", "lp-claim-dag-empty",
      "DAG render failed (" + String((err && err.message) || err) + ")."));
  }
}


function bindReferences(dagBox, graph, references, selectReference) {
  if (!Array.isArray(references) || !references.length) return;
  const nodes = [...graph.querySelectorAll("g.node")];
  const entries = references.map((reference) => ({
    reference,
    node: nodes.find((element) => element.id.startsWith("flowchart-" + reference.id + "-")),
  }));
  let activeReference;
  let pinnedReference = false;
  let hoverTimer;
  const fallback = entries.length > 6 || entries.some(({ node }) => !node);
  const list = fallback ? el("ul", "lp-claim-references") : null;

  function activate(entry, pin = false) {
    if (pinnedReference && !pin) return;
    if (pin) pinnedReference = true;
    const { reference, node } = entry;
    if (activeReference === reference.id) return;
    activeReference = reference.id;
    for (const other of entries) {
      const selected = other === entry;
      other.node?.setAttribute("aria-pressed", String(selected));
      other.node?.classList.toggle("lp-source-highlight", selected);
      other.button?.setAttribute("aria-pressed", String(selected));
    }
    if (selectReference) selectReference(reference);
    else node?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }

  for (const entry of entries) {
    const { reference, node } = entry;
    const role = { input: "Input", output: "Output", process: "Run" }[reference.kind];
    const label = (role ? role + " " : "") + (reference.script_file || reference.label);
    const select = () => activate(entry, true);
    const preview = () => activate(entry);
    if (node) {
      node.setAttribute("role", "button");
      node.setAttribute("tabindex", "0");
      node.setAttribute("aria-label", label);
      node.setAttribute("aria-pressed", "false");
      node.addEventListener("click", select);
      node.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        select();
      });
    }
    if (list) {
      const item = el("li");
      entry.button = previewButton(label, select);
      entry.button.setAttribute("aria-pressed", "false");
      item.append(entry.button);
      list.append(item);
    }
    if (!selectReference) continue;
    for (const control of [node, entry.button].filter(Boolean)) {
      control.addEventListener("pointerenter", () => {
        clearTimeout(hoverTimer);
        hoverTimer = setTimeout(() => { if (control.isConnected) preview(); }, 80);
      });
      control.addEventListener("pointerleave", () => clearTimeout(hoverTimer));
      control.addEventListener("focus", preview);
    }
  }

  if (list) {
    const details = el("details");
    details.append(el("summary", null, "Browse sources"), list);
    dagBox.append(details);
  }
}
