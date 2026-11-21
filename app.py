"""StatAssistant 2-Phases — Application Web Streamlit.

Phase 1 : Assistant structuré déterministe (0 % IA, local, Privacy Gatekeeper +
          Planificateur multi-questions + Moteur SciPy).
Phase 2 : Couche d'intelligence métier multi-agents sur JSON agrégé uniquement +
          boucle de recalcul retour Phase 1 validée par l'humain.
"""

from __future__ import annotations

import json
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.auto_planner import auto_plan_from_question
from src.charts import build_figures
from src.exporters import build_docx_report, build_pdf_report
from src.phase2_agents import run_phase2_interpretation
from src.privacy_gate import exclude_columns, scan_dataframe
from src.stats_engine import (
    generate_reproducible_script,
    infer_column_types,
    parse_dataset,
    run_analysis,
    sha256_bytes,
)

st.set_page_config(page_title="StatAssistant 2-Phases (XL AI)", page_icon="📊", layout="wide")


def _format_diag_row(d: dict) -> str:
    stat_s = f"{d['statistic']:.3f}" if isinstance(d["statistic"], (int, float)) else "—"
    p_val = d["p"]
    if isinstance(p_val, (int, float)):
        p_s = "< .001" if p_val < 0.001 else "." + f"{p_val:.3f}".split(".")[1]
    else:
        p_s = "—"
    return f"| {d['name']} | {d['label']} | {d['n']} | {stat_s} | {p_s} |"


def _build_unified_markdown_report(items: list[tuple[dict, dict | None]], full_question: str) -> str:
    meta = items[0][0]["metadata"]
    lines = [
        "# Rapport d'Étude Statistique Circonstancié (Falsifiable)",
        "",
        f"- **Source :** `{meta['filename']}`",
        f"- **Date UTC :** `{meta['timestamp_utc']}`",
        f"- **Question globale :** {full_question or 'Non précisée'}",
        f"- **Nombre de sous-analyses :** {len(items)}",
        "",
    ]

    for idx, (contract, phase2) in enumerate(items, start=1):
        res = contract["result"]
        sub_q = contract["plan"].get("question") or f"{contract['plan']['y']} ~ {', '.join(contract['plan']['xs'])}"
        lines.extend(
            [
                f"---",
                f"## Sous-analyse {idx} — {sub_q}",
                f"- **Méthode exécutée (Phase 1) :** {res['method']} (N = {res['n_complete']} / {res['n_total']})",
                "",
            ]
        )
        if phase2:
            lines.extend(
                [
                    "### Synthèse Décisionnelle (Agent 3)",
                    phase2["agent3_business_summary"],
                    "",
                    "### Rapport Académique — Normes APA 7 (Agent 2)",
                    phase2["agent2_apa7_report"],
                    "",
                    "### Audit Méthodologique & Limites (Agent 1)",
                ]
            )
            for a in phase2["agent1_methodology_audit"]:
                lines.append(f"- {a}")
            lines.append("")

        if res.get("contingency_table"):
            ct = res["contingency_table"]
            r_var = ct.get("row_var", "Ligne")
            c_var = ct.get("col_var", "Colonne")
            cols_hdr = " | ".join(f"{c_var} = {c}" for c in ct["cols"])
            sep_hdr = " | ".join([":---:"] * len(ct["cols"]))
            lines.extend([f"### Tableau de contingence : {r_var} (lignes) × {c_var} (colonnes, % par ligne)", f"| {r_var} \\ {c_var} | {cols_hdr} |", f"| :--- | {sep_hdr} |"])
            for r_lbl, r_counts in zip(ct["rows"], ct["counts"]):
                tot = sum(r_counts) or 1
                cells = " | ".join(f"{cnt}/{tot} ({cnt/tot*100:.1f} %)" for cnt in r_counts)
                lines.append(f"| {r_lbl} | {cells} |")
            lines.append("")

        lines.extend(
            [
                "### Diagnostics chiffrés (Phase 1)",
                "| Diagnostic | Série / Groupe | n | Statistique | p |",
                "| :--- | :--- | :---: | :---: | :---: |",
            ]
        )
        for d in contract.get("diagnostics", []):
            lines.append(_format_diag_row(d))
        lines.append("")

    lines.extend(
        [
            "---",
            "## Sceau de Falsifiabilité & Reproductibilité",
            f"- **SHA-256 (fichier brut d'origine) :** `{meta['sha256_raw_file']}`",
        ]
    )
    if meta.get("sha256_anonymized_file"):
        lines.append(
            f"- **SHA-256 (jeu anonymisé après retrait de {', '.join(meta.get('excluded_pii_columns', []))}) :** `{meta['sha256_anonymized_file']}`"
        )
    if meta.get("custom_missing"):
        lines.append(f"- **Codes manquants recodés en NaN :** `{', '.join(meta['custom_missing'])}`")
    lines.append(
        f"- **Environnement :** Python {meta['environment']['python']} · NumPy {meta['environment']['numpy']} · SciPy {meta['environment']['scipy']} · Seed {meta['environment']['seed']}"
    )
    return "\n".join(lines)


