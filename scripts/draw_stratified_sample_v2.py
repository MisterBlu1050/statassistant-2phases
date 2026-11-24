#!/usr/bin/env python3
"""
draw_stratified_sample_v2.py — Tirage stratifié reproductible (SEED_V2 = 20261124)
sur le cadre harmonisé Top 50 (1985-2024), verrouillé jusqu'à validation effective
de l'enregistrement OSF Registries et protégé contre tout écrasement.

Usage (UNIQUEMENT après dépôt public/figé sur OSF Registries) :
    python scripts/draw_stratified_sample_v2.py --osf-registration-id <ID_OU_URL_OSF>

Protections d'audit :
1. Validation effective via l'API publique OSF v2 (https://api.osf.io/v2/registrations/{id}/) :
   - vérifie l'existence réelle de l'enregistrement (HTTP 200, type='registrations'),
   - vérifie qu'il est figé et actif (withdrawn=False, pending_registration_approval=False),
   - vérifie la correspondance avec le protocole V1.4 (empreinte SHA-256 du protocole ou commit 8871cbf / graine 20261124).
2. Protection stricte contre l'écrasement :
   - refuse de s'exécuter si un fichier de tirage existe déjà dans data/draw_v2_0/,
   - utilise l'ouverture exclusive 'x' au niveau OS (FileExistsError garanti).
3. Vérifie l'empreinte SHA-256 exacte de sampling_frame_works_1985_2024.csv et de protocole_preenregistre_v2_4.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SEED_V2 = 20261124
EXPECTED_FRAME_SHA256 = "668a448dac68299cc5431868d21f983f3dfb5904de8d857b1de070a5efc2f115"
EXPECTED_PROTOCOL_SHA256 = "f3c5621ebbe47743eb58f870058523b12083322f9f64c523bbaac25c0b13f790"
EXPECTED_PROTOCOL_MARKERS = (EXPECTED_PROTOCOL_SHA256[:16], "8871cbf", "20261124")
TARGET_PER_STRATUM = 250
USER_AGENT = "StatAssistant-Research/1.0 (https://github.com/MisterBlu1050/statassistant-2phases)"


def extract_osf_id(raw_value: str) -> str:
    val = raw_value.strip().rstrip("/")
    m = re.search(r"(?:osf\.io(?:/registrations)?/|OSF\.IO/)([A-Za-z0-9]{5,10})$", val, re.I)
    if m:
        return m.group(1).lower()
    if re.fullmatch(r"[A-Za-z0-9]{5,10}", val):
        return val.lower()
    raise ValueError(
        f"Identifiant OSF invalide ({raw_value!r}) : fournir un identifiant OSF (ex. 'abcde') ou une URL/DOI osf.io."
    )


def verify_osf_registration(osf_id: str) -> dict[str, Any]:
    """Vérifie en direct auprès de l'API publique OSF v2 l'existence, le gel et la correspondance du préenregistrement."""
    api_url = f"https://api.osf.io/v2/registrations/{osf_id}/"
    req = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Échec de validation OSF ({api_url}) : HTTP {exc.code}") from exc
    except Exception as exc:
        raise RuntimeError(f"Impossible de joindre l'API OSF ({api_url}) : {exc}") from exc

    data = payload.get("data") or {}
    if data.get("type") != "registrations":
        raise RuntimeError(f"Objet OSF non conforme : type={data.get('type')!r} (attendu 'registrations').")

    attrs = data.get("attributes") or {}
    if attrs.get("withdrawn") is True:
        raise RuntimeError(f"Enregistrement OSF {osf_id} retiré (withdrawn=True) — tirage interdit.")
    if attrs.get("pending_registration_approval") is True:
        raise RuntimeError(f"Enregistrement OSF {osf_id} encore en attente d'approbation — tirage interdit.")
    if attrs.get("archiving") is True:
        raise RuntimeError(f"Enregistrement OSF {osf_id} en cours d'archivage — attendre le gel complet.")

    # Vérifier la correspondance avec le protocole figé dans le texte/métadonnées de l'enregistrement OSF
    searchable = json.dumps(attrs, ensure_ascii=False).lower()
    matched_markers = [mk for mk in EXPECTED_PROTOCOL_MARKERS if mk.lower() in searchable]
    if not matched_markers:
        raise RuntimeError(
            f"Enregistrement OSF {osf_id} trouvé mais aucun marqueur de correspondance du protocole v1.4 "
            f"({EXPECTED_PROTOCOL_MARKERS}) n'a été détecté dans ses métadonnées/description."
        )

    return {
        "osf_id": osf_id,
        "api_url": api_url,
        "html_url": (data.get("links") or {}).get("html", f"https://osf.io/{osf_id}"),
        "title": attrs.get("title", ""),
        "date_registered": attrs.get("date_registered", ""),
        "public": attrs.get("public", False),
        "withdrawn": attrs.get("withdrawn", False),
        "matched_protocol_markers": matched_markers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tirage stratifié reproductible V2 (verrouillé par validation OSF).")
    parser.add_argument(
        "--osf-registration-id",
        required=True,
        help="Identifiant, URL ou DOI du préenregistrement public/figé sur OSF Registries.",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    frame_path = repo / "data" / "sampling_frame_v2" / "sampling_frame_works_1985_2024.csv"
    protocol_path = repo / "docs" / "protocole_preenregistre_v2_4.md"
    out_dir = repo / "data" / "draw_v2_0"

    # 1. Protection stricte contre tout écrasement (vérification préalable avant tout appel réseau)
    target_files = [
        out_dir / "stratified_candidate_order_v2.csv",
        out_dir / "excluded_pilot_top50.csv",
        out_dir / "draw_manifest_v2.json",
    ]
    existing = [p for p in target_files if p.exists()]
    if existing:
        raise FileExistsError(
            "Protection anti-écrasement : un tirage existe déjà dans data/draw_v2_0/ "
            f"({', '.join(p.name for p in existing)}). Aucun écrasement autorisé."
        )

    # 2. Vérification des empreintes SHA-256 locales (protocole + base de sondage)
    if not protocol_path.exists():
        raise FileNotFoundError(f"Protocole V1.4 introuvable : {protocol_path}")
    actual_proto_sha = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    if actual_proto_sha != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError(f"SHA-256 du protocole modifié ! Attendu {EXPECTED_PROTOCOL_SHA256}, trouvé {actual_proto_sha}")

    if not frame_path.exists():
        raise FileNotFoundError(f"Base de sondage introuvable : {frame_path}")
    actual_frame_sha = hashlib.sha256(frame_path.read_bytes()).hexdigest()
    if actual_frame_sha != EXPECTED_FRAME_SHA256:
        raise RuntimeError(f"SHA-256 de la base modifié ! Attendu {EXPECTED_FRAME_SHA256}, trouvé {actual_frame_sha}")

    # 3. Validation effective en direct de l'enregistrement OSF
    osf_id = extract_osf_id(args.osf_registration_id)
    osf_verified = verify_osf_registration(osf_id)

    df = pd.read_csv(frame_path)
    df_top50 = df[df["Eligible_Top50_Constant"] == "Oui"].copy()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 4. Écriture exclusive ('x') des 96 œuvres pilotes Top 50 exclues
    df_pilots_excluded = df_top50[df_top50["In_Pilot"] == "Oui"].copy()
    pilot_excl_csv = out_dir / "excluded_pilot_top50.csv"
    with pilot_excl_csv.open("x", encoding="utf-8", newline="") as f:
        df_pilots_excluded.to_csv(f, index=False, lineterminator="\n")

    # 5. Permutation complète reproductible dans chacune des 8 strates Top50_Block_5Y (graine 20261124)
    df_cand = df_top50[df_top50["In_Pilot"] != "Oui"].copy()
    rng = np.random.default_rng(SEED_V2)

    ordered_rows: list[dict[str, Any]] = []
    strata_summary: dict[str, dict[str, int]] = {}
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
    with order_csv.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ordered_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(ordered_rows)

    manifest = {
        "osf_verification": osf_verified,
        "drawn_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": SEED_V2,
        "protocol_file": "docs/protocole_preenregistre_v2_4.md",
        "protocol_sha256": actual_proto_sha,
        "sampling_frame_file": "data/sampling_frame_v2/sampling_frame_works_1985_2024.csv",
        "sampling_frame_sha256": actual_frame_sha,
        "target_per_stratum": TARGET_PER_STRATUM,
        "strata_summary": strata_summary,
        "sha256_outputs": {
            "stratified_candidate_order_v2.csv": hashlib.sha256(order_csv.read_bytes()).hexdigest(),
            "excluded_pilot_top50.csv": hashlib.sha256(pilot_excl_csv.read_bytes()).hexdigest(),
        },
    }
    manifest_json = out_dir / "draw_manifest_v2.json"
    with manifest_json.open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
