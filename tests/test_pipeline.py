"""Tests automatisés du pipeline StatAssistant 2-Phases."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.auto_planner import auto_plan_from_question
from src.exporters import build_docx_report, build_pdf_report
from src.phase2_agents import assert_aggregated_only, run_phase2_interpretation
from src.privacy_gate import exclude_columns, scan_dataframe
from src.stats_engine import (
    generate_reproducible_script,
    infer_column_types,
    parse_dataset,
    run_analysis,
)


CSV_PIEGES = """Matricule_ID,Site,Type_Contrat,Salaire_K,Stress_Avant,Stress_Apres,Performance
EMP-101,Paris,1,38.5,8,4,72
EMP-102,Paris,1,41.0,7,5,75
EMP-103,Paris,1,39.2,9,3,70
EMP-104,Paris,2,36.0,8,6,68
EMP-105,Paris,1,45.0,7,4,80
EMP-106,Paris,2,37.5,9,5,71
EMP-201,Lyon,1,35.0,8,7,69
EMP-202,Lyon,2,34.5,7,8,65
EMP-203,Lyon,1,36.0,9,9,66
EMP-204,Lyon,2,33.0,8,7,62
EMP-205,Lyon,2,35.5,7,6,68
EMP-206,Lyon,1,37.0,8,8,70
EMP-301,Marseille,1,34.0,5,5,64
EMP-302,Marseille,2,32.5,6,6,61
EMP-303,Marseille,1,-999,9,8,63
EMP-304,Marseille,2,33.0,7,7,60
EMP-305,Marseille,1,35.0,8,7,66
EMP-306,Marseille,2,142.0,6,5,95
"""

CSV_SUBTILS = """Dossier_ID,Pole,Niveau,Charge_Hebdo,Stress_Percu,Anciennete_Poste,Anciennete_Groupe,Performance_Q3,Engagement
DOS-01,Technique,Junior,36.0,28,1.2,1.5,58,4.2
DOS-02,Technique,Junior,39.5,35,1.8,2.0,66,3.8
DOS-03,Technique,Junior,43.0,52,2.2,2.5,88,3.4
DOS-04,Technique,Junior,46.5,78,2.8,3.0,62,2.9
DOS-05,Technique,Senior,38.0,32,4.5,5.0,64,4.5
DOS-06,Technique,Senior,41.5,48,5.2,5.8,91,4.1
DOS-07,Technique,Senior,45.0,54,5.8,6.5,94,3.7
DOS-08,Technique,Senior,49.0,82,6.5,7.2,60,3.1
DOS-09,Conseil,Junior,35.0,25,0.8,1.0,54,4.4
DOS-10,Conseil,Junior,38.5,38,1.5,1.8,68,3.9
DOS-11,Conseil,Junior,42.0,50,2.0,2.3,86,3.5
DOS-12,Conseil,Junior,48.0,80,2.5,2.9,59,2.7
DOS-13,Conseil,Senior,37.5,30,4.0,4.6,62,4.6
DOS-14,Conseil,Senior,40.0,46,4.8,5.4,89,4.2
DOS-15,Conseil,Senior,44.5,55,5.5,6.2,93,3.8
DOS-16,Conseil,Senior,50.0,85,6.2,7.0,56,3.0
DOS-17,Support,Junior,35.5,27,1.0,1.2,55,4.3
DOS-18,Support,Junior,39.0,40,1.6,1.9,71,3.7
DOS-19,Support,Junior,41.5,49,2.1,2.4,85,3.3
DOS-20,Support,Junior,47.0,76,2.6,3.0,63,2.8
DOS-21,Support,Senior,38.5,34,3.8,4.3,67,4.4
DOS-22,Support,Senior,42.0,51,4.6,5.2,90,4.0
DOS-23,Support,Senior,45.5,58,5.4,6.0,88,3.6
DOS-24,Support,Senior,48.5,84,6.0,6.8,58,3.1
"""


def test_privacy_gate_blocks_and_one_click_scrub():
    df, _ = parse_dataset(CSV_PIEGES.encode("utf-8"), filename="pieges.csv", custom_missing=["-999"])
    report = scan_dataframe(df)
    assert report["blocked"] is True
    assert "Matricule_ID" in report["flagged_columns"]

    # One-Click Scrub débloque proprement sans faux positif sur les autres colonnes
    df_clean = exclude_columns(df, report["flagged_columns"])
    report2 = scan_dataframe(df_clean)
    assert report2["blocked"] is False


def test_parsing_missing_code_and_column_typing():
    df, _ = parse_dataset(CSV_PIEGES.encode("utf-8"), filename="pieges.csv", custom_missing=["-999"])
    assert df["Salaire_K"].isna().sum() == 1
    types = infer_column_types(df.drop(columns=["Matricule_ID"]))
    assert types["Type_Contrat"] == "categorical"
    assert types["Salaire_K"] == "continuous"


def test_trap_outlier_anova_recommends_kruskal():
    df, meta = parse_dataset(CSV_PIEGES.encode("utf-8"), filename="pieges.csv", custom_missing=["-999"])
    df = exclude_columns(df, ["Matricule_ID"])
    plan = {"mode": "anova", "y": "Salaire_K", "xs": ["Site"], "alpha": 0.05, "question": "Salaire par site ?"}
    contract, _ = run_analysis(df, plan, meta)
    flag_codes = {f["code"] for f in contract["flags"]}
    assert "normality_failed" in flag_codes
    assert "extreme_variance_ratio" in flag_codes

    p2 = run_phase2_interpretation(contract)
    assert any(a["new_plan"]["mode"] == "kw" for a in p2["recommended_actions"])


def test_trap_inverted_u_nonlinearity_and_quadratic_loop():
    df, meta = parse_dataset(CSV_SUBTILS.encode("utf-8"), filename="subtils.csv")
    df = exclude_columns(df, ["Dossier_ID"])
    plan = {"mode": "reg", "y": "Performance_Q3", "xs": ["Stress_Percu"], "alpha": 0.05, "question": "Stress -> Perf ?"}
    contract, _ = run_analysis(df, plan, meta)
    flag_codes = {f["code"] for f in contract["flags"]}
    assert "possible_nonlinearity" in flag_codes
    assert contract["result"]["r2"] < 0.05

    # Phase 2 détecte la courbe en U et propose le bouton quadratique
    p2 = run_phase2_interpretation(contract)
    quad_actions = [a for a in p2["recommended_actions"] if a["new_plan"]["mode"] == "quad"]
    assert len(quad_actions) == 1

    # Exécution de la boucle retour Phase 1 -> R² quadratique > 0.90 !
    contract_q, _ = run_analysis(df, quad_actions[0]["new_plan"], meta)
    assert contract_q["result"]["r2"] > 0.90
    assert contract_q["result"]["p_value"] < 0.001


def test_trap_extreme_vif_and_sign_flip():
    df, meta = parse_dataset(CSV_SUBTILS.encode("utf-8"), filename="subtils.csv")
    df = exclude_columns(df, ["Dossier_ID"])
    plan = {
        "mode": "multi",
        "y": "Performance_Q3",
        "xs": ["Anciennete_Poste", "Anciennete_Groupe"],
        "alpha": 0.05,
        "question": "Anciennetés -> Perf ?",
    }
    contract, _ = run_analysis(df, plan, meta)
    flag_codes = {f["code"] for f in contract["flags"]}
    assert "vif_critical" in flag_codes
    assert "beta_out_of_bounds" in flag_codes
    assert "sign_flip" in flag_codes
    assert contract["coefficients"][1]["VIF"] > 1000

    p2 = run_phase2_interpretation(contract)
    assert "ne doivent pas être interprétés" in " ".join(p2["agent1_methodology_audit"])
    assert any(len(a["new_plan"]["xs"]) == 1 for a in p2["recommended_actions"])


def test_ultimate_dataset_welch_hc3_wilcoxon_montecarlo():
    ultime = Path(r"C:\Users\Bibi\.gemini\antigravity\brain\8802d19f-1c88-4080-bde7-63bec90bee06\dataset_rh_ultime.csv")
    if not ultime.exists():
        pytest.skip("dataset_rh_ultime.csv non présent")

    df, meta = parse_dataset(ultime.read_bytes(), filename=ultime.name)
    assert scan_dataframe(df)["blocked"] is False

    # 1. Welch ANOVA + Games-Howell
    c1, _ = run_analysis(df, {"mode": "anova", "y": "Salaire_K", "xs": ["Site"]}, meta)
    assert c1["result"]["method"] == "Welch's ANOVA"
    assert abs(c1["result"]["statistic"] - 126.6) < 0.5
    assert c1["posthoc"][0]["method"] == "Games-Howell"

    # 2. Wilcoxon signé
    c2, _ = run_analysis(df, {"mode": "signed", "y": "Stress_Apres", "xs": ["Stress_Avant"]}, meta)
    assert c2["result"]["p_value"] < 0.01
    assert c2["result"]["zero_diff_count"] == 31

    # 3. Régression HC3
    c3, _ = run_analysis(df, {"mode": "multi", "y": "Engagement", "xs": ["Charge_Hebdo", "Anciennete_Ans"]}, meta)
    assert c3["result"]["robust_hc3"] is True

    # 4. Chi2 Monte Carlo (effectifs attendus faibles)
    c4, _ = run_analysis(df, {"mode": "chi", "y": "Site", "xs": ["Statut"]}, meta)
    assert "Monte Carlo" in c4["result"]["method"]


def test_privacy_firewall_and_reproducible_script():
    df, meta = parse_dataset(CSV_SUBTILS.encode("utf-8"), filename="subtils.csv")
    df = exclude_columns(df, ["Dossier_ID"])
    contract, _ = run_analysis(df, {"mode": "desc", "y": "Engagement", "xs": []}, meta)

    # Vérifier le pare-feu RGPD
    bad_contract = {**contract, "records": [{"secret": "Jean Dupont"}]}
    with pytest.raises(PermissionError):
        assert_aggregated_only(bad_contract)

    # Vérifier le script Python reproductible lisible (pas de Base64)
    script = generate_reproducible_script(df, contract)
    assert "base64" not in script.lower()
    assert "assert actual_sha == EXPECTED_PAYLOAD_SHA256" in script
    assert contract["metadata"]["sha256_raw_file"] in script


def test_vif_mathematical_invariant_and_question_coherence():
    ultime = Path(r"C:\Users\Bibi\.gemini\antigravity\brain\8802d19f-1c88-4080-bde7-63bec90bee06\dataset_rh_ultime.csv")
    if not ultime.exists():
        pytest.skip("dataset_rh_ultime.csv non présent")

    df, meta = parse_dataset(ultime.read_bytes(), filename=ultime.name)

    # 1. Invariant mathématique VIF : deux variables corrélées à r > 0.99 doivent avoir le même VIF centré
    c_vif, _ = run_analysis(
        df,
        {"mode": "multi", "y": "Engagement", "xs": ["Charge_Hebdo", "Heures_Sup_Mois", "Anciennete_Ans"]},
        meta,
    )
    vifs = {c["term"]: c["VIF"] for c in c_vif["coefficients"] if c["VIF"] is not None}
    assert abs(vifs["Charge_Hebdo"] - vifs["Heures_Sup_Mois"]) < 0.2
    assert vifs["Charge_Hebdo"] > 300.0
    assert vifs["Anciennete_Ans"] < 1.5

    # 2. Cohérence Question <-> Variables : alerte si la question parle d'engagement mais l'ANOVA porte sur Anciennete_Ans
    c_mis, _ = run_analysis(
        df,
        {
            "mode": "anova",
            "y": "Anciennete_Ans",
            "xs": ["Site"],
            "question": "La charge de travail explique-t-elle l'engagement ?",
        },
        meta,
    )
    p2 = run_phase2_interpretation(c_mis)
    audit_text = " ".join(p2["agent1_methodology_audit"])
    assert "Incohérence Question ↔ Variables" in audit_text
    assert "Engagement" in audit_text


def test_auto_planner_v3_european_csv_and_5_sub_analyses():
    v3 = Path(r"C:\Users\Bibi\.gemini\antigravity\brain\8802d19f-1c88-4080-bde7-63bec90bee06\dataset_exigeant_v3.csv")
    if not v3.exists():
        pytest.skip("dataset_exigeant_v3.csv non présent")

    # 1. Auto-détection séparateur ';' + décimale ',' + recodage '-99'
    df, meta = parse_dataset(v3.read_bytes(), filename=v3.name, decimal="auto", custom_missing=["-99"])
    assert meta["delimiter"] == ";"
    assert meta["decimal"] == ","
    assert df["Note_Finale"].isna().sum() == 2

    # 2. Double PII bloquée en un coup
    pii = scan_dataframe(df)
    assert pii["blocked"] is True
    assert set(pii["flagged_columns"]) >= {"Student_ID", "Telephone_Contact"}
    df_clean = exclude_columns(df, pii["flagged_columns"])
    assert scan_dataframe(df_clean)["blocked"] is False

    # 3. Détection automatique des 5 sous-analyses depuis la question maîtresse
    q = (
        "L'atelier de préparation a-t-il réduit l'anxiété des étudiants, "
        "le temps de sommeil influence-t-il le taux d'erreur à l'examen, "
        "quels facteurs (révisions, pages lues, assiduité) expliquent la note finale, "
        "le présentiel surpasse-t-il le distanciel, "
        "et la mention dépend-elle de la filière ?"
    )
    types = infer_column_types(df_clean)
    plans = auto_plan_from_question(q, df_clean, types)
    assert len(plans) == 5
    modes = [p["mode"] for p in plans]
    assert modes == ["pair", "reg", "multi", "ind", "chi"]

    # 4. Exécution bout-en-bout des 5 plans + Phase 2 sans erreur
    for p in plans:
        c, _ = run_analysis(df_clean, p, meta)
        p2 = run_phase2_interpretation(c)
        assert p2["agent2_apa7_report"]
        assert p2["agent3_business_summary"]
        # Critère d'acceptation audit : sur la régression multiple (plan #3),
        # Assiduite_Pct (VIF ~ 1) doit être préservée dans la synthèse et le rapport APA 7 !
        if p["mode"] == "multi":
            assert "Assiduite_Pct" in p2["agent3_business_summary"]
            assert "Assiduite_Pct" in p2["agent2_apa7_report"]
            assert "Heures_Revision" in p2["agent3_business_summary"]
            assert "Pages_Lues" in p2["agent3_business_summary"]


def test_palier2_logistic_corr_rm_anova_and_exports():
    import io
    import fitz
    import numpy as np
    from docx import Document

    rng = np.random.default_rng(123)
    n = 80
    x1 = rng.normal(0, 1, n)
    x2 = rng.normal(0, 1, n)
    prob = 1.0 / (1.0 + np.exp(-(2.2 * x1 - 0.1 * x2)))
    y_bin = np.where(rng.random(n) < prob, "Oui", "Non")
    t0 = rng.normal(50, 8, n)
    t1 = t0 + rng.normal(6, 3, n)
    t2 = t1 + rng.normal(5, 3, n)

    df = pd.DataFrame({"Cible": y_bin, "X1": x1, "X2": x2, "T0": t0, "T1": t1, "T2": t2})
    meta = {"filename": "palier2_test.csv", "sha256_raw_file": "abc123", "custom_missing": ["-999"]}

    # 1. Régression logistique
    c_log, pd_log = run_analysis(df, {"mode": "logit", "y": "Cible", "xs": ["X1", "X2"], "question": "X1 prédit-il Cible ?"}, meta)
    assert c_log["result"]["significant"] is True
    assert c_log["result"]["auc"] > 0.80
    assert c_log["coefficients"][1]["OR"] > 2.5
    p2_log = run_phase2_interpretation(c_log)
    assert "AUC" in p2_log["agent3_business_summary"]

    # 2. Matrice de corrélations
    c_cor, pd_cor = run_analysis(df, {"mode": "corr", "y": "T0", "xs": ["T1", "T2"], "question": "Corrélations T0/T1/T2"}, meta)
    assert c_cor["result"]["significant"] is True
    assert len(c_cor["posthoc"]) == 3
    p2_cor = run_phase2_interpretation(c_cor)
    assert "Holm" in p2_cor["agent2_apa7_report"]

    # 3. ANOVA mesures répétées (Greenhouse-Geisser + Friedman)
    c_rm, pd_rm = run_analysis(df, {"mode": "rm_anova", "y": "T0", "xs": ["T1", "T2"], "question": "Évolution T0 -> T1 -> T2"}, meta)
    assert c_rm["result"]["significant"] is True
    assert 0.5 <= c_rm["result"]["gg_epsilon"] <= 1.0
    assert c_rm["result"]["friedman_p"] < 0.001
    p2_rm = run_phase2_interpretation(c_rm)
    assert "Greenhouse-Geisser" in p2_rm["agent2_apa7_report"]

    # 4. Export PDF natif + Word .docx avec graphiques intégrés
    items = [(c_log, p2_log, pd_log), (c_cor, p2_cor, pd_cor), (c_rm, p2_rm, pd_rm)]
    pdf_bytes = build_pdf_report(items, "Test Palier 2 complet")
    assert pdf_bytes[:4] == b"%PDF"
    doc_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert len(doc_pdf) >= 2
    full_txt = "\n".join(pg.get_text() for pg in doc_pdf)
    assert "Rapport" in full_txt and "abc123" in full_txt

    docx_bytes = build_docx_report(items, "Test Palier 2 complet")
    doc_w = Document(io.BytesIO(docx_bytes))
    assert any("abc123" in p.text for p in doc_w.paragraphs)
    assert len(doc_w.inline_shapes) >= 3


def test_off_topic_question_rejected_before_compute():
    v8 = Path(r"C:\Users\Bibi\Downloads\dataset_saas_palier2_v8.csv")
    if not v8.exists():
        pytest.skip("dataset_saas_palier2_v8.csv non présent")

    df, _ = parse_dataset(v8.read_bytes(), filename=v8.name, decimal="auto", custom_missing=["-999"])
    df_c = exclude_columns(df, scan_dataframe(df)["flagged_columns"])
    types = infer_column_types(df_c)

    # Texte bancaire collé par erreur sur le CSV SaaS -> 0 plan détecté (pas de repli silencieux vers desc)
    wrong_text = "Sur les 130 observations appariées, le délai moyen passe de 19,14 à 16,66 jours, soit 2,48 jours de baisse."
    assert auto_plan_from_question(wrong_text, df_c, types) == []

    # Question SaaS correcte -> exactement les 5 analyses attendues
    right_q = (
        "La nouvelle interface a-t-elle augmenté le NPS, "
        "le temps d'onboarding influence-t-il la rétention, "
        "quels facteurs (licences actives, utilisateurs jour, score support, ancienneté mois) expliquent le revenu annuel, "
        "l'usage hebdo varie-t-il selon le plan tarif, "
        "et le churn dépend-il du CSM dédié ?"
    )
    plans = auto_plan_from_question(right_q, df_c, types)
    assert [p["mode"] for p in plans] == ["pair", "reg", "multi", "anova", "chi"]





