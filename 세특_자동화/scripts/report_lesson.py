#!/usr/bin/env python3
"""4단계 반·차시별 분석결과 보고서(PDF 스펙 + Drive용 CSV)를 만드는 공용 스크립트.

양식은 9반 1차시 보고서를 표준 템플릿으로 삼아 모든 반·차시에 동일하게 적용한다:
제목/개요 → 반 전체 등급 분포 요약 → 학생별 채점 결과 → 유의사항.
차시마다 바뀌는 것(채점기·기준 이름·차시 특유의 유의사항)은 LESSONS 설정에만 둔다.

사용법:  python3 report_lesson.py <차시키> <채점결과디렉터리> <출력디렉터리>
         채점결과디렉터리에 {prefix}_{반}.json (채점기 출력)이 있어야 한다.
"""
import collections
import csv
import importlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

CRITS = ["기준1", "기준2", "기준3", "기준4", "기준5"]
BANDS = ["상", "중", "하", "확인불가"]
NAMES = json.loads(pathlib.Path(".claude/cache/명렬표/명렬표.json").read_text(encoding="utf-8"))

LESSONS = {
    "eohwi": {
        "grader": "grade_eohwi", "prefix": "eohwi",
        "title": "「어휘의 양상」 분석결과 보고서",
        "chasi": "대단원3-2_어휘의양상", "unit": "대단원 3 · 소단원 2",
        "date": "2026-11-09", "criteria": "공통_대단원3-2_어휘의양상_20261109_v1 (승인 완료본)",
        "crit_name": {"기준1": "세대에 따른 어휘의 차이 이해", "기준2": "분야에 따른 어휘(전문어) 이해",
                      "기준3": "매체(인터넷)에 따른 어휘 이해", "기준4": "상황에 맞게 어휘를 선택하는 태도",
                      "기준5": "어휘의 개념과 다양성 존중"},
        "band_text": "등급 기준(승인본): 기준1·2·4는 5칸 중 5칸 상 / 3~4칸 중, 기준3은 6칸 중 5칸 이상 상 / "
                     "3~4칸 중, 기준5는 4칸 중 4칸 상 / 2~3칸 중.",
        "method": "빈칸 20칸은 빈 학습지·답지와 칸 단위로 대조하고 승인된 허용 표현을 인정했다. "
                  "선택형 5칸(08·09·10)은 학생 표시 규칙(삭제형·색칠형)으로 판정했다.",
        "notes": [
            "02-2의 '줄이'·'줄이거나'는 승인된 허용 표현 '줄임'의 활용형이라 정답으로 인정했다.",
            "뜻이 비슷하지만 승인된 허용 표현에 없는 말(예: 01-2 '차이가', 11-2 '수용적인'·'이해하는')과 "
            "맞춤법이 어긋난 답(예: '사포나드', '에비네프린')은 오답으로 처리했다. 학생별 근거 요약에 그 답을 "
            "적어 두었으니, 허용 범위를 넓힐지는 교사가 확정한다.",
        ],
    },
    "danuh": {
        "grader": "grade_danuh", "prefix": "danuh",
        "title": "「단어의 짜임」 분석결과 보고서",
        "chasi": "대단원3-1_단어의짜임", "unit": "대단원 3 · 소단원 1",
        "date": "2026-11-09", "criteria": "공통_대단원3-1_단어의짜임_20261109_v1 (승인 완료본)",
        "crit_name": {"기준1": "형태소의 개념과 종류", "기준2": "단어를 형태소로 분석하기",
                      "기준3": "어근과 접사 구별", "기준4": "단어의 형성 방법(단일어·복합어)",
                      "기준5": "새말과 새말의 형성 원리"},
        "band_text": "등급 기준(승인본): 기준마다 맞힌 칸의 비율이 80% 이상이면 상, 50% 이상이면 중, "
                     "50% 미만이면 하(기준1 9칸 중 8칸·기준2 16칸 중 13칸·기준3 6칸 중 5칸·기준4 20칸 중 "
                     "16칸·기준5 15칸 중 12칸 이상이 상).",
        "method": "빈칸 56칸은 빈 학습지·답지와 칸 단위로 대조하고 승인된 허용 표현(하이픈 생략, 뜻→의미 등)을 "
                  "인정했다. 02번 10칸은 단어마다 적은 형태소 조각(예: 김, 밥)을 바른 나눔과 비교했고, 조각 없이 "
                  "△·○만 그린 행은 모양의 순서로 판정했다(교사 결정). 두 쪽을 한 장에 모아 찍은 PDF는 쪽을 "
                  "나눠 읽었다.",
        "notes": [
            "02번은 학생들이 '김△, 밥△', '김 -> 세모, 밥 -> 세모', '김:△ 밥:△'처럼 △·○나 그 이름을 조각 "
            "사이에 섞어 썼다. 한글 조각만 뽑아 비교했고, 조각 순서는 따지지 않았다.",
            "02번에 형태소를 나누어 쓰지 않고 △·○만 그린 행은 모양의 순서가 정답과 같으면 정답으로 보았다"
            "(교사 결정 2026-11-09; 예: 김밥 △△, 헛소리 ○△, 가위질 △○). 형태소가 둘인 단어에 모양을 하나만 "
            "그린 경우는 순서가 맞지 않아 오답이다(학생별 근거의 '(모양만)').",
            "승인된 허용 표현의 범위 안에서 다음도 정답으로 보았다: 칸 뒤의 '형태소'까지 함께 쓴 답"
            "(01 '자립 형태소'·'형식 형태소'), ㄹ을 넣어 쓴 07-5의 답('ㄹ 소리'·'받침 ㄹ'), 따옴표를 덧붙인 답"
            "(04-2 '‘-꾼’').",
            "교사 결정(2026-11-09)으로 다음도 정답 처리했다: 06번 예시 칸에 <보기>가 아닌 단어를 쓰고 그 단어와 "
            "형태소 나눔이 서로 맞는 답(예: 밤나무=밤+나무, 풋사과=풋-+사과), 단일어 예시 '밤'·'밥', "
            "09-3 '합성어', 07-5 '받침'. 단, '덧버섯'처럼 <보기> 단어의 맞춤법이 틀린 답은 오답으로 두었다.",
        ],
    },
}