def _render_single_analysis(
    idx: int,
    plan: dict,
    df_clean: pd.DataFrame,
    dataset_meta: dict,
    tier: str,
    llm_config: dict,
) -> tuple[dict, dict | None, dict] | None:
    try:
        contract, plot_data = run_analysis(df_clean, plan, dataset_meta)
    except Exception as exc:
        st.error(f"Erreur de calcul Phase 1 (sous-analyse {idx + 1}) : {exc}")
        return None

    res = contract["result"]
    st.subheader(f"Résultats certifiés Phase 1 — {res['method']}")
    if plan.get("question"):
        st.caption(f"Sous-question : « {plan['question']} »")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Observations complètes", f"{res['n_complete']} / {res['n_total']}")
    if res.get("statistic") is not None:
        m2.metric(f"Statistique ({res['statistic_name']})", f"{res['statistic']}")
    if res.get("p_value") is not None:
        m3.metric("p-value", "< .001" if res["p_value"] < 0.001 else f"{res['p_value']:.3f}")
    if contract["effects"]:
        eff0 = contract["effects"][0]
        m4.metric(eff0["name"], f"{eff0['estimate']}")

    if contract["groups"]:
        st.markdown("**Descriptifs par groupe / condition**")
        st.dataframe(pd.DataFrame(contract["groups"]), width="stretch")
    if contract["coefficients"]:
        st.markdown("**Table des coefficients (Régression)**")
        st.dataframe(pd.DataFrame(contract["coefficients"]), width="stretch")
    if contract["posthoc"]:
        st.markdown("**Comparaisons Post-Hoc ajustées**")
        st.dataframe(pd.DataFrame(contract["posthoc"]), width="stretch")
    if contract["diagnostics"]:
        st.markdown("**Diagnostics des postulats**")
        st.dataframe(pd.DataFrame(contract["diagnostics"]), width="stretch")

    for _, fig in build_figures(contract, plot_data):
        st.pyplot(fig)
        plt.close(fig)

    with st.expander("🔐 Sceau de falsifiabilité & Contrat JSON agrégé"):
        st.code(
            f"SHA-256 jeu de données : {contract['metadata']['sha256_raw_file']}\n"
            f"SHA-256 plan + JSON    : {contract['metadata']['sha256_analysis_json']}\n"
            f"Environnement          : {contract['metadata']['environment']}",
            language="text",
        )
        st.json(contract)

    phase2 = None
    if tier != "Autonome Phase 1 seule (0 IA)":
        st.divider()
        st.markdown("### Phase 2 — Interprétation Métier & Audit des Pièges")
        phase2 = run_phase2_interpretation(contract, llm_config=llm_config)
        st.caption(f"Moteur actif : {phase2['provider_mode']} · Entrée certifiée : JSON agrégé uniquement.")

        if phase2.get("llm_error"):
            st.warning(phase2["llm_error"])

        coherence_alerts = [a for a in phase2["agent1_methodology_audit"] if "Incohérence Question ↔ Variables" in a]
        for ca in coherence_alerts:
            st.error(ca)

        st.markdown("**💼 Synthèse Décideur (Agent 3 — Langage clair)**")
        st.info(phase2["agent3_business_summary"])

        st.markdown("**🎓 Rapport Académique — Normes APA 7 (Agent 2)**")
        st.markdown(phase2["agent2_apa7_report"])

        st.markdown("**🔎 Audit Méthodologique & Détection des Pièges (Agent 1)**")
        for alert in phase2["agent1_methodology_audit"]:
            st.markdown(f"- {alert}")

        if phase2["recommended_actions"]:
            st.markdown("**🔁 Recalculs recommandés (validation humaine requise) :**")
            btn_cols = st.columns(len(phase2["recommended_actions"]))
            for a_idx, act in enumerate(phase2["recommended_actions"]):
                if btn_cols[a_idx].button(act["label"], key=f"loop_{idx}_{a_idx}", type="primary"):
                    plans = list(st.session_state["active_plans"])
                    plans[idx] = act["new_plan"]
                    st.session_state["active_plans"] = plans
                    st.rerun()

        if phase2.get("llm_commentary"):
            st.markdown("**🤖 Enrichissement LLM Enterprise**")
            st.markdown(phase2["llm_commentary"])

    return contract, phase2, plot_data


