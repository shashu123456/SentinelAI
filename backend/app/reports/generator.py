import io
import json
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

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

# A scan has a `kind`: an API specification, a dependency manifest, or source
# code. Only the first has endpoints, so endpoint-shaped reporting is wrong for
# the other two — the labels, blurbs and summary rows below switch on it.
SCAN_TYPE_LABELS = {
    "spec": "API Specification",
    "deps": "Dependency Manifest",
    "code": "Source Code",
}

SCAN_TYPE_BLURBS = {
    "spec": "static analysis of the API specification",
    "deps": "matching the pinned packages against known vulnerability data",
    "code": "static analysis of the uploaded source files",
}

SOURCE_LABELS = {
    "spec": "API Spec",
    "deps": "Dependencies",
    "code": "Source Code",
}

# What the affected location means differs per source: a path, a package pin, or
# an operation from the specification.
LOCATION_FIELD_LABELS = {
    "spec": "ENDPOINT",
    "deps": "PACKAGE",
    "code": "LOCATION",
}


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
        if self.score >= 80:
            return RED_600
        if self.score >= 60:
            return ORANGE_600
        if self.score >= 30:
            return AMBER_600
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
    canvas.drawString(
        MARGIN,
        0.38 * inch,
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
    )
    canvas.drawCentredString(PAGE_W / 2, 0.38 * inch, "CONFIDENTIAL")
    canvas.drawRightString(PAGE_W - MARGIN, 0.38 * inch, f"Page {page_num}")

    canvas.restoreState()


# ============================================================================
# HELPER
# ============================================================================
def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _scan_kind(scan_data: dict) -> str:
    kind = str(scan_data.get("kind") or "spec").lower()
    return kind if kind in SCAN_TYPE_LABELS else "spec"


