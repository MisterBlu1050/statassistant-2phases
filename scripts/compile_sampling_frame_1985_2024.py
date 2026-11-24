#!/usr/bin/env python3
"""
compile_sampling_frame_1985_2024.py (v1.4) — Compilation exhaustive et vérifiable de la base
de sondage hebdomadaire des singles classés en France (lescharts.com / SNEP, 1985-2024),
SANS aucun tirage aléatoire et SANS téléchargement de paroles.

Améliorations v1.4 :
- Calcul exact de First_Top50_Week, First_Top50_Year, Top50_Block_5Y et Weeks_In_Top50
  (basés strictement sur les semaines où rank <= 50, indépendamment de la première entrée #51-#200).
- Manifeste pilote versionné dans le dépôt (data/sampling_frame_v2/pilot_manifest_131.csv),
  aucun chemin local Windows, avec vérification obligatoire et export pilot_matching_audit.csv.
- Comptage explicite des rangs manquants amont dans weeks_inventory_1985_2024.csv
  (Missing_Top50_Ranks et Missing_Total_Ranks).
"""

from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

USER_AGENT = "StatAssistant-Research/1.0 (https://github.com/MisterBlu1050/statassistant-2phases)"

ROW_RE = re.compile(
    r'<li\s+class="row[^"]*"[^>]*>.*?'
    r'<span\s+class="rk">(\d+)</span>.*?'
    r'<a\s+class="t"\s+href="(/chanson/[^"]+)">([^<]+)</a>.*?'
    r'<a\s+class="a-link"\s+href="(/artiste/[^"]+)">([^<]+)</a>',
    re.S,
)
NAV_RE = re.compile(r'href="/singles/(\d{4}-\d{2}-\d{2})"')


