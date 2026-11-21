"""StatAssistant 2-Phases — API REST FastAPI + Service SPA (Palier 3 SaaS)."""

from __future__ import annotations

import base64
import io
import os
import platform
import time
import uuid
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.auto_planner import auto_plan_from_question
from src.charts import build_figures
from src.exporters import build_docx_report, build_pdf_report
from src.governance import (
    get_legal,
    get_tiers,
    is_user_suspended,
    log_audit_event,
    read_recent_audit_logs,
    set_user_suspension,
)
from src.phase2_agents import run_phase2_interpretation
from src.privacy_gate import exclude_columns, scan_dataframe
from src.stats_engine import (
    generate_reproducible_script,
    infer_column_types,
    parse_dataset,
    run_analysis,
    sha256_bytes,
)

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(
    title="StatAssistant 2-Phases API (XL AI)",
    version="3.0.0",
    description="Moteur statistique déterministe falsifiable (Phase 1) + Interprétation IA métier sur JSON agrégé uniquement (Phase 2).",
)

# Stockage éphémère en mémoire vive uniquement (Zero Data Retention + TTL automatique)
SESSIONS: dict[str, dict[str, Any]] = {}
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_MINUTES", "30")) * 60


def _evict_expired_sessions() -> int:
    now = time.time()
    expired = [sid for sid, s in SESSIONS.items() if (now - s.get("last_access", now)) > SESSION_TTL_SECONDS]
    for sid in expired:
        SESSIONS.pop(sid, None)
        log_audit_event(action="zdr_auto_ttl_purge", user_id="system", metadata={"session_purged": True})
    return len(expired)


def _check_user(user_id: str, api_key: str | None = None) -> None:
    _evict_expired_sessions()
    required_key = os.getenv("STAT_API_KEY", "").strip()
    if required_key and api_key != required_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")
    if is_user_suspended(user_id):
        raise HTTPException(status_code=403, detail="User account suspended by governance policy.")


def _check_admin(admin_key: str | None) -> None:
    required_admin = os.getenv("STAT_ADMIN_KEY", "").strip()
    if not required_admin or admin_key != required_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required.")


def _get_session(session_id: str) -> dict[str, Any]:
    _evict_expired_sessions()
    sess = SESSIONS.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found or expired (ZDR).")
    sess["last_access"] = time.time()
    return sess


def _format_diag_row(d: dict[str, Any]) -> str:
    stat_s = f"{d['statistic']:.3f}" if isinstance(d["statistic"], (int, float)) else "—"
    p_val = d["p"]
    if isinstance(p_val, (int, float)):
        p_s = "< .001" if p_val < 0.001 else "." + f"{p_val:.3f}".split(".")[1]
    else:
        p_s = "—"
    return f"| {d['name']} | {d['label']} | {d['n']} | {stat_s} | {p_s} |"


