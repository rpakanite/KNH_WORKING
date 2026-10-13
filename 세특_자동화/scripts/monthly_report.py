#!/usr/bin/env python3
"""5단계 월말 결산 보고서(PDF 스펙 + Drive용 CSV)를 반별로 만든다.

그 달에 4단계를 진행한 반·차시의 채점 결과만 모아 ① 기준별 등급 분포 합산,
② 반복되는 오류 패턴(4단계에서 이미 관찰된 내용), ③ 교사 전용 상위 10명 순위표를 싣는다.
순위표는 월말 결산 전용이며 4·6단계에 인용하지 않는다(CLAUDE.md 5단계 2-주의).

사용법:  python3 monthly_report.py <채점결과디렉터리> <출력디렉터리>
"""
import collections
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from grade_touui import CRIT as TOUUI_CRIT  # noqa: E402

CRITS = ["기준1", "기준2", "기준3", "기준4", "기준5"]
BANDS = ["상", "중", "하", "확인불가"]
POINT = {"상": 2, "중": 1, "하": 0, "확인불가": 0}
MONTH = "2026년 9월"
TAG = "202609"
CLASSES = ["6반", "7반", "8반", "9반", "10반"]

LESSONS = [
    {"key": "주장하는 글 쓰기", "chasi": "대단원4-2_주장하는글쓰기_2~4차시",
     "date": "2026-09-16",
     "names": {"기준1": "쓰기 과정 이해", "기준2": "근거 자료 타당성 판단",
               "기준3": "구성 단계 이해", "기준4": "주장·근거 파악", "기준5": "표현 의도·효과"}},
    {"key": "토의하기", "chasi": "대단원1-2_토의하기", "date": "2026-10-13",
     "names": {"기준1": "토의 주제·전개 과정 파악", "기준2": "모둠별 주장과 근거 파악",
               "기준3": "의견 교환·조정 과정 파악", "기준4": "사회자의 역할 이해",
               "기준5": "토의 태도 구별"}},
]
NAMES = json.loads(pathlib.Path(".claude/cache/명렬표/명렬표.json").read_text(encoding="utf-8"))


def josa(word, pair):
    """받침 유무에 따라 조사를 고른다 — pair 예: ("은", "는"), ("이라고", "라고")."""
    last = word.strip()[-1] if word.strip() else ""
    has = "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28
    return pair[0] if has else pair[1]


def load_month(src):
    """{반: {차시: {학번: 등급dict}}} 형태로 그 달 채점 결과를 모은다."""
    data = {c: {} for c in CLASSES}
    scored = json.loads((src / "scored.json").read_text(encoding="utf-8"))
    for cls, students in scored.items():
        data[cls]["주장하는 글 쓰기"] = {
            sid.split("_")[0]: {c: g[c] for c in CRITS} for sid, g in students.items()}
    for cls in CLASSES:
        f = src / f"touui_{cls}.json"
        if not f.exists():
            continue
        g = json.loads(f.read_text(encoding="utf-8"))
        data[cls]["토의하기"] = {sid.split("_")[0]: {c: v[c] for c in CRITS}
                               for sid, v in g.items() if "items" in v}
    return data


