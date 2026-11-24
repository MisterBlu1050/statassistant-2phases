#!/usr/bin/env python3
"""
simulate_power_v2_3.py — Simulation Monte Carlo (2 000 réplications) de la puissance
de l'ESTIMATEUR CONFIRMATOIRE PONDÉRÉ ROBUSTE AUX GRAPPES D'ARTISTES (WLS + sandwich CR1)
exécutée DIRECTEMENT sur la base de sondage réelle compilée (20 809 œuvres, 1985-2024).

Compare :
1. WLS pondéré (w_h = N_h / 250) sur le cadre complet (Top 50 -> Top 200), tirage stratifié égal (250/bloc)
2. WLS pondéré (w_h = N_h_Top50 / 250) sur le cadre harmonisé Top 50 constant (250/bloc)
3. WLS pondéré sur le cadre complet avec allocation proportionnelle à N_h (N = 2 000, poids uniformes)
4. Estimateur mixte REML non pondéré (tirage stratifié égal 250/bloc, pour comparaison)
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

SEED_V2 = 20261124
SIGMA_TOTAL = 11.5103
ICC_REML = 0.3703


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return [round(max(0.0, center - half), 4), round(min(1.0, center + half), 4)]


def wls_cluster_robust_t(y: np.ndarray, x: np.ndarray, w: np.ndarray, clusters: np.ndarray) -> tuple[float, float, int]:
    """Régression WLS pondérée (intercept + pente x) avec variance sandwich robuste aux grappes (CR1).
    Retourne (b1_hat, se_cr1, n_clusters).
    """
    # X = [1, x]
    sw = float(w.sum())
    swx = float(np.dot(w, x))
    swxx = float(np.dot(w, x * x))
    swy = float(np.dot(w, y))
    swxy = float(np.dot(w, x * y))
    det = sw * swxx - swx * swx
    b0 = (swxx * swy - swx * swxy) / det
    b1 = (-swx * swy + sw * swxy) / det

    # Résidus pondérés e_i = w_i * (y_i - b0 - b1*x_i)
    r = w * (y - b0 - b1 * x)
    # Sommes des scores par grappe (u_g = [sum_i e_i, sum_i e_i * x_i])
    _, inv = np.unique(clusters, return_inverse=True)
    G = int(inv.max() + 1)
    s0 = np.bincount(inv, weights=r, minlength=G)
    s1 = np.bincount(inv, weights=r * x, minlength=G)

    # Meat matrix M = sum_g u_g u_g'
    m00 = float(np.dot(s0, s0))
    m01 = float(np.dot(s0, s1))
    m11 = float(np.dot(s1, s1))

    # Bread (X'WX)^-1 = (1/det) * [[swxx, -swx], [-swx, sw]]
    # (1,1) entry of Bread * Meat * Bread:
    # row 1 of Bread = (-swx, sw) / det
    v11 = (swx * swx * m00 - 2.0 * swx * sw * m01 + sw * sw * m11) / (det * det)
    # Correction petits échantillons CR1: (G / (G - 1)) * ((N - 1) / (N - 2))
    n = len(y)
    cr1 = (G / max(1, G - 1)) * ((n - 1) / max(1, n - 2))
    se_b1 = math.sqrt(max(1e-18, v11 * cr1))
    return b1, se_b1, G


def run_frame_power_sim(
    df_frame: pd.DataFrame,
    n_total: int,
    delta_39: float,
    allocation: str,  # "equal_250" | "proportional"
    icc: float = ICC_REML,
    n_sim: int = 2000,
    seed: int = SEED_V2,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    sigma_u = SIGMA_TOTAL * math.sqrt(icc)
    sigma_e = SIGMA_TOTAL * math.sqrt(1.0 - icc)
    beta1 = delta_39 / 39.0

    # Préparer les strates réelles (hors pilote pour le confirmatoire)
    df_elig = df_frame[df_frame["In_Pilot"] != "Oui"].copy()
    blocks = sorted(df_elig["Block_5Y"].unique())
    strata_arrays: list[tuple[str, np.ndarray, np.ndarray, int]] = []
    # Mapper Artist_Slug -> int global
    artist_codes_all, _ = pd.factorize(df_elig["Artist_Slug"])
    df_elig["_art_id"] = artist_codes_all
    total_N = len(df_elig)

    for b in blocks:
        sub = df_elig[df_elig["Block_5Y"] == b]
        strata_arrays.append((
            b,
            sub["First_Year"].to_numpy(dtype=float),
            sub["_art_id"].to_numpy(dtype=np.int64),
            len(sub),
        ))

    if allocation == "equal_250":
        n_h_list = [n_total // len(blocks)] * len(blocks)
    elif allocation == "proportional":
        raw_nh = [n_total * (Nh / total_N) for _, _, _, Nh in strata_arrays]
        n_h_list = [int(round(v)) for v in raw_nh]
        diff = n_total - sum(n_h_list)
        n_h_list[-1] += diff
    else:
        raise ValueError(allocation)

    weights_by_stratum = [Nh / nh for (_, _, _, Nh), nh in zip(strata_arrays, n_h_list)]
    w_arr = np.concatenate([np.full(nh, wh, dtype=float) for nh, wh in zip(n_h_list, weights_by_stratum)])
    # Facteur de Kish (DEFF dû à la dispersion des poids)
    kish_deff = float(len(w_arr) * np.sum(w_arr ** 2) / (np.sum(w_arr) ** 2))

    hits_wls = 0
    mean_G_list: list[int] = []
    mean_m_list: list[float] = []

    for _ in range(n_sim):
        xs_parts = []
        arts_parts = []
        for (_, yrs, arts, Nh), nh in zip(strata_arrays, n_h_list):
            idx = rng.choice(Nh, size=nh, replace=False)
            xs_parts.append(yrs[idx])
            arts_parts.append(arts[idx])
        years = np.concatenate(xs_parts)
        arts = np.concatenate(arts_parts)
        x = years - 2004.5

        uniq_a, inv_a = np.unique(arts, return_inverse=True)
        u_a = rng.normal(0.0, sigma_u, size=len(uniq_a))
        y = beta1 * x + u_a[inv_a] + rng.normal(0.0, sigma_e, size=len(x))

        b1_hat, se_cr1, G = wls_cluster_robust_t(y, x, w_arr, arts)
        t_crit = float(stats.t.ppf(0.975, df=max(1, G - 2)))
        if abs(b1_hat / se_cr1) >= t_crit:
            hits_wls += 1
        mean_G_list.append(G)
        mean_m_list.append(len(x) / G)

    return {
        "allocation": allocation,
        "N": int(sum(n_h_list)),
        "delta_39": delta_39,
        "icc_true": icc,
        "n_sim": n_sim,
        "kish_weight_deff": round(kish_deff, 3),
        "mean_artist_clusters": round(float(np.mean(mean_G_list)), 1),
        "mean_songs_per_artist": round(float(np.mean(mean_m_list)), 3),
        "power_wls_cr1": round(hits_wls / n_sim, 4),
        "wilson_95_ci": wilson_ci(hits_wls, n_sim),
    }


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    frame_csv = repo / "data" / "sampling_frame_v2" / "sampling_frame_works_1985_2024.csv"
    weeks_csv = repo / "data" / "sampling_frame_v2" / "weeks_inventory_1985_2024.csv"

    df_all = pd.read_csv(frame_csv)
    df_top50 = df_all[df_all["Eligible_Top50_Constant"] == "Oui"].copy()

    # Inspecter les 3 écarts > 7 jours dans weeks_inventory
    df_w = pd.read_csv(weeks_csv)
    gaps = []
    dates = [date.fromisoformat(d) for d in df_w["Week_Date"]]
    for i in range(1, len(dates)):
        delta = (dates[i] - dates[i - 1]).days
        if delta > 7:
            gaps.append({"from": dates[i - 1].isoformat(), "to": dates[i].isoformat(), "days": delta})

    results = {
        "seed": SEED_V2,
        "week_gaps_gt_7d": gaps,
        "scenarios": [
            {"label": "Cadre complet (Top 50->200) | Tirage egal 250/bloc | WLS pondere CR1",
             **run_frame_power_sim(df_all, 2000, 3.0, "equal_250", ICC_REML, 2000, SEED_V2)},
            {"label": "Cadre harmonise Top 50 constant | Tirage egal 250/bloc | WLS pondere CR1",
             **run_frame_power_sim(df_top50, 2000, 3.0, "equal_250", ICC_REML, 2000, SEED_V2 + 1)},
            {"label": "Cadre complet (Top 50->200) | Tirage proportionnel a N_h | WLS pondere CR1",
             **run_frame_power_sim(df_all, 2000, 3.0, "proportional", ICC_REML, 2000, SEED_V2 + 2)},
            {"label": "Cadre harmonise Top 50 constant | Tirage proportionnel a N_h | WLS pondere CR1",
             **run_frame_power_sim(df_top50, 2000, 3.0, "proportional", ICC_REML, 2000, SEED_V2 + 3)},
            {"label": "Cadre complet | Tirage egal 250/bloc | WLS pondere CR1 | N=2800",
             **run_frame_power_sim(df_all, 2800, 3.0, "equal_250", ICC_REML, 1000, SEED_V2 + 4)},
        ],
    }
    out_json = repo / "data" / "sampling_frame_v2" / "power_simulation_wls_real_frame.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
