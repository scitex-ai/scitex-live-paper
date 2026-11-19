/* scitex-live-paper / paper page: the evidence panel's content.
 *
 * A CLASSIC script (module scripts do not run from file://). Defines
 * window.LivePaperPanel.render(ctx, claim), used by paper.js. It fills the
 * panel with: state + reason, stated vs source value, source + locator,
 * where the evidence broke, previous / next / next-needing-inspection
 * buttons, and the claim's minimal evidence graph drawn inline with the
 * vendored mermaid (the exact source the graph page draws, so failing nodes
 * carry the same dash-dot outline and "⚠ KIND" line). Selecting a graph node
 * (click, Enter, Space, or the node list) shows its file, hash, run and
 * failure mark.
 *
 * Every value from the data is inserted as text, never HTML; only mermaid's
 * own SVG output is inserted as markup.
 */
(function () {
  'use strict';

  var FAILURE_MARK = '⚠';
  var KIND_TITLE = {
    claim: 'Claim',
    process: 'Processing run',
    input: 'Input file',
    output: 'Output file',
    other: 'Node',
  };
  var renderSeq = 0;
  var mermaidReady = false;

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'text') node.textContent = v;
      else node.setAttribute(k, v === true ? '' : v);
    });
    (children || []).forEach(function (ch) {
      if (ch !== null && ch !== undefined && ch !== false) node.append(ch);
    });
    return node;
  }

  function fmt(value) {
    if (value && typeof value === 'object' && !Array.isArray(value) &&
        Object.keys(value).length === 1 && Object.prototype.hasOwnProperty.call(value, 'value')) {
      value = value.value;
    }
    if (typeof value === 'string') return value;
    try { return JSON.stringify(value); } catch (e) { return String(value); }
  }

  function same(a, b) {
    try { return JSON.stringify(a) === JSON.stringify(b); } catch (e) { return a === b; }
  }

  function present(v) { return v !== null && v !== undefined; }

  function reducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  // ------------------------------------------------------------ ordering

  function step(order, id, delta) {
    if (!order.length) return null;
    var at = order.indexOf(id);
    if (at < 0) return delta > 0 ? order[0] : order[order.length - 1];
    var next = at + delta;
    return next >= 0 && next < order.length ? order[next] : null;
  }

  function nextInspection(order, id) {
    if (!order.length) return null;
    var next = order[(order.indexOf(id) + 1) % order.length];
    return next === id ? null : next;
  }

  // ------------------------------------------------------------- graph data

  function failureLabel(c, n) {
    var f = (c.failing_nodes || []).filter(function (x) { return x.id === n.id; })[0];
    return f ? f.failure_label : (n.failure ? n.failure.kind : null);
  }

  function nodeName(c, i) {
    var n = c.graph.nodes[i];
    var f = n.failure ? failureLabel(c, n) : null;
    return (KIND_TITLE[n.kind] || n.kind) + ' ' + n.label +
      (f ? ' — ' + FAILURE_MARK + ' evidence broke here: ' + f : '');
  }

  /** Index of the node the claim's value comes from (its source file). */
  function sourceNode(c) {
    var g = c.graph;
    var file = c.source && c.source.file;
    if (!g || !g.nodes) return null;
    var pick = function (pred) {
      for (var i = 0; i < g.nodes.length; i++) if (pred(g.nodes[i])) return i;
      return -1;
    };
    var i = file ? pick(function (n) { return n.kind === 'output' && n.label === file; }) : -1;
    if (i < 0 && file) i = pick(function (n) { return n.label === file; });
    if (i < 0) {
      var ci = pick(function (n) { return n.kind === 'claim'; });
      var claimId = ci >= 0 ? g.nodes[ci].id : null;
      var edge = (g.edges || []).filter(function (e) { return e.target === claimId; })[0];
      if (edge) i = pick(function (n) { return n.id === edge.source; });
    }
    return i >= 0 ? i : null;
  }

  function nodeDetails(c, i) {
    var g = c.graph;
    var n = g.nodes[i];
    var byNode = {};
    g.nodes.forEach(function (x) { byNode[x.id] = x; });
    var labels = function (ids) { return ids.map(function (id) { return byNode[id] ? byNode[id].label : id; }); };
    var procs = function (ids) { return ids.filter(function (id) { return byNode[id] && byNode[id].kind === 'process'; }); };
    var into = g.edges.filter(function (e) { return e.target === n.id; }).map(function (e) { return e.source; });
    var outOf = g.edges.filter(function (e) { return e.source === n.id; }).map(function (e) { return e.target; });

    var dl = el('dl');
    var row = function (term, value, plain) {
      dl.append(el('dt', { text: term }), el('dd', {}, [plain ? value : el('code', { text: value })]));
    };
    if (n.kind === 'process') {
      row('Run', n.label);
      row('Reads', labels(into).join(', ') || '(none recorded)');
      row('Writes', labels(outOf).join(', ') || '(none recorded)');
    } else if (n.kind === 'claim') {
      row('Claim', n.label);
      row('State', c.symbol + ' ' + c.label, true);
      row('Rests on', labels(into).join(', ') || '(nothing)');
    } else {
      row('File', n.label);
      row('Hash', n.hash || '(no hash recorded)');
      var producedBy = labels(procs(into));
      var readBy = labels(procs(outOf));
      if (producedBy.length) row('Produced by run', producedBy.join(', '));
      if (readBy.length) row('Read by run', readBy.join(', '));
      if (!producedBy.length && !readBy.length) row('Run', '(none in this graph)', true);
    }
    if (n.external) row('External', 'yes', true);
    if (n.failure) {
      row('Evidence broke here', FAILURE_MARK + ' ' + failureLabel(c, n) +
        (n.failure.detail ? ' — ' + n.failure.detail : ''), true);
    }
    return el('div', { class: 'lp-node-details', 'data-lp-failure': n.failure ? n.failure.kind : null }, [
      el('h4', { text: (KIND_TITLE[n.kind] || n.kind) + (n.failure ? ' — ' + FAILURE_MARK + ' evidence broke here' : '') }),
      dl,
    ]);
  }

  // ------------------------------------------------------------- sections

  function renderValues(c) {
    var src = c.source || {};
    var dl = el('dl', { class: 'lp-claim-values' });
    var row = function (term, dd) { dl.append(el('dt', { text: term }), dd); };
    var absent = function (text) { return el('dd', {}, [el('span', { class: 'lp-value-absent', text: text })]); };
    var code = function (text) { return el('dd', {}, [el('code', { text: text })]); };
    row('Stated value', present(c.stated_value) ? code(fmt(c.stated_value)) : absent('not stated'));
    if (src.value_reported) {
      var differs = present(c.stated_value) && !same(src.value, c.stated_value);
      row('Source value', el('dd', { class: differs ? 'lp-value-differs' : null }, [
        el('code', { text: fmt(src.value) }),
        differs ? el('strong', { text: ' ≠ differs from the stated value' }) : null,
      ]));
    } else {
      row('Source value', absent('not reported by the evidence provider'));
    }
    row('Source', src.file ? code(src.file) : absent('none linked'));
    row('Locator', present(src.locator) ? code(fmt(src.locator)) : absent('none'));
    if (c.location && c.location.file) {
      row('In the text', code(c.location.file + (c.location.line ? ':' + c.location.line : '')));
    }
    var st = c.provider_status;
    if (st && st.name) row('Provider verdict', code(st.name + (present(st.code) ? ' (' + st.code + ')' : '')));
    return dl;
  }

  function renderBroke(c, select) {
    var nodes = (c.graph && c.graph.nodes) || [];
    var items = (c.failing_nodes || []).map(function (f) {
      var idx = nodes.findIndex(function (n) { return n.id === f.id; });
      var btn = null;
      if (idx >= 0) {
        btn = el('button', { type: 'button', class: 'lp-failing-node-show', text: 'Details' });
        btn.addEventListener('click', function () { select(idx, true); });
      }
      return el('li', { class: 'lp-failing-node', 'data-failure': f.failure, 'data-node-id': f.id }, [
        el('span', { class: 'lp-failure-badge', text: FAILURE_MARK + ' ' + f.failure_label }), ' ',
        f.kind + ' ', el('code', { text: f.label }), f.detail ? ' · ' + f.detail : '', ' ', btn,
      ]);
    });
    var n = items.length;
    return el('div', { class: 'lp-claim-evidence-broke', role: 'group', 'aria-label': 'Where the evidence broke' }, [
      el('p', {
        class: 'lp-claim-evidence-broke-title',
        text: 'Where the evidence broke (' + n + ' node' + (n === 1 ? '' : 's') + ', outlined dash-dot in the graph):',
      }),
      el('ul', { class: 'lp-failing-nodes' }, items),
    ]);
  }

  function svgNodeIndex(g) {
    var m = /^n(\d+)$/.exec(g.getAttribute('data-id') || '') ||
      /flowchart-n(\d+)-\d+$/.exec(g.id || '');
    return m ? Number(m[1]) : -1;
  }

  function drawGraph(ctx, c, holder, select) {
    var mm = window.mermaid;
    if (!mm || typeof mm.render !== 'function') {
      holder.textContent = 'The graph drawing library did not load; the graph’s nodes are listed below.';
      return;
    }
    if (!mermaidReady) {
      mm.initialize({ startOnLoad: false, securityLevel: 'strict' });
      mermaidReady = true;
    }
    var seq = ++renderSeq;
    holder.textContent = 'Drawing the evidence graph…';
    // Same nodes, edges and classes as the graph page; only the direction
    // turns top-down so the graph stays legible in a narrow panel.
    var source = c.mermaid.replace(/^graph LR\b/, 'graph TD');
    Promise.resolve()
      .then(function () { return mm.render('lp-panel-graph-' + seq, source); })
      .then(function (out) {
        if (seq !== renderSeq || !ctx.isCurrent(c.claim_id)) return;
        holder.innerHTML = out.svg;
        holder.querySelectorAll('g.node').forEach(function (gn) {
          var i = svgNodeIndex(gn);
          var n = c.graph.nodes[i];
          if (!n) return;
          gn.setAttribute('data-lp-node-index', String(i));
          gn.setAttribute('data-lp-node-kind', n.kind);
          if (n.failure) gn.setAttribute('data-lp-failure', n.failure.kind);
          gn.setAttribute('tabindex', '0');
          gn.setAttribute('role', 'button');
          gn.setAttribute('aria-pressed', 'false');
          gn.setAttribute('aria-label', nodeName(c, i));
          gn.addEventListener('click', function () { select(i, false); });
          gn.addEventListener('keydown', function (ev) {
            if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(i, false); }
          });
        });
        holder.setAttribute('data-lp-rendered', '');
      })
      .catch(function (err) {
        if (seq !== renderSeq) return;
        holder.textContent = 'The graph could not be drawn (' + ((err && err.message) || err) +
          '); its nodes are listed below.';
      });
  }

  function graphSection(ctx, c, select, refs) {
    var out = [el('h3', { text: 'Minimal evidence graph' })];
    if (!(c.graph && c.mermaid)) {
      out.push(el('p', {
        class: 'lp-dag-empty',
        text: 'No evidence graph for this claim' + (c.graph_error ? ': ' + c.graph_error : '') + '.',
      }));
      return out;
    }
    if (c.graph.summary) out.push(el('p', { class: 'lp-graph-summary', text: c.graph.summary }));
    refs.graph = el('div', {
      class: 'lp-claim-graph', role: 'group',
      'aria-label': 'Minimal evidence graph (the node list below has the same nodes)',
    });
    refs.list = el('ul', { class: 'lp-graph-node-list', 'aria-label': 'Graph nodes' },
      c.graph.nodes.map(function (n, i) {
        var b = el('button', {
          type: 'button', 'data-lp-node-index': String(i), 'aria-pressed': 'false',
          'data-lp-failure': n.failure ? n.failure.kind : null,
        }, [
          el('span', { class: 'lp-node-kind', text: KIND_TITLE[n.kind] || n.kind }),
          el('span', { class: 'lp-node-label', text: n.label }),
          n.failure ? el('span', { class: 'lp-failure-badge', text: FAILURE_MARK + ' ' + failureLabel(c, n) }) : null,
        ]);
        b.addEventListener('click', function () { select(i, false); });
        return el('li', {}, [b]);
      }));
    out.push(refs.graph,
      el('p', { class: 'lp-graph-hint', text: 'Select a node (in the graph or below) for its file, hash and run.' }),
      refs.list, refs.details);
    drawGraph(ctx, c, refs.graph, select);
    return out;
  }

  // ---------------------------------------------------------------- panel

  /**
   * Fill the panel for claim *c*.
   * ctx: {titleEl, body, readingOrder, inspectionOrder, inText(id),
   *       isCurrent(id), navigate(id)}
   */
  function render(ctx, c) {
    renderSeq++;
    ctx.titleEl.textContent = '';
    ctx.titleEl.append(
      el('span', { class: 'lp-support-badge', 'data-support': c.state, text: c.symbol + ' ' + c.label }),
      ' Claim ', el('code', { text: c.claim_id }));
    var body = ctx.body;
    body.textContent = '';

    var ri = ctx.readingOrder.indexOf(c.claim_id);
    var ii = ctx.inspectionOrder.indexOf(c.claim_id);
    var nInsp = ctx.inspectionOrder.length;
    body.append(el('p', {
      class: 'lp-claim-panel-position',
      text: 'Claim ' + (ri + 1) + ' of ' + ctx.readingOrder.length + ' in reading order · ' +
        (ii >= 0 ? (ii + 1) + ' of ' + nInsp + ' needing inspection' : 'supported (' + nInsp + ' need inspection)') +
        (ctx.inText(c.claim_id) ? '' : ' · not found in the rendered text'),
    }));

    // Node selection is shared by the SVG, the node list, and the
    // "where the evidence broke" list.
    var refs = { graph: null, list: null, details: el('div', { class: 'lp-node-details-host', 'aria-live': 'polite' }) };
    function select(i, focusList) {
      if (!c.graph || !c.graph.nodes[i]) return;
      [refs.graph, refs.list].forEach(function (root) {
        if (!root) return;
        root.querySelectorAll('[data-lp-node-index]').forEach(function (x) {
          x.setAttribute('aria-pressed', x.getAttribute('data-lp-node-index') === String(i) ? 'true' : 'false');
        });
      });
      refs.details.textContent = '';
      refs.details.append(nodeDetails(c, i));
      var btn = refs.list && refs.list.querySelector('[data-lp-node-index="' + i + '"]');
      if (focusList && btn) btn.focus();
      refs.details.scrollIntoView({ block: 'nearest', behavior: reducedMotion() ? 'auto' : 'smooth' });
    }

    var navBtn = function (label, cls, target) {
      var b = el('button', { type: 'button', class: cls, text: label });
      if (target === null) b.disabled = true;
      else {
        b.setAttribute('data-target-claim', target);
        b.addEventListener('click', function () { ctx.navigate(target); });
      }
      return b;
    };
    var srcIdx = sourceNode(c);
    var srcBtn = null;
    if (srcIdx !== null) {
      srcBtn = el('button', { type: 'button', class: 'lp-source-node-btn', text: 'Source node details' });
      srcBtn.addEventListener('click', function () { select(srcIdx, true); });
    }
    body.append(el('div', { class: 'lp-claim-panel-nav', role: 'group', 'aria-label': 'Claim navigation' }, [
      navBtn('← Previous claim', 'lp-prev-claim', step(ctx.readingOrder, c.claim_id, -1)),
      navBtn('Next claim →', 'lp-next-claim', step(ctx.readingOrder, c.claim_id, 1)),
      navBtn(FAILURE_MARK + ' Next needing inspection', 'lp-next-inspection',
        nextInspection(ctx.inspectionOrder, c.claim_id)),
      srcBtn,
      c.graph_url ? el('a', { href: c.graph_url, class: 'lp-graph-page-link', text: 'Open full graph page ↗' }) : null,
    ]));

    if (c.stated_text) body.append(el('p', { class: 'lp-claim-panel-quote' }, [el('q', { text: c.stated_text })]));
    body.append(el('p', { class: 'lp-claim-panel-reason' }, [el('strong', { text: 'Reason: ' }), c.reason]));
    body.append(el('h3', { text: 'Stated vs source' }), renderValues(c));
    if (c.failing_nodes && c.failing_nodes.length) body.append(renderBroke(c, select));
    if (c.details && c.details.length) {
      body.append(el('ul', { class: 'lp-claim-evidence-details' },
        c.details.map(function (d) { return el('li', { text: d }); })));
    }
    graphSection(ctx, c, select, refs).forEach(function (n) { body.append(n); });
    body.scrollTop = 0;
  }

  window.LivePaperPanel = {
    render: render,
    /** Drop any graph still being drawn (the panel closed or moved on). */
    cancel: function () { renderSeq++; },
  };
})();