def block_5y(year: int) -> str:
    start = 1985 + ((year - 1985) // 5) * 5
    return f"{start}-{start + 4}"


def norm_key(text: str) -> str:
    s = html.unescape(text).lower().replace("œ", "oe").replace("æ", "ae")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def fetch_week(week_date: str, max_retries: int = 4) -> tuple[int, str]:
    url = f"https://lescharts.com/singles/{week_date}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status, resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            return exc.code, ""
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            return 0, ""
    return 0, ""


def find_first_week_of_year(year: int) -> str | None:
    d = date(year, 1, 1)
    for offset in range(14):
        cand = (d + timedelta(days=offset)).isoformat()
        status, raw = fetch_week(cand)
        if status == 200 and len(ROW_RE.findall(raw)) >= 20:
            return cand
        time.sleep(0.05)
    return None


def compile_single_year(year: int) -> tuple[list[dict[str, Any]], list[tuple[str, int, str, str, str, str]]]:
    weeks_meta: list[dict[str, Any]] = []
    entries: list[tuple[str, int, str, str, str, str]] = []

    curr = find_first_week_of_year(year)
    visited: set[str] = set()
    while curr and curr.startswith(f"{year}-") and curr not in visited:
        visited.add(curr)
        status, raw = fetch_week(curr)
        rows = ROW_RE.findall(raw) if status == 200 else []
        ranks = [int(r[0]) for r in rows]
        rank_set = set(ranks)
        max_rk = max(ranks) if ranks else 0
        miss_top50 = sum(1 for r in range(1, min(50, max_rk) + 1) if r not in rank_set) if max_rk else 50
        miss_total = sum(1 for r in range(1, max_rk + 1) if r not in rank_set) if max_rk else 0
        weeks_meta.append({
            "Week_Date": curr,
            "Year": year,
            "Block_5Y": block_5y(year),
            "HTTP_Status": status,
            "Rows_Parsed": len(rows),
            "Min_Rank": min(ranks) if ranks else 0,
            "Max_Rank": max_rk,
            "Has_Tied_Ranks": "Oui" if len(ranks) != len(rank_set) else "Non",
            "Missing_Top50_Ranks": miss_top50,
            "Missing_Total_Ranks": miss_total,
        })
        for rk_s, w_slug, tit, a_slug, art in rows:
            entries.append((curr, int(rk_s), w_slug, html.unescape(tit).strip(), a_slug, html.unescape(art).strip()))

        nav_dates = sorted(set(NAV_RE.findall(raw)))
        next_candidates = [dt for dt in nav_dates if dt > curr]
        curr = next_candidates[0] if next_candidates else None
        time.sleep(0.06)

    return weeks_meta, entries


def load_versioned_pilot_manifest(manifest_path: Path) -> list[dict[str, str]]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifeste pilote versionné introuvable : {manifest_path}")
    with manifest_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 131:
        raise ValueError(f"Manifeste pilote invalide : attendu 131 lignes, trouvé {len(rows)}")
    return rows


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    out_dir = repo_root / "data" / "sampling_frame_v2"
    out_dir.mkdir(parents=True, exist_ok=True)

    pilot_manifest_path = out_dir / "pilot_manifest_131.csv"
    pilot_rows = load_versioned_pilot_manifest(pilot_manifest_path)
    pilot_key_to_id = {(norm_key(r["Artiste"]), norm_key(r["Titre"])): int(r["LRCLIB_ID"]) for r in pilot_rows}

    all_weeks: list[dict[str, Any]] = []
    all_entries: list[tuple[str, int, str, str, str, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        fut_to_yr = {ex.submit(compile_single_year, yr): yr for yr in range(1985, 2025)}
        for fut in concurrent.futures.as_completed(fut_to_yr):
            w_meta, w_entries = fut.result()
            all_weeks.extend(w_meta)
            all_entries.extend(w_entries)

    all_weeks.sort(key=lambda r: r["Week_Date"])

    # Agréger par œuvre canonique unique (Work_Slug) avec First_Top50_Week exact
    works: dict[str, dict[str, Any]] = {}
    for w_date, rk, w_slug, tit, a_slug, art in all_entries:
        if w_slug not in works:
            works[w_slug] = {
                "Work_Slug": w_slug,
                "Artist_Slug": a_slug,
                "Artist": art,
                "Title": tit,
                "First_Week": w_date,
                "First_Year": int(w_date[:4]),
                "First_Top50_Week": w_date if rk <= 50 else "",
                "First_Top50_Year": int(w_date[:4]) if rk <= 50 else "",
                "Best_Rank": rk,
                "Weeks_Charted": 1,
                "Weeks_In_Top50": 1 if rk <= 50 else 0,
            }
        else:
            rec = works[w_slug]
            rec["Weeks_Charted"] += 1
            if w_date < rec["First_Week"]:
                rec["First_Week"] = w_date
                rec["First_Year"] = int(w_date[:4])
            if rk < rec["Best_Rank"]:
                rec["Best_Rank"] = rk
            if rk <= 50:
                rec["Weeks_In_Top50"] += 1
                if not rec["First_Top50_Week"] or w_date < rec["First_Top50_Week"]:
                    rec["First_Top50_Week"] = w_date
                    rec["First_Top50_Year"] = int(w_date[:4])

    matched_pilot_ids: dict[int, str] = {}
    works_rows = []
    for rec in sorted(works.values(), key=lambda r: (r["First_Week"], r["Best_Rank"], r["Work_Slug"])):
        pkey = (norm_key(rec["Artist"]), norm_key(rec["Title"]))
        pid = pilot_key_to_id.get(pkey)
        if pid is not None:
            matched_pilot_ids[pid] = rec["Work_Slug"]
        t50_block = block_5y(int(rec["First_Top50_Year"])) if rec["First_Top50_Year"] != "" else ""
        works_rows.append({
            **rec,
            "Block_5Y": block_5y(rec["First_Year"]),
            "Top50_Block_5Y": t50_block,
            "Eligible_Top50_Constant": "Oui" if rec["Best_Rank"] <= 50 else "Non",
            "In_Pilot": "Oui" if pid is not None else "Non",
            "Pilot_LRCLIB_ID": pid if pid is not None else "",
        })

    # Audit explicite des 131 correspondances pilotes
    pilot_audit_csv = out_dir / "pilot_matching_audit.csv"
    with pilot_audit_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["LRCLIB_ID", "Genre_Musical", "Annee", "Artiste", "Titre", "Matched_In_Frame", "Matched_Work_Slug"])
        for r in pilot_rows:
            pid = int(r["LRCLIB_ID"])
            slug = matched_pilot_ids.get(pid, "")
            w.writerow([pid, r["Genre_Musical"], r["Annee"], r["Artiste"], r["Titre"], "Oui" if slug else "Non", slug])

    weeks_csv = out_dir / "weeks_inventory_1985_2024.csv"
    with weeks_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "Week_Date", "Year", "Block_5Y", "HTTP_Status", "Rows_Parsed",
                "Min_Rank", "Max_Rank", "Has_Tied_Ranks", "Missing_Top50_Ranks", "Missing_Total_Ranks",
            ],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(all_weeks)

    works_csv = out_dir / "sampling_frame_works_1985_2024.csv"
    with works_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "Work_Slug", "Artist_Slug", "Artist", "Title",
                "First_Week", "First_Year", "Block_5Y",
                "First_Top50_Week", "First_Top50_Year", "Top50_Block_5Y",
                "Best_Rank", "Weeks_Charted", "Weeks_In_Top50",
                "Eligible_Top50_Constant", "In_Pilot", "Pilot_LRCLIB_ID",
            ],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(works_rows)

    works_by_block = dict(sorted(Counter(r["Block_5Y"] for r in works_rows).items()))
    top50_by_top50_block = dict(sorted(Counter(r["Top50_Block_5Y"] for r in works_rows if r["Top50_Block_5Y"]).items()))
    shifted_block_count = sum(
        1 for r in works_rows if r["Top50_Block_5Y"] and r["Top50_Block_5Y"] != r["Block_5Y"]
    )
    artist_counts = Counter(r["Artist_Slug"] for r in works_rows)

    summary = {
        "version": "1.4",
        "source": "lescharts.com (SNEP weekly singles archive, 1985-2024)",
        "total_weeks_compiled": len(all_weeks),
        "weeks_with_http_200": sum(1 for r in all_weeks if r["HTTP_Status"] == 200),
        "weeks_with_missing_top50_ranks": sum(1 for r in all_weeks if r["Missing_Top50_Ranks"] > 0),
        "total_distinct_works_all_languages": len(works_rows),
        "total_distinct_top50_works_all_languages": sum(1 for r in works_rows if r["Eligible_Top50_Constant"] == "Oui"),
        "top50_works_shifted_block_by_First_Top50_Week": shifted_block_count,
        "total_distinct_artists": len(artist_counts),
        "mean_works_per_artist": round(len(works_rows) / len(artist_counts), 3),
        "pilot_manifest_total": len(pilot_rows),
        "pilot_works_matched_in_frame": len(matched_pilot_ids),
        "works_by_block_all_languages": works_by_block,
        "works_top50_by_First_Top50_Block_all_languages": top50_by_top50_block,
        "sha256": {
            "pilot_manifest_131.csv": hashlib.sha256(pilot_manifest_path.read_bytes()).hexdigest(),
            "weeks_inventory_1985_2024.csv": hashlib.sha256(weeks_csv.read_bytes()).hexdigest(),
            "sampling_frame_works_1985_2024.csv": hashlib.sha256(works_csv.read_bytes()).hexdigest(),
            "pilot_matching_audit.csv": hashlib.sha256(pilot_audit_csv.read_bytes()).hexdigest(),
        },
    }
    (out_dir / "frame_summary_1985_2024.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
