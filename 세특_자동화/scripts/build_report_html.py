#!/usr/bin/env python3
"""build_report_pdf.py와 같은 JSON 스펙으로 HTML을 만든다.

Drive 업로드용. PDF를 base64로 통째로 올리는 방식은 보고서 크기(수십~수백 KB)의
base64가 한 번의 도구 호출로 재현하기엔 너무 커서 쓰지 못한다(CLAUDE.md 4단계 7번).
대신 이 HTML을 create_file의 textContent(contentMimeType: text/html)로 올리면
Drive가 구글 문서로 변환해 주며, 표 구조가 그대로 남는다.

사용법:  python3 build_report_html.py spec.json out.html
"""
import html
import json
import sys

CSS = """body{font-family:'Malgun Gothic',AppleGothic,sans-serif;font-size:11pt;line-height:1.6;color:#222}
h1{color:#1F4E79;font-size:17pt;text-align:center;margin-bottom:2px}
p.sub{text-align:center;color:#555;font-size:10pt;margin-top:0}
h2{color:#1F4E79;font-size:13pt;margin-top:22px;border-bottom:1px solid #B7C4D4;padding-bottom:3px}
table{border-collapse:collapse;width:100%;font-size:10pt;margin:6px 0}
th{background:#E8EEF5;border:1px solid #B7C4D4;padding:5px;text-align:center}
td{border:1px solid #B7C4D4;padding:5px;vertical-align:top}
div.note{background:#FFF6E5;border:1px solid #E0A800;padding:8px 12px;margin:8px 0;font-size:10pt}
p.foot{text-align:center;color:#777;font-size:9pt;margin-top:18px}"""


def cell(v):
    """스펙의 <b>·<br/>만 태그로 살리고 나머지는 이스케이프한다."""
    s = html.escape(str(v))
    for tag in ("b",):
        s = s.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return s.replace("&lt;br/&gt;", "<br/>")


def render(spec):
    out = ["<html><head><meta charset='utf-8'><style>", CSS, "</style></head><body>",
           f"<h1>{cell(spec['title'])}</h1>"]
    if spec.get("subtitle"):
        out.append(f"<p class='sub'>{cell(spec['subtitle'])}</p>")
    if spec.get("meta"):
        out.append("<table>")
        for k, v in spec["meta"]:
            out.append(f"<tr><th style='width:16%;text-align:left'>{cell(k)}</th>"
                       f"<td>{cell(v)}</td></tr>")
        out.append("</table>")
    for sec in spec["sections"]:
        out.append(f"<h2>{cell(sec['heading'])}</h2>")
        for blk in sec["blocks"]:
            kind = blk["type"]
            if kind == "para":
                out.append(f"<p>{cell(blk['text'])}</p>")
            elif kind == "note":
                out.append(f"<div class='note'>{cell(blk['text'])}</div>")
            elif kind == "bullets":
                out.append("<ul>" + "".join(f"<li>{cell(i)}</li>" for i in blk["items"]) + "</ul>")
            elif kind == "table":
                out.append("<table>")
                if blk.get("header"):
                    out.append("<tr>" + "".join(f"<th>{cell(c)}</th>" for c in blk["header"]) + "</tr>")
                for row in blk["rows"]:
                    out.append("<tr>" + "".join(f"<td>{cell(c)}</td>" for c in row) + "</tr>")
                out.append("</table>")
    if spec.get("footer"):
        out.append(f"<p class='foot'>{cell(spec['footer'])}</p>")
    out.append("</body></html>")
    return "\n".join(out)


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    open(sys.argv[2], "w", encoding="utf-8").write(render(spec))
    print(f"생성 완료: {sys.argv[2]}")
