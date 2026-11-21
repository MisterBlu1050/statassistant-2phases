"""Phase 2 — Idiomatic Dutch (NL) & English (EN) Rendering for All 3 Agents."""

from __future__ import annotations

from typing import Any


def _p(p: float | None) -> str:
    if p is None:
        return "N/A"
    if p < 0.001:
        return "< .001"
    return f"= .{f'{p:.3f}'.split('.')[1]}"


def _num(val: float | None, ndigits: int = 2) -> str:
    return "N/A" if val is None else f"{val:.{ndigits}f}"


def _df(val: float | None) -> str:
    if val is None:
        return "N/A"
    return str(int(round(val))) if abs(val - round(val)) < 1e-6 else f"{val:.2f}"


def _bnd(val: float | None, ndigits: int = 2) -> str:
    if val is None:
        return "N/A"
    s = f"{abs(val):.{ndigits}f}"
    if s.startswith("0."):
        s = s[1:]
    return f"-{s}" if val < 0 else s


def _ci(ci: list[float | None] | None, bounded: bool = False) -> str:
    if not ci or len(ci) != 2 or ci[0] is None or ci[1] is None:
        return "[N/A]"
    fn = _bnd if bounded else _num
    return f"[{fn(ci[0])}, {fn(ci[1])}]"


