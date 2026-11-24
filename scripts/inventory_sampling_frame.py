#!/usr/bin/env python3
"""
inventory_sampling_frame.py — Inventaire vérifiable de la base de sondage hebdomadaire
française (lescharts.com / SNEP Top Singles, 1985-2024) SANS procéder à aucun tirage aléatoire.

Sonde 1 semaine représentative par année (40 requêtes polies) afin de mesurer :
- la disponibilité HTTP des archives annuelles 1985-2024,
- le nombre exact de titres classés par semaine (profondeur Top 50 / Top 100 / Top 200),
- les années exactes de transition de profondeur.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USER_AGENT = "StatAssistant-Research/1.0 (https://github.com/MisterBlu1050/statassistant-2phases)"


def first_saturday_of_july(year: int) -> str:
    d = date(year, 7, 1)
    while d.weekday() != 5:  # Saturday
        d += timedelta(days=1)
    return d.isoformat()


def probe_year(year: int) -> dict:
    # Chercher la première semaine disponible début juillet (essayer samedi puis dimanche)
    d = date(year, 7, 1)
    for offset in range(7):
        cand = (d + timedelta(days=offset)).isoformat()
        url = f"https://lescharts.com/singles/{cand}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                # Nombre d'entrées classées = nombre unique de rangs / liens artistes dans le tableau principal
                # Chaque ligne du classement contient 1 lien /artiste/ dans le corps du tableau
                n_artist_links = len(re.findall(r'href="/artiste/[^"]+"', raw))
                n_song_hrefs = len(set(re.findall(r'href="(/chanson/[^"]+)"', raw)))
                if n_song_hrefs >= 20:
                    return {
                        "year": year,
                        "sample_week": cand,
                        "http_status": resp.status,
                        "chart_depth_songs": n_song_hrefs,
                        "artist_links": n_artist_links,
                    }
        except Exception:
            continue
    return {"year": year, "sample_week": None, "http_status": None, "chart_depth_songs": 0}


def main() -> int:
    rows = []
    for yr in range(1985, 2025):
        rows.append(probe_year(yr))
        time.sleep(0.25)

    out_path = Path(__file__).resolve().parent.parent / "docs" / "sampling_frame_inventory_1985_2024.json"
    out_path.write_text(json.dumps({"source": "lescharts.com (SNEP weekly singles archive)", "years": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Résumé par profondeur
    by_depth: dict[int, list[int]] = {}
    for r in rows:
        by_depth.setdefault(r["chart_depth_songs"], []).append(r["year"])
    print("Inventory saved to:", out_path)
    print("Years covered:", sum(1 for r in rows if r["chart_depth_songs"] > 0), "/ 40")
    for depth, yrs in sorted(by_depth.items()):
        print(f"  Depth {depth:3d}: {len(yrs):2d} years ({min(yrs)}-{max(yrs)}) -> {yrs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
