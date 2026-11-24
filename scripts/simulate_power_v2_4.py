#!/usr/bin/env python3
"""
simulate_power_v2_4.py — Comparaison APPARIÉE (sur les MÊMES échantillons simulés)
de la puissance de l'estimateur REML (modèle mixte à intercept aléatoire artiste,
variances réestimées à chaque réplication) ET de l'estimateur WLS pondéré CR1,
tirés DIRECTEMENT dans le cadre harmonisé Top 50 corrigé (First_Top50_Year,
Top50_Block_5Y, Artist_Slug réels, hors pilote In_Pilot='Non').
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulate_power_v2 import fit_random_intercept_reml, wilson_ci
from simulate_power_v2_3 import wls_cluster_robust_t

SEED_V2 = 20261124
SIGMA_TOTAL = 11.5103
ICC_REML = 0.3703


def run_paired_top50_power(
    df_top50: pd.DataFrame,
    n_total: int = 2000,
    delta_39: float = 3.0,
    icc: float = ICC_REML,
    n_sim: int = 2000,
    seed: int = SEED_V2,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    sigma_u = SIGMA_TOTAL * math.sqrt(icc)
    sigma_e = SIGMA_TOTAL * math.sqrt(1.0 - icc)
    beta1 = delta_39 / 39.0

    # Strates réelles corrigées par First_Top50_Year / Top50_Block_5Y (hors pilote)
    df_elig = df_top50[df_top50["In_Pilot"] != "Oui"].copy()
    blocks = sorted(df_elig["Top50_Block_5Y"].dropna().unique())
    n_per_block = n_total // len(blocks)

    artist_codes_all, _ = pd.factorize(df_elig["Artist_Slug"])
    df_elig["_art_id"] = artist_codes_all

    strata: list[tuple[str, np.ndarray, np.ndarray, int]] = []
    for b in blocks:
        sub = df_elig[df_elig["Top50_Block_5Y"] == b]
        strata.append((
            b,
            sub["First_Top50_Year"].to_numpy(dtype=float),
            sub["_art_id"].to_numpy(dtype=np.int64),
            len(sub),
        ))

    weights_by_stratum = [Nh / n_per_block for (_, _, _, Nh) in strata]
    w_arr = np.concatenate([np.full(n_per_block, wh, dtype=float) for wh in weights_by_stratum])
    kish_deff = float(len(w_arr) * np.sum(w_arr ** 2) / (np.sum(w_arr) ** 2))

    hits_reml = 0
    hits_wls = 0
    hits_both = 0
    reml_iccs: list[float] = []
    mean_G: list[int] = []

    for _ in range(n_sim):
        yrs_parts = []
        arts_parts = []
        for (_, yrs, arts, Nh) in strata:
            idx = rng.choice(Nh, size=n_per_block, replace=False)
            yrs_parts.append(yrs[idx])
            arts_parts.append(arts[idx])
        years = np.concatenate(yrs_parts)
        arts = np.concatenate(arts_parts)
        x = years - 2004.5

        uniq_a, inv_a = np.unique(arts, return_inverse=True)
        u_a = rng.normal(0.0, sigma_u, size=len(uniq_a))
        y = beta1 * x + u_a[inv_a] + rng.normal(0.0, sigma_e, size=len(x))

        # 1. Estimateur WLS pondéré CR1 sur cet échantillon exact
        b1_wls, se_wls, G = wls_cluster_robust_t(y, x, w_arr, arts)
        t_crit = float(stats.t.ppf(0.975, df=max(1, G - 2)))
        sig_wls = abs(b1_wls / se_wls) >= t_crit

        # 2. Estimateur REML exact (réestimation des variances) sur LE MÊME échantillon exact
        order = np.argsort(inv_a)
        y_s = y[order]
        x_s = x[order]
        g_s = inv_a[order]
        # Construire les tranches de grappes
        changes = np.flatnonzero(np.diff(g_s)) + 1
        starts = np.concatenate(([0], changes))
        ends = np.concatenate((changes, [len(g_s)]))
        slices = list(zip(starts.tolist(), ends.tolist()))

        b1_reml, se_reml, icc_hat, _, _ = fit_random_intercept_reml(y_s, x_s, slices)
        sig_reml = abs(b1_reml / se_reml) >= t_crit

        if sig_reml:
            hits_reml += 1
        if sig_wls:
            hits_wls += 1
        if sig_reml and sig_wls:
            hits_both += 1
        reml_iccs.append(icc_hat)
        mean_G.append(G)

    return {
        "frame": "Top 50 constant harmonise (First_Top50_Year, hors pilote)",
        "N": n_total,
        "n_per_5y_block": n_per_block,
        "delta_39": delta_39,
        "icc_true": icc,
        "n_sim": n_sim,
        "kish_weight_deff": round(kish_deff, 3),
        "mean_artist_clusters": round(float(np.mean(mean_G)), 1),
        "mean_songs_per_artist": round(n_total / float(np.mean(mean_G)), 3),
        "mean_estimated_icc_reml": round(float(np.mean(reml_iccs)), 4),
        "power_reml": round(hits_reml / n_sim, 4),
        "wilson_95_ci_reml": list(wilson_ci(hits_reml, n_sim)),
        "power_wls_cr1": round(hits_wls / n_sim, 4),
        "wilson_95_ci_wls_cr1": list(wilson_ci(hits_wls, n_sim)),
        "concordant_significant_both": round(hits_both / n_sim, 4),
    }


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    frame_csv = repo / "data" / "sampling_frame_v2" / "sampling_frame_works_1985_2024.csv"
    df_all = pd.read_csv(frame_csv)
    df_top50 = df_all[df_all["Eligible_Top50_Constant"] == "Oui"].copy()

    out = {
        "seed": SEED_V2,
        "null_calibration_type1_error": run_paired_top50_power(
            df_top50, n_total=2000, delta_39=0.0, icc=ICC_REML, n_sim=2000, seed=SEED_V2 + 100
        ),
        "paired_scenarios": [
            run_paired_top50_power(df_top50, n_total=2000, delta_39=3.0, icc=ICC_REML, n_sim=2000, seed=SEED_V2),
            run_paired_top50_power(df_top50, n_total=2000, delta_39=3.0, icc=0.30, n_sim=1000, seed=SEED_V2 + 1),
            run_paired_top50_power(df_top50, n_total=2000, delta_39=3.0, icc=0.45, n_sim=1000, seed=SEED_V2 + 2),
        ],
    }
    out_json = repo / "data" / "sampling_frame_v2" / "power_simulation_paired_v1_4.json"
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
