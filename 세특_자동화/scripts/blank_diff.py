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
BOX = r"\(([^()]{0,40})\)"            # 학생이 채운 빈칸 하나


def compact(s):
    return re.sub(r"\s+", "", s).translate({ord(c): None for c in DECOR})


def blank_positions(tpl):
    """빈 학습지(공백 제거본)에서 빈칸 '()'의 '(' 위치 목록."""
    return [m.start() for m in re.finditer(r"\(\)", tpl)]


def _context(tpl, p, k, side):
    """빈칸 p의 앞(side=-1)이나 뒤(side=1) 글자 k개를 정규식으로 만든다.

    문맥 안에 다른 빈칸 '()'이 끼어 있으면 그 칸은 '학생이 채운 아무 글자'로 둔다.
    """
    units, i = [], (p - 1 if side < 0 else p + 2)
    while len(units) < k and 0 <= i < len(tpl):
        if side < 0 and tpl[i] == ")" and i > 0 and tpl[i - 1] == "(":
            units.append(r"\([^()]{0,40}\)")
            i -= 2
        elif side > 0 and tpl[i] == "(" and i + 1 < len(tpl) and tpl[i + 1] == ")":
            units.append(r"\([^()]{0,40}\)")
            i += 2
        else:
            units.append(re.escape(tpl[i]))
            i += side
    return "".join(reversed(units) if side < 0 else units)


def _hits(pat, doc, claimed=()):
    """pat에 맞는 '(…)' 중 아직 다른 칸이 차지하지 않은 것들 — [(글자, 시작 위치)]."""
    return [(m.group(1), m.start(1)) for m in re.finditer(pat, doc) if m.start(1) not in claimed]


def anchored(tpl, doc, p, k=8):
    """앞뒤 문맥이 빈 학습지와 똑같은 '(…)'가 제출물에 딱 한 곳 있으면 (글자, 위치).

    PDF는 표 칸을 읽는 순서가 원본과 달라 글 덩어리가 자리를 바꾸기도 하는데,
    그러면 순서대로 맞대는 diff가 엉뚱한 칸을 짝짓는다. 앞뒤 문맥으로 찾으면
    덩어리 순서와 상관없이 제자리를 찾는다.
    """
    pat = _context(tpl, p, k, -1) + BOX + _context(tpl, p, k, 1)
    hits = _hits(pat, doc)
    return hits[0] if len(hits) == 1 else None


def _lit(tpl, p, side, k, known):
    """빈칸 p 앞(side=-1)·뒤(side=1) 글자 k개를 문자열 그대로. 다른 빈칸을 만나면, 이미
    읽어 낸 칸이면 그 답을 넣어 이어 가고, 아직 모르는 칸이면 거기서 멈춘다."""
    out, i, n = [], (p - 1 if side < 0 else p + 2), 0
    while n < k and 0 <= i < len(tpl):
        q = i - 1 if side < 0 else i          # 빈칸 '()'의 '(' 위치
        if 0 <= q and q + 1 < len(tpl) and tpl[q] == "(" and tpl[q + 1] == ")":
            if q not in known:
                break
            out.append("(" + known[q] + ")")
            i = q - 1 if side < 0 else q + 2
        else:
            out.append(tpl[i])
            i += side
        n += 1
    return "".join(reversed(out) if side < 0 else out)


def chained(tpl, doc, p, known, claimed):
    """덩어리 경계에 걸린 칸 — 이웃 칸의 답까지 문맥에 넣어 한쪽 문맥만으로 찾는다.

    긴 문맥부터 줄여 가며, 다른 칸이 아직 차지하지 않은 '(…)' 하나로 정해질 때만
    (글자, 위치, 문맥 길이)를 돌려준다. 그래도 안 되면 빈칸과 문맥 사이에 다른 글
    (괄호 없는 20자 이내)이 끼어든 경우까지 본다.
    """
    for k in range(12, 1, -1):
        for side in (-1, 1):
            c = _lit(tpl, p, side, k, known)
            if len(c) < k:
                continue
            pat = re.escape(c) + BOX if side < 0 else BOX + re.escape(c)
            hits = _hits(pat, doc, claimed)
            if len(hits) == 1:
                return hits[0] + (k,)
    for side in (1, -1):                       # 사이에 다른 글이 끼어든 경우
        c = _lit(tpl, p, side, 10, known)
        if len(c) < 10:
            continue
        gap = r"[^()]{0,20}"
        pat = (re.escape(c) + gap + BOX) if side < 0 else (BOX + gap + re.escape(c))
        hits = _hits(pat, doc, claimed)
        if len(hits) == 1:
            return hits[0] + (0,)
    return None


def fills(tpl, doc):
    """빈칸마다 (제출물에서 찾은 글자, 찾은 방식) 목록을 돌려준다."""
    sm = difflib.SequenceMatcher(None, tpl, doc, autojunk=False)
    amap = {}                                   # 빈 학습지 위치 → 제출물 위치(같은 글자일 때만)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            amap[a + k] = b + k
    pos = blank_positions(tpl)
    res, at = {}, {}                            # 칸 → (글자, 방식) / 칸 → 제출물 위치
    # 1) 앞뒤 문맥이 모두 맞는 곳
    for p in pos:
        hit = anchored(tpl, doc, p)
        if hit is not None:
            res[p], at[p] = (hit[0], "괄호"), hit[1]
    # 2) diff로 '('와 ')'가 모두 짝지어진 곳(사이에 다른 괄호가 끼면 어긋난 것)
    for p in pos:
        lo, hi = amap.get(p), amap.get(p + 1)
        if (p not in res and lo is not None and hi is not None and hi > lo
                and not re.search(r"[()]", doc[lo + 1:hi]) and lo + 1 not in at.values()):
            res[p], at[p] = (doc[lo + 1:hi], "괄호"), lo + 1
    # 3) 남은 칸: 이웃 칸 답을 문맥에 넣어 한쪽 문맥으로 찾는다. 두 칸이 같은 '(…)'를
    #    가리키면 문맥이 더 긴 쪽만 인정하고, 찾을 때마다 다시 돈다.
    while True:
        known = {q: v[0] for q, v in res.items()}
        claimed = set(at.values())
        cand = {}
        for p in pos:
            if p not in res:
                h = chained(tpl, doc, p, known, claimed)
                if h is not None:
                    cand[p] = h
        by_span = {}
        for p, h in cand.items():
            by_span.setdefault(h[1], []).append((h[2], p))
        took = False
        for span, lst in by_span.items():
            lst.sort(reverse=True)
            top = [q for k, q in lst if k == lst[0][0]]
            if len(top) > 1:                    # 같은 길이 문맥끼리 다투면, 이 자리 말고도 갈 곳이
                stay = [q for q in top          # 있는 칸은 비켜 주고 갈 곳이 없는 칸 하나만 인정
                        if chained(tpl, doc, q, known, claimed | {span}) is None]
                if len(stay) != 1:
                    continue
                top = stay
            p = top[0]
            res[p], at[p] = (cand[p][0], "괄호"), span
            took = True
        if not took:
            break
    # 4) 그래도 못 찾은 칸: 괄호가 지워진 것으로 보고 그 자리에 바뀐 글자를 쓴다
    ops = sm.get_opcodes()
    for p in pos:
        if p in res:
            continue
        seg = next(((j1, j2) for tag, i1, i2, j1, j2 in ops
                     if tag != "equal" and i1 <= p + 1 and i2 >= p), None)
        res[p] = (doc[seg[0]:seg[1]].strip("()"), "보정") if seg else ("", "없음")
    return [res[p] for p in pos]
