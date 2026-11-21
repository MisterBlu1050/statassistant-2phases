/* StatAssistant 2-Phases — Bilingual NL / EN SPA Client (Palier 3) */

const I18N = {
  nl: {
    badge: "XL AI · 2-Fasen ZDR",
    tier_local: "🛡️ Local Expert (0 netwerkverkeer)",
    tier_auto: "⚙️ Autonoom Fase 1 (0 AI)",
    tier_zdr: "🏢 Vertrouwelijk / Enterprise ZDR",
    btn_gov: "Governance & Audit",
    btn_purge: "ZDR Wissen",
    step1: "Gegevens & AVG",
    step2: "Vraag & Plan",
    step3: "Fase 1 & Fase 2",
    step4: "Falsifieerbare export",
    h1_ingest: "1. Importeer uw gegevens <em>(Fase 1 — 0 % AI)</em>",
    lead_ingest: "Deterministische Python/SciPy-berekening. Individuele rijen worden nooit naar een LLM verzonden.",
    tab_file: "📁 Bestand (CSV, TSV, XLSX)",
    tab_paste: "📋 Tabel plakken",
    btn_sample: "✨ Voorbeelddataset laden",
    llm_panel_title: "🏢 Enterprise / ZDR LLM-configuratie (alleen geaggregeerde JSON)",
    drop_label: "Sleep uw bestand hierheen of klik om te kiezen",
    drop_sub: "CSV · TSV · Excel (.xlsx) — scheidingsteken en decimaal worden automatisch herkend",
    paste_ph: "Plak uw CSV/TSV-tabel hier…",
    btn_load_paste: "Geplakte gegevens laden",
    import_opts: "⚙️ Importinstellingen (ontbrekende codes, scheidingsteken)",
    opt_sep: "Scheidingsteken",
    opt_dec: "Decimaal",
    opt_missing: "Ontbrekende codes",
    preview_sum: "🔍 Voorbeeld (eerste 5 rijen) & kolomtypen",
    h2_plan: "2. Uw onderzoeksvraag",
    q_ph: "Stel een enkelvoudige of meervoudige vraag (bijv. Verlaagt de maatregel de doorlooptijd, en hangen incidenten af van de audit?)",
    opt_alpha: "Drempel α",
    btn_detect: "⚡ Analyses detecteren",
    btn_run_all: "▶️ Fase 1 & Fase 2 uitvoeren",
    manual_sum: "🎛️ Handmatige Expertmodus (Logistisch, Correlaties, Herhaalde metingen, ANOVA…)",
    man_method: "Methode",
    man_y: "Doelvariabele (Y)",
    man_x: "Factor(en) / Voorspeller(s) (X)",
    btn_run_man: "▶️ Handmatige analyse starten",
    h2_res: "3. Gecertificeerde resultaten (Fase 1) & Interpretatie (Fase 2)",
    h2_exp: "4. Falsifieerbaar rapport exporteren",
    lead_exp: "Dubbele SHA-256-vingerafdruk (origineel + geanonimiseerd), gecertificeerde omgeving en volledige reproduceerbaarheid.",
    exp_pdf: "📕 PDF-rapport (grafieken)",
    exp_docx: "📘 Word-rapport (.docx)",
    exp_md: "📄 Markdown (.md)",
    exp_py: "🐍 Python-script (.py)",
    gov_title: "🛡️ XL AI Governance, AVG & Auditlogboek",
    pii_block: "🛑 AVG-blokkade (Privacy Gatekeeper):",
    btn_scrub: "🧹 Identificerende kolommen automatisch uitsluiten en doorgaan (1 klik)",
    ok_rgpd: "✅ AVG-controle geslaagd",
    obs_label: "observaties",
    cols_label: "kolommen",
    col_cont: "Continu",
    col_cat: "Categorisch",
    col_ign: "Negeren",
    kpi_method: "Methode Fase 1",
    kpi_obs: "Observaties",
    kpi_stat: "Statistiek / p",
    kpi_eff: "Effectgrootte",
    h_biz: "💼 Beslissingssamenvatting (Fase 2 — Agent 3)",
    h_apa: "🎓 Academisch Rapport APA 7 (Agent 2)",
    h_aud: "🔎 Methodologische Audit (Agent 1)",
    h_diag: "Diagnostiek Fase 1",
    seal_sum: "🔐 Zegel voor falsifieerbaarheid (Dubbele SHA-256 & Geaggregeerd JSON-contract)",
    purged_msg: "Sessie gewist uit het geheugen (ZDR). Sleep een nieuw bestand.",
    gov_roles: "AVG-rollen & DPA",
    gov_cgu: "Voorwaarden & ZDR-principes",
    gov_log: "Recent auditlogboek (strikt nul persoonsgegevens)",
  },
  en: {
    badge: "XL AI · 2-Phase ZDR",
    tier_local: "🛡️ Local Expert (0 network egress)",
    tier_auto: "⚙️ Autonomous Phase 1 (0 AI)",
    tier_zdr: "🏢 Confidential / Enterprise ZDR",
    btn_gov: "Governance & Audit",
    btn_purge: "Purge ZDR",
    step1: "Data & GDPR",
    step2: "Question & Plan",
    step3: "Phase 1 & Phase 2",
    step4: "Falsifiable Export",
    h1_ingest: "1. Import your data <em>(Phase 1 — 0% AI)</em>",
    lead_ingest: "Deterministic Python/SciPy engine. Individual rows are never sent to an LLM.",
    tab_file: "📁 Upload file (CSV, TSV, XLSX)",
    tab_paste: "📋 Paste a table",
    btn_sample: "✨ Load sample dataset",
    llm_panel_title: "🏢 Enterprise / ZDR LLM Configuration (aggregated JSON only)",
    drop_label: "Drop your file here or click to browse",
    drop_sub: "CSV · TSV · Excel (.xlsx) — delimiter and decimal separator auto-detected",
    paste_ph: "Paste your CSV/TSV table here…",
    btn_load_paste: "Load pasted data",
    import_opts: "⚙️ Import settings (missing codes, delimiter)",
    opt_sep: "Delimiter",
    opt_dec: "Decimal",
    opt_missing: "Missing codes",
    preview_sum: "🔍 Data preview (first 5 rows) & column types",
    h2_plan: "2. Your research question",
    q_ph: "Enter a single or multi-part question (e.g. Did the change reduce delay, and do incidents depend on the audit?)",
    opt_alpha: "Threshold α",
    btn_detect: "⚡ Detect analyses",
    btn_run_all: "▶️ Run Phase 1 & Phase 2",
    manual_sum: "🎛️ Manual Expert Mode (Logistic, Correlations, Repeated Measures, ANOVA…)",
    man_method: "Method",
    man_y: "Target variable (Y)",
    man_x: "Factor(s) / Predictor(s) (X)",
    btn_run_man: "▶️ Run manual analysis",
    h2_res: "3. Certified Results (Phase 1) & Interpretation (Phase 2)",
    h2_exp: "4. Export Falsifiable Study Report",
    lead_exp: "Dual SHA-256 fingerprint (raw + anonymised), certified environment, and full reproducibility.",
    exp_pdf: "📕 PDF Report (charts)",
    exp_docx: "📘 Word Report (.docx)",
    exp_md: "📄 Markdown (.md)",
    exp_py: "🐍 Python Script (.py)",
    gov_title: "🛡️ XL AI Governance, GDPR & Audit Log",
    pii_block: "🛑 GDPR Block (Privacy Gatekeeper):",
    btn_scrub: "🧹 Exclude identifying columns automatically and continue (1 click)",
    ok_rgpd: "✅ GDPR check passed",
    obs_label: "observations",
    cols_label: "columns",
    col_cont: "Continuous",
    col_cat: "Categorical",
    col_ign: "Ignore",
    kpi_method: "Phase 1 Method",
    kpi_obs: "Observations",
    kpi_stat: "Statistic / p",
    kpi_eff: "Effect size",
    h_biz: "💼 Decision Summary (Phase 2 — Agent 3)",
    h_apa: "🎓 Academic Report APA 7 (Agent 2)",
    h_aud: "🔎 Methodological Audit (Agent 1)",
    h_diag: "Phase 1 Diagnostics",
    seal_sum: "🔐 Falsifiability Seal (Dual SHA-256 & Aggregated JSON Contract)",
    purged_msg: "Session purged from memory (ZDR). Drop a new file.",
    gov_roles: "GDPR Roles & DPA",
    gov_cgu: "Terms & ZDR Principles",
    gov_log: "Recent audit log (strictly zero individual data)",
  },
};

