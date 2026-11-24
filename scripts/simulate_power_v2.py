#!/usr/bin/env python3
"""
simulate_power_v2.py (v1.2) — Estimateur ICC pilote (ANOVA + REML exact) et simulation
Monte Carlo de puissance du modèle linéaire mixte sous allocation stratifiée exacte
(8 blocs quinquennaux de 1985 à 2024, 12,5 % par bloc, sans empilement sur 2024)
avec réestimation REML des composantes de variance à CHAQUE réplication.

Usage:
    python scripts/simulate_power_v2.py --n-sim 2000
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import optimize, stats

SEED_V2 = 20261124
BLOCKS_5Y = [
    (1985, 1989),
    (1990, 1994),
    (1995, 1999),
    (2000, 2004),
    (2005, 2009),
    (2010, 2014),
    (2015, 2019),
    (2020, 2024),
]


def wilson_ci(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    half = (z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * total)) / total)) / denom
    return round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)


def fit_random_intercept_reml(
    y: np.ndarray,
    x: np.ndarray,
    cluster_slices: list[tuple[int, int]],
) -> tuple[float, float, float, float, float]:
    """Estimation REML exacte du modèle mixte Y_ij = b0 + b1 * x_ij + u_i + e_ij
    par profilage 1D sur lambda = sigma_u^2 / sigma_e^2 (Sherman-Morrison par grappe).

    Retourne : (b1_hat, se_b1, icc_hat, sigma_u_hat, sigma_e_hat)
    """
    n = len(y)
    # Pré-calcul par grappe pour accélération vectorisée
    sizes = np.array([end - start for start, end in cluster_slices], dtype=float)
    sum_x = np.array([x[s:e].sum() for s, e in cluster_slices], dtype=float)
    sum_y = np.array([y[s:e].sum() for s, e in cluster_slices], dtype=float)
    sum_xx = np.array([float(np.dot(x[s:e], x[s:e])) for s, e in cluster_slices], dtype=float)
    sum_xy = np.array([float(np.dot(x[s:e], y[s:e])) for s, e in cluster_slices], dtype=float)
    sum_yy = np.array([float(np.dot(y[s:e], y[s:e])) for s, e in cluster_slices], dtype=float)

    def _eval_lambda(lam: float) -> tuple[float, float, float, float]:
        # V_i / sigma_e^2 = I + lam * 11'  =>  (V_i/se^2)^-1 = I - c_i * 11', c_i = lam / (1 + m_i * lam)
        denom_i = 1.0 + sizes * lam
        c_i = lam / denom_i
        w_1 = 1.0 - c_i * sizes  # = 1 / (1 + m_i * lam)

        a00 = float(np.sum(sizes * w_1))
        a01 = float(np.sum(w_1 * sum_x))
        a11 = float(np.sum(sum_xx - c_i * (sum_x ** 2)))
        b0_rhs = float(np.sum(w_1 * sum_y))
        b1_rhs = float(np.sum(sum_xy - c_i * sum_x * sum_y))

        det = a00 * a11 - a01 * a01
        if det <= 1e-12:
            return 1e18, 0.0, 1.0, 1.0
        b0 = (a11 * b0_rhs - a01 * b1_rhs) / det
        b1 = (-a01 * b0_rhs + a00 * b1_rhs) / det

        # Quadrature r' V^-1 r
        # Pour chaque grappe: r_i = y_i - b0 - b1 * x_i
        # sum(r_i^2) = sum_yy + m*b0^2 + b1^2*sum_xx - 2*b0*sum_y - 2*b1*sum_xy + 2*b0*b1*sum_x
        sr2 = (
            sum_yy
            + sizes * (b0 * b0)
            + (b1 * b1) * sum_xx
            - 2.0 * b0 * sum_y
            - 2.0 * b1 * sum_xy
            + 2.0 * b0 * b1 * sum_x
        )
        sr = sum_y - sizes * b0 - b1 * sum_x
        quad = float(np.sum(sr2 - c_i * (sr * sr)))
        if quad <= 1e-12:
            return 1e18, b1, 1.0, 1.0

        sigma_e2 = quad / (n - 2.0)
        logdet_v = float(np.sum(np.log(denom_i)))
        # -2 * logL_REML (à constante près) = (n-2)*log(sigma_e2) + log|V| + log|X'V^-1X|
        nll = (n - 2.0) * math.log(sigma_e2) + logdet_v + math.log(det)
        se_b1 = math.sqrt(sigma_e2 * a00 / det)
        return nll, b1, se_b1, sigma_e2

    # Optimisation 1D sur log(1 + lam) ou directement sur lam in [0, 20]
    res = optimize.minimize_scalar(lambda l: _eval_lambda(l)[0], bounds=(0.0, 20.0), method="bounded", options={"xatol": 1e-4})
    lam_hat = float(res.x)
    _, b1_hat, se_b1, sigma_e2 = _eval_lambda(lam_hat)
    sigma_u2 = lam_hat * sigma_e2
    icc_hat = sigma_u2 / (sigma_u2 + sigma_e2) if (sigma_u2 + sigma_e2) > 0 else 0.0
    return b1_hat, se_b1, icc_hat, math.sqrt(sigma_u2), math.sqrt(sigma_e2)


def compute_pilot_iccs(values: np.ndarray, group_codes: np.ndarray) -> dict[str, Any]:
    """Calcule l'ICC pilote par ANOVA (1 facteur aléatoire) ET par REML exact (intercept seul)."""
    n = len(values)
    k = int(group_codes.max() + 1)
    gm = float(values.mean())
    counts = np.bincount(group_codes)
    means = np.bincount(group_codes, weights=values) / counts
    ssb = float(np.sum(counts * (means - gm) ** 2))
    ssw = float(np.sum((values - means[group_codes]) ** 2))
    msb = ssb / (k - 1)
    msw = ssw / (n - k)
    n0 = float((n - np.sum(counts ** 2) / n) / (k - 1))
    icc_anova = (msb - msw) / (msb + (n0 - 1.0) * msw)

    # REML intercept-seul : trier par groupe
    order = np.argsort(group_codes)
    y_sorted = values[order]
    g_sorted = group_codes[order]
    slices: list[tuple[int, int]] = []
    start = 0
    for i in range(1, n):
        if g_sorted[i] != g_sorted[i - 1]:
            slices.append((start, i))
            start = i
    slices.append((start, n))

    sizes = np.array([e - s for s, e in slices], dtype=float)
    sum_y = np.array([y_sorted[s:e].sum() for s, e in slices], dtype=float)
    sum_yy = np.array([float(np.dot(y_sorted[s:e], y_sorted[s:e])) for s, e in slices], dtype=float)

    def _nll_null(lam: float) -> float:
        denom_i = 1.0 + sizes * lam
        c_i = lam / denom_i
        w_1 = 1.0 - c_i * sizes
        a00 = float(np.sum(sizes * w_1))
        b0 = float(np.sum(w_1 * sum_y)) / a00
        sr2 = sum_yy + sizes * (b0 * b0) - 2.0 * b0 * sum_y
        sr = sum_y - sizes * b0
        quad = float(np.sum(sr2 - c_i * (sr * sr)))
        se2 = quad / (n - 1.0)
        return (n - 1.0) * math.log(se2) + float(np.sum(np.log(denom_i))) + math.log(a00)

    res = optimize.minimize_scalar(_nll_null, bounds=(0.0, 20.0), method="bounded", options={"xatol": 1e-6})
    lam_reml = float(res.x)
    icc_reml = lam_reml / (1.0 + lam_reml)

    return {
        "n": int(n),
        "k_clusters": int(k),
        "avg_cluster_size": round(n / k, 3),
        "sd_total": round(float(values.std(ddof=1)), 4),
        "icc_anova": round(float(icc_anova), 4),
        "icc_reml": round(float(icc_reml), 4),
    }


