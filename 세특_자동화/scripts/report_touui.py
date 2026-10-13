#!/usr/bin/env python3
"""4단계 「토의하기」 반별 분석결과 보고서(PDF 스펙 + Drive용 CSV)를 만든다.

양식은 9반 1차시 보고서를 표준 템플릿으로 삼아 모든 반·차시에 동일하게 적용한다:
제목/개요 → 반 전체 등급 분포 요약 → 학생별 채점 결과 → 유의사항.

사용법:  python3 report_touui.py <채점결과디렉터리> <출력디렉터리>
         (채점결과디렉터리에 grade_touui.py가 만든 touui_{반}.json 들이 있어야 한다)
"""
import collections
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from grade_touui import BAND, CRIT  # noqa: E402

CRIT_NAME = {"기준1": "토의 주제·전개 과정 파악", "기준2": "모둠별 주장과 근거 파악",
             "기준3": "의견 교환·조정 과정 파악", "기준4": "사회자의 역할 이해",
             "기준5": "토의 태도 구별"}
CRITS = ["기준1", "기준2", "기준3", "기준4", "기준5"]
BANDS = ["상", "중", "하", "확인불가"]
TITLE = "「토의하기」 분석결과 보고서"
CHASI = "대단원1-2_토의하기"
DATE = "2026-10-13"
NAMES = json.loads(pathlib.Path(".claude/cache/명렬표/명렬표.json").read_text(encoding="utf-8"))


def basis(g):
    """기준별 정답 칸 수와 무응답 칸 수를 한 줄로 줄여 적는다."""
    per = []
    for c in CRITS:
        vals = [g["items"][k][0] for k in CRIT[c]]
        per.append(f"{vals.count('O')}/{len(vals)}")
    blank = sum(1 for v in g["items"].values() if v[0] == "-")
    wrong = [f"{k} '{v[1].strip()}'" for k, v in g["items"].items() if v[0] == "X"]
    s = "기준별 정답 " + "·".join(per) + f" · 무응답 {blank}칸"
    if wrong:
        s += " · 오답 " + ", ".join(wrong[:4]) + (" 외" if len(wrong) > 4 else "")
    return s


