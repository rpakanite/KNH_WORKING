#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""자리 배정 실행 스크립트.

세션 진행 순서(프로젝트 규칙)
  1) 격자 크기(가로 몇 칸 × 세로 몇 칸)를 묻는다 — 저장되어 있고 1년이 지나지 않았으면 묻지 않는다.
  2) 저장된 조건을 보여 주고 "수정할까요?"만 묻는다.
  3) 조건을 만족하는 배치를 만들어 그림으로 보여 주고 "수정할까요?"를 묻는다.
  4) 확정되면 저장하고 "완료." 를 출력한 뒤 끝낸다.

사용 예
  python3 scripts/seat_assign.py                      # 대화형 전체 흐름
  python3 scripts/seat_assign.py --격자 6x5           # 가로6 × 세로5 로 설정
  python3 scripts/seat_assign.py --학생 명단.txt
  python3 scripts/seat_assign.py --조건추가 "홍길동 앞자리" --조건추가 "홍길동 김철수 분리"
  python3 scripts/seat_assign.py --배치 --씨드 7      # 질문 없이 배치만 생성
  python3 scripts/seat_assign.py --상태               # 저장된 설정 확인
  python3 scripts/seat_assign.py --조건도움말
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seat_engine as E  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE / "데이터" / "settings.json"
OUT_DIR = BASE / "출력"


# ---------------------------------------------------------------- 출력 도우미 --

def 알림(msg: str = "") -> None:
    print(msg, flush=True)


def 제목줄(text: str) -> None:
    알림()
    알림(f"── {text} " + "─" * max(0, 60 - E._w(text)))


def 보기좋은경로(path: Path) -> str:
    """가능하면 프로젝트 기준 상대경로로, 아니면 절대경로 그대로."""
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def 대화가능() -> bool:
    return sys.stdin is not None and sys.stdin.isatty()


def 물음(prompt: str, 기본: str = "") -> str:
    try:
        답 = input(prompt).strip()
    except EOFError:
        return 기본
    return 답 or 기본


def 예아니오(prompt: str, 기본: bool = False) -> bool:
    표시 = "[y/N]" if not 기본 else "[Y/n]"
    답 = 물음(f"{prompt} {표시} ").lower()
    if not 답:
        return 기본
    return 답 in ("y", "yes", "ㅇ", "예", "네", "응", "수정")


def 여러줄입력(안내: str) -> str:
    알림(안내)
    알림("(입력을 마치려면 빈 줄에서 Enter)")
    줄들 = []
    while True:
        try:
            줄 = input()
        except EOFError:
            break
        if not 줄.strip():
            break
        줄들.append(줄)
    return "\n".join(줄들)


# ------------------------------------------------------------------- 단계 --

def 격자단계(settings: dict, 강제질문: bool = False) -> None:
    """1·2단계: 격자 크기는 1년에 한 번만 묻는다."""
    if E.grid_is_valid(settings) and not 강제질문:
        rows, cols = E.grid_size(settings)
        설정일 = settings["격자"].get("설정일", "?")
        알림(f"교실 격자: 가로 {cols}칸 × 세로 {rows}칸 "
             f"(설정일 {설정일} · 1년간 유지하므로 다시 묻지 않습니다)")
        return
    if not 대화가능():
        raise SystemExit(
            "격자 크기가 설정되어 있지 않습니다. --격자 6x5 처럼 '가로x세로'를 지정해 주세요."
        )
    제목줄("1단계 · 교실 격자 크기")
    알림("이 질문은 1년에 한 번만 합니다. (한 해 동안 같은 값을 계속 사용합니다)")
    while True:
        try:
            가로 = int(물음("가로(한 줄에 놓인 자리 수)는 몇 칸인가요? "))
            세로 = int(물음("세로(줄 수)는 몇 칸인가요? "))
            E.set_grid(settings, 가로, 세로)
            break
        except (ValueError, TypeError):
            알림("1 이상의 숫자로 입력해 주세요.")
    알림(f"→ 가로 {가로}칸 × 세로 {세로}칸 (총 {가로 * 세로}자리) 로 저장했습니다.")


