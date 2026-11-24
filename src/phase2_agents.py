"""Phase 2 — Couche d'Intelligence Métier (Multi-Agents sur JSON agrégé uniquement).

Reçoit EXCLUSIVEMENT le Contrat JSON certifié de la Phase 1 (zéro donnée individuelle) :
1. Agent Auditeur Méthodologique : détecte les pièges (VIF, non-linéarité, outliers, sign-flip)
   et propose des actions de recalcul retour Phase 1 validées par l'humain.
2. Agent Rédacteur Académique APA 7 : rédige le paragraphe narratif continu prêt à publier.
3. Agent Traducteur Métier : répond en langage clair (Oui/Non/Prudence) pour décideurs RH/étudiants.

Inclut un routeur multi-modèles (Mode Local Déterministe sans clé API + connecteur REST
Enterprise / ZDR / Ollama local).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from src.scientific_guardrails import render_scientific_warnings


def assert_aggregated_only(contract: dict[str, Any]) -> None:
    """Pare-feu RGPD : garantit qu'aucune ligne brute n'est envoyée en Phase 2."""
    if contract.get("privacy_guarantee") != "AGGREGATED_ONLY_NO_RAW_ROWS":
        raise PermissionError("Contrat non certifié : transmission vers la Phase 2 bloquée par sécurité RGPD.")
    forbidden_keys = {"records", "raw_rows", "raw_data", "dataframe"}
    if forbidden_keys.intersection(contract.keys()):
        raise PermissionError("Présence de données brutes détectée dans le contrat Phase 2 : blocage immédiat.")


def _fmt_p(p: float | None) -> str:
    if p is None:
        return "N/A"
    if p < 0.001:
        return "< .001"
    return f"= .{f'{p:.3f}'.split('.')[1]}"


def _fmt_num(val: float | None, ndigits: int = 2) -> str:
    if val is None:
        return "N/A"
    return f"{val:.{ndigits}f}"


def _fmt_df(val: float | None) -> str:
    if val is None:
        return "N/A"
    return str(int(round(val))) if abs(val - round(val)) < 1e-6 else f"{val:.2f}"


def _fmt_bounded(val: float | None, ndigits: int = 2) -> str:
    """Formate un indice borné entre -1 et 1 sans zéro initial (norme APA 7 : .01, -.81)."""
    if val is None:
        return "N/A"
    s = f"{abs(val):.{ndigits}f}"
    if s.startswith("0."):
        s = s[1:]
    return f"-{s}" if val < 0 else s


def _fmt_ci(ci: list[float | None] | None, bounded: bool = False) -> str:
    if not ci or len(ci) != 2 or ci[0] is None or ci[1] is None:
        return "[N/A]"
    fn = _fmt_bounded if bounded else _fmt_num
    return f"[{fn(ci[0])}, {fn(ci[1])}]"


METHOD_FR = {
    "One-way ANOVA": "ANOVA à un facteur",
    "Welch's ANOVA": "ANOVA de Welch",
    "Paired-samples t-test": "test *t* pour échantillons appariés",
    "Wilcoxon signed-rank test": "test des rangs signés de Wilcoxon",
    "Independent-samples t-test (Student)": "test *t* de Student pour échantillons indépendants",
    "Welch's t-test": "test *t* de Welch pour échantillons indépendants",
    "Mann-Whitney U test": "test *U* de Mann-Whitney",
    "Kruskal-Wallis test": "test de Kruskal-Wallis",
    "Pearson's chi-square test": "test du χ² de Pearson",
    "Fisher's exact test": "test exact de Fisher",
    "Chi-square (Monte Carlo, 2000)": "test du χ² (simulation Monte Carlo, 2 000 tirages)",
}


def _agent1_audit(contract: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    """Agent 1 : Auditeur Méthodologique + génération des boutons de boucle retour Phase 1."""
    plan = contract["plan"]
    res = contract["result"]
    flags = contract.get("flags", [])
    flag_codes = {f["code"] for f in flags}

    alerts: list[str] = []
    actions: list[dict[str, Any]] = []

    # 0. Contrôle de cohérence Question <-> Variables sélectionnées
    question_raw = plan.get("question") or ""
    if question_raw.strip():
        from src.scientific_guardrails import find_mentioned_unselected_columns
        selected = {plan["y"], *plan.get("xs", [])}
        all_cols = contract.get("metadata", {}).get("all_columns", [])
        mentioned_unselected = find_mentioned_unselected_columns(question_raw, selected, all_cols)
        if mentioned_unselected:
            alerts.append(
                f"⚠️ **Incohérence Question ↔ Variables** : votre question semble mentionner "
                f"**{', '.join(mentioned_unselected)}**, qui ne fait pas partie des variables analysées "
                f"(`{plan['y']}` ~ `{', '.join(plan.get('xs', []))}`). Vérifiez votre sélection en Phase 1."
            )

    # 1. Colinéarité / VIF
    vif_flags = [f for f in flags if f["code"] == "vif_critical"]
    if vif_flags:
        max_vif = max(f["vif"] for f in vif_flags)
        vars_col = [f["variable"] for f in vif_flags]
        if max_vif > 100:
            alerts.append(
                f"⛔ **Colinéarité extrême (VIF max = {max_vif})** sur {', '.join(vars_col)} : "
                "les prédicteurs sont quasi redondants. **Les coefficients individuels (B, β, p) ne doivent pas être interprétés.**"
            )
        else:
            alerts.append(
                f"⚠️ **Colinéarité élevée (VIF max = {max_vif})** sur {', '.join(vars_col)} : les erreurs standards sont gonflées."
            )
        if len(plan.get("xs", [])) >= 2:
            drop_var = vars_col[-1]
            remaining = [c for c in plan["xs"] if c != drop_var]
            actions.append(
                {
                    "label": f"Recalculer sans « {drop_var} » (supprimer la colinéarité)",
                    "new_plan": {**plan, "mode": "reg" if len(remaining) == 1 else "multi", "xs": remaining},
                }
            )

    # 2. |beta| > 1 et inversion de signe
    for f in flags:
        if f["code"] == "beta_out_of_bounds":
            alerts.append(f"⛔ **Artefact standardisé** : {f['detail']}")
        elif f["code"] == "sign_flip":
            alerts.append(f"⛔ **Inversion de signe (Paradoxe de colinéarité)** : {f['detail']}")

    # 3. Non-linéarité quadratique (courbe en U / U inversé)
    for f in flags:
        if f["code"] == "possible_nonlinearity":
            alerts.append(
                f"⛔ **Relation non linéaire probable (courbe en U / U inversé)** : {f['detail']} "
                "Un modèle linéaire masque une association curvilinéaire marquée dans l'échantillon."
            )
            actions.append(
                {
                    "label": f"Tester le modèle quadratique sur « {f['variable']} » (Phase 1)",
                    "new_plan": {**plan, "mode": "quad", "xs": [f["variable"]]},
                }
            )

    # 4. Normalité violée / Outliers -> bascule non-paramétrique suggérée
    if "normality_failed" in flag_codes:
        mode = plan["mode"]
        if mode == "anova":
            extra = " (rapport de variances extrême détecté)" if "extreme_variance_ratio" in flag_codes else ""
            alerts.append(
                f"⚠️ **Postulat de normalité violé**{extra} : une valeur aberrante ou asymétrie peut biaiser la moyenne et masquer un effet réel."
            )
            actions.append(
                {
                    "label": "Basculer sur le test non-paramétrique de Kruskal-Wallis (Phase 1)",
                    "new_plan": {**plan, "mode": "kw"},
                }
            )
        elif mode == "ind":
            alerts.append(
                "⚠️ **Normalité violée dans au moins un groupe** : la moyenne peut être tirée par un profil atypique. Un test sur les rangs (Mann-Whitney) est recommandé en sensibilité."
            )
            actions.append(
                {
                    "label": "Basculer sur le test de Mann-Whitney U (Phase 1)",
                    "new_plan": {**plan, "mode": "mw"},
                }
            )
        elif mode == "pair":
            alerts.append(
                "⚠️ **Normalité des différences violée** : le test de Wilcoxon sur rangs signés est plus robuste que le test t apparié."
            )
            actions.append(
                {
                    "label": "Basculer sur le test de Wilcoxon signé (Phase 1)",
                    "new_plan": {**plan, "mode": "signed"},
                }
            )
        elif mode in ("reg", "multi", "quad"):
            alerts.append(
                "⚠️ **Résidus non normaux (Shapiro-Wilk p < .05)** : même avec HC3 (qui corrige l'hétéroscédasticité), vérifiez l'absence d'une variable omise ou d'un effet non linéaire."
            )

    if "outliers_detected" in flag_codes:
        for f in flags:
            if f["code"] == "outliers_detected":
                alerts.append(f"⚠️ **Valeurs extrêmes** : {f['detail']}")

    if "low_power_wide_ci" in flag_codes:
        alerts.append(
            "ℹ️ **Faible puissance statistique** : l'intervalle de confiance de la taille d'effet est très large. Un résultat non significatif ne prouve pas l'absence d'effet."
        )

    if "sparse_contingency" in flag_codes:
        alerts.append("ℹ️ **Effectifs attendus faibles** : le moteur a automatiquement basculé sur un test exact / Monte Carlo.")

    # Rappel systématique sur la causalité
    alerts.append(
        "ℹ️ **Limite méthodologique (Causalité)** : une analyse observationnelle sans groupe témoin randomisé établit une association statistique, pas un lien de causalité."
    )

    return alerts, actions


def _agent2_apa7(contract: dict[str, Any]) -> str:
    """Agent 2 : Rédacteur Académique APA 7e édition (paragraphe narratif continu)."""
    plan = contract["plan"]
    res = contract["result"]
    groups = contract.get("groups", [])
    effects = contract.get("effects", [])
    posthoc = contract.get("posthoc", [])
    coefs = contract.get("coefficients", [])
    flags = contract.get("flags", [])
    severe_vif = any(f["code"] == "vif_critical" and f["vif"] > 100 for f in flags)

    mode = plan["mode"]
    y_col = plan["y"]
    x_cols = plan.get("xs", [])
    n = res["n_complete"]

    if mode == "desc":
        return (
            f"L'analyse descriptive de *{y_col}* (*N* = {n}) indique une moyenne de *M* = {res['mean']} "
            f"(*SD* = {res['sd']}, IC 95 % [{res['ci_95'][0]}, {res['ci_95'][1]}]) et une médiane de "
            f"*Mdn* = {res['median']} (IQR = [{res['q1']}, {res['q3']}])."
        )

    if mode in ("pair", "signed"):
        g0, g1 = groups[0], groups[1]
        eff = effects[1] if len(effects) > 1 else effects[0]
        p_txt = _fmt_p(res["p_value"])
        verb = "a révélé une différence statistiquement significative" if res["significant"] else "n'a révélé aucune différence statistiquement significative"
        alt_lbl = {"two-sided": "bilatéral", "greater": "unilatéral (hausse)", "less": "unilatéral (baisse)"}.get(
            plan.get("alternative", "two-sided"), "bilatéral"
        )
        if mode == "pair":
            return (
                f"Un test *t* pour échantillons appariés ({alt_lbl}, *N* = {n}) {verb} entre *{g0['label']}* "
                f"(*M* = {_fmt_num(g0['mean'])}, *SD* = {_fmt_num(g0['sd'])}) et *{g1['label']}* "
                f"(*M* = {_fmt_num(g1['mean'])}, *SD* = {_fmt_num(g1['sd'])}), "
                f"*t*({_fmt_df(res['df'][0])}) = {_fmt_num(res['statistic'])}, *p* {p_txt}, Δ*M* = {_fmt_num(res['mean_change'])}, "
                f"*d_z* = {_fmt_num(eff['estimate'])} (IC 95 % bootstrap {_fmt_ci(eff['ci_95'])})."
            )
        return (
            f"Un test des rangs signés de Wilcoxon ({alt_lbl}, *N* = {n}, {res['zero_diff_count']} différences nulles) {verb} "
            f"entre *{g0['label']}* (*Mdn* = {_fmt_num(g0['median'])}) et *{g1['label']}* (*Mdn* = {_fmt_num(g1['median'])}), "
            f"*W* = {_fmt_num(res['statistic'])}, *p* {p_txt}, *r_rb* = {_fmt_bounded(eff['estimate'])} "
            f"(IC 95 % bootstrap {_fmt_ci(eff['ci_95'], bounded=True)})."
        )

    if mode in ("ind", "mw"):
        g0, g1 = groups[0], groups[1]
        p_txt = _fmt_p(res["p_value"])
        verb = "a montré une différence statistiquement significative" if res["significant"] else "n'a montré aucune différence statistiquement significative"
        if mode == "ind":
            eff = effects[1]
            m_fr = METHOD_FR.get(res["method"], res["method"])
            return (
                f"Un {m_fr} (*N* = {n}) {verb} sur *{y_col}* entre le groupe *{g0['label']}* "
                f"(*n* = {g0['n']}, *M* = {_fmt_num(g0['mean'])}, *SD* = {_fmt_num(g0['sd'])}) et le groupe *{g1['label']}* "
                f"(*n* = {g1['n']}, *M* = {_fmt_num(g1['mean'])}, *SD* = {_fmt_num(g1['sd'])}), "
                f"*t*({_fmt_df(res['df'][0])}) = {_fmt_num(res['statistic'])}, *p* {p_txt}, "
                f"*d* = {_fmt_num(eff['estimate'])} (IC 95 % bootstrap {_fmt_ci(eff['ci_95'])})."
            )
        eff = effects[0]
        return (
            f"Un test *U* de Mann-Whitney (*N* = {n}) {verb} sur *{y_col}* entre *{g0['label']}* "
            f"(*Mdn* = {_fmt_num(g0['median'])}) et *{g1['label']}* (*Mdn* = {_fmt_num(g1['median'])}), "
            f"*U* = {_fmt_num(res['statistic'])}, *p* {p_txt}, *r_rb* = {_fmt_bounded(eff['estimate'])} "
            f"(IC 95 % bootstrap {_fmt_ci(eff['ci_95'], bounded=True)})."
        )

    if mode in ("anova", "kw"):
        p_txt = _fmt_p(res["p_value"])
        eff = effects[0]
        grp_str = ", ".join(
            f"*{g['label']}* (*n* = {g['n']}, *M* = {_fmt_num(g['mean'])}, *SD* = {_fmt_num(g['sd'])}, *Mdn* = {_fmt_num(g['median'])})"
            for g in groups
        )
        verb = "a révélé un effet statistiquement significatif" if res["significant"] else "n'a révélé aucun effet statistiquement significatif"
        if mode == "anova":
            m_fr = METHOD_FR.get(res["method"], res["method"])
            lead = (
                f"Une {m_fr} (*N* = {n}) {verb} de *{x_cols[0]}* sur *{y_col}*, "
                f"*F*({_fmt_df(res['df'][0])}, {_fmt_df(res['df'][1])}) = {_fmt_num(res['statistic'])}, *p* {p_txt}, "
                f"η² = {_fmt_bounded(eff['estimate'])} (IC 95 % bootstrap {_fmt_ci(eff['ci_95'], bounded=True)}). "
                f"Les descriptifs par groupe étaient : {grp_str}."
            )
        else:
            lead = (
                f"Un test de Kruskal-Wallis (*N* = {n}) {verb} de *{x_cols[0]}* sur *{y_col}*, "
                f"*H*({_fmt_df(res['df'][0])}) = {_fmt_num(res['statistic'])}, *p* {p_txt}, "
                f"ε² = {_fmt_bounded(eff['estimate'])} (IC 95 % bootstrap {_fmt_ci(eff['ci_95'], bounded=True)}). "
                f"Les descriptifs par groupe étaient : {grp_str}."
            )
        if posthoc:
            sig_pairs = [
                f"*{ph['a']}* vs *{ph['b']}* (Δ = {_fmt_num(ph['difference'])}, *p_adj* {_fmt_p(ph['p_adj'])})"
                for ph in posthoc
                if ph["p_adj"] is not None and ph["p_adj"] < plan["alpha"]
            ]
            if sig_pairs:
                lead += f" Les comparaisons post-hoc ({posthoc[0]['method']}) montrent des écarts significatifs pour : {', '.join(sig_pairs)}."
            else:
                lead += f" Aucune comparaison par paire ({posthoc[0]['method']}) n'atteint le seuil de significativité après ajustement."
        return lead

    if mode in ("reg", "multi", "quad"):
        p_txt = _fmt_p(res["p_value"])
        verdict = "est statistiquement significatif" if res["significant"] else "n'est pas statistiquement significatif"
        hc3_note = " avec erreurs standards robustes HC3" if res.get("robust_hc3") else ""
        base = (
            f"Un modèle de régression ({res['method']}{hc3_note}, *N* = {n}) prédisant *{y_col}* à partir de "
            f"{', '.join(f'*{c}*' for c in x_cols)} {verdict}, *F*({int(res['df'][0])}, {int(res['df'][1])}) = {res['statistic']}, "
            f"*p* {p_txt}, *R*² = {res['r2']}, *R*² ajusté = {res['r2_adj']}."
        )
        if severe_vif:
            col_vars = {f["variable"] for f in flags if f["code"] == "vif_critical" and f["vif"] > 100}
            clean_coefs = [c for c in coefs[1:] if c["term"] not in col_vars]
            msg = (
                f" En raison d'une multicolinéarité extrême (VIF > 100) entre {', '.join(f'*{v}*' for v in sorted(col_vars))}, "
                "leurs coefficients partiels respectifs ne sont pas interprétables isolément."
            )
            if clean_coefs:
                clean_parts = [
                    f"*{c['term']}* (*B* = {_fmt_num(c['B'], 3)}, β = {_fmt_num(c['beta'], 3)}, *SE* = {_fmt_num(c['SE'], 3)}, *t* = {_fmt_num(c['t'])}, *p* {_fmt_p(c['p'])}, IC 95 % {_fmt_ci(c['ci_95'])})"
                    for c in clean_coefs
                ]
                msg += " En revanche, les prédicteurs non colinéaires restent interprétables : " + " ; ".join(clean_parts) + "."
            return base + msg
        parts = []
        for c in coefs[1:]:
            parts.append(
                f"*{c['term']}* (*B* = {c['B']}, β = {c['beta']}, *SE* = {c['SE']}, *t* = {c['t']}, *p* {_fmt_p(c['p'])}, IC 95 % {c['ci_95']})"
            )
        apa_out = base + " Paramètres estimés : " + " ; ".join(parts) + "."
        nl_flag = next((f for f in flags if f["code"] == "possible_nonlinearity"), None)
        if nl_flag:
            apa_out += (
                f" L'ajout exploratoire d'un terme quadratique améliore nettement l'ajustement, "
                f"*F*({nl_flag['df_add'][0]}, {nl_flag['df_add'][1]}) = {_fmt_num(nl_flag['f_add'])}, *p* {_fmt_p(nl_flag['p_add'])}, "
                f"portant le *R*² à {_fmt_bounded(nl_flag['r2_quadratic'], 3)} (relation en {nl_flag['shape']}, extremum estimé autour de {nl_flag['vertex_x']}). "
                f"Note : les diagnostics de résidus de cette section évaluent le modèle linéaire initial."
            )
        return apa_out

    if mode == "chi":
        p_txt = _fmt_p(res["p_value"])
        eff = effects[0]
        verdict = "une association statistiquement significative" if res["significant"] else "aucune association statistiquement significative"
        stat_part = (
            f"χ²({int(res['df'][0])}) = {res['statistic']}, " if res.get("statistic") is not None else ""
        )
        return (
            f"Un {res['method']} (*N* = {n}) a mis en évidence {verdict} entre *{y_col}* et *{x_cols[0]}*, "
            f"{stat_part}*p* {p_txt}, *V* de Cramér = {_fmt_bounded(eff['estimate'])}."
        )

    if mode == "logit":
        p_txt = _fmt_p(res["p_value"])
        verb = "est statistiquement significatif" if res["significant"] else "n'est pas statistiquement significatif"
        base = (
            f"Une régression logistique binaire (*N* = {n}, classe positive : *{res['positive_class']}*) prédisant *{y_col}* "
            f"à partir de {', '.join(f'*{c}*' for c in x_cols)} {verb}, χ²({_fmt_df(res['df'][0])}) = {_fmt_num(res['statistic'])}, "
            f"*p* {p_txt}, pseudo-*R*² de McFadden = {_fmt_bounded(res['mcfadden_r2'])}, AUC = {_fmt_num(res['auc'], 3)}."
        )
        parts = [
            f"*{c['term']}* (*OR* = {_fmt_num(c['OR'])}, IC 95 % {_fmt_ci(c['OR_ci_95'])}, *z* = {_fmt_num(c['z'])}, *p* {_fmt_p(c['p'])})"
            for c in coefs[1:]
        ]
        return base + " Rapports de cotes : " + " ; ".join(parts) + "."

    if mode == "corr":
        sig_pairs = [
            f"*{ph['a']}* × *{ph['b']}* (*r* = {_fmt_bounded(ph['difference'])}, ρ = {_fmt_bounded(ph['spearman_rho'])}, *p_adj* {_fmt_p(ph['p_adj'])})"
            for ph in posthoc
            if ph["p_adj"] is not None and ph["p_adj"] < plan["alpha"]
        ]
        if sig_pairs:
            return f"L'analyse de corrélations (*N* = {n}, ajustement de Holm) met en évidence {len(sig_pairs)} association(s) significative(s) : " + " ; ".join(sig_pairs) + "."
        return f"L'analyse de corrélations (*N* = {n}, ajustement de Holm) ne met en évidence aucune association significative au seuil de {int(plan['alpha']*100)} %."

    if mode == "rm_anova":
        p_txt = _fmt_p(res["p_value"])
        verb = "a révélé un effet statistiquement significatif" if res["significant"] else "n'a révélé aucun effet statistiquement significatif"
        grp_str = ", ".join(f"*{g['label']}* (*M* = {_fmt_num(g['mean'])}, *SD* = {_fmt_num(g['sd'])})" for g in groups)
        return (
            f"Une ANOVA à mesures répétées avec correction de Greenhouse-Geisser (ε = {_fmt_num(res['gg_epsilon'], 3)}, *N* = {n}) "
            f"{verb} entre les conditions, *F*({_fmt_df(res['df'][0])}, {_fmt_df(res['df'][1])}) = {_fmt_num(res['statistic'])}, "
            f"*p* {p_txt}, η²_p = {_fmt_bounded(effects[0]['estimate'])} (contrôle de Friedman : *p* {_fmt_p(res['friedman_p'])}). "
            f"Moyennes : {grp_str}."
        )

    return ""


def _agent3_business(contract: dict[str, Any]) -> str:
    """Agent 3 : Traducteur Métier en langage naturel pour non-statisticiens (RH / Décideurs)."""
    plan = contract["plan"]
    res = contract["result"]
    groups = contract.get("groups", [])
    posthoc = contract.get("posthoc", [])
    coefs = contract.get("coefficients", [])
    flags = contract.get("flags", [])
    flag_codes = {f["code"] for f in flags}

    mode = plan["mode"]
    y_col = plan["y"]
    x_cols = plan.get("xs", [])
    q = plan.get("question") or f"Analyse de {y_col}"

    if mode == "desc":
        return (
            f"**Réponse directe :** Sur les {res['n_complete']} observations analysées, *{y_col}* s'établit en moyenne à "
            f"**{res['mean']}** (médiane **{res['median']}**, étendue de {res['min']} à {res['max']})."
        )

    # Cas critiques bloquants pour les seules variables colinéaires (préserve les prédicteurs sains !)
    severe_vif_flags = [f for f in flags if f["code"] == "vif_critical" and f["vif"] > 100]
    if severe_vif_flags:
        col_vars = [f["variable"] for f in severe_vif_flags]
        clean_coefs = [c for c in coefs[1:] if c["term"] not in set(col_vars)]
        pct_var = round(res["r2"] * 100, 1)
        clean_txt = ""
        if clean_coefs:
            sig_clean = [c for c in clean_coefs if c["p"] is not None and c["p"] < plan["alpha"]]
            ns_clean = [c for c in clean_coefs if c["p"] is None or c["p"] >= plan["alpha"]]
            parts_clean = []
            if sig_clean:
                items = " ; ".join(
                    f"**{c['term']}** ({c['B']:+.3f} par unité sur *{y_col}*, *p* {_fmt_p(c['p'])})"
                    for c in sig_clean
                )
                parts_clean.append(f"facteur(s) indépendant(s) significatif(s) : {items}")
            if ns_clean:
                ns_items = " ; ".join(f"**{c['term']}** (*p* {_fmt_p(c['p'])})" for c in ns_clean)
                parts_clean.append(f"non significatif(s) dans le modèle complet au seuil de {int(plan['alpha']*100)} % : {ns_items}")
            clean_txt = " En revanche, les variables indépendantes restent interprétables — " + " ; ".join(parts_clean) + "."
        verdict_head = (
            f"**Oui, globalement** ({pct_var} % de variance expliquée, *p* {_fmt_p(res['p_value'])}), **mais avec redondance partielle.**"
            if res.get("significant")
            else "**Verdict : Non concluant (variables redondantes).**"
        )
        return (
            f"{verdict_head} Les variables **{', '.join(col_vars)}** sont quasi redondantes (VIF > 100) et leurs effets "
            f"individuels ne peuvent pas être séparés.{clean_txt} **Recommandation :** conservez une seule des variables "
            f"redondantes tout en maintenant les variables indépendantes."
        )

    if "possible_nonlinearity" in flag_codes:
        nl = next(f for f in flags if f["code"] == "possible_nonlinearity")
        shape = nl.get("shape", "courbe quadratique")
        vertex_txt = f" avec un extremum estimé autour de **{nl['vertex_x']}**" if nl.get("vertex_x") is not None else ""
        f_txt = (
            f" (ajout du terme au carré : *F*({nl['df_add'][0]}, {nl['df_add'][1]}) = {nl['f_add']}, *p* {_fmt_p(nl['p_add'])})"
            if nl.get("f_add") is not None
            else ""
        )
        if res.get("significant"):
            lin_lead = (
                f"**Verdict : Une tendance linéaire est détectée (*p* {_fmt_p(res['p_value'])}), mais elle résume très mal "
                f"la relation ({round(nl['r2_linear']*100, 2)} % seulement) ; une relation non linéaire marquée en {shape}{vertex_txt} domine.** "
            )
        else:
            lin_lead = (
                f"**Verdict : Pas de lien linéaire significatif (*p* {_fmt_p(res['p_value'])}), mais une relation non linéaire "
                f"marquée en {shape}{vertex_txt}.** "
            )
        return (
            f"{lin_lead}"
            f"L'ajustement quadratique exploratoire explique **{round(nl['r2_quadratic']*100, 2)} %** de la variation de *{y_col}*{f_txt}. "
            f"*Réserve : cet extremum décrit l'échantillon observé et ne constitue pas à lui seul une prescription causale.*"
        )

    verdict_word = "**Oui**" if res.get("significant") else "**Non établi**"

    if mode in ("pair", "signed"):
        g0, g1 = groups[0], groups[1]
        is_nps = "nps" in g0["label"].lower() or "nps" in g1["label"].lower()
        pct = "" if is_nps else (f" ({res['pct_change_vs_baseline']:+.1f} % par rapport au niveau initial)" if res.get("pct_change_vs_baseline") is not None else "")
        unit_lbl = "point(s) de NPS" if is_nps else "unité(s)"
        sens = "augmenté" if res["mean_change"] > 0 else "diminué"
        med_chg = f" (médiane des changements individuels : **{res['median_change']:+.2f}**)" if res.get("median_change") is not None else ""
        dist_chg = (
            f" Répartition individuelle : **{res['n_decreased']} baisses**, **{res['n_unchanged']} stables**, **{res['n_increased']} hausses**."
            if res.get("n_decreased") is not None
            else ""
        )
        if res["significant"]:
            return (
                f"**Oui, une évolution est observée** entre *{g0['label']}* (moyenne {g0['mean']}) et *{g1['label']}* (moyenne {g1['mean']}). "
                f"En moyenne, la mesure a {sens} de **{abs(res['mean_change']):.2f} {unit_lbl}**{pct}{med_chg}.{dist_chg} "
                f"*Réserve : sans groupe témoin, cette évolution observée ne prouve pas à elle seule un lien causal.*"
            )
        return (
            f"**Non établi au seuil de {int(plan['alpha']*100)} %** : les {res['n_complete']} paires observées ne suffisent pas "
            f"à conclure à une évolution statistiquement significative entre *{g0['label']}* et *{g1['label']}*."
        )

    if mode in ("ind", "mw"):
        g0, g1 = groups[0], groups[1]
        if res["significant"]:
            return (
                f"**Oui, un écart brut est observé** sur *{y_col}* entre **{g0['label']}** (moyenne {g0['mean']}, médiane {g0['median']}) "
                f"et **{g1['label']}** (moyenne {g1['mean']}, médiane {g1['median']}). "
                f"*Réserve : sans affectation aléatoire, cet écart décrit une association et non un effet causal.*"
            )
        return (
            f"**Non établi au seuil de {int(plan['alpha']*100)} %** : les {res['n_complete']} observations ne suffisent pas "
            f"à établir une différence significative sur *{y_col}* entre **{g0['label']}** et **{g1['label']}**."
        )

    if mode in ("anova", "kw"):
        if not res["significant"]:
            caution = " Attention toutefois : un profil extrême ou un faible effectif peut masquer un écart réel (voir les alertes méthodologiques)." if ("normality_failed" in flag_codes or "low_power_wide_ci" in flag_codes) else ""
            return (
                f"{verdict_word}, l'analyse globale ne détecte pas de différence significative de *{y_col}* selon *{x_cols[0]}*.{caution}"
            )
        ranked = sorted(groups, key=lambda g: g["mean"], reverse=True)
        top_g = ranked[0]
        sig_pairs = [ph for ph in posthoc if ph["p_adj"] is not None and ph["p_adj"] < plan["alpha"]]
        detail = ""
        if sig_pairs:
            detail = " En détail, les écarts significatifs concernent : " + ", ".join(f"**{ph['a']} vs {ph['b']}**" for ph in sig_pairs) + "."
        return (
            f"{verdict_word}, *{y_col}* varie significativement selon *{x_cols[0]}*. "
            f"Le groupe le plus élevé est **{top_g['label']}** (moyenne {top_g['mean']}, médiane {top_g['median']}).{detail}"
        )

    if mode in ("reg", "multi", "quad"):
        pct_var = round(res["r2"] * 100, 1)
        if not res["significant"]:
            return (
                f"{verdict_word}, le modèle global n'explique pas significativement *{y_col}* ({pct_var} % de variation expliquée, *p* {_fmt_p(res['p_value'])})."
            )
        sig_preds = [c for c in coefs[1:] if c["p"] is not None and c["p"] < plan["alpha"]]
        if sig_preds:
            pred_txt = " ; ".join(
                f"**{c['term']}** (chaque +1 unité est associée à **{c['B']:+.3f}** sur *{y_col}*)"
                for c in sig_preds
            )
            return (
                f"{verdict_word}, le modèle explique **{pct_var} %** de la variation de *{y_col}*. "
                f"Les facteurs statistiquement significatifs sont : {pred_txt}."
            )
        return f"{verdict_word}, le modèle global est significatif ({pct_var} % de variance expliquée), sans qu'un prédicteur isolé ne domine individuellement."

    if mode == "chi":
        ct = res.get("contingency_table") or {}
        rate_note = ""
        if ct and len(ct.get("rows", [])) == 2 and len(ct.get("cols", [])) == 2:
            counts = ct["counts"]
            r0, r1 = ct["rows"][0], ct["rows"][1]
            c_target = ct["cols"][1]
            t0, t1 = sum(counts[0]) or 1, sum(counts[1]) or 1
            p0, p1 = counts[0][1] / t0 * 100.0, counts[1][1] / t1 * 100.0
            diff_pts = abs(p1 - p0)
            rate_note = (
                f" La proportion de *{ct.get('col_var', y_col)} = {c_target}* est de **{p1:.1f} %** "
                f"pour *{ct.get('row_var', x_cols[0])} = {r1}* ({counts[1][1]}/{t1}) contre **{p0:.1f} %** "
                f"pour *{r0}* ({counts[0][1]}/{t0}), soit un écart de **{diff_pts:.1f} points de pourcentage**."
            )
        if res["significant"]:
            return (
                f"**Oui**, il existe une association statistiquement significative entre *{y_col}* et *{x_cols[0]}* "
                f"(V de Cramér = {_fmt_bounded(contract['effects'][0]['estimate'])}, *p* {_fmt_p(res['p_value'])}).{rate_note}"
            )
        return (
            f"**Non établi au seuil de {int(plan['alpha']*100)} %** : les {res['n_complete']} observations ne suffisent pas "
            f"à conclure à une association significative entre *{y_col}* et *{x_cols[0]}* (*p* {_fmt_p(res['p_value'])}, "
            f"V de Cramér = {_fmt_bounded(contract['effects'][0]['estimate'])}).{rate_note}"
        )

    if mode == "logit":
        if not res["significant"]:
            return (
                f"**Non établi au seuil de {int(plan['alpha']*100)} %** : le modèle logistique ne prédit pas significativement "
                f"*{y_col} = {res['positive_class']}* (AUC = {_fmt_num(res['auc'], 3)}, *p* {_fmt_p(res['p_value'])})."
            )
        sig_c = [c for c in coefs[1:] if c["p"] is not None and c["p"] < plan["alpha"]]
        or_txt = " ; ".join(
            f"**{c['term']}** (OR = **{c['OR']}** par unité, *p* {_fmt_p(c['p'])})"
            for c in sig_c
        )
        return (
            f"**Oui**, le modèle logistique prédit significativement la probabilité de *{y_col} = {res['positive_class']}* "
            f"(pouvoir discriminant **AUC = {_fmt_num(res['auc'], 3)}**, pseudo-*R*² = {round(res['mcfadden_r2']*100, 1)} %, *p* {_fmt_p(res['p_value'])}). "
            f"Facteurs significatifs : {or_txt or 'effet global uniquement'}."
        )

    if mode == "corr":
        sig_pairs = [ph for ph in posthoc if ph["p_adj"] is not None and ph["p_adj"] < plan["alpha"]]
        if not sig_pairs:
            return f"**Non établi** : aucune corrélation entre les variables sélectionnées n'est significative après correction de Holm."
        top = max(sig_pairs, key=lambda x: abs(x["difference"]))
        return (
            f"**Oui**, {len(sig_pairs)} corrélation(s) significative(s) détectée(s) après ajustement de Holm. "
            f"La plus forte concerne **{top['a']} × {top['b']}** (*r* = {top['difference']}, ρ = {top['spearman_rho']}, *p_adj* {_fmt_p(top['p_adj'])})."
        )

    if mode == "rm_anova":
        if not res["significant"]:
            return f"**Non établi au seuil de {int(plan['alpha']*100)} %** : aucune évolution significative n'est détectée entre les {len(groups)} temps de mesure (*p* {_fmt_p(res['p_value'])})."
        return (
            f"**Oui**, une évolution significative est observée au fil des {len(groups)} mesures répétées "
            f"(η²_p = {_fmt_bounded(contract['effects'][0]['estimate'])}, *p* {_fmt_p(res['p_value'])}, confirmé par Friedman *p* {_fmt_p(res['friedman_p'])}). "
            f"*Réserve : sans groupe témoin, cette évolution temporelle n'établit pas à elle seule un lien causal.*"
        )

    return ""


def _optional_llm_enrichment(
    contract: dict[str, Any],
    base_output: dict[str, Any],
    llm_config: dict[str, Any],
) -> dict[str, Any]:
    """Connecteur REST multi-modèles (OpenAI / Azure / Ollama / Gemini Enterprise ZDR) sur JSON agrégé uniquement."""
    provider = llm_config.get("provider", "openai_compat")
    endpoint = llm_config.get("endpoint", "").strip()
    api_key = llm_config.get("api_key", "").strip()
    model = llm_config.get("model", "").strip()
    if not model:
        return base_output

    system_prompt = (
        "Tu es un comité de 3 experts statistiques (Auditeur méthodologique, Rédacteur APA 7, Consultant métier). "
        "Tu reçois UNIQUEMENT un contrat JSON agrégé certifié (aucune donnée individuelle). "
        "Ne modifie JAMAIS un chiffre du JSON. Rédige en français une synthèse exécutive claire, "
        "les limites méthodologiques (VIF, non-linéarité, outliers, causalité) et des recommandations concrètes. "
        "Un résultat non significatif ne démontre jamais l'absence d'effet. "
        "Aucune généralisation n'est autorisée sans plan de sondage documenté ; "
        "une métrique lexicale ne démontre pas la qualité globale d'une langue. "
        "Les avertissements déterministes des flags du contrat prévalent sur tout verdict rédigé."
    )
    user_content = json.dumps(contract, ensure_ascii=False)

    if provider == "gemini":
        url = endpoint or f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {"temperature": 0.1},
        }
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["candidates"][0]["content"]["parts"][0]["text"]
    else:
        if not endpoint:
            return base_output
        payload = {
            "model": model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]

    return {**base_output, "llm_commentary": content, "provider_mode": f"LLM ({provider} · {model})"}


def run_phase2_interpretation(
    contract: dict[str, Any],
    llm_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Exécute les 3 agents de Phase 2 sur le Contrat JSON certifié (zéro donnée brute)."""
    assert_aggregated_only(contract)

    lang = (contract.get("plan", {}).get("language") or "fr").lower()
    if lang in ("nl", "en"):
        from src.phase2_i18n import render_phase2_nl_en

        output = render_phase2_nl_en(contract, lang)
    else:
        alerts, actions = _agent1_audit(contract)
        apa7 = _agent2_apa7(contract)
        business = _agent3_business(contract)
        output = {
            "provider_mode": "Local Expert Engine (Offline — 0 fuite réseau)",
            "agent1_methodology_audit": alerts,
            "recommended_actions": actions,
            "agent2_apa7_report": apa7,
            "agent3_business_summary": business,
            "llm_commentary": None,
        }

    scientific_alerts, caveat = render_scientific_warnings(contract, lang)
    headings = {
        "fr": ("Limites d'interprétation", "Réserves scientifiques", "Limites méthodologiques vérifiées"),
        "nl": ("Interpretatiebeperkingen", "Wetenschappelijke voorbehouden", "Geverifieerde methodologische beperkingen"),
        "en": ("Interpretation limitations", "Scientific caveats", "Verified methodological limits"),
    }
    apa_heading, summary_heading, llm_heading = headings.get(lang, headings["fr"])
    if scientific_alerts:
        output["agent1_methodology_audit"] = [
            *output.get("agent1_methodology_audit", []), *scientific_alerts
        ]
        output["agent2_apa7_report"] = (
            output.get("agent2_apa7_report", "") + f"\n\n**{apa_heading} :** " + caveat
        )
        output["agent3_business_summary"] = (
            output.get("agent3_business_summary", "") + f"\n\n**{summary_heading} :** " + caveat
        )

    if llm_config and llm_config.get("enabled"):
        try:
            output = _optional_llm_enrichment(contract, output, llm_config)
            if caveat and output.get("llm_commentary"):
                output["llm_commentary"] += f"\n\n**{llm_heading} :** " + caveat
        except Exception as exc:
            output["llm_error"] = f"LLM unavailable ({exc}) — fallback to local expert engine."

    return output
