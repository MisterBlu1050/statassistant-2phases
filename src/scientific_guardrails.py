"""Garde-fous scientifiques déterministes — aucune observation brute en sortie.

Les avertissements sur l'échantillonnage et la dépendance reflètent l'état
des informations disponibles : une propriété inconnue n'est jamais inventée.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd
from scipy import stats


_GROUPING_NAMES = {"artiste", "artist", "auteur", "author", "subject_id", "participant_id",
                   "patient_id", "employee_id", "salarie_id", "id_participant"}
_TEMPORAL_NAMES = {"annee", "year", "jaar", "publication_year", "release_year", "hire_year",
                   "admission_year", "date", "time", "temps", "periode", "period", "mois", "month"}
_COMPOSITION_NAMES = {"genre", "genre_musical", "site", "departement", "department",
                      "pole", "segment", "sector", "secteur", "type_contrat", "contract_type"}
_LEXICAL_PATTERN = re.compile(r"mattr|mtld|lexic|mots?_uniques?|vocabulaire|"
                              r"repetition|longueur_moyenne_mot", re.I)


def _norm_col(column: Any) -> str:
    import unicodedata
    value = unicodedata.normalize("NFKD", str(column).lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch)).replace(" ", "_")


def build_design_flags(df: pd.DataFrame, plan: dict[str, Any],
                       dataset_meta: dict[str, Any]) -> list[dict[str, Any]]:
    """Diagnostique échantillonnage, grappes, confusion temporelle et omissions structurelles.

    Les seules données retournées sont des indicateurs agrégés, sans identifiants
    individuels ni valeurs par personne ou par artiste.
    """
    flags: list[dict[str, Any]] = []
    design = plan.get("study_design")
    design = design if isinstance(design, dict) else {}
    method = str(design.get("sampling_method") or dataset_meta.get("sampling_method") or "unknown").lower()
    representative = design.get("representative", dataset_meta.get("representative_of_target_population"))
    probability_methods = {"simple_random", "stratified_random", "cluster_random",
                           "systematic_random", "probability"}
    nonprob_markers = ("purposive", "convenience", "non_probabil", "quota", "volunteer",
                       "selection_raisonnee", "judgment")
    if representative is False or any(word in method for word in nonprob_markers):
        flags.append({"code": "nonrepresentative_sampling", "severity": "warning",
                      "detail": "Échantillonnage non probabiliste ou non représentatif déclaré : ne pas généraliser à la population cible."})
    elif representative is not True or method not in probability_methods:
        flags.append({"code": "representativeness_unverified", "severity": "info",
                      "detail": "Plan d'échantillonnage et représentativité non établis : les résultats concernent les observations étudiées."})

    y_col = str(plan.get("y", ""))
    x_cols = [str(c) for c in plan.get("xs", [])]
    used = {y_col, *x_cols}
    if _LEXICAL_PATTERN.search(y_col):
        flags.append({"code": "lexical_scope_only", "severity": "warning",
                      "detail": "La mesure porte uniquement sur une dimension lexicale ; elle n'établit pas la richesse globale d'une langue."})

    # Distinguer NA structurel (fenêtre MATTR-100 incompatible) et NA ordinaire.
    if "MATTR_100" in used and "Eligible_MATTR_100" in df.columns:
        eligibility = df["Eligible_MATTR_100"].astype("string").str.casefold()
        ineligible = int(eligibility.eq("non").fillna(False).sum())
        if ineligible:
            flags.append({"code": "structural_mattr_missing", "severity": "warning",
                          "count": ineligible,
                          "detail": f"{ineligible} texte(s) inéligible(s) au MATTR-100 ; exclusion structurelle et non donnée aléatoirement manquante."})

    # La présence de plusieurs observations du même auteur, patient ou sujet
    # invalide l'indépendance présumée dans de nombreux tests usuels.
    cluster_col = design.get("cluster_column") or dataset_meta.get("cluster_column")
    if cluster_col not in df.columns:
        cluster_col = next((c for c in df.columns if _norm_col(c) in _GROUPING_NAMES), None)
    if cluster_col in df.columns:
        counts = df[cluster_col].dropna().value_counts(dropna=True)
        repeated_rows = int(counts[counts > 1].sum())
        if repeated_rows:
            flags.append({"code": "cluster_dependence", "severity": "warning",
                          "n_clusters": int(len(counts)), "repeated_rows": repeated_rows,
                          "detail": f"{repeated_rows} observations relèvent de grappes répétées ({len(counts)} grappes) : tester un modèle tenant compte de cette dépendance."})
    elif design.get("independence_verified") is not True:
        flags.append({"code": "independence_unverified", "severity": "info",
                      "detail": "Aucun identifiant de grappe exploitable : l'indépendance (artiste, participant, patient, site) n'a pas été vérifiée."})

    # Lorsque l'année est un prédicteur, tester le changement de composition
    # d'une variable qualitative omise à l'aide d'écarts de proportions agrégés.
    time_cols = [c for c in x_cols if _norm_col(c) in _TEMPORAL_NAMES and c in df.columns]
    if time_cols and plan.get("mode") in {"reg", "multi", "quad"}:
        t_col = time_cols[0]
        numeric_time = pd.to_numeric(df[t_col], errors="coerce")
        if numeric_time.notna().sum() >= 10 and numeric_time.nunique() >= 3:
            midpoint = numeric_time.median()
            for col in df.columns:
                if col in used or _norm_col(col) not in _COMPOSITION_NAMES:
                    continue
                valid = numeric_time.notna() & df[col].notna()
                if valid.sum() < 10 or not 2 <= df.loc[valid, col].nunique() <= 20:
                    continue
                early = df.loc[valid & (numeric_time <= midpoint), col].astype("string").value_counts(normalize=True)
                late = df.loc[valid & (numeric_time > midpoint), col].astype("string").value_counts(normalize=True)
                categories = early.index.union(late.index)
                tvd = 0.5 * sum(abs(float(early.get(g, 0.0)) - float(late.get(g, 0.0))) for g in categories)
                if tvd >= 0.15:
                    flags.append({"code": "temporal_composition_shift", "severity": "warning",
                                  "variable": str(col), "total_variation": round(tvd, 3),
                                  "detail": f"Composition de {col} différente entre périodes (distance de variation totale {tvd:.3f}) ; tendance chronologique non ajustée pour ce facteur."})

    # Lors d'une comparaison de groupes (ANOVA, t-test, Kruskal, Mann-Whitney),
    # vérifier si une colonne temporelle omise diffère entre les groupes (risque de confusion groupe x temps).
    if plan.get("mode") in {"anova", "ind", "kruskal", "mannwhitney"} and x_cols:
        g_col = x_cols[0]
        if g_col in df.columns:
            for col in df.columns:
                if col in used or _norm_col(col) not in _TEMPORAL_NAMES:
                    continue
                numeric_time = pd.to_numeric(df[col], errors="coerce")
                valid = numeric_time.notna() & df[g_col].notna()
                if valid.sum() < 10 or numeric_time[valid].nunique() < 3:
                    continue
                grouped_times = [
                    grp.to_numpy(dtype=float)
                    for _, grp in numeric_time[valid].groupby(df.loc[valid, g_col].astype("string"))
                    if len(grp) >= 3
                ]
                if len(grouped_times) < 2:
                    continue
                try:
                    kw_stat, kw_p = stats.kruskal(*grouped_times)
                except ValueError:
                    continue
                midpoint = numeric_time[valid].median()
                early = df.loc[valid & (numeric_time <= midpoint), g_col].astype("string").value_counts(normalize=True)
                late = df.loc[valid & (numeric_time > midpoint), g_col].astype("string").value_counts(normalize=True)
                categories = early.index.union(late.index)
                tvd = 0.5 * sum(abs(float(early.get(g, 0.0)) - float(late.get(g, 0.0))) for g in categories)
                if kw_p < 0.05 or tvd >= 0.15:
                    flags.append({
                        "code": "temporal_group_imbalance",
                        "severity": "warning",
                        "time_variable": str(col),
                        "group_variable": str(g_col),
                        "kruskal_stat": round(float(kw_stat), 3),
                        "kruskal_p": round(float(kw_p), 4),
                        "total_variation": round(tvd, 3),
                        "detail": (
                            f"Distribution temporelle ({col}) déséquilibrée entre les groupes de {g_col} "
                            f"(Kruskal-Wallis p = {kw_p:.4f}, TVD = {tvd:.3f}) ; risque de confusion groupe × temps — "
                            f"envisager une analyse ajustée pour {col}."
                        ),
                    })
    return flags


def render_scientific_warnings(contract: dict[str, Any], language: str = "fr") -> tuple[list[str], str]:
    """Traduit les alertes Phase 1 en réserves opposables aux conclusions Phase 2."""
    translations: dict[str, tuple[str, str, str]] = {
        "nonrepresentative_sampling": (
            "Échantillonnage non représentatif déclaré : aucune généralisation à la population.",
            "Non-representatieve steekproef: geen generalisatie naar de populatie.",
            "Non-representative sampling: do not generalize to the target population."),
        "representativeness_unverified": (
            "Représentativité non documentée : pas de généralisation sans plan de sondage.",
            "Representativiteit niet gedocumenteerd: geen populatieconclusies.",
            "Representativeness is undocumented: do not infer population-wide results."),
        "cluster_dependence": (
            "Observations répétées dans des grappes : les tests supposant l'indépendance peuvent être invalides.",
            "Herhaalde observaties per cluster: onafhankelijkheidsaanname mogelijk geschonden.",
            "Repeated observations within clusters: independence assumptions may be violated."),
        "independence_unverified": (
            "Indépendance des observations non établie ; vérifier les identifiants de grappes.",
            "Onafhankelijkheid van observaties is niet vastgesteld.",
            "Observation independence is unverified; inspect cluster identifiers."),
        "temporal_composition_shift": (
            "La composition des groupes évolue dans le temps : une tendance brute peut être confondue.",
            "Groepssamenstelling verandert doorheen de tijd: ruwe trends kunnen vertekend zijn.",
            "Group composition changes over time: unadjusted trends may be confounded."),
        "temporal_group_imbalance": (
            "Distribution temporelle déséquilibrée entre les groupes : risque de confusion groupe × temps ; envisager une analyse ajustée.",
            "Ongelijke tijdsverdeling tussen groepen: risico op verstrengeling groep × tijd; overweeg een gecorrigeerde analyse.",
            "Temporal distribution differs across groups: risk of group × time confounding; consider a time-adjusted analysis."),
        "structural_mattr_missing": (
            "MATTR-100 : exclusions structurelles de textes trop courts ; analyser la sélection.",
            "MATTR-100: structurele uitsluiting van te korte teksten; controleer selectie.",
            "MATTR-100: structurally excluded short texts; assess selection bias."),
        "lexical_scope_only": (
            "Mesure lexicale seulement : ne pas conclure à un appauvrissement général de la langue.",
            "Alleen lexicale maat: geen uitspraak over algemene taalverarming.",
            "Lexical metric only: no inference about overall language impoverishment."),
        "non_significance_not_equivalence": (
            "Résultat non significatif : absence de preuve d'effet ≠ preuve d'absence d'effet ; une équivalence exige un test dédié.",
            "Niet-significant resultaat: geen bewijs voor een effect is geen bewijs voor afwezigheid van een effect.",
            "Non-significance is not evidence of no effect; equivalence requires a dedicated test."),
        "small_group": (
            "Au moins un groupe de faible effectif : puissance et précision potentiellement réduites.",
            "Minstens één kleine groep: beperkte statistische power en precisie mogelijk.",
            "At least one small group: potentially limited statistical power and precision."),
        "unbalanced_group_sizes": (
            "Effectifs des groupes déséquilibrés : vérifier la robustesse de la comparaison.",
            "Ongelijke groepsgroottes: controleer robuustheid van de vergelijking.",
            "Unequal group sizes: assess robustness of the group comparison."),
    }
    lang_idx = {"fr": 0, "nl": 1, "en": 2}.get(language, 0)
    codes = {str(f.get("code")) for f in contract.get("flags", [])}
    if contract.get("result", {}).get("significant") is False:
        codes.add("non_significance_not_equivalence")
    ordered = [k for k in translations if k in codes]
    alerts = ["⚠️ **" + key + "** — " + translations[key][lang_idx] for key in ordered]
    # Une réserve structurée, ajoutée aux deux rapports déterministes.
    caveat = " ".join(translations[key][lang_idx] for key in ordered)
    return alerts, caveat


def find_mentioned_unselected_columns(
    question: str,
    selected_cols: set[str],
    all_columns: list[str],
) -> list[str]:
    """Détecte les colonnes explicitement mentionnées dans la question mais absentes du modèle.

    Masque d'abord les correspondances exactes des colonnes déjà sélectionnées afin d'éviter
    les faux positifs par collision de préfixe/sous-token (ex: MATTR_100 vs MATTR_50).
    """
    import unicodedata
    q_clean = unicodedata.normalize("NFKD", str(question).lower())
    q_id = "".join(ch for ch in q_clean if not unicodedata.combining(ch))
    if not q_id.strip():
        return []

    generic_words = {
        "taux", "score", "indice", "heures", "jours", "nombre", "niveau",
        "part", "type", "avant", "apres", "moyen", "moyenne", "total", "global",
        "rate", "hours", "days", "level", "mean", "average", "uren", "dagen", "aantal",
    }

    # 1. Masquer dans la question toutes les mentions exactes des colonnes sélectionnées
    masked_id = q_id
    selected_tokens: set[str] = set()
    exact_selected_hits = 0
    for scol in sorted(selected_cols, key=len, reverse=True):
        sn = _norm_col(scol)
        if not sn:
            continue
        if re.search(rf"(?<![a-z0-9_]){re.escape(sn)}(?![a-z0-9_])", masked_id):
            exact_selected_hits += 1
            masked_id = re.sub(rf"(?<![a-z0-9_]){re.escape(sn)}(?![a-z0-9_])", " ", masked_id)
        for tok in re.split(r"[_\s-]+", sn):
            if len(tok) >= 4:
                selected_tokens.add(tok)

    masked_words = masked_id.replace("_", " ")
    # Si la question cite déjà explicitement les identifiants exacts des colonnes sélectionnées,
    # exiger une correspondance exacte (ou tous les tokens significatifs) pour les autres colonnes.
    strict_identifier_mode = exact_selected_hits >= len(selected_cols) and exact_selected_hits > 0

    mentioned: list[str] = []
    for col in all_columns:
        if col in selected_cols:
            continue
        cn = _norm_col(col)
        if not cn:
            continue
        # Correspondance exacte d'identifiant sur le texte masqué
        if re.search(rf"(?<![a-z0-9_]){re.escape(cn)}(?![a-z0-9_])", masked_id):
            mentioned.append(col)
            continue

        # Correspondance partielle par tokens significatifs non génériques et non couverts par une colonne sélectionnée
        sig_tokens = [
            t for t in re.split(r"[_\s-]+", cn)
            if len(t) >= 4 and t not in generic_words and t not in selected_tokens
        ]
        if not sig_tokens:
            continue
        hits = [t for t in sig_tokens if re.search(rf"\b{re.escape(t)}\w*", masked_words)]
        all_sig = [t for t in re.split(r"[_\s-]+", cn) if len(t) >= 4 and t not in generic_words]
        if strict_identifier_mode:
            if len(hits) == len(all_sig) and len(all_sig) >= 2:
                mentioned.append(col)
        else:
            min_needed = 2 if len(all_sig) >= 3 else 1
            if len(hits) >= min_needed:
                mentioned.append(col)
    return mentioned
