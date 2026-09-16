#!/usr/bin/env python3
"""대단원4-2 「주장하는 글 쓰기」 2~4차시 학습지 1차 채점기.

승인된 분석기준(v3)의 기계 판정 가능한 문항만 처리한다.
  - 빈칸형 01·04·05·07, 03의 까닭 빈칸  → 정답 대조
  - 선택형 03의 O/X, 08의 (1)(2)        → 남은 보기 / 색이 바뀐 보기로 판정
서술형 02·06은 채점하지 않고 학생이 쓴 원문만 뽑아 둔다(Claude가 직접 읽고 판단).

판정 결과는 O(정답) / X(오답) / -(무응답) / ?(판정 보류) 로 표기한다.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from extract_submission import load, render  # noqa: E402

# 빈 학습지 원문 — 학생이 실제로 써 넣은 부분만 남기기 위한 대조 기준
TEMPLATE = pathlib.Path(".claude/cache/원본/주장하는글쓰기_2-4차시_학습지.hwp")
_tpl_cache = None


def template_text():
    global _tpl_cache
    if _tpl_cache is None:
        try:
            lines, _ = load(str(TEMPLATE))
            _tpl_cache = compact(render(lines, False))
        except Exception:
            _tpl_cache = ""
    return _tpl_cache


MIN_TPL_RUN = 8          # 이 길이 이상 학습지와 겹치면 본문이 섞여 든 것으로 본다


def student_only(text):
    """서술형 구간에서 학습지 본문과 겹치는 대목을 지우고 학생이 쓴 말만 남긴다.

    PDF는 표의 칸들이 한 줄로 합쳐져 나오는 탓에 학생 답과 학습지 본문이 한 덩어리가
    된다. 줄 단위로는 걸러지지 않으므로, 빈 학습지와 글자 단위로 대조해 겹치는 구간만
    도려낸다.
    """
    tpl = template_text()
    if not tpl:
        return text.strip()
    # 공백을 뺀 문자열과 원문 위치의 대응표
    comp, idx = [], []
    for i, ch in enumerate(text):
        if not ch.isspace():
            comp.append(ch); idx.append(i)
    comp = "".join(comp)

    drop, i = set(), 0
    while i < len(comp):
        hi = i
        # 학습지에 들어 있는 가장 긴 구간을 찾는다
        while hi < len(comp) and comp[i:hi + 1] in tpl:
            hi += 1
        if hi - i >= MIN_TPL_RUN:
            drop.update(idx[i:hi])
            i = hi
        else:
            i += 1
    out = "".join(ch for j, ch in enumerate(text) if j not in drop)
    return _tidy(out)


# 8자 미만이라 위 대조에 걸리지 않고 남는 학습지 조각들
RESIDUE = [
    r"(표현하기|근거\s*마련하기|개요\s*짜기|주장\s*정하기)",
    r"(잡지|면담|텔레비전|신문|책)\s*\(?[^)]{0,12}\)?\s*\.?",   # 03번 표 잔재
    r"\)\s*(제시|결론|서론|본론)",
    r"이/가\s*떨어짐\.?",
    r"^\s*-?\s*\d+\s*-?\s*$",
]


def _tidy(out):
    for pat in RESIDUE:
        out = re.sub(pat, " ", out)
    out = re.sub(r"(^|\s)[^()\s]{0,4}\)", " ", out)    # 앞이 잘려 남은 '강조 )' 같은 조각
    out = re.sub(r"\s+", " ", out)
    return out.strip(" ➜•\t-:/.,").strip()

MARK = re.compile(r"\[/?C?\]")


def compact(s):
    return re.sub(r"\s+", "", s)


def plain(s):
    return MARK.sub("", s)


# ---- 빈칸 문항: (키, 정규식, 정답 판정 함수) -------------------------------
def has(*subs):
    return lambda v: any(s in v for s in subs)


BLANKS = [
    ("01-1", r"(?:주변에서일어나는)?\(?([^)（）\n]{0,24}?)\)?을/를떠올려", has("문제")),
    ("01-2", r"자기전에스마트폰을\(?([^)\n]{0,24}?)\)?\.", has("사용하지말", "사용하지않", "쓰지말", "사용금지", "안쓰")),
    ("04-1", r"글을좀더\(?([^)\n]{0,24}?)\)?있게", has("짜임새", "짜임")),
    ("04-2", r"전체적인\(?([^)\n]{0,24}?)\)?이/가자연스러운가", has("흐름")),
    ("04-3", r"주장을뒷받침하는\(?([^)\n]{0,24}?)\)?한근거", has("타당")),
    ("04-4", r"\(?([^)\n]{0,12}?)\)?,본론,결론에맞게", has("서론")),
    ("05-1", r"독자의\(?([^)\n]{0,24}?)\)?과/와관심유발", has("흥미", "관심")),
    ("05-2", r"글에서다루려는\(?([^)\n]{0,24}?)\)?제시", has("문제")),
    ("05-3", r"주장을뒷받침하는\(?([^)\n]{0,24}?)\)?제시", has("근거")),
    ("05-4", r"글전체의내용요약,\(?([^)\n]{0,24}?)\)?", has("정리", "마무리")),
    ("07-1", r"\(?([^)\n]{0,16}?)\)?에스마트폰을사용하지말아야", has("자기전", "잠들기전", "자기직전")),
    ("07-2", r"사용하면\(?([^)\n]{0,24}?)\)?을/를해칠", has("눈건강", "눈의건강", "시력")),
    ("07-3", r"수면부족이생기고\(?([^)\n]{0,24}?)\)?이/가낮아진다", has("수면의질", "수면질")),
]

# 까닭 빈칸. 학생이 '없음' 대신 '없다', 'X'처럼 써도 뜻이 같으면 정답으로 본다.
NEG, POS = ("없", "X", "x", "무관"), ("있", "O", "o")
REASON = [
    ("03까닭-관련", r"주장과직접적인관련이[^(\n]{0,4}\(([^)\n]{0,16})\)",
     [NEG, NEG, POS, POS, POS, POS]),
]
REASON_SINGLE = [
    ("03까닭-객관성", r"개인의경험이라[^(\n]{0,4}\(([^)\n]{0,16})\)", has("객관")),
    ("03까닭-신뢰1", r"전문가가이야기한내용으로[^(\n]{0,4}\(([^)\n]{0,16})\)", has("신뢰")),
    ("03까닭-신뢰2", r"언론사에서제작한자료이기때문에[^(\n]{0,4}\(([^)\n]{0,16})\)", has("신뢰")),
]

OX_ANSWERS = ["X", "X", "O", "O", "O", "O"]      # 잡지·면담·텔레비전·신문·책·신문
OX_LABELS = ["잡지", "면담", "텔레비전", "신문", "책", "신문2"]
# 각 행을 가려내는 '자료 내용' 앵커 (학생이 지우지 않는 본문)
OX_ANCHORS = ["스마트아이티", "반학생두명과면담", "안과교수", "녹내장", "블루라이트", "우울증이나조울증"]

PAREN = re.compile(r"\(([^()]{0,40})\)")
MARKS = "oO0vVㅇㅁ√✓○◯●■✔"      # 정답 옆에 덧붙이는 표시 (제3의 방식)
# 03번 '까닭' 빈칸 — O/X 선택칸으로 오인하지 않도록 걸러낸다
REASON_CUE = ("관련이", "경험이라", "내용으로", "때문에")


def ox_cells(marked_c):
    """괄호 단위로 훑어 O/X 선택칸만 골라 [(위치, [(글자, 색칠, 표시)])] 목록으로 만든다.

    'ㅇ'처럼 고른 보기 옆에 덧붙이는 표시도 함께 읽는다. 앞말이 '관련이' 등인 괄호는
    03번 '까닭' 빈칸이므로 선택칸으로 세지 않는다.
    """
    cells = []
    for m in PAREN.finditer(marked_c):
        # '까닭' 빈칸인지 판단할 때는 단서가 괄호 '바로 앞'에 와야 한다.
        # 앞줄에서 딸려온 '...관련이(있음).' 때문에 정상 칸이 걸러지지 않도록 한다.
        before = MARK.sub("", marked_c[max(0, m.start() - 16):m.start()]).rstrip()
        if before.endswith(REASON_CUE):
            continue
        inner = m.group(1)
        letters = _scan(inner, "OX")
        if letters is None:
            continue
        if not letters and re.search(r"[ox]", inner):
            letters = _scan(inner, "ox")       # 소문자로만 적은 학생
            if letters is None:
                continue
        if 1 <= len(letters) <= 2:
            cells.append((m.start(), letters))
    return cells


def _scan(inner, opts):
    """괄호 안을 훑어 [(글자, 색칠, 표시)]를 만든다. O/X 칸이 아니면 None."""
    letters, i, depth = [], 0, 0
    while i < len(inner):
        if inner.startswith("[C]", i):
            depth += 1; i += 3; continue
        if inner.startswith("[/]", i):
            depth -= 1; i += 3; continue
        ch = inner[i]
        if ch in opts:
            nxt = inner[i + 1:i + 2]
            letters.append([ch.upper(), depth > 0, nxt in MARKS and nxt not in opts])
        elif ch in MARKS and letters:
            letters[-1][2] = True              # 표시가 조금 떨어져 붙은 경우
        elif ch not in ", \t":
            return None                        # O/X 칸이 아님 (예: "(있음)")
        i += 1
    return letters


def assign_rows(cells, marked_c):
    """O/X 칸을 가장 가까운 자료 행에 하나씩 붙인다(빠진 칸이 있어도 밀리지 않도록)."""
    anchors = {}
    for lab, kw in zip(OX_LABELS, OX_ANCHORS):
        i = marked_c.find(kw)
        if i >= 0:
            anchors[lab] = i
    pairs = sorted(((abs(pos - apos), lab, idx)
                    for idx, (pos, _) in enumerate(cells)
                    for lab, apos in anchors.items()))
    out, used_lab, used_cell = {}, set(), set()
    for _, lab, idx in pairs:
        if lab in used_lab or idx in used_cell:
            continue
        out[lab] = cells[idx][1]
        used_lab.add(lab); used_cell.add(idx)
    return out


def pick(letters):
    """한 칸의 [(글자, 색칠, 표시)]에서 학생이 고른 보기를 판정한다."""
    if len(letters) == 1:
        return letters[0][0], "삭제형"
    on = [l for l, c, _ in letters if c]
    if len(on) == 1:
        return on[0], "색칠형"
    if len(on) == 2:
        return None, "둘다색칠"
    marked = [l for l, _, mk in letters if mk]
    if len(marked) == 1:
        return marked[0], "표시형*"
    return None, "무응답"


def choice(marked_c, opt1, opt2):
    """08번처럼 낱말 두 개 중 고르는 문항.

    삭제형·색칠형 외에 '정답 낱말 옆에 o 같은 표시를 덧붙이는' 방식도 실제 제출물에서
    확인되어 함께 판정한다(승인된 분석기준 v3에는 없는 방식이므로 교사 확인 대상으로 표시).
    """
    def state(word):
        i = marked_c.find(word)
        if i < 0:
            return None, False
        before = marked_c[:i]
        colored = before.count("[C]") > before.count("[/]")
        after = MARK.sub("", marked_c[i + len(word):i + len(word) + 4]).lstrip(", ")
        return ("C" if colored else "K"), bool(after) and after[0] in MARKS

    s1, m1 = state(opt1)
    s2, m2 = state(opt2)
    if s1 and not s2:
        return opt1, "삭제형"
    if s2 and not s1:
        return opt2, "삭제형"
    if s1 == "C" and s2 == "K":
        return opt1, "색칠형"
    if s2 == "C" and s1 == "K":
        return opt2, "색칠형"
    if m1 and not m2:
        return opt1, "표시형*"
    if m2 and not m1:
        return opt2, "표시형*"
    if s1 is None and s2 is None:
        return None, "미검출"
    return None, "무응답"


def span_lines(text, start_pat, end_pat):
    """문항 줄과 다음 문항 줄 사이에 학생이 써 넣은 줄만 모은다.

    서술형 답은 문항 바로 아래 줄에 들어가므로, 통짜 텍스트에서 자르면
    (특히 PDF에서) 표의 다른 칸이 섞여 들어온다. 줄 구조를 그대로 쓴다.
    """
    lines = text.split("\n")
    si = next((i for i, l in enumerate(lines) if re.search(start_pat, l)), None)
    if si is None:
        return ""
    ei = next((i for i in range(si + 1, len(lines)) if re.search(end_pat, lines[i])), len(lines))
    head = lines[si]
    m = re.search(start_pat, head)
    out = [head[m.end():]] + lines[si + 1:ei]
    return " ".join(x.strip(" ➜•\t") for x in out if x.strip(" ➜•\t"))


def grade(path):
    lines, fmt = load(str(path))
    marked_c = compact(render(lines, True))
    text_c = compact(render(lines, False))
    r = {"format": fmt, "items": {}, "notes": []}

    for key, pat, ok in BLANKS:
        m = re.search(pat, text_c)
        if not m:
            r["items"][key] = ["?", ""]
            continue
        v = m.group(1).strip()
        r["items"][key] = ["O" if ok(v) else ("-" if not v else "X"), v]

    # 03 O/X 6칸 — 자료 행에 붙여서 판정
    cells = ox_cells(marked_c)
    by_row = assign_rows(cells, marked_c)
    cells_ok = any(pick(v)[0] for v in by_row.values())
    for i, lab in enumerate(OX_LABELS):
        if lab in by_row:
            got, how = pick(by_row[lab])
            verdict = "O" if got == OX_ANSWERS[i] else ("-" if got is None else "X")
            r["items"][f"03OX-{lab}"] = [verdict, f"{got or '?'}({how})"]
        else:
            r["items"][f"03OX-{lab}"] = ["?", "미검출"]
    if len(cells) != 6:
        r["notes"].append(f"03번 선택칸 {len(cells)}개 검출(정상 6개)")

    # 03 까닭
    for key, pat, answers in REASON:
        found = re.findall(pat, text_c)
        misplaced = sum(1 for v in found if v.strip() in ("O", "X")) if not cells_ok else 0
        for i, ans in enumerate(answers):
            v = found[i].strip() if i < len(found) else ""
            ok = any(a in v for a in ans)
            r["items"][f"{key}{i+1}"] = ["O" if ok else ("-" if not v else "X"), v]
        if misplaced >= 3:
            r["notes"].append("03번 활용 여부를 '까닭' 칸에 표시한 것으로 보임 → 교사 확인 필요")
            for lab in OX_LABELS:
                k = f"03OX-{lab}"
                if r["items"].get(k, [""])[0] == "-":
                    r["items"][k] = ["?", "까닭칸에 표시한 듯"]
    for key, pat, ok in REASON_SINGLE:
        m = re.search(pat, text_c)
        v = m.group(1).strip() if m else ""
        r["items"][key] = ["O" if v and ok(v) else ("-" if not v else "X"), v]

    # 08번
    got1, how1 = choice(marked_c, "요약정리하는", "반박하는")
    r["items"]["08-1"] = ["O" if got1 == "요약정리하는" else ("-" if got1 is None else "X"), f"{got1 or '?'}({how1})"]
    got2, how2 = choice(marked_c, "인상깊게", "과장하여")
    r["items"]["08-2"] = ["O" if got2 == "인상깊게" else ("-" if got2 is None else "X"), f"{got2 or '?'}({how2})"]

    # 서술형 원문 (채점하지 않음 — Claude가 직접 읽고 판단)
    text = render(lines, False)
    r["essay"] = {
        "02": student_only(span_lines(text, r"세\s*가지를\s*써\s*보자\.",
                                      r"다음은\s*유나가|^\s*03\b"))[:250],
        "06": student_only(span_lines(text, r"까닭은\s*무엇인지\s*써\s*보자\.",
                                      r"유나의\s*주장과|^\s*07\b"))[:300],
    }
    return r


if __name__ == "__main__":
    out = {}
    for p in sorted(pathlib.Path(sys.argv[1]).iterdir()):
        if p.suffix.lower() in (".hwp", ".hwpx", ".pdf"):
            try:
                out[p.stem] = grade(p)
            except Exception as e:
                out[p.stem] = {"error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False, indent=1))
