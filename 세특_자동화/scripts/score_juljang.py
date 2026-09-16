#!/usr/bin/env python3
"""1차 채점 결과를 승인된 분석기준(v3)의 기준 1~5 등급으로 환산한다.

서술형 02·06은 기계가 정오를 가릴 수 없으므로 핵심 개념이 들어 있는지로 1차 판정한다.
(02: 관련성·신뢰성·객관성 세 기준 / 06: 흥미 유발 또는 문제 상황 제시의 취지)
판정 결과는 원문과 함께 남겨 교사가 대조할 수 있게 한다.
"""
import json
import pathlib
import sys

CLASSES = ["6반", "7반", "8반", "9반", "10반"]
Q02_KEYS = {"관련": ("관련",), "신뢰": ("신뢰",), "객관": ("객관", "개관")}
Q06_KEYS = ("흥미", "관심", "문제", "단점", "부정적", "생각해", "생각하")


def q02_score(t):
    return sum(any(k in t for k in ks) for ks in Q02_KEYS.values())


def q06_ok(t):
    return any(k in t for k in Q06_KEYS)


def tally(items, keys):
    v = [items[k][0] for k in keys if k in items]
    return v.count("O"), v.count("?"), len(v)


def grade_student(rec):
    it, out = rec["items"], {}
    e02, e06 = rec["essay"]["02"], rec["essay"]["06"]
    s02, ok06 = q02_score(e02), q06_ok(e06)

    def band(o, q, n, hi, mid):
        if q == n:
            return "확인불가"
        return "상" if o >= hi else ("중" if o >= mid else "하")

    o, q, n = tally(it, ["01-1", "01-2", "04-1"])
    out["기준1"] = band(o, q, n, 3, 2)

    ox_o, ox_q, _ = tally(it, [f"03OX-{l}" for l in ["잡지", "면담", "텔레비전", "신문", "책", "신문2"]])
    rz_keys = [f"03까닭-관련{i}" for i in range(1, 7)] + ["03까닭-객관성", "03까닭-신뢰1", "03까닭-신뢰2"]
    rz_o, _, rz_n = tally(it, rz_keys)
    if ox_q == 6 and not e02:
        out["기준2"] = "확인불가"
    elif s02 == 3 and ox_o == 6 and rz_o >= rz_n - 2:
        out["기준2"] = "상"
    elif s02 >= 2 and ox_o >= 4:
        out["기준2"] = "중"
    else:
        out["기준2"] = "하"

    o, q, n = tally(it, ["04-2", "04-3", "04-4", "05-1", "05-2", "05-3", "05-4"])
    out["기준3"] = band(o, q, n, 6, 4)

    o, q, n = tally(it, ["07-1", "07-2", "07-3"])
    out["기준4"] = band(o, q, n, 3, 2)

    o8, q8, _ = tally(it, ["08-1", "08-2"])
    if q8 == 2 and not e06:
        out["기준5"] = "확인불가"
    elif ok06 and o8 == 2:
        out["기준5"] = "상"
    elif ok06 or o8 >= 1:
        out["기준5"] = "중"
    else:
        out["기준5"] = "하"

    out["_근거"] = {"02": e02, "02개념수": s02, "06": e06, "06도달": ok06,
                    "03OX정답": ox_o, "03까닭정답": f"{rz_o}/{rz_n}",
                    "08": f"{it.get('08-1',['?'])[0]}{it.get('08-2',['?'])[0]}"}
    out["_비고"] = rec.get("notes", [])
    out["_형식"] = rec["format"]
    return out


if __name__ == "__main__":
    sp = pathlib.Path(sys.argv[1])
    res = {}
    for c in CLASSES:
        d = json.loads((sp / f"grade_{c}.json").read_text(encoding="utf-8"))
        res[c] = {k: grade_student(v) for k, v in sorted(d.items())}
    (sp / "scored.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in CLASSES:
        dist = {}
        for v in res[c].values():
            for i in range(1, 6):
                dist.setdefault(f"기준{i}", {}).setdefault(v[f"기준{i}"], 0)
                dist[f"기준{i}"][v[f"기준{i}"]] += 1
        print(f"\n[{c}] {len(res[c])}명")
        for k, d2 in dist.items():
            print(f"  {k}: " + " ".join(f"{g}={d2.get(g,0)}" for g in ["상", "중", "하", "확인불가"]))
