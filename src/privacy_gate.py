"""Phase 1 — Privacy Gatekeeper (RGPD by Design).

Détecte localement les données directement identifiantes (PII) dans les en-têtes
et les cellules avant toute analyse, avec localisation précise pour permettre
l'exclusion en un clic (One-Click Scrub).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd


# En-têtes d'identifiants directs (FR / EN / NL)
PII_HEADER_PATTERNS = [
    (r"(?i)^(?:nom|prenom|prénom|nom_complet|full_?name|first_?name|last_?name|surname|name)$", "Nom / Prénom"),
    (r"(?i)(?:e-?mail|courriel|mail)", "Adresse email"),
    (r"(?i)(?:phone|tel|t[eé]l[eé]phone|mobile|gsm)", "Numéro de téléphone"),
    (r"(?i)(?:nir|niss|insz|ssn|secu|s[eé]curit[eé]_?sociale|social_?security)", "Numéro de sécurité sociale"),
    (r"(?i)(?:iban|bic|rib|carte_?bancaire|credit_?card)", "Coordonnée bancaire"),
    (r"(?i)(?:adresse|address|rue|street|domicile|ip_?address)", "Adresse postale / IP"),
    (
        r"(?i)(?:matricule|dossier_?id|employee_?id|emp_?id|patient_?id|participant_?id|"
        r"subject_?id|student_?id|user_?id|personeelsnummer|studentnummer|patientnummer|id_?salari[eé])",
        "Identifiant individuel (Matricule / ID)",
    ),
]

# Motifs de valeurs PII
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")
PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s.-]?)?(?:\(0\)|0)\d(?:[\s.-]?\d{2}){4}\b")
EMP_CODE_RE = re.compile(r"(?i)^(?:EMP|PAT|USR|DOS|MAT|SAL)[-_]?\d{2,8}$")
NISS_RE = re.compile(r"^\d{2}\.?\d{2}\.?\d{2}[-.]?\d{3}\.?\d{2}$")
FULL_NAME_RE = re.compile(r"^[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'-]{1,20}\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ'-]{1,20}$")

# Liste blanche multilingue pour éviter les faux positifs sur les modalités catégorielles
SAFE_CATEGORY_WORDS = {
    "sur site", "télétravail", "teletravail", "hybride", "temps plein", "temps partiel",
    "non cadre", "cadre supérieur", "groupe contrôle", "groupe controle", "groupe test",
    "service client", "service technique", "ressources humaines", "direction générale",
    "control group", "treatment group", "high school", "master degree", "full time", "part time",
}


def _is_valid_belgian_niss(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)
    if len(digits) != 11:
        return False
    base = int(digits[:9])
    check = int(digits[9:])
    # Nés avant 2000 ou à partir de 2000
    return (97 - (base % 97) == check) or (97 - ((2000000000 + base) % 97) == check)


def _mask_sample(val: str) -> str:
    s = str(val).strip()
    if len(s) <= 4:
        return "***"
    return f"{s[:2]}***{s[-2:]}"


@dataclass
class PIIFinding:
    column: str
    reason: str
    source: str  # "header" | "values"
    match_count: int
    masked_samples: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scan_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Scanne un DataFrame et retourne les colonnes PII détectées (sans fuite en clair)."""
    findings: list[PIIFinding] = []
    flagged_columns: list[str] = []

    for col in df.columns:
        col_str = str(col).strip()
        col_findings: list[PIIFinding] = []

        # 1. Vérification de l'en-tête
        for pattern, label in PII_HEADER_PATTERNS:
            if re.search(pattern, col_str):
                col_findings.append(
                    PIIFinding(
                        column=col_str,
                        reason=f"En-tête identifiant : {label}",
                        source="header",
                        match_count=len(df),
                        masked_samples=[],
                    )
                )
                break

        # 2. Vérification des valeurs (échantillon jusqu'à 500 valeurs non nulles)
        series = df[col].dropna().astype(str).str.strip()
        if len(series) > 500:
            series = series.iloc[:500]

        if not series.empty:
            checks = [
                ("Adresse email", lambda s: bool(EMAIL_RE.search(s))),
                ("IBAN", lambda s: bool(IBAN_RE.search(s))),
                ("Adresse IP", lambda s: bool(IPV4_RE.search(s))),
                ("Téléphone", lambda s: bool(PHONE_RE.search(s))),
                ("Code matricule / dossier", lambda s: bool(EMP_CODE_RE.match(s))),
                ("Numéro NISS/INSZ", lambda s: bool(NISS_RE.match(s)) and _is_valid_belgian_niss(s)),
                (
                    "Nom et prénom probables",
                    lambda s: bool(FULL_NAME_RE.match(s)) and s.lower() not in SAFE_CATEGORY_WORDS,
                ),
            ]
            for label, fn in checks:
                matches = [v for v in series if fn(v)]
                # Pour les noms propres, exiger >= 2 correspondances ou >= 30% pour limiter les faux positifs
                threshold = 2 if label == "Nom et prénom probables" else 1
                if len(matches) >= threshold:
                    col_findings.append(
                        PIIFinding(
                            column=col_str,
                            reason=f"Valeurs identifiantes détectées : {label}",
                            source="values",
                            match_count=len(matches),
                            masked_samples=[_mask_sample(m) for m in matches[:3]],
                        )
                    )

        if col_findings:
            flagged_columns.append(col_str)
            findings.extend(col_findings)

    return {
        "blocked": len(flagged_columns) > 0,
        "flagged_columns": flagged_columns,
        "findings": [f.to_dict() for f in findings],
        "message": (
            f"Données potentiellement identifiantes détectées dans {len(flagged_columns)} colonne(s) : "
            f"{', '.join(flagged_columns)}. Excluez-les en un clic ou anonymisez votre fichier."
            if flagged_columns
            else "Aucune donnée directement identifiante détectée."
        ),
    }


def exclude_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """One-Click Scrub : retire les colonnes identifiantes sélectionnées par l'utilisateur."""
    to_drop = [c for c in columns if c in df.columns]
    return df.drop(columns=to_drop)