def generate_stratified_years_and_clusters(
    n_per_block: int,
    mean_cluster: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Génère EXACTEMENT n_per_block chansons dans chacun des 8 blocs quinquennaux (1985-2024),
    soit 12,5 % par bloc et ~2,5 % par année, puis regroupe les chansons en grappes d'artistes
    réalistes (carrière locale) sans jamais altérer la distribution temporelle stratifiée.
    """
    # 1. Allocation temporelle exactement stratifiée : n_per_block / 5 par année (exact si multiple de 5)
    years_list: list[int] = []
    for y_start, y_end in BLOCKS_5Y:
        span = y_end - y_start + 1
        base = n_per_block // span
        rem = n_per_block % span
        for offset in range(span):
            cnt = base + (1 if offset < rem else 0)
            years_list.extend([y_start + offset] * cnt)
    years = np.array(years_list, dtype=float)
    # Légère permutation locale dans chaque bloc pour mélanger les artistes tout en gardant l'ordre chronologique global
    n = len(years)
    # Trier par année puis regrouper séquentiellement en grappes d'artistes de taille ~mean_cluster
    # (les chansons d'un même artiste sont ainsi proches dans le temps sans jamais déplacer leurs années !)
    years.sort()
    # Ajouter une petite perturbation d'ordre (fenêtre +/- 3 ans) pour que les grappes couvrent des carrières de 0-6 ans
    noisy_key = years + rng.uniform(-3.0, 3.0, size=n)
    order = np.argsort(noisy_key)
    years_ordered = years[order]

    slices: list[tuple[int, int]] = []
    idx = 0
    while idx < n:
        sz = int(rng.poisson(max(0.05, mean_cluster - 1.0))) + 1
        end = min(n, idx + sz)
        slices.append((idx, end))
        idx = end

    return years_ordered, slices


def simulate_power_reml_stratified(
    n_total: int,
    delta_39: float,
    sigma_total: float,
    icc_true: float,
    mean_cluster: float = 1.8,
    n_sim: int = 2000,
    seed: int = SEED_V2,
) -> dict[str, Any]:
    """Simulation Monte Carlo avec allocation stratifiée exacte (8 blocs de 5 ans) et
    réestimation REML des composantes de variance à chaque réplication (test t à k-2 ddl).
    """
    assert n_total % 8 == 0, "n_total doit être divisible par 8 blocs quinquennaux."
    n_per_block = n_total // 8
    rng = np.random.default_rng(seed)
    sigma_u = sigma_total * math.sqrt(icc_true)
    sigma_e = sigma_total * math.sqrt(1.0 - icc_true)
    beta1 = delta_39 / 39.0

    hits = 0
    est_iccs: list[float] = []
    block_check_done = False
    block_shares: dict[str, float] = {}

    for _ in range(n_sim):
        years, slices = generate_stratified_years_and_clusters(n_per_block, mean_cluster, rng)
        if not block_check_done:
            for ys, ye in BLOCKS_5Y:
                block_shares[f"{ys}-{ye}"] = round(float(np.mean((years >= ys) & (years <= ye))), 4)
            block_shares["year_2024_only"] = round(float(np.mean(years == 2024)), 4)
            block_check_done = True

        x = years - 2004.5
        y = np.empty(n_total, dtype=float)
        for s, e in slices:
            u_c = float(rng.normal(0.0, sigma_u))
            y[s:e] = beta1 * x[s:e] + u_c + rng.normal(0.0, sigma_e, size=e - s)

        b1_hat, se_b1, icc_hat, _, _ = fit_random_intercept_reml(y, x, slices)
        est_iccs.append(icc_hat)
        df_t = max(1, len(slices) - 2)
        t_crit = float(stats.t.ppf(0.975, df=df_t))
        if abs(b1_hat / se_b1) >= t_crit:
            hits += 1

    ci_lo, ci_hi = wilson_ci(hits, n_sim)
    return {
        "N": n_total,
        "n_per_5y_block": n_per_block,
        "delta_39": delta_39,
        "icc_true": icc_true,
        "mean_cluster": mean_cluster,
        "n_sim": n_sim,
        "power": round(hits / n_sim, 4),
        "wilson_95_ci": [ci_lo, ci_hi],
        "mean_estimated_icc_reml": round(float(np.mean(est_iccs)), 4),
        "verified_temporal_allocation": block_shares,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulation de puissance REML stratifiée (Protocole v1.2).")
    parser.add_argument("--pilot-analytic", type=Path, default=None)
    parser.add_argument("--pilot-sources", type=Path, default=None)
    parser.add_argument("--n-sim", type=int, default=2000)
    args = parser.parse_args()

    pilot_info: dict[str, Any] = {"sd_total": 11.5103, "icc_anova": 0.3438, "icc_reml": 0.370}
    if args.pilot_analytic and args.pilot_sources and args.pilot_analytic.exists() and args.pilot_sources.exists():
        df_a = pd.read_csv(args.pilot_analytic)
        df_s = pd.read_csv(args.pilot_sources)
        merged = df_a.merge(df_s[["LRCLIB_ID", "Artiste"]], on="LRCLIB_ID").dropna(subset=["MATTR_100"])
        vals = merged["MATTR_100"].to_numpy(dtype=float)
        codes = merged["Artiste"].astype("category").cat.codes.to_numpy()
        pilot_info = compute_pilot_iccs(vals, codes)

    sd_use = float(pilot_info["sd_total"])
    icc_reml = float(pilot_info["icc_reml"])

    # Scénario principal (N=2000, delta=3.0, ICC_REML) + grille de sensibilité ICC et cluster size
    scenarios = [
        simulate_power_reml_stratified(2000, 3.0, sd_use, icc_reml, mean_cluster=1.8, n_sim=args.n_sim, seed=SEED_V2),
        simulate_power_reml_stratified(2000, 3.0, sd_use, 0.30, mean_cluster=1.8, n_sim=min(args.n_sim, 1000), seed=SEED_V2 + 1),
        simulate_power_reml_stratified(2000, 3.0, sd_use, 0.45, mean_cluster=1.8, n_sim=min(args.n_sim, 1000), seed=SEED_V2 + 2),
        simulate_power_reml_stratified(2000, 3.0, sd_use, icc_reml, mean_cluster=2.5, n_sim=min(args.n_sim, 1000), seed=SEED_V2 + 3),
        simulate_power_reml_stratified(1600, 3.0, sd_use, icc_reml, mean_cluster=1.8, n_sim=min(args.n_sim, 1000), seed=SEED_V2 + 4),
        simulate_power_reml_stratified(2400, 3.0, sd_use, icc_reml, mean_cluster=1.8, n_sim=min(args.n_sim, 1000), seed=SEED_V2 + 5),
    ]

    print(json.dumps({"seed": SEED_V2, "pilot_icc": pilot_info, "scenarios": scenarios}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
