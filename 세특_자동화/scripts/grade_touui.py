#!/usr/bin/env python3
"""대단원1-2 「토의하기」 학습지 채점기.

이 학습지는 문항 01~06이 전부 빈칸 채우기이고 선택형(O/X)도 서술형도 없다.
따라서 '학생 표시 규칙'(삭제형·색칠형·표시형) 판정은 쓰이지 않고, 27칸을 답지와 대조한다.
뜻이 같은 다른 표현은 허용 표현에 등록해 정답으로 인정한다(분석기준 4절 정성 관찰 포인트).

빈칸은 '앞말 + ( ) + 뒷말'로 찾는다. 학생이 답을 적다가 괄호를 지우거나 괄호를 겹쳐 쓰는
일이 잦아서, 엄격한 대조가 실패하면 보정 패턴을 차례로 더 시도한다. 그래도 못 찾은 칸은
임의로 판정하지 않고 '미검출'로 남겨 교사 확인 목록에 올린다(CLAUDE.md 표시 규칙).
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from extract_submission import load_cells as load, render  # noqa: E402

TEMPLATE = pathlib.Path(".claude/cache/원본/토의하기_학습지.hwp")
DECOR = "⇨⇧⇩↔→←•"          # 표의 흐름을 나타내는 장식 기호 — 본문으로 보지 않는다

# (키, 앞말, 뒷말, 칸폭, 정답, 허용 표현, 보조 앞말, 보조 뒷말)
#   앞말·뒷말은 공백을 지운 본문에서 빈칸 바로 앞·뒤에 붙는 글자다. 둘 중 하나는 비어도 된다.
#   보조 앞말·뒷말은 학생이 학습지 문구를 고쳐 써서 원래 앞말·뒷말이 사라진 경우에만 쓴다.
BLANKS = [
    ("01-1", "참여하게됨.", "에서무엇을운영할까", 24, "마을 축제", ("마을축제", "축제"), "", ()),
    ("02-1", "토의자소개,토의", "안내", 20, "순서", ("순서", "진행순서", "규칙"), "", ()),
    ("02-2", "대한토의자들의", "제시", 20, "의견", ("의견", "주장"), "", ()),
    ("02-3", "토의자끼리의의견", "", 20, "교환", ("교환", "조율"), "", ()),
    ("02-4", "청중의", "과/와토의자의", 20, "질문", ("질문", "질의"), "", ()),
    ("02-5", "토의자의", "", 20, "답변", ("답변", "응답", "대답"), "", ()),
    ("03-1", "학교를소개하는", "을/를열자", 20, "사진전", ("사진전", "사진"), "", ()),
    ("03-2", "학생들이", "이/가되어사진을설명", 20, "해설사",
     ("해설사", "해설자", "설명"), "", ("이/가되어", "가되어", "이되어")),
    ("03-3", "", "을/를만들어팔자", 20, "떡볶이", ("떡볶이", "떡볶기"), "", ()),
    ("03-4", "수익금을", "할수있음", 20, "기부", ("기부", "기증"), "", ()),
    ("03-5", "", "을/를운영하자", 24, "풍선 아트 체험장",
     ("풍선아트체험장", "풍선아트", "체험장"), "", ()),
    ("03-6", "②", "이/가적게듦", 20, "비용", ("비용", "돈", "예산"), "", ()),
    ("04-1", "풍선아트를배운", "수가적어", 20, "학생", ("학생", "사람", "인원"), "", ()),
    ("04-2", "재료구입", "이/가적지않고", 20, "비용", ("비용", "돈", "가격"), "", ()),
    ("04-3", "인터넷", "을/를보고배울수있음", 20, "동영상", ("동영상", "영상", "강의"), "", ()),
    ("04-4", "", "의개입", 20, "한재현", ("한재현",), "", ()),
    ("04-5", "끼어든것에대해", "을/를줌", 20, "주의", ("주의", "경고", "지적"), "", ()),
    ("04-6", "", "문제가있으니떡볶이를판매", 20, "안전", ("안전", "위생"), "", ()),
    ("04-7", "", "은/는학교와특별한관계가없는", 20, "사진전", ("사진전", "사진"),
     "윤이음의답변", ()),
    ("05-1", "토의", "제시,토의자소개", 20, "주제", ("주제", "논제"), "", ()),
    ("05-2", "토의진행", "안내", 20, "순서", ("순서", "방법", "규칙"), "", ()),
    ("05-3", "토의자에게", "부여", 20, "발언권", ("발언권", "발언기회", "말할기회"), "", ()),
    ("05-4", "토의내용", ",청중의토의", 20, "요약", ("요약", "정리"), "", ()),
    ("05-5", "청중의토의", "", 24, "참여 유도", ("참여유도", "참여", "유도"), "", ()),
    ("05-6", "토의내용", "·정리", 20, "종합", ("종합", "요약", "정리"), "", ()),
    ("06-1", "상대방의의견을", "하는태도", 20, "존중", ("존중", "경청", "수용"), "", ()),
    ("06-2", "상대방의", "이/가끝나지않았는데", 20, "발언", ("발언", "말", "이야기"), "", ()),
]

CRIT = {"기준1": ["01-1"] + [f"02-{i}" for i in range(1, 6)],
        "기준2": [f"03-{i}" for i in range(1, 7)],
        "기준3": [f"04-{i}" for i in range(1, 8)],
        "기준4": [f"05-{i}" for i in range(1, 7)],
        "기준5": [f"06-{i}" for i in range(1, 3)]}
BAND = {"기준1": (5, 3), "기준2": (5, 3), "기준3": (6, 4), "기준4": (5, 3), "기준5": (2, 1)}

_tpl = None


def compact(s):
    """공백과 표 장식 기호를 지워 .hwp와 PDF에서 같은 모양이 되게 한다."""
    return re.sub(r"\s+", "", s).translate({ord(c): None for c in DECOR})


def patterns(before, after, w, before2=("",), after2=()):
    """빈칸 하나를 찾을 패턴 목록 — 엄격한 것부터, 괄호가 망가진 경우의 보정까지."""
    pre, post = re.escape(before), re.escape(after)
    pats = [pre + r"\(([^()]{0,%d})\)" % w + post]
    for alt in after2:                                    # 학생이 뒷말을 고쳐 쓴 경우
        pats.append(pre + r"\(([^()]{0,%d})\)" % w + re.escape(alt))
    pats.append(pre + r"\(([^()]{0,%d}?)\)?" % w + post)  # 닫는 괄호를 지운 경우
    pats.append(pre + r"\((.{0,%d}?)\)" % w + post)       # 괄호를 겹쳐 쓴 경우
    if before:                                            # 여는 괄호를 지운 경우
        pats.append(pre + r"\(?([^()]{0,%d})\)" % w + post)
    if before2 and before2[0]:
        pats.append(re.escape(before2[0]) + r"\(?([^()]{0,%d})\)" % w + post)
    if before:                                            # 뒷말 앞부분까지 지운 경우
        for cut in range(1, len(after)):
            pats.append(pre + r"\(([^()]{0,%d}?)\)?" % w + re.escape(after[cut:]))
    for alt in after2:                                    # 앞말까지 고쳐 쓴 경우
        pats.append(r"\(([^()]{0,%d})\)" % w + re.escape(alt))
    return pats


def _pats(row):
    _k, before, after, w, _a, _alt, b2, a2 = row
    return patterns(before, after, w, (b2,), a2)


def template_blanks():
    """빈 학습지에서 각 빈칸이 '비어 있는 상태'로 보이는 값을 모아 둔다."""
    global _tpl
    if _tpl is None:
        lines, _ = load(str(TEMPLATE))
        t = compact(render(lines, False))
        _tpl = {}
        for row in BLANKS:
            hit = next((m for p in _pats(row) if (m := re.search(p, t))), None)
            _tpl[row[0]] = hit.group(1).strip() if hit else None
    return _tpl


def grade(path):
    lines, fmt = load(str(path))
    text = compact(render(lines, False))
    tpl = template_blanks()
    items, miss, fixed = {}, [], []
    for row in BLANKS:
        key, _before, _after, _w, _ans, alts, _b2, _a2 = row
        pats = _pats(row)
        hit = next(((i, m) for i, p in enumerate(pats) if (m := re.search(p, text))), None)
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
            items[key] = ["-", ""]            # 빈 학습지와 같음 = 무응답
        elif any(a in vc for a in alts):
            items[key] = ["O", v]
        else:
            items[key] = ["X", v]

    out = {"format": fmt, "items": items, "notes": []}
    if miss:
        out["notes"].append(f"미검출 {len(miss)}칸({', '.join(miss)}) — 교사 확인 권장")
    if len(miss) >= 5:
        out["notes"].append("파일 구조 확인 필요")
    if fixed:
        out["notes"].append(f"괄호가 지워진 칸 보정해 읽음({', '.join(fixed)})")
    if "배포용" in fmt:
        out["notes"].append("배포용(읽기 전용) 한글 파일 — 복호화해 읽음")

    for c, keys in CRIT.items():
        vals = [items[k][0] for k in keys]
        hi, mid = BAND[c]
        if all(v == "?" for v in vals):
            out[c] = "확인불가"          # 판독 실패 — 무응답과 구분한다
        else:
            # 빈칸을 그대로 둔 칸('-')은 무응답이므로 미도달로 센다(지침: 무응답≠확인불가)
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
