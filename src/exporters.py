"""Export natif PDF (ReportLab) et Word (.docx) avec graphiques intégrés."""

from __future__ import annotations

import io
import re
from typing import Any

import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.charts import build_figures


PRIMARY_HEX = "#2345b7"
PRIMARY_RL = colors.HexColor(PRIMARY_HEX)
LIGHT_BG_RL = colors.HexColor("#f0f4ff")
BORDER_RL = colors.HexColor("#d0d7de")


def _md_to_rl_xml(text: str) -> str:
    """Convertit un texte Markdown léger (**gras**, *italique*, `code`) en balises ReportLab."""
    s = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", s)
    # Nettoyer les emojis susceptibles de manquer dans les polices Helvetica standard
    s = re.sub(r"[^\x00-\u024F\u0370-\u03FF\u2000-\u22FF\u2500-\u257F]", "", s)
    return s.strip()


def _md_to_plain(text: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", str(text))
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    return s.strip()


def _fig_to_png_bytes(fig: plt.Figure, dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _fmt_p_cell(p_val: Any) -> str:
    if isinstance(p_val, (int, float)):
        return "< .001" if p_val < 0.001 else "." + f"{p_val:.3f}".split(".")[1]
    return "—"


def _rl_styled_table(data: list[list[str]], col_widths: list[float] | None = None) -> Table:
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_RL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG_RL]),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER_RL),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


EXPORT_LABELS: dict[str, dict[str, str]] = {
    "nl": {
        "title": "Statistisch Onderzoeksrapport (Falsifieerbaar)",
        "source": "Bron",
        "date": "Datum UTC",
        "analyses": "Deelanalyses",
        "question": "Onderzoeksvraag",
        "method": "Methode Fase 1",
        "biz": "Beslissingssamenvatting (Begrijpelijke taal)",
        "apa": "Academisch Rapport — APA 7",
        "audit": "Methodologische Audit & Grenzen",
        "diag": "Diagnostiek Fase 1",
        "seal": "Zegel voor Falsifieerbaarheid & Reproduceerbaarheid",
        "sha_raw": "SHA-256 (origineel bestand)",
        "sha_anon": "SHA-256 (geanonimiseerde dataset)",
        "missing": "Gecodeerde ontbrekende waarden",
        "env": "Omgeving",
    },
    "en": {
        "title": "Statistical Analysis Report (Falsifiable)",
        "source": "Source",
        "date": "Date UTC",
        "analyses": "Sub-analyses",
        "question": "Research question",
        "method": "Phase 1 Method",
        "biz": "Decision Summary (Plain Language)",
        "apa": "Academic Report — APA 7",
        "audit": "Methodological Audit & Limits",
        "diag": "Phase 1 Diagnostics",
        "seal": "Falsifiability & Reproducibility Seal",
        "sha_raw": "SHA-256 (original file)",
        "sha_anon": "SHA-256 (anonymised dataset)",
        "missing": "Recoded missing codes",
        "env": "Environment",
    },
    "fr": {
        "title": "Rapport d'Étude Statistique Circonstancié (Falsifiable)",
        "source": "Source",
        "date": "Date UTC",
        "analyses": "Sous-analyses",
        "question": "Question globale",
        "method": "Méthode Phase 1",
        "biz": "Synthèse Décisionnelle (Langage clair)",
        "apa": "Rapport Académique — Normes APA 7",
        "audit": "Audit Méthodologique & Limites",
        "diag": "Diagnostics chiffrés (Phase 1)",
        "seal": "Sceau de Falsifiabilité & Reproductibilité",
        "sha_raw": "SHA-256 (fichier brut d'origine)",
        "sha_anon": "SHA-256 (jeu anonymisé)",
        "missing": "Codes manquants recodés",
        "env": "Environnement",
    },
}