def wrong_items(src, cls):
    """토의하기에서 그 반이 많이 틀린 칸 — 4단계에서 이미 관찰된 사실만 옮긴다."""
    f = src / f"touui_{cls}.json"
    if not f.exists():
        return []
    g = json.loads(f.read_text(encoding="utf-8"))
    cnt, pick = collections.Counter(), collections.defaultdict(collections.Counter)
    for v in g.values():
        for k, val in v.get("items", {}).items():
            if val[0] == "X":
                cnt[k] += 1
                pick[k][val[1].strip()] += 1
    n = len(g)
    return [(k, c, pick[k].most_common(1)[0][0]) for k, c in cnt.most_common(3)
            if c >= max(3, n // 4)]


def ranking(cls, lessons):
    """그 달 성취도가 우수하고 성실히 참여한 학생 — 교사 전용 참고 순위표."""
    taught = [k for k in lessons if lessons[k]]
    rows = []
    for sid in sorted({s for k in taught for s in lessons[k]}):
        grades = {k: lessons[k].get(sid) for k in taught}
        if any(g is None for g in grades.values()):
            continue                                  # 제출 누락 — 순위 대상 제외
        flat = [g[c] for g in grades.values() for c in CRITS]
        if "확인불가" in flat:
            continue                                  # 확인불가 있음 — 순위 대상 제외
        rows.append((sid, flat.count("상"), flat.count("중"), len(flat), len(taught)))
    rows.sort(key=lambda r: (-r[1], -r[2], r[0]))

    out, rank, prev = [], 0, None
    for i, (sid, hi, mid, total, nles) in enumerate(rows, 1):
        if (hi, mid) != prev:
            rank, prev = i, (hi, mid)
        if rank > 10:
            break
        if hi == total:
            why = f"{nles}개 차시 전 기준 '상', 전 차시 제출"
        else:
            why = f"{nles}개 차시 {total}개 기준 중 상 {hi}·중 {mid}, 전 차시 제출"
        out.append([str(rank), sid, NAMES[cls].get(sid, ""), why])
    return out, len(rows)


def build(cls, lessons, src, out_dir):
    taught = [k for k in lessons if lessons[k]]
    roll = {c: collections.Counter() for c in CRITS}
    for k in taught:
        for g in lessons[k].values():
            for c in CRITS:
                roll[c][g[c]] += 1
    per = [[k, str(len(lessons[k])),
            str(sum(1 for g in lessons[k].values() for c in CRITS if g[c] == "상")),
            str(sum(1 for g in lessons[k].values() for c in CRITS if g[c] == "중")),
            str(sum(1 for g in lessons[k].values() for c in CRITS if g[c] == "하")),
            str(sum(1 for g in lessons[k].values() for c in CRITS if g[c] == "확인불가"))]
           for k in taught]
    rank_rows, pool = ranking(cls, lessons)

    qual = []
    for k in taught:
        n = len(lessons[k])
        low = [c for c in CRITS if sum(1 for g in lessons[k].values() if g[c] == "하") >= max(2, n // 5)]
        if low:
            qual.append(f"<b>{k}</b>: {', '.join(low)}에서 '하'가 상대적으로 많았다.")
        hi = [c for c in CRITS if sum(1 for g in lessons[k].values() if g[c] == "상") >= n * 0.8]
        if hi:
            qual.append(f"<b>{k}</b>: {', '.join(hi)}{josa(hi[-1], ('은', '는'))} "
                        f"대부분의 학생이 '상'에 도달했다.")
    if len(taught) < len(LESSONS):
        missing = [l["key"] for l in LESSONS if l["key"] not in taught]
        qual.append(f"<b>{cls}</b>{josa(cls, ('은', '는'))} {', '.join(missing)} "
                    f"제출물이 한 건도 없어"
                    f"(교사 지시로 제외) 이 달 대상 차시가 {len(taught)}개다.")
    for key, cnt, ans in wrong_items(src, cls):
        qual.append(f"<b>토의하기</b>: {key} 칸을 {cnt}명이 틀렸고 대부분 "
                    f"'{ans}'{josa(ans, ('이라고', '라고'))} 적었다. "
                    f"반복되는 오류 패턴으로, 다음 차시 도입에서 짚어 줄 지점이다.")

    spec = {
        "title": f"{cls} {MONTH} 월말 결산 보고서",
        "subtitle": f"대상 차시 {len(taught)}개 · 작성일 2026-10-13 · 교사 참고용 내부 자료",
        "meta": [["대상 차시", " / ".join(f"{k}({next(l['chasi'] for l in LESSONS if l['key'] == k)})"
                                        for k in taught)],
                 ["집계 범위", f"{MONTH}에 4단계를 진행한 반·차시의 채점 결과만 집계했다."],
                 ["근거 자료", ".claude/cache/results/ 의 학생별 채점 결과(제출자 기준)"]],
        "sections": [
            {"heading": "1. 차시별 처리 현황과 등급 합계", "blocks": [
                {"type": "table", "widths": [2.2, 1.0, 0.9, 0.9, 0.9, 1.1],
                 "header": ["차시", "제출 인원", "상", "중", "하", "확인불가"],
                 "rows": per},
                {"type": "para", "text": "상·중·하 칸의 숫자는 <b>학생 수가 아니라 기준 판정 건수</b>"
                                         "(학생 수 × 기준 5개)이다."}]},
            {"heading": "2. 기준별 등급 분포 합산", "blocks": [
                {"type": "table", "widths": [1.6, 1.2, 1.2, 1.2, 1.4],
                 "header": ["분석 기준", "상", "중", "하", "확인불가"],
                 "rows": [[c] + [str(roll[c][b]) for b in BANDS] for c in CRITS]},
                {"type": "para", "text": "차시마다 기준의 뜻이 다르므로(차시별 보고서 참조) "
                                         "같은 번호끼리의 합계는 <b>그 달 전체의 도달 분포</b>로만 읽는다."}]},
            {"heading": "3. 정성적 분석", "blocks": [
                {"type": "bullets", "items": qual or
                    ["이 달 자료에서 반 전체에 공통되는 뚜렷한 강·약점은 확인되지 않았다."]}]},
        ],
        "footer": "본 보고서는 교사의 검토·수정을 전제로 한 초안이며, 4·6단계 산출물에 인용하지 않습니다.",
    }

    rank_blocks = [{"type": "para",
                    "text": "<b>교사 전용 참고 자료.</b> 아래 순위는 월말 결산에서만 쓰며, "
                            "차시별 분석 보고서나 세특 문구에는 인용하지 않는다"
                            "(나이스 작성 지침상 서열 표현 금지)."}]
    if rank_rows:
        rank_blocks.append({"type": "table", "widths": [0.7, 1.0, 1.1, 4.2],
                            "header": ["순위", "학번", "이름", "선정 근거"], "rows": rank_rows})
        rank_blocks.append({"type": "para",
                            "text": f"대상자 {pool}명(전 차시 제출 + 확인불가 없음) 가운데 "
                                    f"상위 {len(rank_rows)}명. 동률은 공동 순위로 적었다."})
    else:
        rank_blocks.append({"type": "para", "text": "조건(전 차시 제출·확인불가 없음)을 "
                                                    "만족하는 학생이 없어 순위를 매기지 않았다."})
    spec["sections"].append({"heading": "4. 우수·성실 참여 학생 (상위 10명)",
                             "blocks": rank_blocks})

    out_dir = pathlib.Path(out_dir)
    (out_dir / f"spec_monthly_{cls}.json").write_text(json.dumps(spec, ensure_ascii=False),
                                                      encoding="utf-8")
    csv_path = out_dir / f"{cls}_{TAG}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([f"{cls} {MONTH} 월말 결산 보고서"])
        w.writerow(["대상 차시", " / ".join(taught), "작성일", "2026-10-13"])
        w.writerow([])
        w.writerow(["[차시별 처리 현황과 등급 합계]"])
        w.writerow(["차시", "제출 인원", "상", "중", "하", "확인불가"])
        for r in per:
            w.writerow(r)
        w.writerow([])
        w.writerow(["[기준별 등급 분포 합산]"])
        w.writerow(["분석 기준"] + BANDS)
        for c in CRITS:
            w.writerow([c] + [roll[c][b] for b in BANDS])
        w.writerow([])
        w.writerow(["[정성적 분석]"])
        for q in qual:
            w.writerow([q.replace("<b>", "").replace("</b>", "")])
        w.writerow([])
        w.writerow(["[우수·성실 참여 학생 상위 10명 — 교사 전용, 4·6단계 인용 금지]"])
        w.writerow(["순위", "학번", "이름", "선정 근거"])
        for r in rank_rows:
            w.writerow(r)
    return csv_path


if __name__ == "__main__":
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    data = load_month(src)
    for cls in CLASSES:
        p = build(cls, data[cls], src, dst)
        print(f"{cls}: {p.name} ({', '.join(k for k in data[cls] if data[cls][k])})")
