"""Render the reproducible Markdown methodology report as an uploadable PDF."""

from __future__ import annotations

import html
import csv
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "SUBMISSION_REPORT.md"
OUTPUT = ROOT / "output" / "pdf" / "superr_selector_methodology.pdf"
NAVY = colors.HexColor("#153047")
TEAL = colors.HexColor("#147D85")
PALE = colors.HexColor("#EAF3F3")
RULE = colors.HexColor("#C7D7DA")


def register_fonts() -> None:
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("ArialReport", str(font_dir / "arial.ttf")))
    pdfmetrics.registerFont(TTFont("ArialReportBold", str(font_dir / "arialbd.ttf")))
    pdfmetrics.registerFontFamily(
        "ArialReport", normal="ArialReport", bold="ArialReportBold"
    )


def inline_markup(value: str) -> str:
    value = html.escape(value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`(.+?)`", r"<font color='#286A76'>\1</font>", value)
    return value


def draw_page(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(RULE)
    canvas.line(17 * mm, height - 18 * mm, width - 17 * mm, height - 18 * mm)
    canvas.setFont("ArialReportBold", 8)
    canvas.setFillColor(NAVY)
    canvas.drawString(17 * mm, height - 14 * mm, "SupeRR Selector Season 2")
    canvas.setFont("ArialReport", 8)
    canvas.setFillColor(colors.HexColor("#5C6E78"))
    canvas.drawRightString(width - 17 * mm, 13 * mm, f"Methodology report  |  {doc.page}")
    canvas.restoreState()


def table_from_lines(lines: list[str], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in lines
    ]
    rows = [rows[0]] + rows[2:]
    n = len(rows[0])
    usable = A4[0] - 34 * mm
    if n == 7:
        proportions = [0.06, 0.20, 0.15, 0.13, 0.13, 0.14, 0.19]
    elif n == 4:
        proportions = [0.56, 0.12, 0.12, 0.20]
    elif n == 2:
        proportions = [0.69, 0.31]
    else:
        proportions = [1 / n] * n
    widths = [usable * part / sum(proportions) for part in proportions]
    contents = [
        [Paragraph(inline_markup(cell), styles["table_header" if index == 0 else "table"])
         for cell in row]
        for index, row in enumerate(rows)
    ]
    table = Table(contents, colWidths=widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, TEAL),
        ("LINEBELOW", (0, -1), (-1, -1), 0.4, RULE),
    ]))
    return table


def main() -> None:
    register_fonts()
    source_text = SOURCE.read_text(encoding="utf-8")
    displayed_rows = re.findall(
        r"^\| (\d+) \| ([^|]+) \| ([0-9.]+) \|", source_text, re.M
    )
    displayed = [(rank, name.strip(), value) for rank, name, value in displayed_rows]
    with (ROOT / "data" / "processed" / "rankings.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        ranked = list(csv.DictReader(handle))
    expected = [
        (row["rank"], row["player_name"], f"{float(row['conservative_score']):.3f}")
        for row in ranked
    ]
    if displayed != expected:
        raise ValueError("The report ranking tables differ from rankings.csv")
    styles = {
        "title": ParagraphStyle(
            "title", fontName="ArialReportBold", fontSize=19, leading=23,
            textColor=NAVY, spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "h2", fontName="ArialReportBold", fontSize=12.3, leading=16,
            textColor=NAVY, spaceBefore=14, spaceAfter=7, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "h3", fontName="ArialReportBold", fontSize=10.3, leading=13,
            textColor=TEAL, spaceBefore=9, spaceAfter=6, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "body", fontName="ArialReport", fontSize=9.2, leading=13.5,
            textColor=colors.HexColor("#24333B"), spaceAfter=8,
        ),
        "table": ParagraphStyle(
            "table", fontName="ArialReport", fontSize=7.1, leading=9.1,
            textColor=colors.HexColor("#203039"), alignment=TA_LEFT,
        ),
        "table_header": ParagraphStyle(
            "table_header", fontName="ArialReportBold", fontSize=7.1,
            leading=9.1, textColor=colors.white, alignment=TA_LEFT,
        ),
    }
    lines = source_text.splitlines()
    story = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("|"):
            block = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                block.append(lines[index])
                index += 1
            story.append(table_from_lines(block, styles))
            story.append(Spacer(1, 5 * mm))
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), styles["title"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), styles["h2"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), styles["h3"]))
        else:
            block = [line]
            while index + 1 < len(lines) and lines[index + 1].strip():
                if lines[index + 1].startswith(("#", "|")):
                    break
                index += 1
                block.append(lines[index].strip())
            story.append(Paragraph(inline_markup(" ".join(block)), styles["body"]))
        index += 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=17 * mm, rightMargin=17 * mm,
        topMargin=23 * mm, bottomMargin=20 * mm,
        title="SupeRR Selector Season 2 - Methodology report",
        author="Pressure rankings analysis",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=draw_page))
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
