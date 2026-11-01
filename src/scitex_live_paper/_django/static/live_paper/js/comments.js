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
  try {
    const res = await fetch(apiBase + "comments", {
      headers: { Accept: "application/json" },
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) return [];
    return Array.isArray(body.comments) ? body.comments : [];
  } catch (err) {
    console.warn("[live-paper] comments fetch failed:", err);
    return [];
  }
}

export async function postComment(apiBase, { body, target, author, kind }) {
  const comment = { body, target };
  if (author) comment.author = author;
  if (kind) comment.kind = kind;
  const res = await fetch(apiBase + "comments", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
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

/**
 * Render the comment section (list + add form) into a claim detail
 * pane. Re-renders after each successful post so the count stays
 * honest. Failures surface as an inline message, never a throw.
 */
export async function renderCommentSection(containerEl, claimId, apiBase) {
  containerEl.innerHTML = "";
  const section = el("div", "lp-comments");
  section.appendChild(el("p", "lp-comments-loading", "Loading comments…"));
  containerEl.appendChild(section);
  let comments = [];
  try {
    comments = (await fetchComments(apiBase)).filter(
      (c) => c?.target?.claim_id === claimId
    );
  } catch (err) {
    section.innerHTML = "";
    section.appendChild(el("p", "lp-comments-empty", "Comments unavailable."));
    return section;
  }
  section.innerHTML = "";
  section.appendChild(el("h3", "lp-comments-title", `Comments (${comments.length})`));
  if (comments.length === 0) {
    section.appendChild(
      el("p", "lp-comments-empty", "No comments yet — add the first below.")
    );
  } else {
    const list = el("ul", "lp-comments-list");
    for (const c of comments) {
      const item = el("li", "lp-comments-item");
      const head = el("div", "lp-comments-head");
      head.appendChild(el("span", "lp-comment-author", c.author || "anonymous"));
      if (c.created_at) head.appendChild(el("span", "lp-comment-ts", String(c.created_at).slice(0, 16).replace("T", " ")));
      item.appendChild(head);
      item.appendChild(el("p", "lp-comment-body", c.body || ""));
      list.appendChild(item);
    }
    section.appendChild(list);
  }
  const form = el("form", "lp-comments-form");
  const input = el("textarea", "lp-comments-input");
  input.rows = 2;
  input.placeholder = "Add a comment on this claim…";
  input.setAttribute("aria-label", "New comment");
  const row = el("div", "lp-comments-form-row");
  const author = el("input", "lp-comments-author");
  author.placeholder = "name (optional)";
  author.setAttribute("aria-label", "Author name");
  const submit = el("button", "lp-comments-submit", "Comment");
  submit.type = "submit";
  row.appendChild(author);
  row.appendChild(submit);
  form.appendChild(input);
  form.appendChild(row);
  const error = el("p", "lp-comments-error");
  error.hidden = true;
  form.appendChild(error);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;
    const text = input.value.trim();
    if (!text) return;
    submit.disabled = true;
    try {
      await postComment(apiBase, {
        body: text,
        target: { claim_id: claimId },
        author: author.value.trim() || undefined,
      });
      await renderCommentSection(containerEl, claimId, apiBase);
    } catch (err) {
      error.textContent = String((err && err.message) || err);
      error.hidden = false;
    } finally {
      submit.disabled = false;
    }
  });
  section.appendChild(form);
  return section;
}
