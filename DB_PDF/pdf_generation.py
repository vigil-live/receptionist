import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
PDF_OUTPUT_DIR = "reports"
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
PRIORITY_CONFIG = {
    1: {"label": "CRITICAL",  "color": colors.HexColor("#CC0000")},
    2: {"label": "HIGH",      "color": colors.HexColor("#E85D04")},
    3: {"label": "MODERATE",  "color": colors.HexColor("#F48C06")},
    4: {"label": "LOW",       "color": colors.HexColor("#2D6A4F")},
    5: {"label": "MINIMAL",   "color": colors.HexColor("#40916C")},
}
DARK_GRAY   = colors.HexColor("#1A1A2E")
MID_GRAY    = colors.HexColor("#4A4A6A")
LIGHT_GRAY  = colors.HexColor("#F5F5F5")
BORDER_GRAY = colors.HexColor("#CCCCCC")
WHITE       = colors.white
RED         = colors.HexColor("#CC0000")
BLUE        = colors.HexColor("#1B4F72")


def _styles():
    base = getSampleStyleSheet()

    custom = {
        "agency": ParagraphStyle("agency",
            fontSize=10, textColor=MID_GRAY,
            alignment=TA_CENTER, spaceBefore=6, spaceAfter=12),

        "doc_title": ParagraphStyle("doc_title",
            fontSize=26, textColor=DARK_GRAY, fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceBefore=10, spaceAfter=16),

        "doc_sub": ParagraphStyle("doc_sub",
            fontSize=10, textColor=MID_GRAY,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=20),

        "section_header": ParagraphStyle("section_header",
            fontSize=11, textColor=WHITE, fontName="Helvetica-Bold",
            leftIndent=8, spaceAfter=0),

        "field_label": ParagraphStyle("field_label",
            fontSize=8, textColor=MID_GRAY, fontName="Helvetica-Bold",
            spaceAfter=1),

        "field_value": ParagraphStyle("field_value",
            fontSize=10, textColor=DARK_GRAY,
            spaceAfter=6),

        "transcript_ai": ParagraphStyle("transcript_ai",
            fontSize=9, textColor=BLUE, fontName="Helvetica-Bold",
            leftIndent=12, spaceBefore=6, spaceAfter=2),

        "transcript_caller": ParagraphStyle("transcript_caller",
            fontSize=9, textColor=DARK_GRAY,
            leftIndent=12, spaceBefore=6, spaceAfter=2),

        "timestamp": ParagraphStyle("timestamp",
            fontSize=7, textColor=MID_GRAY,
            leftIndent=12, spaceAfter=8),

        "footer": ParagraphStyle("footer",
            fontSize=7, textColor=MID_GRAY,
            alignment=TA_CENTER),
    }
    return custom


def _section_header(title: str, bg_color=DARK_GRAY):
    data = [[Paragraph(f"  {title}", _styles()["section_header"])]]
    t = Table(data, colWidths=[7.0 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]))
    return t


def _priority_badge(priority: int):
    cfg   = PRIORITY_CONFIG.get(priority, PRIORITY_CONFIG[3])
    label = f"PRIORITY {priority}  —  {cfg['label']}"
    style = ParagraphStyle("badge",
        fontSize=12, textColor=WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER)
    data = [[Paragraph(label, style)]]
    t = Table(data, colWidths=[7.0 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), cfg["color"]),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def _info_grid(rows: list[tuple]):
    """Two-column label/value grid."""
    s = _styles()
    table_data = []
    for label, value in rows:
        table_data.append([
            Paragraph(label, s["field_label"]),
            Paragraph(str(value) if value else "—", s["field_value"]),
        ])
    t = Table(table_data, colWidths=[1.6 * inch, 5.4 * inch])
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, BORDER_GRAY),
    ]))
    return t