def 명단단계(settings: dict) -> None:
    if settings.get("학생"):
        인원 = len(settings["학생"])
        알림(f"학생 명단: {인원}명 (저장됨)")
        return
    rows, cols = E.grid_size(settings)
    if not 대화가능():
        raise SystemExit(
            "학생 명단이 없습니다. --학생 <파일> 또는 --학생수 <숫자> 로 등록해 주세요."
        )
    제목줄("학생 명단")
    알림("한 줄에 한 명씩 입력하세요. 예) '1 홍길동 남' · '홍길동(여)' · '홍길동'")
    알림(f"이름 없이 번호만 쓰려면 인원수만 숫자로 입력하세요. (최대 {rows * cols}명)")
    글 = 여러줄입력("명단 입력:")
    if re.fullmatch(r"\d+", 글.strip()):
        settings["학생"] = E.numbered_students(int(글.strip()))
    else:
        settings["학생"] = E.parse_students(글)
    알림(f"→ {len(settings['학생'])}명을 등록했습니다.")


def 조건출력(settings: dict) -> None:
    조건들 = settings.get("조건") or []
    if not 조건들:
        알림("등록된 조건이 없습니다.")
        return
    수정일 = settings.get("조건_수정일") or "-"
    알림(f"저장된 배치 조건 {len(조건들)}개 (최종 수정 {수정일}) — 매 세션 동일하게 적용됩니다.")
    for i, rule in enumerate(조건들, 1):
        알림(f"  {i}. {E.describe_rule(rule)}")


def 조건입력받기(settings: dict) -> None:
    이름들 = [s["이름"] for s in settings.get("학생", [])]
    글 = 여러줄입력("조건을 한 줄에 하나씩 입력하세요. (문법이 궁금하면 '?' 입력)")
    if 글.strip() == "?":
        알림(조건도움말())
        글 = 여러줄입력("조건을 한 줄에 하나씩 입력하세요.")
    for 줄 in 글.splitlines():
        if not 줄.strip():
            continue
        try:
            settings.setdefault("조건", []).append(E.parse_rule(줄, 이름들))
        except (E.RuleError, ValueError) as err:
            알림(f"  ! 건너뜀 — {err}")
    settings["조건_수정일"] = date.today().isoformat()


def 조건단계(settings: dict) -> None:
    """3·4단계: 조건은 계속 유지하되, 매 세션 수정 여부는 반드시 묻는다."""
    제목줄("조건 확인")
    조건출력(settings)
    if not settings.get("조건"):
        if not 대화가능():
            알림("(조건 없이 무작위로 배치합니다)")
            return
        조건입력받기(settings)
        조건출력(settings)
        return
    if not 대화가능():
        알림("(비대화 모드 — 저장된 조건을 그대로 적용합니다)")
        return
    while 예아니오("조건을 수정할까요?"):
        알림("  1) 조건 추가   2) 번호로 삭제   3) 전부 지우고 다시 입력   0) 그대로 두기")
        선택 = 물음("  선택: ", "0")
        if 선택 == "1":
            조건입력받기(settings)
        elif 선택 == "2":
            번호 = 물음("  삭제할 번호(쉼표로 여러 개): ")
            지울것 = sorted({int(n) for n in re.findall(r"\d+", 번호)}, reverse=True)
            for n in 지울것:
                if 1 <= n <= len(settings["조건"]):
                    삭제 = settings["조건"].pop(n - 1)
                    알림(f"  - 삭제: {E.describe_rule(삭제)}")
            settings["조건_수정일"] = date.today().isoformat()
        elif 선택 == "3":
            settings["조건"] = []
            조건입력받기(settings)
        else:
            break
        조건출력(settings)


