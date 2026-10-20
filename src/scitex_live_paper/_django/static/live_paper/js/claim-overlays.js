// Claim overlays — PDF-space anchor regions over PDF.js pages.
//
// Django SPA counterpart to the static renderer's `assets/viewer.js`
// paint path. Groups claims by `anchor.page`, converts each
// PDF-space `bbox [x0, y0, x1, y1]` (origin bottom-left) to a CSS
// rect via `viewport.convertToViewportRectangle`, and paints one
// `<button class="lp-claim-anchor">` per anchored claim into the
// per-page `.lp-overlay` layer.
//
// Port binding (contract §4): figure claims carrying `figure_id` get
// `data-lp-port="figure"` + `data-lp-target=<figure_id>` so the
// `port-events.js` bus delegation picks up clicks and renders the
// evidence popup. Non-figure anchors dispatch `live-paper:claim`
// for the claims sidebar.
//
// Vanilla ES module — no build step.

const STATUS_CLASS = {
  verified: "lp-status-verified",
  suspect: "lp-status-suspect",
  mismatch: "lp-status-mismatch",
  missing: "lp-status-missing",
  // clew 1.4 "unsourced" folds into the amber bucket (same as the
  // static renderer) — colour alias only, status word untouched.
  unsourced: "lp-status-suspect",
};

export function classFor(status) {
  return STATUS_CLASS[(status || "").toLowerCase()] || "";
}

export function groupClaimsByPage(claims) {
  const out = new Map();
  for (const c of claims || []) {
    const p = c?.anchor?.page;
    if (!Number.isInteger(p)) continue;
    if (!out.has(p)) out.set(p, []);
    out.get(p).push(c);
  }
  return out;
}

/**
 * Convert a PDF-space bbox `[x0, y0, x1, y1]` (origin bottom-left)
 * to a top-left CSS rect on the rendered canvas. Delegates to the
 * PDF.js viewport so the maths stays correct under any zoom.
 */
export function pdfBboxToCssRect(viewport, bbox) {
  const [vx0, vy0, vx1, vy1] = viewport.convertToViewportRectangle(bbox);
  const left = Math.min(vx0, vx1);
  const top = Math.min(vy0, vy1);
  const w = Math.abs(vx1 - vx0);
  const h = Math.abs(vy1 - vy0);
  return { left, top, w, h };
}

export function paintClaimAnchor(overlayEl, viewport, claim) {
  const a = claim?.anchor;
  if (!a || !Array.isArray(a.bbox) || a.bbox.length !== 4) return null;
  const rect = pdfBboxToCssRect(viewport, a.bbox);

  const el = document.createElement("button");
  el.type = "button";
  el.className = `lp-claim-anchor ${classFor(claim.status)}`.trim();
  el.dataset.claimId = claim.claim_id;
  el.dataset.status = claim.status || "registered";
  el.style.left = `${rect.left}px`;
  el.style.top = `${rect.top}px`;
  el.style.width = `${rect.w}px`;
  el.style.height = `${rect.h}px`;
  el.title = claim.claim_value || claim.claim_id;
  el.setAttribute("aria-label", `Claim ${claim.claim_id}`);

  // Figure claims are port-backed evidence targets (contract §4).
  // The port-events bus listens for [data-lp-port] clicks at the
  // root and fetches api/port/figure/<id>.
  if (claim.figure_id) {
    el.setAttribute("data-lp-port", "figure");
    el.setAttribute("data-lp-target", claim.figure_id);
  }

  el.addEventListener("click", () => {
    overlayEl.dispatchEvent(
      new CustomEvent("live-paper:claim", {
        bubbles: true,
        detail: { id: claim.claim_id },
      })
    );
  });
  overlayEl.appendChild(el);
  return el;
}

/**
 * Create the per-page `.lp-overlay` layer inside *pageWrap* and
 * paint every anchored claim for that viewport. Returns the
 * overlay element (empty when *claimsForPage* is empty).
 */
export function paintPageOverlays(pageWrap, viewport, claimsForPage) {
  const overlay = document.createElement("div");
  overlay.className = "lp-overlay";
  pageWrap.appendChild(overlay);
  for (const claim of claimsForPage || []) {
    paintClaimAnchor(overlay, viewport, claim);
  }
  return overlay;
}
