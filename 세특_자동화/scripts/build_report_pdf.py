#!/usr/bin/env python3
"""세특 자동화 공용 PDF 보고서 생성기.

JSON 스펙을 받아 한글 PDF를 만든다. 3단계(분석기준)·4단계(차시별 분석결과)·
5단계(월말 결산) 보고서가 같은 레이아웃을 쓰도록 하기 위한 공용 스크립트이며,
차시마다 레이아웃을 새로 설계하지 않는다 (CLAUDE.md 사용량 최적화 원칙 7).

사용법:  python3 build_report_pdf.py spec.json out.pdf

스펙 형식:
{
  "title": str, "subtitle": str, "meta": [[label, value], ...],
  "sections": [
     {"heading": str,
      "blocks": [ {"type":"para","text":str}
                | {"type":"bullets","items":[str,...]}
                | {"type":"table","header":[...],"rows":[[...],...],"widths":[float,...]}
                | {"type":"note","text":str} ]}
  ],
  "footer": str
}
"""
import json
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

FONT_DIR = "/usr/share/fonts/truetype/nanum"
pdfmetrics.registerFont(TTFont("Nanum", f"{FONT_DIR}/NanumGothic.ttf"))
pdfmetrics.registerFont(TTFont("Nanum-B", f"{FONT_DIR}/NanumGothicBold.ttf"))
pdfmetrics.registerFontFamily("Nanum", normal="Nanum", bold="Nanum-B")

ACCENT = colors.HexColor("#1F4E79")
HEAD_BG = colors.HexColor("#E8EEF5")
NOTE_BG = colors.HexColor("#FFF6E5")
GRID = colors.HexColor("#B7C4D4")

_ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=_ss["Title"], fontName="Nanum-B",
                            fontSize=17, leading=23, textColor=ACCENT, spaceAfter=2),
    "subtitle": ParagraphStyle("st", parent=_ss["Normal"], fontName="Nanum",
                               fontSize=10.5, leading=15, alignment=TA_CENTER,
                               textColor=colors.HexColor("#555555"), spaceAfter=10),
    "h": ParagraphStyle("h", parent=_ss["Heading2"], fontName="Nanum-B", fontSize=12.5,
                        leading=17, textColor=ACCENT, spaceBefore=12, spaceAfter=5,
                        keepWithNext=1),
    "p": ParagraphStyle("p", parent=_ss["Normal"], fontName="Nanum", fontSize=9.5,
                        leading=14.5, spaceAfter=4),
    "b": ParagraphStyle("b", parent=_ss["Normal"], fontName="Nanum", fontSize=9.5,
                        leading=14.5, leftIndent=10, bulletIndent=2, spaceAfter=2),
    "cell": ParagraphStyle("c", parent=_ss["Normal"], fontName="Nanum", fontSize=8.3,
                           leading=11.8),
    "cellh": ParagraphStyle("ch", parent=_ss["Normal"], fontName="Nanum-B", fontSize=8.5,
                            leading=12, alignment=TA_CENTER),
}


def _table(block, avail):
    widths = block.get("widths")
    ncol = len(block["header"]) if block.get("header") else len(block["rows"][0])
    widths = ([w / sum(widths) * avail for w in widths] if widths
              else [avail / ncol] * ncol)
    data, style = [], [
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if block.get("header"):
        data.append([Paragraph(str(c), S["cellh"]) for c in block["header"]])
        style += [("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.9, ACCENT)]
    for r in block["rows"]:
        data.append([Paragraph(str(c), S["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1 if block.get("header") else 0,
              spaceBefore=3, spaceAfter=2)
    t.setStyle(TableStyle(style))
    return t


def build(spec, out_path):
    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            leftMargin=17 * mm, rightMargin=17 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=spec["title"], author="Claude Code")
    avail = doc.width
    story = [Paragraph(spec["title"], S["title"])]
    if spec.get("subtitle"):
        story.append(Paragraph(spec["subtitle"], S["subtitle"]))
    if spec.get("meta"):
        story.append(_table({"rows": [[f"<b>{k}</b>", v] for k, v in spec["meta"]],
                             "widths": [1, 4]}, avail))
    for sec in spec["sections"]:
        flow = [Paragraph(sec["heading"], S["h"])]
        for blk in sec["blocks"]:
            kind = blk["type"]
            if kind == "para":
                flow.append(Paragraph(blk["text"], S["p"]))
            elif kind == "bullets":
                flow += [Paragraph(i, S["b"], bulletText="•") for i in blk["items"]]
            elif kind == "note":
                n = Table([[Paragraph(blk["text"], S["cell"])]], colWidths=[avail])
                n.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NOTE_BG),
                                       ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E0A800")),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 7),
                                       ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                                       ("TOPPADDING", (0, 0), (-1, -1), 5),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
                n.spaceBefore = n.spaceAfter = 3
                flow.append(n)
            elif kind == "table":
                flow.append(_table(blk, avail))
        # 제목은 keepWithNext로 다음 블록과 붙어 다니므로 그대로 이어 붙인다
        story += flow
    if spec.get("footer"):
        story += [Spacer(1, 10), Paragraph(spec["footer"], S["subtitle"])]
    doc.build(story)
    print(f"생성 완료: {out_path}")


if __name__ == "__main__":
    build(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