const state = {
  lang: "nl",
  sessionId: null,
  meta: null,
  colTypes: {},
  plans: [],
  results: [],
  activeTab: 0,
};

const $ = (id) => document.getElementById(id);
const t = (key) => I18N[state.lang][key] || key;

function applyLanguage(lang) {
  state.lang = lang;
  document.documentElement.lang = lang;
  $("langNL").classList.toggle("active", lang === "nl");
  $("langEN").classList.toggle("active", lang === "en");

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const k = el.getAttribute("data-i18n");
    if (I18N[lang][k]) el.innerHTML = I18N[lang][k];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const k = el.getAttribute("data-i18n-placeholder");
    if (I18N[lang][k]) el.setAttribute("placeholder", I18N[lang][k]);
  });

  if (state.results.length && state.plans.length) {
    state.plans = state.plans.map((p) => ({ ...p, language: lang }));
    executePlans(state.plans);
  }
}

$("langNL").onclick = () => applyLanguage("nl");
$("langEN").onclick = () => applyLanguage("en");

function esc(str) {
  return String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function mdToHtml(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

function setStep(n) {
  for (let i = 1; i <= 4; i++) {
    const el = $(`st${i}`);
    el.classList.remove("active", "done");
    if (i < n) el.classList.add("done");
    else if (i === n) el.classList.add("active");
  }
}

function renderTable(headers, rows) {
  const ths = headers.map((h) => `<th>${esc(h)}</th>`).join("");
  const trs = rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c ?? "—")}</td>`).join("")}</tr>`).join("");
  return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
}

