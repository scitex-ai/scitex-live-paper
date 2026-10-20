// Archive action — the "PDF + event-log sidecar" half of CCT 3000.
//
// Renders the Archive button into the viewer header. On click it
// persists the session event log server-side (`POST <apiBase>event-log`,
// stored as `live-paper-events.json` next to `manuscript.pdf`) and
// falls back to a client download when the POST fails — the archive
// action always produces a sidecar either way. Status text next to
// the button reports the server receipt or the failure.
//
// Reads the session log from `rootEl._livePaperEventLog` (bound at
// boot in `viewer.js`) and bundle identity from
// `rootEl._livePaperBundle` (stashed at boot; may be absent when the
// boot RPCs failed — the sidecar then carries `bundle: null`).
//
// Vanilla ES module — no build step.

import { downloadSidecar, persistSidecar } from "./event-log.js";

export function renderArchiveButton(rootEl, apiBase) {
  const host =
    rootEl.querySelector(".live-paper-header") || rootEl;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "lp-archive-button";
  btn.textContent = "Archive event log";
  btn.addEventListener("click", () => {
    void archiveEventLog(btn, rootEl, apiBase);
  });
  const status = document.createElement("span");
  status.className = "lp-archive-status";
  status.setAttribute("aria-live", "polite");
  host.appendChild(btn);
  host.appendChild(status);
  return btn;
}

export async function archiveEventLog(btn, rootEl, apiBase) {
  const status =
    rootEl.querySelector(".lp-archive-status") ||
    btn.parentElement.querySelector(".lp-archive-status");
  const log = rootEl._livePaperEventLog || [];
  const meta = { bundle: rootEl._livePaperBundle || null };
  const count = Array.isArray(log) ? log.length : 0;
  btn.disabled = true;
  try {
    const { receipt } = await persistSidecar(log, meta, { apiBase });
    if (status) {
      status.textContent =
        "Archived " + count + " events (server: " + receipt.filename + ")";
    }
  } catch (err) {
    try {
      downloadSidecar(log, meta);
    } catch (dlErr) {
      if (status) {
        status.textContent = "Archive failed: " + String(err);
      }
      btn.disabled = false;
      return;
    }
    if (status) {
      status.textContent =
        "Saved " +
        count +
        " events (download — server persist failed: " +
        String(err) +
        ")";
    }
  }
  btn.disabled = false;
}
