#!/usr/bin/env python3
"""빈 학습지와 제출물을 글자 단위로 맞대어 각 빈칸 '( )'에 들어간 글자를 뽑는다.

빈칸이 수십 개인 학습지는 칸마다 앞말·뒷말을 정해 두기 어렵다. 빈 학습지에서 공백을
지우면 빈칸은 '()'로 남으므로, 제출물과 맞대어(difflib) 그 '('와 ')'가 제출물의 어디로
옮겨 갔는지 찾고 그 사이 글자를 학생의 답으로 본다. 학생이 괄호를 지웠으면 그 자리에
끼워진 글자를 대신 쓴다.
"""
import difflib
import re

DECOR = "⇨⇧⇩↔→←•󰄤"


def compact(s):
    return re.sub(r"\s+", "", s).translate({ord(c): None for c in DECOR})


def blank_positions(tpl):
    """빈 학습지(공백 제거본)에서 빈칸 '()'의 '(' 위치 목록."""
    return [m.start() for m in re.finditer(r"\(\)", tpl)]


def fills(tpl, doc):
    """빈칸마다 (제출물에서 찾은 글자, 찾은 방식) 목록을 돌려준다."""
    sm = difflib.SequenceMatcher(None, tpl, doc, autojunk=False)
    amap = {}                                   # 빈 학습지 위치 → 제출물 위치(같은 글자일 때만)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            amap[a + k] = b + k
    ops = sm.get_opcodes()
    out = []
    for p in blank_positions(tpl):
        lo, hi = amap.get(p), amap.get(p + 1)
        if lo is not None and hi is not None and hi > lo:
            out.append((doc[lo + 1:hi], "괄호"))
            continue
        # 괄호가 지워졌거나 어긋난 경우: 그 위치를 덮는 바뀐 구간의 글자를 쓴다
        seg = next(((j1, j2) for tag, i1, i2, j1, j2 in ops
                     if tag != "equal" and i1 <= p + 1 and i2 >= p), None)
        if seg:
            txt = doc[seg[0]:seg[1]].strip("()")
            out.append((txt, "보정"))
        else:
            out.append(("", "없음"))
    return out