// ---------------- FILE / PASTE TABS ----------------
$("tabFile").onclick = () => {
  $("tabFile").classList.add("active");
  $("tabPaste").classList.remove("active");
  $("paneFile").hidden = false;
  $("panePaste").hidden = true;
};
$("tabPaste").onclick = () => {
  $("tabPaste").classList.add("active");
  $("tabFile").classList.remove("active");
  $("panePaste").hidden = false;
  $("paneFile").hidden = true;
};

const dropzone = $("dropzone");
dropzone.ondragover = (e) => { e.preventDefault(); dropzone.classList.add("drag"); };
dropzone.ondragleave = () => dropzone.classList.remove("drag");
dropzone.ondrop = (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  if (e.dataTransfer.files[0]) ingestFile(e.dataTransfer.files[0]);
};
$("fileInput").onchange = (e) => { if (e.target.files[0]) ingestFile(e.target.files[0]); };
$("btnIngestPaste").onclick = () => {
  const txt = $("pasteInput").value.trim();
  if (txt) ingestPayload({ pasted_text: txt });
};

async function ingestFile(file) {
  $("dropLabel").textContent = file.name;
  await ingestPayload({ file });
}

async function ingestPayload({ file = null, pasted_text = null }) {
  const fd = new FormData();
  if (file) fd.append("file", file);
  if (pasted_text) fd.append("pasted_text", pasted_text);
  fd.append("sep", $("optSep").value);
  fd.append("decimal", $("optDec").value);
  fd.append("has_header", "true");
  fd.append("custom_missing", $("optMissing").value);

  const res = await fetch("/api/phase1/ingest", { method: "POST", body: fd });
  const data = await res.json();
  if (!res.ok) {
    $("piiBox").hidden = false;
    $("piiBox").innerHTML = `<strong>Error:</strong> ${esc(data.detail)}`;
    return;
  }

  state.sessionId = data.session_id;
  state.meta = data.meta;
  state.colTypes = data.col_types;
  state.plans = [];
  state.results = [];

  $("questionInput").value = "";
  $("planPreview").hidden = true;
  $("planWarning").hidden = true;
  $("secResults").hidden = true;
  $("secExport").hidden = true;
  $("btnPurge").hidden = false;

  handlePiiAndPreview(data);
}