def 배치생성(settings: dict, seed: int | None = None) -> tuple[dict, list]:
    try:
        return E.solve_detail(settings, seed=seed)
    except E.SeatError as err:
        알림()
        알림(f"⚠ {err}")
        충돌 = E.diagnose(settings)
        if 충돌:
            알림("다음 조건 중 하나를 빼면 배치가 가능합니다 — 조건을 조정해 주세요.")
            for rule in 충돌:
                알림(f"  · {E.describe_rule(rule)}")
        else:
            알림("여러 조건이 한꺼번에 충돌하고 있습니다. 조건을 줄여 보세요.")
        raise SystemExit(1)


def 배치보여주기(settings: dict, 배치: dict, 제목: str | None = None,
              미충족희망: list | None = None) -> dict:
    제목줄("자리 배치표")
    알림(E.render_text(settings, 배치))
    미충족희망 = 미충족희망 or []
    if 미충족희망:
        알림()
        알림("※ 자리가 모자라 이번 배치에서 못 지킨 희망 조건:")
        for rule in 미충족희망:
            알림(f"  · {E.describe_rule(rule)}")
    경로 = E.write_outputs(settings, 배치, OUT_DIR, 제목, 미충족희망=미충족희망)
    알림()
    알림(f"그림 파일: {보기좋은경로(경로['html'])}  /  {보기좋은경로(경로['svg'])}")
    if 경로.get("A4_html"):
        알림(f"A4 가로(조건 목록 없이 배치표만): {보기좋은경로(경로['A4_html'])}  /  "
             f"{보기좋은경로(경로['A4_svg'])}")
    return 경로


def 자리맞바꾸기(settings: dict, 배치: dict) -> None:
    이름들 = [s["이름"] for s in settings["학생"]]
    답 = 물음("  맞바꿀 두 학생 이름을 띄어쓰기로 입력: ")
    고른이름 = [n for n in 이름들 if n in 답]
    if len(고른이름) != 2:
        알림("  ! 두 명의 이름을 정확히 찾지 못했습니다.")
        return
    a, b = 고른이름
    배치[a], 배치[b] = 배치[b], 배치[a]
    알림(f"  → {a} ↔ {b} 자리를 맞바꿨습니다. (수동 변경이라 조건 위반이 생길 수 있습니다)")


def 확정단계(settings: dict, 배치: dict) -> None:
    settings["최근배치"] = {
        "일시": datetime.now().isoformat(timespec="seconds"),
        "자리": {이름: [자리[0], 자리[1]] for 이름, 자리 in 배치.items()},
    }
    E.save_settings(SETTINGS_PATH, settings)


# ---------------------------------------------------------------- 도움말 --

def 조건도움말() -> str:
    return """조건 문장 예시 (한 줄에 하나씩)
  · 홍길동 3행 2열 고정          → 특정 자리에 고정
  · 홍길동 앞자리 / 홍길동 맨앞   → 앞쪽 줄에 배치
  · 홍길동 앞에서 2줄 이내
  · 홍길동 뒷자리 / 홍길동 맨뒤
  · 홍길동 왼쪽 / 오른쪽 / 가운데 / 창가 / 복도쪽
  · 홍길동 2행 / 홍길동 1열        → 그 줄·그 열에 배치
  · 이채현 1열 희망               → 가능하면 지키는 '희망' 조건(다 못 지키면 알려 줌)
  · 홍길동 맨뒤 금지             → 해당 영역 배치 금지
  · 홍길동 김철수 짝꿍           → 좌우 옆자리로 붙이기
  · 홍길동 김철수 분리           → 기본 2칸 이상 떨어뜨리기
  · 홍길동 김철수 3칸 이상 떨어뜨리기
  · 홍길동 김철수 이영희 서로 다른 분단
  · 남녀 짝                      → 같은 분단 좌우 짝을 남녀로
  · 1행 1열 빈자리               → 그 칸은 사용하지 않음
  · {"종류": "분리", "대상들": ["홍길동", "김철수"], "최소거리": 3}   ← JSON 직접 입력

좌표 약속: 1행 = 교탁과 가장 가까운 맨 앞줄, 1열 = 칠판을 볼 때 가장 왼쪽."""