def class_notes(cfg, cls):
    """반별 비고(중복 제출 처리 등). 학번이 들어가므로 코드가 아니라 로컬 캐시에 둔다."""
    f = pathlib.Path(".claude/cache/notes") / f"{cfg['prefix']}_{cls}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def basis(g, crit):
    per = []
    for c in CRITS:
        vals = [g["items"][k][0] for k in crit[c] if g["items"][k][0] != "?"]   # 판독 못 한 칸 제외
        per.append(f"{vals.count('O')}/{len(vals)}")
    blank = sum(1 for v in g["items"].values() if v[0] == "-")
    unread = sum(1 for v in g["items"].values() if v[0] == "?")
    wrong = [f"{k} '{v[1].strip()}'" for k, v in g["items"].items() if v[0] == "X"]
    s = "기준별 정답 " + "·".join(per) + f" · 무응답 {blank}칸"
    if unread:
        s += f" · 판독 제외 {unread}칸"
    if wrong:
        s += " · 오답 " + ", ".join(wrong[:4]) + (" 외" if len(wrong) > 4 else "")
    return s


def build(cfg, crit, cls, graded, out_dir):
    rows = sorted(graded.items())
    names = NAMES[cls]
    dist = {c: {b: sum(1 for _, v in rows if v[c] == b) for b in BANDS} for c in CRITS}

    def who(sid):
        n = sid.split("_")[0]
        return f"{n} {names.get(n, '')}"

    wrong = collections.Counter()
    picks = collections.defaultdict(collections.Counter)
    for _, g in rows:
        for k, v in g["items"].items():
            if v[0] == "X":
                wrong[k] += 1
                picks[k][v[1].strip()] += 1

    spec = {
        "title": f"{cls} {cfg['title']}",
        "subtitle": f"{cfg['unit']} · 채점일 {cfg['date']} · 적용 분석기준 v1({cfg['date']} 승인)",
        "meta": [
            ["차시 ID", cfg["chasi"]],
            ["적용 분석기준", cfg["criteria"]],
            ["처리 인원", f"{len(rows)}명 (제출자 전원). 미제출자는 이 표에 포함하지 않는다."],
            ["채점 방법", cfg["method"]],
        ],
        "sections": [
            {"heading": "1. 반 전체 등급 분포 요약", "blocks": [
                {"type": "table", "widths": [2.9, 0.9, 0.9, 0.9, 1.2],
                 "header": ["분석 기준", "상", "중", "하", "확인불가"],
                 "rows": [[f"<b>{c}</b> {cfg['crit_name'][c]}"] + [str(dist[c][b]) for b in BANDS]
                          for c in CRITS]},
                {"type": "para", "text": cfg["band_text"] + " 등급은 <b>개별 학생의 목표 도달 여부</b>만을 "
                                         "뜻하며, 학생 간 비교·서열을 나타내지 않는다."}]},
            {"heading": "2. 학생별 채점 결과", "blocks": [
                {"type": "table", "widths": [0.85, 0.95, 0.5, 0.5, 0.5, 0.5, 0.5, 3.6],
                 "header": ["학번", "이름"] + CRITS + ["기준별 근거 요약"],
                 "rows": [[sid.split("_")[0], names.get(sid.split("_")[0], sid.split("_")[-1])]
                          + [g[c] for c in CRITS] + [basis(g, crit)] for sid, g in rows]}]},
        ],
        "footer": "본 보고서는 교사의 검토·수정을 전제로 한 초안입니다. 최종 판단은 교사가 확정합니다.",
    }

    notes = []
    CHECK = ("미검출", "파일 구조", "교사 확인", "빈 학습지")
    flagged = [(sid, [n for n in g["notes"] if any(c in n for c in CHECK)]) for sid, g in rows]
    flagged = [(sid, ns) for sid, ns in flagged if ns]
    if flagged:
        notes.append("<b>교사 확인이 필요한 제출물</b>: " + " / ".join(
            f"{who(sid)}({'; '.join(ns)})" for sid, ns in flagged))
    info = [(sid, [n for n in g["notes"] if not any(c in n for c in CHECK)]) for sid, g in rows]
    info = [(sid, ns) for sid, ns in info if ns]
    if info:
        notes.append("<b>참고 사항이 있는 제출물</b>(판정은 정상 진행): " + " / ".join(
            f"{who(sid)} — {'; '.join(ns)}" for sid, ns in info))
    floor = max(2, len(rows) // 4)
    ranked = [(k, n) for k, n in wrong.most_common() if n >= floor]
    if len(ranked) > 3:                      # 3위와 동점인 칸은 함께 싣는다
        ranked = [(k, n) for k, n in ranked if n >= ranked[2][1]]

    def usual(k):
        ans, n = picks[k].most_common(1)[0]
        return f"{n}명이 '{ans}'" if n >= 2 else "답이 제각각"

    if ranked:
        notes.append("<b>이 반에서 많이 틀린 칸</b>: " + " / ".join(
            f"{k} {n}명 ({usual(k)})" for k, n in ranked)
            + ". 다음 차시 도입에서 짚어 줄 지점이다.")
    many = [(sid, sum(1 for v in g["items"].values() if v[0] == "-")) for sid, g in rows]
    many = [(sid, n) for sid, n in many if n >= 5]
    if many:
        notes.append("<b>상당 부분을 비워 제출한 학생</b>: " + " / ".join(
            f"{who(sid)} {n}칸 무응답" for sid, n in many)
            + ". 무응답은 미도달로 처리했으며, 판독 불가('확인불가')와 구분한다.")
    notes += cfg["notes"] + class_notes(cfg, cls)
    notes += ["<b>등급의 '확인불가'는 파일을 읽을 수 없어 판정하지 못한 경우</b>로, 빈칸을 그대로 둔 무응답과 "
              "구분해 표기했다." + ("" if any(dist[c]["확인불가"] for c in CRITS)
                                  else " 이번 차시에는 판독 실패로 인한 확인불가가 없다."),
              "학생 간 비교·서열화 표현은 쓰지 않았으며, 모든 판정은 제출물에서 확인되는 사실에만 근거한다."]
    spec["sections"].append({"heading": "3. 유의사항",
                             "blocks": [{"type": "bullets", "items": notes}]})

    out_dir = pathlib.Path(out_dir)
    tag = cfg["date"].replace("-", "")
    (out_dir / f"spec_{cfg['prefix']}_{cls}.json").write_text(json.dumps(spec, ensure_ascii=False),
                                                              encoding="utf-8")
    csv_path = out_dir / f"{cls}_{cfg['chasi']}_{tag}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([f"{cls} {cfg['title']}"])
        w.writerow(["차시 ID", cfg["chasi"], "채점일", cfg["date"], "처리 인원", f"{len(rows)}명"])
        w.writerow([])
        w.writerow(["[반 전체 등급 분포]"])
        w.writerow(["분석 기준"] + BANDS)
        for c in CRITS:
            w.writerow([f"{c} {cfg['crit_name'][c]}"] + [dist[c][b] for b in BANDS])
        w.writerow([])
        w.writerow(["[학생별 채점 결과]"])
        w.writerow(["학번", "이름"] + CRITS + ["기준별 근거 요약"])
        for sid, g in rows:
            n = sid.split("_")[0]
            w.writerow([n, names.get(n, sid.split("_")[-1])] + [g[c] for c in CRITS] + [basis(g, crit)])
        w.writerow([])
        w.writerow(["[유의사항]"])
        for n in notes:
            w.writerow([n.replace("<b>", "").replace("</b>", "")])
    return csv_path


def save_results(cfg, cls, graded):
    """학생별 채점 결과를 .claude/cache/results/ 에 남긴다(5·6단계 근거)."""
    out = pathlib.Path(".claude/cache/results")
    out.mkdir(parents=True, exist_ok=True)
    names = NAMES[cls]
    for sid, g in sorted(graded.items()):
        num = sid.split("_")[0]
        lines = [f"# {cls} {num} {names.get(num, '')} — {cfg['chasi']}", "",
                 f"- 채점일: {cfg['date']} / 파일형식: {g['format']} / 적용 분석기준: 승인본 v1",
                 "- 기준별 등급: " + ", ".join(f"{c} {g[c]}" for c in CRITS),
                 f"- 정답 {g['_정답수']}/{len(g['items'])}칸", ""]
        if g["notes"]:
            lines += ["## 비고"] + [f"- {n}" for n in g["notes"]] + [""]
        lines.append("## 칸별 판정 (O 정답 / X 오답 / - 무응답 / ? 미검출 / ! 판정 보류)")
        lines += [f"- {k}: {v[0]} {v[1]}".rstrip() for k, v in g["items"].items()]
        (out / f"{cls}_{cfg['chasi']}_{num}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    key, src, dst = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    cfg = LESSONS[key]
    crit = importlib.import_module(cfg["grader"]).CRIT
    for f in sorted(src.glob(f"{cfg['prefix']}_*반.json"),
                    key=lambda p: int(p.stem.split("_")[-1].replace("반", ""))):
        cls = f.stem.split("_")[-1]
        graded = {k: v for k, v in json.loads(f.read_text(encoding="utf-8")).items() if "items" in v}
        csv_path = build(cfg, crit, cls, graded, dst)
        save_results(cfg, cls, graded)
        print(f"{cls}: {len(graded)}명 → {csv_path.name}")
