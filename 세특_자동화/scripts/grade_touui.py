#!/usr/bin/env python3
"""대단원1-2 「토의하기」 학습지 채점기.

이 학습지는 문항 01~06이 전부 빈칸 채우기이고 선택형(O/X)도 서술형도 없다.
따라서 '학생 표시 규칙'(삭제형·색칠형·표시형) 판정은 쓰이지 않고, 27칸을 답지와 대조한다.
뜻이 같은 다른 표현은 ALT에 등록해 정답으로 인정한다(분석기준 4절 정성 관찰 포인트).
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from extract_submission import load, render  # noqa: E402

MARK = re.compile(r"\[/?C?\]")
TEMPLATE = pathlib.Path(".claude/cache/원본/토의하기_학습지.hwp")

# (키, 앞말 정규식, 정답, 허용 표현) — 앞말은 공백 제거한 본문에서 빈칸 바로 앞을 가리킨다
BLANKS = [
    ("01-1", r"\(([^)\n]{0,20})\)에서무엇을운영할까", "마을 축제", ("마을축제", "축제")),
    ("02-1", r"토의자소개,토의\(([^)\n]{0,20})\)안내", "순서", ("순서", "진행순서", "규칙")),
    ("02-2", r"토의자들의\(([^)\n]{0,20})\)제시", "의견", ("의견", "주장")),
    ("02-3", r"토의자끼리의의견\(([^)\n]{0,20})\)", "교환", ("교환", "조율")),
    ("02-4", r"청중의\(([^)\n]{0,20})\)과/와토의자의", "질문", ("질문", "질의")),
    ("02-5", r"토의자의\(([^)\n]{0,20})\)", "답변", ("답변", "응답", "대답")),
    ("03-1", r"학교를소개하는\(([^)\n]{0,20})\)을/를열자", "사진전", ("사진전", "사진")),
    ("03-2", r"학생들이\(([^)\n]{0,20})\)이/가되어사진을설명", "해설사", ("해설사", "해설자", "설명")),
    ("03-3", r"\(([^)\n]{0,20})\)을/를만들어팔자", "떡볶이", ("떡볶이", "떡볶기")),
    ("03-4", r"수익금을\(([^)\n]{0,20})\)할수있음", "기부", ("기부", "기증")),
    ("03-5", r"\(([^)\n]{0,24})\)을/를운영하자", "풍선 아트 체험장", ("풍선아트체험장", "풍선아트", "체험장")),
    ("03-6", r"②\(([^)\n]{0,20})\)이/가적게듦", "비용", ("비용", "돈", "예산")),
    ("04-1", r"풍선아트를배운\(([^)\n]{0,20})\)수가적어", "학생", ("학생", "사람", "인원")),
    ("04-2", r"재료구입\(([^)\n]{0,20})\)이/가적지않고", "비용", ("비용", "돈", "가격")),
    ("04-3", r"인터넷\(([^)\n]{0,20})\)을/를보고배울수있음", "동영상", ("동영상", "영상", "강의")),
    ("04-4", r"\(([^)\n]{0,20})\)의개입", "한재현", ("한재현",)),
    ("04-5", r"끼어든것에대해\(([^)\n]{0,20})\)을/를줌", "주의", ("주의", "경고", "지적")),
    ("04-6", r"\(([^)\n]{0,20})\)문제가있으니떡볶이를판매", "안전", ("안전", "위생")),
    ("04-7", r"\(([^)\n]{0,20})\)은/는학교와특별한관계가없는", "사진전", ("사진전", "사진")),
    ("05-1", r"토의\(([^)\n]{0,20})\)제시,토의자소개", "주제", ("주제", "논제")),
    ("05-2", r"토의진행\(([^)\n]{0,20})\)안내", "순서", ("순서", "방법", "규칙")),
    ("05-3", r"토의자에게\(([^)\n]{0,20})\)부여", "발언권", ("발언권", "발언기회", "말할기회")),
    ("05-4", r"토의내용\(([^)\n]{0,20})\),청중의토의", "요약", ("요약", "정리")),
    ("05-5", r"청중의토의\(([^)\n]{0,24})\)", "참여 유도", ("참여유도", "참여", "유도")),
    ("05-6", r"토의내용\(([^)\n]{0,20})\)·정리", "종합", ("종합", "요약", "정리")),
    ("06-1", r"상대방의의견을\(([^)\n]{0,20})\)하는태도", "존중", ("존중", "경청", "수용")),
    ("06-2", r"상대방의\(([^)\n]{0,20})\)이/가끝나지않았는데", "발언", ("발언", "말", "이야기")),
]

CRIT = {"기준1": ["01-1"] + [f"02-{i}" for i in range(1, 6)],
        "기준2": [f"03-{i}" for i in range(1, 7)],
        "기준3": [f"04-{i}" for i in range(1, 8)],
        "기준4": [f"05-{i}" for i in range(1, 7)],
        "기준5": [f"06-{i}" for i in range(1, 3)]}
BAND = {"기준1": (5, 3), "기준2": (5, 3), "기준3": (6, 4), "기준4": (5, 3), "기준5": (2, 1)}

_tpl = None


def compact(s):
    return re.sub(r"\s+", "", s)


def template_blanks():
    """빈 학습지에서 각 빈칸이 '비어 있는 상태'로 보이는 값을 모아 둔다."""
    global _tpl
    if _tpl is None:
        lines, _ = load(str(TEMPLATE))
        t = compact(render(lines, False))
        _tpl = {k: (m.group(1).strip() if (m := re.search(p, t)) else None)
                for k, p, _a, _alt in BLANKS}
    return _tpl


def grade(path):
    lines, fmt = load(str(path))
    text = compact(render(lines, False))
    tpl = template_blanks()
    items, miss = {}, []
    for key, pat, ans, alts in BLANKS:
        m = re.search(pat, text)
        if not m:
            items[key] = ["?", "미검출"]
            miss.append(key)
            continue
        v = m.group(1).strip()
        vc = compact(v)
        if not vc or vc == compact(tpl.get(key) or "\x00"):
            items[key] = ["-", ""]            # 빈 학습지와 같음 = 무응답
        elif any(a in vc for a in alts):
            items[key] = ["O", v]
        else:
            items[key] = ["X", v]
    out = {"format": fmt, "items": items, "notes": []}
    if len(miss) >= 5:
        out["notes"].append(f"빈칸 {len(miss)}개 미검출 — 파일 구조 확인 필요")

    for c, keys in CRIT.items():
        vals = [items[k][0] for k in keys]
        hi, mid = BAND[c]
        if all(v == "?" for v in vals):
            out[c] = "확인불가"
        elif all(v in "-?" for v in vals):
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