# ------------------------------------------------------------------ 메인 --

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="조건에 맞춰 교실 자리를 배정합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--격자", metavar="가로x세로", help="예: 6x5 (가로 6칸, 세로 5칸)")
    ap.add_argument("--격자재설정", action="store_true", help="1년 전이라도 격자를 다시 묻는다")
    ap.add_argument("--학생", metavar="파일", help="명단 텍스트 파일 ('-' 는 표준입력)")
    ap.add_argument("--학생수", type=int, metavar="N", help="이름 없이 번호만으로 N명 등록")
    ap.add_argument("--조건추가", action="append", default=[], metavar="문장")
    ap.add_argument("--조건삭제", action="append", default=[], metavar="번호")
    ap.add_argument("--조건비우기", action="store_true")
    ap.add_argument("--조건목록", action="store_true")
    ap.add_argument("--창가", choices=["왼쪽", "오른쪽"], help="창가가 어느 쪽인지")
    ap.add_argument("--보기", choices=["교사시점", "학생시점"],
                    help="배치표를 그리는 방향 (기본: 교사시점 — 교탁에서 학생을 바라본 방향)")
    ap.add_argument("--배치", action="store_true", help="질문 없이 배치를 만들고 저장한다")
    ap.add_argument("--최소수정", action="store_true",
                    help="지난 배치를 최대한 유지한 채 어긋난 조건만 고친다")
    ap.add_argument("--교환", action="append", default=[], metavar="\"이름1 이름2\"",
                    help="지난 배치에서 두 학생 자리를 맞바꾼다(--최소수정 과 함께 사용)")
    ap.add_argument("--씨드", type=int, metavar="N", help="같은 값이면 같은 배치가 나온다")
    ap.add_argument("--제목", metavar="제목", help="배치표 제목 (예: 3학년 7반 2학기)")
    ap.add_argument("--상태", action="store_true", help="저장된 설정을 보여 준다")
    ap.add_argument("--조건도움말", action="store_true")
    ap.add_argument("--설정", metavar="경로", help="설정 파일 경로 (기본: 자리배정/데이터/settings.json)")
    ap.add_argument("--출력", metavar="경로", help="배치표 저장 폴더 (기본: 자리배정/출력)")
    return ap