def _audit_nl_en(contract: dict[str, Any], lang: str) -> tuple[list[str], list[dict[str, Any]]]:
    nl = lang == "nl"
    plan = contract["plan"]
    flags = contract.get("flags", [])
    flag_codes = {f["code"] for f in flags}
    alerts: list[str] = []
    actions: list[dict[str, Any]] = []

    # 0. Question <-> Variables coherence
    q_low = (plan.get("question") or "").lower()
    if q_low:
        generic = {"taux", "score", "indice", "heures", "jours", "nombre", "niveau", "rate", "hours", "days", "uren", "dagen", "aantal"}
        sel = {plan["y"], *plan.get("xs", [])}
        missed = []
        for col in contract.get("metadata", {}).get("all_columns", []):
            if col in sel:
                continue
            toks = [t for t in col.lower().replace("_", " ").split() if len(t) >= 4 and t not in generic]
            if col.lower() in q_low or (toks and any(t in q_low for t in toks)):
                missed.append(col)
        if missed:
            alerts.append(
                (f"⚠️ **Vraag ↔ Variabelen mismatch**: uw vraag lijkt **{', '.join(missed)}** te noemen, maar deze kolom zit niet in het model."
                 if nl else
                 f"⚠️ **Question ↔ Variables mismatch**: your question appears to mention **{', '.join(missed)}**, which is not included in the model.")
            )

    # 1. VIF
    vif_flags = [f for f in flags if f["code"] == "vif_critical"]
    if vif_flags:
        max_v = max(f["vif"] for f in vif_flags)
        v_cols = [f["variable"] for f in vif_flags]
        if max_v > 100:
            alerts.append(
                (f"⛔ **Extreme multicollineariteit (max VIF = {max_v})** tussen {', '.join(v_cols)}: individuele coëfficiënten mogen niet afzonderlijk worden geïnterpreteerd."
                 if nl else
                 f"⛔ **Extreme multicollinearity (max VIF = {max_v})** among {', '.join(v_cols)}: individual slopes must not be interpreted in isolation.")
            )
        else:
            alerts.append(
                (f"⚠️ **Hoge collineariteit (max VIF = {max_v})** op {', '.join(v_cols)}."
                 if nl else
                 f"⚠️ **High collinearity (max VIF = {max_v})** on {', '.join(v_cols)}.")
            )
        if len(plan.get("xs", [])) >= 2:
            drop_v = v_cols[-1]
            rem = [c for c in plan["xs"] if c != drop_v]
            actions.append(
                {
                    "label": (f"Herberekenen zonder « {drop_v} »" if nl else f"Recalculate without « {drop_v} »"),
                    "new_plan": {**plan, "mode": "reg" if len(rem) == 1 else "multi", "xs": rem},
                }
            )

    # 2. Nonlinearity
    for f in flags:
        if f["code"] == "possible_nonlinearity":
            shape = ("omgekeerde U (maximum)" if "inversé" in f.get("shape", "") else "U-vorm (minimum)") if nl else ("inverted-U (maximum)" if "inversé" in f.get("shape", "") else "U-shape (minimum)")
            alerts.append(
                (f"⛔ **Niet-lineaire relatie ({shape}, extremum ≈ {f.get('vertex_x')})**: lineaire R² = {_num(f['r2_linear'], 3)} vs kwadratische R² = {_num(f['r2_quadratic'], 3)}. Een rechte lijn verbergt een duidelijke kromlijnige samenhang."
                 if nl else
                 f"⛔ **Non-linear relationship ({shape}, extremum ≈ {f.get('vertex_x')})**: linear R² = {_num(f['r2_linear'], 3)} vs quadratic R² = {_num(f['r2_quadratic'], 3)}. A straight line masks a pronounced curvilinear association.")
            )
            actions.append(
                {
                    "label": (f"Kwadratisch model uitvoeren op « {f['variable']} »" if nl else f"Run quadratic model on « {f['variable']} »"),
                    "new_plan": {**plan, "mode": "quad", "xs": [f["variable"]]},
                }
            )

    # 3. Normality -> non-parametric fallback
    if "normality_failed" in flag_codes:
        m = plan["mode"]
        if m == "anova":
            alerts.append("⚠️ **Normaliteit geschonden (Shapiro-Wilk p < .05)** : overweeg Kruskal-Wallis als gevoeligheidscontrole." if nl else "⚠️ **Normality assumption departed (Shapiro-Wilk p < .05)**: consider Kruskal-Wallis as a sensitivity check.")
            actions.append({"label": "Overschakelen naar Kruskal-Wallis" if nl else "Switch to Kruskal-Wallis", "new_plan": {**plan, "mode": "kw"}})
        elif m == "ind":
            alerts.append("⚠️ **Normaliteit geschonden in minstens één groep** : Mann-Whitney U aanbevolen ter controle." if nl else "⚠️ **Normality departed in at least one group**: Mann-Whitney U recommended as a sensitivity check.")
            actions.append({"label": "Overschakelen naar Mann-Whitney U" if nl else "Switch to Mann-Whitney U", "new_plan": {**plan, "mode": "mw"}})
        elif m == "pair":
            alerts.append("⚠️ **Verschillen wijken af van normaliteit** : Wilcoxon signed-rank test is robuuster." if nl else "⚠️ **Paired differences depart from normality**: Wilcoxon signed-rank test is more robust.")
            actions.append({"label": "Overschakelen naar Wilcoxon signed-rank" if nl else "Switch to Wilcoxon signed-rank", "new_plan": {**plan, "mode": "signed"}})
        elif m in ("reg", "multi", "quad"):
            alerts.append("⚠️ **Residuen niet normaal verdeeld (Shapiro-Wilk p < .05)**." if nl else "⚠️ **Non-normal residuals (Shapiro-Wilk p < .05)**.")

    if "sparse_contingency" in flag_codes:
        alerts.append("ℹ️ **Lage verwachte celfrequenties** : automatisch overgeschakeld op exacte / Monte Carlo-toets." if nl else "ℹ️ **Low expected cell counts**: automatically switched to exact / Monte Carlo test.")

    alerts.append(
        "ℹ️ **Methodologische grens (Causaliteit)** : observationele gegevens zonder gerandomiseerde controlegroep tonen een associatie, geen oorzakelijk verband."
        if nl else
        "ℹ️ **Methodological limit (Causality)**: observational data without a randomized control group establish an association, not causation."
    )
    return alerts, actions


