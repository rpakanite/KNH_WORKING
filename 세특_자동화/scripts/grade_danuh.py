#!/usr/bin/env python3
"""대단원3-1 「단어의 짜임」 학습지 채점기.

빈칸 56칸은 blank_diff로 빈 학습지와 맞대어 순서대로 뽑고, 02번 형태소 분석표(괄호가
없는 칸 10개)는 02번 구간에서 단어를 바르게 나눈 표기(예: 김,밥 / 헛-+소리)가 있는지 본다.
△·○ 표시는 도형으로 그리는 경우가 많아 판독하지 않는다(분석기준 v1).
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from blank_diff import compact, fills  # noqa: E402
from extract_submission import load_cells as load, render  # noqa: E402

TEMPLATE = pathlib.Path(".claude/cache/원본/단어의짜임_학습지.hwp")

# 빈칸 56칸 — 빈 학습지에 나오는 순서 그대로 (키, 정답, 허용 표현)
BLANKS = [
    ("01-1", "자립", ("자립형태소",)), ("01-2", "꽃", ()), ("01-3", "병", ()), ("01-4", "-개", ()),
    ("01-5", "하늘", ()), ("01-6", "지우-", ()), ("01-7", "형식", ("형식형태소",)), ("01-8", "-개", ()),
    ("01-9", "뜻", ("의미",)),
    ("03-1", "헛-", ()), ("03-2", "소리", ()), ("03-3", "헛-", ()),
    ("03-4", "가위", ()), ("03-5", "-질", ()), ("03-6", "-질", ()),
    ("04-1", "실질적 의미", ("실질", "의미", "뜻")), ("04-2", "-꾼", ()),
    ("05-1", "접두사", ()), ("05-2", "풋-", ()), ("05-3", "-쟁이", ()), ("05-4", "-꾸러기", ()),
    ("06-1", "어근", ()), ("06-2", "거울", ()), ("06-3", "어근", ()), ("06-4", "허리띠", ()),
    ("06-5", "허리", ()), ("06-6", "띠", ()), ("06-7", "책", ()), ("06-8", "가방", ()),
    ("06-9", "파생어", ()), ("06-10", "덧버선", ()), ("06-11", "덧-", ()), ("06-12", "버선", ()),
    ("06-13", "울-", ()), ("06-14", "-보", ()), ("06-15", "복합어", ()),
    ("07-1", "솔", ()), ("07-2", "나무", ()), ("07-3", "딸", ()), ("07-4", "-님", ()),
    ("07-5", "-ㄹ", ("ㄹ",)),
    ("08-1", "댓글", ()), ("08-2", "홈페이지", ()), ("08-3", "소리책", ()),
    ("09-1", "둘레", ()), ("09-2", "길", ()), ("09-3", "합성", ()), ("09-4", "누리", ()),
    ("09-5", "접사", ("접미사",)), ("09-6", "접사", ("접미사",)),
    ("09-7", "앞부분", ("앞글자", "첫글자", "앞")), ("09-8", "뒷부분", ("뒷글자", "끝글자", "뒤")),
    ("10-1", "누리집", ()), ("10-2", "캠핑족", ()), ("10-3", "인강", ()), ("10-4", "라볶이", ()),
]
# 순서가 바뀌어도 맞는 칸 묶음 (하늘, (꽃), (병) / (하늘), 꽃, 병, (지우-))
UNORDERED = [("01-2", "01-3"), ("01-5", "01-6")]

# 02번: 단어 → 바르게 나눈 형태소
SPLITS = [
    ("02-1", "바다", ["바다"]), ("02-2", "김밥", ["김", "밥"]), ("02-3", "헛소리", ["헛", "소리"]),
    ("02-4", "돌다리", ["돌", "다리"]), ("02-5", "색종이", ["색", "종이"]), ("02-6", "비옷", ["비", "옷"]),
    ("02-7", "주머니", ["주머니"]), ("02-8", "풋나물", ["풋", "나물"]), ("02-9", "가위질", ["가위", "질"]),
    ("02-10", "장난꾸러기", ["장난", "꾸러기"]),
]

CRIT = {"기준1": [k for k, *_ in BLANKS if k.startswith("01")],
        "기준2": [k for k, *_ in SPLITS] + [k for k, *_ in BLANKS if k.startswith("03")],
        "기준3": [k for k, *_ in BLANKS if k[:2] in ("04", "05")],
        "기준4": [k for k, *_ in BLANKS if k[:2] in ("06", "07")],
        "기준5": [k for k, *_ in BLANKS if k[:2] in ("08", "09", "10")]}
HI, MID = 0.8, 0.5        # 상: 정답률 80% 이상, 중: 50% 이상

_tpl = None


def norm(s):
    """하이픈(-)과 표시 기호를 빼고 비교한다 — 하이픈 생략은 정답으로 본다(분석기준 v1)."""
    return re.sub(r"[-–_\s△▲○◯●□■‘’'\"“”]", "", s)


def template():
    global _tpl
    if _tpl is None:
        _tpl = compact(render(load(str(TEMPLATE))[0], False))
    return _tpl


def section02(text):
    i, j = text.find("02다음단어들의형태소"), text.find("03다음단어의형태소")
    return text[i:j] if 0 <= i < j else ""


LABELS = ("동그라미", "동그리미", "세모", "네모", "삼각형")   # △·○를 글로 쓴 경우
MARKS = "△▲▵Δ○◯●ㅇOo⬆□■"


def grade_splits(text):
    """02번 — 단어마다 그 행에 적힌 형태소 조각을 모아 바른 나눔과 비교한다.

    학생들은 '김△,밥△', '김 -> 세모, 밥 -> 세모', '김:△ 밥:△'처럼 △·○ 표시나 그
    이름을 조각 사이에 섞어 쓰므로, 한글 조각만 뽑아 비교한다(△·○ 자체는 판독 제외).
    조각 순서는 따지지 않는다. 한글 조각 없이 △·○만 그린 행은 나눔을 판독할 수 없어
    '?'(판독 제외)로 둔다.
    """
    sec = section02(text)
    out = {}
    if not sec:
        return {k: ["?", "미검출"] for k, *_ in SPLITS}
    pos, starts = 0, []
    for _key, word, _parts in SPLITS:          # 행 머리(단어)를 차례로 찾는다
        k = sec.find(word, pos)
        starts.append(k)
        if k >= 0:
            pos = k + len(word)
    for n, (key, word, parts) in enumerate(SPLITS):
        if starts[n] < 0:
            out[key] = ["?", "미검출"]
            continue
        a = starts[n] + len(word)
        b = next((x for x in starts[n + 1:] if x >= 0), len(sec))
        seg = sec[a:b]
        for lb in LABELS:
            seg = seg.replace(lb, "|")
        toks = re.findall(r"[가-힣]+", seg)
        if len(toks) > len(parts) and toks[0] == word:   # '김밥: 김, 밥'처럼 단어를 다시 쓴 경우
            toks = toks[1:]
        shown = "+".join(toks)
        if not toks:
            marked = any(m in seg for m in MARKS) or "|" in seg
            out[key] = ["?", "△·○만 표시"] if marked else ["-", ""]
        elif sorted(toks) == sorted(parts):
            out[key] = ["O", shown]
        elif len(parts) > 1 and toks == [word]:
            out[key] = ["X", f"{word}(나누지 않음)"]
        else:
            out[key] = ["X", shown]
    return out


def grade(path):
    lines, fmt = load(str(path))
    text = compact(render(lines, False))
    got = fills(template(), text)
    items, fixed, notes = {}, [], []
    vals = {}
    for (key, ans, alts), (v, how) in zip(BLANKS, got):
        vals[key] = v
        if how == "보정":
            fixed.append(key)
        if how == "없음":
            items[key] = ["?", "미검출"]
        elif not norm(v):
            items[key] = ["-", ""]
        elif norm(v) == norm(ans) or any(norm(a) in norm(v) for a in alts):
            items[key] = ["O", v]
        else:
            items[key] = ["X", v]
    for a, b in UNORDERED:                   # 두 칸의 답이 서로 바뀐 경우도 정답
        ans_a = next(x[1] for x in BLANKS if x[0] == a)
        ans_b = next(x[1] for x in BLANKS if x[0] == b)
        if {norm(vals[a]), norm(vals[b])} == {norm(ans_a), norm(ans_b)}:
            items[a], items[b] = ["O", vals[a]], ["O", vals[b]]
    items.update(grade_splits(text))

    marks = [k for k, v in items.items() if v == ["?", "△·○만 표시"]]
    if marks:
        notes.append(f"02번 {len(marks)}칸은 형태소를 나누어 쓰지 않고 △·○만 표시 — "
                     "판독 제외(등급 계산에서 뺌), 교사 확인")
    miss = [k for k, v in items.items() if v[0] == "?" and k not in marks]
    if miss:
        notes.append(f"미검출 {len(miss)}칸({', '.join(miss)}) — 교사 확인 권장")
    if fixed:
        notes.append(f"괄호가 지워진 칸 보정해 읽음({', '.join(fixed)})")
    if "배포용" in fmt:
        notes.append("배포용(읽기 전용) 한글 파일 — 복호화해 읽음")
    if pathlib.Path(path).read_bytes() == TEMPLATE.read_bytes():
        notes.append("빈 학습지 원본을 그대로 제출함 — 파일이 원본과 같음")

    out = {"format": fmt, "items": items, "notes": notes}
    for c, keys in CRIT.items():
        vs = [items[k][0] for k in keys if items[k][0] != "?"]   # 판독 못 한 칸은 분모에서 뺀다
        if not vs:
            out[c] = "확인불가"
        else:
            r = vs.count("O") / len(vs)
            out[c] = "상" if r >= HI else ("중" if r >= MID else "하")
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