def main(argv: list[str] | None = None) -> int:
    global SETTINGS_PATH, OUT_DIR
    args = build_parser().parse_args(argv)

    if args.조건도움말:
        알림(조건도움말())
        return 0
    if args.설정:
        SETTINGS_PATH = Path(args.설정).expanduser().resolve()
    if args.출력:
        OUT_DIR = Path(args.출력).expanduser().resolve()

    settings = E.load_settings(SETTINGS_PATH)
    변경 = False

    # --- 옵션으로 들어온 설정 반영 -------------------------------------
    if args.격자:
        m = re.fullmatch(r"\s*(\d+)\s*[xX×*]\s*(\d+)\s*", args.격자)
        if not m:
            알림("--격자 는 '가로x세로' 형식입니다. 예: 6x5")
            return 2
        E.set_grid(settings, int(m.group(1)), int(m.group(2)))
        변경 = True
    if args.창가:
        settings.setdefault("교실", {})["창가"] = args.창가
        변경 = True
    if args.보기:
        settings.setdefault("교실", {})["보기"] = args.보기
        변경 = True
    if args.학생:
        글 = sys.stdin.read() if args.학생 == "-" else \
            Path(args.학생).read_text(encoding="utf-8")
        settings["학생"] = E.parse_students(글)
        변경 = True
    if args.학생수:
        settings["학생"] = E.numbered_students(args.학생수)
        변경 = True
    if args.조건비우기:
        settings["조건"] = []
        settings["조건_수정일"] = date.today().isoformat()
        변경 = True
    for 문장 in args.조건추가:
        이름들 = [s["이름"] for s in settings.get("학생", [])]
        settings.setdefault("조건", []).append(E.parse_rule(문장, 이름들))
        settings["조건_수정일"] = date.today().isoformat()
        변경 = True
    if args.조건삭제:
        번호들 = sorted({int(n) for arg in args.조건삭제 for n in re.findall(r"\d+", arg)},
                      reverse=True)
        for n in 번호들:
            if 1 <= n <= len(settings.get("조건", [])):
                settings["조건"].pop(n - 1)
        settings["조건_수정일"] = date.today().isoformat()
        변경 = True
    if 변경:
        E.save_settings(SETTINGS_PATH, settings)

    if args.상태 or args.조건목록:
        if E.grid_is_valid(settings):
            rows, cols = E.grid_size(settings)
            알림(f"격자: 가로 {cols}칸 × 세로 {rows}칸 (설정일 {settings['격자']['설정일']})")
        else:
            알림("격자: 미설정(또는 1년 경과) — 다시 물어봐야 합니다.")
        알림(f"학생: {len(settings.get('학생') or [])}명")
        조건출력(settings)
        if args.상태:
            알림(f"설정 파일: {SETTINGS_PATH}")
        return 0

    # --- 1~2단계: 격자 --------------------------------------------------
    격자단계(settings, 강제질문=args.격자재설정)
    명단단계(settings)
    E.save_settings(SETTINGS_PATH, settings)

    # --- 3~4단계: 조건 --------------------------------------------------
    조건단계(settings)
    E.save_settings(SETTINGS_PATH, settings)

    # --- 5단계: 배치 그림 + 수정 여부 ------------------------------------
    씨드 = args.씨드
    바뀐사람 = []
    if args.최소수정 or args.교환:
        이전 = (settings.get("최근배치") or {}).get("자리")
        if not 이전:
            알림("지난 배치 기록이 없어 처음부터 배치합니다.")
            배치, 미충족 = 배치생성(settings, seed=씨드)
        else:
            기존배치 = {이름: tuple(자리) for 이름, 자리 in 이전.items()}
            이름들 = [x["이름"] for x in settings["학생"]]
            for 짝 in args.교환:
                고른이름 = [n for n in 이름들 if n in 짝]
                if len(고른이름) != 2:
                    알림(f"  ! 교환할 두 학생을 찾지 못했습니다: {짝}")
                    return 2
                a, b = 고른이름
                기존배치[a], 기존배치[b] = 기존배치[b], 기존배치[a]
                알림(f"교환: {a} ↔ {b}")
            배치, 미충족, 바뀐사람 = E.repair_detail(settings, 기존배치, seed=씨드)
            제목줄("지난 배치에서 바뀐 자리")
            알림(", ".join(바뀐사람) if 바뀐사람 else "(교환 외에 옮긴 학생 없음)")
    else:
        배치, 미충족 = 배치생성(settings, seed=씨드)
    배치보여주기(settings, 배치, args.제목, 미충족)

    if 대화가능() and not args.배치:
        while 예아니오("배치를 수정할까요?"):
            알림("  1) 다시 섞기   2) 조건 수정 후 다시 배치   "
                 "3) 두 학생 자리 맞바꾸기   0) 이대로 확정")
            선택 = 물음("  선택: ", "0")
            if 선택 == "1":
                씨드 = None if 씨드 is None else 씨드 + 1
                배치, 미충족 = 배치생성(settings, seed=씨드)
            elif 선택 == "2":
                조건단계(settings)
                E.save_settings(SETTINGS_PATH, settings)
                배치, 미충족 = 배치생성(settings, seed=씨드)
            elif 선택 == "3":
                자리맞바꾸기(settings, 배치)
            else:
                break
            배치보여주기(settings, 배치, args.제목, 미충족)

    # --- 6단계: 확정 -----------------------------------------------------
    확정단계(settings, 배치)
    알림()
    알림("완료.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:      # head 등으로 출력을 끊었을 때
        sys.stderr.close()
        raise SystemExit(0)
    except KeyboardInterrupt:
        알림()
        알림("중단했습니다. (저장된 격자·조건은 그대로 남아 있습니다)")
        raise SystemExit(130)
