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

let graphSequence = 0;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

export function renderClaimDetail(sidebarEl, claim, apiBase) {
  const active = sidebarEl.querySelector(":scope > .lp-claim-detail");
  if (active?.dataset.claimId === claim.claim_id) return active;
  closeClaimDetail(sidebarEl);
  const pane = el("div", "lp-claim-detail");
  pane.dataset.claimId = claim.claim_id;
  pane.setAttribute("role", "dialog");
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

  const status = el("p", "lp-claim-detail-status",
    "status: " + (claim.status || "registered"));
  status.dataset.status = claim.status || "registered";
  pane.appendChild(status);

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

  const dagBox = el("div", "lp-claim-dag");
  dagBox.appendChild(el("p", "lp-claim-dag-loading", "Loading evidence graph…"));
  pane.appendChild(dagBox);
  renderDagPane(dagBox, claim.claim_id, apiBase);

  // Anchored comments (provider item 4): list + add form for this
  // claim. Best-effort — a comments outage must not break the pane.
  try {
    const commentsBox = el("div", "lp-claim-comments-slot");
    pane.appendChild(commentsBox);
    void renderCommentSection(commentsBox, claim.claim_id, apiBase);
  } catch (err) {
    console.warn("[live-paper] comments section failed:", err);
  }

  sidebarEl.appendChild(pane);
  return pane;
}

export function closeClaimDetail(sidebarEl) {
  const open = sidebarEl.querySelector(":scope > .lp-claim-detail");
  if (open) open.remove();
}

