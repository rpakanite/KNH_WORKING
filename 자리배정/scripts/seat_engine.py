# -*- coding: utf-8 -*-
"""자리 배정 엔진.

교실 격자(가로 = 열, 세로 = 행), 학생 명단, 배치 조건을 받아
조건을 모두 만족하는 자리 배치를 찾고 텍스트 / SVG / HTML 로 그려 준다.

좌표 약속
  - 행(row) 1 = 칠판·교탁과 가장 가까운 맨 앞줄, 행 번호가 커질수록 뒤쪽.
  - 열(col) 1 = 학생이 칠판을 바라볼 때 가장 왼쪽, 열 번호가 커질수록 오른쪽.
  - 분단 = 좌우로 붙어 있는 열 묶음(기본 2열씩). 남녀짝 조건에서만 쓴다.
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------- 기본 설정 --

GRID_VALID_DAYS = 365          # 1번 질문한 격자 크기를 유지하는 기간(1년)
DEFAULT_BLOCK_WIDTH = 2        # 한 분단을 이루는 열 수
DEFAULT_MIN_DISTANCE = 2       # "분리" 조건의 기본 최소 거리(칸)

GENDER_ALIASES = {
    "남": "남", "남자": "남", "m": "남", "M": "남", "1": "남",
    "여": "여", "녀": "여", "여자": "여", "f": "여", "F": "여", "2": "여",
}

RULE_KINDS = ("고정", "영역", "금지", "짝꿍", "근처", "분리", "분단분리", "남녀짝", "빈자리")


class RuleError(ValueError):
    """조건 문장을 해석하지 못했을 때."""


class SeatError(RuntimeError):
    """배치를 만들 수 없을 때."""


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", str(text)).strip()


# ------------------------------------------------------------------ 설정값 --

def default_settings() -> dict:
    return {
        "격자": None,                 # {"가로": C, "세로": R, "설정일": "YYYY-MM-DD"}
        "교실": {"창가": "왼쪽", "분단열수": DEFAULT_BLOCK_WIDTH, "빈자리": "뒤쪽"},
        "학생": [],                   # [{"번호": 1, "이름": "홍길동", "성별": "남"}]
        "조건": [],                   # 아래 parse_rule 이 만드는 dict 목록
        "조건_수정일": None,
        "최근배치": None,             # {"일시": ..., "자리": {"이름": [행, 열]}}
    }


def load_settings(path: Path) -> dict:
    base = default_settings()
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        base.update(saved)
        # 하위 키 누락 대비
        교실 = default_settings()["교실"]
        교실.update(base.get("교실") or {})
        base["교실"] = 교실
    return base


def save_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def grid_is_valid(settings: dict, today: date | None = None) -> bool:
    """격자 크기를 다시 묻지 않아도 되는지(설정 후 1년 이내인지)."""
    grid = settings.get("격자")
    if not grid or not grid.get("가로") or not grid.get("세로"):
        return False
    설정일 = grid.get("설정일")
    if not 설정일:
        return True
    today = today or date.today()
    try:
        d = datetime.strptime(설정일, "%Y-%m-%d").date()
    except ValueError:
        return True
    return (today - d).days < GRID_VALID_DAYS


def set_grid(settings: dict, 가로: int, 세로: int, today: date | None = None) -> dict:
    가로, 세로 = int(가로), int(세로)
    if 가로 < 1 or 세로 < 1:
        raise ValueError("가로·세로는 1 이상의 정수여야 합니다.")
    settings["격자"] = {
        "가로": 가로,
        "세로": 세로,
        "설정일": (today or date.today()).isoformat(),
    }
    return settings


def grid_size(settings: dict) -> tuple[int, int]:
    """(행 수, 열 수) = (세로, 가로)."""
    grid = settings.get("격자") or {}
    return int(grid["세로"]), int(grid["가로"])


# ------------------------------------------------------------------ 명렬표 --

_NUM_PREFIX = re.compile(r"^(\d{1,3})\s*[.)\-:]?\s+(.+)$")
_GENDER_TAIL = re.compile(r"[\s/(\[·]\s*([남녀여])\s*[)\]]?$")


def parse_student(token: str, 기본번호: int) -> dict:
    tok = nfc(token)
    if not tok:
        raise RuleError("빈 이름입니다.")
    번호 = 기본번호
    m = _NUM_PREFIX.match(tok)
    if m:
        번호, tok = int(m.group(1)), m.group(2).strip()
    성별 = ""
    g = _GENDER_TAIL.search(tok)
    if g:
        성별 = GENDER_ALIASES.get(g.group(1), "")
        tok = tok[: g.start()].strip()
    if not tok:
        raise RuleError(f"이름을 찾지 못했습니다: {token!r}")
    return {"번호": 번호, "이름": tok, "성별": 성별}


def parse_students(text: str) -> list[dict]:
    """줄바꿈 / 쉼표 / 탭으로 구분된 명단 문자열을 파싱한다.

    허용 형식:  홍길동 / 홍길동(남) / 1 홍길동 남 / 1. 홍길동
    """
    학생: list[dict] = []
    for raw_line in nfc(text).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p for p in re.split(r"[,\t]", line) if p.strip()] or [line]
        for part in parts:
            학생.append(parse_student(part, len(학생) + 1))
    이름들 = [s["이름"] for s in 학생]
    중복 = {n for n in 이름들 if 이름들.count(n) > 1}
    if 중복:
        raise RuleError("이름이 중복됩니다: " + ", ".join(sorted(중복)))
    return 학생


def numbered_students(n: int) -> list[dict]:
    """이름 없이 번호만으로 명단을 만든다."""
    return [{"번호": i, "이름": f"{i}번", "성별": ""} for i in range(1, int(n) + 1)]


# -------------------------------------------------------------- 조건 해석 --

_POS_WORDS = {
    "맨앞": ("행", 1, 1), "맨 앞": ("행", 1, 1),
    "앞자리": ("행", 1, 2), "앞쪽": ("행", 1, 2), "앞": ("행", 1, 2),
    "맨뒤": ("행", -1, -1), "맨 뒤": ("행", -1, -1),
    "뒷자리": ("행", -2, -1), "뒤쪽": ("행", -2, -1), "뒤": ("행", -2, -1),
    "왼쪽": ("열", 1, 2), "좌측": ("열", 1, 2),
    "오른쪽": ("열", -2, -1), "우측": ("열", -2, -1),
    "가운데": ("열", 0, 0), "중앙": ("열", 0, 0),
}

_SEP = re.compile(r"\s*(?:,|·|/|과|와|하고|랑|이랑|-|—|~)\s*")


def _names_in(text: str, 이름들: list[str]) -> list[str]:
    """문장에서 등장하는 학생 이름을 등장 순서대로 뽑는다."""
    found: list[tuple[int, str]] = []
    for name in 이름들:
        pos = text.find(name)
        while pos != -1:
            found.append((pos, name))
            pos = text.find(name, pos + 1)
    found.sort()
    결과: list[str] = []
    for _, name in found:
        if name not in 결과:
            결과.append(name)
    return 결과


def parse_rule(line: str, 이름들: list[str]) -> dict:
    """한 줄짜리 한국어 조건 문장을 조건 dict 로 바꾼다.

    지원하는 문장 (예시)
      · 홍길동 3행 2열 고정
      · 홍길동 앞자리 / 홍길동 앞에서 2줄 이내 / 홍길동 맨뒤
      · 홍길동 왼쪽 / 홍길동 창가 / 홍길동 복도쪽
      · 홍길동 김철수 짝꿍
      · 홍길동 김철수 분리 / 홍길동 김철수 3칸 이상 떨어뜨리기
      · 홍길동 김철수 이영희 서로 다른 분단
      · 남녀 짝
      · 1행 1열 빈자리
      · {"종류": "분리", "대상들": ["홍길동", "김철수"], "최소거리": 3}   ← JSON 직접 입력
    """
    원문 = nfc(line)
    if not 원문 or 원문.startswith("#"):
        raise RuleError("빈 조건입니다.")

    if 원문.startswith("{"):
        rule = json.loads(원문)
        if rule.get("종류") not in RULE_KINDS:
            raise RuleError(f"알 수 없는 조건 종류: {rule.get('종류')!r}")
        rule.setdefault("원문", 원문)
        return rule

    text = 원문.replace(" ", "")
    대상 = _names_in(원문, 이름들)

    def done(rule: dict) -> dict:
        rule["원문"] = 원문
        return rule

    # 남녀 짝
    if re.search(r"남녀(짝|자리|섞)", text) or "남녀를섞" in text:
        return done({"종류": "남녀짝"})

    # 빈자리 (사람이 앉지 않는 칸)
    m = re.search(r"(\d+)행(\d+)열", text)
    if m and re.search(r"(빈자리|비움|비운다|사용안함|제외)", text):
        return done({"종류": "빈자리", "자리들": [[int(m.group(1)), int(m.group(2))]]})

    # 자리 고정
    if m and re.search(r"(고정|앉힌다|앉히기|지정|자리는)", text):
        if not 대상:
            raise RuleError("누구를 고정할지 이름을 찾지 못했습니다.")
        return done({"종류": "고정", "대상": 대상[0],
                     "행": int(m.group(1)), "열": int(m.group(2))})

    # 서로 다른 분단
    if re.search(r"다른분단|분단분리|분단을나", text) and len(대상) >= 2:
        return done({"종류": "분단분리", "대상들": 대상})

    # 붙이기 / 짝꿍
    if len(대상) >= 2 and re.search(r"(짝|붙|같이앉|나란히|옆자리|옆에)", text) \
            and not re.search(r"(안|말|금지|못)", text):
        if len(대상) > 2:
            raise RuleError("짝꿍 조건은 두 명씩만 지정할 수 있습니다: " + ", ".join(대상))
        return done({"종류": "짝꿍", "대상들": 대상[:2]})

    # 떼어놓기 / 분리
    if len(대상) >= 2 and re.search(
            r"(분리|떨어|멀리|떼|같이앉지|붙이지|옆에앉지|서로다른)", text):
        거리 = DEFAULT_MIN_DISTANCE
        d = re.search(r"(\d+)칸", text)
        if d:
            거리 = max(1, int(d.group(1)))
        return done({"종류": "분리", "대상들": 대상, "최소거리": 거리})

    # 앞/뒤/좌/우 영역 (금지 여부 포함)
    금지 = bool(re.search(r"(금지|안됨|안돼|하지마|피함|말것|말기|제외)", text))
    for 낱말, (축, a, b) in _POS_WORDS.items():
        key = 낱말.replace(" ", "")
        if key in text:
            if not 대상:
                raise RuleError(f"'{낱말}' 조건의 대상 학생을 찾지 못했습니다.")
            줄수 = re.search(r"(\d+)(?:줄|행|번째줄)", text)
            rule: dict = {"종류": "금지" if 금지 else "영역", "대상": 대상[0]}
            if 축 == "행":
                if 줄수 and a > 0:
                    rule["행범위"] = [1, int(줄수.group(1))]
                elif 줄수 and a < 0:
                    rule["행범위"] = [-int(줄수.group(1)), -1]
                else:
                    rule["행범위"] = [a, b]
            else:
                rule["열범위"] = [a, b] if (a, b) != (0, 0) else "가운데"
            return done(rule)

    # 창가 / 복도 — 창가가 어느 쪽인지는 설정(교실.창가)에서 정한다
    if re.search(r"창(가|측|쪽)", text):
        if not 대상:
            raise RuleError("창가 조건의 대상 학생을 찾지 못했습니다.")
        return done({"종류": "영역", "대상": 대상[0], "열범위": "창가"})
    if re.search(r"복도(쪽|측)?", text):
        if not 대상:
            raise RuleError("복도 조건의 대상 학생을 찾지 못했습니다.")
        return done({"종류": "영역", "대상": 대상[0], "열범위": "복도"})

    raise RuleError(f"해석하지 못한 조건입니다: {원문}")


def describe_rule(rule: dict) -> str:
    """조건 dict 를 사람이 읽을 문장으로."""
    k = rule.get("종류")
    if k == "고정":
        return f"{rule['대상']} → {rule['행']}행 {rule['열']}열 고정"
    if k in ("영역", "금지"):
        말머리 = "금지" if k == "금지" else "배치"
        조각 = []
        if rule.get("행범위"):
            조각.append(_row_text(rule["행범위"]))
        if rule.get("열범위"):
            조각.append(_col_text(rule["열범위"]))
        return f"{rule['대상']} → " + ", ".join(조각) + f" {말머리}"
    if k == "짝꿍":
        return " · ".join(rule["대상들"]) + " → 짝꿍(좌우 옆자리)"
    if k == "근처":
        return " · ".join(rule["대상들"]) + f" → {rule.get('최대거리', 1)}칸 이내"
    if k == "분리":
        return " · ".join(rule["대상들"]) + f" → 서로 {rule.get('최소거리', DEFAULT_MIN_DISTANCE)}칸 이상 떨어뜨리기"
    if k == "분단분리":
        return " · ".join(rule["대상들"]) + " → 서로 다른 분단"
    if k == "남녀짝":
        return "모든 짝(같은 분단 좌우)은 남녀로 구성"
    if k == "빈자리":
        자리 = ", ".join(f"{r}행 {c}열" for r, c in rule.get("자리들", []))
        return f"{자리} → 사용하지 않는 빈자리"
    return rule.get("원문", json.dumps(rule, ensure_ascii=False))


def _row_text(행범위) -> str:
    a, b = 행범위
    if (a, b) == (1, 1):
        return "맨 앞줄"
    if (a, b) == (-1, -1):
        return "맨 뒷줄"
    if a == 1:
        return f"앞에서 {b}줄 이내"
    if b == -1 and a < 0:
        return f"뒤에서 {abs(a)}줄 이내"
    fa = f"뒤에서 {abs(a)}번째 줄" if a < 0 else f"{a}행"
    fb = f"뒤에서 {abs(b)}번째 줄" if b < 0 else f"{b}행"
    return fa if fa == fb else f"{fa}~{fb}"


def _col_text(열범위) -> str:
    if 열범위 == "가운데":
        return "가운데 열"
    if 열범위 == "창가":
        return "창가 쪽"
    if 열범위 == "복도":
        return "복도 쪽"
    a, b = 열범위
    fa = f"오른쪽에서 {abs(a)}번째 열" if a < 0 else f"{a}열"
    fb = f"오른쪽에서 {abs(b)}번째 열" if b < 0 else f"{b}열"
    return fa if fa == fb else f"{fa}~{fb}"


# ------------------------------------------------------------ 조건 컴파일 --

def _resolve_span(범위, n: int, 교실: dict | None = None) -> tuple[int, int]:
    """범위 표기를 실제 (시작, 끝) 번호로 바꾼다. 음수는 뒤에서부터 센다."""
    교실 = 교실 or {}
    if 범위 == "가운데":
        return (n // 2 + 1, n // 2 + 1) if n % 2 else (n // 2, n // 2 + 1)
    if 범위 == "창가":
        c = 1 if 교실.get("창가", "왼쪽") == "왼쪽" else n
        return (c, c)
    if 범위 == "복도":
        c = n if 교실.get("창가", "왼쪽") == "왼쪽" else 1
        return (c, c)
    a, b = 범위
    a = a if a > 0 else n + 1 + a
    b = b if b > 0 else n + 1 + b
    a, b = max(1, min(a, n)), max(1, min(b, n))
    return (min(a, b), max(a, b))


class Problem:
    """풀이에 필요한 형태로 정리한 배치 문제."""

    def __init__(self, rows, cols, students, seats, domains,
                 adj, near, far, diff_block, gender_pair, 교실):
        self.rows, self.cols = rows, cols
        self.students = students
        self.seats = seats
        self.domains = domains          # 이름 -> [좌석]
        self.adj = adj                  # [(A, B)] 좌우 옆자리
        self.near = near                # [(A, B, 최대거리)]
        self.far = far                  # [(A, B, 최소거리)]
        self.diff_block = diff_block    # [(A, B)]
        self.gender_pair = gender_pair  # 남녀짝 적용 여부
        self.교실 = 교실
        self.성별 = {s["이름"]: s.get("성별", "") for s in students}
        self.이웃조건: dict[str, list[tuple]] = {s["이름"]: [] for s in students}
        for a, b in adj:
            self.이웃조건[a].append(("짝꿍", b, 1))
            self.이웃조건[b].append(("짝꿍", a, 1))
        for a, b, d in near:
            self.이웃조건[a].append(("근처", b, d))
            self.이웃조건[b].append(("근처", a, d))
        for a, b, d in far:
            self.이웃조건[a].append(("분리", b, d))
            self.이웃조건[b].append(("분리", a, d))
        for a, b in diff_block:
            self.이웃조건[a].append(("분단분리", b, 0))
            self.이웃조건[b].append(("분단분리", a, 0))

    @property
    def 분단열수(self) -> int:
        return int(self.교실.get("분단열수", DEFAULT_BLOCK_WIDTH))

    def 분단(self, seat) -> int:
        return (seat[1] - 1) // self.분단열수

    def 짝좌석(self, seat):
        """같은 분단에서 좌우로 붙어 있는 짝의 자리(분단이 2열일 때만)."""
        if self.분단열수 != 2:
            return None
        r, c = seat
        return (r, c + 1) if (c - 1) % 2 == 0 and c + 1 <= self.cols else (
            (r, c - 1) if (c - 1) % 2 == 1 else None)


def blocked_seats(settings: dict, rules: list[dict] | None = None) -> set[tuple[int, int]]:
    rules = settings.get("조건", []) if rules is None else rules
    막힌자리 = set()
    for rule in rules:
        if rule.get("종류") == "빈자리":
            for r, c in rule.get("자리들", []):
                막힌자리.add((int(r), int(c)))
    return 막힌자리


def build_problem(settings: dict, rules: list[dict] | None = None,
                  행제한: int | None = None) -> Problem:
    rows, cols = grid_size(settings)
    students = settings.get("학생") or []
    if not students:
        raise SeatError("학생 명단이 비어 있습니다.")
    rules = settings.get("조건", []) if rules is None else rules
    교실 = settings.get("교실") or default_settings()["교실"]

    이름들 = [s["이름"] for s in students]
    막힌자리 = blocked_seats(settings, rules)
    마지막행 = rows if 행제한 is None else max(1, min(int(행제한), rows))
    seats = [(r, c) for r in range(1, 마지막행 + 1) for c in range(1, cols + 1)
             if (r, c) not in 막힌자리]
    if 행제한 is None and len(students) > len([
            (r, c) for r in range(1, rows + 1) for c in range(1, cols + 1)
            if (r, c) not in 막힌자리]):
        raise SeatError(
            f"자리가 부족합니다. 학생 {len(students)}명 / 사용 가능한 자리 {len(seats)}칸 "
            f"(격자 {cols}×{rows}, 빈자리 지정 {len(막힌자리)}칸)"
        )

    domains = {n: list(seats) for n in 이름들}
    adj, near, far, diff_block = [], [], [], []
    gender_pair = False

    def 확인(name: str, rule: dict) -> None:
        if name not in domains:
            raise SeatError(f"명단에 없는 학생입니다: {name} (조건: {describe_rule(rule)})")

    for rule in rules:
        k = rule.get("종류")
        if k == "빈자리":
            continue
        if k == "남녀짝":
            gender_pair = True
            continue
        if k == "고정":
            확인(rule["대상"], rule)
            자리 = (int(rule["행"]), int(rule["열"]))
            domains[rule["대상"]] = [s for s in domains[rule["대상"]] if s == 자리]
            continue
        if k in ("영역", "금지"):
            확인(rule["대상"], rule)
            행 = _resolve_span(rule["행범위"], rows, 교실) if rule.get("행범위") else None
            열 = _resolve_span(rule["열범위"], cols, 교실) if rule.get("열범위") else None

            def 해당(seat, 행=행, 열=열) -> bool:
                if 행 and not (행[0] <= seat[0] <= 행[1]):
                    return False
                if 열 and not (열[0] <= seat[1] <= 열[1]):
                    return False
                return True

            domains[rule["대상"]] = [
                s for s in domains[rule["대상"]] if 해당(s) != (k == "금지")
            ]
            continue
        if k == "짝꿍":
            a, b = rule["대상들"][:2]
            확인(a, rule); 확인(b, rule)
            adj.append((a, b))
            continue
        if k == "근처":
            대상들 = rule["대상들"]
            d = int(rule.get("최대거리", 1))
            for i in range(len(대상들)):
                for j in range(i + 1, len(대상들)):
                    확인(대상들[i], rule); 확인(대상들[j], rule)
                    near.append((대상들[i], 대상들[j], d))
            continue
        if k == "분리":
            대상들 = rule["대상들"]
            d = int(rule.get("최소거리", DEFAULT_MIN_DISTANCE))
            for i in range(len(대상들)):
                for j in range(i + 1, len(대상들)):
                    확인(대상들[i], rule); 확인(대상들[j], rule)
                    far.append((대상들[i], 대상들[j], d))
            continue
        if k == "분단분리":
            대상들 = rule["대상들"]
            for i in range(len(대상들)):
                for j in range(i + 1, len(대상들)):
                    확인(대상들[i], rule); 확인(대상들[j], rule)
                    diff_block.append((대상들[i], 대상들[j]))
            continue
        raise SeatError(f"알 수 없는 조건 종류: {k!r}")

    빈도메인 = [n for n, d in domains.items() if not d]
    if 빈도메인:
        raise SeatError(
            "다음 학생은 조건을 모두 만족하는 자리가 하나도 없습니다: " + ", ".join(빈도메인)
        )

    return Problem(rows, cols, students, seats, domains,
                   adj, near, far, diff_block, gender_pair, 교실)


# ---------------------------------------------------------------- 풀이 --

def _dist(s1, s2) -> int:
    return max(abs(s1[0] - s2[0]), abs(s1[1] - s2[1]))


def _fits(p: Problem, name: str, seat, 배치: dict, 사용중: dict) -> bool:
    if seat in 사용중:
        return False
    for 종류, 상대, d in p.이웃조건[name]:
        자리2 = 배치.get(상대)
        if 자리2 is None:
            continue
        if 종류 == "짝꿍":
            if seat[0] != 자리2[0] or abs(seat[1] - 자리2[1]) != 1:
                return False
        elif 종류 == "근처":
            if _dist(seat, 자리2) > d:
                return False
        elif 종류 == "분리":
            if _dist(seat, 자리2) < d:
                return False
        elif 종류 == "분단분리":
            if p.분단(seat) == p.분단(자리2):
                return False
    if p.gender_pair:
        내성별 = p.성별.get(name, "")
        짝자리 = p.짝좌석(seat)
        if 내성별 and 짝자리 is not None:
            상대 = 사용중.get(짝자리)
            if 상대 and p.성별.get(상대, "") == 내성별:
                return False
    return True


def _backtrack(p: Problem, 배치: dict, 사용중: dict, rng: random.Random,
               카운터: list[int], 한계: int) -> bool:
    if len(배치) == len(p.students):
        return True
    카운터[0] += 1
    if 카운터[0] > 한계:
        return False

    남은 = [n for n in p.domains if n not in 배치]
    후보목록 = None
    고른이름 = None
    for name in 남은:
        가능 = [s for s in p.domains[name] if _fits(p, name, s, 배치, 사용중)]
        if 후보목록 is None or len(가능) < len(후보목록):
            후보목록, 고른이름 = 가능, name
        if not 가능:
            return False
    rng.shuffle(후보목록)
    for seat in 후보목록:
        배치[고른이름] = seat
        사용중[seat] = 고른이름
        if _backtrack(p, 배치, 사용중, rng, 카운터, 한계):
            return True
        del 배치[고른이름]
        del 사용중[seat]
        if 카운터[0] > 한계:
            return False
    return False


def _시도(settings, rules, 행제한, rng, restarts, node_limit):
    try:
        p = build_problem(settings, rules, 행제한=행제한)
    except SeatError:
        return None
    for _ in range(max(1, restarts)):
        배치: dict = {}
        if _backtrack(p, 배치, {}, rng, [0], node_limit):
            return 배치
    return None


def _최소사용행(settings: dict, rules: list[dict] | None) -> int:
    """학생을 모두 앉히는 데 필요한 최소 줄 수(앞줄부터 셀 때)."""
    rows, cols = grid_size(settings)
    막힌자리 = blocked_seats(settings, rules)
    남은 = len(settings.get("학생") or [])
    for r in range(1, rows + 1):
        남은 -= sum(1 for c in range(1, cols + 1) if (r, c) not in 막힌자리)
        if 남은 <= 0:
            return r
    return rows


def solve(settings: dict, rules: list[dict] | None = None, seed: int | None = None,
          restarts: int = 40, node_limit: int = 20000) -> dict:
    """조건을 만족하는 배치를 찾아 {이름: (행, 열)} 로 돌려준다.

    교실.빈자리 == "뒤쪽"(기본)이면 앞줄부터 채우고 남는 자리는 뒤에 모아 둔다.
    앞줄만으로 조건을 만족할 수 없으면 사용할 줄 수를 한 줄씩 늘려 가며 다시 시도한다.
    """
    rows, _ = grid_size(settings)
    실제조건 = settings.get("조건", []) if rules is None else rules
    build_problem(settings, 실제조건)          # 자리 수·명단 오류를 먼저 알린다
    rng = random.Random(seed)
    정책 = (settings.get("교실") or {}).get("빈자리", "뒤쪽")

    if 정책 == "뒤쪽":
        시작 = _최소사용행(settings, 실제조건)
        for 행제한 in range(시작, rows):
            배치 = _시도(settings, rules, 행제한, rng, max(4, restarts // 5), node_limit // 3)
            if 배치:
                return 배치
    배치 = _시도(settings, rules, None, rng, restarts, node_limit)
    if 배치:
        return 배치
    raise SeatError("조건을 모두 만족하는 배치를 찾지 못했습니다.")


def diagnose(settings: dict, seed: int | None = None) -> list[dict]:
    """배치가 불가능할 때, 하나만 빼면 풀리는 '충돌 의심 조건'을 찾는다."""
    rules = list(settings.get("조건") or [])
    충돌: list[dict] = []
    for i in range(len(rules)):
        남긴조건 = rules[:i] + rules[i + 1:]
        try:
            solve(settings, rules=남긴조건, seed=seed, restarts=8, node_limit=8000)
        except (SeatError, ValueError):
            continue
        충돌.append(rules[i])
    return 충돌


# ------------------------------------------------------------------ 그리기 --

def _w(text: str) -> int:
    """한글은 두 칸으로 세는 표시 폭."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    남는칸 = max(0, width - _w(text))
    왼쪽 = 남는칸 // 2
    return " " * 왼쪽 + text + " " * (남는칸 - 왼쪽)


