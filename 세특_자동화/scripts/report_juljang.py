#!/usr/bin/env python3
"""4단계 반·차시별 분석결과 보고서(PDF 스펙 + Drive용 CSV)를 만든다.

양식은 9반 1차시 보고서를 표준 템플릿으로 삼아 모든 반·차시에 동일하게 적용한다:
제목/개요 → 반 전체 등급 분포 요약 → 학생별 채점 결과 → 유의사항.
"""
import csv
import json
import pathlib
import sys

CRIT = ["기준1", "기준2", "기준3", "기준4", "기준5"]
CRIT_NAME = {"기준1": "쓰기 과정 이해", "기준2": "근거 자료 타당성 판단",
             "기준3": "구성 단계 이해", "기준4": "주장·근거 파악", "기준5": "표현 의도·효과"}
BANDS = ["상", "중", "하", "확인불가"]
TITLE = "「주장하는 글 쓰기」 분석결과 보고서"
CHASI = "대단원4-2_주장하는글쓰기_2~4차시"


def basis(g):
    b = g["_근거"]
    parts = [f"03 O/X {b['03OX정답']}/6", f"까닭 {b['03까닭정답']}",
             f"02 개념 {b['02개념수']}/3", f"08 {b['08']}"]
    parts.append("06 도달" if b["06도달"] else ("06 미도달" if b["06"] else "06 무응답"))
    return " · ".join(parts)


def build(cls, scored, names, out_dir):
    rows = sorted(scored.items())
    dist = {c: {g: sum(1 for _, v in rows if v[c] == g) for g in BANDS} for c in CRIT}

    spec = {
        "title": f"{cls} {TITLE}",
        "subtitle": f"대단원 4 · 소단원 2 (2~4차시) · 채점일 2026-09-16 · 적용 분석기준 v3(2026-09-16 승인)",
        "meta": [
            ["차시 ID", CHASI],
            ["적용 분석기준", "6~10반_대단원4-2_주장하는글쓰기_2~4차시_20260916_v3 (승인 완료본)"],
            ["처리 인원", f"{len(rows)}명 (제출자 전원). 미제출자는 이 표에 포함하지 않는다."],
            ["채점 방법", "선택형(03·08)은 남은 보기·색이 바뀐 보기·덧붙인 표시로 판정, "
                          "서술형(02·06)은 제출 원문을 읽고 판정"],
        ],
        "sections": [
            {"heading": "1. 반 전체 등급 분포 요약", "blocks": [
                {"type": "table", "widths": [2.6, 1, 1, 1, 1.3],
                 "header": ["분석 기준", "상", "중", "하", "확인불가"],
                 "rows": [[f"<b>{c}</b> {CRIT_NAME[c]}"] + [str(dist[c][g]) for g in BANDS] for c in CRIT]},
                {"type": "para", "text": "등급은 <b>개별 학생의 목표 도달 여부</b>만을 뜻하며, "
                                         "학생 간 비교·서열을 나타내지 않는다."}]},
            {"heading": "2. 학생별 채점 결과", "blocks": [
                {"type": "table", "widths": [0.9, 1.0, 0.55, 0.55, 0.55, 0.55, 0.55, 3.6],
                 "header": ["학번", "이름", "기준1", "기준2", "기준3", "기준4", "기준5", "기준별 근거 요약"],
                 "rows": [[sid.split("_")[0], names.get(sid.split("_")[0], sid.split("_")[-1])]
                          + [g[c] for c in CRIT] + [basis(g)] for sid, g in rows]}]},
        ],
        "footer": "본 보고서는 교사의 검토·수정을 전제로 한 초안입니다. 최종 판단은 교사가 확정합니다.",
    }

    notes = ["<b>서술형 02·06번은 제출 원문을 읽고 판정</b>했으며, 판정 근거가 된 학생 원문은 "
             "로컬 채점 기록에 남아 있다. 표현이 애매한 답안은 교사 확인을 권한다.",
             "<b>02번 무응답이 많다.</b> 이 문항을 비운 학생은 승인된 기준에 따라 기준 2가 '하'로 "
             "내려간다. 학습지 수정 건의 4번(02번을 항목별 서술 형식으로 변경)과 연결되는 지점이다.",
             "학생 간 비교·서열화 표현은 쓰지 않았으며, 모든 판정은 제출물에서 확인되는 사실에만 근거한다."]
    flagged = [(sid, g) for sid, g in rows if g["_비고"]]
    if flagged:
        notes.insert(0, "<b>교사 확인이 필요한 제출물</b>: " + " / ".join(
            f"{sid.split('_')[0]} {names.get(sid.split('_')[0], '')}({'; '.join(g['_비고'])})"
            for sid, g in flagged))
    if cls == "10반":
        notes.insert(0, "<b>학번-이름 대응 주의.</b> Drive 학급명렬표의 10반은 11009번부터 학번과 이름이 "
                        "한 칸씩 밀려 있어, 제출물에 학생이 직접 적은 학번·이름을 따랐다(6~9반은 명렬표와 "
                        "일치). 명렬표 쪽 확인이 필요하다.")
    spec["sections"].append({"heading": "3. 유의사항",
                             "blocks": [{"type": "bullets", "items": notes}]})

    out_dir = pathlib.Path(out_dir)
    (out_dir / f"spec_{cls}.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

    with open(out_dir / f"{cls}_{CHASI}_20260916.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([f"{cls} {TITLE}"])
        w.writerow(["차시 ID", CHASI, "채점일", "2026-09-16", "처리 인원", f"{len(rows)}명"])
        w.writerow([])
        w.writerow(["[반 전체 등급 분포]"]); w.writerow(["분석 기준"] + BANDS)
        for c in CRIT:
            w.writerow([f"{c} {CRIT_NAME[c]}"] + [dist[c][g] for g in BANDS])
        w.writerow([])
        w.writerow(["[학생별 채점 결과]"])
        w.writerow(["학번", "이름"] + CRIT + ["기준별 근거 요약"])
        for sid, g in rows:
            n = sid.split("_")[0]
            w.writerow([n, names.get(n, sid.split("_")[-1])] + [g[c] for c in CRIT] + [basis(g)])
    return spec


if __name__ == "__main__":
    sp = pathlib.Path(sys.argv[1])
    scored = json.loads((sp / "scored.json").read_text(encoding="utf-8"))
    names = json.loads((sp / "roster_official.json").read_text(encoding="utf-8"))
    for cls in scored:
        build(cls, scored[cls], names[cls], sp)
        print(f"{cls}: spec + csv 생성 ({len(scored[cls])}명)")
