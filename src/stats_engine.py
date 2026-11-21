"""Phase 1 — Moteur Statistique Déterministe (0 % IA).

Exécute les calculs statistiques via NumPy et SciPy avec graine aléatoire fixe,
produit un Contrat JSON certifié (double SHA-256, zéro donnée individuelle dans
le contrat envoyé en Phase 2) et génère un script Python compagnon lisible.
"""

from __future__ import annotations

import hashlib
import io
import itertools
import json
import platform
import warnings
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import scipy
from scipy import linalg, stats

SEED = 74101
BOOTSTRAP_REPS = 999
DEFAULT_MISSING_CODES = ["", "NA", "N/A", "NULL", "NaN", "nan", "None"]


def _finite(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _round_opt(val: Any, ndigits: int = 4) -> float | None:
    f = _finite(val)
    return round(f, ndigits) if f is not None else None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def detect_delimiter(text: str) -> str:
    first_lines = [ln for ln in text.splitlines() if ln.strip()][:5]
    if not first_lines:
        return ","
    sample = "\n".join(first_lines)
    counts = {sep: sample.count(sep) for sep in ["\t", ";", ","]}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def detect_decimal(text: str, sep: str) -> str:
    """Détecte automatiquement la décimale ',' sur les fichiers européens (séparateur ';' ou tab)."""
    if sep == ",":
        return "."
    import re
    sample = "\n".join(text.splitlines()[1:20])
    comma_nums = len(re.findall(r"(?:^|[;\t])-?\d+,\d+(?:[;\t]|$)", sample, flags=re.MULTILINE))
    dot_nums = len(re.findall(r"(?:^|[;\t])-?\d+\.\d+(?:[;\t]|$)", sample, flags=re.MULTILINE))
    return "," if comma_nums > dot_nums else "."


def parse_dataset(
    raw_bytes: bytes,
    filename: str = "pasted_data.csv",
    sep: str | None = None,
    decimal: str = "auto",
    has_header: bool = True,
    custom_missing: list[str] | None = None,
    sheet_name: str | int = 0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Parse un fichier CSV/TSV/XLSX ou texte collé avec options explicites."""
    missing_values = list(DEFAULT_MISSING_CODES)
    if custom_missing:
        missing_values.extend([m.strip() for m in custom_missing if m.strip()])

    raw_hash = sha256_bytes(raw_bytes)
    lower = filename.lower()
    effective_decimal = "." if decimal == "auto" else decimal

    if lower.endswith(".xlsx"):
        df = pd.read_excel(
            io.BytesIO(raw_bytes),
            sheet_name=sheet_name,
            header=0 if has_header else None,
            na_values=missing_values,
            keep_default_na=False,
        )
        detected_sep = "xlsx"
    else:
        text = raw_bytes.decode("utf-8-sig", errors="replace").strip()
        # Support format inline "Scores: 12 15 18"
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if lines and all(":" in ln and not ln.endswith("?") for ln in lines) and "," not in lines[0] and ";" not in lines[0]:
            series_dict = {}
            for ln in lines:
                k, v = ln.split(":", 1)
                vals = [x for x in v.replace(";", " ").replace(",", " ").split() if x]
                series_dict[k.strip()] = vals
            df = pd.DataFrame(series_dict)
            detected_sep = "inline"
        else:
            detected_sep = sep if sep else detect_delimiter(text)
            if decimal == "auto":
                effective_decimal = detect_decimal(text, detected_sep)
            df = pd.read_csv(
                io.StringIO(text),
                sep=detected_sep,
                decimal=effective_decimal,
                header=0 if has_header else None,
                na_values=missing_values,
                keep_default_na=False,
            )

    if not has_header:
        df.columns = [f"V{i + 1}" for i in range(len(df.columns))]
    else:
        df.columns = [str(c).strip() for c in df.columns]

    # Conversion numérique explicite quand applicable (en respectant les codes manquants personnalisés)
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            cleaned = df[col].replace(missing_values, np.nan)
            if effective_decimal == ",":
                cleaned = cleaned.apply(lambda x: x.replace(",", ".") if isinstance(x, str) else x)
            numeric_try = pd.to_numeric(cleaned, errors="coerce")
            non_null_orig = cleaned.notna().sum()
            non_null_num = numeric_try.notna().sum()
            if non_null_orig > 0 and non_null_num == non_null_orig:
                df[col] = numeric_try
            else:
                df[col] = cleaned
        else:
            # Gérer les codes manquants numériques (ex: -999)
            num_missing = []
            for m in missing_values:
                try:
                    num_missing.append(float(m))
                except ValueError:
                    pass
            if num_missing:
                df[col] = df[col].replace(num_missing, np.nan)

    meta = {
        "filename": filename,
        "sha256_raw_file": raw_hash,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "delimiter": detected_sep,
        "decimal": effective_decimal,
        "has_header": has_header,
        "custom_missing": custom_missing or [],
    }
    return df, meta


def infer_column_types(df: pd.DataFrame) -> dict[str, str]:
    """Infère un typage explicite ('continuous' | 'categorical') modifiable par l'utilisateur."""
    types: dict[str, str] = {}
    for col in df.columns:
        s = df[col].dropna()
        if s.empty:
            types[col] = "ignored"
        elif pd.api.types.is_numeric_dtype(s):
            n_unique = s.nunique()
            is_all_int = np.all(np.isclose(s.to_numpy(dtype=float) % 1, 0))
            # Un entier avec <= 4 modalités (ex: Type_Contrat 1/2) est proposé comme catégoriel
            if is_all_int and 2 <= n_unique <= 4:
                types[col] = "categorical"
            else:
                types[col] = "continuous"
        else:
            types[col] = "categorical"
    return types


def _bootstrap_ci(groups: list[np.ndarray], stat_fn, paired: bool = False) -> list[float | None]:
    rng = np.random.default_rng(SEED)
    vals: list[float] = []
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        for _ in range(BOOTSTRAP_REPS):
            if paired:
                idx = rng.integers(len(groups[0]), size=len(groups[0]))
                draw = [g[idx] for g in groups]
            else:
                draw = [g[rng.integers(len(g), size=len(g))] for g in groups]
            v = _finite(stat_fn(*draw))
            if v is not None:
                vals.append(v)
    if len(vals) < 0.95 * BOOTSTRAP_REPS:
        return [None, None]
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return [_round_opt(lo), _round_opt(hi)]


def _shapiro_diag(values: np.ndarray, label: str) -> dict[str, Any]:
    n = len(values)
    if n < 3 or n > 5000 or np.ptp(values) == 0:
        return {"name": "Shapiro-Wilk", "label": label, "n": n, "statistic": None, "p": None}
    w, p = stats.shapiro(values)
    return {"name": "Shapiro-Wilk", "label": label, "n": n, "statistic": _round_opt(w), "p": _round_opt(p)}


def _detect_outliers(values: np.ndarray) -> dict[str, Any]:
    q1, q3 = np.quantile(values, [0.25, 0.75])
    iqr = q3 - q1
    iqr_outliers = int(np.sum((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr))) if iqr > 0 else 0
    sd = np.std(values, ddof=1) if len(values) > 1 else 0.0
    z_outliers = int(np.sum(np.abs((values - np.mean(values)) / sd) > 3.0)) if sd > 0 else 0
    return {
        "iqr_count": iqr_outliers,
        "zscore3_count": z_outliers,
        "q1": _round_opt(q1),
        "median": _round_opt(np.median(values)),
        "q3": _round_opt(q3),
        "min": _round_opt(np.min(values)),
        "max": _round_opt(np.max(values)),
    }


def _welch_anova(gs: list[np.ndarray]) -> tuple[float, float, list[float]]:
    k = len(gs)
    ns = np.array([len(g) for g in gs], dtype=float)
    means = np.array([np.mean(g) for g in gs], dtype=float)
    variances = np.array([np.var(g, ddof=1) for g in gs], dtype=float)
    if np.min(variances) <= 0:
        raise ValueError("Variance nulle dans au moins un groupe ; ANOVA de Welch impossible.")
    w = ns / variances
    w_sum = np.sum(w)
    m_w = np.sum(w * means) / w_sum
    cor = np.sum(((1.0 - w / w_sum) ** 2) / (ns - 1.0)) / (k**2 - 1.0)
    f_stat = (np.sum(w * (means - m_w) ** 2) / (k - 1.0)) / (1.0 + 2.0 * (k - 2.0) * cor)
    df2 = 1.0 / (3.0 * cor)
    p_val = float(stats.f.sf(f_stat, k - 1, df2))
    return float(f_stat), p_val, [float(k - 1), float(df2)]


def _parametric_posthoc(gs: list[np.ndarray], labels: list[str], unequal: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    k = len(gs)
    if not unequal:
        res = stats.tukey_hsd(*gs)
        ci = res.confidence_interval()
        for i in range(k):
            for j in range(i + 1, k):
                rows.append(
                    {
                        "method": "Tukey HSD",
                        "a": labels[i],
                        "b": labels[j],
                        "difference": _round_opt(res.statistic[i, j]),
                        "p_adj": _round_opt(res.pvalue[i, j]),
                        "ci_95": [_round_opt(ci.low[i, j]), _round_opt(ci.high[i, j])],
                    }
                )
        return rows

    # Games-Howell (variances inégales)
    for i in range(k):
        for j in range(i + 1, k):
            a, b = gs[i], gs[j]
            va = np.var(a, ddof=1) / len(a)
            vb = np.var(b, ddof=1) / len(b)
            se = np.sqrt(va + vb)
            df = (va + vb) ** 2 / ((va**2) / (len(a) - 1) + (vb**2) / (len(b) - 1))
            diff = float(np.mean(a) - np.mean(b))
            q = np.sqrt(2.0) * abs(diff) / se
            p = float(stats.studentized_range.sf(q, k, df))
            crit = float(stats.studentized_range.ppf(0.95, k, df)) / np.sqrt(2.0)
            rows.append(
                {
                    "method": "Games-Howell",
                    "a": labels[i],
                    "b": labels[j],
                    "difference": _round_opt(diff),
                    "p_adj": _round_opt(p),
                    "ci_95": [_round_opt(diff - crit * se), _round_opt(diff + crit * se)],
                }
            )
    return rows


def _dunn_posthoc(gs: list[np.ndarray], labels: list[str]) -> list[dict[str, Any]]:
    z = np.concatenate(gs)
    ranks = stats.rankdata(z)
    counts = np.unique(z, return_counts=True)[1]
    n = len(z)
    tie_corr = 1.0 - np.sum(counts**3 - counts) / (n**3 - n)
    means = []
    start = 0
    for g in gs:
        means.append(float(np.mean(ranks[start : start + len(g)])))
        start += len(g)

    pairs = []
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            se = np.sqrt(n * (n + 1) / 12.0 * tie_corr * (1.0 / len(gs[i]) + 1.0 / len(gs[j])))
            z_stat = (means[i] - means[j]) / se
            p_raw = float(2.0 * stats.norm.sf(abs(z_stat)))
            pairs.append(
                {
                    "method": "Dunn-Holm",
                    "a": labels[i],
                    "b": labels[j],
                    "difference": _round_opt(means[i] - means[j]),
                    "p_raw": _round_opt(p_raw),
                    "p_adj": None,
                }
            )
    # Ajustement Holm
    order = sorted(range(len(pairs)), key=lambda idx: pairs[idx]["p_raw"])
    running_max = 0.0
    m = len(pairs)
    for rank, idx in enumerate(order):
        adj = min(1.0, max(running_max, (m - rank) * pairs[idx]["p_raw"]))
        running_max = adj
        pairs[idx]["p_adj"] = _round_opt(adj)
    return pairs


def _fit_ols(y: np.ndarray, p_mat: np.ndarray, alpha: float) -> dict[str, Any]:
    n = len(y)
    p = p_mat.shape[1] + 1
    if n <= p:
        raise ValueError("Trop peu d'observations par rapport au nombre de prédicteurs.")
    x_mat = np.column_stack((np.ones(n), p_mat))
    if np.linalg.matrix_rank(x_mat) < p or np.linalg.cond(x_mat) > 1e10:
        raise ValueError("Matrice de prédicteurs singulière ou colinéarité parfaite.")

    q_mat, r_mat = np.linalg.qr(x_mat, mode="reduced")
    beta_hat = linalg.solve_triangular(r_mat, q_mat.T @ y)
    fitted = x_mat @ beta_hat
    resid = y - fitted
    df_res = n - p
    ss_res = float(resid @ resid)
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot <= 0 or ss_res <= np.finfo(float).eps * ss_tot:
        raise ValueError("Variance nulle ou ajustement dégénéré.")

    h = np.sum(q_mat * q_mat, axis=1)
    inv_rq = linalg.solve_triangular(r_mat, q_mat.T)

    # Breusch-Pagan (version Koenker)
    e2 = resid**2
    explained_e2 = q_mat @ (q_mat.T @ e2)
    den = float(np.sum((e2 - np.mean(e2)) ** 2))
    lm = max(0.0, n * (1.0 - float(np.sum((e2 - explained_e2) ** 2)) / den)) if den > 0 else 0.0
    bp_p = float(stats.chi2.sf(lm, p - 1))
    robust = bp_p < alpha

    if robust and np.any(1.0 - h < 1e-9):
        raise ValueError("Point de levier extrême empêchant le calcul HC3.")
    cov = (inv_rq * (resid / (1.0 - h)) ** 2) @ inv_rq.T if robust else (ss_res / df_res) * (inv_rq @ inv_rq.T)
    se = np.sqrt(np.diag(cov))

    r2 = 1.0 - ss_res / ss_tot
    df_mod = p - 1
    if robust:
        # Test conjoint de Wald utilisant la matrice de covariance HC3 (cohérent avec les SE HC3)
        b_slopes = beta_hat[1:]
        cov_slopes = cov[1:, 1:]
        f_mod = float((b_slopes @ linalg.solve(cov_slopes, b_slopes)) / df_mod)
    else:
        f_mod = ((ss_tot - ss_res) / df_mod) / (ss_res / df_res)
    p_mod = float(stats.f.sf(f_mod, df_mod, df_res))
    r2_adj = 1.0 - (1.0 - r2) * (n - 1) / df_res

    std_beta = np.r_[np.nan, beta_hat[1:] * np.std(p_mat, axis=0, ddof=1) / np.std(y, ddof=1)]
    if p_mat.shape[1] == 1:
        vif = np.array([np.nan, 1.0])
    else:
        corr_p = np.corrcoef(p_mat, rowvar=False)
        vif = np.r_[np.nan, np.diag(np.linalg.inv(corr_p))]

    # Distance de Cook maximale
    mse = ss_res / df_res
    cooks_d = (resid**2 / (p * mse)) * (h / ((1.0 - h) ** 2))

    return {
        "b": beta_hat,
        "se": se,
        "df_res": df_res,
        "df_mod": df_mod,
        "fitted": fitted,
        "resid": resid,
        "r2": r2,
        "r2_adj": r2_adj,
        "f_mod": f_mod,
        "p_mod": p_mod,
        "std_beta": std_beta,
        "vif": vif,
        "bp_stat": lm,
        "bp_p": bp_p,
        "robust_hc3": robust,
        "max_cooks_d": float(np.max(cooks_d)),
    }


def _fit_logistic(y_bin: np.ndarray, p_mat: np.ndarray) -> dict[str, Any]:
    """Estimation exacte par Maximum de Vraisemblance (IRLS / Newton-Raphson)."""
    n = len(y_bin)
    p = p_mat.shape[1] + 1
    if n <= p + 2:
        raise ValueError("Trop peu d'observations pour une régression logistique.")
    if len(np.unique(y_bin)) != 2:
        raise ValueError("La variable cible doit comporter exactement 2 modalités.")

    x_mat = np.column_stack((np.ones(n), p_mat))
    # Standardisation interne des prédicteurs pour stabilité numérique du Newton-Raphson
    means = np.mean(p_mat, axis=0)
    stds = np.std(p_mat, axis=0, ddof=0)
    stds = np.where(stds == 0, 1.0, stds)
    xs = np.column_stack((np.ones(n), (p_mat - means) / stds))

    beta_s = np.zeros(p, dtype=float)
    converged = False
    for _ in range(50):
        eta = np.clip(xs @ beta_s, -30.0, 30.0)
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(mu * (1.0 - mu), 1e-9, None)
        hess = (xs.T * w) @ xs
        grad = xs.T @ (y_bin - mu)
        try:
            step = linalg.solve(hess + np.eye(p) * 1e-10, grad)
        except linalg.LinAlgError:
            break
        beta_s += step
        if np.max(np.abs(step)) < 1e-8:
            converged = True
            break

    # Retour à l'échelle d'origine
    b = np.zeros(p, dtype=float)
    b[1:] = beta_s[1:] / stds
    b[0] = beta_s[0] - float(np.sum((beta_s[1:] / stds) * means))

    eta = np.clip(x_mat @ b, -30.0, 30.0)
    probs = 1.0 / (1.0 + np.exp(-eta))
    w_orig = np.clip(probs * (1.0 - probs), 1e-9, None)
    info_mat = (x_mat.T * w_orig) @ x_mat
    cov = linalg.pinv(info_mat)
    se = np.sqrt(np.maximum(np.diag(cov), 1e-18))

    # Log-vraisemblance, LRT et Pseudo-R² de McFadden
    eps = 1e-15
    ll_mod = float(np.sum(y_bin * np.log(np.clip(probs, eps, 1 - eps)) + (1 - y_bin) * np.log(np.clip(1 - probs, eps, 1 - eps))))
    p0 = float(np.mean(y_bin))
    ll_null = float(n * (p0 * np.log(np.clip(p0, eps, 1 - eps)) + (1 - p0) * np.log(np.clip(1 - p0, eps, 1 - eps))))
    lrt_chi2 = max(0.0, 2.0 * (ll_mod - ll_null))
    df_mod = p - 1
    lrt_p = float(stats.chi2.sf(lrt_chi2, df_mod))
    mcfadden_r2 = 1.0 - (ll_mod / ll_null) if ll_null != 0 else 0.0

    # AUC-ROC exact via rangs de Mann-Whitney
    pos_mask = y_bin == 1
    n_pos = int(np.sum(pos_mask))
    n_neg = n - n_pos
    ranks = stats.rankdata(probs)
    auc = float((np.sum(ranks[pos_mask]) - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))

    if p_mat.shape[1] == 1:
        vif = np.array([np.nan, 1.0])
    else:
        corr_p = np.corrcoef(p_mat, rowvar=False)
        vif = np.r_[np.nan, np.diag(np.linalg.inv(corr_p))]

    return {
        "b": b,
        "se": se,
        "probs": probs,
        "lrt_chi2": lrt_chi2,
        "df_mod": df_mod,
        "lrt_p": lrt_p,
        "mcfadden_r2": mcfadden_r2,
        "auc": auc,
        "vif": vif,
        "converged": converged,
    }


def run_analysis(
    df: pd.DataFrame,
    plan: dict[str, Any],
    dataset_meta: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Exécute la Phase 1 déterministe et retourne (contrat_json_sans_donnees_brutes, plot_data)."""
    mode = plan["mode"]
    y_col = plan["y"]
    x_cols = list(plan.get("xs", []))
    alpha = float(plan.get("alpha", 0.05))
    alternative = plan.get("alternative", "two-sided")  # two-sided | greater | less
    question = str(plan.get("question", "")).strip()
    language = plan.get("language", "fr")

    used_cols = [y_col] + [c for c in x_cols if c != y_col]
    sub = df[used_cols].dropna().copy()
    n_complete = int(len(sub))
    n_total = int(len(df))
    if n_complete == 0:
        raise ValueError("Aucune observation complète pour les variables sélectionnées.")

    missing_summary = {
        c: {"observed": int(df[c].notna().sum()), "missing": int(df[c].isna().sum())}
        for c in used_cols
    }

    flags: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    effects: list[dict[str, Any]] = []
    groups_summary: list[dict[str, Any]] = []
    posthoc: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []
    plot_data: dict[str, Any] = {"mode": mode, "y_col": y_col, "x_cols": x_cols}

    result_block: dict[str, Any] = {
        "method": mode,
        "n_complete": n_complete,
        "n_total": n_total,
        "alpha": alpha,
        "alternative": alternative,
        "h0": "",
        "h1": "",
        "statistic_name": "",
        "statistic": None,
        "df": None,
        "p_value": None,
        "significant": None,
    }

    if n_complete < n_total:
        flags.append(
            {
                "code": "missing_values",
                "severity": "info",
                "detail": f"{n_total - n_complete} observation(s) incomplète(s) exclue(s) sans imputation ({n_complete}/{n_total}).",
            }
        )

    # ---------------- 1. DESCRIPTIF ----------------
    if mode == "desc":
        y = sub[y_col].to_numpy(dtype=float)
        m = float(np.mean(y))
        sd = float(np.std(y, ddof=1)) if n_complete > 1 else 0.0
        out_info = _detect_outliers(y)
        ci = stats.t.interval(1.0 - alpha, n_complete - 1, loc=m, scale=stats.sem(y)) if n_complete > 1 and sd > 0 else (m, m)
        sw = _shapiro_diag(y, y_col)
        diagnostics.append(sw)
        if sw["p"] is not None and sw["p"] < alpha:
            flags.append({"code": "normality_failed", "severity": "warning", "detail": f"Shapiro-Wilk p = {sw['p']}"})
        if out_info["iqr_count"] > 0 or out_info["zscore3_count"] > 0:
            flags.append({"code": "outliers_detected", "severity": "warning", "detail": f"{out_info['iqr_count']} outlier(s) IQR"})
        result_block.update(
            {
                "method": "Descriptive statistics",
                "h0": "Aucune (analyse descriptive)",
                "h1": "Aucune",
                "mean": _round_opt(m),
                "sd": _round_opt(sd),
                "ci_95": [_round_opt(ci[0]), _round_opt(ci[1])],
                **out_info,
            }
        )
        plot_data["y"] = y.tolist()

    # ---------------- 2. APPARIÉS (PAIR / SIGNED) ----------------
    elif mode in ("pair", "signed"):
        x_col = x_cols[0]
        y_after = sub[y_col].to_numpy(dtype=float)
        x_before = sub[x_col].to_numpy(dtype=float)
        diff = y_after - x_before
        if n_complete < 3 or np.ptp(diff) == 0:
            raise ValueError("Il faut au moins 3 paires non constantes.")

        sw = _shapiro_diag(diff, f"{y_col} - {x_col}")
        diagnostics.append(sw)
        if sw["p"] is not None and sw["p"] < alpha:
            flags.append(
                {
                    "code": "normality_failed",
                    "severity": "warning",
                    "detail": f"Les différences ({y_col} - {x_col}) dévient de la normalité (Shapiro-Wilk p = {sw['p']}).",
                }
            )
        out_info = _detect_outliers(diff)
        if out_info["iqr_count"] > 0:
            flags.append({"code": "outliers_detected", "severity": "warning", "detail": f"{out_info['iqr_count']} écart(s) extrême(s) IQR."})

        groups_summary = [
            {
                "label": x_col,
                "n": n_complete,
                "mean": _round_opt(np.mean(x_before)),
                "median": _round_opt(np.median(x_before)),
                "sd": _round_opt(np.std(x_before, ddof=1)),
            },
            {
                "label": y_col,
                "n": n_complete,
                "mean": _round_opt(np.mean(y_after)),
                "median": _round_opt(np.median(y_after)),
                "sd": _round_opt(np.std(y_after, ddof=1)),
            },
        ]
        baseline_mean = float(np.mean(x_before))
        pct_change = (float(np.mean(diff)) / baseline_mean * 100.0) if baseline_mean != 0 else None

        sym = {"two-sided": "≠", "greater": ">", "less": "<"}[alternative]
        result_block["h0"] = "La différence moyenne/médiane entre les deux mesures est nulle (μΔ = 0)."
        result_block["h1"] = f"La différence entre {y_col} et {x_col} est non nulle (μΔ {sym} 0)."
        result_block["mean_change"] = _round_opt(np.mean(diff))
        result_block["median_change"] = _round_opt(np.median(diff))
        result_block["pct_change_vs_baseline"] = _round_opt(pct_change, 2)
        result_block["zero_diff_count"] = int(np.sum(diff == 0))
        result_block["n_decreased"] = int(np.sum(diff < 0))
        result_block["n_unchanged"] = int(np.sum(diff == 0))
        result_block["n_increased"] = int(np.sum(diff > 0))

        if mode == "pair":
            res = stats.ttest_1samp(diff, 0.0, alternative=alternative)
            ci_t = stats.ttest_1samp(diff, 0.0).confidence_interval(confidence_level=1.0 - alpha)
            dz = float(np.mean(diff) / np.std(diff, ddof=1))
            dz_ci = _bootstrap_ci([diff], lambda d: np.mean(d) / np.std(d, ddof=1))
            result_block.update(
                {
                    "method": "Paired-samples t-test",
                    "statistic_name": "t",
                    "statistic": _round_opt(res.statistic),
                    "df": [float(n_complete - 1)],
                    "p_value": _round_opt(res.pvalue),
                    "significant": bool(res.pvalue < alpha),
                }
            )
            effects = [
                {"name": "ΔM", "estimate": _round_opt(np.mean(diff)), "ci_95": [_round_opt(ci_t.low), _round_opt(ci_t.high)], "method": "Student t"},
                {"name": "d_z", "estimate": _round_opt(dz), "ci_95": dz_ci, "method": f"Bootstrap ({BOOTSTRAP_REPS})"},
            ]
        else:
            nz = diff[diff != 0]
            res = stats.wilcoxon(diff, alternative=alternative)
            ranks = stats.rankdata(np.abs(nz))
            r_rb = float(np.sum(ranks * np.sign(nz)) / np.sum(ranks)) if len(nz) > 0 else 0.0

            def _rb(d):
                v = d[d != 0]
                if len(v) == 0:
                    return np.nan
                rk = stats.rankdata(np.abs(v))
                return np.sum(rk * np.sign(v)) / np.sum(rk)

            r_ci = _bootstrap_ci([diff], _rb)
            result_block.update(
                {
                    "method": "Wilcoxon signed-rank test",
                    "statistic_name": "W",
                    "statistic": _round_opt(res.statistic),
                    "df": None,
                    "p_value": _round_opt(res.pvalue),
                    "significant": bool(res.pvalue < alpha),
                }
            )
            effects = [{"name": "r_rb", "estimate": _round_opt(r_rb), "ci_95": r_ci, "method": f"Bootstrap ({BOOTSTRAP_REPS})"}]

        plot_data["diff"] = diff.tolist()
        plot_data["before"] = x_before.tolist()
        plot_data["after"] = y_after.tolist()

    # ---------------- 3. GROUPES INDÉPENDANTS (IND / MW / ANOVA / KW) ----------------
    elif mode in ("ind", "mw", "anova", "kw"):
        g_col = x_cols[0]
        labels = list(dict.fromkeys(sub[g_col].astype(str).tolist()))
        if mode in ("ind", "mw") and len(labels) != 2:
            raise ValueError(f"Le test {mode} exige exactement 2 groupes (trouvé : {len(labels)}).")
        if mode in ("anova", "kw") and len(labels) < 2:
            raise ValueError("Il faut au moins 2 groupes.")

        gs = [sub.loc[sub[g_col].astype(str) == lb, y_col].to_numpy(dtype=float) for lb in labels]
        if min(len(g) for g in gs) < 2:
            raise ValueError("Chaque groupe doit contenir au moins 2 observations complètes.")

        norm_failed = False
        total_outliers = 0
        for lb, g in zip(labels, gs):
            sw = _shapiro_diag(g, lb)
            diagnostics.append(sw)
            if sw["p"] is not None and sw["p"] < alpha:
                norm_failed = True
            oi = _detect_outliers(g)
            total_outliers += oi["iqr_count"]
            groups_summary.append(
                {
                    "label": lb,
                    "n": len(g),
                    "mean": _round_opt(np.mean(g)),
                    "median": _round_opt(np.median(g)),
                    "sd": _round_opt(np.std(g, ddof=1)),
                    "q1": oi["q1"],
                    "q3": oi["q3"],
                    "iqr_outliers": oi["iqr_count"],
                }
            )

        lev_stat, lev_p = stats.levene(*gs, center="median")
        diagnostics.append({"name": "Levene (median)", "label": "Global", "n": n_complete, "statistic": _round_opt(lev_stat), "p": _round_opt(lev_p)})
        unequal = (not np.isfinite(lev_p)) or (lev_p < alpha) or any(np.var(g, ddof=1) == 0 for g in gs)

        if norm_failed:
            flags.append({"code": "normality_failed", "severity": "warning", "detail": "Au moins un groupe dévie de la normalité (Shapiro-Wilk p < .05)."})
        if unequal:
            flags.append({"code": "heteroscedasticity", "severity": "warning", "detail": f"Variances inégales (Levene p = {_round_opt(lev_p)})."})
        if total_outliers > 0:
            flags.append({"code": "outliers_detected", "severity": "warning", "detail": f"{total_outliers} valeur(s) aberrante(s) détectée(s) dans les groupes."})

        # Ratio max/min de variance pour repérer les petits échantillons à variance explosée malgré Levene
        vars_g = [float(np.var(g, ddof=1)) for g in gs if np.var(g, ddof=1) > 0]
        if len(vars_g) >= 2 and (max(vars_g) / min(vars_g)) > 10.0 and not unequal:
            flags.append(
                {
                    "code": "extreme_variance_ratio",
                    "severity": "warning",
                    "detail": f"Rapport de variances très élevé ({round(max(vars_g)/min(vars_g), 1)}x) malgré Levene non significatif (manque de puissance sur petit effectif).",
                }
            )

        if mode == "ind":
            a, b = gs
            res = stats.ttest_ind(a, b, equal_var=not unequal, alternative=alternative)
            ci = stats.ttest_ind(a, b, equal_var=not unequal).confidence_interval(confidence_level=1.0 - alpha)

            def _cohend(x1, x2):
                pooled = np.sqrt(((len(x1) - 1) * np.var(x1, ddof=1) + (len(x2) - 1) * np.var(x2, ddof=1)) / (len(x1) + len(x2) - 2))
                return (np.mean(x1) - np.mean(x2)) / pooled if pooled > 0 else np.nan

            d_val = float(_cohend(a, b))
            d_ci = _bootstrap_ci(gs, _cohend)
            result_block.update(
                {
                    "method": "Welch's t-test" if unequal else "Independent-samples t-test (Student)",
                    "h0": f"Les moyennes de {y_col} sont égales entre {labels[0]} et {labels[1]}.",
                    "h1": f"Les moyennes de {y_col} diffèrent entre {labels[0]} et {labels[1]}.",
                    "statistic_name": "t",
                    "statistic": _round_opt(res.statistic),
                    "df": [_round_opt(res.df, 2)],
                    "p_value": _round_opt(res.pvalue),
                    "significant": bool(res.pvalue < alpha),
                }
            )
            effects = [
                {"name": "ΔM", "estimate": _round_opt(np.mean(a) - np.mean(b)), "ci_95": [_round_opt(ci.low), _round_opt(ci.high)], "method": "Welch" if unequal else "Student t"},
                {"name": "Cohen's d", "estimate": _round_opt(d_val), "ci_95": d_ci, "method": f"Bootstrap ({BOOTSTRAP_REPS})"},
            ]

        elif mode == "mw":
            a, b = gs
            res = stats.mannwhitneyu(a, b, alternative=alternative, method="auto")

            def _rb_mw(x1, x2):
                rk = stats.rankdata(np.concatenate([x1, x2]))[: len(x1)].sum()
                return 2.0 * (rk - len(x1) * (len(x1) + 1) / 2.0) / (len(x1) * len(x2)) - 1.0

            rb_val = float(_rb_mw(a, b))
            rb_ci = _bootstrap_ci(gs, _rb_mw)
            result_block.update(
                {
                    "method": "Mann-Whitney U test",
                    "h0": f"Les distributions de {y_col} sont identiques entre {labels[0]} et {labels[1]}.",
                    "h1": f"Les distributions de {y_col} diffèrent entre {labels[0]} et {labels[1]}.",
                    "statistic_name": "U",
                    "statistic": _round_opt(res.statistic),
                    "df": None,
                    "p_value": _round_opt(res.pvalue),
                    "significant": bool(res.pvalue < alpha),
                }
            )
            effects = [{"name": "r_rb", "estimate": _round_opt(rb_val), "ci_95": rb_ci, "method": f"Bootstrap ({BOOTSTRAP_REPS})"}]

        elif mode == "anova":
            if unequal:
                f_stat, p_val, df_list = _welch_anova(gs)
                method_name = "Welch's ANOVA"
            else:
                res = stats.f_oneway(*gs)
                f_stat, p_val = float(res.statistic), float(res.pvalue)
                df_list = [float(len(gs) - 1), float(n_complete - len(gs))]
                method_name = "One-way ANOVA"

            def _eta2(*arrs):
                z = np.concatenate(arrs)
                ss_t = np.sum((z - np.mean(z)) ** 2)
                return np.sum([len(g) * (np.mean(g) - np.mean(z)) ** 2 for g in arrs]) / ss_t if ss_t > 0 else np.nan

            eta_val = float(_eta2(*gs))
            eta_ci = _bootstrap_ci(gs, _eta2)
            if eta_ci[0] is not None and eta_ci[1] is not None and (eta_ci[1] - eta_ci[0]) > 0.25 and p_val >= alpha:
                flags.append({"code": "low_power_wide_ci", "severity": "info", "detail": f"IC 95 % de η² très large ({eta_ci}) : faible puissance statistique."})

            if p_val < alpha and len(gs) > 2:
                posthoc = _parametric_posthoc(gs, labels, unequal=unequal)

            result_block.update(
                {
                    "method": method_name,
                    "h0": f"Les moyennes de {y_col} sont égales dans tous les groupes de {g_col}.",
                    "h1": f"Au moins un groupe de {g_col} diffère en moyenne sur {y_col}.",
                    "statistic_name": "F",
                    "statistic": _round_opt(f_stat),
                    "df": [_round_opt(d, 2) for d in df_list],
                    "p_value": _round_opt(p_val),
                    "significant": bool(p_val < alpha),
                }
            )
            effects = [{"name": "η²", "estimate": _round_opt(eta_val), "ci_95": eta_ci, "method": f"Bootstrap ({BOOTSTRAP_REPS})"}]

        else:  # kw
            res = stats.kruskal(*gs)

            def _eps2(*arrs):
                if np.ptp(np.concatenate(arrs)) == 0:
                    return np.nan
                return stats.kruskal(*arrs).statistic / (sum(len(g) for g in arrs) - 1)

            eps_val = float(_eps2(*gs))
            eps_ci = _bootstrap_ci(gs, _eps2)
            if res.pvalue < alpha and len(gs) > 2:
                posthoc = _dunn_posthoc(gs, labels)

            result_block.update(
                {
                    "method": "Kruskal-Wallis test",
                    "h0": f"Les distributions de {y_col} sont identiques selon {g_col}.",
                    "h1": f"Au moins un groupe de {g_col} diffère en rangs sur {y_col}.",
                    "statistic_name": "H",
                    "statistic": _round_opt(res.statistic),
                    "df": [float(len(gs) - 1)],
                    "p_value": _round_opt(res.pvalue),
                    "significant": bool(res.pvalue < alpha),
                }
            )
            effects = [{"name": "ε²", "estimate": _round_opt(eps_val), "ci_95": eps_ci, "method": f"Bootstrap ({BOOTSTRAP_REPS})"}]

        plot_data["groups"] = {lb: g.tolist() for lb, g in zip(labels, gs)}

    # ---------------- 4. RÉGRESSION (REG / MULTI / QUAD) ----------------
    elif mode in ("reg", "multi", "quad"):
        y = sub[y_col].to_numpy(dtype=float)
        if mode == "quad":
            x_raw = sub[x_cols[0]].to_numpy(dtype=float)
            x_centered = x_raw - np.mean(x_raw)
            p_mat = np.column_stack((x_raw, x_centered**2))
            term_names = ["(Intercept)", x_cols[0], f"({x_cols[0]} - M)²"]
        else:
            p_mat = np.column_stack([sub[c].to_numpy(dtype=float) for c in x_cols])
            term_names = ["(Intercept)"] + x_cols

        ols = _fit_ols(y, p_mat, alpha)
        sw = _shapiro_diag(ols["resid"], "Residuals")
        diagnostics.append({"name": "Breusch-Pagan (Koenker)", "label": "Global", "n": n_complete, "statistic": _round_opt(ols["bp_stat"]), "p": _round_opt(ols["bp_p"])})
        diagnostics.append(sw)

        if ols["robust_hc3"]:
            flags.append({"code": "heteroscedasticity", "severity": "warning", "detail": f"Breusch-Pagan p = {_round_opt(ols['bp_p'])} : bascule automatique sur erreurs standards HC3."})
        if sw["p"] is not None and sw["p"] < alpha:
            flags.append({"code": "normality_failed", "severity": "warning", "detail": f"Résidus non normaux (Shapiro-Wilk p = {sw['p']})."})
        if ols["max_cooks_d"] > 4.0 / n_complete:
            flags.append({"code": "high_leverage_cooks_d", "severity": "warning", "detail": f"Observation influente détectée (Cook's D max = {_round_opt(ols['max_cooks_d'], 3)})."})

        t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, ols["df_res"]))
        for idx, name in enumerate(term_names):
            b_val = float(ols["b"][idx])
            se_val = float(ols["se"][idx])
            t_val = b_val / se_val
            p_val = float(2.0 * stats.t.sf(abs(t_val), ols["df_res"]))
            vif_val = _round_opt(ols["vif"][idx], 1) if idx > 0 else None
            beta_val = _round_opt(ols["std_beta"][idx], 3) if idx > 0 else None

            simple_r = None
            if idx > 0 and mode != "quad":
                simple_r = float(np.corrcoef(p_mat[:, idx - 1], y)[0, 1])
                if vif_val is not None and vif_val > 10.0:
                    flags.append(
                        {
                            "code": "vif_critical",
                            "severity": "critical" if vif_val > 100 else "warning",
                            "variable": name,
                            "vif": vif_val,
                            "detail": f"Colinéarité {'extrême' if vif_val > 100 else 'élevée'} sur {name} (VIF = {vif_val}).",
                        }
                    )
                if beta_val is not None and abs(beta_val) > 1.0:
                    flags.append({"code": "beta_out_of_bounds", "severity": "critical", "variable": name, "detail": f"|β| > 1 sur {name} (β = {beta_val}) : artefact de colinéarité."})
                if simple_r is not None and abs(simple_r) > 0.1 and (b_val * simple_r < 0) and (vif_val is not None and vif_val > 5.0):
                    flags.append(
                        {
                            "code": "sign_flip",
                            "severity": "critical",
                            "variable": name,
                            "detail": f"Inversion de signe sur {name} (VIF = {vif_val}) : corrélation simple r = {round(simple_r, 3)} mais B multiple = {round(b_val, 3)}.",
                        }
                    )

            coefficients.append(
                {
                    "term": name,
                    "B": _round_opt(b_val),
                    "beta": beta_val,
                    "SE": _round_opt(se_val),
                    "t": _round_opt(t_val),
                    "p": _round_opt(p_val),
                    "VIF": vif_val,
                    "simple_r": _round_opt(simple_r, 3) if simple_r is not None else None,
                    "ci_95": [_round_opt(b_val - t_crit * se_val), _round_opt(b_val + t_crit * se_val)],
                }
            )

        # Détection automatique de non-linéarité quadratique sur régression simple
        if mode == "reg" and n_complete >= 6:
            x_raw = p_mat[:, 0]
            x_mean = float(np.mean(x_raw))
            xc = x_raw - x_mean
            q_mat = np.column_stack((np.ones(n_complete), xc, xc**2))
            if np.linalg.matrix_rank(q_mat) == 3:
                bq = np.linalg.lstsq(q_mat, y, rcond=None)[0]
                eq = y - q_mat @ bq
                ss_res_q = float(eq @ eq)
                ss_tot_y = float(np.sum((y - np.mean(y)) ** 2))
                r2_quad = 1.0 - ss_res_q / ss_tot_y
                if (r2_quad - ols["r2"]) > 0.15 and ss_res_q > 0:
                    ss_res_lin = float(ols["resid"] @ ols["resid"])
                    df_q = n_complete - 3
                    f_add = ((ss_res_lin - ss_res_q) / 1.0) / (ss_res_q / df_q)
                    p_add = float(stats.f.sf(f_add, 1, df_q))
                    shape = "U inversé (maximum)" if bq[2] < 0 else "U (minimum)"
                    vertex_x = x_mean - float(bq[1]) / (2.0 * float(bq[2])) if bq[2] != 0 else None
                    p_add_s = "< .001" if p_add < 0.001 else "= ." + f"{p_add:.3f}".split(".")[1]
                    # Diagnostics propres au modèle quadratique (Shapiro-Wilk + Breusch-Pagan)
                    sw_q = _shapiro_diag(eq, "Résidus (Modèle quadratique)")
                    diagnostics.append(sw_q)
                    qq_mat, _ = np.linalg.qr(q_mat, mode="reduced")
                    e2_q = eq**2
                    den_q = float(np.sum((e2_q - np.mean(e2_q)) ** 2))
                    lm_q = max(0.0, n_complete * (1.0 - float(np.sum((e2_q - qq_mat @ (qq_mat.T @ e2_q)) ** 2)) / den_q)) if den_q > 0 else 0.0
                    bp_q_p = float(stats.chi2.sf(lm_q, 2))
                    diagnostics.append(
                        {"name": "Breusch-Pagan (Koenker)", "label": "Modèle quadratique", "n": n_complete, "statistic": _round_opt(lm_q), "p": _round_opt(bp_q_p)}
                    )
                    flags.append(
                        {
                            "code": "possible_nonlinearity",
                            "severity": "critical",
                            "variable": x_cols[0],
                            "r2_linear": _round_opt(ols["r2"], 4),
                            "r2_quadratic": _round_opt(r2_quad, 4),
                            "shape": shape,
                            "vertex_x": _round_opt(vertex_x, 2),
                            "f_add": _round_opt(f_add, 2),
                            "df_add": [1, df_q],
                            "p_add": _round_opt(p_add, 4),
                            "detail": (
                                f"Relation non linéaire en {shape} (extremum estimé à {round(vertex_x, 2) if vertex_x is not None else 'N/A'}) : "
                                f"R² linéaire = {round(ols['r2'], 3)} vs R² quadratique = {round(r2_quad, 3)} "
                                f"(ajout du terme quadratique : F(1, {df_q}) = {round(f_add, 2)}, p {p_add_s})."
                            ),
                        }
                    )

        method_label = {
            "reg": "Linear regression (OLS · HC3)" if ols["robust_hc3"] else "Linear regression (OLS)",
            "multi": "Multiple regression (OLS · HC3)" if ols["robust_hc3"] else "Multiple regression (OLS)",
            "quad": "Quadratic regression (OLS · HC3)" if ols["robust_hc3"] else "Quadratic regression (OLS)",
        }[mode]

        result_block.update(
            {
                "method": method_label,
                "h0": "Toutes les pentes du modèle sont nulles (βj = 0).",
                "h1": "Au moins un prédicteur a un effet non nul (βj ≠ 0).",
                "statistic_name": "F",
                "statistic": _round_opt(ols["f_mod"]),
                "df": [float(ols["df_mod"]), float(ols["df_res"])],
                "p_value": _round_opt(ols["p_mod"]),
                "significant": bool(ols["p_mod"] < alpha),
                "r2": _round_opt(ols["r2"]),
                "r2_adj": _round_opt(ols["r2_adj"]),
                "robust_hc3": ols["robust_hc3"],
                "max_cooks_d": _round_opt(ols["max_cooks_d"], 3),
            }
        )
        effects = [
            {"name": "R²", "estimate": _round_opt(ols["r2"]), "ci_95": [None, None], "method": "OLS"},
            {"name": "R² ajusté", "estimate": _round_opt(ols["r2_adj"]), "ci_95": [None, None], "method": "OLS"},
        ]
        plot_data.update(
            {
                "y": y.tolist(),
                "x": p_mat[:, 0].tolist(),
                "fitted": ols["fitted"].tolist(),
                "resid": ols["resid"].tolist(),
            }
        )

    # ---------------- 5. CONTINGENCE (CHI2 / FISHER / MONTE CARLO) ----------------
    elif mode == "chi":
        x_col = x_cols[0]
        # Orientation P(Y | X) : variable explicative X en lignes, variable expliquée Y en colonnes
        ct = pd.crosstab(sub[x_col].astype(str), sub[y_col].astype(str))
        tab = ct.to_numpy(dtype=int)
        if min(tab.shape) < 2:
            raise ValueError("Il faut au moins 2 modalités dans chaque variable catégorielle.")

        chi_stat, chi_p, dof, expected = stats.chi2_contingency(tab, correction=False)
        min_exp = float(np.min(expected))
        pct_low = float(np.mean(expected < 5.0))
        sparse = (min_exp < 1.0) or (pct_low > 0.20)

        diagnostics.append(
            {
                "name": "Effectifs attendus",
                "label": f"{int(np.sum(expected < 5))}/{expected.size} cellules < 5",
                "n": n_complete,
                "statistic": _round_opt(min_exp, 2),
                "p": None,
            }
        )

        if sparse:
            flags.append(
                {
                    "code": "sparse_contingency",
                    "severity": "warning",
                    "detail": f"Effectifs attendus faibles (min = {round(min_exp, 2)}, {round(pct_low*100)}% < 5) : bascule automatique sur test exact / Monte Carlo.",
                }
            )
            if tab.shape == (2, 2):
                _, p_exact = stats.fisher_exact(tab)
                method_name, stat_name, stat_val, p_val = "Fisher's exact test", "exact", None, float(p_exact)
            else:
                rng = np.random.default_rng(SEED)
                row_sums = tab.sum(axis=1)
                col_sums = tab.sum(axis=0)
                hits = 0
                mc_reps = 2000
                for _ in range(20):
                    sims = stats.random_table.rvs(row_sums, col_sums, size=100, random_state=rng)
                    sim_chi = np.sum(((sims - expected) ** 2) / expected, axis=(1, 2))
                    hits += int(np.sum(sim_chi >= chi_stat - 1e-12))
                p_mc = (hits + 1.0) / (mc_reps + 1.0)
                method_name, stat_name, stat_val, p_val = "Chi-square (Monte Carlo, 2000)", "χ²", float(chi_stat), float(p_mc)
        else:
            method_name, stat_name, stat_val, p_val = "Pearson's chi-square test", "χ²", float(chi_stat), float(chi_p)

        cramer_v = float(np.sqrt(chi_stat / (tab.sum() * (min(tab.shape) - 1))))
        result_block.update(
            {
                "method": method_name,
                "h0": f"{y_col} et {x_col} sont indépendants.",
                "h1": f"Il existe une association entre {y_col} et {x_col}.",
                "statistic_name": stat_name,
                "statistic": _round_opt(stat_val),
                "df": [float(dof)] if stat_name == "χ²" else None,
                "p_value": _round_opt(p_val),
                "significant": bool(p_val < alpha),
                "contingency_table": {
                    "row_var": x_col,
                    "col_var": y_col,
                    "rows": list(ct.index),
                    "cols": list(ct.columns),
                    "counts": tab.tolist(),
                },
            }
        )
        effects = [{"name": "Cramér's V", "estimate": _round_opt(cramer_v), "ci_95": [None, None], "method": "Asymptotic"}]
        plot_data["contingency"] = result_block["contingency_table"]

    # ---------------- 6. RÉGRESSION LOGISTIQUE BINAIRE (LOGIT) ----------------
    elif mode == "logit":
        raw_y = sub[y_col].astype(str).str.strip()
        uniq_y = sorted(raw_y.unique().tolist())
        if len(uniq_y) != 2:
            raise ValueError(f"La régression logistique exige exactement 2 classes dans {y_col} (trouvé : {uniq_y}).")
        # Classe positive : "Oui", "1", "True" si présent, sinon 2e modalité triée
        pos_label = next((u for u in uniq_y if u.lower() in ("oui", "yes", "1", "1.0", "true")), uniq_y[1])
        neg_label = [u for u in uniq_y if u != pos_label][0]
        y_bin = (raw_y == pos_label).to_numpy(dtype=float)

        p_mat = np.column_stack([sub[c].to_numpy(dtype=float) for c in x_cols])
        log_res = _fit_logistic(y_bin, p_mat)

        if not log_res["converged"]:
            flags.append({"code": "quasi_separation", "severity": "warning", "detail": "Convergence IRLS partielle : possible séparation quasi-parfaite des classes."})

        z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
        term_names = ["(Intercept)"] + x_cols
        for idx, name in enumerate(term_names):
            b_val = float(log_res["b"][idx])
            se_val = float(log_res["se"][idx])
            z_val = b_val / se_val
            p_val = float(2.0 * stats.norm.sf(abs(z_val)))
            or_val = float(np.exp(np.clip(b_val, -20, 20))) if idx > 0 else None
            or_lo = float(np.exp(np.clip(b_val - z_crit * se_val, -20, 20))) if idx > 0 else None
            or_hi = float(np.exp(np.clip(b_val + z_crit * se_val, -20, 20))) if idx > 0 else None
            vif_val = _round_opt(log_res["vif"][idx], 1) if idx > 0 else None
            if vif_val is not None and vif_val > 10.0:
                flags.append(
                    {
                        "code": "vif_critical",
                        "severity": "critical" if vif_val > 100 else "warning",
                        "variable": name,
                        "vif": vif_val,
                        "detail": f"Colinéarité {'extrême' if vif_val > 100 else 'élevée'} sur {name} (VIF = {vif_val}).",
                    }
                )
            coefficients.append(
                {
                    "term": name,
                    "B": _round_opt(b_val),
                    "SE": _round_opt(se_val),
                    "z": _round_opt(z_val),
                    "p": _round_opt(p_val),
                    "OR": _round_opt(or_val, 3) if or_val is not None else None,
                    "OR_ci_95": [_round_opt(or_lo, 3), _round_opt(or_hi, 3)] if or_val is not None else [None, None],
                    "VIF": vif_val,
                    "ci_95": [_round_opt(b_val - z_crit * se_val), _round_opt(b_val + z_crit * se_val)],
                }
            )

        diagnostics.append(
            {
                "name": "Rapport de vraisemblance (LRT)",
                "label": f"Classe positive : {pos_label} ({int(np.sum(y_bin))}/{n_complete})",
                "n": n_complete,
                "statistic": _round_opt(log_res["lrt_chi2"]),
                "p": _round_opt(log_res["lrt_p"]),
            }
        )
        result_block.update(
            {
                "method": "Binary logistic regression (MLE)",
                "h0": "Tous les Odds Ratios valent 1 (βj = 0).",
                "h1": f"Au moins un prédicteur modifie la probabilité de {y_col} = {pos_label}.",
                "positive_class": pos_label,
                "negative_class": neg_label,
                "statistic_name": "χ² (LRT)",
                "statistic": _round_opt(log_res["lrt_chi2"]),
                "df": [float(log_res["df_mod"])],
                "p_value": _round_opt(log_res["lrt_p"]),
                "significant": bool(log_res["lrt_p"] < alpha),
                "mcfadden_r2": _round_opt(log_res["mcfadden_r2"]),
                "auc": _round_opt(log_res["auc"], 3),
            }
        )
        effects = [
            {"name": "Pseudo-R² (McFadden)", "estimate": _round_opt(log_res["mcfadden_r2"]), "ci_95": [None, None], "method": "MLE"},
            {"name": "AUC-ROC", "estimate": _round_opt(log_res["auc"], 3), "ci_95": [None, None], "method": "Mann-Whitney"},
        ]
        plot_data.update({"y_bin": y_bin.tolist(), "probs": log_res["probs"].tolist(), "pos_label": pos_label})

    # ---------------- 7. MATRICE DE CORRÉLATIONS (PEARSON + SPEARMAN + HOLM) ----------------
    elif mode == "corr":
        corr_cols = [y_col] + [c for c in x_cols if c != y_col]
        if len(corr_cols) < 2:
            raise ValueError("Sélectionnez au moins 2 variables continues pour une matrice de corrélations.")
        mat = sub[corr_cols].to_numpy(dtype=float)
        r_mat = np.corrcoef(mat, rowvar=False)
        pairs: list[dict[str, Any]] = []
        for i, j in itertools.combinations(range(len(corr_cols)), 2):
            rp, pp = stats.pearsonr(mat[:, i], mat[:, j])
            rs, ps = stats.spearmanr(mat[:, i], mat[:, j])
            pairs.append(
                {
                    "method": "Pearson / Spearman",
                    "a": corr_cols[i],
                    "b": corr_cols[j],
                    "difference": _round_opt(rp, 3),  # r de Pearson
                    "spearman_rho": _round_opt(rs, 3),
                    "p_raw": _round_opt(pp),
                    "p_spearman": _round_opt(ps),
                    "p_adj": None,
                }
            )
            if abs(rp - rs) > 0.20:
                flags.append(
                    {
                        "code": "pearson_spearman_gap",
                        "severity": "warning",
                        "detail": f"Écart fort entre Pearson (r = {round(rp, 2)}) et Spearman (ρ = {round(rs, 2)}) pour {corr_cols[i]} × {corr_cols[j]} : outlier ou non-linéarité monotone.",
                    }
                )
        # Ajustement Holm
        order = sorted(range(len(pairs)), key=lambda k: pairs[k]["p_raw"])
        run_max = 0.0
        for rank, idx in enumerate(order):
            adj = min(1.0, max(run_max, (len(pairs) - rank) * pairs[idx]["p_raw"]))
            run_max = adj
            pairs[idx]["p_adj"] = _round_opt(adj)
        posthoc = pairs
        min_p = min(p["p_adj"] for p in pairs)
        max_abs_r = max(abs(p["difference"]) for p in pairs)
        result_block.update(
            {
                "method": "Correlation matrix (Pearson & Spearman, Holm)",
                "h0": "Toutes les corrélations par paires sont nulles (r = 0).",
                "h1": "Au moins une paire de variables présente une corrélation non nulle.",
                "statistic_name": "max |r|",
                "statistic": _round_opt(max_abs_r, 3),
                "df": [float(n_complete - 2)],
                "p_value": _round_opt(min_p),
                "significant": bool(min_p < alpha),
            }
        )
        effects = [{"name": "max |r|", "estimate": _round_opt(max_abs_r, 3), "ci_95": [None, None], "method": "Pearson"}]
        plot_data.update({"corr_cols": corr_cols, "r_matrix": r_mat.tolist()})

    # ---------------- 8. ANOVA À MESURES RÉPÉTÉES (GREENHOUSE-GEISSER + FRIEDMAN) ----------------
    elif mode == "rm_anova":
        cond_cols = [y_col] + [c for c in x_cols if c != y_col]
        k = len(cond_cols)
        if k < 3 or n_complete < 3:
            raise ValueError("L'ANOVA à mesures répétées exige au moins 3 conditions (colonnes) et 3 sujets complets.")
        mat = sub[cond_cols].to_numpy(dtype=float)  # shape (n, k)

        grand_mean = float(np.mean(mat))
        cond_means = np.mean(mat, axis=0)
        subj_means = np.mean(mat, axis=1)
        ss_cond = float(n_complete * np.sum((cond_means - grand_mean) ** 2))
        ss_subj = float(k * np.sum((subj_means - grand_mean) ** 2))
        ss_tot = float(np.sum((mat - grand_mean) ** 2))
        ss_err = max(1e-12, ss_tot - ss_cond - ss_subj)

        df1 = float(k - 1)
        df2 = float((n_complete - 1) * (k - 1))
        f_stat = (ss_cond / df1) / (ss_err / df2)
        eta_p2 = ss_cond / (ss_cond + ss_err)

        # Epsilon de Greenhouse-Geisser (correction de sphéricité)
        cov_m = np.cov(mat, rowvar=False, ddof=1)
        row_m = np.mean(cov_m, axis=1, keepdims=True)
        col_m = np.mean(cov_m, axis=0, keepdims=True)
        d_mat = cov_m - row_m - col_m + np.mean(cov_m)
        tr_d = float(np.trace(d_mat))
        tr_d2 = float(np.sum(d_mat * d_mat))
        gg_eps = float(np.clip((tr_d**2) / ((k - 1) * tr_d2), 1.0 / (k - 1), 1.0)) if tr_d2 > 0 else 1.0
        df1_gg, df2_gg = df1 * gg_eps, df2 * gg_eps
        p_gg = float(stats.f.sf(f_stat, df1_gg, df2_gg))

        # Test non-paramétrique de Friedman en contrôle de robustesse
        fried = stats.friedmanchisquare(*[mat[:, j] for j in range(k)])
        diagnostics.append({"name": "Greenhouse-Geisser ε", "label": "Sphéricité", "n": n_complete, "statistic": _round_opt(gg_eps, 3), "p": None})
        diagnostics.append({"name": "Friedman (contrôle)", "label": "Non-paramétrique", "n": n_complete, "statistic": _round_opt(fried.statistic), "p": _round_opt(fried.pvalue)})
        if gg_eps < 0.75:
            flags.append({"code": "sphericity_departure", "severity": "warning", "detail": f"Sphéricité dégradée (ε GG = {round(gg_eps, 3)}) : degrés de liberté corrigés par Greenhouse-Geisser."})

        for j, cname in enumerate(cond_cols):
            arr = mat[:, j]
            groups_summary.append(
                {
                    "label": cname,
                    "n": n_complete,
                    "mean": _round_opt(np.mean(arr)),
                    "median": _round_opt(np.median(arr)),
                    "sd": _round_opt(np.std(arr, ddof=1)),
                }
            )

        # Post-hoc appariés ajustés Holm si significatif
        if p_gg < alpha:
            pairs_rm = []
            for i, j in itertools.combinations(range(k), 2):
                t_r = stats.ttest_rel(mat[:, j], mat[:, i])
                pairs_rm.append(
                    {
                        "method": "Paired t (Holm)",
                        "a": cond_cols[i],
                        "b": cond_cols[j],
                        "difference": _round_opt(float(np.mean(mat[:, j] - mat[:, i]))),
                        "p_raw": _round_opt(t_r.pvalue),
                        "p_adj": None,
                    }
                )
            order = sorted(range(len(pairs_rm)), key=lambda idx: pairs_rm[idx]["p_raw"])
            run_max = 0.0
            for rank, idx in enumerate(order):
                adj = min(1.0, max(run_max, (len(pairs_rm) - rank) * pairs_rm[idx]["p_raw"]))
                run_max = adj
                pairs_rm[idx]["p_adj"] = _round_opt(adj)
            posthoc = pairs_rm

        result_block.update(
            {
                "method": "Repeated-measures ANOVA (Greenhouse-Geisser)",
                "h0": "Les moyennes des conditions répétées sont toutes égales.",
                "h1": "Au moins une condition répétée diffère en moyenne.",
                "statistic_name": "F",
                "statistic": _round_opt(f_stat),
                "df": [_round_opt(df1_gg, 2), _round_opt(df2_gg, 2)],
                "p_value": _round_opt(p_gg),
                "significant": bool(p_gg < alpha),
                "gg_epsilon": _round_opt(gg_eps, 3),
                "friedman_p": _round_opt(fried.pvalue),
            }
        )
        effects = [{"name": "η²_p", "estimate": _round_opt(eta_p2), "ci_95": [None, None], "method": "Partial eta-squared"}]
        plot_data.update({"cond_cols": cond_cols, "matrix": mat.tolist()})
    else:
        raise ValueError(f"Mode statistique inconnu : {mode}")

    # Assemblage du Contrat JSON certifié (STRICTEMENT SANS DONNÉES INDIVIDUELLES)
    payload_for_hash = {
        "plan": {
            "mode": mode,
            "y": y_col,
            "xs": x_cols,
            "alpha": alpha,
            "alternative": alternative,
            "question": question,
            "language": language,
        },
        "data_rows_hash": sha256_json(sub.to_dict(orient="records")),
    }
    contract = {
        "contract_version": "2.0",
        "privacy_guarantee": "AGGREGATED_ONLY_NO_RAW_ROWS",
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "filename": dataset_meta.get("filename", "unknown"),
            "all_columns": list(df.columns),
            "custom_missing": dataset_meta.get("custom_missing", []),
            "excluded_pii_columns": dataset_meta.get("excluded_pii_columns", []),
            "sha256_raw_file": dataset_meta.get("sha256_raw_file", ""),
            "sha256_anonymized_file": dataset_meta.get("sha256_anonymized_file", ""),
            "sha256_analysis_json": sha256_json(payload_for_hash),
            "environment": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "seed": SEED,
            },
        },
        "plan": payload_for_hash["plan"],
        "missing_summary": missing_summary,
        "result": result_block,
        "groups": groups_summary,
        "effects": effects,
        "coefficients": coefficients,
        "posthoc": posthoc,
        "diagnostics": diagnostics,
        "flags": flags,
    }
    return contract, plot_data


def generate_reproducible_script(df: pd.DataFrame, contract: dict[str, Any]) -> str:
    """Génère un script Python compagnon lisible (JSON en clair, pas de Base64 opaque)."""
    plan = contract["plan"]
    used_cols = [plan["y"]] + [c for c in plan["xs"] if c != plan["y"]]
    sub_records = df[used_cols].dropna().to_dict(orient="records")
    payload = {"plan": plan, "records": sub_records}
    payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
    payload_sha = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
    env = contract["metadata"]["environment"]

    return f'''"""Script compagnon reproductible — StatAssistant 2-Phases.
SHA-256 fichier original : {contract["metadata"]["sha256_raw_file"]}
SHA-256 plan + données   : {contract["metadata"]["sha256_analysis_json"]}
Environnement requis     : Python {env["python"]}, NumPy {env["numpy"]}, SciPy {env["scipy"]}
"""

import hashlib
import json
import pandas as pd
from src.stats_engine import run_analysis

PAYLOAD_JSON = r"""{payload_str}"""
EXPECTED_PAYLOAD_SHA256 = "{payload_sha}"

if __name__ == "__main__":
    actual_sha = hashlib.sha256(PAYLOAD_JSON.encode("utf-8")).hexdigest()
    assert actual_sha == EXPECTED_PAYLOAD_SHA256, "Intégrité du payload compromise !"
    payload = json.loads(PAYLOAD_JSON)
    df = pd.DataFrame(payload["records"])
    contract, _ = run_analysis(
        df,
        payload["plan"],
        {{"filename": "{contract["metadata"]["filename"]}", "sha256_raw_file": "{contract["metadata"]["sha256_raw_file"]}"}},
    )
    print(json.dumps(contract["result"], indent=2, ensure_ascii=False))
'''