def seat_labels(settings: dict, 배치: dict) -> dict:
    labels = {}
    for s in settings.get("학생", []):
        자리 = 배치.get(s["이름"])
        if 자리:
            자리 = (int(자리[0]), int(자리[1]))
            labels[자리] = f"{s['번호']} {s['이름']}"
    return labels


def render_text(settings: dict, 배치: dict) -> str:
    """터미널·채팅에 그대로 붙일 수 있는 배치표."""
    rows, cols = grid_size(settings)
    labels = seat_labels(settings, 배치)
    막힌자리 = blocked_seats(settings)
    폭 = max([8] + [_w(v) + 2 for v in labels.values()])

    줄들: list[str] = []
    전체폭 = cols * 폭 + (cols + 1)
    교탁 = "[ 교 탁 ]"
    줄들.append(_pad(교탁, 전체폭))
    줄들.append(_pad("─" * _w(교탁), 전체폭))
    줄들.append("".join(" " + _pad(f"{c}열", 폭) for c in range(1, cols + 1)))
    줄들.append("┌" + "┬".join("─" * 폭 for _ in range(cols)) + "┐")
    for r in range(1, rows + 1):
        칸들 = []
        for c in range(1, cols + 1):
            if (r, c) in 막힌자리:
                칸들.append(_pad("✕", 폭))
            else:
                칸들.append(_pad(labels.get((r, c), ""), 폭))
        꼬리 = f"  {r}행" + ("(앞)" if r == 1 else "(뒤)" if r == rows else "")
        줄들.append("│" + "│".join(칸들) + "│" + 꼬리)
        if r < rows:
            줄들.append("├" + "┼".join("─" * 폭 for _ in range(cols)) + "┤")
    줄들.append("└" + "┴".join("─" * 폭 for _ in range(cols)) + "┘")
    return "\n".join(줄들)