def _build_markdown_report(items: list[tuple[dict[str, Any], dict[str, Any] | None]], full_question: str, lang: str = "nl") -> str:
    nl = lang == "nl"
    meta = items[0][0]["metadata"]
    lines = [
        "# Statistisch Onderzoeksrapport (Falsifieerbaar)" if nl else "# Statistical Analysis Report (Falsifiable)",
        "",
        f"- **{'Bron' if nl else 'Source'}:** `{meta['filename']}`",
        f"- **{'Datum UTC' if nl else 'Date UTC'}:** `{meta['timestamp_utc']}`",
        f"- **{'Onderzoeksvraag' if nl else 'Research question'}:** {full_question or ('Niet opgegeven' if nl else 'Not specified')}",
        f"- **{'Aantal deelanalyses' if nl else 'Sub-analyses'}:** {len(items)}",
        "",
    ]
    for idx, (contract, phase2) in enumerate(items, start=1):
        res = contract["result"]
        sub_q = contract["plan"].get("question") or f"{contract['plan']['y']} ~ {', '.join(contract['plan']['xs'])}"
        lines.extend(
            [
                "---",
                f"## {'Deelanalyse' if nl else 'Sub-analysis'} {idx} — {sub_q}",
                f"- **{'Methode (Fase 1)' if nl else 'Method (Phase 1)'}:** {res['method']} (N = {res['n_complete']} / {res['n_total']})",
                "",
            ]
        )
        if phase2:
            lines.extend(
                [
                    "### Beslissingssamenvatting (Agent 3)" if nl else "### Decision Summary (Agent 3)",
                    phase2["agent3_business_summary"],
                    "",
                    "### Academisch Rapport — APA 7 (Agent 2)" if nl else "### Academic Report — APA 7 (Agent 2)",
                    phase2["agent2_apa7_report"],
                    "",
                    "### Methodologische Audit & Grenzen (Agent 1)" if nl else "### Methodological Audit & Limits (Agent 1)",
                ]
            )
            for a in phase2["agent1_methodology_audit"]:
                lines.append(f"- {a}")
            lines.append("")
        if res.get("contingency_table"):
            ct = res["contingency_table"]
            r_var, c_var = ct.get("row_var", "Row"), ct.get("col_var", "Col")
            cols_hdr = " | ".join(f"{c_var} = {c}" for c in ct["cols"])
            sep_hdr = " | ".join([":---:"] * len(ct["cols"]))
            lines.extend([f"### {'Kruistabel' if nl else 'Contingency table'}: {r_var} × {c_var}", f"| {r_var} \\ {c_var} | {cols_hdr} |", f"| :--- | {sep_hdr} |"])
            for r_lbl, r_counts in zip(ct["rows"], ct["counts"]):
                tot = sum(r_counts) or 1
                cells = " | ".join(f"{cnt}/{tot} ({cnt/tot*100:.1f} %)" for cnt in r_counts)
                lines.append(f"| {r_lbl} | {cells} |")
            lines.append("")
        lines.extend(
            [
                "### Diagnostiek (Fase 1)" if nl else "### Diagnostics (Phase 1)",
                "| Diagnostic | Series / Group | n | Statistic | p |",
                "| :--- | :--- | :---: | :---: | :---: |",
            ]
        )
        for d in contract.get("diagnostics", []):
            lines.append(_format_diag_row(d))
        lines.append("")

    lines.extend(["---", "## Reproducibility & Falsifiability Seal" if not nl else "## Zegel voor Reproduceerbaarheid & Falsifieerbaarheid", f"- **SHA-256 ({'origineel bestand' if nl else 'original file'}):** `{meta['sha256_raw_file']}`"])
    if meta.get("sha256_anonymized_file"):
        lines.append(f"- **SHA-256 ({'geanonimiseerde dataset' if nl else 'anonymised dataset'}):** `{meta['sha256_anonymized_file']}`")
    if meta.get("custom_missing"):
        lines.append(f"- **{'Gecodeerde ontbrekende waarden' if nl else 'Recoded missing codes'}:** `{', '.join(meta['custom_missing'])}`")
    env = meta["environment"]
    lines.append(f"- **{'Omgeving' if nl else 'Environment'}:** Python {env['python']} · NumPy {env['numpy']} · SciPy {env['scipy']} · Seed {env['seed']}")
    return "\n".join(lines)


def _figs_to_base64(contract: dict[str, Any], plot_data: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for title, fig in build_figures(contract, plot_data):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
        plt.close(fig)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        out.append({"title": title, "png_base64": b64})
    return out


# ---------------- SCHÉMAS PYDANTIC ----------------
class ScrubRequest(BaseModel):
    session_id: str
    columns: list[str]


class AutoPlanRequest(BaseModel):
    session_id: str
    question: str
    alpha: float = 0.05
    language: str = "nl"
    col_types: dict[str, str] | None = None


class RunRequest(BaseModel):
    session_id: str
    plans: list[dict[str, Any]]
    full_question: str = ""
    tier: str = "local_expert"
    language: str = "nl"
    llm_config: dict[str, Any] | None = None


class ExportRequest(BaseModel):
    session_id: str
    plans: list[dict[str, Any]] = Field(default_factory=list)
    full_question: str = ""
    tier: str = "local_expert"
    language: str = "nl"


# ---------------- ENDPOINTS GOUVERNANCE ----------------
@app.get("/api/health")
def health(lang: str = "nl") -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "3.0.0",
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "tiers": get_tiers(lang),
        "active_sessions": len(SESSIONS),
    }