function handlePiiAndPreview(data) {
  const pii = data.pii;
  if (pii.blocked) {
    $("ingestOk").hidden = true;
    $("secPlan").hidden = true;
    $("piiBox").hidden = false;
    const rows = pii.findings.map((f) => [f.column, f.reason, f.match_count, (f.masked_samples || []).join(", ")]);
    $("piiBox").innerHTML = `
      <strong>${t("pii_block")}</strong> ${esc(pii.flagged_columns.join(", "))}
      <div class="table-scroll">${renderTable(["Column", "Reason", "Matches", "Masked"], rows)}</div>
      <button id="btnScrubPii" class="btn-primary" type="button" style="margin-top:10px;">${t("btn_scrub")}</button>
    `;
    $("btnScrubPii").onclick = async () => {
      const r = await fetch("/api/phase1/scrub", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: state.sessionId, columns: pii.flagged_columns }),
      });
      const scrubbed = await r.json();
      if (r.ok) {
        state.meta = scrubbed.meta;
        state.colTypes = scrubbed.col_types;
        handlePiiAndPreview(scrubbed);
      }
    };
    return;
  }

  $("piiBox").hidden = true;
  $("ingestOk").hidden = false;
  $("ingestOk").innerHTML = `${t("ok_rgpd")} — <strong>${state.meta.rows} ${t("obs_label")} × ${state.meta.columns.length} ${t("cols_label")}</strong> (<code>${esc(state.meta.delimiter)}</code> / <code>${esc(state.meta.decimal)}</code>).`;

  $("previewWrap").hidden = false;
  const cols = state.meta.columns;
  const rows = (data.preview || []).map((row) => cols.map((c) => row[c]));
  $("previewTable").innerHTML = renderTable(cols, rows);
  $("colTypesGrid").innerHTML = cols
    .map(
      (c) => `
      <label style="font-size:0.82rem;">${esc(c)}
        <select data-col="${esc(c)}" class="col-type-sel">
          <option value="continuous" ${state.colTypes[c] === "continuous" ? "selected" : ""}>${t("col_cont")}</option>
          <option value="categorical" ${state.colTypes[c] === "categorical" ? "selected" : ""}>${t("col_cat")}</option>
          <option value="ignored" ${state.colTypes[c] === "ignored" ? "selected" : ""}>${t("col_ign")}</option>
        </select>
      </label>`
    )
    .join("");
  document.querySelectorAll(".col-type-sel").forEach((sel) => {
    sel.onchange = () => {
      state.colTypes[sel.dataset.col] = sel.value;
      refreshManualSelectors();
    };
  });

  refreshManualSelectors();
  $("secPlan").hidden = false;
  setStep(2);
}

function refreshManualSelectors() {
  const cols = Object.keys(state.colTypes).filter((c) => state.colTypes[c] !== "ignored");
  const opts = cols.map((c) => `<option value="${esc(c)}">${esc(c)} (${state.colTypes[c]})</option>`).join("");
  $("manY").innerHTML = opts;
  $("manX").innerHTML = opts;
}

// ---------------- STEP 2: AUTO-PLAN & MANUAL ----------------
$("btnAutoPlan").onclick = async () => {
  const q = $("questionInput").value.trim();
  if (!q) return;
  const res = await fetch("/api/phase1/auto-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: state.sessionId,
      question: q,
      alpha: parseFloat($("optAlpha").value),
      language: state.lang,
      col_types: state.colTypes,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    $("planWarning").hidden = false;
    $("planWarning").textContent = data.detail;
    return;
  }
  if (!data.matched) {
    $("planPreview").hidden = true;
    $("planWarning").hidden = false;
    $("planWarning").textContent = `⚠️ ${data.warning}`;
    return;
  }
  $("planWarning").hidden = true;
  state.plans = data.plans;
  const rows = state.plans.map((p, i) => [i + 1, p.mode.toUpperCase(), p.y, (p.xs || []).join(", ") || "—", p.question]);
  $("planTable").innerHTML = renderTable(["#", "Test", "Y", "X", "Sub-question"], rows);
  $("planPreview").hidden = false;
};

$("btnRunAll").onclick = () => executePlans(state.plans);

$("btnRunManual").onclick = () => {
  const mode = $("manMode").value;
  const y = $("manY").value;
  const xs = Array.from($("manX").selectedOptions).map((o) => o.value).filter((c) => c !== y);
  const plan = {
    mode,
    y,
    xs,
    alpha: parseFloat($("optAlpha").value),
    alternative: "two-sided",
    question: $("questionInput").value.trim() || `${mode.toUpperCase()}: ${y} ~ ${xs.join(", ")}`,
    language: state.lang,
  };
  state.plans = [plan];
  executePlans(state.plans);
};

$("tierSelect").onchange = () => {
  $("llmConfigBox").hidden = $("tierSelect").value !== "confidentiel_zdr";
};

$("btnSample").onclick = async () => {
  const res = await fetch(`/api/phase1/sample?lang=${state.lang}`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) return;
  state.sessionId = data.session_id;
  state.meta = data.meta;
  state.colTypes = data.col_types;
  state.plans = [];
  state.results = [];
  $("btnPurge").hidden = false;
  handlePiiAndPreview(data);
  $("questionInput").value = data.sample_question || "";
  $("btnAutoPlan").click();
};

