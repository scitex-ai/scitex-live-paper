/**
 * Static-export companion for the canonical SDK AppHeader (header-parity).
 *
 * The SDK `app-header.js` auto-mounts on DOMContentLoaded: it finds
 * `[data-stx-app-header]` and builds the `<header class="stx-app-header">`
 * row (title span, version badge, project slot, actions). This module —
 * loaded AFTER it — moves the page's static project label
 * (`[data-lp-static-project]`) into the canonical project slot once the
 * slot exists, mirroring what leaf JS does for the server-rendered
 * `{% scitex_project_picker %}` in the Django shell.
 *
 * Static export has no project provider, so the label is plain text
 * (no interactive picker). When the page carries no label there is
 * nothing to move and the slot stays empty.
 */

function moveStaticProject(root) {
  const doc = root.ownerDocument || document;
  const label = root.querySelector("[data-lp-static-project]");
  const slot = doc.querySelector(".stx-app-header__slot--project-selector");
  if (label && slot && label.parentElement !== slot) {
    slot.appendChild(label);
    return true;
  }
  return Boolean(!label || (label && slot && label.parentElement === slot));
}

for (const root of document.querySelectorAll("[data-stx-app-header]")) {
  if (moveStaticProject(root)) continue;
  const observer = new MutationObserver(() => {
    if (moveStaticProject(root)) observer.disconnect();
  });
  observer.observe(root.ownerDocument.documentElement, {
    childList: true,
    subtree: true,
  });
}
