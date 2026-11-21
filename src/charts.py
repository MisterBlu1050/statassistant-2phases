"""Visualisations comparatives annotées (Phase 1 — Matplotlib)."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


def _style_ax(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.35)


def build_figures(contract: dict[str, Any], plot_data: dict[str, Any]) -> list[tuple[str, plt.Figure]]:
    """Génère des graphiques comparatifs lisibles avec axes gradués et titrés."""
    mode = plot_data["mode"]
    y_col = plot_data["y_col"]
    x_cols = plot_data.get("x_cols", [])
    figs: list[tuple[str, plt.Figure]] = []

    if mode == "desc":
        y = np.asarray(plot_data["y"], dtype=float)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))
        ax1.hist(y, bins="auto", color="#2345b7", alpha=0.8, edgecolor="white")
        ax1.set_title(f"Distribution de {y_col} (n = {len(y)})")
        ax1.set_xlabel(y_col)
        ax1.set_ylabel("Effectif")
        _style_ax(ax1)

        ax2.boxplot(y, vert=True, widths=0.35, patch_artist=True, boxprops=dict(facecolor="#dce5ff"))
        jitter = np.random.default_rng(42).normal(1.0, 0.04, size=len(y))
        ax2.scatter(jitter, y, color="#2345b7", alpha=0.75, s=26, zorder=3)
        ax2.set_title(f"Boxplot & observations — {y_col}")
        ax2.set_xticks([1])
        ax2.set_xticklabels([y_col])
        ax2.set_ylabel(y_col)
        _style_ax(ax2)
        fig.tight_layout()
        figs.append(("Distribution et dispersion", fig))

    elif mode in ("pair", "signed"):
        diff = np.asarray(plot_data["diff"], dtype=float)
        before = np.asarray(plot_data["before"], dtype=float)
        after = np.asarray(plot_data["after"], dtype=float)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.8))

        # Avant / Après apparié
        for b, a in zip(before, after):
            ax1.plot([0, 1], [b, a], color="#9aa8c7", alpha=0.55, linewidth=1)
        ax1.scatter(np.zeros(len(before)), before, color="#5c6f91", s=28, zorder=3)
        ax1.scatter(np.ones(len(after)), after, color="#2345b7", s=28, zorder=3)
        ax1.plot([0, 1], [np.mean(before), np.mean(after)], color="#d9480f", linewidth=2.5, marker="o", label="Moyenne")
        ax1.set_xticks([0, 1])
        ax1.set_xticklabels([x_cols[0], y_col])
        ax1.set_ylabel("Score")
        ax1.set_title("Évolution individuelle & moyenne")
        ax1.legend(frameon=False)
        _style_ax(ax1)

        # Distribution des différences + Q-Q
        (osm, osr), (slope, intercept, _) = stats.probplot(diff, dist="norm")
        ax2.scatter(osm, osr, color="#2345b7", s=26, alpha=0.8)
        ax2.plot(osm, slope * osm + intercept, color="#d9480f", linewidth=1.6)
        ax2.set_title(f"Q-Q plot des différences ({y_col} - {x_cols[0]})")
        ax2.set_xlabel("Quantiles normaux théoriques")
        ax2.set_ylabel("Différences observées")
        _style_ax(ax2)
        fig.tight_layout()
        figs.append(("Évolution appariée et normalité des différences", fig))

    elif mode in ("ind", "mw", "anova", "kw"):
        groups: dict[str, list[float]] = plot_data["groups"]
        labels = list(groups.keys())
        data_list = [np.asarray(groups[lb], dtype=float) for lb in labels]

        fig, ax = plt.subplots(figsize=(8.2, 4.2))
        positions = np.arange(1, len(labels) + 1)
        bp = ax.boxplot(
            data_list,
            positions=positions,
            widths=0.4,
            patch_artist=True,
            showfliers=False,
            boxprops=dict(facecolor="#e6ecff", edgecolor="#2345b7"),
            medianprops=dict(color="#1d3557", linewidth=2),
        )
        rng = np.random.default_rng(42)
        for pos, arr in zip(positions, data_list):
            jitter = rng.normal(pos, 0.06, size=len(arr))
            ax.scatter(jitter, arr, color="#2345b7", alpha=0.75, s=30, zorder=3)
            ax.hlines(np.mean(arr), pos - 0.25, pos + 0.25, colors="#d9480f", linewidth=2.4, zorder=4, label="Moyenne" if pos == 1 else "")
        ax.set_xticks(positions)
        ax.set_xticklabels([f"{lb}\n(n={len(arr)})" for lb, arr in zip(labels, data_list)])
        ax.set_ylabel(y_col)
        ax.set_title(f"Comparaison comparative de {y_col} selon {x_cols[0]}")
        ax.legend(frameon=False, loc="best")
        _style_ax(ax)
        fig.tight_layout()
        figs.append(("Comparaison comparative des groupes (Boxplot + points individuels + moyenne)", fig))

    elif mode in ("reg", "multi", "quad"):
        y = np.asarray(plot_data["y"], dtype=float)
        x0 = np.asarray(plot_data["x"], dtype=float)
        fitted = np.asarray(plot_data["fitted"], dtype=float)
        resid = np.asarray(plot_data["resid"], dtype=float)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.6, 3.8))
        if mode in ("reg", "quad"):
            order = np.argsort(x0)
            ax1.scatter(x0, y, color="#2345b7", alpha=0.8, s=30, label="Observations")
            ax1.plot(x0[order], fitted[order], color="#d9480f", linewidth=2.2, label="Modèle ajusté")
            ax1.set_xlabel(x_cols[0])
            ax1.set_ylabel(y_col)
            ax1.set_title(f"{y_col} en fonction de {x_cols[0]}")
            ax1.legend(frameon=False)
        else:
            ax1.scatter(fitted, y, color="#2345b7", alpha=0.8, s=30)
            lims = [min(y.min(), fitted.min()), max(y.max(), fitted.max())]
            ax1.plot(lims, lims, color="#d9480f", linestyle="--", linewidth=1.5)
            ax1.set_xlabel("Valeurs prédites")
            ax1.set_ylabel(f"{y_col} observé")
            ax1.set_title("Observé vs Prédit (Régression multiple)")
        _style_ax(ax1)

        ax2.scatter(fitted, resid, color="#2345b7", alpha=0.8, s=30)
        ax2.axhline(0, color="#d9480f", linestyle="--", linewidth=1.4)
        ax2.set_xlabel("Valeurs ajustées")
        ax2.set_ylabel("Résidus")
        ax2.set_title("Résidus vs Valeurs ajustées")
        _style_ax(ax2)
        fig.tight_layout()
        figs.append(("Ajustement du modèle et diagnostic des résidus", fig))

    elif mode == "chi":
        ct = plot_data["contingency"]
        counts = np.asarray(ct["counts"], dtype=float)
        fig, ax = plt.subplots(figsize=(7.2, 3.8))
        im = ax.imshow(counts, cmap="Blues", aspect="auto")
        ax.set_xticks(range(len(ct["cols"])))
        ax.set_xticklabels(ct["cols"])
        ax.set_yticks(range(len(ct["rows"])))
        ax.set_yticklabels(ct["rows"])
        for i in range(counts.shape[0]):
            for j in range(counts.shape[1]):
                ax.text(j, i, f"{int(counts[i, j])}", ha="center", va="center", color="black", fontweight="bold")
        ax.set_title(f"Tableau de contingence : {ct.get('row_var', x_cols[0])} × {ct.get('col_var', y_col)}")
        fig.colorbar(im, ax=ax, label="Effectif")
        fig.tight_layout()
        figs.append(("Carte de contingence", fig))

    elif mode == "logit":
        y_bin = np.asarray(plot_data["y_bin"], dtype=int)
        probs = np.asarray(plot_data["probs"], dtype=float)
        pos_lbl = plot_data.get("pos_label", "Oui")
        fig, ax = plt.subplots(figsize=(7.6, 3.8))
        p0 = probs[y_bin == 0]
        p1 = probs[y_bin == 1]
        ax.boxplot([p0, p1], positions=[1, 2], widths=0.4, patch_artist=True, boxprops=dict(facecolor="#e6ecff", edgecolor="#2345b7"))
        rng = np.random.default_rng(42)
        ax.scatter(rng.normal(1, 0.05, len(p0)), p0, color="#5c6f91", alpha=0.65, s=24)
        ax.scatter(rng.normal(2, 0.05, len(p1)), p1, color="#2345b7", alpha=0.75, s=24)
        ax.set_xticks([1, 2])
        ax.set_xticklabels([f"Autres (n={len(p0)})", f"{y_col} = {pos_lbl} (n={len(p1)})"])
        ax.set_ylabel(f"Probabilité prédite P({pos_lbl})")
        ax.set_title(f"Régression logistique — Discrimination (AUC = {contract['result']['auc']})")
        _style_ax(ax)
        fig.tight_layout()
        figs.append(("Probabilités prédites par classe observée", fig))

    elif mode == "corr":
        cols = plot_data["corr_cols"]
        rmat = np.asarray(plot_data["r_matrix"], dtype=float)
        fig, ax = plt.subplots(figsize=(max(5.5, len(cols) * 1.3), max(4.2, len(cols) * 1.0)))
        im = ax.imshow(rmat, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels(cols, rotation=30, ha="right")
        ax.set_yticks(range(len(cols)))
        ax.set_yticklabels(cols)
        for i in range(len(cols)):
            for j in range(len(cols)):
                val = rmat[i, j]
                txt_col = "white" if abs(val) > 0.55 else "black"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=txt_col, fontweight="bold")
        ax.set_title("Matrice de corrélations (Pearson r)")
        fig.colorbar(im, ax=ax, label="r")
        fig.tight_layout()
        figs.append(("Heatmap de corrélations", fig))

    elif mode == "rm_anova":
        cols = plot_data["cond_cols"]
        mat = np.asarray(plot_data["matrix"], dtype=float)
        fig, ax = plt.subplots(figsize=(8.0, 4.0))
        xs = np.arange(len(cols))
        for row in mat[:40]:
            ax.plot(xs, row, color="#9aa8c7", alpha=0.35, linewidth=0.9)
        means = np.mean(mat, axis=0)
        sems = stats.sem(mat, axis=0)
        ax.errorbar(xs, means, yerr=1.96 * sems, color="#d9480f", linewidth=2.5, marker="o", capsize=5, label="Moyenne ± IC 95 %")
        ax.set_xticks(xs)
        ax.set_xticklabels(cols)
        ax.set_ylabel("Score mesuré")
        ax.set_title("Évolution sur mesures répétées (trajectoires individuelles & moyenne)")
        ax.legend(frameon=False)
        _style_ax(ax)
        fig.tight_layout()
        figs.append(("Profil des mesures répétées", fig))

    return figs
