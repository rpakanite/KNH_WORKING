#!/usr/bin/env python3
"""5단계 월말 결산 보고서(PDF 스펙 + Drive용 CSV)를 반별로 만든다.

그 달의 반·차시 채점 결과만 모아 ① 기준별 등급 분포 합산,
② 반복되는 오류 패턴(4단계에서 이미 관찰된 내용), ③ 교사 전용 상위 10명 순위표를 싣는다.
순위표는 월말 결산 전용이며 4·6단계에 인용하지 않는다(CLAUDE.md 5단계 2-주의).

월을 나누는 기준은 채점일이 아니라 수업·제출 시점이다(9월 결산 선례: 9월에 제출된
「토의하기」를 10/13에 채점해 9월 결산에 넣음).

사용법:  python3 monthly_report.py <연월 YYYYMM> <채점결과디렉터리> <출력디렉터리>
         채점결과디렉터리에 차시별 채점기 출력({prefix}_{반}.json)이 있어야 한다.
"""
import collections
import csv
import json
import pathlib
import sys

CRITS = ["기준1", "기준2", "기준3", "기준4", "기준5"]
BANDS = ["상", "중", "하", "확인불가"]
CLASSES = ["6반", "7반", "8반", "9반", "10반"]

# 달마다 바뀌는 것(대상 차시, 작성일, 반별 제외 사유)은 여기에만 둔다.
MONTHS = {
    "202609": {
        "month": "2026년 9월", "written": "2026-10-13",
        "excluded": {"7반": "교사 지시로 제외"},
        "lessons": [
            {"key": "주장하는 글 쓰기", "chasi": "대단원4-2_주장하는글쓰기_2~4차시",
             "scored": "scored.json"},
            {"key": "토의하기", "chasi": "대단원1-2_토의하기", "prefix": "touui"},
        ]},
    "202610": {
        "month": "2026년 10월", "written": "2026-11-10",
        "excluded": {},
        "lessons": [
            {"key": "어휘의 양상", "chasi": "대단원3-2_어휘의양상", "prefix": "eohwi"},
            {"key": "단어의 짜임", "chasi": "대단원3-1_단어의짜임", "prefix": "danuh"},
        ]},
}
NAMES = json.loads(pathlib.Path(".claude/cache/명렬표/명렬표.json").read_text(encoding="utf-8"))


def josa(word, pair):
    """받침 유무에 따라 조사를 고른다 — pair 예: ("은", "는"), ("이라고", "라고")."""
    last = word.strip()[-1] if word.strip() else ""
    if last.isdigit():                          # 숫자는 읽는 소리로: 영·일·삼·육·칠·팔은 받침 있음
        return pair[0] if last in "013678" else pair[1]
    has = "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28
    return pair[0] if has else pair[1]


def load_month(cfg, src):
    """{반: {차시: {학번: 등급dict}}} 형태로 그 달 채점 결과를 모은다."""
    data = {c: {} for c in CLASSES}
    for les in cfg["lessons"]:
        if "scored" in les:                       # 9월 「주장하는 글 쓰기」: 반별로 묶인 한 파일
            scored = json.loads((src / les["scored"]).read_text(encoding="utf-8"))
            for cls, students in scored.items():
                data[cls][les["key"]] = {sid.split("_")[0]: {c: g[c] for c in CRITS}
                                         for sid, g in students.items()}
            continue
        for cls in CLASSES:
            f = src / f"{les['prefix']}_{cls}.json"
            if not f.exists():
                continue
            g = json.loads(f.read_text(encoding="utf-8"))
            data[cls][les["key"]] = {sid.split("_")[0]: {c: v[c] for c in CRITS}
                                     for sid, v in g.items() if "items" in v}
    return data


