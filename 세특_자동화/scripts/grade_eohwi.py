#!/usr/bin/env python3
"""대단원3-2 「어휘의 양상」 학습지 채점기.

빈칸 20칸은 「토의하기」 채점기와 같은 방식(앞말·뒷말로 빈칸을 찾고 괄호가 망가진 경우를
보정)으로 읽고, 선택형 5칸(08·09·10)은 CLAUDE.md '학생 제출물 표시 규칙'에 따라
오답 보기를 지운 삭제형, 정답 보기의 색만 바꾼 색칠형으로 판정한다.
보기를 모두 지웠거나 둘 다 색칠한 경우는 판정하지 않고 교사 확인 목록에 올린다.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from extract_submission import load_cells as load, render  # noqa: E402
from grade_touui import compact, patterns  # noqa: E402

TEMPLATE = pathlib.Path(".claude/cache/원본/어휘의양상_학습지.hwp")

# (키, 앞말, 뒷말, 칸폭, 정답, 허용 표현, 보조 앞말, 보조 뒷말)
BLANKS = [
    ("01-1", "일정한범위안에서쓰이는", "의집합", 20, "단어", ("단어", "낱말"), "", ()),
    ("01-2", "어휘의양상과쓰임이", "나타남", 24, "달리/다르게", ("달리", "다르게", "다양하게"), "", ()),
    ("02-1", "", "로/으로된어휘,전통적생활문화", 20, "한자", ("한자",), "", ()),
    ("02-2", "말을", "하거나", 20, "변형", ("변형", "줄임", "줄여", "줄이", "축약"), "", ()),  # 줄이: 승인된 '줄임'의 활용형
    ("03-1", "", ",무탈하게,처서", 20, "별고", ("별고",), "", ()),
    ("03-2", "무탈하게,처서,", ",그믐", 20, "자제", ("자제",), "", ()),
    ("03-3", "생파,", ",각", 20, "댓", ("댓",), "", ()),
    ("04-1", "해당분야의", "개념을담고있음", 20, "전문적", ("전문",), "", ()),
    ("04-2", "정확하고", "로/으로소통할수있음", 20, "효율적", ("효율", "효과적"), "", ()),
    ("05-1", "", ",심리", 20, "변론", ("변론",), "", ()),
    ("05-2", "수비드,", "", 20, "시포나드", ("시포나드",), "", ()),
    ("05-3", "아나필락시스,", "", 20, "에피네프린", ("에피네프린",), "", ()),
    ("06-1", "", "을/를많이사용함", 20, "줄임말", ("줄임말", "준말", "축약어"), "", ()),
    ("06-2", "통해", "나/이나태도를", 20, "감정", ("감정", "기분", "느낌"), "", ()),
    ("07-1", "울,", "", 20, "넘", ("넘",), "", ()),
    ("07-2", "", ",봐야겠넹", 20, "좋당", ("좋당",), "", ()),
    ("07-3", "짝짝,", "", 20, "꾸벅", ("꾸벅",), "", ()),
    ("07-4", "찐맛집,", "", 20, "꿀팁", ("꿀팁",), "", ()),
    ("11-1", "어휘의사용양상에", "이/가있음", 20, "차이", ("차이", "다름"), "", ()),
    ("11-2", "언어에", "태도를지녀야", 20, "관용적", ("관용", "개방", "열린", "존중"), "", ()),
]

# (키, 앞말, 뒷말, 보기, 정답) — 정답은 답지에 표시가 없어 본문 맥락으로 정함(분석기준 v1 ※)
CHOICES = [
    ("08-1", "할아버지와대화할때", "사용하여", ("그대로", "변형하여"), "그대로"),
    ("08-2", "새말은", "표현하는것이", ("그대로", "쉽게풀어"), "쉽게풀어"),
    ("09-1", "효율성이", ".그러나", ("낮아진다", "높아진다"), "높아진다"),
    ("09-2", "일반인과대화할때", "를사용하면", ("전문어", "일상어"), "전문어"),
    ("10", "", "이고격식적인", ("사적", "공적"), "공적"),
]

CRIT = {"기준1": ["02-1", "02-2", "03-1", "03-2", "03-3"],
        "기준2": ["04-1", "04-2", "05-1", "05-2", "05-3"],
        "기준3": ["06-1", "06-2", "07-1", "07-2", "07-3", "07-4"],
        "기준4": ["08-1", "08-2", "09-1", "09-2", "10"],
        "기준5": ["01-1", "01-2", "11-1", "11-2"]}
BAND = {"기준1": (5, 3), "기준2": (5, 3), "기준3": (5, 3), "기준4": (5, 3), "기준5": (4, 2)}

MARK = re.compile(r"\[C\](.*?)\[/\]")
TICKS = "○◯●Oo0ㅇVv✓√✔"   # 보기 옆에 덧붙인 표시(승인 규칙 밖 — 교사 확인용으로만 판정)
_tpl = None


def _pats(row):
    _k, before, after, w, _a, _alt, b2, a2 = row
    return patterns(before, after, w, (b2,), a2)


def template_blanks():
    global _tpl
    if _tpl is None:
        lines, _ = load(str(TEMPLATE))
        t = compact(render(lines, False))
        _tpl = {}
        for row in BLANKS:
            hit = next((m for p in _pats(row) if (m := re.search(p, t))), None)
            _tpl[row[0]] = hit.group(1).strip() if hit else None
    return _tpl


def pick(inner_marked, options):
    """선택형 괄호 안(색 표시 포함)을 보고 학생의 답을 판정한다."""
    plain = MARK.sub(r"\1", inner_marked)
    colored = "".join(MARK.findall(inner_marked))
    remain = [o for o in options if o in plain]
    painted = [o for o in options if o in colored]
    if len(painted) == 1:
        return painted[0], "색칠형"
    if len(painted) == 2:
        return None, "둘다색칠"
    if len(remain) == 1:
        return remain[0], "삭제형"
    if not remain:
        return None, "모두삭제"
    ticked = [o for o in options
              if re.search(re.escape(o) + "[" + TICKS + "]", plain)
              or re.search("[" + TICKS + "]" + re.escape(o), plain)]
    if len(ticked) == 1:
        return ticked[0], "표시형"
    return None, "무응답"


def grade_choices(marked_text):
    out = {}
    for key, before, after, options, ans in CHOICES:
        pat = re.escape(before) + r"\(((?:[^()]|\[/?C?\]){0,80}?)\)" + \
            re.escape(after).replace(r"\.", r"\.?")
        # 색 표시가 앞말·뒷말 사이에 끼어 있을 수 있어 표시를 뺀 본문으로도 위치를 찾는다
        m = re.search(pat, marked_text)
        if not m and before:
            m2 = re.search(re.escape(before) + r"\(((?:[^()]|\[/?C?\]){0,80}?)\)", marked_text)
            if m2 and any(o in MARK.sub(r"\1", m2.group(1)) for o in options):
                m = m2
        if not m:
            # 색 표시가 괄호 밖까지 이어져 위 패턴에 안 걸리는 경우를 구분해 적어 둔다
            stripped = re.sub(r"\[/?C?\]", "", marked_text)
            loose = re.escape(before) + r"\([^()]*\)" + re.escape(after).replace(r"\.", r"\.?")
            why = "미검출(표시가 괄호 밖까지 이어짐)" if re.search(loose, stripped) else "미검출"
            out[key] = ["?", why, ""]
            continue
        got, how = pick(m.group(1), options)
        if got is None:
            out[key] = ["-" if how == "무응답" else "!", how, how]
        else:
            out[key] = ["O" if got == ans else "X", got, how]
    return out


def grade(path):
    lines, fmt = load(str(path))
    text = compact(render(lines, False))
    marked = re.sub(r"\s+", "", render(lines, True))
    tpl = template_blanks()
    items, miss, fixed, notes = {}, [], [], []
    for row in BLANKS:
        key, alts = row[0], row[5]
        hit = next(((i, m) for i, p in enumerate(_pats(row)) if (m := re.search(p, text))), None)
        if hit is None:
            items[key] = ["?", "미검출"]
            miss.append(key)
            continue
        i, m = hit
        if i > 0:
            fixed.append(key)
        v = m.group(1).strip()
        vc = compact(v)
        if not vc or vc == compact(tpl.get(key) or "\x00"):
            items[key] = ["-", ""]
        elif any(a in vc for a in alts):
            items[key] = ["O", v]
        else:
            items[key] = ["X", v]

    ticked = []
    for key, (mark, val, how) in grade_choices(marked).items():
        items[key] = [mark, val]
        if mark == "?":
            miss.append(key)
        elif mark == "!":
            notes.append(f"{key} {how} — 교사 확인 필요")
        if how == "표시형":
            ticked.append(key)
    if ticked:
        notes.append(f"선택형을 보기 옆 ○ 표시로 답함: {'·'.join(ticked)} — 승인 규칙 밖이라 교사 확인 권장")
    if pathlib.Path(path).read_bytes() == TEMPLATE.read_bytes():
        notes.append("빈 학습지 원본을 그대로 제출함 — 파일이 원본과 같음")

    if miss:
        notes.append(f"미검출 {len(miss)}칸({', '.join(miss)}) — 교사 확인 권장")
    if fixed:
        notes.append(f"괄호가 지워진 칸 보정해 읽음({', '.join(fixed)})")
    if "배포용" in fmt:
        notes.append("배포용(읽기 전용) 한글 파일 — 복호화해 읽음")

    out = {"format": fmt, "items": items, "notes": notes}
    for c, keys in CRIT.items():
        vals = [items[k][0] for k in keys]
        hi, mid = BAND[c]
        if all(v == "?" for v in vals):
            out[c] = "확인불가"
        else:
            o = vals.count("O")
            out[c] = "상" if o >= hi else ("중" if o >= mid else "하")
    out["_정답수"] = sum(1 for v in items.values() if v[0] == "O")
    return out


if __name__ == "__main__":
    res = {}
    for p in sorted(pathlib.Path(sys.argv[1]).iterdir()):
        if p.suffix.lower() in (".hwp", ".hwpx", ".pdf"):
            try:
                res[p.stem] = grade(p)
            except Exception as e:
                res[p.stem] = {"error": f"{type(e).__name__}: {e}"}
    print(json.dumps(res, ensure_ascii=False, indent=1))
