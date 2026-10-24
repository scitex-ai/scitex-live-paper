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

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

export function renderClaimDetail(sidebarEl, claim, apiBase) {
  closeClaimDetail(sidebarEl);
  const pane = el("div", "lp-claim-detail");
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
  dagBox.appendChild(el("p", "lp-claim-dag-loading", "Loading DAG…"));
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

export async function renderDagPane(dagBox, claimId, apiBase) {
  let body = {};
  try {
    const res = await fetch(apiBase + "dag", { headers: { Accept: "application/json" } });
    body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.error || ("dag request failed: " + res.status));
  } catch (err) {
    dagBox.innerHTML = "";
    dagBox.appendChild(el("p", "lp-claim-dag-empty",
      "DAG unavailable (" + String((err && err.message) || err) + ")."));
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
      window.mermaid.initialize({ startOnLoad: false });
    }
    const { svg } = await window.mermaid.render("lp-dag-" + String(claimId || "x"), body.mermaid);
    dagBox.innerHTML = "";
    const wrap = el("div", "lp-claim-dag-svg");
    wrap.innerHTML = svg;
    dagBox.appendChild(wrap);
  } catch (err) {
    dagBox.innerHTML = "";
    dagBox.appendChild(el("p", "lp-claim-dag-empty",
      "DAG render failed (" + String((err && err.message) || err) + ")."));
  }
}
