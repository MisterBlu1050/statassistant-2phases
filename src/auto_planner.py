"""Phase 1 — Planificateur Automatique Déterministe (0 % IA).

Analyse une question de recherche simple ou multi-parties en langage naturel,
repère les colonnes et modalités mentionnées dans chaque proposition, et génère
automatiquement la liste des plans statistiques à exécuter en Phase 1.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd


STOP_TOKENS = {
    "score", "indice", "taux", "pct", "heures", "heure", "jours", "jour", "ans", "mois", "niveau",
    "moyen", "moyenne", "globale", "global", "annuelle", "annuel", "finale", "final",
    "cours", "travail", "avant", "apres", "pre", "post", "type", "index", "percu",
    # NL & EN generic words
    "uur", "uren", "dag", "dagen", "jaar", "maand", "maanden", "gemiddelde", "voor", "vooraf", "achteraf",
    "hours", "hour", "days", "day", "years", "year", "months", "month", "rate", "level", "mean", "average", "before", "after",
}


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def _split_clauses(question: str) -> list[str]:
    """Découpe une question complexe en sous-questions sans couper l'intérieur des parenthèses."""
    q = question.strip()
    if not q:
        return []
    # Protéger le contenu entre parenthèses pendant le découpage
    protected: list[str] = []

    def _hide(m):
        protected.append(m.group(0))
        return f"__PAR{len(protected) - 1}__"

    q_mask = re.sub(r"\([^)]*\)", _hide, q)
    raw_parts = re.split(
        r"[?;]|\s*,\s*(?:et\s+|en\s+|and\s+)?|\s+(?:et|en|and)\s+(?=(?:le |la |les |l'|de |het |welke |hoe |does |do |is |are |which |what |the ))",
        q_mask,
        flags=re.IGNORECASE,
    )

    clauses = []
    for part in raw_parts:
        for idx, orig in enumerate(protected):
            part = part.replace(f"__PAR{idx}__", orig)
        part = part.strip(" .,;:-«»\"'")
        if len(part) >= 6:
            clauses.append(part)
    return clauses if clauses else [q]


def _match_columns_in_clause(
    clause: str,
    df: pd.DataFrame,
    col_types: dict[str, str],
) -> list[str]:
    """Identifie les colonnes du DataFrame mentionnées dans une proposition (par nom ou modalité).

    Passe 1 : correspondances exactes de noms de colonnes (frontières d'identifiant), masquées ensuite
    dans la proposition afin qu'une colonne exacte (ex. MATTR_100) ne déclenche jamais de faux positif
    partiel sur une colonne voisine (ex. MATTR_50).
    Passe 2 : correspondances partielles par tokens significatifs ou modalités catégorielles.
    """
    c_norm = _norm(clause)
    matched: list[tuple[int, str, set[str], bool]] = []  # (pos, col, tokens, is_exact)
    exact_cols: set[str] = set()
    exact_subtokens: set[str] = set()

    # Passe 1 : correspondances exactes d'identifiants de colonnes (les plus longs d'abord)
    masked_norm = c_norm
    candidates = [(col, _norm(col)) for col, ctype in col_types.items() if ctype != "ignored"]
    for col, col_norm in sorted(candidates, key=lambda item: len(item[1]), reverse=True):
        m = re.search(rf"(?<![a-z0-9_]){re.escape(col_norm)}(?![a-z0-9_])", masked_norm)
        if m:
            matched.append((m.start(), col, {col_norm}, True))
            exact_cols.add(col)
            for t in re.split(r"[_\s-]+", col_norm):
                if len(t) >= 3:
                    exact_subtokens.add(t)
            # Masquer l'empan exact en conservant les indices de position
            masked_norm = masked_norm[: m.start()] + (" " * (m.end() - m.start())) + masked_norm[m.end() :]

    # Passe 2 : correspondances partielles uniquement sur le texte non consommé par une correspondance exacte
    for col, col_norm in candidates:
        if col in exact_cols:
            continue
        ctype = col_types[col]

        tokens = [t for t in re.split(r"[_\s-]+", col_norm) if len(t) >= 3 and t not in STOP_TOKENS]
        if not tokens:
            tokens = [t for t in re.split(r"[_\s-]+", col_norm) if len(t) >= 3]

        best_pos = None
        hit_tokens: set[str] = set()
        for tok in tokens:
            if tok in exact_subtokens:
                continue
            stem = tok[:-1] if len(tok) >= 6 and tok.endswith(("s", "e")) else tok
            m = re.search(rf"\b{re.escape(stem)}\w*", masked_norm)
            if m:
                hit_tokens.add(tok)
                best_pos = m.start() if best_pos is None else min(best_pos, m.start())

        # Pour les colonnes multi-tokens (>= 3 tokens significatifs), éviter un faux positif sur 1 seul token
        # lorsqu'au moins une colonne exacte a déjà été identifiée dans la proposition.
        if best_pos is not None and exact_cols and len(tokens) >= 3 and len(hit_tokens) < 2:
            best_pos = None
            hit_tokens = set()

        # Correspondance par valeurs de modalités catégorielles (ex: "présentiel", "distanciel")
        if best_pos is None and ctype == "categorical":
            vals = df[col].dropna().astype(str).unique()
            val_hits = 0
            first_vpos = None
            for v in vals:
                vn = _norm(v)
                if len(vn) >= 4 and vn not in ("true", "false", "oui", "non"):
                    m = re.search(rf"\b{re.escape(vn)}\w*", masked_norm)
                    if m:
                        val_hits += 1
                        first_vpos = m.start() if first_vpos is None else min(first_vpos, m.start())
            if val_hits >= 2 or (val_hits == 1 and len(vals) <= 4):
                best_pos = first_vpos
                hit_tokens.add(f"__val_{col_norm}")

        if best_pos is not None:
            matched.append((best_pos, col, hit_tokens, False))

    # Éliminer les correspondances partielles dont l'unique token touché est déjà couvert par une correspondance plus riche (>= 2 tokens)
    rich_tokens: set[str] = set()
    for _, _, htoks, is_exact in matched:
        if is_exact or len(htoks) >= 2:
            rich_tokens.update(htoks)
    filtered = [
        (pos, col)
        for pos, col, htoks, is_exact in matched
        if is_exact or len(htoks) >= 2 or not htoks.issubset(rich_tokens)
    ]

    # Trier par ordre d'apparition dans la phrase et dédupliquer
    filtered.sort(key=lambda x: x[0])
    seen = set()
    ordered = []
    for _, col in filtered:
        if col not in seen:
            seen.add(col)
            ordered.append(col)
    return ordered


