"""Render the reproducible Markdown methodology report as an uploadable PDF."""

from __future__ import annotations

import html
import csv
import re
import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle,
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
    elif n == 8:
        proportions = [0.07, 0.18, 0.10, 0.10, 0.08, 0.15, 0.12, 0.20]
    elif n == 6:
        proportions = [0.10, 0.15, 0.10, 0.21, 0.21, 0.23]
    elif n == 4:
        proportions = (
            [0.28, 0.24, 0.24, 0.24] if rows[0][0] == "Player"
            else [0.56, 0.12, 0.12, 0.20]
        )
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


def main(final: bool = False) -> None:
    register_fonts()
    source = ROOT / "docs" / "FINAL_SUBMISSION_REPORT.md" if final else SOURCE
    output = ROOT / "output" / "pdf" / "superr_selector_final_methodology.pdf" if final else OUTPUT
    ranking_path = ROOT / "data" / "processed" / ("final_rankings.csv" if final else "rankings.csv")
    source_text = source.read_text(encoding="utf-8")
    with ranking_path.open(newline="", encoding="utf-8") as handle:
        ranked = list(csv.DictReader(handle))
    if final:
        displayed = []
        for heading, ending in (("### Batters", "### Bowlers"),
                                ("### Bowlers", "## Data")):
            section = source_text.split(heading, 1)[1].split(ending, 1)[0]
            displayed.extend(re.findall(
                r"^\| (\d+) \| ([^|]+) \| (\d+) \| (\d+) \| (\d+) \|",
                section, re.M,
            ))
        displayed = [(rank, name.strip(), old, state, total)
                     for rank, name, old, state, total in displayed]
        expected = [(row["rank"], row["player_name"], row["legacy_rank"],
                     row["state_rank"], row["rank_sum"]) for row in ranked]
    else:
        displayed_rows = re.findall(
            r"^\| (\d+) \| ([^|]+) \| ([0-9.]+) \|", source_text, re.M
        )
        displayed = [(rank, name.strip(), value) for rank, name, value in displayed_rows]
        expected = [
            (row["rank"], row["player_name"], f"{float(row['conservative_score']):.3f}")
            for row in ranked
        ]
    if displayed != expected:
        raise ValueError(f"The report ranking tables differ from {ranking_path.name}")
    styles = {
        "title": ParagraphStyle(
            "title", fontName="ArialReportBold", fontSize=19, leading=23,
            textColor=NAVY, spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "h2", fontName="ArialReportBold", fontSize=12.3, leading=16,
            textColor=NAVY, spaceBefore=12, spaceAfter=6, keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "h3", fontName="ArialReportBold", fontSize=10.3, leading=13,
            textColor=TEAL, spaceBefore=7, spaceAfter=5, keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "body", fontName="ArialReport", fontSize=9.2, leading=13.5,
            textColor=colors.HexColor("#24333B"), spaceAfter=6,
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
    in_worked_examples = False
    pending_worked_heading = None
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
            story.append(Spacer(1, 3 * mm))
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), styles["title"]))
        elif line.startswith("## "):
            in_worked_examples = line.startswith("## Worked selections:")
            story.append(Paragraph(inline_markup(line[3:]), styles["h2"]))
        elif line.startswith("### "):
            heading = Paragraph(inline_markup(line[4:]), styles["h3"])
            if in_worked_examples:
                pending_worked_heading = heading
            else:
                story.append(heading)
        else:
            block = [line]
            while index + 1 < len(lines) and lines[index + 1].strip():
                if lines[index + 1].startswith(("#", "|")):
                    break
                index += 1
                block.append(lines[index].strip())
            paragraph = Paragraph(inline_markup(" ".join(block)), styles["body"])
            if pending_worked_heading is not None:
                story.append(KeepTogether([pending_worked_heading, paragraph]))
                pending_worked_heading = None
            else:
                story.append(KeepTogether([paragraph]) if in_worked_examples else paragraph)
        index += 1

    if pending_worked_heading is not None:
        raise ValueError("Worked example heading lacks a paragraph")

    output.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(output), pagesize=A4,
        leftMargin=17 * mm, rightMargin=17 * mm,
        topMargin=23 * mm, bottomMargin=20 * mm,
        title="SupeRR Selector Season 2 - Final methodology report" if final
              else "SupeRR Selector Season 2 - Methodology report",
        author="Pressure rankings analysis",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=draw_page))
    doc.build(story)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true", help="Render the final consensus report")
    main(parser.parse_args().final)
