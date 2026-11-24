#!/usr/bin/env python3
"""
collect_corpus_v2.py — Collecte contrôlée, résumable et auditable du Corpus V2 (1985-2024)
dans l'ordre exact Draw_Order = 1, 2, 3... de data/draw_v2_0/stratified_candidate_order_v2.csv.

Garanties scientifiques et juridiques :
- Vérifie l'empreinte SHA-256 exacte de stratified_candidate_order_v2.csv (ne le modifie jamais).
- Ne stocke ni ne redistribue aucune parole protégée (uniquement métriques dérivées + Lyrics_SHA256 + LRCLIB_ID).
- Enregistre chaque décision dans disposition_log.csv (zéro suppression silencieuse ; cas ambigus en PENDING_HUMAN_REVIEW).
- Fige les versions exactes des outils dans environment_lock.json et trace chaque requête dans ingestion_log.jsonl.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import simplemma
from lingua import Language, LanguageDetectorBuilder

EXPECTED_DRAW_ORDER_SHA256 = "dbe027644b62b39e513e6455d02424efb19f17a1e9e89f0b529a611bbee6d4e1"
USER_AGENT = "StatAssistant-Research/1.0 (https://github.com/MisterBlu1050/statassistant-2phases)"

APOSTROPHE_TRANS = str.maketrans({
    "\u2019": "'",
    "\u2018": "'",
    "\u02bc": "'",
    "\u2032": "'",
    "`": "'",
})
WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿŒœŸ]+(?:'[A-Za-zÀ-ÖØ-öø-ÿŒœŸ]+)?")
NUM_RE = re.compile(r"\b\d+\b")
ABBREV_CHORUS_RE = re.compile(r"\[[^\]]*(?:refrain|chorus)[^\]]*(?:x\s*\d|\d\s*x)[^\]]*\]|\(\s*(?:refrain|chorus)\s*x\s*\d+\s*\)", re.I)
PROCLITIC_RE = re.compile(r"^(?:l|d|c|j|n|m|t|s|qu)'(.+)$")


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text).translate(APOSTROPHE_TRANS)


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(normalize_text(text))]


def lemmatize_fr_tokens(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for tok in tokens:
        m = PROCLITIC_RE.match(tok)
        core = m.group(1) if m else tok
        out.append(simplemma.lemmatize(core, lang="fr").lower())
    return out


def compute_mattr(tokens: list[str], window: int) -> float | None:
    n = len(tokens)
    if n < window or window <= 0:
        return None
    total = 0.0
    num_w = n - window + 1
    for i in range(num_w):
        total += len(set(tokens[i : i + window])) / window
    return (total / num_w) * 100.0


def _mtld_one_pass(tokens: list[str], threshold: float = 0.72) -> tuple[float, int]:
    factors = 0.0
    full_factors = 0
    start = 0
    seen: set[str] = set()
    for i, tok in enumerate(tokens):
        seen.add(tok)
        if len(seen) / (i - start + 1) <= threshold:
            factors += 1.0
            full_factors += 1
            start = i + 1
            seen = set()
    rem = len(tokens) - start
    if rem > 0:
        ttr = len(seen) / rem
        if ttr < 1.0:
            factors += (1.0 - ttr) / (1.0 - threshold)
    val = len(tokens) / factors if factors > 0 else float(len(tokens))
    return val, full_factors


def compute_mtld(tokens: list[str], threshold: float = 0.72) -> tuple[float | None, bool]:
    if len(tokens) < 20:
        return None, True
    fwd, ff1 = _mtld_one_pass(tokens, threshold)
    bwd, ff2 = _mtld_one_pass(list(reversed(tokens)), threshold)
    return (fwd + bwd) / 2.0, (ff1 == 0 or ff2 == 0)


def compute_all_metrics(plain_lyrics: str) -> dict[str, Any]:
    norm_lyrics = normalize_text(plain_lyrics)
    tokens = tokenize(norm_lyrics)
    n_words = len(tokens)
    n_num = len(NUM_RE.findall(norm_lyrics))

    raw_lines = [ln.strip().lower() for ln in norm_lyrics.splitlines() if len(tokenize(ln)) >= 2]
    unique_lines_ordered: list[str] = []
    seen_lines: set[str] = set()
    for ln in raw_lines:
        if ln not in seen_lines:
            seen_lines.add(ln)
            unique_lines_ordered.append(ln)

    rep_pct = (1.0 - len(unique_lines_ordered) / len(raw_lines)) * 100.0 if raw_lines else 0.0
    norepeat_text = "\n".join(unique_lines_ordered)
    tokens_nr = tokenize(norepeat_text)

    lemmas = lemmatize_fr_tokens(tokens)
    lemmas_nr = lemmatize_fr_tokens(tokens_nr)

    mattr100_s = compute_mattr(tokens, 100)
    mattr50_s = compute_mattr(tokens, 50)
    mattr100_nr = compute_mattr(tokens_nr, 100)
    mattr100_lem = compute_mattr(lemmas, 100)
    mattr100_lem_nr = compute_mattr(lemmas_nr, 100)

    mtld_s, zero_fac = compute_mtld(tokens)
    mtld_nr, _ = compute_mtld(tokens_nr)
    mtld_lem, _ = compute_mtld(lemmas)

    raw_bytes = norm_lyrics.lower().encode("utf-8")
    zlib_ratio = len(zlib.compress(raw_bytes, level=9)) / len(raw_bytes) if raw_bytes else 0.0
    avg_wl = sum(len(w) for w in tokens) / n_words if n_words else 0.0
    avg_lw = sum(len(tokenize(ln)) for ln in raw_lines) / len(raw_lines) if raw_lines else 0.0

    def _r(v: float | None) -> Any:
        return round(v, 2) if v is not None else ""

    return {
        "Longueur_Mots": n_words,
        "Mots_Uniques": len(set(tokens)),
        "Nb_Tokens_Numeriques": n_num,
        "Longueur_Mots_NoRepeat": len(tokens_nr),
        "MATTR_100_Surface": _r(mattr100_s),
        "MATTR_50_Surface": _r(mattr50_s),
        "MATTR_100_NoRepeat": _r(mattr100_nr),
        "MATTR_100_Lemmes": _r(mattr100_lem),
        "MATTR_100_Lemmes_NoRepeat": _r(mattr100_lem_nr),
        "MTLD_Surface": _r(mtld_s),
        "MTLD_NoRepeat": _r(mtld_nr),
        "MTLD_Lemmes": _r(mtld_lem),
        "MTLD_ZeroFactor_Flag": "Oui" if zero_fac else "Non",
        "Taux_Repetition_Pct": round(rep_pct, 2),
        "Ratio_Compression_Zlib": round(zlib_ratio, 4),
        "Longueur_Moyenne_Mot": round(avg_wl, 2),
        "Longueur_Moyenne_Vers": round(avg_lw, 2),
    }


def _norm_meta(text: str) -> str:
    s = normalize_text(text).lower().replace("œ", "oe").replace("æ", "ae")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _clean_query_artist(artist: str) -> str:
    # Retirer les feat. / collaborations secondaires pour la recherche LRCLIB tout en gardant la vérification stricte
    s = re.split(r"\b(?:feat\.?|ft\.?|with|avec|&|/|vs\.?)\b", artist, flags=re.I)[0]
    s = re.sub(r"\[[^\]]*\]", "", s)
    return s.strip(" -,&")


def _clean_query_title(title: str) -> str:
    s = re.sub(r"\([^)]*\)", "", title)
    return s.strip(" -")


def _candidate_matches(req_artist: str, req_title: str, ret_artist: str, ret_title: str) -> bool:
    if any(ord(c) < 32 for c in ret_artist) or any(ord(c) < 32 for c in ret_title):
        return False
    ra, rt = _norm_meta(_clean_query_artist(req_artist)), _norm_meta(_clean_query_title(req_title))
    ga, gt = _norm_meta(ret_artist), _norm_meta(ret_title)
    if not ra or not rt or not ga or not gt:
        return False
    # Titre : correspondance exacte ou inclusion forte (sans version live/remix/instrumental)
    if any(bad in gt for bad in ("instrumental", "karaoke", "remix")) and not any(bad in _norm_meta(req_title) for bad in ("remix",)):
        return False
    title_ok = (rt == gt) or (len(rt) >= 5 and rt in gt) or (len(gt) >= 5 and gt in rt)
    # Artiste : correspondance sur au moins un token significatif (>= 3 chars) du premier artiste
    a_toks = [t for t in ra.split() if len(t) >= 3]
    art_ok = (ra == ga) or (ra in ga) or (ga in ra) or (bool(a_toks) and all(t in ga for t in a_toks[:2]))
    return title_ok and art_ok


def search_lrclib(artist: str, title: str, max_retries: int = 4) -> dict[str, Any] | None:
    queries = [
        {"artist_name": artist, "track_name": title},
        {"artist_name": _clean_query_artist(artist), "track_name": _clean_query_title(title)},
    ]
    seen_q: set[tuple[str, str]] = set()
    for q in queries:
        key = (q["artist_name"].strip().lower(), q["track_name"].strip().lower())
        if not key[0] or not key[1] or key in seen_q:
            continue
        seen_q.add(key)
        url = f"https://lrclib.net/api/search?{urllib.parse.urlencode(q)}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    items = json.loads(resp.read().decode("utf-8"))
                for it in items:
                    plain = (it.get("plainLyrics") or "").strip()
                    if len(plain) < 50:
                        continue
                    ret_a = it.get("artistName") or ""
                    ret_t = it.get("trackName") or ""
                    if _candidate_matches(artist, title, ret_a, ret_t):
                        return it
                break
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(2.0 ** (attempt + 1))
                    continue
                break
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break
        time.sleep(0.20)
    return None


def write_environment_lock(out_dir: Path) -> None:
    lock = {
        "locked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": platform.python_version(),
        "simplemma": importlib.metadata.version("simplemma"),
        "lingua_language_detector": importlib.metadata.version("lingua-language-detector"),
        "tokenizer_regex": WORD_RE.pattern,
        "mtld_threshold": 0.72,
        "language_triage_thresholds": {
            "auto_include_french_min_conf": 0.85,
            "auto_exclude_non_french_max_conf": 0.25,
            "grey_zone_pending_human_review": [0.25, 0.85],
        },
    }
    lock_path = out_dir / "environment_lock.json"
    if not lock_path.exists():
        lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collecte contrôlée du Corpus V2 (respect strict de Draw_Order).")
    parser.add_argument("--max-draw-order", type=int, default=20, help="Rang Draw_Order max à évaluer par strate (Lot 1 = 20 -> 160 titres).")
    parser.add_argument("--target-per-stratum", type=int, default=250, help="Plafond de titres INCLUDED par strate.")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    draw_csv = repo / "data" / "draw_v2_0" / "stratified_candidate_order_v2.csv"
    actual_sha = hashlib.sha256(draw_csv.read_bytes()).hexdigest()
    if actual_sha != EXPECTED_DRAW_ORDER_SHA256:
        raise RuntimeError(f"SHA-256 de stratified_candidate_order_v2.csv modifié ! {actual_sha}")

    out_dir = repo / "data" / "corpus_v2_collect"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_environment_lock(out_dir)

    disp_csv = out_dir / "disposition_log.csv"
    metrics_csv = out_dir / "corpus_v2_metrics.csv"
    ing_log = out_dir / "ingestion_log.jsonl"

    # Charger l'état déjà collecté (reprise idempotente sans jamais retraiter un Work_Slug)
    done_slugs: set[str] = set()
    included_per_block: Counter[str] = Counter()
    if disp_csv.exists():
        with disp_csv.open("r", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                done_slugs.add(r["Work_Slug"])
                if r["Disposition_Status"] == "INCLUDED":
                    included_per_block[r["Top50_Block_5Y"]] += 1

    detector = LanguageDetectorBuilder.from_languages(
        Language.FRENCH, Language.ENGLISH, Language.SPANISH, Language.ITALIAN,
        Language.GERMAN, Language.PORTUGUESE, Language.DUTCH, Language.ARABIC,
    ).build()

    disp_fields = [
        "Top50_Block_5Y", "Draw_Order", "Work_Slug", "Artist_Slug", "Artist", "Title",
        "First_Top50_Year", "Best_Rank", "Disposition_Status", "Exclusion_Category",
        "LRCLIB_ID", "LRCLIB_Artist_Returned", "LRCLIB_Track_Returned",
        "Lang_Top", "Lang_FR_Confidence", "Longueur_Mots", "Notes",
    ]
    metric_fields = [
        "Top50_Block_5Y", "Draw_Order", "Work_Slug", "Artist_Slug", "First_Top50_Year", "Best_Rank",
        "LRCLIB_ID", "Lyrics_SHA256", "Lang_Top", "Lang_FR_Confidence",
        "Longueur_Mots", "Mots_Uniques", "Nb_Tokens_Numeriques", "Longueur_Mots_NoRepeat",
        "MATTR_100_Surface", "MATTR_50_Surface", "MATTR_100_NoRepeat",
        "MATTR_100_Lemmes", "MATTR_100_Lemmes_NoRepeat",
        "MTLD_Surface", "MTLD_NoRepeat", "MTLD_Lemmes", "MTLD_ZeroFactor_Flag",
        "Taux_Repetition_Pct", "Ratio_Compression_Zlib", "Longueur_Moyenne_Mot", "Longueur_Moyenne_Vers",
    ]

    write_disp_header = not disp_csv.exists()
    write_met_header = not metrics_csv.exists()

    with draw_csv.open("r", encoding="utf-8", newline="") as f:
        candidates = list(csv.DictReader(f))

    processed_now = 0
    with disp_csv.open("a", encoding="utf-8", newline="") as f_disp, \
         metrics_csv.open("a", encoding="utf-8", newline="") as f_met, \
         ing_log.open("a", encoding="utf-8", newline="\n") as f_ing:

        w_disp = csv.DictWriter(f_disp, fieldnames=disp_fields, lineterminator="\n")
        w_met = csv.DictWriter(f_met, fieldnames=metric_fields, lineterminator="\n")
        if write_disp_header:
            w_disp.writeheader()
        if write_met_header:
            w_met.writeheader()

        for row in candidates:
            block = row["Top50_Block_5Y"]
            order = int(row["Draw_Order"])
            slug = row["Work_Slug"]
            if order > args.max_draw_order:
                continue
            if slug in done_slugs:
                continue
            if included_per_block[block] >= args.target_per_stratum:
                continue

            artist = row["Artist"]
            title = row["Title"]
            ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            rec = search_lrclib(artist, title)

            if rec is None:
                # Paroles introuvables sur LRCLIB : ne PAS classer arbitrairement comme non francophone !
                w_disp.writerow({
                    "Top50_Block_5Y": block, "Draw_Order": order, "Work_Slug": slug,
                    "Artist_Slug": row["Artist_Slug"], "Artist": artist, "Title": title,
                    "First_Top50_Year": row["First_Top50_Year"], "Best_Rank": row["Best_Rank"],
                    "Disposition_Status": "LYRICS_MISSING_PENDING_LANG_VERIFY",
                    "Exclusion_Category": "LYRICS_MISSING_LRCLIB",
                    "LRCLIB_ID": "", "LRCLIB_Artist_Returned": "", "LRCLIB_Track_Returned": "",
                    "Lang_Top": "", "Lang_FR_Confidence": "", "Longueur_Mots": "",
                    "Notes": "Introuvable sur LRCLIB ; langue à vérifier hors LRCLIB (Cat. A vs B).",
                })
                f_ing.write(json.dumps({"utc": ts_utc, "slug": slug, "lrclib_id": None, "status": "LYRICS_MISSING"}) + "\n")
                processed_now += 1
                continue

            plain = (rec.get("plainLyrics") or "").strip()
            lid = int(rec["id"])
            ret_a = rec.get("artistName", "")
            ret_t = rec.get("trackName", "")
            lyrics_sha = hashlib.sha256(plain.encode("utf-8")).hexdigest()

            # Classification linguistique sur le texte complet (lingua)
            conf_vals = detector.compute_language_confidence_values(plain)
            top_lang = conf_vals[0].language.name if conf_vals else "UNKNOWN"
            fr_conf = next((cv.value for cv in conf_vals if cv.language == Language.FRENCH), 0.0)

            tokens = tokenize(plain)
            n_words = len(tokens)
            has_abbrev = bool(ABBREV_CHORUS_RE.search(plain))

            if top_lang != "FRENCH" and fr_conf < 0.25:
                status = "EXCLUDED_NON_FRENCH"
                cat = "CAT_A_NON_FRENCH"
                note = f"Langue détectée={top_lang} (conf FR={fr_conf:.3f})"
            elif has_abbrev:
                status = "EXCLUDED_UNUSABLE_TRANSCRIPTION"
                cat = "CAT_C_UNUSABLE_ABBREV_CHORUS"
                note = "Balise de refrain abrégé détectée dans la transcription LRCLIB"
            elif fr_conf < 0.85 or top_lang != "FRENCH":
                status = "PENDING_HUMAN_REVIEW"
                cat = "GREY_ZONE_LINGUISTIC"
                note = f"Zone grise linguistique (top={top_lang}, conf FR={fr_conf:.3f}) — arbitrage humain requis"
            elif n_words < 100:
                status = "EXCLUDED_SHORT_LT_100"
                cat = "CAT_C_SHORT_LT_100"
                note = f"Francophone confirmé mais {n_words} mots < 100 (inéligible MATTR_100)"
            else:
                status = "INCLUDED"
                cat = ""
                note = "Francophone confirmé, transcription exploitable >= 100 mots"

            w_disp.writerow({
                "Top50_Block_5Y": block, "Draw_Order": order, "Work_Slug": slug,
                "Artist_Slug": row["Artist_Slug"], "Artist": artist, "Title": title,
                "First_Top50_Year": row["First_Top50_Year"], "Best_Rank": row["Best_Rank"],
                "Disposition_Status": status, "Exclusion_Category": cat,
                "LRCLIB_ID": lid, "LRCLIB_Artist_Returned": ret_a, "LRCLIB_Track_Returned": ret_t,
                "Lang_Top": top_lang, "Lang_FR_Confidence": round(fr_conf, 4),
                "Longueur_Mots": n_words, "Notes": note,
            })

            if status == "INCLUDED":
                m = compute_all_metrics(plain)
                w_met.writerow({
                    "Top50_Block_5Y": block, "Draw_Order": order, "Work_Slug": slug,
                    "Artist_Slug": row["Artist_Slug"], "First_Top50_Year": row["First_Top50_Year"],
                    "Best_Rank": row["Best_Rank"], "LRCLIB_ID": lid, "Lyrics_SHA256": lyrics_sha,
                    "Lang_Top": top_lang, "Lang_FR_Confidence": round(fr_conf, 4),
                    **m,
                })
                included_per_block[block] += 1

            f_ing.write(json.dumps({
                "utc": ts_utc, "slug": slug, "lrclib_id": lid, "lyrics_sha256": lyrics_sha,
                "status": status, "lang_top": top_lang, "fr_conf": round(fr_conf, 4),
            }) + "\n")
            processed_now += 1
            time.sleep(0.20)

    print(f"Processed {processed_now} candidates in this run. Total INCLUDED per block:", dict(sorted(included_per_block.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
