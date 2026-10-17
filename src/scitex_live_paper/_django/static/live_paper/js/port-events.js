// Port-events bus — DOM side of the contract §3 envelope.
// Vanilla ES module.
//
// Flow: any `[data-lp-port]` element (claim row, PDF overlay region,
// DAG node) emits `live-paper:evidence-request` on click; this module
// fetches `apiBase + "port/<port>/<target>"` and renders the returned
// fragment (title/html/provenance) in a popup. The core positions the
// popup and draws the chrome; the FRAGMENT comes from the port.
//
// Until adapters are injected the backend 404s and the popup says so
// loudly — never an empty popup.

export function bindPortEvents(rootEl, apiBase) {
  rootEl.addEventListener("click", (event) => {
    const hit = event.target.closest("[data-lp-port]");
    if (!hit || !rootEl.contains(hit)) return;
    const port = hit.getAttribute("data-lp-port");
    const target = hit.getAttribute("data-lp-target");
    if (!port || !target) return;
    rootEl.dispatchEvent(
      new CustomEvent("live-paper:evidence-request", {
        bubbles: true,
        detail: { port, target },
      })
    );
  });

  rootEl.addEventListener("live-paper:evidence-request", (event) => {
    const { port, target } = event.detail || {};
    if (!port || !target) return;
    const url = apiBase + "port/" + encodeURIComponent(port) + "/" + encodeURIComponent(target);
    fetch(url, { headers: { Accept: "application/json" } })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(body.error || ("port request failed: " + response.status));
        }
        rootEl.dispatchEvent(
          new CustomEvent("live-paper:evidence-response", {
            bubbles: true,
            detail: { port, target, fragment: body },
          })
        );
        renderEvidencePopup(rootEl, body);
      })
      .catch((err) => {
        renderEvidencePopup(rootEl, {
          title: port + ":" + target,
          html: "<p class=\"lp-evidence-error\">Evidence unavailable.</p>",
          provenance: [],
          _error: String(err),
        });
      });
  });
}

export function renderEvidencePopup(rootEl, fragment) {
  closeEvidencePopup(rootEl);
  const popup = document.createElement("div");
  popup.className = "lp-evidence-popup";
  popup.setAttribute("role", "dialog");

  const title = document.createElement("div");
  title.className = "lp-evidence-title";
  title.textContent = fragment.title || "evidence";
  popup.appendChild(title);

  const body = document.createElement("div");
  body.className = "lp-evidence-body";
  body.innerHTML = fragment.html || "";
  popup.appendChild(body);

  const provenance = Array.isArray(fragment.provenance) ? fragment.provenance : [];
  if (provenance.length > 0) {
    const list = document.createElement("ul");
    list.className = "lp-evidence-provenance";
    for (const link of provenance) {
      const item = document.createElement("li");
      const anchor = document.createElement("a");
      anchor.href = link.href || "#";
      anchor.textContent = link.label || link.href || "(link)";
      item.appendChild(anchor);
      list.appendChild(item);
    }
    popup.appendChild(list);
  } else {
    const note = document.createElement("p");
    note.className = "lp-evidence-no-provenance";
    note.textContent = fragment._error || "No provenance links.";
    popup.appendChild(note);
  }

  const close = document.createElement("button");
  close.className = "lp-evidence-close";
  close.type = "button";
  close.textContent = "Close";
  close.addEventListener("click", () => closeEvidencePopup(rootEl));
  popup.appendChild(close);

  rootEl.appendChild(popup);
  return popup;
}

export function closeEvidencePopup(rootEl) {
  const open = rootEl.querySelector(":scope > .lp-evidence-popup");
  if (open) open.remove();
}