# ---------------- SIDEBAR : GOUVERNANCE XL AI ----------------
with st.sidebar:
    st.title("🛡️ Gouvernance XL AI")
    tier = st.radio(
        "Palier d'exécution",
        [
            "Local Expert (0 sortie réseau)",
            "Autonome Phase 1 seule (0 IA)",
            "API Enterprise / ZDR / Ollama",
        ],
    )
    llm_config = {"enabled": False}
    if tier == "API Enterprise / ZDR / Ollama":
        st.caption("Seul le Contrat JSON agrégé (zéro donnée individuelle) est envoyé au modèle.")
        provider = st.selectbox("Fournisseur", ["openai_compat", "gemini"], format_func=lambda p: "OpenAI / Azure / Ollama" if p == "openai_compat" else "Google Gemini API")
        if provider == "gemini":
            model_name = st.text_input("Modèle Gemini", value="gemini-2.5-flash")
            endpoint = st.text_input("Endpoint custom (laisser vide par défaut)", value="")
        else:
            endpoint = st.text_input("Endpoint OpenAI-compatible", value="http://localhost:11434/v1/chat/completions")
            model_name = st.text_input("Modèle", value="llama3.1")
        api_key = st.text_input("Clé API (optionnel en local)", type="password")
        llm_config = {"enabled": True, "provider": provider, "endpoint": endpoint, "model": model_name, "api_key": api_key}

    st.divider()
    st.info(
        "**Architecture en 2 phases :**\n"
        "1. **Phase 1 (0 % IA)** : parsing auto, filtre RGPD, planificateur multi-questions et calculs SciPy déterministes.\n"
        "2. **Phase 2 (IA)** : audit des pièges, APA 7 et vulgarisation sur stats agrégées uniquement."
    )

st.title("📊 StatAssistant 2-Phases")
st.caption("Calcul statistique déterministe falsifiable (Phase 1) + Interprétation métier multi-agents (Phase 2)")

# ---------------- PHASE 1 — ÉTAPE 1 : INGESTION & RGPD ----------------
st.header("Phase 1 — Structuration & Calcul Déterministe (Sans IA)")

tab_file, tab_paste = st.tabs(["📁 Importer un fichier (CSV, TSV, XLSX)", "📋 Coller un tableau ou une série"])

raw_bytes: bytes | None = None
filename = "pasted_data.csv"

with tab_file:
    uploaded = st.file_uploader("Choisissez un fichier anonymisé", type=["csv", "tsv", "txt", "xlsx"])
    if uploaded is not None:
        raw_bytes = uploaded.getvalue()
        filename = uploaded.name

with tab_paste:
    pasted = st.text_area(
        "Collez un tableau CSV/TSV ou une série (ex: Scores: 12 15 18 20)",
        height=130,
        placeholder="Pole,Satisfaction\nTechnique,8.1\nSupport,6.7",
    )
    if pasted.strip():
        raw_bytes = pasted.encode("utf-8")
        filename = "pasted_data.csv"

with st.expander("⚙️ Paramètres d'import (séparateur, décimales, codes manquants)"):
    c1, c2, c3, c4 = st.columns(4)
    sep_choice = c1.selectbox("Séparateur", ["Auto", ",", ";", "\\t"])
    dec_choice = c2.selectbox("Décimale", ["Auto", ".", ","])
    has_header = c3.checkbox("1re ligne = en-têtes", value=True)
    custom_na_str = c4.text_input("Codes manquants supplémentaires", value="-999, -99")

if raw_bytes is None:
    st.stop()

sep_arg = None if sep_choice == "Auto" else ("\t" if sep_choice == "\\t" else sep_choice)
dec_arg = "auto" if dec_choice == "Auto" else dec_choice
custom_missing = [x.strip() for x in custom_na_str.split(",") if x.strip()]

try:
    df_raw, dataset_meta = parse_dataset(
        raw_bytes,
        filename=filename,
        sep=sep_arg,
        decimal=dec_arg,
        has_header=has_header,
        custom_missing=custom_missing,
    )
