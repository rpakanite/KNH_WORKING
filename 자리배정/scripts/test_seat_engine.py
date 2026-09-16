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
    분리 = E.parse_rule("가영 나연 3칸 이상 떨어뜨리기", 이름)
    assert 분리["종류"] == "분리" and 분리["최소거리"] == 3
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
           E.parse_rule("다훈 라온 3칸 이상 떨어뜨리기", 이름)]
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
           E.parse_rule("가영 나연 3칸 이상 떨어뜨리기", 이름)]
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


def test_파일_저장(tmp_dir=None):
    import tempfile
    학생 = _이름학생()
    s = _설정(학생=학생)
    배치 = E.solve(s, seed=0)
    with tempfile.TemporaryDirectory() as d:
        경로 = E.write_outputs(s, 배치, Path(d), "테스트 반")
        assert 경로["html"].exists() and 경로["svg"].exists()
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