def build_pdf_report(
    items: list[tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]],
    full_question: str = "",
    lang: str = "fr",
) -> bytes:
    """Génère un rapport PDF professionnel bilingue (NL / EN / FR) avec graphiques intégrés et sceau SHA-256."""
    lb = EXPORT_LABELS.get(lang, EXPORT_LABELS["en"])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=lb["title"],
    )

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle("TitleXL", parent=styles["Title"], textColor=PRIMARY_RL, fontSize=18, spaceAfter=6)
    s_h1 = ParagraphStyle("H1XL", parent=styles["Heading1"], textColor=PRIMARY_RL, fontSize=13, spaceBefore=12, spaceAfter=4)
    s_h2 = ParagraphStyle("H2XL", parent=styles["Heading2"], textColor=colors.HexColor("#1f2937"), fontSize=10.5, spaceBefore=8, spaceAfter=3)
    s_body = ParagraphStyle("BodyXL", parent=styles["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
    s_box = ParagraphStyle("BoxXL", parent=s_body, backColor=LIGHT_BG_RL, borderPadding=6, borderColor=PRIMARY_RL, borderWidth=0.6)
    s_small = ParagraphStyle("SmallXL", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#4b5563"))

    story: list[Any] = []
    meta = items[0][0]["metadata"]

    story.append(Paragraph(lb["title"], s_title))
    story.append(
        Paragraph(
            _md_to_rl_xml(
                f"**{lb['source']}:** `{meta['filename']}` · **{lb['date']}:** `{meta['timestamp_utc'][:19]}Z` · "
                f"**{lb['analyses']}:** {len(items)}"
            ),
            s_small,
        )
    )
    if full_question:
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(_md_to_rl_xml(f"**{lb['question']}:** {full_question}"), s_body))
    story.append(Spacer(1, 0.3 * cm))

    for idx, (contract, phase2, plot_data) in enumerate(items, start=1):
        res = contract["result"]
        sub_q = contract["plan"].get("question") or f"{contract['plan']['y']} ~ {', '.join(contract['plan']['xs'])}"
        story.append(Paragraph(_md_to_rl_xml(f"{idx}. {sub_q}"), s_h1))
        story.append(
            Paragraph(
                _md_to_rl_xml(f"**{lb['method']}:** {res['method']} (N = {res['n_complete']} / {res['n_total']})"),
                s_small,
            )
        )

        if phase2:
            story.append(Paragraph(lb["biz"], s_h2))
            story.append(Paragraph(_md_to_rl_xml(phase2["agent3_business_summary"]), s_box))
            story.append(Spacer(1, 0.15 * cm))
            story.append(Paragraph(lb["apa"], s_h2))
            story.append(Paragraph(_md_to_rl_xml(phase2["agent2_apa7_report"]), s_body))

            story.append(Paragraph(lb["audit"], s_h2))
            for al in phase2["agent1_methodology_audit"]:
                story.append(Paragraph(f"• {_md_to_rl_xml(al)}", s_body))

        # Tableau des coefficients / groupes / contingence
        if contract.get("coefficients"):
            hdr = ["Terme", "B", "SE", "Stat", "p", "VIF", "IC 95 %"]
            rows = [hdr]
            for c in contract["coefficients"]:
                stat_c = c.get("t", c.get("z"))
                ci_c = c.get("ci_95") or [None, None]
                ci_s = f"[{ci_c[0]}, {ci_c[1]}]" if ci_c[0] is not None else "—"
                rows.append(
                    [
                        str(c["term"]),
                        str(c["B"]),
                        str(c["SE"]),
                        str(stat_c if stat_c is not None else "—"),
                        _fmt_p_cell(c.get("p")),
                        str(c["VIF"]) if c.get("VIF") is not None else "—",
                        ci_s,
                    ]
                )
            story.append(Spacer(1, 0.15 * cm))
            story.append(_rl_styled_table(rows))

        elif contract.get("groups"):
            hdr = ["Groupe / Condition", "n", "Moyenne", "Médiane", "SD"]
            rows = [hdr]
            for g in contract["groups"]:
                rows.append([str(g["label"]), str(g["n"]), str(g["mean"]), str(g["median"]), str(g["sd"])])
            story.append(Spacer(1, 0.15 * cm))
            story.append(_rl_styled_table(rows))

        if res.get("contingency_table"):
            ct = res["contingency_table"]
            r_var = ct.get("row_var", "Ligne")
            c_var = ct.get("col_var", "Colonne")
            rows = [[f"{r_var} \\ {c_var}"] + [f"{c_var}={c}" for c in ct["cols"]]]
            for rl, rc in zip(ct["rows"], ct["counts"]):
                tot = sum(rc) or 1
                rows.append([str(rl)] + [f"{cnt}/{tot} ({cnt/tot*100:.1f}%)" for cnt in rc])
            story.append(Spacer(1, 0.15 * cm))
            story.append(_rl_styled_table(rows))

        if contract.get("diagnostics"):
            rows = [["Diagnostic", "Série / Groupe", "n", "Statistique", "p"]]
            for d in contract["diagnostics"]:
                st_s = f"{d['statistic']:.3f}" if isinstance(d["statistic"], (int, float)) else "—"
                rows.append([str(d["name"]), str(d["label"]), str(d["n"]), st_s, _fmt_p_cell(d["p"])])
            story.append(Spacer(1, 0.15 * cm))
            story.append(_rl_styled_table(rows))

        # Graphiques intégrés
        figs = build_figures(contract, plot_data)
        for _, fig in figs:
            png_bytes = _fig_to_png_bytes(fig, dpi=140)
            story.append(Spacer(1, 0.2 * cm))
            story.append(RLImage(io.BytesIO(png_bytes), width=16.2 * cm, height=7.2 * cm, kind="proportional"))

        story.append(Spacer(1, 0.35 * cm))

    # Sceau de falsifiabilité
    story.append(Paragraph(lb["seal"], s_h1))
    env = meta["environment"]
    seal_lines = [f"**{lb['sha_raw']}:** `{meta['sha256_raw_file']}`"]
    if meta.get("sha256_anonymized_file"):
        seal_lines.append(f"**{lb['sha_anon']}:** `{meta['sha256_anonymized_file']}`")
    if meta.get("custom_missing"):
        seal_lines.append(f"**{lb['missing']}:** `{', '.join(meta['custom_missing'])}`")
    seal_lines.append(
        f"**{lb['env']}:** Python {env['python']} · NumPy {env['numpy']} · SciPy {env['scipy']} · Seed {env['seed']}"
    )
    for ln in seal_lines:
        story.append(Paragraph(_md_to_rl_xml(ln), s_small))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def build_docx_report(
    items: list[tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]],
    full_question: str = "",
    lang: str = "fr",
) -> bytes:
    """Génère un rapport Word (.docx) bilingue éditable avec tableaux, graphiques et sceau SHA-256."""
    lb = EXPORT_LABELS.get(lang, EXPORT_LABELS["en"])
    doc = Document()
    meta = items[0][0]["metadata"]

    title = doc.add_heading(lb["title"], level=0)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x23, 0x45, 0xB7)

    p_meta = doc.add_paragraph()
    p_meta.add_run(f"{lb['source']}: {meta['filename']}  |  {lb['date']}: {meta['timestamp_utc'][:19]}Z  |  {lb['analyses']}: {len(items)}").font.size = Pt(9)
    if full_question:
        p_q = doc.add_paragraph()
        r_q = p_q.add_run(f"{lb['question']}: ")
        r_q.bold = True
        p_q.add_run(full_question)

    for idx, (contract, phase2, plot_data) in enumerate(items, start=1):
        res = contract["result"]
        sub_q = contract["plan"].get("question") or f"{contract['plan']['y']} ~ {', '.join(contract['plan']['xs'])}"
        doc.add_heading(f"{idx}. {sub_q}", level=1)
        doc.add_paragraph(f"{lb['method']}: {res['method']} (N = {res['n_complete']} / {res['n_total']})")

        if phase2:
            doc.add_heading(lb["biz"], level=2)
            doc.add_paragraph(_md_to_plain(phase2["agent3_business_summary"]))

            doc.add_heading(lb["apa"], level=2)
            doc.add_paragraph(_md_to_plain(phase2["agent2_apa7_report"]))

            doc.add_heading(lb["audit"], level=2)
            for al in phase2["agent1_methodology_audit"]:
                doc.add_paragraph(_md_to_plain(al), style="List Bullet")

        if contract.get("diagnostics"):
            doc.add_heading(lb["diag"], level=2)
            tbl = doc.add_table(rows=1, cols=5)
            tbl.style = "Light Grid Accent 1"
            for i_h, h in enumerate(["Diagnostic", "Series / Group", "n", "Statistic", "p"]):
                tbl.rows[0].cells[i_h].text = h
            for d in contract["diagnostics"]:
                row_c = tbl.add_row().cells
                row_c[0].text = str(d["name"])
                row_c[1].text = str(d["label"])
                row_c[2].text = str(d["n"])
                row_c[3].text = f"{d['statistic']:.3f}" if isinstance(d["statistic"], (int, float)) else "—"
                row_c[4].text = _fmt_p_cell(d["p"])

        for _, fig in build_figures(contract, plot_data):
            png_bytes = _fig_to_png_bytes(fig, dpi=140)
            doc.add_picture(io.BytesIO(png_bytes), width=Inches(6.0))

    doc.add_heading(lb["seal"], level=1)
    env = meta["environment"]
    doc.add_paragraph(f"{lb['sha_raw']}: {meta['sha256_raw_file']}")
    if meta.get("sha256_anonymized_file"):
        doc.add_paragraph(f"{lb['sha_anon']}: {meta['sha256_anonymized_file']}")
    if meta.get("custom_missing"):
        doc.add_paragraph(f"{lb['missing']}: {', '.join(meta['custom_missing'])}")
    doc.add_paragraph(f"{lb['env']}: Python {env['python']} · NumPy {env['numpy']} · SciPy {env['scipy']} · Seed {env['seed']}")

    out = io.BytesIO()
    doc.save(out)
    out.seek(0)
    return out.getvalue()