def _dispatch_table(dispatches: list[dict]):
    s = _styles()
    header_style = ParagraphStyle("dh", fontSize=9, textColor=WHITE,
                                  fontName="Helvetica-Bold", alignment=TA_CENTER)
    cell_style   = ParagraphStyle("dc", fontSize=9, textColor=DARK_GRAY,
                                  alignment=TA_CENTER)
    data = [[
        Paragraph("TYPE",          header_style),
        Paragraph("DISPATCHED BY", header_style),
        Paragraph("TIME",          header_style),
    ]]
    for d in dispatches:
        data.append([
            Paragraph(d.get("dispatch_type", "—").upper(), cell_style),
            Paragraph(d.get("dispatched_by", "—"),         cell_style),
            Paragraph(d.get("dispatched_at", "—"),         cell_style),
        ])

    t = Table(data, colWidths=[2.33 * inch, 2.33 * inch, 2.34 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  DARK_GRAY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID",          (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t

def _transcript_block(transcript: list[dict]):
    s      = _styles()
    items  = []
    for entry in transcript:
        speaker = entry.get("speaker", "unknown").lower()
        message = entry.get("message", "")
        ts      = entry.get("timestamp", "")

        if speaker == "ai":
            label = "[AI OPERATOR]"
            style = s["transcript_ai"]
        else:
            label = "[CALLER]"
            style = s["transcript_caller"]

        items.append(Paragraph(f"<b>{label}</b>   {message}", style))
        items.append(Paragraph(ts, s["timestamp"]))

    return items

def generate_report(call_data: dict, transcript: list[dict],
                    dispatches: list[dict]) -> str:
    call_id  = call_data.get("call_id", "UNKNOWN")
    priority = call_data.get("priority") or 3
    s        = _styles()

    filename = os.path.join(PDF_OUTPUT_DIR, f"report_{call_id}.pdf")

    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    story = []
    story.append(Spacer(1, 16))
    story.append(Paragraph("EMERGENCY RESPONSE SYSTEM", s["agency"]))
    story.append(Paragraph("911 INCIDENT REPORT", s["doc_title"]))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y  %H:%M:%S')}",
        s["doc_sub"]))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=2, color=DARK_GRAY))
    story.append(Spacer(1, 24))
    story.append(_priority_badge(priority))
    story.append(Spacer(1, 26))
    story.append(_section_header("INCIDENT DETAILS"))
    story.append(_info_grid([
        ("CALL ID",          call_id),
        ("CALLER NUMBER",    call_data.get("caller_number")),
        ("CALLER NAME",      call_data.get("caller_name")),
        ("EMERGENCY TYPE",   (call_data.get("emergency_type") or "").upper()),
        ("STATUS",           (call_data.get("status") or "").upper()),
        ("CALL START",       call_data.get("call_start")),
        ("CALL END",         call_data.get("call_end")),
    ]))
    story.append(Spacer(1, 20))
    story.append(_section_header("LOCATION"))
    story.append(_info_grid([
        ("ADDRESS",    call_data.get("location_raw")),
        ("LATITUDE",   call_data.get("latitude")),
        ("LONGITUDE",  call_data.get("longitude")),
    ]))
    story.append(Spacer(1, 20))
    story.append(_section_header("SITUATION SUMMARY"))
    story.append(_info_grid([
        ("INJURIES REPORTED",   "YES" if call_data.get("injuries_reported") else "NO"),
        ("HAZARDS PRESENT",     call_data.get("hazards_present")),
        ("PEOPLE AFFECTED",     call_data.get("num_people_affected")),
    ]))
    story.append(Spacer(1, 20))
    story.append(_section_header("DISPATCHED UNITS"))
    story.append(Spacer(1, 6))
    if dispatches:
        story.append(_dispatch_table(dispatches))
    else:
        story.append(Paragraph("  No units dispatched yet.", s["field_value"]))
    story.append(Spacer(1, 20))
    story.append(_section_header("CALL TRANSCRIPT"))
    story.append(Spacer(1, 8))
    if transcript:
        story.extend(_transcript_block(transcript))
    else:
        story.append(Paragraph("  No transcript available.", s["field_value"]))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "CONFIDENTIAL — For authorised emergency personnel only. "
        "This document was auto-generated by the AI-assisted 911 triage system.",
        s["footer"]))

    doc.build(story)
    return os.path.abspath(filename)