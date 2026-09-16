#!/usr/bin/env python3
"""학생 제출물(.hwp / .hwpx / .pdf)에서 본문과 글자 색을 함께 뽑는다.

학생은 선택형 문항에 ○를 치지 않고 (가) 오답 보기를 지우거나 (나) 정답 보기의
글자 색을 바꾸는 방식으로 답한다(CLAUDE.md '학생 제출물 표시 규칙'). 따라서
채점하려면 남아 있는 글자와 그 색을 모두 알아야 한다.

출력: JSON {"file":…, "format":…, "text":…, "marked":…}
  text   — 본문 그대로
  marked — 검은색이 아닌 구간을 [C]…[/] 로 감싼 본문

사용법:  python3 extract_submission.py 파일 [--marked|--text]
"""
import json
import re
import struct
import sys
import zipfile
import zlib

BLACK_TOL = 0.12


# ---------------------------------------------------------------- hwp (5.0)
EXT_CTRL = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}
CHAR_SHAPE, PARA_TEXT, PARA_CHAR_SHAPE = 21, 67, 68


def _records(data):
    i, n = 0, len(data)
    while i < n - 4:
        h = struct.unpack_from("<I", data, i)[0]
        tag, ln = h & 0x3FF, (h >> 20) & 0xFFF
        i += 4
        if ln == 0xFFF:
            ln = struct.unpack_from("<I", data, i)[0]
            i += 4
        yield tag, data[i:i + ln]
        i += ln


def _hwp(path):
    import olefile
    ole = olefile.OleFileIO(path)
    comp = bool(ole.openstream("FileHeader").read()[36] & 1)

    def st(name):
        d = ole.openstream(name).read()
        return zlib.decompress(d, -15) if comp else d

    colors, idx = {}, 0
    for tag, body in _records(st("DocInfo")):
        if tag == CHAR_SHAPE:
            if len(body) >= 56:
                c = struct.unpack_from("<I", body, 52)[0]
                colors[idx] = ((c & 0xFF) / 255, ((c >> 8) & 0xFF) / 255, ((c >> 16) & 0xFF) / 255)
            idx += 1

    paras, cur = [], None
    for name in sorted([x for x in ole.listdir() if x[0] == "BodyText"],
                       key=lambda x: int(x[1].replace("Section", ""))):
        for tag, body in _records(st(name)):
            if tag == PARA_TEXT:
                cur, j = [], 0
                while j + 1 < len(body):
                    code = struct.unpack_from("<H", body, j)[0]
                    pos = j // 2
                    if code in (10, 13):
                        cur.append((pos, "\n")); j += 2
                    elif code == 9:
                        cur.append((pos, "\t")); j += 2
                    elif code < 32:
                        j += 16 if code in EXT_CTRL else 2
                    else:
                        cur.append((pos, chr(code))); j += 2
            elif tag == PARA_CHAR_SHAPE and cur is not None:
                runs = [struct.unpack_from("<II", body, k) for k in range(0, len(body) - 7, 8)]
                paras.append((cur, runs)); cur = None
    ole.close()

    out = []
    for chars, runs in paras:
        line = []
        for pos, ch in chars:
            sid = 0
            for start, s in runs:
                if pos >= start:
                    sid = s
                else:
                    break
            line.append((ch, colors.get(sid, (0, 0, 0))))
        out.append(line)
    return out


# ---------------------------------------------------------------- hwpx
def _hwpx(path):
    z = zipfile.ZipFile(path)
    hdr = z.read("Contents/header.xml").decode("utf-8", "ignore")
    colors = {}
    for cid, col in re.findall(r'<hh:charPr[^>]*?id="(\d+)"[^>]*?textColor="#?([0-9A-Fa-f]{6})"', hdr):
        colors[cid] = tuple(int(col[i:i + 2], 16) / 255 for i in (0, 2, 4))

    out = []
    for name in sorted(n for n in z.namelist()
                       if re.fullmatch(r"Contents/section\d+\.xml", n)):
        xml = z.read(name).decode("utf-8", "ignore")
        for para in re.findall(r"<hp:p\b.*?</hp:p>", xml, re.S):
            line = []
            for cid, inner in re.findall(r'<hp:run[^>]*?charPrIDRef="(\d+)".*?>(.*?)</hp:run>',
                                         para, re.S):
                col = colors.get(cid, (0, 0, 0))
                for t in re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", inner, re.S):
                    txt = (t.replace("&lt;", "<").replace("&gt;", ">")
                             .replace("&quot;", '"').replace("&apos;", "'")
                             .replace("&amp;", "&"))
                    txt = re.sub(r"<[^>]+>", "", txt)
                    line += [(c, col) for c in txt]
            if line:
                out.append(line)
    return out


# ---------------------------------------------------------------- pdf
def _pdf(path):
    import pdfplumber
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            rows = {}
            for ch in page.chars:
                rows.setdefault(round(ch["top"] / 3), []).append(ch)
            for key in sorted(rows):
                line = []
                for ch in sorted(rows[key], key=lambda c: c["x0"]):
                    col = ch.get("non_stroking_color")
                    if not isinstance(col, (list, tuple)):
                        col = (0, 0, 0)
                    elif len(col) == 1:          # grayscale
                        col = (col[0],) * 3
                    elif len(col) == 4:          # CMYK
                        c, m, y, k = col
                        col = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
                    line.append((ch["text"], tuple(col[:3])))
                if line:
                    out.append(line)
    return out


# ---------------------------------------------------------------- 공통
def load(path):
    low = path.lower()
    if low.endswith(".hwpx"):
        return _hwpx(path), "hwpx"
    if low.endswith(".pdf"):
        return _pdf(path), "pdf"
    return _hwp(path), "hwp"


def is_black(col):
    return all(v <= BLACK_TOL for v in col)


def render(lines, marked):
    out = []
    for line in lines:
        if not marked:
            out.append("".join(c for c, _ in line))
            continue
        buf, inc = [], False
        for ch, col in line:
            want = not is_black(col)
            if want != inc:
                buf.append("[C]" if want else "[/]")
                inc = want
            buf.append(ch)
        if inc:
            buf.append("[/]")
        out.append("".join(buf))
    return "\n".join(out)


if __name__ == "__main__":
    p = sys.argv[1]
    lines, fmt = load(p)
    if "--marked" in sys.argv:
        print(render(lines, True))
    elif "--text" in sys.argv:
        print(render(lines, False))
    else:
        print(json.dumps({"file": p, "format": fmt,
                          "text": render(lines, False),
                          "marked": render(lines, True)}, ensure_ascii=False))