except Exception as exc:
    st.error(f"Erreur de lecture des données : {exc}")
    st.stop()

if "excluded_pii_cols" not in st.session_state or st.session_state.get("last_hash") != dataset_meta["sha256_raw_file"]:
    st.session_state["excluded_pii_cols"] = []
    st.session_state["last_hash"] = dataset_meta["sha256_raw_file"]
    st.session_state["active_plans"] = []

df_clean = exclude_columns(df_raw, st.session_state["excluded_pii_cols"])
pii_report = scan_dataframe(df_clean)

if pii_report["blocked"]:
    st.error(f"🛑 **Blocage RGPD (Privacy Gatekeeper) :** {pii_report['message']}")
    st.dataframe(pd.DataFrame(pii_report["findings"]), width="stretch")
    if st.button("🧹 Exclure automatiquement ces colonnes identifiantes et continuer (1 clic)", type="primary"):
        st.session_state["excluded_pii_cols"].extend(pii_report["flagged_columns"])
        st.rerun()
    st.stop()
else:
    if st.session_state["excluded_pii_cols"]:
        anon_bytes = df_clean.to_csv(index=False).encode("utf-8")
        dataset_meta = {
            **dataset_meta,
            "sha256_anonymized_file": sha256_bytes(anon_bytes),
            "excluded_pii_columns": list(st.session_state["excluded_pii_cols"]),
        }
    st.success(
        f"✅ Contrôle RGPD validé — {len(df_clean)} observations × {len(df_clean.columns)} colonnes "
        f"(séparateur `{dataset_meta['delimiter']}`, décimale `{dataset_meta['decimal']}`)."
    )

# ---------------- PHASE 1 — ÉTAPE 2 : REVUE & TYPAGE ----------------
inferred = infer_column_types(df_clean)
col_types: dict[str, str] = {}
with st.expander("🔍 Revue des données & Typage explicite des colonnes", expanded=False):
    st.dataframe(df_clean.head(5), width="stretch")
    cols_ui = st.columns(min(4, max(1, len(df_clean.columns))))
    for idx, col in enumerate(df_clean.columns):
        default_t = inferred[col]
        options = ["continuous", "categorical", "ignored"]
        col_types[col] = cols_ui[idx % len(cols_ui)].selectbox(
            f"Type : {col}", options, index=options.index(default_t), key=f"type_{col}"
        )

num_cols = [c for c, t in col_types.items() if t == "continuous"]
cat_cols = [c for c, t in col_types.items() if t == "categorical"]

# ---------------- PHASE 1 — ÉTAPE 3 : FORMULATION AUTO OU MANUELLE ----------------
st.subheader("Assistant de formulation (Automatique ou Manuel)")
c_q, c_a = st.columns([5, 1])
question = c_q.text_input(
    "Votre question de recherche / question métier (simple ou multi-parties)",
    placeholder="Ex : L'atelier a-t-il réduit l'anxiété, le sommeil influence-t-il les erreurs, et la mention dépend-elle de la filière ?",
    key=f"question_{dataset_meta['sha256_raw_file']}",
)
alpha = c_a.selectbox("Seuil α", [0.05, 0.01, 0.10], index=0)

# Mode Automatique : détection déterministe des sous-analyses depuis la question
detected_plans = auto_plan_from_question(question, df_clean, col_types, alpha=alpha) if question.strip() else []
if question.strip() and not detected_plans:
    st.warning(
        "⚠️ **Question non appariée aux colonnes du fichier :** aucune analyse statistique cohérente n'a été "
        "identifiée depuis ce texte. Vérifiez que votre question correspond bien au fichier importé (et non à "
        "un texte collé d'une étude précédente), ou utilisez la configuration manuelle ci-dessous."
    )
if detected_plans:
    st.markdown(f"**⚡ {len(detected_plans)} sous-analyse(s) détectée(s) automatiquement depuis votre question :**")
    preview_rows = [
        {
            "#": i + 1,
            "Test proposé": p["mode"].upper(),
            "Variable cible (Y)": p["y"],
            "Facteur(s) / Prédicteur(s) (X)": ", ".join(p["xs"]) or "—",
            "Sous-question": p["question"],
        }
        for i, p in enumerate(detected_plans)
    ]
    st.dataframe(pd.DataFrame(preview_rows), width="stretch", hide_index=True)
    if st.button(f"⚡ Exécuter automatiquement les {len(detected_plans)} analyse(s) détectée(s)", type="primary"):
        st.session_state["active_plans"] = detected_plans
        st.rerun()

