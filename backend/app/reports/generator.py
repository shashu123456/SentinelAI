import io
import json
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Frame, PageTemplate,
    BaseDocTemplate, Flowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ============================================================================
# DESIGN TOKENS
# ============================================================================
NAVY_900 = colors.HexColor("#0F172A")
NAVY_800 = colors.HexColor("#1E293B")
NAVY_700 = colors.HexColor("#334155")
NAVY_600 = colors.HexColor("#475569")
NAVY_500 = colors.HexColor("#64748B")
NAVY_400 = colors.HexColor("#94A3B8")
NAVY_300 = colors.HexColor("#CBD5E1")
NAVY_100 = colors.HexColor("#F1F5F9")
NAVY_50 = colors.HexColor("#F8FAFC")

BLUE_600 = colors.HexColor("#2563EB")
BLUE_500 = colors.HexColor("#3B82F6")
BLUE_100 = colors.HexColor("#DBEAFE")

RED_700 = colors.HexColor("#B91C1C")
RED_600 = colors.HexColor("#DC2626")
RED_100 = colors.HexColor("#FEE2E2")

ORANGE_600 = colors.HexColor("#EA580C")
ORANGE_100 = colors.HexColor("#FFEDD5")

AMBER_600 = colors.HexColor("#D97706")
AMBER_100 = colors.HexColor("#FEF3C7")

GREEN_600 = colors.HexColor("#16A34A")
GREEN_100 = colors.HexColor("#DCFCE7")

GRAY_600 = colors.HexColor("#4B5563")
GRAY_400 = colors.HexColor("#9CA3AF")
GRAY_200 = colors.HexColor("#E5E7EB")
GRAY_100 = colors.HexColor("#F3F4F6")
GRAY_50 = colors.HexColor("#F9FAFB")

WHITE = colors.white
BLACK = colors.HexColor("#000000")

SEVERITY_COLORS = {
    "Critical": RED_600,
    "High": ORANGE_600,
    "Medium": AMBER_600,
    "Low": GREEN_600,
    "Info": GRAY_400,
}

SEVERITY_BG = {
    "Critical": RED_100,
    "High": ORANGE_100,
    "Medium": AMBER_100,
    "Low": GREEN_100,
    "Info": GRAY_100,
}

OWASP_NAMES = {
    "API1": "Broken Object Level Authorization",
    "API2": "Broken Authentication",
    "API3": "Broken Object Property Level Authorization",
    "API4": "Unrestricted Resource Consumption",
    "API5": "Broken Function Level Authorization",
    "API6": "Unrestricted Access to Sensitive Business Flows",
    "API7": "Server Side Request Forgery",
    "API8": "Security Misconfiguration",
    "API9": "Improper Inventory Management",
    "API10": "Unsafe Consumption of APIs",
}

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch


# ============================================================================
# CUSTOM FLOWABLES
# ============================================================================
class CircleScore(Flowable):
    """Draws a large circular risk score for the cover page."""

    def __init__(self, score, level, width=220, height=260):
        Flowable.__init__(self)
        self.score = score
        self.level = level
        self.width = width
        self.height = height

    def _get_color(self):
        if self.score >= 80: return RED_600
        if self.score >= 60: return ORANGE_600
        if self.score >= 30: return AMBER_600
        return GREEN_600

    def draw(self):
        c = self.canv
        cx = self.width / 2
        cy = self.height / 2 + 15
        r = 80
        clr = self._get_color()

        # Outer glow
        c.setStrokeColor(colors.Color(clr.red, clr.green, clr.blue, 0.15))
        c.setLineWidth(16)
        c.circle(cx, cy, r + 8, stroke=1, fill=0)

        # Track circle
        c.setStrokeColor(GRAY_200)
        c.setLineWidth(10)
        c.circle(cx, cy, r, stroke=1, fill=0)

        # Score arc
        c.setStrokeColor(clr)
        c.setLineWidth(10)
        c.setLineCap(1)
        if self.score > 0:
            start_angle = 90
            extent = -(self.score / 100.0) * 360
            c.arc(cx - r, cy - r, cx + r, cy + r, start_angle, extent)

        # Score number
        c.setFillColor(NAVY_900)
        c.setFont("Helvetica-Bold", 48)
        c.drawCentredString(cx, cy - 8, str(self.score))

        # /100 label below score
        c.setFillColor(NAVY_500)
        c.setFont("Helvetica", 12)
        c.drawCentredString(cx, cy - 30, "/100 POINTS")

        # Level badge
        level_title = self.level.title() if self.level.isupper() else self.level
        badge_text = f"  {level_title}  "
        tw = c.stringWidth(badge_text, "Helvetica-Bold", 12) + 24
        bx = cx - tw / 2
        c.setFillColor(colors.Color(clr.red, clr.green, clr.blue, 0.08))
        c.setStrokeColor(colors.Color(clr.red, clr.green, clr.blue, 0.3))
        c.setLineWidth(1)
        c.roundRect(bx, cy - r - 36, tw, 26, 13, stroke=1, fill=1)
        c.setFillColor(clr)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(cx, cy - r - 28, level_title)


