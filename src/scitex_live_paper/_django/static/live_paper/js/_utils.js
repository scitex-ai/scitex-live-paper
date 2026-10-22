// Shared utility helpers for the live-paper SPA modules. Vanilla ES
// module — every other JS file under this dir imports from here.
// No DOM-shape assumptions beyond `#live-paper-root` / `#live-paper-pdf`
// / `#live-paper-bundle-info` (the IDs the SPA contract pins).

export function normalizeBase(base) {
  if (!base.endsWith("/")) base += "/";
  return base;
}

export async function fetchJson(url) {
  const res = await fetch(url);
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch (_err) {
    // Non-JSON error bodies (the mount wrapper answers resolver
    // failures as text/plain): surface status + body instead of a
    // bare SyntaxError so the boot error path can react to it.
    throw new Error("HTTP " + res.status + ": " + text.slice(0, 200));
  }
}

export async function fetchOrNull(url) {
  // Soft fetch — returns the parsed body on 2xx, returns null on any
  // non-OK status or a network error. Used for opportunistic boot
  // endpoints (e.g. `api/dashboard`) where the caller wants to fall
  // back to a slower path rather than fail the whole boot.
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch (_err) {
    return null;
  }
}

export function setStatus(payload) {
  // Beta-1 chrome: the loading line is replaced by a rendered bundle
  // header; the raw JSON moves into the collapsed diagnostics
  // <details>. textContent only — bundle fields are server data, never
  // markup.
  const loading = document.getElementById("live-paper-loading");
  if (loading) loading.hidden = true;
  const header = document.getElementById("live-paper-bundle-header");
  const diagnostics = document.getElementById(
    "live-paper-bundle-diagnostics"
  );
  const pre = document.getElementById("live-paper-bundle-info");
  if (pre) {
    pre.textContent = JSON.stringify(payload, null, 2);
  }
  if (diagnostics) diagnostics.hidden = false;
  if (!header) return;
  header.hidden = false;
  header.textContent = "";
  if (payload && payload.error) {
    header.className = "lp-bundle-header lp-bundle-error";
    header.textContent = "Couldn't load bundle info: " + payload.error;
    return;
  }
  header.className = "lp-bundle-header";
  const ps = (payload && payload.paper_state) || {};
  const title = document.createElement("strong");
  title.className = "lp-bundle-title";
  title.textContent = ps.header_label || ps.stage || "Live paper";
  header.appendChild(title);
  const meta = document.createElement("span");
  meta.className = "lp-bundle-meta";
  const parts = [];
  if (ps.journal) parts.push(ps.journal);
  if (ps.doi) parts.push(ps.doi);
  if (payload && payload.manuscript) parts.push(payload.manuscript);
  if (payload && payload.claim_count != null)
    parts.push(payload.claim_count + " claims");
  meta.textContent = parts.join(" · ");
  header.appendChild(meta);
}

export function ensurePdfContainer(rootEl) {
  let host = document.getElementById("live-paper-pdf");
  if (!host) {
    host = document.createElement("div");
    host.id = "live-paper-pdf";
    host.className = "live-paper-pdf";
    rootEl.appendChild(host);
  }
  return host;
}

export function ensureClaimsSidebar(rootEl) {
  let host = document.getElementById("live-paper-claims");
  if (!host) {
    host = document.createElement("aside");
    host.id = "live-paper-claims";
    host.className = "live-paper-claims";
    rootEl.appendChild(host);
  }
  return host;
}

export function renderError(message) {
  const container = document.getElementById("live-paper-bundle-info");
  if (container) {
    container.textContent = JSON.stringify({ error: message }, null, 2);
  }
}

export function cssEscape(value) {
  // Minimal CSS attribute-value escape. clew claim_ids are
  // alphanumerics + _ + - in practice, but we cover the corner case
  // when the runtime exposes CSS.escape() and fall back to a manual
  // replace otherwise.
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") {
    return CSS.escape(value);
  }
  return String(value).replace(/(["\\])/g, "\\$1");
}
