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
    ("01-1", "자립", ()), ("01-2", "꽃", ()), ("01-3", "병", ()), ("01-4", "-개", ()),
    ("01-5", "하늘", ()), ("01-6", "지우-", ()), ("01-7", "형식", ()), ("01-8", "-개", ()),
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
    ("07-5", "-ㄹ", ()),
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
SEP = r"[-]?\s*[,+/·|ㆍ]\s*[-]?"

CRIT = {"기준1": [k for k, *_ in BLANKS if k.startswith("01")],
        "기준2": [k for k, *_ in SPLITS] + [k for k, *_ in BLANKS if k.startswith("03")],
        "기준3": [k for k, *_ in BLANKS if k[:2] in ("04", "05")],
        "기준4": [k for k, *_ in BLANKS if k[:2] in ("06", "07")],
        "기준5": [k for k, *_ in BLANKS if k[:2] in ("08", "09", "10")]}
HI, MID = 0.8, 0.5        # 상: 정답률 80% 이상, 중: 50% 이상

_tpl = None


def norm(s):
    """하이픈(-)과 표시 기호를 빼고 비교한다 — 하이픈 생략은 정답으로 본다(분석기준 v1)."""
    return re.sub(r"[-\s△▲○◯●□■]", "", s)


def template():
    global _tpl
    if _tpl is None:
        _tpl = compact(render(load(str(TEMPLATE))[0], False))
    return _tpl


def section02(text):
    i, j = text.find("02다음단어들의형태소"), text.find("03다음단어의형태소")
    return text[i:j] if 0 <= i < j else ""


def grade_splits(text):
    sec = section02(text)
    out = {}
    for key, word, parts in SPLITS:
        if not sec:
            out[key] = ["?", "미검출"]
            continue
        if len(parts) == 1:
            split_any = any(re.search(re.escape(word[:k]) + SEP + re.escape(word[k:]), sec)
                            for k in range(1, len(word)))
            n = sec.count(word)
            out[key] = ["X", "잘못 나눔"] if split_any else (["O", word] if n >= 2 else ["-", ""])
        else:
            if re.search(SEP.join(re.escape(p) for p in parts), sec):
                out[key] = ["O", "+".join(parts)]
            elif any(re.search(re.escape(word[:k]) + SEP + re.escape(word[k:]), sec)
                     for k in range(1, len(word))):
                out[key] = ["X", "다르게 나눔"]
            else:
                out[key] = ["-", ""]
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

    miss = [k for k, v in items.items() if v[0] == "?"]
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
        vs = [items[k][0] for k in keys]
        if all(v == "?" for v in vs):
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