def _esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


SEAT_W, SEAT_H, GAP, PAD = 132, 76, 14, 44
FONT = ("'Pretendard','Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',"
        "'NanumGothic',sans-serif")
색 = {"남": ("#e8f1fd", "#8fb6ea"), "여": ("#fdeef3", "#e8a2bd"), "": ("#f2f3f5", "#c3c7cd")}


def render_svg(settings: dict, 배치: dict, 제목: str | None = None) -> str:
    """배치표를 SVG 그림으로 그린다(단독 파일로도 열린다)."""
    rows, cols = grid_size(settings)
    막힌자리 = blocked_seats(settings)
    자리별 = {}
    for s in settings.get("학생", []):
        자리 = 배치.get(s["이름"])
        if 자리:
            자리별[(int(자리[0]), int(자리[1]))] = s

    격자폭 = cols * SEAT_W + (cols - 1) * GAP
    머리높이 = 128
    바닥높이 = 46
    너비 = 격자폭 + PAD * 2
    높이 = 머리높이 + rows * SEAT_H + (rows - 1) * GAP + 바닥높이
    제목 = 제목 or "자리 배치표"
    오늘 = date.today().isoformat()

    p: list[str] = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{너비}" height="{높이}" '
             f'viewBox="0 0 {너비} {높이}" font-family="{FONT}">')
    p.append(f'<rect width="{너비}" height="{높이}" fill="#ffffff"/>')
    p.append(f'<text x="{너비/2:.0f}" y="38" text-anchor="middle" font-size="24" '
             f'font-weight="700" fill="#1f2328">{_esc(제목)}</text>')
    p.append(f'<text x="{너비/2:.0f}" y="60" text-anchor="middle" font-size="13" '
             f'fill="#6b7280">{cols}열 × {rows}행 · {오늘}</text>')

    # 교탁
    교탁폭, 교탁높이 = 150, 34
    교탁x = (너비 - 교탁폭) / 2
    p.append(f'<rect x="{교탁x:.0f}" y="78" width="{교탁폭}" height="{교탁높이}" rx="8" '
             f'fill="#eef2f7" stroke="#9aa4b2"/>')
    p.append(f'<text x="{너비/2:.0f}" y="{78 + 22}" text-anchor="middle" font-size="15" '
             f'fill="#374151" font-weight="600">교 탁 (칠판)</text>')

    for r in range(1, rows + 1):
        y = 머리높이 + (r - 1) * (SEAT_H + GAP)
        for c in range(1, cols + 1):
            x = PAD + (c - 1) * (SEAT_W + GAP)
            if (r, c) in 막힌자리:
                p.append(f'<rect x="{x}" y="{y}" width="{SEAT_W}" height="{SEAT_H}" rx="10" '
                         f'fill="#fafafa" stroke="#e5e7eb" stroke-dasharray="6 5"/>')
                p.append(f'<text x="{x + SEAT_W/2:.0f}" y="{y + SEAT_H/2 + 5:.0f}" '
                         f'text-anchor="middle" font-size="13" fill="#b0b5bd">빈자리</text>')
                continue
            학생 = 자리별.get((r, c))
            바탕, 테두리 = 색.get((학생 or {}).get("성별", ""), 색[""])
            if 학생 is None:
                바탕, 테두리 = "#ffffff", "#e5e7eb"
            p.append(f'<rect x="{x}" y="{y}" width="{SEAT_W}" height="{SEAT_H}" rx="10" '
                     f'fill="{바탕}" stroke="{테두리}"/>')
            if 학생 is None:
                continue
            p.append(f'<text x="{x + SEAT_W/2:.0f}" y="{y + 30:.0f}" text-anchor="middle" '
                     f'font-size="13" fill="#6b7280">{_esc(학생["번호"])}번</text>')
            p.append(f'<text x="{x + SEAT_W/2:.0f}" y="{y + 55:.0f}" text-anchor="middle" '
                     f'font-size="19" font-weight="600" fill="#1f2328">'
                     f'{_esc(학생["이름"])}</text>')
        p.append(f'<text x="{PAD - 10}" y="{y + SEAT_H/2 + 5:.0f}" text-anchor="end" '
                 f'font-size="12" fill="#9aa4b2">{r}행</text>')

    바닥y = 높이 - 18
    창가 = (settings.get("교실") or {}).get("창가", "왼쪽")
    p.append(f'<text x="{PAD}" y="{바닥y}" font-size="12" fill="#9aa4b2">'
             f'← {_esc(창가)}쪽(창가) · 위쪽이 교탁 방향 · 행 번호는 왼쪽 숫자</text>')
    p.append('</svg>')
    return "\n".join(p)


