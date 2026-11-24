#!/usr/bin/env python3
"""
compile_sampling_frame_1985_2024.py — Compilation exhaustive et vérifiable de la base
de sondage hebdomadaire des singles classés en France (lescharts.com / SNEP, 1985-2024),
SANS aucun tirage aléatoire et SANS téléchargement de paroles.

Produit dans data/sampling_frame_v2/ :
1. weeks_inventory_1985_2024.csv : inventaire semaine par semaine (date, statut HTTP,
   nb lignes, rang min/max, ex-aequo, profondeur officielle).
2. sampling_frame_works_1985_2024.csv : 1 ligne par œuvre canonique unique (/chanson/...),
   avec artiste, titre, première semaine d'entrée, bloc quinquennal, meilleur rang,
   nb semaines classées, éligibilité Top 50 constant, et drapeau In_Pilot.
3. frame_summary_1985_2024.json : synthèse exacte des effectifs par strate et transitions de profondeur.
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
    s = unicodedata.normalize("NFKD", html.unescape(text).lower())
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
    """Parcourt toutes les semaines officielles d'une année en suivant les liens de navigation."""
    weeks_meta: list[dict[str, Any]] = []
    entries: list[tuple[str, int, str, str, str, str]] = []  # (week, rank, work_slug, title, artist_slug, artist)

    curr = find_first_week_of_year(year)
    visited: set[str] = set()
    while curr and curr.startswith(f"{year}-") and curr not in visited:
        visited.add(curr)
        status, raw = fetch_week(curr)
        rows = ROW_RE.findall(raw) if status == 200 else []
        ranks = [int(r[0]) for r in rows]
        has_dup = len(ranks) != len(set(ranks))
        weeks_meta.append({
            "Week_Date": curr,
            "Year": year,
            "Block_5Y": block_5y(year),
            "HTTP_Status": status,
            "Rows_Parsed": len(rows),
            "Min_Rank": min(ranks) if ranks else 0,
            "Max_Rank": max(ranks) if ranks else 0,
            "Has_Tied_Ranks": "Oui" if has_dup else "Non",
        })
        for rk_s, w_slug, tit, a_slug, art in rows:
            entries.append((curr, int(rk_s), w_slug, html.unescape(tit).strip(), a_slug, html.unescape(art).strip()))

        # Chercher la semaine suivante strictement > curr dans les liens de navigation
        nav_dates = sorted(set(NAV_RE.findall(raw)))
        next_candidates = [dt for dt in nav_dates if dt > curr]
        curr = next_candidates[0] if next_candidates else None
        time.sleep(0.06)

    return weeks_meta, entries