class MetricCard(Flowable):
    """A small metric card for the executive summary."""

    def __init__(self, value, label, accent_color, width=145, height=72):
        Flowable.__init__(self)
        self.value = str(value)
        self.label = label
        self.accent = accent_color
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        # Background
        c.setFillColor(NAVY_50)
        c.roundRect(0, 0, self.width, self.height, 8, stroke=0, fill=1)
        # Accent bar
        c.setFillColor(self.accent)
        c.roundRect(0, 0, 4, self.height, 2, stroke=0, fill=1)
        # Value
        c.setFillColor(NAVY_900)
        c.setFont("Helvetica-Bold", 26)
        c.drawString(16, self.height - 32, self.value)
        # Label
        c.setFillColor(NAVY_500)
        c.setFont("Helvetica", 9)
        c.drawString(16, 12, self.label)


# ============================================================================
# HEADER / FOOTER
# ============================================================================
def _header_footer(canvas, doc):
    canvas.saveState()
    page_num = canvas.getPageNumber()

    if page_num > 1:
        # Header line
        canvas.setStrokeColor(GRAY_200)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, PAGE_H - 0.6 * inch, PAGE_W - MARGIN, PAGE_H - 0.6 * inch)
        # Header text
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(NAVY_500)
        canvas.drawString(MARGIN, PAGE_H - 0.55 * inch, "SENTINELAI")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(NAVY_400)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.55 * inch, "Security Assessment Report")

    # Footer line
    canvas.setStrokeColor(GRAY_200)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 0.55 * inch, PAGE_W - MARGIN, 0.55 * inch)
    # Footer text
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(NAVY_400)
    canvas.drawString(MARGIN, 0.38 * inch, f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    canvas.drawCentredString(PAGE_W / 2, 0.38 * inch, "CONFIDENTIAL")
    canvas.drawRightString(PAGE_W - MARGIN, 0.38 * inch, f"Page {page_num}")

    canvas.restoreState()


# ============================================================================
# HELPER
# ============================================================================
def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _severity_color_hex(severity):
    clr = SEVERITY_COLORS.get(severity, NAVY_900)
    return clr.hexval()


def _severity_bg_hex(severity):
    clr = SEVERITY_BG.get(severity, GRAY_100)
    return clr.hexval()


# ============================================================================
# MAIN GENERATOR
# ============================================================================
def generate_pdf_report(scan_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.85 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
    )
    styles = getSampleStyleSheet()
    story = []

    # ----------------------------------------------------------------
    # STYLES
    # ----------------------------------------------------------------
    title_style = ParagraphStyle(
        "CoverTitle", parent=styles["Title"],
        fontSize=36, textColor=NAVY_900, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4, leading=42,
    )
    subtitle_style = ParagraphStyle(
        "CoverSub", parent=styles["Normal"],
        fontSize=14, textColor=NAVY_500, alignment=TA_CENTER, spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"],
        fontSize=18, textColor=NAVY_900, fontName="Helvetica-Bold",
        spaceBefore=24, spaceAfter=6, leading=22,
    )
    subsection_style = ParagraphStyle(
        "SubSection", parent=styles["Normal"],
        fontSize=12, fontName="Helvetica-Bold", textColor=NAVY_700,
        spaceBefore=10, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=15, textColor=NAVY_700,
    )
    small_style = ParagraphStyle(
        "Small", parent=styles["Normal"],
        fontSize=9, leading=13, textColor=NAVY_500,
    )
    label_style = ParagraphStyle(
        "Label", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica-Bold", textColor=NAVY_500,
        spaceAfter=2, leading=11,
    )
    value_style = ParagraphStyle(
        "Value", parent=styles["Normal"],
        fontSize=10, leading=14, textColor=NAVY_700,
    )
    meta_style = ParagraphStyle(
        "Meta", parent=styles["Normal"],
        fontSize=9, leading=12, textColor=NAVY_500, alignment=TA_CENTER,
    )

    CONTENT_W = PAGE_W - 2 * MARGIN

    # ================================================================
    # COVER PAGE
    # ================================================================
    story.append(Spacer(1, 0.6 * inch))

    # Shield icon drawn with text
    shield_style = ParagraphStyle(
        "Shield", parent=styles["Normal"],
        fontSize=14, fontName="Helvetica-Bold", textColor=BLUE_500,
        alignment=TA_CENTER, spaceAfter=12,
    )
    story.append(Paragraph("[ SHIELD ]", shield_style))

    story.append(Paragraph("SentinelAI", title_style))
    story.append(Spacer(1, 6))

    # Blue accent line
    story.append(HRFlowable(width="25%", thickness=3, color=BLUE_500, spaceAfter=16))

    story.append(Paragraph("Security Assessment Report", subtitle_style))
    story.append(Spacer(1, 8))

    # Target info
    cover_info_style = ParagraphStyle(
        "CoverInfo", parent=styles["Normal"],
        fontSize=12, textColor=NAVY_600, alignment=TA_CENTER, leading=18,
    )
    story.append(Paragraph(
        f"Target API: <b>{_escape(scan_data.get('api_name', 'N/A'))}</b>",
        cover_info_style,
    ))
    story.append(Paragraph(
        f"Version {_escape(scan_data.get('api_version', 'N/A'))}  |  {_escape(scan_data.get('scan_date', 'N/A'))}",
        ParagraphStyle("CoverDate", parent=styles["Normal"], fontSize=11, textColor=NAVY_400, alignment=TA_CENTER),
    ))

    story.append(Spacer(1, 28))

    # Risk Score Circle
    risk_score = scan_data.get("risk_score", 0)
    risk_level = scan_data.get("risk_level", "Unknown").title()
    circle = CircleScore(risk_score, risk_level, width=220, height=220)
    # Wrap in a centered table
    circle_table = Table([[circle]], colWidths=[CONTENT_W])
    circle_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
    ]))
    story.append(circle_table)

    story.append(Spacer(1, 40))

    # Confidential badge
    story.append(HRFlowable(width="60%", thickness=0.5, color=GRAY_200, spaceAfter=12))
    story.append(Paragraph(
        "CONFIDENTIAL - For authorized recipients only",
        ParagraphStyle("Conf", parent=styles["Normal"], fontSize=9, textColor=NAVY_400, alignment=TA_CENTER),
    ))

    story.append(PageBreak())

    # ================================================================
    # EXECUTIVE SUMMARY
    # ================================================================
    story.append(Paragraph("Executive Summary", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY_200, spaceAfter=14))

    findings = scan_data.get("findings", [])
    total = len(findings)
    severity_counts = {}
    for f in findings:
        sev = f.get("severity", "Info")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    crit = severity_counts.get("Critical", 0)
    high = severity_counts.get("High", 0)
    crit_high = crit + high

    # Summary paragraph
    if total == 0:
        summary = "No security vulnerabilities were identified. The API specification appears to follow security best practices."
    else:
        summary = (
            f"The security assessment of <b>{_escape(scan_data.get('api_name', 'the API'))}</b> identified "
            f"<b>{total}</b> security finding{'s' if total != 1 else ''} across the OWASP API Security Top 10. "
        )
        if crit_high > 0:
            summary += (
                f"<b><font color='#DC2626'>{crit_high}</font></b> finding{'s are' if crit_high != 1 else ' is'} "
                f"rated <b>Critical</b> or <b>High</b> severity and require{'s' if crit_high == 1 else ''} immediate remediation. "
            )
        if severity_counts.get("Medium", 0) > 0:
            summary += (
                f"Additionally, <b>{severity_counts['Medium']}</b> medium-severity "
                f"issue{'s' if severity_counts['Medium'] != 1 else ''} should be addressed in the near term. "
            )
    story.append(Paragraph(summary, body_style))
    story.append(Spacer(1, 18))

    # Metric cards row
    endpoints = scan_data.get("total_endpoints", 0)
    card_w = (CONTENT_W - 30) / 4
    metric_row = [
        [
            MetricCard(str(risk_score), "Risk Score", SEVERITY_COLORS.get(
                "Critical" if risk_score >= 80 else "High" if risk_score >= 60 else "Medium" if risk_score >= 30 else "Low",
                NAVY_900
            ), width=card_w),
            MetricCard(str(total), "Total Findings", RED_600 if total > 0 else GREEN_600, width=card_w),
            MetricCard(str(crit_high), "Critical & High", RED_600 if crit_high > 0 else GREEN_600, width=card_w),
            MetricCard(str(endpoints), "Endpoints Scanned", BLUE_500, width=card_w),
        ]
    ]
    metric_table = Table(metric_row, colWidths=[card_w + 10] * 4)
    metric_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 20))

    # Severity distribution
    if findings:
        story.append(Paragraph("Severity Distribution", subsection_style))
        story.append(Spacer(1, 6))

        # Stacked bar
        bar_data = [[]]
        bar_style_cmds = [
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]
        col_widths = []
        for sev in ["Critical", "High", "Medium", "Low", "Info"]:
            cnt = severity_counts.get(sev, 0)
            if cnt > 0:
                w = max((cnt / total) * CONTENT_W, 40)
                col_widths.append(w)
                bar_data[0].append(Paragraph(
                    f'<font color="white" size="11"><b>{cnt}</b></font>',
                    ParagraphStyle("BC", alignment=TA_CENTER, fontSize=11),
                ))
                bar_style_cmds.append(("BACKGROUND", (len(col_widths)-1, 0), (len(col_widths)-1, 0), SEVERITY_COLORS[sev]))
            else:
                col_widths.append(0)

        # Remove zero-width columns
        final_data = [[]]
        final_widths = []
        idx = 0
        for sev in ["Critical", "High", "Medium", "Low", "Info"]:
            cnt = severity_counts.get(sev, 0)
            if cnt > 0:
                final_data[0].append(bar_data[0][idx])
                final_widths.append(max((cnt / total) * CONTENT_W, 40))
            idx += 1

        if final_data[0]:
            bar = Table(final_data, colWidths=final_widths, rowHeights=[36])
            bar.setStyle(TableStyle(bar_style_cmds[:len(final_data[0]) + 3]))
            story.append(bar)
            story.append(Spacer(1, 8))

            # Legend row
            legend_items = []
            for sev in ["Critical", "High", "Medium", "Low", "Info"]:
                cnt = severity_counts.get(sev, 0)
                if cnt > 0:
                    legend_items.append(Paragraph(
                        f'<font color="{_severity_color_hex(sev)}">&#9632;</font> '
                        f'<font color="{NAVY_600.hexval()}" size="9">{sev}: {cnt} ({cnt/total*100:.0f}%)</font>',
                        ParagraphStyle("Leg", fontSize=9, leading=14),
                    ))
            legend = Table([legend_items], colWidths=[CONTENT_W / len(legend_items)] * len(legend_items))
            legend.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(legend)
            story.append(Spacer(1, 16))

    # Scan details
    story.append(Paragraph("Scan Details", subsection_style))
    detail_data = [
        ["Field", "Value"],
        ["API Name", _escape(scan_data.get("api_name", "N/A"))],
        ["API Version", _escape(scan_data.get("api_version", "N/A"))],
        ["Scan Date", _escape(scan_data.get("scan_date", "N/A"))],
        ["Total Endpoints", str(endpoints)],
        ["Total Findings", str(total)],
        ["Risk Score", f"{risk_score}/100 ({risk_level})"],
    ]
    dt = Table(detail_data, colWidths=[2.2 * inch, CONTENT_W - 2.2 * inch])
    dt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_900),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (0, -1), NAVY_50),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 1), (0, -1), NAVY_600),
        ("TEXTCOLOR", (1, 1), (1, -1), NAVY_700),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY_200),
    ]))
    story.append(dt)

    story.append(PageBreak())

    # ================================================================
    # DETAILED FINDINGS
    # ================================================================
    story.append(Paragraph("Detailed Findings", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY_200, spaceAfter=8))
    story.append(Paragraph(
        "Each finding below represents a potential security issue identified through static analysis "
        "of the API specification. Manual verification is recommended before confirming exploitability.",
        small_style,
    ))
    story.append(Spacer(1, 14))

    if not findings:
        story.append(Paragraph(
            "No vulnerabilities were identified. The API specification appears to follow security best practices.",
            body_style,
        ))
    else:
        sorted_findings = sorted(
            findings,
            key=lambda x: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}.get(x.get("severity", "Info"), 5)
        )

        for i, finding in enumerate(sorted_findings, 1):
            severity = finding.get("severity", "Info")
            sev_clr = _severity_color_hex(severity)
            sev_bg = _severity_bg_hex(severity)
            confidence = finding.get("confidence", 85)
            owasp = finding.get("owasp_category", "N/A")
            cwe = finding.get("cwe_id", "N/A")

            # ---- Finding Card ----
            # Header bar
            header_inner = [[
                Paragraph(
                    f'<font color="{sev_clr}" size="11"><b>[{severity.upper()}]</b></font>'
                    f'  <font size="11"><b>{_escape(finding.get("vulnerability_name", "Unknown"))}</b></font>',
                    ParagraphStyle("FH", fontSize=11, fontName="Helvetica-Bold", textColor=NAVY_900),
                ),
                Paragraph(
                    f'<font size="8" color="{NAVY_500.hexval()}">Confidence: </font>'
                    f'<font size="9" color="{NAVY_900.hexval()}"><b>{confidence}%</b></font>',
                    ParagraphStyle("FC", fontSize=9, alignment=TA_RIGHT),
                ),
            ]]
            hdr = Table(header_inner, colWidths=[CONTENT_W - 110, 100])
            hdr.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(sev_bg)),
                ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor(sev_clr)),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))

            # OWASP + CWE tags
            tags = []
            tags.append(Paragraph(
                f'<font color="{NAVY_600.hexval()}" size="8">OWASP: </font>'
                f'<font color="{BLUE_600.hexval()}" size="8"><b>{owasp}</b></font>'
                f'<font color="{NAVY_400.hexval()}" size="8"> - {_escape(OWASP_NAMES.get(owasp, ""))}</font>',
                ParagraphStyle("Tag1", fontSize=8, leading=11),
            ))
            if cwe and cwe != "N/A":
                tags.append(Paragraph(
                    f'<font color="{NAVY_600.hexval()}" size="8">CWE: </font>'
                    f'<font color="{GREEN_600.hexval()}" size="8"><b>{cwe}</b></font>',
                    ParagraphStyle("Tag2", fontSize=8, leading=11),
                ))
            tag_row = [[tags[0], tags[1] if len(tags) > 1 else Paragraph("", ParagraphStyle("Empty"))]]
            tag_table = Table(tag_row, colWidths=[CONTENT_W / 2, CONTENT_W / 2])
            tag_table.setStyle(TableStyle([
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]))

            # Detail fields
            detail_rows = []

            def _add_field(label, text):
                if text and text != "N/A" and str(text).strip():
                    detail_rows.append([
                        Paragraph(f"<b>{label}</b>", label_style),
                        Paragraph(_escape(str(text)), value_style),
                    ])

            _add_field("ENDPOINT", f'{finding.get("affected_method", "N/A")} {finding.get("affected_endpoint", "N/A")}')
            _add_field("DESCRIPTION", finding.get("description", ""))
            _add_field("DETECTION REASON", finding.get("detection_reason", ""))
            _add_field("EVIDENCE", finding.get("evidence", ""))
            _add_field("IMPACT", finding.get("impact", ""))
            _add_field("REMEDIATION", finding.get("remediation", ""))

            if finding.get("false_positive_note"):
                detail_rows.append([
                    Paragraph("<b>FALSE POSITIVE NOTE</b>", ParagraphStyle(
                        "FPLabel", parent=label_style, textColor=AMBER_600,
                    )),
                    Paragraph(
                        f'<i>{_escape(finding["false_positive_note"])}</i>',
                        ParagraphStyle("FPVal", parent=value_style, fontSize=9, textColor=NAVY_500),
                    ),
                ])

            detail_table = Table(detail_rows, colWidths=[1.4 * inch, CONTENT_W - 1.4 * inch])
            detail_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), NAVY_50),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, GRAY_200),
            ]))

            finding_block = KeepTogether([
                hdr,
                tag_table,
                detail_table,
                Spacer(1, 18),
            ])
            story.append(finding_block)

    # ================================================================
    # AI ANALYSIS
    # ================================================================
    ai_analysis = scan_data.get("ai_analysis")
    if ai_analysis:
        story.append(PageBreak())
        story.append(Paragraph("AI Security Analysis", section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=GRAY_200, spaceAfter=8))
        story.append(Paragraph(
            "The following analysis was generated by SentinelAI's integrated LLM engine. "
            "Rule-based fallback analysis is applied when an LLM is unavailable.",
            small_style,
        ))
        story.append(Spacer(1, 10))

        for field_name, label in [
            ("executive_summary", "Executive Summary"),
            ("technical_explanation", "Technical Explanation"),
            ("business_impact", "Business Impact"),
            ("attack_scenario", "Attack Scenario"),
            ("recommended_mitigation", "Recommended Mitigation"),
        ]:
            content = ai_analysis.get(field_name, "")
            if content:
                # Card-style AI block
                card_data = [[Paragraph(f"<b>{label}</b>", ParagraphStyle(
                    f"AIL_{field_name}", fontSize=10, fontName="Helvetica-Bold",
                    textColor=BLUE_600, spaceAfter=4,
                ))]]
                card_data.append([Paragraph(
                    _escape(content).replace("\n", "<br/>"),
                    body_style,
                )])
                card = Table(card_data, colWidths=[CONTENT_W])
                card.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), BLUE_100),
                    ("BOX", (0, 0), (-1, -1), 0.5, BLUE_500),
                    ("TOPPADDING", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ]))
                story.append(KeepTogether([card, Spacer(1, 10)]))

    # ================================================================
    # DISCLAIMER
    # ================================================================
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=10))
    story.append(Paragraph(
        "<b>Disclaimer:</b> This report is generated by automated static analysis of the API specification. "
        "Findings represent potential vulnerabilities that may require manual verification. "
        "This assessment does not replace a comprehensive penetration test or security audit.",
        ParagraphStyle("Disclaimer", parent=styles["Normal"], fontSize=8, textColor=NAVY_400, leading=11),
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Report generated by SentinelAI v1.0 on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
        ParagraphStyle("ReportMeta", parent=styles["Normal"], fontSize=7.5, textColor=NAVY_400, alignment=TA_CENTER),
    ))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()


def generate_json_report(scan_data: dict) -> str:
    return json.dumps(scan_data, indent=2, default=str)
