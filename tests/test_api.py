"""Tests automatisés de l'API SaaS Palier 3 (FastAPI + SPA + Gouvernance XL AI)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api import app
from src.governance import set_user_suspension


client = TestClient(app)


def test_spa_and_governance_endpoints():
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert "StatAssistant" in r_home.text

    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_legal_nl = client.get("/api/governance/legal?lang=nl")
    assert r_legal_nl.status_code == 200
    assert "Verwerkingsverantwoordelijke" in r_legal_nl.json()["legal"]["roles_rgpd"]["client"]

    r_legal_en = client.get("/api/governance/legal?lang=en")
    assert r_legal_en.status_code == 200
    assert "Data Controller" in r_legal_en.json()["legal"]["roles_rgpd"]["client"]


def test_user_suspension_blocks_access():
    set_user_suspension("blocked-user", True)
    try:
        r = client.get("/api/governance/audit-log", headers={"X-User-Id": "blocked-user"})
        assert r.status_code == 403
    finally:
        set_user_suspension("blocked-user", False)


def test_full_saas_workflow_ingest_scrub_plan_run_export_purge():
    v8 = Path(r"C:\Users\Bibi\Downloads\dataset_saas_palier2_v8.csv")
    if not v8.exists():
        # Fallback CSV inline minimal avec PII
        csv_bytes = (
            "Email;Groupe;X;Y\n"
            "a@test.fr;A;10;20\n"
            "b@test.fr;A;12;24\n"
            "c@test.fr;B;15;35\n"
            "d@test.fr;B;18;40\n"
            "e@test.fr;B;20;44\n"
        ).encode("utf-8")
        fname = "mini.csv"
    else:
        csv_bytes = v8.read_bytes()
        fname = v8.name

    # 1. Ingest -> Privacy Gatekeeper bloque les PII
    r_ing = client.post(
        "/api/phase1/ingest",
        files={"file": (fname, csv_bytes, "text/csv")},
        data={"sep": "auto", "decimal": "auto", "custom_missing": "-999, -99"},
    )
    assert r_ing.status_code == 200
    d_ing = r_ing.json()
    sid = d_ing["session_id"]
    assert d_ing["pii"]["blocked"] is True

    # 2. One-Click Scrub débloque et calcule le SHA-256 anonymisé
    r_scr = client.post(
        "/api/phase1/scrub",
        json={"session_id": sid, "columns": d_ing["pii"]["flagged_columns"]},
    )
    assert r_scr.status_code == 200
    d_scr = r_scr.json()
    assert d_scr["pii"]["blocked"] is False
    assert d_scr["meta"]["sha256_anonymized_file"]

    # 3. Texte hors sujet rejeté avant calcul
    r_off = client.post(
        "/api/phase1/auto-plan",
        json={"session_id": sid, "question": "Le délai bancaire moyen passe de 19 jours à 16 jours."},
    )
    assert r_off.status_code == 200
    assert r_off.json()["matched"] is False

    # 4. Run Phase 1 + Phase 2 (ex. régression logistique ou t-test)
    if v8.exists():
        plans = [{"mode": "logit", "y": "Churn_Client", "xs": ["Score_Support", "Usage_Hebdo_H"], "question": "Prédire le churn"}]
    else:
        plans = [{"mode": "reg", "y": "Y", "xs": ["X"], "question": "X prédit-il Y ?"}]

    r_run = client.post(
        "/api/phase1/run",
        json={"session_id": sid, "plans": plans, "tier": "local_expert"},
    )
    assert r_run.status_code == 200
    res0 = r_run.json()["results"][0]
    assert res0["contract"]["privacy_guarantee"] == "AGGREGATED_ONLY_NO_RAW_ROWS"
    assert res0["phase2"]["agent2_apa7_report"]
    assert len(res0["charts"]) >= 1

    # 5. Exports PDF, DOCX, Markdown (NL & EN), Script Python
    for fmt, magic in [("pdf", b"%PDF"), ("docx", b"PK"), ("markdown", b"# Statistisch"), ("script", b'"""Script')]:
        r_exp = client.post(f"/api/export/{fmt}", json={"session_id": sid, "language": "nl"})
        assert r_exp.status_code == 200
        assert r_exp.content.startswith(magic)

    r_md_en = client.post("/api/export/markdown", json={"session_id": sid, "language": "en"})
    assert r_md_en.status_code == 200
    assert r_md_en.content.startswith(b"# Statistical")

    # 6. Purge ZDR de la session -> 404 ensuite
    r_del = client.delete(f"/api/session/{sid}")
    assert r_del.status_code == 200 and r_del.json()["purged"] is True
    r_after = client.post("/api/phase1/auto-plan", json={"session_id": sid, "question": "test"})
    assert r_after.status_code == 404


def test_sample_endpoint_bilingual_nl_and_en():
    for lang in ("nl", "en"):
        r = client.post(f"/api/phase1/sample?lang={lang}")
        assert r.status_code == 200
        d = r.json()
        assert d["pii"]["blocked"] is False
        r_plan = client.post(
            "/api/phase1/auto-plan",
            json={"session_id": d["session_id"], "question": d["sample_question"], "language": lang},
        )
        assert r_plan.status_code == 200
        assert len(r_plan.json()["plans"]) >= 3
        client.delete(f"/api/session/{d['session_id']}")


def test_admin_suspend_api_key_and_zdr_ttl_eviction(monkeypatch):
    import api as api_mod

    # 1. Suspension via endpoint admin protégé par STAT_ADMIN_KEY
    monkeypatch.setenv("STAT_ADMIN_KEY", "super-admin-secret")
    assert client.post("/api/admin/users/u-bad/suspend").status_code == 403
    r_sus = client.post("/api/admin/users/u-bad/suspend", headers={"X-Admin-Key": "super-admin-secret"})
    assert r_sus.status_code == 200 and r_sus.json()["suspended"] is True
    assert client.get("/api/governance/audit-log", headers={"X-User-Id": "u-bad"}).status_code == 403
    r_unsus = client.delete("/api/admin/users/u-bad/suspend", headers={"X-Admin-Key": "super-admin-secret"})
    assert r_unsus.status_code == 200 and r_unsus.json()["suspended"] is False

    # 2. Clé API obligatoire quand STAT_API_KEY est définie
    monkeypatch.setenv("STAT_API_KEY", "client-secret")
    assert client.get("/api/governance/audit-log").status_code == 401
    assert client.get("/api/governance/audit-log", headers={"X-API-Key": "client-secret"}).status_code == 200
    monkeypatch.delenv("STAT_API_KEY", raising=False)

    # 3. Expiration automatique ZDR (TTL)
    r_s = client.post("/api/phase1/sample?lang=en")
    sid = r_s.json()["session_id"]
    api_mod.SESSIONS[sid]["last_access"] -= (api_mod.SESSION_TTL_SECONDS + 10)
    r_exp = client.post("/api/phase1/auto-plan", json={"session_id": sid, "question": "test"})
    assert r_exp.status_code == 404


