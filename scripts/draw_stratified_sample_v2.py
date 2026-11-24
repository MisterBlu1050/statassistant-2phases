#!/usr/bin/env python3
"""
draw_stratified_sample_v2.py — Tirage stratifié reproductible (SEED_V2 = 20261124)
sur le cadre harmonisé Top 50 (1985-2024), verrouillé jusqu'au dépôt OSF Registries.

Usage (UNIQUEMENT après obtention de l'identifiant OSF figé) :
    python scripts/draw_stratified_sample_v2.py --osf-registration-id <ID_OSF>

Garanties d'audit :
- Exige un identifiant --osf-registration-id non vide (refuse de tirer sans préenregistrement).
- Vérifie l'empreinte SHA-256 exacte de data/sampling_frame_v2/sampling_frame_works_1985_2024.csv.
- Exclut explicitement les œuvres pilotes (In_Pilot='Oui') dans un journal dédié (zéro suppression silencieuse).
- Génère l'ordre complet permuté des candidats dans chacune des 8 strates Top50_Block_5Y
  avec la graine SEED_V2 = 20261124 (target = 250 exploitables/strate, sans remplacement inter-strates).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SEED_V2 = 20261124
EXPECTED_FRAME_SHA256 = "668a448dac68299cc5431868d21f983f3dfb5904de8d857b1de070a5efc2f115"
TARGET_PER_STRATUM = 250


def main() -> int:
    parser = argparse.ArgumentParser(description="Tirage stratifié reproductible V2 (verrouillé par ID OSF).")
    parser.add_argument(
        "--osf-registration-id",
        required=True,
        help="Identifiant ou URL figée du préenregistrement OSF Registries (obligatoire avant tirage).",
    )
    args = parser.parse_args()

    osf_id = args.osf_registration_id.strip()
    if len(osf_id) < 4:
        raise ValueError("Identifiant OSF invalide ou vide — tirage refusé.")

    repo = Path(__file__).resolve().parent.parent
    frame_path = repo / "data" / "sampling_frame_v2" / "sampling_frame_works_1985_2024.csv"
    if not frame_path.exists():
        raise FileNotFoundError(f"Base de sondage introuvable : {frame_path}")

    actual_sha = hashlib.sha256(frame_path.read_bytes()).hexdigest()
    if actual_sha != EXPECTED_FRAME_SHA256:
        raise RuntimeError(
            f"Empreinte SHA-256 de la base de sondage modifiée ! Attendu {EXPECTED_FRAME_SHA256}, trouvé {actual_sha}"
        )

    df = pd.read_csv(frame_path)
    df_top50 = df[df["Eligible_Top50_Constant"] == "Oui"].copy()

    out_dir = repo / "data" / "draw_v2_0"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Journaliser explicitement les 96 œuvres pilotes Top 50 exclues (zéro suppression silencieuse)
    df_pilots_excluded = df_top50[df_top50["In_Pilot"] == "Oui"].copy()
    pilot_excl_csv = out_dir / "excluded_pilot_top50.csv"
    df_pilots_excluded.to_csv(pilot_excl_csv, index=False, lineterminator="\n")

    # 2. Générer la permutation complète reproductible dans chacune des 8 strates Top50_Block_5Y
    df_cand = df_top50[df_top50["In_Pilot"] != "Oui"].copy()
    rng = np.random.default_rng(SEED_V2)

    ordered_rows: list[dict] = []
    strata_summary: dict[str, dict] = {}
    for block in sorted(df_cand["Top50_Block_5Y"].dropna().unique()):
        sub = df_cand[df_cand["Top50_Block_5Y"] == block].sort_values(["First_Top50_Week", "Work_Slug"]).reset_index(drop=True)
        perm = rng.permutation(len(sub))
        strata_summary[block] = {
            "candidates_non_pilot_all_languages": int(len(sub)),
            "target_exploitable": TARGET_PER_STRATUM,
            "excluded_pilot_top50": int((df_pilots_excluded["Top50_Block_5Y"] == block).sum()),
        }
        for rank_order, idx in enumerate(perm, start=1):
            r = sub.iloc[int(idx)]
            ordered_rows.append({
                "Top50_Block_5Y": block,
                "Draw_Order": rank_order,
                "Work_Slug": r["Work_Slug"],
                "Artist_Slug": r["Artist_Slug"],
                "Artist": r["Artist"],
                "Title": r["Title"],
                "First_Top50_Week": r["First_Top50_Week"],
                "First_Top50_Year": int(r["First_Top50_Year"]),
                "Best_Rank": int(r["Best_Rank"]),
                "Disposition_Status": "PENDING",
                "Exclusion_Category": "",
                "Notes": "",
            })

    order_csv = out_dir / "stratified_candidate_order_v2.csv"
    with order_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ordered_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(ordered_rows)

    manifest = {
        "osf_registration_id": osf_id,
        "drawn_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": SEED_V2,
        "sampling_frame_file": "data/sampling_frame_v2/sampling_frame_works_1985_2024.csv",
        "sampling_frame_sha256": actual_sha,
        "target_per_stratum": TARGET_PER_STRATUM,
        "strata_summary": strata_summary,
        "sha256_outputs": {
            "stratified_candidate_order_v2.csv": hashlib.sha256(order_csv.read_bytes()).hexdigest(),
            "excluded_pilot_top50.csv": hashlib.sha256(pilot_excl_csv.read_bytes()).hexdigest(),
        },
    }
    manifest_json = out_dir / "draw_manifest_v2.json"
    manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