export function renderEvidencePreview(panel, claim, apiBase, signal) {
  panel.append(el("h2", "lp-evidence-preview-title", claim.claim_value ?? claim.claim_id));
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
  });

  function load(reference, { start = 0, member } = {}) {
    request?.abort();
    request = new AbortController();
    const current = request;
    preview.hidden = false;
    preview.replaceChildren(el("p", null, "Loading file preview…"));
    const url = new URL("../preview.json", new URL(apiBase, location.href));
    url.searchParams.set("claim_id", claim.claim_id);
    url.searchParams.set("node_id", reference.node_id);
    if (start) url.searchParams.set("start", start);
    if (member !== undefined) url.searchParams.set("member", member);
    fetch(withBundleContext(url.href), {
      signal: AbortSignal.any([signal, current.signal]),
      headers: { Accept: "application/json" },
    }).then(async (response) => {
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      if (current.signal.aborted || signal.aborted) return;
      preview.replaceChildren(
        el("code", null, result.file),
        el("span", "lp-source-preview-status", result.truncated
          ? "Matches recorded hash · excerpt" : "Matches recorded hash"),
      );
      if (result.member) {
        const back = previewButton("Archive contents", () => load(reference));
        preview.append(el("p", null, result.member), back);
      }
      renderSourceContent(preview, result, (options) => load(reference, options), member);
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

function previewButton(label, action) {
  const button = el("button", null, label);
  button.type = "button";
  button.addEventListener("click", action);
  return button;
}

function renderSourceContent(panel, result, load, member) {
  if (result.kind === "image") {
    const image = el("img");
    image.src = `data:${result.media_type};base64,${result.data}`;
    image.alt = result.file;
    panel.append(image);
  } else if (result.kind === "text") {
    panel.append(el("pre", null, result.text));
  } else if (result.kind === "archive") {
    const list = el("ul", "lp-archive-preview");
    for (const item of result.members) {
      const row = el("li");
      row.append(previewButton(item.name, () => load({ member: item.id })));
      list.append(row);
    }
    panel.append(el("p", null, "First archive entries"), list);
  } else if (result.kind === "idx") {
    renderIdxWindow(panel, result, load, member);
  } else {
    panel.append(el("p", null, result.description));
  }
}

function renderIdxWindow(panel, result, load, member) {
  const { start, end, total, rows, columns, page_size: size } = result;
  const recordType = rows ? ` · ${rows} × ${columns} unsigned-byte grids` : " · unsigned-byte values";
  panel.append(el("p", null, `Records ${start + 1}–${end} of ${total}${recordType}`));
  const records = atob(result.records);
  if (rows) {
    const grid = el("div", "lp-idx-grids");
    const stride = rows * columns;
    for (let index = 0; index < end - start; index++) {
      const canvas = el("canvas");
      canvas.width = columns;
      canvas.height = rows;
      canvas.setAttribute("role", "img");
      canvas.setAttribute("aria-label", `Grayscale grid for record ${start + index + 1}`);
      const context = canvas.getContext("2d");
      const image = context.createImageData(columns, rows);
      for (let pixel = 0; pixel < stride; pixel++) {
        const intensity = records.charCodeAt(index * stride + pixel);
        image.data.set([intensity, intensity, intensity, 255], pixel * 4);
      }
      context.putImageData(image, 0, 0);
      grid.append(canvas);
    }
    panel.append(grid);
  } else {
    panel.append(el("pre", null, Array.from(records, (value) => value.charCodeAt(0)).join("  ")));
  }
  const navigation = el("div", "lp-source-preview-navigation");
  const previous = previewButton("Previous records", () => load({ start: Math.max(0, start - size), member }));
  const next = previewButton("Next records", () => load({ start: end, member }));
  previous.disabled = start === 0;
  next.disabled = end >= total;
  navigation.append(previous, next);
  panel.append(navigation);
}

export async function renderDagPane(dagBox, claimId, apiBase, { signal, selectReference } = {}) {
  let body = {};
  try {
    const selector = new URLSearchParams({ claim_id: claimId });
    const res = await fetch(withBundleContext(apiBase + "dag?" + selector), {
      headers: { Accept: "application/json" },
      signal,
    });
    body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || ("dag request failed: " + res.status));
  } catch (err) {
    if (signal?.aborted) return;
    dagBox.innerHTML = "";
    dagBox.appendChild(el("p", "lp-claim-dag-empty",
      String((err && err.message) || "Evidence graph unavailable.")));
    return;
  }
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
    if (typeof window.mermaid.initialize === "function") {
      window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
    }
    const { svg } = await window.mermaid.render("lp-dag-" + (++graphSequence), body.mermaid);
    if (signal?.aborted) return;
    const title = body.scope === "claim" ? "Evidence graph" : "Bundle graph";
    const heading = el("h3", "lp-claim-graph-title", title);
    if (body.provider) heading.append(" (" + body.provider + ")");
    const wrap = el("div", "lp-claim-dag-svg");
    wrap.innerHTML = svg;
    dagBox.replaceChildren(heading);
    if (selectReference && body.reason) {
      const status = el("p", "lp-claim-trace-status", body.state === "supported"
        ? "Calculation trace verified" : body.reason);
      status.dataset.state = body.state;
      dagBox.append(status);
    }
    dagBox.append(wrap);
    if (body.scope === "claim") {
      const graphPage = new URL("../graph.html", new URL(apiBase, location.href));
      graphPage.searchParams.set("claim_id", claimId);
      const link = el("a", "lp-claim-graph-link", "Open full evidence graph");
      link.href = withBundleContext(graphPage.href);
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
  const list = el("ul", "lp-claim-references");
  dagBox.append(el("h4", "lp-claim-graph-title", "Source references"), list);
  const entries = new Map();
  let hoverTimer;
  function highlight(id) {
    for (const [key, { button, node }] of entries) {
      button.setAttribute("aria-pressed", String(key === id));
      node.classList.toggle("lp-source-highlight", key === id);
    }
  }
  for (const reference of references) {
    const node = [...graph.querySelectorAll("g.node")].find(
      (element) => element.id.startsWith("flowchart-" + reference.id + "-"),
    );
    if (!node) continue;
    const item = el("li", null);
    const label = reference.script_file || reference.label;
    const button = el("button", null, label);
    if (selectReference) {
      const role = { input: "Input", output: "Output", process: "Run" }[reference.kind];
      button.prepend(el("span", "lp-source-kind", role + " "));
    }
    button.type = "button";
    button.setAttribute("aria-pressed", "false");
    function select() {
      if (selectReference && button.getAttribute("aria-pressed") === "true") return;
      highlight(reference.id);
      selectReference?.(reference);
    }
    button.addEventListener("click", () => {
      select();
      if (!selectReference) node.scrollIntoView({ block: "nearest", inline: "nearest" });
    });
    node.addEventListener("click", select);
    if (selectReference) {
      for (const target of [node, button]) {
        target.addEventListener("pointerenter", () => {
          clearTimeout(hoverTimer);
          hoverTimer = setTimeout(() => { if (target.isConnected) select(); }, 80);
        });
        target.addEventListener("pointerleave", () => clearTimeout(hoverTimer));
      }
      button.addEventListener("focus", () => {
        clearTimeout(hoverTimer);
        select();
      });
    }
    entries.set(reference.id, { button, node });
    item.append(button);
    list.append(item);
  }
}