def _apa7_nl_en(contract: dict[str, Any], lang: str) -> str:
    nl = lang == "nl"
    plan = contract["plan"]
    res = contract["result"]
    groups = contract.get("groups", [])
    effects = contract.get("effects", [])
    posthoc = contract.get("posthoc", [])
    coefs = contract.get("coefficients", [])
    flags = contract.get("flags", [])
    mode, y_col, x_cols, n = plan["mode"], plan["y"], plan.get("xs", []), res["n_complete"]
    p_txt = _p(res.get("p_value"))

    if mode == "desc":
        return (
            f"Beschrijvende analyse van *{y_col}* (*N* = {n}): *M* = {_num(res['mean'])}, *SD* = {_num(res['sd'])}, 95% BI {_ci(res['ci_95'])}, *Mdn* = {_num(res['median'])}."
            if nl else
            f"Descriptive analysis of *{y_col}* (*N* = {n}): *M* = {_num(res['mean'])}, *SD* = {_num(res['sd'])}, 95% CI {_ci(res['ci_95'])}, *Mdn* = {_num(res['median'])}."
        )

    if mode in ("pair", "signed"):
        g0, g1 = groups[0], groups[1]
        eff = effects[1] if len(effects) > 1 else effects[0]
        if mode == "pair":
            return (
                f"Een gepaarde *t*-toets (*N* = {n}) tussen *{g0['label']}* (*M* = {_num(g0['mean'])}, *SD* = {_num(g0['sd'])}) en *{g1['label']}* (*M* = {_num(g1['mean'])}, *SD* = {_num(g1['sd'])}) gaf *t*({_df(res['df'][0])}) = {_num(res['statistic'])}, *p* {p_txt}, Δ*M* = {_num(res['mean_change'])}, *d_z* = {_num(eff['estimate'])} (95% bootstrap BI {_ci(eff['ci_95'])})."
                if nl else
                f"A paired-samples *t*-test (*N* = {n}) comparing *{g0['label']}* (*M* = {_num(g0['mean'])}, *SD* = {_num(g0['sd'])}) and *{g1['label']}* (*M* = {_num(g1['mean'])}, *SD* = {_num(g1['sd'])}) yielded *t*({_df(res['df'][0])}) = {_num(res['statistic'])}, *p* {p_txt}, Δ*M* = {_num(res['mean_change'])}, *d_z* = {_num(eff['estimate'])} (95% bootstrap CI {_ci(eff['ci_95'])})."
            )
        return (
            f"Een Wilcoxon signed-rank toets (*N* = {n}, {res['zero_diff_count']} nulverschillen) gaf *W* = {_num(res['statistic'])}, *p* {p_txt}, *r_rb* = {_bnd(eff['estimate'])} (95% bootstrap BI {_ci(eff['ci_95'], bounded=True)})."
            if nl else
            f"A Wilcoxon signed-rank test (*N* = {n}, {res['zero_diff_count']} zero differences) yielded *W* = {_num(res['statistic'])}, *p* {p_txt}, *r_rb* = {_bnd(eff['estimate'])} (95% bootstrap CI {_ci(eff['ci_95'], bounded=True)})."
        )

    if mode in ("ind", "mw"):
        g0, g1 = groups[0], groups[1]
        eff = effects[1] if mode == "ind" else effects[0]
        stat_s = f"*t*({_df(res['df'][0])}) = {_num(res['statistic'])}, *d* = {_num(eff['estimate'])}" if mode == "ind" else f"*U* = {_num(res['statistic'])}, *r_rb* = {_bnd(eff['estimate'])}"
        return (
            f"*{res['method']}* (*N* = {n}) op *{y_col}* tussen *{g0['label']}* (*M* = {_num(g0['mean'])}, *SD* = {_num(g0['sd'])}) en *{g1['label']}* (*M* = {_num(g1['mean'])}, *SD* = {_num(g1['sd'])}): {stat_s}, *p* {p_txt}."
            if nl else
            f"*{res['method']}* (*N* = {n}) on *{y_col}* comparing *{g0['label']}* (*M* = {_num(g0['mean'])}, *SD* = {_num(g0['sd'])}) and *{g1['label']}* (*M* = {_num(g1['mean'])}, *SD* = {_num(g1['sd'])}): {stat_s}, *p* {p_txt}."
        )

    if mode in ("anova", "kw"):
        eff = effects[0]
        stat_s = (
            f"*F*({_df(res['df'][0])}, {_df(res['df'][1])}) = {_num(res['statistic'])}, *p* {p_txt}, η² = {_bnd(eff['estimate'])} (95% bootstrap {_ci(eff['ci_95'], bounded=True)})"
            if mode == "anova"
            else f"*H*({_df(res['df'][0])}) = {_num(res['statistic'])}, *p* {p_txt}, ε² = {_bnd(eff['estimate'])}"
        )
        base = f"*{res['method']}* (*N* = {n}) voor *{y_col}* naar *{x_cols[0]}*: {stat_s}." if nl else f"*{res['method']}* (*N* = {n}) for *{y_col}* by *{x_cols[0]}*: {stat_s}."
        sig_ph = [f"*{ph['a']}* vs *{ph['b']}* (*p_adj* {_p(ph['p_adj'])})" for ph in posthoc if ph["p_adj"] is not None and ph["p_adj"] < plan["alpha"]]
        if sig_ph:
            base += (f" Post-hoc ({posthoc[0]['method']}): {', '.join(sig_ph)}." if nl else f" Post-hoc ({posthoc[0]['method']}): {', '.join(sig_ph)}.")
        return base

    if mode in ("reg", "multi", "quad"):
        base = (
            f"*{res['method']}* (*N* = {n}) voorspelt *{y_col}* uit {', '.join(f'*{c}*' for c in x_cols)}: *F*({_df(res['df'][0])}, {_df(res['df'][1])}) = {_num(res['statistic'])}, *p* {p_txt}, *R*² = {_bnd(res['r2'], 3)}, gecorrigeerde *R*² = {_bnd(res['r2_adj'], 3)}."
            if nl else
            f"*{res['method']}* (*N* = {n}) predicting *{y_col}* from {', '.join(f'*{c}*' for c in x_cols)}: *F*({_df(res['df'][0])}, {_df(res['df'][1])}) = {_num(res['statistic'])}, *p* {p_txt}, *R*² = {_bnd(res['r2'], 3)}, adjusted *R*² = {_bnd(res['r2_adj'], 3)}."
        )
        nl_flag = next((f for f in flags if f["code"] == "possible_nonlinearity"), None)
        if nl_flag:
            base += (
                f" Exploratieve toevoeging van een kwadratische term verbetert de fit sterk, *F*({nl_flag['df_add'][0]}, {nl_flag['df_add'][1]}) = {_num(nl_flag['f_add'])}, *p* {_p(nl_flag['p_add'])}, *R*² = {_bnd(nl_flag['r2_quadratic'], 3)} (extremum ≈ {nl_flag['vertex_x']})."
                if nl else
                f" Adding an exploratory quadratic term substantially improves fit, *F*({nl_flag['df_add'][0]}, {nl_flag['df_add'][1]}) = {_num(nl_flag['f_add'])}, *p* {_p(nl_flag['p_add'])}, raising *R*² to {_bnd(nl_flag['r2_quadratic'], 3)} (extremum ≈ {nl_flag['vertex_x']})."
            )
        return base

    if mode == "chi":
        eff = effects[0]
        return (
            f"*{res['method']}* (*N* = {n}) tussen *{y_col}* en *{x_cols[0]}*: *p* {p_txt}, Cramérs *V* = {_bnd(eff['estimate'])}."
            if nl else
            f"*{res['method']}* (*N* = {n}) between *{y_col}* and *{x_cols[0]}*: *p* {p_txt}, Cramér's *V* = {_bnd(eff['estimate'])}."
        )

    if mode == "logit":
        return (
            f"Binaire logistische regressie (*N* = {n}, positieve klasse: *{res['positive_class']}*): χ²({_df(res['df'][0])}) = {_num(res['statistic'])}, *p* {p_txt}, McFadden *R*² = {_bnd(res['mcfadden_r2'])}, AUC = {_num(res['auc'], 3)}."
            if nl else
            f"Binary logistic regression (*N* = {n}, positive class: *{res['positive_class']}*): χ²({_df(res['df'][0])}) = {_num(res['statistic'])}, *p* {p_txt}, McFadden's *R*² = {_bnd(res['mcfadden_r2'])}, AUC = {_num(res['auc'], 3)}."
        )

    if mode == "corr":
        sig_n = sum(1 for ph in posthoc if ph["p_adj"] is not None and ph["p_adj"] < plan["alpha"])
        return (
            f"Correlatiematrix (*N* = {n}, Holm-correctie): {sig_n} significante paar(en), max |*r*| = {_bnd(res['statistic'], 3)}."
            if nl else
            f"Correlation matrix (*N* = {n}, Holm-adjusted): {sig_n} significant pair(s), max |*r*| = {_bnd(res['statistic'], 3)}."
        )

    if mode == "rm_anova":
        return (
            f"Herhaalde-metingen ANOVA (Greenhouse-Geisser ε = {_num(res['gg_epsilon'], 3)}, *N* = {n}): *F*({_df(res['df'][0])}, {_df(res['df'][1])}) = {_num(res['statistic'])}, *p* {p_txt}, η²_p = {_bnd(effects[0]['estimate'])} (Friedman *p* {_p(res['friedman_p'])})."
            if nl else
            f"Repeated-measures ANOVA (Greenhouse-Geisser ε = {_num(res['gg_epsilon'], 3)}, *N* = {n}): *F*({_df(res['df'][0])}, {_df(res['df'][1])}) = {_num(res['statistic'])}, *p* {p_txt}, η²_p = {_bnd(effects[0]['estimate'])} (Friedman *p* {_p(res['friedman_p'])})."
        )

    return ""