def _count_by_source(findings: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        source = str(finding.get("source") or "spec")
        counts[source] = counts.get(source, 0) + 1
    return counts


def _scope_metric(kind: str, endpoints: int, findings: list[dict]) -> tuple[int, str]:
    """Pick the fourth metric card: what a scan of this kind actually covered."""
    if endpoints:
        return endpoints, "Endpoints Scanned"
    if kind == "deps":
        return _distinct_locations(findings, "deps"), "Vulnerable Packages"
    if kind == "code":
        return _distinct_locations(findings, "code"), "Vulnerable Files"
    return 0, "Endpoints Scanned"


def _distinct_locations(findings: list[dict], source: str) -> int:
    """Count the packages (deps) or files (code) the findings point at."""
    locations = set()
    for finding in findings:
        if str(finding.get("source") or "spec") != source:
            continue
        location = str(finding.get("affected_endpoint") or "").strip()
        if not location:
            continue
        if source == "code":
            # ``path/to/file.py:12`` — the file is what was scanned, not the line.
            location = location.rsplit(":", 1)[0]
        locations.add(location)
    return len(locations)


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
        "CoverTitle",
        parent=styles["Title"],
        fontSize=36,
        textColor=NAVY_900,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=4,
        leading=42,
    )
    subtitle_style = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontSize=14,
        textColor=NAVY_500,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=18,
        textColor=NAVY_900,
        fontName="Helvetica-Bold",
        spaceBefore=24,
        spaceAfter=6,
        leading=22,
    )
    subsection_style = ParagraphStyle(
        "SubSection",
        parent=styles["Normal"],
        fontSize=12,
        fontName="Helvetica-Bold",
        textColor=NAVY_700,
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        textColor=NAVY_700,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=NAVY_500,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Bold",
        textColor=NAVY_500,
        spaceAfter=2,
        leading=11,
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=NAVY_700,
    )

    CONTENT_W = PAGE_W - 2 * MARGIN
    kind = _scan_kind(scan_data)
    scan_type = SCAN_TYPE_LABELS[kind]
    target_name = scan_data.get("api_name", "N/A")
    api_version = scan_data.get("api_version") or ""
    if str(api_version) in ("N/A", "None"):
        api_version = ""

    # ================================================================
    # COVER PAGE
    # ================================================================
    story.append(Spacer(1, 0.6 * inch))

    # Shield icon drawn with text
    shield_style = ParagraphStyle(
        "Shield",
        parent=styles["Normal"],
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=BLUE_500,
        alignment=TA_CENTER,
        spaceAfter=12,
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
        "CoverInfo",
        parent=styles["Normal"],
        fontSize=12,
        textColor=NAVY_600,
        alignment=TA_CENTER,
        leading=18,
    )
    # A dependency manifest or a source archive is not an "API" and has no
    # version, so the cover says what was scanned instead of inventing both.
    target_prefix = "Target API" if kind == "spec" else "Target"
    story.append(Paragraph(f"{target_prefix}: <b>{_escape(target_name)}</b>", cover_info_style))
    cover_bits = [scan_type]
    if api_version:
        cover_bits.insert(0, f"Version {_escape(api_version)}")
    cover_bits.append(_escape(scan_data.get("scan_date", "N/A")))
    story.append(
        Paragraph(
            "  |  ".join(cover_bits),
            ParagraphStyle(
                "CoverDate",
                parent=styles["Normal"],
                fontSize=11,
                textColor=NAVY_400,
                alignment=TA_CENTER,
            ),
        )
    )

    story.append(Spacer(1, 28))

    # Risk Score Circle
    risk_score = scan_data.get("risk_score", 0)
    risk_level = scan_data.get("risk_level", "Unknown").title()
    circle = CircleScore(risk_score, risk_level, width=220, height=220)
    # Wrap in a centered table
    circle_table = Table([[circle]], colWidths=[CONTENT_W])
    circle_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
            ]
        )
    )
    story.append(circle_table)

    story.append(Spacer(1, 40))

    # Confidential badge
    story.append(HRFlowable(width="60%", thickness=0.5, color=GRAY_200, spaceAfter=12))
    story.append(
        Paragraph(
            "CONFIDENTIAL - For authorized recipients only",
            ParagraphStyle(
                "Conf", parent=styles["Normal"], fontSize=9, textColor=NAVY_400, alignment=TA_CENTER
            ),
        )
    )

    story.append(PageBreak())

    # ================================================================
    # EXECUTIVE SUMMARY
    # ================================================================
    story.append(Paragraph("Executive Summary", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY_200, spaceAfter=14))

    findings = scan_data.get("findings", [])
    total = len(findings)
    severity_counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "Info")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    crit = severity_counts.get("Critical", 0)
    high = severity_counts.get("High", 0)
    crit_high = crit + high

    # Summary paragraph
    if total == 0:
        summary = "No security findings were identified. " + (
            "The API specification appears to follow security best practices."
            if kind == "spec"
            else f"No issues were reported by {SCAN_TYPE_BLURBS[kind]}."
        )
    else:
        scope = (
            "across the OWASP API Security Top 10"
            if kind == "spec"
            else f"through {SCAN_TYPE_BLURBS[kind]}"
        )
        summary = (
            f"The security assessment of <b>{_escape(target_name if kind == 'spec' else target_name or 'the target')}</b> identified "
            f"<b>{total}</b> security finding{'s' if total != 1 else ''} {scope}. "
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
    endpoints = int(scan_data.get("total_endpoints") or 0)
    packages = _distinct_locations(findings, "deps")
    source_files = _distinct_locations(findings, "code")
    scope_value, scope_label = _scope_metric(kind, endpoints, findings)
    card_w = (CONTENT_W - 30) / 4
    metric_row = [
        [
            MetricCard(
                str(risk_score),
                "Risk Score",
                SEVERITY_COLORS.get(
                    (
                        "Critical"
                        if risk_score >= 80
                        else "High" if risk_score >= 60 else "Medium" if risk_score >= 30 else "Low"
                    ),
                    NAVY_900,
                ),
                width=card_w,
            ),
            MetricCard(
                str(total), "Total Findings", RED_600 if total > 0 else GREEN_600, width=card_w
            ),
            MetricCard(
                str(crit_high),
                "Critical & High",
                RED_600 if crit_high > 0 else GREEN_600,
                width=card_w,
            ),
            MetricCard(str(scope_value), scope_label, BLUE_500, width=card_w),
        ]
    ]
    metric_table = Table(metric_row, colWidths=[card_w + 10] * 4)
    metric_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(metric_table)
    story.append(Spacer(1, 20))

    # Severity distribution
    if findings:
        story.append(Paragraph("Severity Distribution", subsection_style))
        story.append(Spacer(1, 6))

        # Stacked bar (only severities with findings)
        present = [
            sev
            for sev in ["Critical", "High", "Medium", "Low", "Info"]
            if severity_counts.get(sev, 0) > 0
        ]
        if present:
            widths = [max((severity_counts[sev] / total) * CONTENT_W, 40) for sev in present]
            cells = [
                Paragraph(
                    f'<font color="white" size="11"><b>{severity_counts[sev]}</b></font>',
                    ParagraphStyle("BC", alignment=TA_CENTER, fontSize=11),
                )
                for sev in present
            ]
            bar_styles = [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
            for i, sev in enumerate(present):
                bar_styles.append(("BACKGROUND", (i, 0), (i, 0), SEVERITY_COLORS[sev]))

            bar = Table([cells], colWidths=widths, rowHeights=[36])
            bar.setStyle(TableStyle(bar_styles))
            story.append(bar)
            story.append(Spacer(1, 8))

            # Legend row
            legend_items = [
                Paragraph(
                    f'<font color="{_severity_color_hex(sev)}">&#9632;</font> '
                    f'<font color="{NAVY_600.hexval()}" size="9">{sev}: {severity_counts[sev]} ({severity_counts[sev] / total * 100:.0f}%)</font>',
                    ParagraphStyle("Leg", fontSize=9, leading=14),
                )
                for sev in present
            ]
            legend = Table(
                [legend_items], colWidths=[CONTENT_W / len(legend_items)] * len(legend_items)
            )
            legend.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            story.append(legend)
            story.append(Spacer(1, 16))

    # Findings by source — a scan of a manifest or an archive has no endpoints,
    # so the per-scanner breakdown is the honest replacement for that view.
    counts_by_source = scan_data.get("counts_by_source") or _count_by_source(findings)
    if not endpoints and counts_by_source:
        story.append(Paragraph("Findings by Source", subsection_style))
        story.append(Spacer(1, 6))
        sev_order = ["Critical", "High", "Medium", "Low", "Info"]
        source_rows = [["Source", "Findings", *sev_order]]
        for source, count in sorted(counts_by_source.items(), key=lambda kv: -kv[1]):
            per_sev = dict.fromkeys(sev_order, 0)
            for finding in findings:
                if str(finding.get("source") or "spec") != source:
                    continue
                key = str(finding.get("severity") or "Info").strip().title()
                per_sev[key] = per_sev.get(key, 0) + 1
            source_rows.append(
                [SOURCE_LABELS.get(source, source.title()), str(count)]
                + [str(per_sev[sev]) for sev in sev_order]
            )

        src_w = 1.7 * inch
        sev_w = (CONTENT_W - src_w) / 6
        source_table = Table(source_rows, colWidths=[src_w] + [sev_w] * 6)
        source_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY_900),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, GRAY_200),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, NAVY_50]),
                ]
            )
        )
        story.append(source_table)
        story.append(Spacer(1, 16))

    # Scan details
    story.append(Paragraph("Scan Details", subsection_style))
    detail_data = [
        ["Field", "Value"],
        ["API Name" if kind == "spec" else "Target", _escape(target_name)],
    ]
    if kind != "spec":
        detail_data.append(["Scan Type", scan_type])
    if api_version:
        detail_data.append(["API Version", _escape(api_version)])
    detail_data.append(["Scan Date", _escape(scan_data.get("scan_date", "N/A"))])
    if endpoints:
        detail_data.append(["Endpoints Scanned", str(endpoints)])
    if kind == "deps" and packages:
        detail_data.append(["Vulnerable Packages", str(packages)])
    if kind == "code" and source_files:
        detail_data.append(["Vulnerable Files", str(source_files)])
    if scan_data.get("partial"):
        scanned = int(scan_data.get("files_scanned") or 0)
        eligible = int(scan_data.get("files_eligible") or 0)
        coverage = (
            f"Partial - first {scanned} of {eligible} files scanned"
            if eligible
            else "Partial - the per-scan file cap truncated this scan"
        )
        detail_data.append(["Coverage", coverage])
    detail_data += [
        ["Total Findings", str(total)],
        ["Risk Score", f"{risk_score}/100 ({risk_level})"],
    ]
    dt = Table(detail_data, colWidths=[2.2 * inch, CONTENT_W - 2.2 * inch])
    dt.setStyle(
        TableStyle(
            [
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
            ]
        )
    )
    story.append(dt)

    story.append(PageBreak())

    # ================================================================
    # DETAILED FINDINGS
    # ================================================================
    story.append(Paragraph("Detailed Findings", section_style))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY_200, spaceAfter=8))
    story.append(
        Paragraph(
            "Each finding below represents a potential security issue identified through "
            f"{SCAN_TYPE_BLURBS[kind]}. Manual verification is recommended before confirming exploitability.",
            small_style,
        )
    )
    story.append(Spacer(1, 14))

    if not findings:
        story.append(
            Paragraph(
                "No vulnerabilities were identified."
                + (
                    " The API specification appears to follow security best practices."
                    if kind == "spec"
                    else ""
                ),
                body_style,
            )
        )
    else:
        sorted_findings = sorted(
            findings,
            key=lambda x: {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}.get(
                x.get("severity", "Info"), 5
            ),
        )

        for _, finding in enumerate(sorted_findings, 1):
            severity = finding.get("severity", "Info")
            sev_clr = _severity_color_hex(severity)
            sev_bg = _severity_bg_hex(severity)
            confidence = finding.get("confidence", 85)
            owasp = str(finding.get("owasp_category") or "N/A").strip()
            cwe = finding.get("cwe_id", "N/A")
            # Dependency and SAST findings carry no OWASP API category, and a
            # bare "OWASP: N/A - " line is noise rather than a finding detail.
            owasp_known = owasp not in ("", "N/A", "None", "Unmapped (SAST)")

            # ---- Finding Card ----
            # Header bar
            header_inner = [
                [
                    Paragraph(
                        f'<font color="{sev_clr}" size="11"><b>[{severity.upper()}]</b></font>'
                        f'  <font size="11"><b>{_escape(finding.get("vulnerability_name", "Unknown"))}</b></font>',
                        ParagraphStyle(
                            "FH", fontSize=11, fontName="Helvetica-Bold", textColor=NAVY_900
                        ),
                    ),
                    Paragraph(
                        f'<font size="8" color="{NAVY_500.hexval()}">Confidence: </font>'
                        f'<font size="9" color="{NAVY_900.hexval()}"><b>{confidence}%</b></font>',
                        ParagraphStyle("FC", fontSize=9, alignment=TA_RIGHT),
                    ),
                ]
            ]
            hdr = Table(header_inner, colWidths=[CONTENT_W - 110, 100])
            hdr.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(sev_bg)),
                        ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor(sev_clr)),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )

            # OWASP + CWE tags
            tags = []
            if owasp_known:
                owasp_name = OWASP_NAMES.get(owasp, "")
                tags.append(
                    Paragraph(
                        f'<font color="{NAVY_600.hexval()}" size="8">OWASP: </font>'
                        f'<font color="{BLUE_600.hexval()}" size="8"><b>{_escape(owasp)}</b></font>'
                        + (
                            f'<font color="{NAVY_400.hexval()}" size="8"> - {_escape(owasp_name)}</font>'
                            if owasp_name
                            else ""
                        ),
                        ParagraphStyle("Tag1", fontSize=8, leading=11),
                    )
                )
            if cwe and cwe != "N/A":
                tags.append(
                    Paragraph(
                        f'<font color="{NAVY_600.hexval()}" size="8">CWE: </font>'
                        f'<font color="{GREEN_600.hexval()}" size="8"><b>{cwe}</b></font>',
                        ParagraphStyle("Tag2", fontSize=8, leading=11),
                    )
                )
            if tags:
                tag_w = CONTENT_W / len(tags)
                tag_table = Table([tags], colWidths=[tag_w] * len(tags))
                tag_table.setStyle(
                    TableStyle(
                        [
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
            else:
                tag_table = Spacer(0, 6)

            # Detail fields
            detail_rows: list[list[Paragraph]] = []

            def _add_field(label, text, _rows=detail_rows):
                if text and text != "N/A" and str(text).strip():
                    _rows.append(
                        [
                            Paragraph(f"<b>{label}</b>", label_style),
                            Paragraph(_escape(str(text)), value_style),
                        ]
                    )

            # "N/A C:\\...\\app.py" was the old output for a code finding, since
            # only specification findings have a method.
            location_parts = [
                str(part).strip()
                for part in (
                    finding.get("affected_method"),
                    finding.get("affected_endpoint"),
                )
                if part and str(part).strip() and str(part).strip().upper() != "N/A"
            ]
            _add_field(
                LOCATION_FIELD_LABELS.get(str(finding.get("source") or "spec"), "ENDPOINT"),
                " ".join(location_parts),
            )
            _add_field("DESCRIPTION", finding.get("description", ""))
            _add_field("DETECTION REASON", finding.get("detection_reason", ""))
            _add_field("EVIDENCE", finding.get("evidence", ""))
            _add_field("IMPACT", finding.get("impact", ""))
            _add_field("TECHNICAL IMPACT", finding.get("technical_impact", ""))
            _add_field("BUSINESS IMPACT", finding.get("business_impact", ""))
            _add_field("REMEDIATION", finding.get("remediation", ""))
            _add_field("FIX RECOMMENDATION", finding.get("fix_recommendation", ""))

            if finding.get("cvss_score") is not None:
                _add_field(
                    "CVSS",
                    f"Score {finding['cvss_score']}  ({finding.get('cvss_vector', 'N/A')})",
                )

            references = finding.get("references") or []
            if references:
                _add_field("REFERENCES", " | ".join(str(r) for r in references))

            if finding.get("false_positive_note"):
                detail_rows.append(
                    [
                        Paragraph(
                            "<b>FALSE POSITIVE NOTE</b>",
                            ParagraphStyle(
                                "FPLabel",
                                parent=label_style,
                                textColor=AMBER_600,
                            ),
                        ),
                        Paragraph(
                            f"<i>{_escape(finding['false_positive_note'])}</i>",
                            ParagraphStyle(
                                "FPVal", parent=value_style, fontSize=9, textColor=NAVY_500
                            ),
                        ),
                    ]
                )

            detail_table = Table(detail_rows, colWidths=[1.4 * inch, CONTENT_W - 1.4 * inch])
            detail_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), NAVY_50),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("LINEBELOW", (0, 0), (-1, -2), 0.4, GRAY_200),
                    ]
                )
            )

            finding_block = KeepTogether(
                [
                    hdr,
                    tag_table,
                    detail_table,
                    Spacer(1, 18),
                ]
            )
            story.append(finding_block)

    # ================================================================
    # AI ANALYSIS
    # ================================================================
    ai_analysis = scan_data.get("ai_analysis")
    if ai_analysis:
        story.append(PageBreak())
        story.append(Paragraph("AI Security Analysis", section_style))
        story.append(HRFlowable(width="100%", thickness=1, color=GRAY_200, spaceAfter=8))
        story.append(
            Paragraph(
                "The following analysis was generated by SentinelAI's integrated LLM engine. "
                "Rule-based fallback analysis is applied when an LLM is unavailable.",
                small_style,
            )
        )
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
                card_data = [
                    [
                        Paragraph(
                            f"<b>{label}</b>",
                            ParagraphStyle(
                                f"AIL_{field_name}",
                                fontSize=10,
                                fontName="Helvetica-Bold",
                                textColor=BLUE_600,
                                spaceAfter=4,
                            ),
                        )
                    ]
                ]
                card_data.append(
                    [
                        Paragraph(
                            _escape(content).replace("\n", "<br/>"),
                            body_style,
                        )
                    ]
                )
                card = Table(card_data, colWidths=[CONTENT_W])
                card.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), BLUE_100),
                            ("BOX", (0, 0), (-1, -1), 0.5, BLUE_500),
                            ("TOPPADDING", (0, 0), (-1, 0), 10),
                            ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                            ("LEFTPADDING", (0, 0), (-1, -1), 14),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                        ]
                    )
                )
                story.append(KeepTogether([card, Spacer(1, 10)]))

    # ================================================================
    # DISCLAIMER
    # ================================================================
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_200, spaceAfter=10))
    story.append(
        Paragraph(
            "<b>Disclaimer:</b> This report is generated by automated analysis: "
            f"{SCAN_TYPE_BLURBS[kind]}. "
            "Findings represent potential vulnerabilities that may require manual verification. "
            "This assessment does not replace a comprehensive penetration test or security audit.",
            ParagraphStyle(
                "Disclaimer", parent=styles["Normal"], fontSize=8, textColor=NAVY_400, leading=11
            ),
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"Report generated by SentinelAI v1.0 on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}.",
            ParagraphStyle(
                "ReportMeta",
                parent=styles["Normal"],
                fontSize=7.5,
                textColor=NAVY_400,
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()


def generate_json_report(scan_data: dict) -> str:
    return json.dumps(scan_data, indent=2, default=str)
