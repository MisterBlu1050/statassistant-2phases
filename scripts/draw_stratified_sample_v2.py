#!/usr/bin/env python3
"""
draw_stratified_sample_v2.py — Tirage stratifié reproductible (SEED_V2 = 20261124)
sur le cadre harmonisé Top 50 (1985-2024), verrouillé par vérification cryptographique
de la GitHub Release figée (protocol-v1.4-freeze) et protégé contre tout écrasement.

Usage :
    python scripts/draw_stratified_sample_v2.py --github-release-tag protocol-v1.4-freeze

Protections d'audit :
1. Validation effective en direct via l'API publique GitHub Releases :
   - vérifie l'existence réelle de la release (HTTP 200, draft=False) ;
   - vérifie que published_at (ISO 8601 UTC) est strictement antérieur à l'heure du tirage ;
   - télécharge la pièce jointe figée protocole_preenregistre_v2_4.md depuis la GitHub Release
     et vérifie l'identité EXACTE octet par octet (64 hex) avec EXPECTED_PROTOCOL_SHA256.
2. Vérifie l'empreinte SHA-256 exacte de sampling_frame_works_1985_2024.csv et du protocole local.
3. Protection anti-écrasement et anti-écriture partielle :
   - écriture complète dans un répertoire de staging daté (data/.staging_draw_v2_0_<utc>/),
   - publication unique par os.rename(staging_dir, out_dir) (refus immédiat si data/draw_v2_0 existe).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SEED_V2 = 20261124
GITHUB_REPO = "MisterBlu1050/statassistant-2phases"
EXPECTED_FRAME_SHA256 = "668a448dac68299cc5431868d21f983f3dfb5904de8d857b1de070a5efc2f115"
EXPECTED_PROTOCOL_SHA256 = "4b51d09f104d68046dac6b93e31569b9453e09e5efc30e02ef41cc9b8744438e"
TARGET_PER_STRATUM = 250
USER_AGENT = "StatAssistant-Research/1.0 (https://github.com/MisterBlu1050/statassistant-2phases)"


def _http_get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Échec API GitHub ({url}) : HTTP {exc.code}") from exc
    except Exception as exc:
        raise RuntimeError(f"Impossible de joindre l'API GitHub ({url}) : {exc}") from exc


def _parse_iso_utc(ts: str) -> datetime:
    cleaned = ts.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def verify_github_release_freeze(tag: str, now_utc: datetime) -> dict[str, Any]:
    """Vérifie existence, non-brouillon, antériorité et SHA-256 exact octet par octet de la GitHub Release."""
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{tag}"
    rel = _http_get_json(api_url)

    if rel.get("draft") is True:
        raise RuntimeError(f"La GitHub Release {tag} est encore en brouillon (draft=True) — tirage interdit.")
    pub_raw = rel.get("published_at") or ""
    if not pub_raw:
        raise RuntimeError(f"La GitHub Release {tag} ne possède pas de date published_at valide.")
    pub_dt = _parse_iso_utc(pub_raw)
    if not (pub_dt < now_utc):
        raise RuntimeError(
            f"Horodatage incohérent : published_at ({pub_dt.isoformat()}) doit précéder le tirage ({now_utc.isoformat()})."
        )

    assets = rel.get("assets") or []
    asset_proof: dict[str, Any] | None = None
    for asset in assets:
        if asset.get("name") == "protocole_preenregistre_v2_4.md":
            dl_url = asset.get("browser_download_url")
            if not dl_url:
                continue
            req = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw_bytes = resp.read()
            dl_sha = hashlib.sha256(raw_bytes).hexdigest()
            if dl_sha != EXPECTED_PROTOCOL_SHA256:
                raise RuntimeError(
                    f"SHA-256 de l'asset figé sur GitHub Release divergent ! Attendu {EXPECTED_PROTOCOL_SHA256}, trouvé {dl_sha}"
                )
            asset_proof = {
                "asset_name": asset["name"],
                "download_url": dl_url,
                "downloaded_sha256": dl_sha,
                "exact_byte_identity": True,
            }
            break

    if asset_proof is None:
        raise RuntimeError(
            f"L'asset figé 'protocole_preenregistre_v2_4.md' est introuvable dans la GitHub Release {tag}."
        )

    return {
        "freeze_type": "github_release_annotated_tag",
        "repo": GITHUB_REPO,
        "tag": tag,
        "release_url": rel.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/tag/{tag}"),
        "published_at_utc": pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "frozen_protocol_asset": asset_proof,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tirage stratifié reproductible V2 (verrouillé par GitHub Release).")
    parser.add_argument(
        "--github-release-tag",
        required=True,
        help="Tag de la GitHub Release figée avant tirage (ex. protocol-v1.4-freeze).",
    )
    args = parser.parse_args()

    now_utc = datetime.now(timezone.utc)
    repo = Path(__file__).resolve().parent.parent
    frame_path = repo / "data" / "sampling_frame_v2" / "sampling_frame_works_1985_2024.csv"
    protocol_path = repo / "docs" / "protocole_preenregistre_v2_4.md"
    out_dir = repo / "data" / "draw_v2_0"

    # 1. Protection anti-écrasement stricte
    if out_dir.exists():
        raise FileExistsError(
            f"Protection anti-écrasement : le répertoire de tirage {out_dir} existe déjà. Aucun écrasement autorisé."
        )

    # 2. Vérification des empreintes SHA-256 locales (protocole + base de sondage)
    actual_proto_sha = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    if actual_proto_sha != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError(f"SHA-256 du protocole local modifié ! Attendu {EXPECTED_PROTOCOL_SHA256}, trouvé {actual_proto_sha}")

    actual_frame_sha = hashlib.sha256(frame_path.read_bytes()).hexdigest()
    if actual_frame_sha != EXPECTED_FRAME_SHA256:
        raise RuntimeError(f"SHA-256 de la base modifié ! Attendu {EXPECTED_FRAME_SHA256}, trouvé {actual_frame_sha}")

    # 3. Vérification en direct de la GitHub Release figée
    release_verified = verify_github_release_freeze(args.github_release_tag.strip(), now_utc)

    df = pd.read_csv(frame_path)
    df_top50 = df[df["Eligible_Top50_Constant"] == "Oui"].copy()

    # 4. Écriture dans un répertoire de staging daté (anti-écriture partielle)
    stamp = now_utc.strftime("%Y%m%dT%H%M%SZ")
    staging_dir = repo / "data" / f".staging_draw_v2_0_{stamp}"
    staging_dir.mkdir(parents=True, exist_ok=False)

    df_pilots_excluded = df_top50[df_top50["In_Pilot"] == "Oui"].copy()
    pilot_excl_csv = staging_dir / "excluded_pilot_top50.csv"
    with pilot_excl_csv.open("x", encoding="utf-8", newline="") as f:
        df_pilots_excluded.to_csv(f, index=False, lineterminator="\n")

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

    order_csv = staging_dir / "stratified_candidate_order_v2.csv"
    with order_csv.open("x", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ordered_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(ordered_rows)

    manifest = {
        "freeze_verification": release_verified,
        "drawn_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    manifest_json = staging_dir / "draw_manifest_v2.json"
    with manifest_json.open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2))

    # 5. Publication atomique du dossier complet validé
    os.rename(staging_dir, out_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
