/** Present hash-verified SciTeX Stats results as readable evidence. */
const MISSING = "—";

function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function number(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return MISSING;
  return value !== 0 && Math.abs(value) < 0.001
    ? value.toExponential(3)
    : Number(value.toPrecision(5)).toString();
}

function effect(row) {
  if (typeof row.effect_size !== "number") return MISSING;
  const result = [row.effect_size_metric, number(row.effect_size)].filter(Boolean).join(" ");
  const interval = Array.isArray(row.effect_ci) ? row.effect_ci.map(number).join(" – ") : "";
  return interval ? result + " [" + interval + "]" : result;
}

function resultTable(rows) {
  const wrap = element("div");
  wrap.className = "lp-stats-table-scroll";
  const table = element("table");
  const header = table.createTHead().insertRow();
  const hasInterval = rows.some((row) => Array.isArray(row?.ci));
  const headers = ["Test", "Role", "Statistic", "df", "p", "Effect size"];
  if (hasInterval) headers.push("Confidence interval");
  for (const label of headers) {
    const heading = element("th", label);
    heading.scope = "col";
    header.append(heading);
  }
  const body = table.createTBody();
  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const values = [
      row.method || row.label || row.test_method || row.test || MISSING,
      typeof row.role === "string" && row.role ? row.role[0].toUpperCase() + row.role.slice(1) : MISSING,
      number(row.statistic),
      Array.isArray(row.df) ? row.df.map(number).join(", ") : number(row.df),
      number(row.p_value ?? row.pvalue),
      effect(row),
    ];
    if (hasInterval) values.push(Array.isArray(row.ci) ? row.ci.map(number).join(" – ") : MISSING);
    const tr = body.insertRow();
    for (const value of values) tr.insertCell().textContent = value;
  }
  wrap.append(table);
  return wrap;
}

function appendApa(node, segments, plain) {
  if (!Array.isArray(segments) || !segments.length) {
    node.textContent = plain;
    return;
  }
  for (const segment of segments) {
    if (typeof segment?.text !== "string") continue;
    const tag = { sym: "i", sup: "sup", sub: "sub" }[segment.kind];
    node.append(tag ? element(tag, segment.text) : segment.text);
  }
}

function detailedResult(row, open) {
  const rows = row.apa_table ?? row.apa?.table;
  if (!Array.isArray(rows) || !rows.length) return null;
  const detail = element("details");
  detail.open = open;
  detail.append(element("summary", row.method || row.label || row.test_method || row.test));
  const table = element("table");
  const body = table.createTBody();
  for (const row of rows) {
    if (typeof row?.label_plain !== "string" || typeof row.value_plain !== "string") continue;
    const tr = body.insertRow();
    const label = element("th");
    label.scope = "row";
    const value = element("td");
    appendApa(label, row.label, row.label_plain);
    appendApa(value, row.value, row.value_plain);
    tr.append(label, value);
  }
  detail.append(table);
  return detail;
}

export function renderStatistics(panel, data, loadPlot) {
  if (!data || typeof data !== "object") return;
  const card = element("section");
  card.className = "lp-stats-card";
  card.setAttribute("aria-label", "SciTeX Stats");
  card.append(element("h3", "SciTeX Stats"));
  if (data.missing_effect_sizes?.length) {
    const incomplete = element("p", "Incomplete report · effect size required for " + data.missing_effect_sizes.join(", "));
    incomplete.setAttribute("role", "status");
    card.append(incomplete);
  }
  const comparisons = Object.values(data.comparisons || {});
  for (const study of comparisons) {
    if (!study || !Array.isArray(study.results) || !study.results.length) continue;
    const group = element("section");
    if (study.title) group.append(element("h4", study.title));
    if (study.note) group.append(element("p", study.note));
    const first = study.results[0] || {};
    const alpha = study.alpha ?? first.alpha;
    const power = study.power ?? first.power;
    const beta = study.beta ?? first.beta;
    const thresholds = ["α " + number(alpha), "β " + (Number.isFinite(beta) ? number(beta) : "not estimated")];
    if (Number.isFinite(power)) thresholds.push("Power " + number(power));
    group.append(element("p", thresholds.join(" · ")), resultTable(study.results));
    for (const row of study.results) {
      const line = row?.apa_plain ?? row?.apa?.plain;
      if (typeof line === "string" && line) {
        const report = element("p");
        appendApa(report, row.apa_segments ?? row.apa?.segments, line);
        report.className = "lp-stats-reported-line";
        group.append(report);
      }
    }

    for (const [index, row] of study.results.entries()) {
      if (!row || typeof row !== "object") continue;
      const details = detailedResult(row, index === 0);
      if (details) group.append(details);
    }

    const check = study.assumptions;
    if (Number.isFinite(check?.min_expected)) {
      group.append(element("p",
        "Expected counts · minimum " + number(check.min_expected) +
        " · " + check.cells_below + " of " + check.cells + " below " + number(check.threshold)));
    } else if (Number.isFinite(first.expected_min)) {
      group.append(element("p", "Minimum expected count · " + number(first.expected_min)));
    }
    const checks = study.checks;
    if (Array.isArray(checks?.normality?.samples)) {
      for (const sample of checks.normality.samples) {
        if (!sample || !Number.isFinite(sample.p)) continue;
        group.append(element("p",
          "Shapiro–Wilk · " + sample.sample + " · W " + number(sample.W) + " · p " + number(sample.p)));
      }
    }
    const variance = checks?.equal_variance?.brown_forsythe;
    if (Number.isFinite(variance?.p)) {
      group.append(element("p", "Brown–Forsythe · F " + number(variance.statistic) + " · p " + number(variance.p)));
    }
    if (study.agreement) group.append(element("p", study.agreement));
    if (typeof study.visual === "string" && loadPlot) {
      const plot = element("figure");
      loadPlot(study.visual, plot, study.title, study.visual_sha256);
      group.append(plot);
    }
    card.append(group);
  }
  panel.append(card);
}