def load_pilot_keys(pilot_sources_path: Path | None) -> set[tuple[str, str]]:
    if not pilot_sources_path or not pilot_sources_path.exists():
        return set()
    keys: set[tuple[str, str]] = set()
    with pilot_sources_path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            keys.add((norm_key(r["Artiste"]), norm_key(r["Titre"])))
    return keys


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    out_dir = repo_root / "data" / "sampling_frame_v2"
    out_dir.mkdir(parents=True, exist_ok=True)

    pilot_path = Path(r"C:\Users\Bibi\Downloads\corpus_musical_reel_sources.csv")
    pilot_keys = load_pilot_keys(pilot_path)

    all_weeks: list[dict[str, Any]] = []
    all_entries: list[tuple[str, int, str, str, str, str]] = []

    years = list(range(1985, 2025))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        fut_to_yr = {ex.submit(compile_single_year, yr): yr for yr in years}
        for fut in concurrent.futures.as_completed(fut_to_yr):
            yr = fut_to_yr[fut]
            w_meta, w_entries = fut.result()
            all_weeks.extend(w_meta)
            all_entries.extend(w_entries)

    all_weeks.sort(key=lambda r: r["Week_Date"])

    # Agréger par œuvre canonique unique (Work_Slug)
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
                "Best_Rank": rk,
                "Weeks_Charted": 1,
            }
        else:
            rec = works[w_slug]
            rec["Weeks_Charted"] += 1
            if w_date < rec["First_Week"]:
                rec["First_Week"] = w_date
                rec["First_Year"] = int(w_date[:4])
            if rk < rec["Best_Rank"]:
                rec["Best_Rank"] = rk

    works_rows = []
    for rec in sorted(works.values(), key=lambda r: (r["First_Week"], r["Best_Rank"], r["Work_Slug"])):
        in_pilot = (norm_key(rec["Artist"]), norm_key(rec["Title"])) in pilot_keys
        works_rows.append({
            **rec,
            "Block_5Y": block_5y(rec["First_Year"]),
            "Eligible_Top50_Constant": "Oui" if rec["Best_Rank"] <= 50 else "Non",
            "In_Pilot": "Oui" if in_pilot else "Non",
        })

    # Écriture CSV semaines
    weeks_csv = out_dir / "weeks_inventory_1985_2024.csv"
    with weeks_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["Week_Date", "Year", "Block_5Y", "HTTP_Status", "Rows_Parsed", "Min_Rank", "Max_Rank", "Has_Tied_Ranks"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(all_weeks)

    # Écriture CSV œuvres uniques
    works_csv = out_dir / "sampling_frame_works_1985_2024.csv"
    with works_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "Work_Slug", "Artist_Slug", "Artist", "Title", "First_Week", "First_Year",
                "Block_5Y", "Best_Rank", "Weeks_Charted", "Eligible_Top50_Constant", "In_Pilot",
            ],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(works_rows)

    # Synthèse JSON vérifiable
    weeks_per_year = dict(Counter(r["Year"] for r in all_weeks))
    depth_transitions = []
    prev_max = None
    for r in all_weeks:
        if r["Max_Rank"] != prev_max:
            depth_transitions.append({"Week_Date": r["Week_Date"], "Max_Rank": r["Max_Rank"], "Rows_Parsed": r["Rows_Parsed"]})
            prev_max = r["Max_Rank"]

    works_by_block = dict(Counter(r["Block_5Y"] for r in works_rows))
    top50_by_block = dict(Counter(r["Block_5Y"] for r in works_rows if r["Eligible_Top50_Constant"] == "Oui"))
    artist_counts = Counter(r["Artist_Slug"] for r in works_rows)

    summary = {
        "source": "lescharts.com (SNEP weekly singles archive, 1985-2024)",
        "total_weeks_compiled": len(all_weeks),
        "weeks_with_http_200": sum(1 for r in all_weeks if r["HTTP_Status"] == 200),
        "weeks_with_gaps_gt_7d": sum(
            1 for i in range(1, len(all_weeks))
            if (date.fromisoformat(all_weeks[i]["Week_Date"]) - date.fromisoformat(all_weeks[i - 1]["Week_Date"])).days > 7
        ),
        "min_weeks_in_a_year": min(weeks_per_year.values()) if weeks_per_year else 0,
        "max_weeks_in_a_year": max(weeks_per_year.values()) if weeks_per_year else 0,
        "total_distinct_works_all_languages": len(works_rows),
        "total_distinct_artists": len(artist_counts),
        "mean_works_per_artist": round(len(works_rows) / len(artist_counts), 3) if artist_counts else 0.0,
        "pilot_works_matched_in_frame": sum(1 for r in works_rows if r["In_Pilot"] == "Oui"),
        "works_by_block_all_languages": dict(sorted(works_by_block.items())),
        "works_top50_constant_by_block_all_languages": dict(sorted(top50_by_block.items())),
        "depth_transitions_first_15": depth_transitions[:15],
        "sha256": {
            "weeks_inventory_1985_2024.csv": hashlib.sha256(weeks_csv.read_bytes()).hexdigest(),
            "sampling_frame_works_1985_2024.csv": hashlib.sha256(works_csv.read_bytes()).hexdigest(),
        },
    }
    summary_json = out_dir / "frame_summary_1985_2024.json"
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
