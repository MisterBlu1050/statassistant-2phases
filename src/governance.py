"""Governance, GDPR Compliance, Tiers & Audit Log (XL AI Principles) — Bilingual NL / EN."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "audit_log.jsonl"

TIERS_BY_LANG: dict[str, dict[str, dict[str, Any]]] = {
    "nl": {
        "autonome": {
            "label": "Autonoom — Fase 1 (0 AI)",
            "phase1": "Deterministisch lokaal (SciPy/NumPy)",
            "phase2": "Uitgeschakeld",
            "llm_data": "Geen",
            "zdr": True,
        },
        "local_expert": {
            "label": "Kritiek / Local Expert (0 netwerkverkeer)",
            "phase1": "Deterministisch lokaal (SciPy/NumPy)",
            "phase2": "Lokale expert-engine (offline) + menselijke validatie",
            "llm_data": "Geen uitgaand netwerkverkeer",
            "zdr": True,
        },
        "confidentiel_zdr": {
            "label": "Vertrouwelijk / Enterprise ZDR",
            "phase1": "Deterministisch lokaal (SciPy/NumPy)",
            "phase2": "Enterprise API zonder training + Zero Data Retention",
            "llm_data": "Alleen geaggregeerd JSON-contract (nul ruwe rijen)",
            "zdr": True,
        },
    },
    "en": {
        "autonome": {
            "label": "Autonomous — Phase 1 (0 AI)",
            "phase1": "Deterministic local (SciPy/NumPy)",
            "phase2": "Disabled",
            "llm_data": "None",
            "zdr": True,
        },
        "local_expert": {
            "label": "Critical / Local Expert (0 network egress)",
            "phase1": "Deterministic local (SciPy/NumPy)",
            "phase2": "Local expert engine (offline) + human validation",
            "llm_data": "No external network transfer",
            "zdr": True,
        },
        "confidentiel_zdr": {
            "label": "Confidential / Enterprise ZDR",
            "phase1": "Deterministic local (SciPy/NumPy)",
            "phase2": "Enterprise API (no training) + Zero Data Retention",
            "llm_data": "Aggregated JSON contract only (zero raw rows)",
            "zdr": True,
        },
    },
}

LEGAL_BY_LANG: dict[str, dict[str, Any]] = {
    "nl": {
        "version": "1.0",
        "roles_rgpd": {
            "client": "Verwerkingsverantwoordelijke — garandeert de rechtmatigheid en voorafgaande anonimisering van geüploade bestanden.",
            "xl_ai": "Verwerker — levert de beveiligde analyse-infrastructuur, de Privacy Gatekeeper en PII-vrije auditlogging.",
            "fournisseur_llm": "Subverwerker (alleen bij Enterprise/ZDR API) — ontvangt uitsluitend geaggregeerde statistieken, nooit individuele gegevens.",
        },
        "cgu_resume": [
            "De gebruiker verbindt zich ertoe geen direct identificeerbare persoonsgegevens te uploaden; de Privacy Gatekeeper blokkeert gedetecteerde PII automatisch.",
            "Statistische berekeningen (Fase 1) zijn deterministisch en reproduceerbaar; de gebruiker blijft verantwoordelijk voor zakelijke of klinische beslissingen.",
            "In Zero Data Retention (ZDR)-modus blijven sessiegegevens uitsluitend in het werkgeheugen en worden ze op verzoek direct gewist.",
        ],
        "dpa_points_cles": [
            "Strikte scheiding tussen Fase 1 (data) en Fase 2 (uitsluitend geaggregeerde statistieken).",
            "Cryptografische SHA-256-vingerafdrukken (origineel bestand + geanonimiseerde dataset) voor volledige auditeerbaarheid.",
            "Mogelijkheid tot onmiddellijke schorsing van een gebruikersaccount bij niet-conform gebruik.",
        ],
    },
    "en": {
        "version": "1.0",
        "roles_rgpd": {
            "client": "Data Controller — guarantees lawfulness and prior anonymisation of uploaded datasets.",
            "xl_ai": "Data Processor — provides the governed analysis infrastructure, Privacy Gatekeeper, and PII-free audit logging.",
            "fournisseur_llm": "Sub-processor (Enterprise/ZDR API tier only) — receives aggregated statistics exclusively, never individual rows.",
        },
        "cgu_resume": [
            "Users agree not to submit directly identifiable personal data; the Privacy Gatekeeper automatically blocks detected PII.",
            "Statistical computations (Phase 1) are deterministic and reproducible; users remain accountable for business or clinical decisions.",
            "Under Zero Data Retention (ZDR), session data reside exclusively in volatile memory and can be purged on demand.",
        ],
        "dpa_points_cles": [
            "Strict separation between Phase 1 (raw data) and Phase 2 (aggregated statistics only).",
            "Cryptographic SHA-256 fingerprints (original file + anonymised dataset) for independent auditability.",
            "Immediate user account suspension capability in case of policy violation.",
        ],
    },
}

TIERS = TIERS_BY_LANG["en"]
LEGAL_NOTICE = LEGAL_BY_LANG["en"]

_SUSPENDED_USERS: set[str] = set()


def get_tiers(lang: str = "nl") -> dict[str, dict[str, Any]]:
    return TIERS_BY_LANG.get(lang, TIERS_BY_LANG["en"])


def get_legal(lang: str = "nl") -> dict[str, Any]:
    return LEGAL_BY_LANG.get(lang, LEGAL_BY_LANG["en"])


def is_user_suspended(user_id: str) -> bool:
    return user_id in _SUSPENDED_USERS


def set_user_suspension(user_id: str, suspended: bool) -> None:
    if suspended:
        _SUSPENDED_USERS.add(user_id)
    else:
        _SUSPENDED_USERS.discard(user_id)


def log_audit_event(
    action: str,
    user_id: str = "demo-user",
    tier: str = "local_expert",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Logs a GDPR-compliant audit event (strictly zero individual data)."""
    safe_meta = {}
    if metadata:
        allowed_keys = {
            "filename",
            "sha256_raw_file",
            "sha256_anonymized_file",
            "pii_blocked_count",
            "excluded_pii_columns",
            "modes_run",
            "n_analyses",
            "export_format",
            "session_purged",
        }
        safe_meta = {k: v for k, v in metadata.items() if k in allowed_keys}

    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "tier": tier,
        "action": action,
        "metadata": safe_meta,
    }
    try:
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return entry


def read_recent_audit_logs(limit: int = 30) -> list[dict[str, Any]]:
    if not AUDIT_LOG_PATH.exists():
        return []
    lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
    out = []
    for ln in reversed(lines[-limit:]):
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out