def _find_paired_pair(cols: list[str]) -> tuple[str, str] | None:
    """Repère une paire Avant/Après, Voor/Na ou Before/After dans une liste de colonnes."""
    before_kw = ("avant", "pre", "t0", "initial", "debut", "before", "voor", "baseline")
    after_kw = ("apres", "post", "t1", "final", "fin", "after", "na_", "_na", "achteraf")
    before = next((c for c in cols if any(k in _norm(c) for k in before_kw)), None)
    after = next((c for c in cols if any(k in _norm(c) for k in after_kw)), None)
    if before and after and before != after:
        return before, after
    return None


def _detect_direction(clause_norm: str) -> str:
    if any(w in clause_norm for w in ("redui", "baisse", "diminu", "moins", "inferieur", "verminder", "daal", "lager", "reduc", "decreas", "lower", "drop")):
        return "less"
    if any(w in clause_norm for w in ("augment", "hausse", "ameliore", "plus", "superieur", "surpasse", "verhoog", "stijg", "hoger", "increas", "improv", "higher", "outperform")):
        return "greater"
    return "two-sided"


def auto_plan_from_question(
    question: str,
    df: pd.DataFrame,
    col_types: dict[str, str],
    alpha: float = 0.05,
    language: str = "nl",
) -> list[dict[str, Any]]:
    """Construit automatiquement 1 à N plans d'analyse Phase 1 depuis une question libre."""
    clauses = _split_clauses(question)
    plans: list[dict[str, Any]] = []
    last_continuous_y: str | None = None

    for clause in clauses:
        cols = _match_columns_in_clause(clause, df, col_types)
        if not cols:
            continue

        c_norm = _norm(clause)
        cont = [c for c in cols if col_types.get(c) == "continuous"]
        cat = [c for c in cols if col_types.get(c) == "categorical"]

        # 1. Mesures appariées (Avant / Après)
        pair = _find_paired_pair(cont)
        if pair:
            before, after = pair
            plans.append(
                {
                    "mode": "pair",
                    "y": after,
                    "xs": [before],
                    "alpha": alpha,
                    "alternative": _detect_direction(c_norm),
                    "question": clause,
                    "language": language,
                }
            )
            last_continuous_y = after
            continue

        # 2. Croisement de 2 variables catégorielles (Chi2 / Fisher / Monte Carlo)
        if len(cat) >= 2 and not cont:
            plans.append(
                {
                    "mode": "chi",
                    "y": cat[0],
                    "xs": [cat[1]],
                    "alpha": alpha,
                    "alternative": "two-sided",
                    "question": clause,
                    "language": language,
                }
            )
            continue

        # 3. Comparaison de groupes (1 continue + 1 catégorielle, ou modalités + continue précédente)
        if len(cat) >= 1 and (len(cont) == 1 or (len(cont) == 0 and last_continuous_y)):
            y_col = cont[0] if cont else last_continuous_y
            g_col = cat[0]
            n_grp = int(df[g_col].dropna().nunique())
            mode = "ind" if n_grp == 2 else "anova"
            plans.append(
                {
                    "mode": mode,
                    "y": y_col,
                    "xs": [g_col],
                    "alpha": alpha,
                    "alternative": "two-sided",
                    "question": clause,
                    "language": language,
                }
            )
            last_continuous_y = y_col
            continue

        # 4. Régression simple ou multiple (>= 2 variables continues)
        if len(cont) >= 2:
            # Si la phrase contient "explique(nt)" ou "prédit" ou "influence" : X vient avant Y (ex: "X expliquent Y")
            # Si la phrase contient "expliqué(e) par" ou "selon" ou "en fonction de" : Y vient avant X
            if re.search(r"expliqu\w*\s+par|selon|en fonction de|dep\w*\s+de|verklaard\s+door|afhankelijk\s+van|explained\s+by|depend\w*\s+on|by\s+", c_norm):
                y_col = cont[0]
                xs = cont[1:]
            else:
                y_col = cont[-1]
                xs = cont[:-1]
            # La variable temporelle est le prédicteur, et non la réponse,
            # même lorsqu'elle est mentionnée après l'indicateur étudié (FR / EN / NL).
            temporal_names = {"annee", "year", "jaar", "publication_year", "release_year",
                              "hire_year", "admission_year", "date", "temps", "time", "periode", "period", "mois", "month"}
            temporal_cols = [c for c in cont if _norm(c).replace(" ", "_") in temporal_names]
            trend_question = bool(
                re.search(
                    r"evolu|evolv|tendan|chronolog|au fil|dans le temps|over time|trend|"
                    r"chang\w*\s+(?:with|over)|with\s+year|avec\s+l.?annee|avec\s+annee|"
                    r"door de jaren|in de tijd|verander\w*\s+(?:met|door)",
                    c_norm,
                )
            )
            if len(temporal_cols) == 1 and len(cont) == 2:
                time_col = temporal_cols[0]
                t_norm = _norm(time_col)
                explicitly_predicts_time = bool(
                    re.search(rf"(?:predi\w*|voorspel\w*|expliqu\w*)\s+{re.escape(t_norm)}", c_norm)
                )
                if trend_question or (y_col == time_col and not explicitly_predicts_time):
                    y_col = next(c for c in cont if c != time_col)
                    xs = [time_col]
            plans.append(
                {
                    "mode": "reg" if len(xs) == 1 else "multi",
                    "y": y_col,
                    "xs": xs,
                    "alpha": alpha,
                    "alternative": "two-sided",
                    "question": clause,
                    "language": language,
                }
            )
            last_continuous_y = y_col
            continue

        # 5. Descriptif simple (1 variable continue) — UNIQUEMENT si demande explicite (FR / NL / EN)
        if len(cont) == 1 and any(w in c_norm for w in ("decri", "moyenne", "mediane", "distribution", "statistique", "resum", "beschrijf", "gemiddelde", "mediaan", "verdeling", "describ", "mean", "median", "summary")):
            plans.append(
                {
                    "mode": "desc",
                    "y": cont[0],
                    "xs": [],
                    "alpha": alpha,
                    "alternative": "two-sided",
                    "question": clause,
                    "language": language,
                }
            )
            last_continuous_y = cont[0]

    # Dédupliquer d'éventuels plans identiques
    unique: list[dict[str, Any]] = []
    seen_keys = set()
    for p in plans:
        key = (p["mode"], p["y"], tuple(p["xs"]))
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(p)
    return unique
