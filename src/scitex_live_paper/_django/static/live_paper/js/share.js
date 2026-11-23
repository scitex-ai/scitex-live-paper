export function bindShare(root) {
  const share = root.querySelector(".lp-share");
  const page = new URL(location.href);
  const project = root.dataset.viewProject || page.searchParams.get("project");
  if (page.searchParams.has("working_dir") && !root.dataset.viewProject) return;

  const button = share.querySelector("button");
  const status = share.querySelector('[role="status"]');
  const input = share.querySelector("input");
  share.hidden = false;
  button.addEventListener("click", async () => {
    const link = new URL(page.pathname, page.origin);
    if (project) link.searchParams.set("project", project);
    link.searchParams.set("shared", "1");
    const panel = root.querySelector("#lp-selection-panel:not([hidden])");
    const claim = panel?.closest("#live-paper-claims").dataset.pinnedClaim;
    if (claim) link.searchParams.set("claim", claim);
    input.hidden = true;
    try {
      await navigator.clipboard.writeText(link.href);
      status.textContent = claim ? "Claim link copied." : "Paper link copied.";
    } catch {
      input.value = link.href;
      input.hidden = false;
      input.focus();
      input.select();
      status.textContent = "Copy the selected link.";
    }
  });
  return status;
}

export function openSharedClaim(root, claims, status) {
  const params = new URL(location.href).searchParams;
  const claim = params.get("claim");
  if (params.get("shared") !== "1" || !claim) return;
  if (!claims.some((entry) => entry.claim_id === claim)) {
    if (status) status.textContent = "This claim is unavailable in the current paper.";
    return;
  }
  const anchor = root.querySelector('[data-overlay-id="' + CSS.escape(claim) + '"]');
  if (anchor) {
    anchor.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
    anchor.click();
  } else {
    root.dispatchEvent(new CustomEvent("live-paper:claim", { bubbles: true, detail: { id: claim } }));
  }
  const toggle = root.querySelector(".lp-reader-evidence-toggle");
  if (getComputedStyle(toggle).display !== "none" && toggle.getAttribute("aria-expanded") === "false") {
    toggle.click();
  }
}
