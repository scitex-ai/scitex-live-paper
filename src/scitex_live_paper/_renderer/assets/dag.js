/* scitex-live-paper / M1 DAG navigator
 *
 * - Initialises vendored mermaid (UMD global `mermaid`) and renders
 *   the <pre class="mermaid"> source block on DOMContentLoaded.
 * - After mermaid finishes painting, walks the rendered <g class="node">
 *   elements and tags each with a data-lp-node-kind attribute derived
 *   from its label prefix (the node taxonomy: Source / Input /
 *   Processing / Output / Claim). The renderer does NOT redefine that
 *   taxonomy — it just looks at the label text mermaid drew.
 * - Wires clicks:
 *     - Claim node  → dispatch `live-paper:claim` CustomEvent
 *                     (same channel as the PDF viewer / sidebar) and
 *                     navigate to `<claims_url>#claim=<id>`.
 *     - Source / Processing node → open the small in-page overlay
 *                     with the script path + hash from the embedded
 *                     provenance map.
 */

const PROVENANCE = (() => {
  const el = document.getElementById('lp-provenance-map');
  if (!el) return {};
  try {
    return JSON.parse(el.textContent || '{}');
  } catch {
    return {};
  }
})();

// Label prefix → kind. Matches the DAG node-class taxonomy.
const KIND_PREFIXES = [
  ['claim', 'Claim'],
  ['source', 'Source'],
  ['processing', 'Processing'],
  ['input', 'Input'],
  ['output', 'Output'],
];

const FAILURE_MARK = '⚠';

function kindFromLabel(label) {
  if (!label) return null;
  const head = label.split(/<br\/?>|\n/, 1)[0].trim().toLowerCase();
  for (const [kind, prefix] of KIND_PREFIXES) {
    if (head === prefix.toLowerCase()) return kind;
  }
  return null;
}

function labelTextOfNode(node) {
  // mermaid 10.x renders text inside <foreignObject> spans OR <text>
  // tspans depending on theme. Concatenate either to recover the label.
  // Line breaks MUST survive: kindFromLabel keys on the first line, and
  // htmlLabels render <br/> as an element textContent drops
  // ("Inputdata/x" instead of "Input\ndata/x").
  const fo = node.querySelector('foreignObject');
  if (fo && fo.textContent) {
    const tmp = document.createElement('div');
    tmp.innerHTML = fo.innerHTML.replace(/<br\s*\/?>/gi, '\n');
    return tmp.textContent || '';
  }
  const spans = node.querySelectorAll('text tspan');
  if (spans.length) return Array.from(spans, (s) => s.textContent || '').join('\n');
  const ts = node.querySelector('text');
  return ts ? ts.textContent || '' : '';
}

function payloadFromLabel(label) {
  // Lines are mermaid-escaped <br/> separated. The second line carries
  // the renderer's per-kind payload: source script for Source /
  // Processing, claim_id for Claim, etc.
  // A failing node's label ends with a "⚠ KIND" marker (evidence
  // contract 1.1.0); it is display-only, never part of the payload.
  const parts = label.split(FAILURE_MARK, 1)[0].split(/<br\/?>|\n/).map((s) => s.trim());
  return parts.slice(1).filter(Boolean).join(' ');
}

function failureFromLabel(label) {
  const at = (label || '').indexOf(FAILURE_MARK);
  if (at < 0) return null;
  return label.slice(at + FAILURE_MARK.length).split(/<br\/?>|\n/, 1)[0].trim() || null;
}

function emitClaimEvent(id) {
  window.dispatchEvent(
    new CustomEvent('live-paper:claim', { detail: { id } })
  );
}

function openOverlay({ title, items }) {
  const overlay = document.getElementById('lp-dag-overlay');
  if (!overlay) return;
  const titleEl = overlay.querySelector('.lp-dag-overlay-title');
  const dl = overlay.querySelector('.lp-dag-overlay-detail');
  if (titleEl) titleEl.textContent = title || 'Node';
  if (dl) {
    dl.innerHTML = '';
    for (const [key, value] of items) {
      const dt = document.createElement('dt');
      dt.textContent = key;
      const dd = document.createElement('dd');
      const code = document.createElement('code');
      code.textContent = value;
      dd.appendChild(code);
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
  }
  overlay.removeAttribute('hidden');
}

function closeOverlay() {
  const overlay = document.getElementById('lp-dag-overlay');
  if (overlay) overlay.setAttribute('hidden', '');
}

function nodeClickHandler(kind, payload, shell, failure = null) {
  const broke = failure ? [['Evidence broke here', failure]] : [];
  return (ev) => {
    ev.preventDefault();
    if (kind === 'claim' && payload) {
      emitClaimEvent(payload);
      const claimsUrl = shell.dataset.claimsUrl || 'claims.html';
      // Same `#claim=<id>` protocol the viewer / sidebar speak.
      window.location.href = `${claimsUrl}#claim=${encodeURIComponent(payload)}`;
      return;
    }
    if (kind === 'source' || kind === 'processing') {
      const hash = PROVENANCE[payload];
      openOverlay({
        title: kind === 'source' ? 'Source script' : 'Processing script',
        items: [
          ['Script', payload || '(unknown)'],
          ['Hash', hash || '(no hash recorded)'],
          ...broke,
        ],
      });
      return;
    }
    if (kind === 'input' || kind === 'output') {
      // Per-claim evidence graphs embed {file label: hash} for files.
      const hash = PROVENANCE[payload];
      openOverlay({
        title: kind === 'input' ? 'Input file' : 'Output file',
        items: [
          ['File', payload || '(unknown)'],
          ['Hash', hash || '(no hash recorded)'],
          ...broke,
        ],
      });
      return;
    }
    // Unknown kinds: show label only.
    openOverlay({ title: 'Node', items: [['Label', payload || '(unlabeled)'], ...broke] });
  };
}

function decorateNodes(shell) {
  const nodes = document.querySelectorAll('g.node');
  nodes.forEach((node) => {
    const label = labelTextOfNode(node);
    const kind = kindFromLabel(label);
    if (!kind) return;
    node.setAttribute('data-lp-node-kind', kind);
    const payload = payloadFromLabel(label);
    const failure = failureFromLabel(label);
    if (failure) node.setAttribute('data-lp-failure', failure.toLowerCase());
    node.addEventListener('click', nodeClickHandler(kind, payload, shell, failure));
    node.style.cursor = 'pointer';
  });
}

async function bootstrap() {
  const shell = document.querySelector('.lp-dag-shell');
  if (!shell) return;

  if (typeof mermaid !== 'undefined' && mermaid?.initialize) {
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
    try {
      await mermaid.run({ querySelector: 'pre.mermaid' });
    } catch (err) {
      console.error('mermaid render failed:', err);
    }
  }

  decorateNodes(shell);

  const closeBtn = document.querySelector('.lp-dag-overlay-close');
  if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}

export {
  bootstrap,
  decorateNodes,
  kindFromLabel,
  payloadFromLabel,
};
