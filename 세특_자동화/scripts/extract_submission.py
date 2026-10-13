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


def _distdoc_decrypt(data):
    """'배포용 문서'(읽기 전용으로 저장한 한글 파일)의 ViewText 스트림을 복호화한다.

    배포용으로 저장하면 본문이 BodyText가 아니라 ViewText에 AES-128로 암호화되어 들어가고,
    BodyText에는 "상위 버전의 배포용 문서입니다"라는 안내문만 남는다. 열쇠는 스트림 첫
    레코드(HWPTAG_DISTRIBUTE_DOC_DATA, 256바이트)에 들어 있다.
    알고리즘 출처: pyhwp hwp5/distdoc.py (Changwoo Ryu가 정리한 방식).
    """
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    size = (struct.unpack_from("<I", data, 0)[0] >> 20) & 0xFFF
    head, tail = bytearray(data[4:4 + size]), data[4 + size:]
    if len(head) != 256:
        raise ValueError("배포용 문서 머리말이 256바이트가 아니다")

    seed = struct.unpack_from("<I", head, 0)[0]
    state = seed

    def rand():
        nonlocal state
        state = (state * 214013 + 2531011) & 0xFFFFFFFF
        return (state >> 16) & 0x7FFF

    n, key = 0, 0
    for i in range(256):
        if n == 0:
            key = rand() & 0xFF
            n = (rand() & 0xF) + 1
        if i >= 4:
            head[i] ^= key
        n -= 1
    off = 4 + (seed & 0xF)
    dec = Cipher(algorithms.AES(bytes(head[off:off + 16])), modes.ECB()).decryptor()
    return dec.update(tail) + dec.finalize()


def _hwp(path):
    import olefile
    ole = olefile.OleFileIO(path)
    props = ole.openstream("FileHeader").read()[36]
    comp, dist = bool(props & 1), bool(props & 4)
    base = ("ViewText" if dist and any(x[0] == "ViewText" for x in ole.listdir())
            else "BodyText")

    def st(name):
        d = ole.openstream(name).read()
        if name[0] == "ViewText":
            d = _distdoc_decrypt(d)
        return zlib.decompress(d, -15) if comp else d

    colors, idx = {}, 0
    for tag, body in _records(st("DocInfo")):
        if tag == CHAR_SHAPE:
            if len(body) >= 56:
                c = struct.unpack_from("<I", body, 52)[0]
                colors[idx] = ((c & 0xFF) / 255, ((c >> 8) & 0xFF) / 255, ((c >> 16) & 0xFF) / 255)
            idx += 1

    paras, cur = [], None
    for name in sorted([x for x in ole.listdir() if x[0] == base],
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


# ------------------------------------------------------- pdf (표 칸 단위)
def _char_color(ch):
    col = ch.get("non_stroking_color")
    if not isinstance(col, (list, tuple)):
        return (0, 0, 0)
    if len(col) == 1:                    # grayscale
        return (col[0],) * 3
    if len(col) == 4:                    # CMYK
        c, m, y, k = col
        return ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    return tuple(col[:3])


def _group_lines(chars, tol=None):
    """글자를 줄 단위로 묶는다 — top이 몇 px 어긋나도 같은 줄로 본다.

    한글 글자와 괄호·마침표는 같은 줄인데도 top이 0.4px쯤 다르게 나와서,
    top을 그대로 반올림해 묶으면 "(비용)이/가 적게 듦."이 "(   )/  . 비용이가적게듦"
    처럼 흐트러진다. 그래서 글자 높이의 절반을 허용 오차로 두고 묶는다.
    """
    chars = sorted(chars, key=lambda c: c["top"])
    if tol is None:
        hs = sorted(c["height"] for c in chars) or [10.0]
        tol = max(2.0, 0.5 * hs[len(hs) // 2])
    lines, cur, ref = [], [], None
    for ch in chars:
        if ref is not None and ch["top"] - ref > tol:
            lines.append(cur)
            cur, ref = [], None
        if ref is None:
            ref = ch["top"]
        cur.append(ch)
    if cur:
        lines.append(cur)
    for line in lines:
        line.sort(key=lambda c: c["x0"])
    return lines


def _pdf_cells(path):
    """PDF를 '표 칸' 단위로 읽는다.

    학습지는 대부분 표로 되어 있어, 글자를 y좌표만으로 줄로 묶으면 나란히 놓인
    칸들의 글자가 한 줄에 섞여 들어온다(예: "토의자끼리의 의견 (…)과/와 토의 전체 내용").
    그러면 빈칸 앞말로 문항을 찾을 수 없다. 그래서 칸 경계로 글자를 먼저 나눈 뒤
    칸 안에서만 줄을 묶어, .hwp 원본과 같은 읽기 순서를 만든다.
    """
    import pdfplumber
    out = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            cells = [c for t in page.find_tables() for c in t.cells if c]
            groups, loose = {}, []
            for ch in page.chars:
                cx, cy = (ch["x0"] + ch["x1"]) / 2, (ch["top"] + ch["bottom"]) / 2
                best = None
                for c in cells:
                    if c[0] - 0.5 <= cx <= c[2] + 0.5 and c[1] - 0.5 <= cy <= c[3] + 0.5:
                        area = (c[2] - c[0]) * (c[3] - c[1])
                        if best is None or area < best[0]:
                            best = (area, c)
                (groups.setdefault(best[1], []) if best else loose).append(ch)

            # 칸은 (칸 위치) 순으로, 칸 밖 글자는 줄 단위로 같은 목록에 넣어 정렬한다
            items = [(c[1], c[0], [ch for line in _group_lines(chs) for ch in line])
                     for c, chs in groups.items()]
            items += [(line[0]["top"], line[0]["x0"], line)
                      for line in _group_lines(loose)]
            items.sort(key=lambda it: (round(it[0] / 3), it[1]))
            for _top, _x0, chs in items:
                out.append([(ch["text"], _char_color(ch)) for ch in chs])
    return out


# ---------------------------------------------------------------- 공통
def _is_distdoc(path):
    """배포용(읽기 전용)으로 저장된 .hwp인지 — 보고서에 그대로 적기 위해 구분한다."""
    import olefile
    ole = olefile.OleFileIO(path)
    try:
        return bool(ole.openstream("FileHeader").read()[36] & 4)
    finally:
        ole.close()


def load(path):
    low = path.lower()
    if low.endswith(".hwpx"):
        return _hwpx(path), "hwpx"
    if low.endswith(".pdf"):
        return _pdf(path), "pdf"
    return _hwp(path), ("hwp(배포용)" if _is_distdoc(path) else "hwp")


def load_cells(path):
    """load()와 같되 PDF만 표 칸 단위로 읽는다(표가 많은 학습지용)."""
    if path.lower().endswith(".pdf"):
        return _pdf_cells(path), "pdf"
    return load(path)


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