@app.get("/api/governance/legal")
def governance_legal(lang: str = "nl") -> dict[str, Any]:
    return {"tiers": get_tiers(lang), "legal": get_legal(lang)}


@app.get("/api/governance/audit-log")
def governance_audit_log(
    x_user_id: str = Header(default="demo-user"),
    x_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    _check_user(x_user_id, x_api_key)
    return {"entries": read_recent_audit_logs(limit=30)}


@app.post("/api/admin/users/{target_user_id}/suspend")
def admin_suspend_user(target_user_id: str, x_admin_key: str | None = Header(default=None)) -> dict[str, Any]:
    _check_admin(x_admin_key)
    set_user_suspension(target_user_id, True)
    log_audit_event(action="admin_user_suspended", user_id=target_user_id)
    return {"user_id": target_user_id, "suspended": True}


@app.delete("/api/admin/users/{target_user_id}/suspend")
def admin_unsuspend_user(target_user_id: str, x_admin_key: str | None = Header(default=None)) -> dict[str, Any]:
    _check_admin(x_admin_key)
    set_user_suspension(target_user_id, False)
    log_audit_event(action="admin_user_unsuspended", user_id=target_user_id)
    return {"user_id": target_user_id, "suspended": False}


# ---------------- ENDPOINTS PHASE 1 & PHASE 2 ----------------
@app.post("/api/phase1/ingest")
async def phase1_ingest(
    file: UploadFile | None = File(default=None),
    pasted_text: str | None = Form(default=None),
    sep: str = Form(default="auto"),
    decimal: str = Form(default="auto"),
    has_header: bool = Form(default=True),
    custom_missing: str = Form(default="-999, -99"),
    x_user_id: str = Header(default="demo-user"),
) -> dict[str, Any]:
    _check_user(x_user_id)
    if file is not None:
        raw_bytes = await file.read()
        filename = file.filename or "upload.csv"
    elif pasted_text and pasted_text.strip():
        raw_bytes = pasted_text.encode("utf-8")
        filename = "pasted_data.csv"
    else:
        raise HTTPException(status_code=400, detail="Fournissez un fichier ou un tableau collé.")

    sep_arg = None if sep == "auto" else ("\t" if sep == "\\t" else sep)
    missing_list = [x.strip() for x in custom_missing.split(",") if x.strip()]

    try:
        df, meta = parse_dataset(
            raw_bytes,
            filename=filename,
            sep=sep_arg,
            decimal=decimal,
            has_header=has_header,
            custom_missing=missing_list,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erreur de lecture : {exc}")

    pii = scan_dataframe(df)
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "df": df,
        "meta": meta,
        "excluded_pii": [],
        "last_results": [],
        "last_access": time.time(),
    }

    log_audit_event(
        action="phase1_ingest",
        user_id=x_user_id,
        metadata={
            "filename": filename,
            "sha256_raw_file": meta["sha256_raw_file"],
            "pii_blocked_count": len(pii["flagged_columns"]),
        },
    )

    col_types = infer_column_types(df)
    preview = df.head(5).where(df.head(5).notna(), None).to_dict(orient="records")
    missing_counts = {c: {"observed": int(df[c].notna().sum()), "missing": int(df[c].isna().sum())} for c in df.columns}
    return {
        "session_id": session_id,
        "meta": meta,
        "pii": pii,
        "col_types": col_types,
        "missing_counts": missing_counts,
        "preview": preview,
    }


@app.post("/api/phase1/scrub")
def phase1_scrub(req: ScrubRequest, x_user_id: str = Header(default="demo-user")) -> dict[str, Any]:
    _check_user(x_user_id)
    sess = _get_session(req.session_id)
    df_clean = exclude_columns(sess["df"], req.columns)
    excluded = list(dict.fromkeys(sess["excluded_pii"] + [c for c in req.columns if c in sess["df"].columns]))
    anon_bytes = df_clean.to_csv(index=False).encode("utf-8")

    sess["df"] = df_clean
    sess["excluded_pii"] = excluded
    sess["meta"] = {
        **sess["meta"],
        "columns": list(df_clean.columns),
        "sha256_anonymized_file": sha256_bytes(anon_bytes),
        "excluded_pii_columns": excluded,
    }
    pii = scan_dataframe(df_clean)
    log_audit_event(
        action="phase1_scrub_pii",
        user_id=x_user_id,
        metadata={
            "filename": sess["meta"]["filename"],
            "sha256_anonymized_file": sess["meta"]["sha256_anonymized_file"],
            "excluded_pii_columns": excluded,
        },
    )
    return {
        "session_id": req.session_id,
        "meta": sess["meta"],
        "pii": pii,
        "col_types": infer_column_types(df_clean),
        "preview": df_clean.head(5).where(df_clean.head(5).notna(), None).to_dict(orient="records"),
    }


@app.post("/api/phase1/auto-plan")
def phase1_auto_plan(req: AutoPlanRequest, x_user_id: str = Header(default="demo-user")) -> dict[str, Any]:
    _check_user(x_user_id)
    sess = _get_session(req.session_id)
    if scan_dataframe(sess["df"])["blocked"]:
        raise HTTPException(status_code=403, detail="Données PII non purgées : utilisez /api/phase1/scrub d'abord.")
    col_types = req.col_types or infer_column_types(sess["df"])
    plans = auto_plan_from_question(req.question, sess["df"], col_types, alpha=req.alpha, language=req.language)
    warn_msg = (
        "Geen statistische analyse herkend die overeenkomt met de kolommen van dit bestand."
        if req.language == "nl"
        else "No statistical analysis matching the dataset columns was detected from this question."
    )
    return {
        "plans": plans,
        "matched": len(plans) > 0,
        "warning": None if plans else warn_msg,
    }


@app.post("/api/phase1/run")
def phase1_run(req: RunRequest, x_user_id: str = Header(default="demo-user")) -> dict[str, Any]:
    _check_user(x_user_id)
    sess = _get_session(req.session_id)
    if scan_dataframe(sess["df"])["blocked"]:
        raise HTTPException(status_code=403, detail="Exécution bloquée : données PII détectées.")
    if not req.plans:
        raise HTTPException(status_code=400, detail="Aucun plan d'analyse fourni.")

    results = []
    export_cache = []
    for plan in req.plans:
        plan_lang = {**plan, "language": plan.get("language") or req.language}
        try:
            contract, plot_data = run_analysis(sess["df"], plan_lang, sess["meta"])
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Calculation error ({plan.get('mode')}): {exc}")

        charts_b64 = _figs_to_base64(contract, plot_data)
        phase2 = None
        if req.tier != "autonome":
            llm_cfg = req.llm_config if req.tier == "confidentiel_zdr" else None
            phase2 = run_phase2_interpretation(contract, llm_config=llm_cfg)

        results.append({"contract": contract, "phase2": phase2, "charts": charts_b64})
        export_cache.append((contract, phase2, plot_data))

    sess["last_results"] = export_cache
    sess["last_question"] = req.full_question

    log_audit_event(
        action="phase1_and_2_run",
        user_id=x_user_id,
        tier=req.tier,
        metadata={
            "filename": sess["meta"]["filename"],
            "sha256_raw_file": sess["meta"]["sha256_raw_file"],
            "sha256_anonymized_file": sess["meta"].get("sha256_anonymized_file", ""),
            "modes_run": [p["mode"] for p in req.plans],
            "n_analyses": len(req.plans),
        },
    )
    return {"results": results}


def _resolve_export_items(sess: dict[str, Any], req: ExportRequest) -> list[tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]]:
    if sess.get("last_results"):
        return sess["last_results"]
    if not req.plans:
        raise HTTPException(status_code=400, detail="Exécutez au moins une analyse avant d'exporter.")
    items = []
    for p in req.plans:
        c, pd_d = run_analysis(sess["df"], p, sess["meta"])
        p2 = None if req.tier == "autonome" else run_phase2_interpretation(c)
        items.append((c, p2, pd_d))
    return items