# Mode Manuel (toujours disponible pour le contrôle fin / mode Expert)
with st.expander("🎛️ Configuration manuelle (Mode Expert — choisir les variables à la main)", expanded=not bool(detected_plans)):
    goal = st.selectbox(
        "Que souhaitez-vous faire ?",
        [
            "Comparer des groupes différents (ANOVA / Welch / t-test / Kruskal-Wallis / Mann-Whitney)",
            "Comparer avant et après chez les mêmes individus (t-test apparié / Wilcoxon)",
            "Comparer ≥ 3 mesures répétées sur les mêmes individus (ANOVA mesures répétées / Friedman)",
            "Expliquer ou prédire une variable numérique (Régression simple, multiple ou quadratique)",
            "Prédire un événement binaire Oui/Non (Régression logistique — Odds Ratios & AUC)",
            "Explorer les corrélations entre plusieurs variables (Matrice Pearson & Spearman)",
            "Croiser deux variables catégorielles (χ² / Fisher / Monte Carlo)",
            "Décrire une variable (moyenne, médiane, outliers)",
        ],
    )
    c_var1, c_var2 = st.columns(2)
    alternative = "two-sided"
    mode = "desc"
    y_col = None
    x_cols: list[str] = []
    manual_ready = False

    if goal.startswith("Comparer des groupes") and num_cols and cat_cols:
        y_col = c_var1.selectbox("Variable mesurée (VD)", num_cols, index=None, placeholder="Choisissez la variable mesurée…")
        g_col = c_var2.selectbox("Variable de groupe (VI)", cat_cols, index=None, placeholder="Choisissez la variable de groupe…")
        if y_col and g_col:
            x_cols = [g_col]
            n_groups = df_clean[g_col].dropna().nunique()
            if n_groups == 2:
                mode = st.radio("Méthode", ["ind", "mw"], format_func=lambda m: "t-test (Student / Welch auto)" if m == "ind" else "Mann-Whitney U", horizontal=True)
                alternative = st.radio("Hypothèse", ["two-sided", "greater", "less"], format_func=lambda a: {"two-sided": "Bilatérale (≠)", "greater": "Unilatérale (>)", "less": "Unilatérale (<)"}[a], horizontal=True)
            else:
                mode = st.radio("Méthode", ["anova", "kw"], format_func=lambda m: "ANOVA (Welch auto + Post-Hoc)" if m == "anova" else "Kruskal-Wallis (+ Dunn-Holm)", horizontal=True)
            manual_ready = True

    elif goal.startswith("Comparer avant") and len(num_cols) >= 2:
        x_before = c_var1.selectbox("Mesure 1 (Avant)", num_cols, index=None, placeholder="Choisissez Avant…")
        y_col = c_var2.selectbox("Mesure 2 (Après)", [c for c in num_cols if c != x_before], index=None, placeholder="Choisissez Après…")
        if x_before and y_col:
            x_cols = [x_before]
            mode = st.radio("Méthode", ["pair", "signed"], format_func=lambda m: "t-test apparié" if m == "pair" else "Wilcoxon signé", horizontal=True)
            alternative = st.radio("Hypothèse (Après − Avant)", ["two-sided", "greater", "less"], format_func=lambda a: {"two-sided": "Bilatérale (≠ 0)", "greater": "Hausse (> 0)", "less": "Baisse (< 0)"}[a], horizontal=True)
            manual_ready = True

    elif goal.startswith("Expliquer ou prédire") and len(num_cols) >= 2:
        y_col = c_var1.selectbox("Variable à prédire (Y)", num_cols, index=None, placeholder="Choisissez Y…")
        avail_x = [c for c in num_cols if c != y_col]
        x_cols = c_var2.multiselect("Prédicteur(s) (X)", avail_x, placeholder="Choisissez un ou plusieurs prédicteurs…")
        if y_col and x_cols:
            mode = st.radio("Forme", ["reg", "quad"], format_func=lambda m: "Linéaire (OLS / HC3 auto)" if m == "reg" else "Quadratique (X + X²)", horizontal=True) if len(x_cols) == 1 else "multi"
            manual_ready = True

    elif goal.startswith("Comparer ≥ 3 mesures") and len(num_cols) >= 3:
        rm_cols = st.multiselect("Sélectionnez les conditions répétées (≥ 3 colonnes dans l'ordre)", num_cols, placeholder="Ex : T0, T1, T2…")
        if len(rm_cols) >= 3:
            y_col = rm_cols[0]
            x_cols = rm_cols[1:]
            mode = "rm_anova"
            manual_ready = True

    elif goal.startswith("Prédire un événement binaire") and cat_cols and num_cols:
        bin_cols = [c for c in cat_cols if df_clean[c].dropna().nunique() == 2]
        if not bin_cols:
            st.warning("Aucune variable catégorielle binaire (2 modalités) disponible.")
        else:
            y_col = c_var1.selectbox("Événement binaire à prédire (Y)", bin_cols, index=None, placeholder="Choisissez Y (2 modalités)…")
            x_cols = c_var2.multiselect("Prédicteur(s) numériques (X)", num_cols, placeholder="Choisissez 1 ou plusieurs prédicteurs…")
            if y_col and x_cols:
                mode = "logit"
                manual_ready = True

    elif goal.startswith("Explorer les corrélations") and len(num_cols) >= 2:
        corr_sel = st.multiselect("Variables continues à corréler (≥ 2)", num_cols, placeholder="Choisissez 2 à N variables…")
        if len(corr_sel) >= 2:
            y_col = corr_sel[0]
            x_cols = corr_sel[1:]
            mode = "corr"
            manual_ready = True

    elif goal.startswith("Croiser deux") and len(cat_cols) >= 2:
        y_col = c_var1.selectbox("Variable catégorielle 1", cat_cols, index=None, placeholder="Choisissez la variable 1…")
        x_col = c_var2.selectbox("Variable catégorielle 2", [c for c in cat_cols if c != y_col], index=None, placeholder="Choisissez la variable 2…")
        if y_col and x_col:
            x_cols = [x_col]
            mode = "chi"
            manual_ready = True

    elif num_cols:
        y_col = c_var1.selectbox("Variable à décrire", num_cols, index=None, placeholder="Choisissez la variable…")
        if y_col:
            mode = "desc"
            manual_ready = True

    if manual_ready and st.button("▶️ Exécuter cette analyse manuelle (Phase 1)"):
        st.session_state["active_plans"] = [
            {
                "mode": mode,
                "y": y_col,
                "xs": x_cols,
                "alpha": alpha,
                "alternative": alternative,
                "question": question,
                "language": "fr",
            }
        ]
        st.rerun()

