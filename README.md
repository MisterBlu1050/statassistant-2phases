# StatAssistant — 2-Phase Evidence-Based HR & Statistical Analysis (NL / EN)

> **Live Demo:** https://statassistant-atelier.tawes-1050.chatgpt.site/  
> **Mission:** Non-commercial open proof that rigorous, GDPR-safe, **evidence-based HR analytics** is accessible even to small organizations — without SPSS licenses, without Excel statistical traps, and without LLM math hallucinations.

---

## Why a 2-Phase Architecture?

Most AI data tools either paste raw employee files into a chatbot (a **GDPR risk**) or let an LLM compute $p$-values directly (an **hallucination risk**). StatAssistant strictly decouples computation from interpretation:

```text
[PHASE 1 — 100% Deterministic, 0% AI]
CSV / TSV / XLSX  ──▶  Privacy Gatekeeper (blocks PII + 1-click scrub)
                  ──▶  Deterministic Multi-Question Planner (NL / EN)
                  ──▶  SciPy / NumPy Engine (14 tests, fixed seed, dual SHA-256)
                  ──▶  Certified Aggregated JSON Contract (ZERO individual rows)
                                        │
                                        ▼
[PHASE 2 — Methodological & HR Interpretation (Aggregated JSON only)]
  • Agent 1 — Methodological Auditor (VIF > 100, non-linearity, outliers, causality)
  • Agent 2 — APA 7 Academic Writer (ready-to-cite narrative)
  • Agent 3 — Plain-Language Decision Summary (for HR & SME leaders)
  • Human-in-the-loop Recalculation Buttons (quadratic, Kruskal-Wallis, Wilcoxon, drop collinear)
```

---

## Statistical Coverage (Phase 1)

- **Descriptive & Outliers:** Mean, SD, 95% CI, Median, IQR, Shapiro-Wilk, IQR & z-score outlier flags.
- **Paired / Longitudinal:** Paired *t*-test (directional/two-sided, $d_z$ + bootstrap CI), **Wilcoxon signed-rank** ($r_{rb}$), **Repeated-Measures ANOVA** (Greenhouse-Geisser $\varepsilon$, $\eta_p^2$, Friedman control).
- **Independent Groups:** Student / automatic **Welch *t*-test** (Cohen's $d$), **Mann-Whitney U**, One-Way / automatic **Welch ANOVA** ($\eta^2$) + **Tukey HSD / Games-Howell**, **Kruskal-Wallis** + **Dunn-Holm**.
- **Regression & Modeling:** Simple, Multiple & **Quadratic** OLS (QR decomposition, automatic **HC3 + Wald-HC3** on Breusch-Pagan $p < .05$, centered **VIF**, automatic inverted-U / U-shape detection), **Binary Logistic Regression** (MLE/IRLS, Odds Ratios + 95% CI, LRT, McFadden $R^2$, AUC-ROC).
- **Correlations & Categorical:** **Pearson + Spearman** matrix (Holm-adjusted + heatmap), **Chi-square** with automatic **Fisher's Exact** ($2\times 2$) or **Monte Carlo (2 000)** on sparse expected counts, conditional $P(Y \mid X)$ row tables.

---

## Governance, GDPR & Falsifiability

- **Privacy Gatekeeper:** Blocks `Email`, `IBAN`, `Phone`, `IP`, `NISS/INSZ` (mod-97), full names, and ID columns (`Matricule`, `Employee_ID`, `Patient_ID`, `Dossier_ID`) with **1-click column exclusion**.
- **Zero Data Retention (ZDR):** In-memory ephemeral sessions with automatic 30-minute TTL eviction and manual 1-click purge (`DELETE /api/session/{id}`).
- **Falsifiable Exports:** Native **PDF** (with embedded charts), editable **Word (`.docx`)**, **Markdown**, and human-readable **reproducible Python script** with dual **SHA-256** fingerprints (original file + anonymised dataset).
- **Bilingual UI & Reports:** Instant **NL / EN** toggle across the web app, legal/GDPR notices, Phase 2 reports, and PDF/Word exports.

---

## Quickstart

### Local (FastAPI + Modern SPA)
```bash
pip install -r requirements.txt
uvicorn api:app --host 127.0.0.1 --port 8000
# Open http://localhost:8000  (API docs: http://localhost:8000/docs)
```

### Run Automated Test Suite (16 tests)
```bash
pytest -v
```

### Deploy in Europe with Automatic HTTPS (Docker Compose + Caddy)
See [DEPLOY_EU.md](./DEPLOY_EU.md) for 5-minute deployment on OVH, Scaleway, Hetzner, or Google Cloud Run (`europe-west1`).

---

## License

MIT — Built as an open demonstration of rigorous, accessible evidence-based HR analytics.
