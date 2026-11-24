"""Tests de régression des garde-fous transversaux (RH, clinique, linguistique).

Toutes les données sont synthétiques ; aucune donnée personnelle n'est envoyée
à la Phase 2. Exécuter avec : python -m pytest -q tests/test_scientific_guardrails.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.auto_planner import auto_plan_from_question
from src.scientific_guardrails import build_design_flags, render_scientific_warnings
from src.stats_engine import infer_column_types, run_analysis
from src.phase2_agents import run_phase2_interpretation


def _codes(flags):
    return {flag["code"] for flag in flags}


def _lexical_frame(n=40):
    rng = np.random.default_rng(74101)
    years = np.arange(1985, 1985 + n)
    genre = np.where(np.arange(n) < n // 2, "Pop", "Rap")
    return pd.DataFrame({
        "Annee": years,
        "MATTR_50": 60 + 0.1 * np.arange(n) + rng.normal(0, 2, n),
        "Genre_Musical": genre,
        "Artiste": [f"artist_{j // 2}" for j in range(n)],
    })


def test_auto_planner_uses_year_as_predictor_in_any_phrase_order():
    df = _lexical_frame()
    types = infer_column_types(df[["MATTR_50", "Annee"]])
    q = "MATTR_50 évolue-t-il avec Annee ?"
    plans = auto_plan_from_question(q, df, types, language="fr")
    assert len(plans) == 1
    assert plans[0]["mode"] == "reg"
    assert plans[0]["y"] == "MATTR_50"
    assert plans[0]["xs"] == ["Annee"]


def test_design_flags_sampling_cluster_trend_and_lexical_scope():
    df = _lexical_frame()
    plan = {"mode": "reg", "y": "MATTR_50", "xs": ["Annee"], "alpha": 0.05,
            "language": "fr", "question": "Le MATTR diminue-t-il au fil des années ?"}
    meta = {"filename": "corpus.csv", "sampling_method": "non_probabilistic_purposive_selection"}
    contract, _ = run_analysis(df, plan, meta)
    codes = _codes(contract["flags"])
    assert {"nonrepresentative_sampling", "cluster_dependence",
            "temporal_composition_shift", "lexical_scope_only"}.issubset(codes)
    cluster = next(f for f in contract["flags"] if f["code"] == "cluster_dependence")
    assert cluster["repeated_rows"] == 40 and cluster["n_clusters"] == 20
    # Le contrat Phase 2 ne contient aucun contenu brut des lignes ni noms d'artistes.
    assert "artist_0" not in str(contract)
    phase2 = run_phase2_interpretation(contract)
    assert "nonrepresentative_sampling" in " ".join(phase2["agent1_methodology_audit"])
    assert "langue" in phase2["agent3_business_summary"]


def test_structural_mattr_missing_never_silently_treated_as_random():
    df = _lexical_frame().drop(columns=["Artiste"])
    df["MATTR_100"] = df["MATTR_50"] - 2.0
    df["Eligible_MATTR_100"] = "Oui"
    df.loc[0, "MATTR_100"] = np.nan
    df.loc[0, "Eligible_MATTR_100"] = "Non"
    plan = {"mode": "reg", "y": "MATTR_100", "xs": ["Annee"], "alpha": 0.05,
            "language": "fr", "question": "MATTR_100 selon Annee"}
    contract, _ = run_analysis(df, plan, {"filename": "short-lyrics.csv"})
    assert "structural_mattr_missing" in _codes(contract["flags"])
    f = next(x for x in contract["flags"] if x["code"] == "structural_mattr_missing")
    assert f["count"] == 1
    assert contract["result"]["n_complete"] == len(df) - 1


def test_non_significance_must_not_be_equated_to_no_effect():
    x = np.arange(-10, 11, dtype=float)
    df = pd.DataFrame({"Annee": x + 2000, "Score": x**2})
    plan = {"mode": "reg", "y": "Score", "xs": ["Annee"], "alpha": 0.05,
            "language": "fr", "question": "Score varie-t-il avec Annee ?"}
    contract, _ = run_analysis(df, plan, {"filename": "clinical-test.csv"})
    assert contract["result"]["significant"] is False
    assert "non_significance_not_equivalence" in _codes(contract["flags"])
    p2 = run_phase2_interpretation(contract)
    assert "preuve d'absence" in p2["agent3_business_summary"]
    assert "non_significance_not_equivalence" in " ".join(p2["agent1_methodology_audit"])


def test_group_size_flags_and_unknown_design_are_epistemic_not_fabricated():
    df = pd.DataFrame({
        "Service": ["A"] * 5 + ["B"] * 30,
        "Score": [10.0, 12, 11, 10, 13] + list(np.arange(30, dtype=float)),
    })
    plan = {"mode": "ind", "y": "Score", "xs": ["Service"],
            "alpha": 0.05, "language": "fr"}
    contract, _ = run_analysis(df, plan, {"filename": "rh.csv"})
    codes = _codes(contract["flags"])
    assert {"small_group", "unbalanced_group_sizes",
            "representativeness_unverified", "independence_unverified"}.issubset(codes)
    assert "nonrepresentative_sampling" not in codes


def test_multilingual_caveats_are_present_and_do_not_invent_significance():
    contract = {"result": {"significant": False},
                "flags": [{"code": "lexical_scope_only"},
                          {"code": "nonrepresentative_sampling"}]}
    for lang in ("fr", "nl", "en"):
        alerts, caveat = render_scientific_warnings(contract, lang)
        assert len(alerts) == 3
        assert caveat and "non_significance_not_equivalence" in " ".join(alerts)


def test_flags_are_aggregated_without_rows():
    df = _lexical_frame()
    plan = {"mode": "reg", "y": "MATTR_50", "xs": ["Annee"]}
    flags = build_design_flags(df, plan, {"filename": "pilot.csv"})
    forbidden = {"records", "raw_rows", "raw_data", "dataframe"}
    assert not any(key in forbidden for f in flags for key in f)
    assert all("artist_0" not in str(f) for f in flags)


def test_methodology_changes_are_included_in_analysis_hash():
    df = _lexical_frame().drop(columns=["Artiste"])
    plan = {"mode": "reg", "y": "MATTR_50", "xs": ["Annee"],
            "alpha": 0.05, "language": "fr"}
    meta = {"filename": "same-input.csv", "sha256_raw_file": "fixed-file-hash"}
    unknown, _ = run_analysis(df, plan, meta)
    purposive, _ = run_analysis(
        df, {**plan, "study_design": {
            "sampling_method": "non_probabilistic_purposive_selection",
            "representative": False}}, meta,
    )
    assert unknown["metadata"]["sha256_analysis_json"] != purposive["metadata"]["sha256_analysis_json"]
    assert purposive["plan"]["study_design"]["representative"] is False
    assert "nonrepresentative_sampling" in _codes(purposive["flags"])