async function executePlans(plans) {
  const tier = $("tierSelect").value;
  const llm_config =
    tier === "confidentiel_zdr"
      ? {
          enabled: true,
          provider: $("llmProvider").value,
          model: $("llmModel").value.trim(),
          endpoint: $("llmEndpoint").value.trim(),
          api_key: $("llmApiKey").value.trim(),
        }
      : null;
  const res = await fetch("/api/phase1/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: state.sessionId,
      plans: plans.map((p) => ({ ...p, language: state.lang })),
      full_question: $("questionInput").value.trim(),
      tier,
      language: state.lang,
      llm_config,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(`Error: ${data.detail}`);
    return;
  }
  state.results = data.results;
  state.activeTab = 0;
  renderResults();
  $("secResults").hidden = false;
  $("secExport").hidden = false;
  setStep(4);
}

// ---------------- STEP 3: RESULTS ----------------
function renderResults() {
  const tabsEl = $("resultTabs");
  if (state.results.length > 1) {
    tabsEl.innerHTML = state.results
      .map(
        (item, i) =>
          `<button class="tab-btn ${i === state.activeTab ? "active" : ""}" data-idx="${i}" type="button">
            #${i + 1} · ${esc(item.contract.plan.mode.toUpperCase())} (${esc(item.contract.plan.y)})
          </button>`
      )
      .join("");
    tabsEl.querySelectorAll("button").forEach((b) => {
      b.onclick = () => { state.activeTab = parseInt(b.dataset.idx, 10); renderResults(); };
    });
  } else {
    tabsEl.innerHTML = "";
  }

  const item = state.results[state.activeTab];
  const c = item.contract;
  const p2 = item.phase2;
  const r = c.result;
  const pStr = r.p_value == null ? "—" : r.p_value < 0.001 ? "< .001" : `.${r.p_value.toFixed(3).split(".")[1]}`;
  const eff0 = c.effects?.[0];

  let html = `
    <div class="kpi-grid">
      <div class="kpi"><div class="label">${t("kpi_method")}</div><div class="val" style="font-size:1rem;">${esc(r.method)}</div></div>
      <div class="kpi"><div class="label">${t("kpi_obs")}</div><div class="val">${r.n_complete} / ${r.n_total}</div></div>
      <div class="kpi"><div class="label">${t("kpi_stat")}</div><div class="val">${r.statistic ?? "—"} · ${pStr}</div></div>
      <div class="kpi"><div class="label">${esc(eff0?.name || t("kpi_eff"))}</div><div class="val">${eff0?.estimate ?? "—"}</div></div>
    </div>
  `;

  if (p2) {
    html += `
      <h3>${t("h_biz")}</h3>
      <div class="summary-box">${mdToHtml(p2.agent3_business_summary)}</div>
      <h3>${t("h_apa")}</h3>
      <div class="apa-box">${mdToHtml(p2.agent2_apa7_report)}</div>
      <h3>${t("h_aud")}</h3>
      <ul>${p2.agent1_methodology_audit.map((a) => `<li>${mdToHtml(a)}</li>`).join("")}</ul>
    `;
    if (p2.recommended_actions?.length) {
      html += `<div class="loop-bar">${p2.recommended_actions
        .map((act, i) => `<button class="btn-secondary loop-btn" data-act="${i}" type="button">🔁 ${esc(act.label)}</button>`)
        .join("")}</div>`;
    }
  }

  if (c.coefficients?.length) {
    const rows = c.coefficients.map((x) => [x.term, x.B, x.SE, x.t ?? x.z ?? "—", x.p < 0.001 ? "< .001" : x.p, x.OR ?? x.beta ?? "—", x.VIF ?? "—"]);
    html += `<div class="table-scroll">${renderTable(["Term", "B", "SE", "t / z", "p", "OR / β", "VIF"], rows)}</div>`;
  } else if (c.groups?.length) {
    const rows = c.groups.map((g) => [g.label, g.n, g.mean, g.median, g.sd]);
    html += `<div class="table-scroll">${renderTable(["Group", "n", "Mean", "Median", "SD"], rows)}</div>`;
  }

  if (r.contingency_table) {
    const ct = r.contingency_table;
    const hdr = [`${ct.row_var} \\ ${ct.col_var}`, ...ct.cols.map((col) => `${ct.col_var}=${col}`)];
    const rows = ct.rows.map((rl, idx) => {
      const tot = ct.counts[idx].reduce((a, b) => a + b, 0) || 1;
      return [rl, ...ct.counts[idx].map((cnt) => `${cnt}/${tot} (${((cnt / tot) * 100).toFixed(1)}%)`)];
    });
    html += `<div class="table-scroll">${renderTable(hdr, rows)}</div>`;
  }

  if (c.diagnostics?.length) {
    const rows = c.diagnostics.map((d) => [d.name, d.label, d.n, d.statistic ?? "—", d.p == null ? "—" : d.p < 0.001 ? "< .001" : d.p]);
    html += `<h3>${t("h_diag")}</h3><div class="table-scroll">${renderTable(["Diagnostic", "Series", "n", "Statistic", "p"], rows)}</div>`;
  }

  for (const ch of item.charts || []) {
    html += `<img class="chart-img" src="data:image/png;base64,${ch.png_base64}" alt="${esc(ch.title)}" />`;
  }

  const m = c.metadata;
  html += `
    <details class="expander">
      <summary>${t("seal_sum")}</summary>
      <p style="font-size:0.82rem;font-family:monospace;">
        SHA-256 raw: ${esc(m.sha256_raw_file)}<br/>
        ${m.sha256_anonymized_file ? `SHA-256 anonymised: ${esc(m.sha256_anonymized_file)}<br/>` : ""}
        Python ${esc(m.environment.python)} · NumPy ${esc(m.environment.numpy)} · SciPy ${esc(m.environment.scipy)} · Seed ${esc(m.environment.seed)}
      </p>
    </details>
  `;

  $("resultBody").innerHTML = html;

  $("resultBody").querySelectorAll(".loop-btn").forEach((btn) => {
    btn.onclick = () => {
      const act = p2.recommended_actions[parseInt(btn.dataset.act, 10)];
      const updated = [...state.plans];
      updated[state.activeTab] = { ...act.new_plan, language: state.lang };
      state.plans = updated;
      executePlans(state.plans);
    };
  });
}