def render_html(settings: dict, 배치: dict, 제목: str | None = None) -> str:
    """SVG 배치표 + 적용된 조건 목록을 담은 인쇄용 HTML."""
    svg = render_svg(settings, 배치, 제목)
    조건들 = settings.get("조건") or []
    항목 = "\n".join(f"      <li>{_esc(describe_rule(r))}</li>" for r in 조건들) \
        or "      <li>등록된 조건 없음</li>"
    rows, cols = grid_size(settings)
    제목 = 제목 or "자리 배치표"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(제목)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; padding: 24px 16px 48px; background: #f6f7f9; color: #1f2328;
         font-family: {FONT}; }}
  .wrap {{ max-width: 1000px; margin: 0 auto; }}
  .card {{ background: #fff; border: 1px solid #e5e7eb; border-radius: 14px;
           padding: 20px; margin-bottom: 18px; overflow-x: auto; }}
  h2 {{ font-size: 16px; margin: 0 0 10px; }}
  ul {{ margin: 0; padding-left: 20px; line-height: 1.8; font-size: 14px; }}
  .meta {{ color: #6b7280; font-size: 13px; }}
  svg {{ max-width: 100%; height: auto; }}
  @media print {{ body {{ background: #fff; padding: 0; }}
                  .card {{ border: none; padding: 0; }} }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="card">
{svg}
    </div>
    <div class="card">
      <h2>적용된 배치 조건</h2>
      <ul>
{항목}
      </ul>
      <p class="meta">격자 {cols}열 × {rows}행 · 학생 {len(settings.get('학생') or [])}명 ·
         생성일 {date.today().isoformat()}</p>
    </div>
  </div>
</body>
</html>
"""


def write_outputs(settings: dict, 배치: dict, out_dir: Path,
                  제목: str | None = None, stem: str | None = None) -> dict:
    """배치표를 HTML·SVG 파일로 저장하고 경로를 돌려준다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = stem or "배치표_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = out_dir / f"{stem}.html"
    svg_path = out_dir / f"{stem}.svg"
    html_path.write_text(render_html(settings, 배치, 제목), encoding="utf-8")
    svg_path.write_text(render_svg(settings, 배치, 제목), encoding="utf-8")
    return {"html": html_path, "svg": svg_path}
