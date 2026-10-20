// Friendly empty state — shown when the viewer has no paper to show.
//
// The mount wrapper renders the viewer shell with `data-empty-reason`
// (HTTP 200) when the resolver could not find a bundle, instead of a
// bare-text 404 the operator cannot act on. This module turns that
// reason into guidance: how to open a paper (host file browser, or a
// direct `?working_dir=` deep link).
//
// Vanilla ES module — no build step.

export function isMissingPaper(reason) {
  return /no paper selected|bundle not found|bundle path|not pinned/i.test(
    String(reason || "")
  );
}

export function renderEmptyState(rootEl, reason) {
  const host =
    rootEl.querySelector(".live-paper-status") || rootEl;
  const panel = document.createElement("section");
  panel.className = "lp-empty-state";
  const title = document.createElement("h2");
  title.textContent = "No paper selected";
  const detail = document.createElement("p");
  detail.className = "lp-empty-reason";
  detail.textContent = String(reason || "No bundle is attached to this view.");
  const help = document.createElement("p");
  help.className = "lp-empty-help";
  help.textContent =
    "Open a paper from your workspace file browser, or append " +
    "?working_dir=/absolute/path/to/bundle to this URL.";
  panel.appendChild(title);
  panel.appendChild(detail);
  panel.appendChild(help);
  host.appendChild(panel);
  return panel;
}