// ---------------- STEP 4: EXPORTS ----------------
document.querySelectorAll(".btn-export").forEach((btn) => {
  btn.onclick = async () => {
    const fmt = btn.dataset.fmt;
    const res = await fetch(`/api/export/${fmt}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        plans: state.plans,
        full_question: $("questionInput").value.trim(),
        tier: $("tierSelect").value,
        language: state.lang,
      }),
    });
    if (!res.ok) return alert("Export error.");
    const blob = await res.blob();
    const ext = { pdf: "pdf", docx: "docx", markdown: "md", script: "py" }[fmt];
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fmt === "script" ? "reproducible_analysis.py" : `statistical_report_apa7.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };
});

// ---------------- PURGE ZDR & GOVERNANCE MODAL ----------------
$("btnPurge").onclick = async () => {
  if (!state.sessionId) return;
  await fetch(`/api/session/${state.sessionId}`, { method: "DELETE" });
  state.sessionId = null;
  state.plans = [];
  state.results = [];
  $("ingestOk").hidden = true;
  $("previewWrap").hidden = true;
  $("secPlan").hidden = true;
  $("secResults").hidden = true;
  $("secExport").hidden = true;
  $("btnPurge").hidden = true;
  $("dropLabel").textContent = t("purged_msg");
  setStep(1);
};

$("btnGov").onclick = async () => {
  $("govModal").hidden = false;
  const [legRes, logRes] = await Promise.all([
    fetch(`/api/governance/legal?lang=${state.lang}`),
    fetch("/api/governance/audit-log"),
  ]);
  const leg = await legRes.json();
  const logs = await logRes.json();
  const logRows = (logs.entries || []).slice(0, 12).map((e) => [
    e.timestamp_utc.slice(0, 19), e.user_id, e.tier, e.action, e.metadata?.filename || "—",
  ]);
  $("govContent").innerHTML = `
    <h4>${t("gov_roles")}</h4>
    <ul>
      <li><strong>Client:</strong> ${esc(leg.legal.roles_rgpd.client)}</li>
      <li><strong>XL AI:</strong> ${esc(leg.legal.roles_rgpd.xl_ai)}</li>
      <li><strong>LLM Provider:</strong> ${esc(leg.legal.roles_rgpd.fournisseur_llm)}</li>
    </ul>
    <h4>${t("gov_cgu")}</h4>
    <ul>${leg.legal.cgu_resume.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
    <h4>${t("gov_log")}</h4>
    <div class="table-scroll">${renderTable(["Date UTC", "User", "Tier", "Action", "File"], logRows)}</div>
  `;
};
$("btnCloseGov").onclick = () => { $("govModal").hidden = true; };

applyLanguage("nl");