active_plans = st.session_state.get("active_plans", [])
if not active_plans:
    st.stop()

# ---------------- EXÉCUTION MULTI-ANALYSES PHASE 1 + PHASE 2 ----------------
st.divider()
completed: list[tuple[dict, dict | None, dict]] = []

if len(active_plans) == 1:
    out = _render_single_analysis(0, active_plans[0], df_clean, dataset_meta, tier, llm_config)
    if out:
        completed.append(out)
else:
    tabs = st.tabs([f"Analyse {i + 1} · {p['mode'].upper()} ({p['y']})" for i, p in enumerate(active_plans)])
    for i, (tab, p) in enumerate(zip(tabs, active_plans)):
        with tab:
            out = _render_single_analysis(i, p, df_clean, dataset_meta, tier, llm_config)
            if out:
                completed.append(out)

# ---------------- EXPORT UNIFIÉ FALSIFIABLE ----------------
if completed:
    st.divider()
    st.subheader("📦 Export du Rapport Circonstancié Falsifiable")
    col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns(5)
    md_items = [(c, p2) for c, p2, _ in completed]
    md_report = _build_unified_markdown_report(md_items, question)
    pdf_bytes = build_pdf_report(completed, question)
    docx_bytes = build_docx_report(completed, question)
    first_contract = completed[0][0]
    py_script = generate_reproducible_script(df_clean, first_contract)

    col_e1.download_button("📕 Rapport PDF (graphiques)", data=pdf_bytes, file_name="rapport_statistique_apa7.pdf", mime="application/pdf")
    col_e2.download_button("📘 Rapport Word (.docx)", data=docx_bytes, file_name="rapport_statistique_apa7.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    col_e3.download_button("📄 Markdown (.md)", data=md_report, file_name="rapport_statistique_apa7.md", mime="text/markdown")
    col_e4.download_button("🐍 Script Python (.py)", data=py_script, file_name="analyse_reproductible.py", mime="text/x-python")
    col_e5.download_button(
        "🔐 Contrats JSON (.json)",
        data=json.dumps([c for c, _, _ in completed], indent=2, ensure_ascii=False),
        file_name="contrats_phase1.json",
        mime="application/json",
    )
