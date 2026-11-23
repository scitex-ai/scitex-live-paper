import { withBundleContext } from "./_utils.js";
import { renderPdfDiscussion } from "./pdf-provider.js";

// Anchored comments — client half of `api/comments` (prompt-10 item 4).
//
// Live Paper is the comments provider for consumers: notes anchored to
// a claim id, a PDF region (page + bbox), or a quoted passage. This
// module fetches/posts them, paints region markers into PDF overlay
// layers, and renders the per-claim comment section in the detail
// pane. Everything degrades to a message — never a broken pane.
//
// Vanilla ES module — no build step.

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

export async function fetchComments(apiBase) {
  const res = await fetch(withBundleContext(apiBase + "comments"), {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error("Comments unavailable");
  const body = await res.json();
  return Array.isArray(body.comments) ? body.comments : [];
}

export async function postComment(apiBase, { body, target, author, kind }) {
  const comment = { body, target };
  if (author) comment.author = author;
  if (kind) comment.kind = kind;
  const token = document.querySelector('meta[name="live-paper-csrf-token"]')?.content;
  if (!token || token === "NOTPROVIDED") throw new Error("LivePaper CSRF token missing; reload the viewer");
  const res = await fetch(withBundleContext(apiBase + "comments"), {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "application/json", "X-CSRFToken": token },
    body: JSON.stringify({ comment }),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok || !payload.comment) {
    throw new Error(payload.error || `comment post failed: ${res.status}`);
  }
  return payload.comment;
}

/**
 * Split comments into claim-anchored (`byClaim`: claim_id -> [..])
 * and region-anchored (`byPage`: page -> [..]). Quote-anchored notes
 * carry no page, so they ride with the claim pane only when they
 * name a claim; otherwise they are listed, not painted.
 */
export function groupComments(comments) {
  const byClaim = new Map();
  const byPage = new Map();
  for (const c of comments || []) {
    const target = (c && c.target) || {};
    if (typeof target.claim_id === "string" && target.claim_id) {
      if (!byClaim.has(target.claim_id)) byClaim.set(target.claim_id, []);
      byClaim.get(target.claim_id).push(c);
    } else if (
      Number.isInteger(target.page) &&
      Array.isArray(target.bbox) &&
      target.bbox.length === 4
    ) {
      if (!byPage.has(target.page)) byPage.set(target.page, []);
      byPage.get(target.page).push(c);
    }
  }
  return { byClaim, byPage };
}

/**
 * Paint one `.lp-comment-marker` per region-anchored comment into an
 * already-positioned overlay layer. Clicking a marker toggles a small
 * popup listing that region's notes. Coordinates are PDF-space
 * (origin bottom-left), converted with the same viewport helper the
 * claim anchors use.
 */
export function paintCommentMarkers(overlayEl, viewport, commentsForPage) {
  if (!commentsForPage || commentsForPage.length === 0) return;
  const doc = overlayEl.ownerDocument || document;
  for (const comment of commentsForPage) {
    const bbox = comment?.target?.bbox;
    if (!Array.isArray(bbox) || bbox.length !== 4) continue;
    let rect;
    try {
      const [vx0, vy0, vx1, vy1] = viewport.convertToViewportRectangle(bbox);
      rect = {
        left: Math.min(vx0, vx1),
        top: Math.min(vy0, vy1),
      };
    } catch (err) {
      continue;
    }
    const marker = doc.createElement("button");
    marker.type = "button";
    marker.className = "lp-comment-marker";
    marker.style.left = `${rect.left}px`;
    marker.style.top = `${rect.top}px`;
    marker.textContent = "✎";
    marker.setAttribute(
      "aria-label",
      `Comment by ${comment.author || "anonymous"}: ${(comment.body || "").slice(0, 80)}`
    );
    marker.title = (comment.body || "").slice(0, 140);
    marker.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleMarkerPopup(marker, commentsForPage);
    });
    overlayEl.appendChild(marker);
  }
}

function toggleMarkerPopup(marker, commentsForPage) {
  const open = marker.parentElement?.querySelector(":scope > .lp-comment-popup");
  if (open) {
    open.remove();
    return;
  }
  const popup = marker.ownerDocument.createElement("div");
  popup.className = "lp-comment-popup";
  popup.setAttribute("role", "dialog");
  popup.setAttribute("aria-label", "Region comments");
  for (const c of commentsForPage) {
    const item = marker.ownerDocument.createElement("div");
    item.className = "lp-comment-popup-item";
    const who = marker.ownerDocument.createElement("span");
    who.className = "lp-comment-author";
    who.textContent = c.author || "anonymous";
    item.appendChild(who);
    item.appendChild(marker.ownerDocument.createTextNode((c.body || "").slice(0, 280)));
    popup.appendChild(item);
  }
  marker.parentElement.appendChild(popup);
}

/** Adapt bundle comments to the shared Rich PDF discussion. */
export function showComments(panel, { apiBase, page, claimId, onComments }) {
  const targetControl = el("label", null, "Attach to");
  const select = el("select", "stx-select");
  if (page) select.add(new Option(`PDF page ${page}`, "page"));
  if (claimId) select.add(new Option(`Claim · ${claimId}`, "claim"));
  targetControl.append(select);
  let comments = [];

  function toDiscussion(comment) {
    const { created_at, target, ...rest } = comment;
    return {
      ...rest,
      createdAt: created_at,
      target: target.claim_id ? { overlayId: target.claim_id } : target,
    };
  }
  panel.replaceChildren();
  return renderPdfDiscussion(panel, {
    load: async () => {
      comments = await fetchComments(apiBase);
      onComments(comments);
      return comments.map(toDiscussion);
    },
    post: select.options.length ? async (body) => {
      const target = select.value === "claim" ? { claim_id: claimId } : { page };
      const entry = await postComment(apiBase, { body, target });
      comments.push(entry);
      onComments(comments);
      return toDiscussion(entry);
    } : undefined,
    targetControl,
    labelTarget: (target) => {
      if (target.overlayId) return `Claim · ${target.overlayId}`;
      if (target.page) return `PDF page ${target.page}` + (target.bbox ? " · region" : "");
      return "Quoted passage";
    },
  });
}
