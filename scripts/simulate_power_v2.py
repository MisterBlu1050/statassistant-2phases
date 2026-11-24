#!/usr/bin/env python3
"""
simulate_power_v2.py — Calcul reproductible de l'ICC pilote et simulation de puissance
Monte Carlo du modèle linéaire mixte (intercept aléatoire artiste) pour le Protocole V2 (1985-2024).

Usage:
    python scripts/simulate_power_v2.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SEED_V2 = 20261124


def compute_anova_icc(values: np.ndarray, group_codes: np.ndarray) -> dict[str, float]:
    """Estimateur ICC(1) par ANOVA à effets aléatoires à 1 facteur (déséquilibrée)."""
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
    icc = (msb - msw) / (msb + (n0 - 1.0) * msw)
    return {
        "estimator": "one_way_random_effects_anova",
        "n": int(n),
        "k_clusters": int(k),
        "avg_cluster_size": round(n / k, 3),
        "n0_effective": round(n0, 3),
        "icc": round(float(icc), 4),
        "sd_total": round(float(values.std(ddof=1)), 4),
    }


def simulate_mixed_power_gls(
    n_songs: int,
    delta_39: float,
    sigma_total: float,
    icc: float,
    mean_cluster: float = 1.8,
    n_sim: int = 400,
    seed: int = SEED_V2,
) -> float:
    """Simule la puissance bilatérale (alpha=0.05) de la pente temporelle sur 39 ans (1985-2024)
    dans un modèle à intercept aléatoire artiste (estimateur GLS exact par bloc).
    """
    rng = np.random.default_rng(seed)
    sigma_u = sigma_total * np.sqrt(icc)
    sigma_e = sigma_total * np.sqrt(1.0 - icc)
    inv_e = 1.0 / (sigma_e ** 2)
    beta1 = delta_39 / 39.0
    hits = 0

    for _ in range(n_sim):
        sizes: list[int] = []
        tot = 0
        while tot < n_songs:
            sz = int(rng.poisson(mean_cluster - 1.0)) + 1
            if tot + sz > n_songs:
                sz = n_songs - tot
            sizes.append(sz)
            tot += sz

        xtx_00 = xtx_01 = xtx_11 = xty_0 = xty_1 = 0.0
        for sz in sizes:
            debut = int(rng.integers(1985, 2025))
            offsets = rng.integers(0, 10, size=sz)
            t_c = np.clip(debut + offsets, 1985, 2024) - 2004.5
            u_c = float(rng.normal(0.0, sigma_u))
            e_c = rng.normal(0.0, sigma_e, size=sz)
            y_c = beta1 * t_c + u_c + e_c

            c = (sigma_u ** 2) / (sigma_e ** 2 + sz * (sigma_u ** 2))
            sum_t = float(t_c.sum())
            sum_y = float(y_c.sum())
            v_1 = inv_e * (1.0 - c * sz)

            xtx_00 += sz * v_1
            xtx_01 += v_1 * sum_t
            xtx_11 += inv_e * (float(np.dot(t_c, t_c)) - c * (sum_t ** 2))
            xty_0 += v_1 * sum_y
            xty_1 += inv_e * (float(np.dot(t_c, y_c)) - c * sum_t * sum_y)

        det = xtx_00 * xtx_11 - xtx_01 * xtx_01
        b1_hat = (-xtx_01 * xty_0 + xtx_00 * xty_1) / det
        se_b1 = float(np.sqrt(xtx_00 / det))
        if abs(b1_hat / se_b1) >= 1.959963984540054:
            hits += 1

    return round(hits / n_sim, 4)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulation de puissance mixte pour le Protocole V2.")
    parser.add_argument("--pilot-analytic", type=Path, default=None, help="CSV analytique pilote (optionnel).")
    parser.add_argument("--pilot-sources", type=Path, default=None, help="CSV sources pilote (optionnel).")
    parser.add_argument("--n-sim", type=int, default=400, help="Nombre de réplications Monte Carlo.")
    args = parser.parse_args()

    icc_info: dict[str, Any] = {
        "estimator": "pilot_reference_fallback",
        "icc": 0.344,
        "sd_total": 11.51,
    }
    if args.pilot_analytic and args.pilot_sources and args.pilot_analytic.exists() and args.pilot_sources.exists():
        df_a = pd.read_csv(args.pilot_analytic)
        df_s = pd.read_csv(args.pilot_sources)
        merged = df_a.merge(df_s[["LRCLIB_ID", "Artiste"]], on="LRCLIB_ID").dropna(subset=["MATTR_100"])
        vals = merged["MATTR_100"].to_numpy(dtype=float)
        codes = merged["Artiste"].astype("category").cat.codes.to_numpy()
        icc_info = compute_anova_icc(vals, codes)

    grid: list[dict[str, Any]] = []
    for n_songs in (600, 800, 1000, 1200, 1600, 2000):
        row: dict[str, Any] = {"N": n_songs}
        for delta in (3.0, 4.0, 5.0):
            row[f"power_delta_{delta:.1f}"] = simulate_mixed_power_gls(
                n_songs=n_songs,
                delta_39=delta,
                sigma_total=float(icc_info["sd_total"]),
                icc=float(icc_info["icc"]),
                n_sim=args.n_sim,
            )
        grid.append(row)

    print(json.dumps({"seed": SEED_V2, "pilot_icc": icc_info, "power_grid": grid}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
