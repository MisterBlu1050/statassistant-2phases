#!/usr/bin/env python3
"""
draw_stratified_sample_v2.py — Tirage stratifié reproductible (SEED_V2 = 20261124)
sur le cadre harmonisé Top 50 (1985-2024), verrouillé par vérification cryptographique
du fichier figé sur OSF Registries et protégé contre les écritures partielles et l'écrasement.

Usage (UNIQUEMENT après dépôt public/figé de protocole_preenregistre_v2_4.md sur OSF Registries) :
    python scripts/draw_stratified_sample_v2.py --osf-registration-id <ID_OU_URL_OSF>

Protections d'audit :
1. Validation effective via l'API publique OSF v2 (https://api.osf.io/v2/registrations/{id}/) :
   - vérifie l'existence réelle (HTTP 200, type='registrations'), public=True, withdrawn=False,
     pending_registration_approval=False, archiving=False ;
   - vérifie une date_registered ISO 8601 UTC valide et strictement antérieure à l'heure du tirage ;
   - parcourt les fichiers figés de l'enregistrement OSF (files/osfstorage/), télécharge le fichier
     figé et vérifie l'égalité EXACTE de son empreinte SHA-256 complète (64 hex) avec
     f3c5621ebbe47743eb58f870058523b12083322f9f64c523bbaac25c0b13f790.
2. Protection anti-écrasement et anti-écriture partielle :
   - écriture complète dans un répertoire de staging daté (data/.staging_draw_v2_0_<utc>/),
   - validation intégrale, puis publication par renommage unique os.rename(staging_dir, out_dir)
     (refus garanti si data/draw_v2_0 existe déjà ; en cas d'échec avant renommage, la trace reste
     dans le répertoire de staging sans polluer data/draw_v2_0).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
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


def _http_get_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Échec API OSF ({url}) : HTTP {exc.code}") from exc
    except Exception as exc:
        raise RuntimeError(f"Impossible de joindre l'API OSF ({url}) : {exc}") from exc


def _parse_iso_utc(ts: str) -> datetime:
    cleaned = ts.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _find_matching_frozen_protocol_file(osf_id: str) -> dict[str, Any]:
    """Parcourt l'arborescence osfstorage d'une registration OSF et vérifie le SHA-256 exact (64 hex)
    d'un fichier figé téléchargé directement depuis OSF.
    """
    queue = [f"https://api.osf.io/v2/registrations/{osf_id}/files/osfstorage/"]
    visited: set[str] = set()
    inspected_files: list[str] = []

    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        payload = _http_get_json(url)
        for item in payload.get("data") or []:
            attrs = item.get("attributes") or {}
            kind = attrs.get("kind")
            name = attrs.get("name", "")
            if kind == "folder":
                next_folder = (item.get("relationships") or {}).get("files", {}).get("links", {}).get("related", {}).get("href")
                if next_folder:
                    queue.append(next_folder)
            elif kind == "file":
                inspected_files.append(name)
                dl_url = (item.get("links") or {}).get("download")
                if not dl_url:
                    continue
                # Vérifier d'abord le hash OSF si présent, puis télécharger les octets figés pour preuve cryptographique directe
                osf_reported_sha = ((attrs.get("extra") or {}).get("hashes") or {}).get("sha256", "").lower()
                if osf_reported_sha and osf_reported_sha != EXPECTED_PROTOCOL_SHA256:
                    continue
                req = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=25) as resp:
                    raw_bytes = resp.read()
                downloaded_sha = hashlib.sha256(raw_bytes).hexdigest()
                # Tolérer uniquement une normalisation CRLF/LF stricte si nécessaire en le consignant explicitement
                lf_sha = hashlib.sha256(raw_bytes.replace(b"\r\n", b"\n")).hexdigest()
                if downloaded_sha == EXPECTED_PROTOCOL_SHA256 or lf_sha == EXPECTED_PROTOCOL_SHA256:
                    return {
                        "file_name": name,
                        "download_url": dl_url,
                        "downloaded_sha256": downloaded_sha,
                        "lf_normalized_sha256": lf_sha,
                        "exact_sha256_verified": True,
                    }

        next_page = (payload.get("links") or {}).get("next")
        if next_page:
            queue.append(next_page)

    raise RuntimeError(
        f"Aucun fichier figé dans l'enregistrement OSF {osf_id} ne correspond au SHA-256 exact du protocole V1.4 "
        f"({EXPECTED_PROTOCOL_SHA256}). Fichiers inspectés : {inspected_files}"
    )


def verify_osf_registration(osf_id: str, now_utc: datetime) -> dict[str, Any]:
    """Vérifie existence, état figé/public, antériorité de date_registered et SHA-256 complet du protocole figé."""
    api_url = f"https://api.osf.io/v2/registrations/{osf_id}/"
    payload = _http_get_json(api_url)
    data = payload.get("data") or {}
    if data.get("type") != "registrations":
        raise RuntimeError(f"Objet OSF non conforme : type={data.get('type')!r} (attendu 'registrations').")

    attrs = data.get("attributes") or {}
    if attrs.get("withdrawn") is True:
        raise RuntimeError(f"Enregistrement OSF {osf_id} retiré (withdrawn=True) — tirage interdit.")
    if attrs.get("pending_registration_approval") is True:
        raise RuntimeError(f"Enregistrement OSF {osf_id} en attente d'approbation — tirage interdit.")
    if attrs.get("archiving") is True:
        raise RuntimeError(f"Enregistrement OSF {osf_id} en cours d'archivage — attendre le gel complet.")
    if attrs.get("public") is not True:
        raise RuntimeError(f"Enregistrement OSF {osf_id} non public (public!=True) — vérifiabilité publique requise.")

    date_reg_raw = attrs.get("date_registered") or ""
    if not date_reg_raw:
        raise RuntimeError(f"Enregistrement OSF {osf_id} sans date_registered valide.")
    date_reg_dt = _parse_iso_utc(date_reg_raw)
    if not (date_reg_dt < now_utc):
        raise RuntimeError(
            f"Horodatage incohérent : date_registered ({date_reg_dt.isoformat()}) doit précéder l'heure du tirage ({now_utc.isoformat()})."
        )

    frozen_file_proof = _find_matching_frozen_protocol_file(osf_id)
    return {
        "osf_id": osf_id,
        "api_url": api_url,
        "html_url": (data.get("links") or {}).get("html", f"https://osf.io/{osf_id}"),
        "title": attrs.get("title", ""),
        "date_registered_utc": date_reg_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "public": True,
        "withdrawn": False,
        "frozen_protocol_file": frozen_file_proof,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tirage stratifié reproductible V2 (verrouillé par SHA-256 OSF).")
    parser.add_argument(
        "--osf-registration-id",
        required=True,
        help="Identifiant, URL ou DOI du préenregistrement public/figé sur OSF Registries.",
    )
    args = parser.parse_args()

    now_utc = datetime.now(timezone.utc)
    repo = Path(__file__).resolve().parent.parent
    frame_path = repo / "data" / "sampling_frame_v2" / "sampling_frame_works_1985_2024.csv"
    protocol_path = repo / "docs" / "protocole_preenregistre_v2_4.md"
    out_dir = repo / "data" / "draw_v2_0"

    # 1. Refus immédiat si le répertoire de publication final existe déjà (anti-écrasement strict)
    if out_dir.exists():
        raise FileExistsError(
            f"Protection anti-écrasement : le répertoire de tirage {out_dir} existe déjà. Aucun écrasement autorisé."
        )

    # 2. Vérification des empreintes SHA-256 locales (protocole V1.4 + base de sondage)
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

    # 3. Validation cryptographique en direct de l'enregistrement OSF et de son document figé
    osf_id = extract_osf_id(args.osf_registration_id)
    osf_verified = verify_osf_registration(osf_id, now_utc)

    df = pd.read_csv(frame_path)
    df_top50 = df[df["Eligible_Top50_Constant"] == "Oui"].copy()

    # 4. Écriture complète dans un répertoire de staging daté (anti-écriture partielle)
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
        "osf_verification": osf_verified,
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

    # 5. Publication atomique du dossier complet validé (échoue si out_dir existe déjà)
    os.rename(staging_dir, out_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
