// Event-log sidecar — client-side replay log for the overlay.
//
// Per CCT 3000 the archive keeps `manuscript.pdf + event-log sidecar`
// so an overlay session can be replayed. This module is the
// collection half: it records every `live-paper:*` bus event with a
// timestamp and exports the log as a JSON sidecar the operator can
// archive next to the PDF. Print/export strips the overlay (see
// `viewer.css` `@media print`); this log is what survives.
//
// Vanilla ES module — no build step.

export function createEventLog() {
  return [];
}

export function recordEvent(log, kind, payload) {
  const entry = {
    ts: new Date().toISOString(),
    kind,
    payload: payload || {},
  };
  log.push(entry);
  return entry;
}

export function exportSidecar(log, meta) {
  return {
    schema: "scitex-live-paper.event-log/v1",
    exported_at: new Date().toISOString(),
    bundle: (meta && meta.bundle) || null,
    events: Array.isArray(log) ? log.slice() : [],
  };
}

export function downloadSidecar(log, meta, filename) {
  const sidecar = exportSidecar(log, meta);
  const blob = new Blob([JSON.stringify(sidecar, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "live-paper-events.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return sidecar;
}

/**
 * Persist the sidecar server-side via `POST <apiBase>event-log`.
 *
 * Sends the `exportSidecar()` shape; the server validates it and
 * stores it as `live-paper-events.json` in the bundle directory
 * (the archive half of "PDF + event-log sidecar"). Resolves to
 * `{ sidecar, receipt }` where `receipt` is the server's JSON
 * answer (`{ ok, event_count, filename, received_at }`). Rejects
 * when the POST fails — callers decide whether the archive action
 * retries or just keeps the client-download path.
 */
export async function persistSidecar(log, meta, options) {
  const apiBase = (options && options.apiBase) || "/api/";
  const sidecar = exportSidecar(log, meta);
  const response = await fetch(apiBase + "event-log", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sidecar),
  });
  if (!response.ok) {
    throw new Error(
      "persistSidecar failed: HTTP " + response.status
    );
  }
  const receipt = await response.json();
  return { sidecar, receipt };
}

/**
 * Subscribe to the `live-paper:*` bus on *rootEl* and record every
 * evidence/figure event into *log*. Returns an unbind function.
 */
export function bindEventLog(rootEl, log, meta) {
  const kinds = [
    "live-paper:claim",
    "live-paper:evidence-request",
    "live-paper:evidence-response",
  ];
  const handler = (event) => {
    recordEvent(log, event.type, event.detail || {});
  };
  for (const kind of kinds) {
    rootEl.addEventListener(kind, handler);
  }
  void meta;
  return () => {
    for (const kind of kinds) {
      rootEl.removeEventListener(kind, handler);
    }
  };
}
