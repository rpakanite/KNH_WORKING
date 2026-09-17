# -*- coding: utf-8 -*-
"""자리 배정 엔진 자체 점검.

실행:  python3 scripts/test_seat_engine.py   (pytest 로도 실행 가능)
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seat_engine as E  # noqa: E402


def _설정(가로=4, 세로=3, 학생=None, 조건=None, 설정일=None):
    s = E.default_settings()
    s["격자"] = {"가로": 가로, "세로": 세로,
                "설정일": 설정일 or date.today().isoformat()}
    s["학생"] = 학생 if 학생 is not None else E.numbered_students(8)
    s["조건"] = 조건 or []
    return s


def _이름학생():
    return E.parse_students("1 가영 여\n2 나연 여\n3 다훈 남\n4 라온 남\n5 마루 남\n6 바다 여")


# ------------------------------------------------------------------ 격자 --

def test_격자는_1년간_유지된다():
    s = _설정()
    assert E.grid_is_valid(s)
    s["격자"]["설정일"] = (date.today() - timedelta(days=200)).isoformat()
    assert E.grid_is_valid(s)
    s["격자"]["설정일"] = (date.today() - timedelta(days=400)).isoformat()
    assert not E.grid_is_valid(s), "1년이 지나면 다시 물어야 한다"
    assert not E.grid_is_valid(E.default_settings())


def test_격자_저장과_크기():
    s = E.set_grid(E.default_settings(), 6, 5)
    assert E.grid_size(s) == (5, 6)  # (행, 열) = (세로, 가로)


# ------------------------------------------------------------------ 명단 --

def test_명단_형식들():
    학생 = E.parse_students("1 홍길동 남\n김철수(여)\n3. 이영희\n박민수/남")
    assert [x["이름"] for x in 학생] == ["홍길동", "김철수", "이영희", "박민수"]
    assert [x["번호"] for x in 학생] == [1, 2, 3, 4]
    assert [x["성별"] for x in 학생] == ["남", "여", "", "남"]


def test_명단_쉼표와_중복():
    assert len(E.parse_students("가, 나, 다")) == 3
    try:
        E.parse_students("가\n가")
    except E.RuleError:
        pass
    else:
        raise AssertionError("중복 이름은 거부해야 한다")


# ------------------------------------------------------------------ 조건 --

def test_조건_문장_해석():
    이름 = ["가영", "나연", "다훈"]
    assert E.parse_rule("가영 3행 2열 고정", 이름) == {
        "종류": "고정", "대상": "가영", "행": 3, "열": 2, "원문": "가영 3행 2열 고정"}
    assert E.parse_rule("가영 앞자리", 이름)["행범위"] == [1, 2]
    assert E.parse_rule("가영 앞에서 1줄 이내", 이름)["행범위"] == [1, 1]
    assert E.parse_rule("가영 맨뒤", 이름)["행범위"] == [-1, -1]
    assert E.parse_rule("가영 맨뒤 금지", 이름)["종류"] == "금지"
    assert E.parse_rule("가영 나연 짝꿍", 이름) == {
        "종류": "짝꿍", "대상들": ["가영", "나연"], "원문": "가영 나연 짝꿍"}
    분리 = E.parse_rule("가영 나연 3칸 이상 떨어뜨리기", 이름)   # 사이 3칸 → 좌석 거리 4
    assert 분리["종류"] == "분리" and 분리["최소거리"] == 4
    assert E.parse_rule("가영 나연 분리", 이름)["최소거리"] == 2   # 기본: 붙어 앉지 않기
    assert E.parse_rule("가영 나연 다훈 서로 다른 분단", 이름)["종류"] == "분단분리"
    assert E.parse_rule("남녀 짝", 이름)["종류"] == "남녀짝"
    assert E.parse_rule("1행 1열 빈자리", 이름)["자리들"] == [[1, 1]]
    assert E.parse_rule('{"종류": "근처", "대상들": ["가영", "나연"], "최대거리": 2}',
                        이름)["종류"] == "근처"
    try:
        E.parse_rule("알수없는문장입니다", 이름)
    except E.RuleError:
        pass
    else:
        raise AssertionError("해석 못 하는 문장은 오류여야 한다")


def test_조건_설명문():
    assert "3행 2열 고정" in E.describe_rule(
        {"종류": "고정", "대상": "가영", "행": 3, "열": 2})
    assert "짝꿍" in E.describe_rule({"종류": "짝꿍", "대상들": ["가영", "나연"]})


# ------------------------------------------------------------------ 배치 --

def test_고정과_앞자리_조건을_지킨다():
    학생 = _이름학생()
    조건 = [E.parse_rule("가영 2행 3열 고정", [s["이름"] for s in 학생]),
           E.parse_rule("다훈 앞자리", [s["이름"] for s in 학생])]
    s = _설정(가로=4, 세로=3, 학생=학생, 조건=조건)
    배치 = E.solve(s, seed=1)
    assert 배치["가영"] == (2, 3)
    assert 배치["다훈"][0] <= 2
    assert len(set(배치.values())) == len(배치), "두 학생이 같은 자리에 앉으면 안 된다"


def test_짝꿍과_분리_조건을_지킨다():
    학생 = _이름학생()
    이름 = [s["이름"] for s in 학생]
    조건 = [E.parse_rule("가영 나연 짝꿍", 이름),
           E.parse_rule("다훈 라온 2칸 이상 떨어뜨리기", 이름)]   # 사이 2칸 → 거리 3
    s = _설정(가로=4, 세로=3, 학생=학생, 조건=조건)
    for seed in range(5):
        배치 = E.solve(s, seed=seed)
        r1, c1 = 배치["가영"]; r2, c2 = 배치["나연"]
        assert r1 == r2 and abs(c1 - c2) == 1
        assert max(abs(배치["다훈"][0] - 배치["라온"][0]),
                   abs(배치["다훈"][1] - 배치["라온"][1])) >= 3


def test_남녀짝과_빈자리():
    학생 = _이름학생()
    이름 = [s["이름"] for s in 학생]
    조건 = [E.parse_rule("남녀 짝", 이름), E.parse_rule("1행 1열 빈자리", 이름)]
    s = _설정(가로=4, 세로=3, 학생=학생, 조건=조건)
    배치 = E.solve(s, seed=3)
    assert (1, 1) not in 배치.values()
    자리별 = {v: k for k, v in 배치.items()}
    성별 = {x["이름"]: x["성별"] for x in 학생}
    for (r, c), 이름1 in 자리별.items():
        짝 = (r, c + 1) if (c - 1) % 2 == 0 else (r, c - 1)
        이름2 = 자리별.get(짝)
        if 이름2 and 성별[이름1] and 성별[이름2]:
            assert 성별[이름1] != 성별[이름2], f"{이름1}·{이름2} 짝의 성별이 같다"


def test_분단분리():
    학생 = _이름학생()
    이름 = [s["이름"] for s in 학생]
    조건 = [E.parse_rule("가영 나연 다훈 서로 다른 분단", 이름)]
    s = _설정(가로=6, 세로=3, 학생=학생, 조건=조건)
    배치 = E.solve(s, seed=2)
    분단 = {(배치[n][1] - 1) // 2 for n in ("가영", "나연", "다훈")}
    assert len(분단) == 3


def test_자리가_모자라면_알려준다():
    s = _설정(가로=2, 세로=2, 학생=E.numbered_students(6))
    try:
        E.solve(s)
    except E.SeatError as err:
        assert "자리가 부족" in str(err)
    else:
        raise AssertionError("자리 부족을 알려야 한다")


def test_불가능한_조건은_충돌_조건을_찾아준다():
    학생 = _이름학생()
    이름 = [s["이름"] for s in 학생]
    조건 = [E.parse_rule("가영 나연 짝꿍", 이름),
           E.parse_rule("가영 나연 2칸 이상 떨어뜨리기", 이름)]
    s = _설정(가로=4, 세로=3, 학생=학생, 조건=조건)
    try:
        E.solve(s, restarts=5, node_limit=3000)
    except E.SeatError:
        pass
    else:
        raise AssertionError("모순된 조건은 실패해야 한다")
    충돌 = E.diagnose(s)
    assert len(충돌) == 2, "두 조건 중 하나만 빼도 풀린다는 것을 찾아야 한다"


def test_남는_자리는_뒷줄에_모인다():
    학생 = _이름학생()                     # 6명
    s = _설정(가로=6, 세로=4, 학생=학생)   # 24자리 중 6명 → 맨 앞줄만 사용
    배치 = E.solve(s, seed=4)
    assert {자리[0] for 자리 in 배치.values()} == {1}


def test_뒷줄_조건이_있으면_줄을_늘려서_배치한다():
    학생 = _이름학생()
    이름 = [x["이름"] for x in 학생]
    s = _설정(가로=6, 세로=4, 학생=학생, 조건=[E.parse_rule("마루 맨뒤", 이름)])
    배치 = E.solve(s, seed=4)
    assert 배치["마루"][0] == 4


def test_빈자리_정책_자유():
    학생 = _이름학생()
    s = _설정(가로=6, 세로=4, 학생=학생)
    s["교실"]["빈자리"] = "자유"
    배치 = E.solve(s, seed=4)
    assert len(배치) == 6


def test_모든_학생이_한_자리씩_배정된다():
    s = _설정(가로=5, 세로=5, 학생=E.numbered_students(20))
    배치 = E.solve(s, seed=9)
    assert len(배치) == 20 and len(set(배치.values())) == 20


def test_희망은_가능한_만큼만_지킨다():
    학생 = E.parse_students("가영\n나연\n다훈\n라온")
    이름 = [x["이름"] for x in 학생]
    # 1열은 2칸뿐인데 3명이 1열을 희망 → 두 명만 들어주고 한 명은 못 지킨 것으로 보고
    조건 = [E.parse_rule(f"{n} 1열 희망", 이름) for n in ("가영", "나연", "다훈")]
    s = _설정(가로=2, 세로=2, 학생=학생, 조건=조건)
    배치, 미충족 = E.solve_detail(s, seed=1)
    assert len(배치) == 4
    첫열 = [n for n in ("가영", "나연", "다훈") if 배치[n][1] == 1]
    assert len(첫열) == 2 and len(미충족) == 1
    assert 미충족[0]["대상"] not in 첫열


def test_희망이_충돌하지_않으면_모두_지킨다():
    학생 = _이름학생()
    이름 = [x["이름"] for x in 학생]
    조건 = [E.parse_rule("가영 1열 희망", 이름), E.parse_rule("나연 맨뒤 희망", 이름)]
    s = _설정(가로=6, 세로=4, 학생=학생, 조건=조건)
    배치, 미충족 = E.solve_detail(s, seed=2)
    assert not 미충족 and 배치["가영"][1] == 1 and 배치["나연"][0] == 4


def test_희망은_필수조건보다_뒤로_밀린다():
    학생 = E.parse_students("가영\n나연")
    이름 = [x["이름"] for x in 학생]
    조건 = [E.parse_rule("가영 1행 1열 고정", 이름), E.parse_rule("나연 1열 희망", 이름),
           E.parse_rule("나연 맨앞", 이름)]
    s = _설정(가로=2, 세로=1, 학생=학생, 조건=조건)
    배치, 미충족 = E.solve_detail(s, seed=3)
    assert 배치["가영"] == (1, 1) and 배치["나연"] == (1, 2) and len(미충족) == 1


def test_최소수정은_어긋난_사람만_옮긴다():
    학생 = _이름학생()
    이름 = [x["이름"] for x in 학생]
    s = _설정(가로=6, 세로=4, 학생=학생)
    기존 = E.solve(s, seed=1)
    # 일부러 붙여 앉힌 두 사람에게 분리 조건을 새로 건다
    기존["가영"], 기존["나연"] = (1, 1), (1, 2)
    자리쓴사람 = {v: k for k, v in 기존.items() if k not in ("가영", "나연")}
    남은 = [(r, c) for r in range(1, 5) for c in range(1, 7)
           if (r, c) not in ((1, 1), (1, 2))]
    for 이름2 in [n for n in 이름 if n not in ("가영", "나연")]:
        기존[이름2] = 남은.pop()
    s["조건"] = [E.parse_rule("가영 나연 1칸 이상 떨어뜨리기", 이름)]
    배치, 미충족, 바뀐 = E.repair_detail(s, 기존, seed=2)
    assert max(abs(배치["가영"][0] - 배치["나연"][0]),
               abs(배치["가영"][1] - 배치["나연"][1])) >= 2
    assert len(배치) == len(학생) and len(set(배치.values())) == len(학생)
    assert 0 < len(바뀐) <= 2, f"필요한 만큼만 옮겨야 한다: {바뀐}"


def test_최소수정은_희망도_챙긴다():
    학생 = _이름학생()
    이름 = [x["이름"] for x in 학생]
    s = _설정(가로=6, 세로=4, 학생=학생)
    기존 = E.solve(s, seed=3)
    s["조건"] = [E.parse_rule("마루 맨뒤 희망", 이름)]
    배치, 미충족, 바뀐 = E.repair_detail(s, 기존, seed=3)
    assert not 미충족 and 배치["마루"][0] == 4


# ------------------------------------------------------------------ 그리기 --

def test_그림_출력():
    학생 = _이름학생()
    s = _설정(가로=4, 세로=3, 학생=학생,
             조건=[E.parse_rule("1행 1열 빈자리", [x["이름"] for x in 학생])])
    배치 = E.solve(s, seed=5)
    글 = E.render_text(s, 배치)
    assert "교 탁" in 글 and "가영" in 글 and "✕" in 글
    svg = E.render_svg(s, 배치)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>") and "가영" in svg
    html = E.render_html(s, 배치)
    assert "<!DOCTYPE html>" in html and "적용된 배치 조건" in html


def test_교사시점이_기본이고_행열이_뒤집힌다():
    학생 = _이름학생()
    s = _설정(가로=6, 세로=4, 학생=학생)
    assert s["교실"]["보기"] == "교사시점"
    행순서, 열순서, 교탁아래 = E.표시순서(s)
    assert 행순서 == [4, 3, 2, 1] and 열순서 == [6, 5, 4, 3, 2, 1] and 교탁아래

    글 = E.render_text(s, E.solve(s, seed=1))
    줄들 = 글.splitlines()
    자리줄 = [l for l in 줄들 if "행(" in l or ("행" in l and "│" in l)]
    assert "4행(뒤)" in 자리줄[0] and "1행(앞)" in 자리줄[-1]
    assert 줄들[0].index("6열") < 줄들[0].index("1열"), "왼쪽이 마지막 열이어야 한다"
    assert 줄들.index([l for l in 줄들 if "교 탁" in l][0]) > 줄들.index(자리줄[0]), \
        "교탁은 그림 아래쪽에 있어야 한다"


def test_학생시점으로_되돌릴_수_있다():
    학생 = _이름학생()
    s = _설정(가로=6, 세로=4, 학생=학생)
    s["교실"]["보기"] = "학생시점"
    행순서, 열순서, 교탁아래 = E.표시순서(s)
    assert 행순서 == [1, 2, 3, 4] and 열순서 == [1, 2, 3, 4, 5, 6] and not 교탁아래
    글 = E.render_text(s, E.solve(s, seed=1))
    assert "교 탁" in 글.splitlines()[0]


def test_A4_가로_출력():
    학생 = _이름학생()
    s = _설정(가로=6, 세로=4, 학생=학생)
    배치 = E.solve(s, seed=5)
    svg = E.render_svg(s, 배치, "테스트", 용지="A4가로")
    assert f'width="{E.A4_가로[0]}"' in svg and f'height="{E.A4_가로[1]}"' in svg
    assert "가영" in svg and "<g transform=" in svg
    html = E.render_a4_html(s, 배치, "테스트")
    assert "size: A4 landscape" in html
    assert "적용된 배치 조건" not in html, "A4 출력에는 조건 목록을 넣지 않는다"


def test_파일_저장(tmp_dir=None):
    import tempfile
    학생 = _이름학생()
    s = _설정(학생=학생)
    배치 = E.solve(s, seed=0)
    with tempfile.TemporaryDirectory() as d:
        경로 = E.write_outputs(s, 배치, Path(d), "테스트 반")
        assert 경로["html"].exists() and 경로["svg"].exists()
        assert 경로["A4_html"].exists() and 경로["A4_svg"].exists()
        assert "테스트 반" in 경로["html"].read_text(encoding="utf-8")


def _run_all() -> int:
    실패 = 0
    for 이름, 함수 in sorted(globals().items()):
        if 이름.startswith("test_") and callable(함수):
            try:
                함수()
                print(f"  ✓ {이름}")
            except Exception as err:  # noqa: BLE001
                실패 += 1
                print(f"  ✗ {이름} — {type(err).__name__}: {err}")
    print(("모두 통과" if not 실패 else f"{실패}건 실패"))
    return 1 if 실패 else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
