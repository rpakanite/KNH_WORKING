"""HWP(한글 5.0) 본문을 글자 색 정보와 함께 추출한다.

Drive의 .hwp 학습지·답지·학생 제출물은 read_file_content로 읽을 수 없으므로
download_file_content로 받은 뒤 이 스크립트로 텍스트를 뽑는다.

글자 색이 중요한 이유: 이 학급의 선택형 문항(예: `( O, X )`)은 학생이 ○를 치지 않고
(가) 오답 보기를 지워 정답만 남기거나 (나) 정답 보기의 글자 색만 바꾸는 방식으로 답한다.
빈 학습지의 해당 선택지는 모두 검은색이므로 **검은색이 아닌 글자 = 학생이 고른 답**이다.
답지도 같은 방식(파란색)으로 정답을 표시해 두었다.

사용법:
    python3 hwp_extract.py 파일.hwp            # 색 표시를 [#RRGGBB]...[/] 로 감싼 텍스트
    python3 hwp_extract.py 파일.hwp --plain    # 색 없이 본문만
"""
import sys, zlib, struct, olefile

CHAR_SHAPE, PARA_TEXT, PARA_CHAR_SHAPE = 21, 67, 68
EXT_CTRL = {1,2,3,11,12,14,15,16,17,18,21,22,23}   # 8 wchar 차지하는 확장 제어문자

def records(data):
    i, n = 0, len(data)
    while i < n - 4:
        h = struct.unpack_from('<I', data, i)[0]
        tag, ln = h & 0x3FF, (h >> 20) & 0xFFF
        i += 4
        if ln == 0xFFF:
            ln = struct.unpack_from('<I', data, i)[0]; i += 4
        yield tag, data[i:i+ln]
        i += ln

def stream(ole, name, compressed):
    d = ole.openstream(name).read()
    return zlib.decompress(d, -15) if compressed else d

def char_colors(docinfo):
    """charShapeId -> (r,g,b).
    CHAR_SHAPE 레이아웃: 글꼴ID WORD[7]=14, 장평 UINT8[7]=7, 자간 INT8[7]=7,
    상대크기 UINT8[7]=7, 글자위치 INT8[7]=7 → 42, 기준크기 INT32 → 46,
    속성 UINT32 → 50, 그림자간격 X/Y INT8 2개 → 52, 글자색 COLORREF."""
    out, idx = {}, 0
    for tag, body in records(docinfo):
        if tag == CHAR_SHAPE:
            if len(body) >= 56:
                c = struct.unpack_from('<I', body, 52)[0]
                out[idx] = (c & 0xFF, (c >> 8) & 0xFF, (c >> 16) & 0xFF)
            idx += 1
    return out

def para_chars(buf):
    """PARA_TEXT -> [(wchar위치, 글자)]"""
    res, j = [], 0
    while j + 1 < len(buf):
        code = struct.unpack_from('<H', buf, j)[0]
        pos = j // 2
        if code in (10, 13):
            res.append((pos, '\n')); j += 2
        elif code == 9:
            res.append((pos, '\t')); j += 2
        elif code < 32:
            j += 16 if code in EXT_CTRL else 2
        else:
            res.append((pos, chr(code))); j += 2
    return res

def runs(shape_body):
    """PARA_CHAR_SHAPE -> [(시작위치, charShapeId)]"""
    return [struct.unpack_from('<II', shape_body, k) for k in range(0, len(shape_body) - 7, 8)]

def extract(path):
    ole = olefile.OleFileIO(path)
    compressed = bool(ole.openstream('FileHeader').read()[36] & 1)
    colors = char_colors(stream(ole, 'DocInfo', compressed))
    paras, cur = [], None
    for s in sorted([x for x in ole.listdir() if x[0] == 'BodyText'],
                    key=lambda x: int(x[1].replace('Section', ''))):
        for tag, body in records(stream(ole, s, compressed)):
            if tag == PARA_TEXT:
                cur = para_chars(body)
            elif tag == PARA_CHAR_SHAPE and cur is not None:
                paras.append((cur, runs(body))); cur = None
    ole.close()
    return paras, colors

def colored_text(paras, colors, default=(0, 0, 0)):
    """검은색이 아닌 글자를 [색]...[/] 로 표시한 텍스트를 만든다."""
    out = []
    for chars, rs in paras:
        line, prev = [], default
        for pos, ch in chars:
            sid = 0
            for start, s in rs:
                if pos >= start: sid = s
                else: break
            col = colors.get(sid, default)
            if col != prev:
                if prev != default: line.append('[/]')
                if col != default: line.append(f'[#{col[0]:02X}{col[1]:02X}{col[2]:02X}]')
                prev = col
            line.append(ch)
        if prev != default: line.append('[/]')
        out.append(''.join(line))
    return '\n'.join(out)

def plain_text(paras):
    return '\n'.join(''.join(ch for _, ch in chars) for chars, _ in paras)


if __name__ == '__main__':
    paras, colors = extract(sys.argv[1])
    if '--plain' in sys.argv:
        print(plain_text(paras))
    else:
        used = sorted({c for c in colors.values()})
        print(f"# 문단 {len(paras)}개 / CharShape {len(colors)}개 / 사용된 색: {used}\n",
              file=sys.stderr)
        print(colored_text(paras, colors))