def wrong_items(cfg, src, cls):
    """그 반이 많이 틀린 칸 — 4단계에서 이미 관찰된 사실만 옮긴다. [(차시, 칸, 인원, 흔한 답)]"""
    out = []
    for les in cfg["lessons"]:
        f = src / f"{les.get('prefix', '')}_{cls}.json"
        if "prefix" not in les or not f.exists():
            continue
        g = json.loads(f.read_text(encoding="utf-8"))
        cnt, pick = collections.Counter(), collections.defaultdict(collections.Counter)
        for v in g.values():
            for k, val in v.get("items", {}).items():
                if val[0] == "X":
                    cnt[k] += 1
                    pick[k][val[1].strip()] += 1
        n = len(g)
        for k, c in cnt.most_common(3):
            if c >= max(3, n // 4):
                ans, m = pick[k].most_common(1)[0]
                out.append((les["key"], k, c, ans if m >= 2 else None))
    return out


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


def build(cfg, tag, cls, lessons, src, out_dir):
    month, written = cfg["month"], cfg["written"]
    taught = [k for k in lessons if lessons[k]]
    enrolled = sum(1 for v in NAMES[cls].values() if v)
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
        if n < enrolled / 2:
            qual.append(f"<b>{k}</b>: 재적 {enrolled}명 중 {n}명만 제출해, 아래 분포는 "
                        f"제출한 학생의 결과일 뿐 반 전체의 경향으로 읽기 어렵다.")
        low = [c for c in CRITS if sum(1 for g in lessons[k].values() if g[c] == "하") >= max(2, n // 5)]
        if low:
            qual.append(f"<b>{k}</b>: {', '.join(low)}에서 '하'가 상대적으로 많았다.")
        hi = [c for c in CRITS if sum(1 for g in lessons[k].values() if g[c] == "상") >= n * 0.8]
        if hi and n >= 3:
            qual.append(f"<b>{k}</b>: {', '.join(hi)}{josa(hi[-1], ('은', '는'))} "
                        f"제출한 학생 대부분이 '상'에 도달했다.")
    missing = [les["key"] for les in cfg["lessons"] if les["key"] not in taught]
    if missing:
        why = cfg["excluded"].get(cls)
        qual.append(f"<b>{cls}</b>{josa(cls, ('은', '는'))} {', '.join(missing)} "
                    f"제출물이 한 건도 없어" + (f"({why})" if why else "")
                    + f" 이 달 대상 차시가 {len(taught)}개다.")
    for les, key, cnt, ans in wrong_items(cfg, src, cls):
        said = (f" 대부분 '{ans}'{josa(ans, ('이라고', '라고'))} 적었다." if ans
                else " 답은 제각각이었다.")
        qual.append(f"<b>{les}</b>: {key} 칸을 {cnt}명이 틀렸고{said} "
                    f"반복되는 오류 패턴으로, 다음 차시 도입에서 짚어 줄 지점이다.")

    chasi = {les["key"]: les["chasi"] for les in cfg["lessons"]}
    spec = {
        "title": f"{cls} {month} 월말 결산 보고서",
        "subtitle": f"대상 차시 {len(taught)}개 · 작성일 {written} · 교사 참고용 내부 자료",
        "meta": [["대상 차시", " / ".join(f"{k}({chasi[k]})" for k in taught) or "없음"],
                 ["집계 범위", f"{month}에 수업·제출한 반·차시의 채점 결과만 집계했다."],
                 ["근거 자료", ".claude/cache/results/ 의 학생별 채점 결과(제출자 기준)"]],
        "sections": [
            {"heading": "1. 차시별 처리 현황과 등급 합계", "blocks": [
                {"type": "table", "widths": [2.2, 1.0, 0.9, 0.9, 0.9, 1.1],
                 "header": ["차시", "제출 인원", "상", "중", "하", "확인불가"],
                 "rows": per},
                {"type": "para", "text": f"재적 {enrolled}명. 상·중·하 칸의 숫자는 "
                                         "<b>학생 수가 아니라 기준 판정 건수</b>(학생 수 × 기준 5개)이다."}]},
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
    csv_path = out_dir / f"{cls}_{tag}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([f"{cls} {month} 월말 결산 보고서"])
        w.writerow(["대상 차시", " / ".join(taught), "작성일", written, "재적", f"{enrolled}명"])
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
    tag, src, dst = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    cfg = MONTHS[tag]
    data = load_month(cfg, src)
    for cls in CLASSES:
        p = build(cfg, tag, cls, data[cls], src, dst)
        print(f"{cls}: {p.name} ({', '.join(k for k in data[cls] if data[cls][k])})")