def build(cls, graded, out_dir):
    rows = sorted(graded.items())
    names = NAMES[cls]
    dist = {c: {b: sum(1 for _, v in rows if v[c] == b) for b in BANDS} for c in CRITS}

    # 반 안에서 많이 틀린 칸 — 유의사항에 쓸 사실 근거
    wrong = collections.Counter()
    picks = collections.defaultdict(collections.Counter)
    for _, g in rows:
        for k, v in g["items"].items():
            if v[0] == "X":
                wrong[k] += 1
                picks[k][v[1].strip()] += 1

    spec = {
        "title": f"{cls} {TITLE}",
        "subtitle": f"대단원 1 · 소단원 2 · 채점일 {DATE} · 적용 분석기준 v3({DATE} 승인)",
        "meta": [
            ["차시 ID", CHASI],
            ["적용 분석기준", f"공통_{CHASI}_{DATE.replace('-', '')}_v3 (승인 완료본)"],
            ["처리 인원", f"{len(rows)}명 (제출자 전원). 미제출자는 이 표에 포함하지 않는다."],
            ["채점 방법", "전 문항이 빈칸 채우기(27칸)이므로 빈 학습지·답지와 칸 단위로 대조해 "
                          "채점했고, 뜻이 같은 다른 표현은 승인된 허용 표현으로 인정했다."],
        ],
        "sections": [
            {"heading": "1. 반 전체 등급 분포 요약", "blocks": [
                {"type": "table", "widths": [2.9, 0.9, 0.9, 0.9, 1.2],
                 "header": ["분석 기준", "상", "중", "하", "확인불가"],
                 "rows": [[f"<b>{c}</b> {CRIT_NAME[c]}"] + [str(dist[c][b]) for b in BANDS]
                          for c in CRITS]},
                {"type": "para", "text": "등급 기준(승인본): 기준1·2·4는 정답 5칸 이상 상 / 3~4칸 중, "
                                         "기준3은 6칸 이상 상 / 4~5칸 중, 기준5는 2칸 상 / 1칸 중. "
                                         "등급은 <b>개별 학생의 목표 도달 여부</b>만을 뜻하며, "
                                         "학생 간 비교·서열을 나타내지 않는다."}]},
            {"heading": "2. 학생별 채점 결과", "blocks": [
                {"type": "table", "widths": [0.85, 0.95, 0.5, 0.5, 0.5, 0.5, 0.5, 3.6],
                 "header": ["학번", "이름"] + CRITS + ["기준별 근거 요약"],
                 "rows": [[sid.split("_")[0], names.get(sid.split("_")[0], sid.split("_")[-1])]
                          + [g[c] for c in CRITS] + [basis(g)] for sid, g in rows]}]},
        ],
        "footer": "본 보고서는 교사의 검토·수정을 전제로 한 초안입니다. 최종 판단은 교사가 확정합니다.",
    }

    def who(sid):
        return f"{sid.split('_')[0]} {names.get(sid.split('_')[0], '')}"

    notes = []
    CHECK = ("미검출", "파일 구조")
    flagged = [(sid, [n for n in g["notes"] if any(c in n for c in CHECK)]) for sid, g in rows]
    flagged = [(sid, ns) for sid, ns in flagged if ns]
    if flagged:
        notes.append("<b>교사 확인이 필요한 제출물</b>: " + " / ".join(
            f"{who(sid)}({'; '.join(ns)})" for sid, ns in flagged))
    info = [(sid, [n for n in g["notes"] if not any(c in n for c in CHECK)]) for sid, g in rows]
    info = [(sid, ns) for sid, ns in info if ns]
    if info:
        notes.append("<b>읽을 때 보정한 제출물</b>(판정은 정상 진행): " + " / ".join(
            f"{who(sid)} — {'; '.join(ns)}" for sid, ns in info))
    top = [k for k, n in wrong.most_common(3) if n >= max(3, len(rows) // 4)]
    if top:
        notes.append("<b>이 반에서 많이 틀린 칸</b>: " + " / ".join(
            f"{k} {wrong[k]}명 (주로 '{picks[k].most_common(1)[0][0]}')" for k in top)
            + ". 다음 차시 도입에서 짚어 줄 지점이다.")
    blanks = [(sid, sum(1 for v in g["items"].values() if v[0] == "-")) for sid, g in rows]
    many = [(sid, n) for sid, n in blanks if n >= 5]
    if many:
        notes.append("<b>상당 부분을 비워 제출한 학생</b>: " + " / ".join(
            f"{who(sid)} {n}칸 무응답" for sid, n in many)
            + ". 무응답은 미도달로 처리했으며, 판독 불가('확인불가')와 구분한다.")
    notes += [
        "<b>'확인불가'는 파일을 읽을 수 없어 판정하지 못한 경우</b>로, 빈칸을 그대로 둔 무응답과 "
        "구분해 표기했다. 이번 차시에는 판독 실패로 인한 확인불가가 없다.",
        "맞춤법이 한두 글자 어긋난 답('교횐', '제제')과, 뜻이 비슷하지만 승인된 허용 표현에 "
        "없는 말('제재', '사회자' 등)은 모두 오답으로 처리했다. 위 '많이 틀린 칸'에 그 답이 "
        "함께 적혀 있으니, 허용 범위를 넓힐지는 교사가 확정한다.",
        "학생 간 비교·서열화 표현은 쓰지 않았으며, 모든 판정은 제출물에서 확인되는 사실에만 근거한다.",
    ]
    spec["sections"].append({"heading": "3. 유의사항",
                             "blocks": [{"type": "bullets", "items": notes}]})

    out_dir = pathlib.Path(out_dir)
    (out_dir / f"spec_touui_{cls}.json").write_text(json.dumps(spec, ensure_ascii=False),
                                                    encoding="utf-8")

    csv_path = out_dir / f"{cls}_{CHASI}_{DATE.replace('-', '')}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([f"{cls} {TITLE}"])
        w.writerow(["차시 ID", CHASI, "채점일", DATE, "처리 인원", f"{len(rows)}명"])
        w.writerow([])
        w.writerow(["[반 전체 등급 분포]"])
        w.writerow(["분석 기준"] + BANDS)
        for c in CRITS:
            w.writerow([f"{c} {CRIT_NAME[c]}"] + [dist[c][b] for b in BANDS])
        w.writerow([])
        w.writerow(["[학생별 채점 결과]"])
        w.writerow(["학번", "이름"] + CRITS + ["기준별 근거 요약"])
        for sid, g in rows:
            n = sid.split("_")[0]
            w.writerow([n, names.get(n, sid.split("_")[-1])] + [g[c] for c in CRITS] + [basis(g)])
        w.writerow([])
        w.writerow(["[유의사항]"])
        for n in notes:
            w.writerow([n.replace("<b>", "").replace("</b>", "")])
    return spec, csv_path


def save_results(cls, graded):
    """학생별 채점 결과를 .claude/cache/results/ 에 남긴다(5·6단계 근거)."""
    out = pathlib.Path(".claude/cache/results")
    out.mkdir(parents=True, exist_ok=True)
    names = NAMES[cls]
    for sid, g in sorted(graded.items()):
        num = sid.split("_")[0]
        lines = [f"# {cls} {num} {names.get(num, '')} — {CHASI}", "",
                 f"- 채점일: {DATE} / 파일형식: {g['format']} / 적용 분석기준: 승인본 v3",
                 f"- 기준별 등급: " + ", ".join(f"{c} {g[c]}" for c in CRITS),
                 f"- 정답 {g['_정답수']}/27칸", ""]
        if g["notes"]:
            lines += ["## 비고"] + [f"- {n}" for n in g["notes"]] + [""]
        lines.append("## 칸별 판정 (O 정답 / X 오답 / - 무응답 / ? 미검출)")
        lines += [f"- {k}: {v[0]} {v[1]}".rstrip() for k, v in g["items"].items()]
        (out / f"{cls}_{CHASI}_{num}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    for cls in ["6반", "8반", "9반", "10반"]:
        graded = json.loads((src / f"touui_{cls}.json").read_text(encoding="utf-8"))
        graded = {k: v for k, v in graded.items() if "items" in v}
        _spec, csv_path = build(cls, graded, dst)
        save_results(cls, graded)
        print(f"{cls}: {len(graded)}명 → {csv_path.name}")