def _business_nl_en(contract: dict[str, Any], lang: str) -> str:
    nl = lang == "nl"
    plan = contract["plan"]
    res = contract["result"]
    groups = contract.get("groups", [])
    coefs = contract.get("coefficients", [])
    flags = contract.get("flags", [])
    flag_codes = {f["code"] for f in flags}
    mode, y_col, x_cols = plan["mode"], plan["y"], plan.get("xs", [])

    if mode == "desc":
        return (
            f"**Overzicht:** over {res['n_complete']} observaties is het gemiddelde van *{y_col}* **{res['mean']}** (mediaan **{res['median']}**)."
            if nl else
            f"**Summary:** across {res['n_complete']} observations, the mean of *{y_col}* is **{res['mean']}** (median **{res['median']}**)."
        )

    severe_vif = [f for f in flags if f["code"] == "vif_critical" and f["vif"] > 100]
    if severe_vif:
        col_vars = [f["variable"] for f in severe_vif]
        clean = [c for c in coefs[1:] if c["term"] not in set(col_vars)]
        sig_clean = [c for c in clean if c["p"] is not None and c["p"] < plan["alpha"]]
        pct = round(res["r2"] * 100, 1)
        clean_s = ""
        if sig_clean:
            parts = " ; ".join(f"**{c['term']}** ({c['B']:+.3f}, *p* {_p(c['p'])})" for c in sig_clean)
            clean_s = (f" Onafhankelijke significante factor(en): {parts}." if nl else f" Independent significant predictor(s): {parts}.")
        return (
            (f"**Ja, globaal ({pct} % verklaarde variantie), maar met gedeeltelijke redundantie.** **{', '.join(col_vars)}** zijn sterk collineair (VIF > 100).{clean_s}"
             if nl else
             f"**Yes, overall ({pct}% variance explained), with partial redundancy.** **{', '.join(col_vars)}** are nearly collinear (VIF > 100).{clean_s}")
        )

    if "possible_nonlinearity" in flag_codes:
        f = next(x for x in flags if x["code"] == "possible_nonlinearity")
        shape = ("omgekeerde U (maximum)" if "inversé" in f.get("shape", "") else "U-vorm (minimum)") if nl else ("inverted-U (maximum)" if "inversé" in f.get("shape", "") else "U-shape (minimum)")
        return (
            (f"**Sterke niet-lineaire relatie ({shape}, extremum ≈ {f.get('vertex_x')})**: lineaire fit verklaart {round(f['r2_linear']*100, 2)} %, kwadratische fit **{round(f['r2_quadratic']*100, 2)} %** (*p* {_p(f['p_add'])})."
             if nl else
             f"**Strong non-linear relationship ({shape}, extremum ≈ {f.get('vertex_x')})**: linear fit explains {round(f['r2_linear']*100, 2)}%, whereas quadratic fit explains **{round(f['r2_quadratic']*100, 2)}%** (*p* {_p(f['p_add'])}).")
        )

    if mode in ("pair", "signed"):
        g0, g1 = groups[0], groups[1]
        if res["significant"]:
            return (
                (f"**Ja, een verandering is waargenomen** van *{g0['label']}* ({g0['mean']}) naar *{g1['label']}* ({g1['mean']}), gemiddelde verandering **{res['mean_change']:+.2f}** (mediaan **{res['median_change']:+.2f}**; {res['n_decreased']} dalingen, {res['n_unchanged']} gelijk, {res['n_increased']} stijgingen). *Let op: zonder controlegroep bewijst dit geen causaliteit.*"
                 if nl else
                 f"**Yes, a change is observed** from *{g0['label']}* ({g0['mean']}) to *{g1['label']}* ({g1['mean']}), mean change **{res['mean_change']:+.2f}** (median **{res['median_change']:+.2f}**; {res['n_decreased']} decreases, {res['n_unchanged']} unchanged, {res['n_increased']} increases). *Note: without a control group, this does not establish causality.*")
            )
        return (f"**Niet aangetoond op 5 %-niveau** (*p* {_p(res['p_value'])})." if nl else f"**Not established at the 5% threshold** (*p* {_p(res['p_value'])}).")

    if mode == "chi":
        ct = res.get("contingency_table") or {}
        rate_s = ""
        if ct and len(ct.get("rows", [])) == 2 and len(ct.get("cols", [])) == 2:
            cnt = ct["counts"]
            t0, t1 = sum(cnt[0]) or 1, sum(cnt[1]) or 1
            p0, p1 = cnt[0][1] / t0 * 100.0, cnt[1][1] / t1 * 100.0
            rate_s = (
                f" Aandeel *{ct['col_var']} = {ct['cols'][1]}*: **{p1:.1f} %** bij *{ct['rows'][1]}* ({cnt[1][1]}/{t1}) vs **{p0:.1f} %** bij *{ct['rows'][0]}* ({cnt[0][1]}/{t0}), verschil **{abs(p1-p0):.1f} procentpunt**."
                if nl else
                f" Rate of *{ct['col_var']} = {ct['cols'][1]}*: **{p1:.1f}%** for *{ct['rows'][1]}* ({cnt[1][1]}/{t1}) vs **{p0:.1f}%** for *{ct['rows'][0]}* ({cnt[0][1]}/{t0}), a difference of **{abs(p1-p0):.1f} percentage points**."
            )
        if res["significant"]:
            return (f"**Ja**, significante associatie tussen *{y_col}* en *{x_cols[0]}* (*p* {_p(res['p_value'])}).{rate_s}" if nl else f"**Yes**, significant association between *{y_col}* and *{x_cols[0]}* (*p* {_p(res['p_value'])}).{rate_s}")
        return (f"**Niet aangetoond op 5 %-niveau** (*p* {_p(res['p_value'])}).{rate_s}" if nl else f"**Not established at the 5% level** (*p* {_p(res['p_value'])}).{rate_s}")

    yes_no = ("**Ja**" if res.get("significant") else "**Niet aangetoond op 5 %-niveau**") if nl else ("**Yes**" if res.get("significant") else "**Not established at the 5% level**")
    return f"{yes_no} (*{res['method']}*, *p* {_p(res.get('p_value'))})."


def render_phase2_nl_en(contract: dict[str, Any], lang: str) -> dict[str, Any]:
    alerts, actions = _audit_nl_en(contract, lang)
    apa7 = _apa7_nl_en(contract, lang)
    business = _business_nl_en(contract, lang)
    return {
        "provider_mode": "Lokale Expert-Engine (Offline — 0 datalek)" if lang == "nl" else "Local Expert Engine (Offline — 0 network egress)",
        "agent1_methodology_audit": alerts,
        "recommended_actions": actions,
        "agent2_apa7_report": apa7,
        "agent3_business_summary": business,
        "llm_commentary": None,
    }