@app.post("/api/export/{fmt}")
def export_report(fmt: str, req: ExportRequest, x_user_id: str = Header(default="demo-user")) -> Response:
    _check_user(x_user_id)
    sess = _get_session(req.session_id)
    items = _resolve_export_items(sess, req)
    full_q = req.full_question or sess.get("last_question", "")

    log_audit_event(
        action="export_report",
        user_id=x_user_id,
        tier=req.tier,
        metadata={"filename": sess["meta"]["filename"], "export_format": fmt},
    )

    if fmt == "pdf":
        data = build_pdf_report(items, full_q, lang=req.language)
        return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="statistical_report_apa7.pdf"'})
    if fmt == "docx":
        data = build_docx_report(items, full_q, lang=req.language)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="statistical_report_apa7.docx"'},
        )
    if fmt == "markdown":
        md = _build_markdown_report([(c, p2) for c, p2, _ in items], full_q, lang=req.language)
        return Response(content=md.encode("utf-8"), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="statistical_report_apa7.md"'})
    if fmt == "script":
        script = generate_reproducible_script(sess["df"], items[0][0])
        return Response(content=script.encode("utf-8"), media_type="text/x-python; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="analyse_reproductible.py"'})
    raise HTTPException(status_code=400, detail=f"Format d'export inconnu : {fmt}")


@app.post("/api/phase1/sample")
def phase1_sample(lang: str = "nl", x_user_id: str = Header(default="demo-user")) -> dict[str, Any]:
    """Loads a built-in realistic anonymised demo dataset + sample bilingual question."""
    _check_user(x_user_id)
    sample_csv = (
        "Department;Training;Score_Before;Score_After;Workload_Hours;Performance;Satisfaction\n"
        "Sales;Yes;58;72;38;74;7.2\nSales;Yes;62;76;41;84;7.5\nSales;No;50;52;48;61;6.0\n"
        "Sales;Yes;68;81;43;88;7.8\nSales;No;55;56;35;64;6.4\nSales;Yes;65;79;42;85;7.4\n"
        "Tech;Yes;60;78;42;89;8.1\nTech;Yes;72;89;44;92;8.6\nTech;No;54;56;50;59;6.8\n"
        "Tech;Yes;75;93;43;94;8.9\nTech;No;66;67;34;63;7.6\nTech;Yes;68;85;41;90;8.3\n"
        "Support;No;48;50;36;58;5.9\nSupport;Yes;56;69;42;83;6.8\nSupport;No;52;53;49;57;6.1\n"
        "Support;Yes;63;75;43;86;7.3\nSupport;No;58;59;35;62;6.5\nSupport;Yes;67;80;44;87;7.7\n"
    ).encode("utf-8")
    df, meta = parse_dataset(sample_csv, filename="demo_hr_study.csv", decimal="auto")
    pii = scan_dataframe(df)
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"df": df, "meta": meta, "excluded_pii": [], "last_results": [], "last_access": time.time()}
    sample_q = (
        "Verhoogt de training de score voor en na, beïnvloedt Workload_Hours de Performance, en verschilt Satisfaction per Department?"
        if lang == "nl"
        else "Does training increase Score_Before and Score_After, does Workload_Hours predict Performance, and does Satisfaction differ by Department?"
    )
    return {
        "session_id": session_id,
        "meta": meta,
        "pii": pii,
        "col_types": infer_column_types(df),
        "preview": df.head(5).where(df.head(5).notna(), None).to_dict(orient="records"),
        "sample_question": sample_q,
    }


@app.delete("/api/session/{session_id}")
def purge_session(session_id: str, x_user_id: str = Header(default="demo-user")) -> dict[str, Any]:
    _check_user(x_user_id)
    existed = SESSIONS.pop(session_id, None) is not None
    log_audit_event(action="zdr_session_purge", user_id=x_user_id, metadata={"session_purged": existed})
    return {"purged": existed}


# ---------------- FRONTEND SPA ----------------
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def serve_spa() -> FileResponse:
    return FileResponse(str(WEB_DIR / "index.html"))
