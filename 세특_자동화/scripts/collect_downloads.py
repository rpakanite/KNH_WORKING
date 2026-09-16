#!/usr/bin/env python3
"""Drive download_file_content 결과(도구 결과 파일)를 학생별 원본으로 풀어 놓는다.

.hwp 등은 read_file_content로 못 읽어 download_file_content를 쓰는데, base64가 커서
도구 결과가 파일로 저장된다. 그 파일들을 훑어 roster.json의 file_id와 맞추고
`{반}/{학번}_{이름}.{확장자}` 로 저장한다. 이미 저장된 학생은 건너뛴다.

사용법:  python3 collect_downloads.py <도구결과디렉터리> <roster.json> <출력디렉터리>
"""
import base64
import json
import pathlib
import sys

EXT = {"application/pdf": "pdf", "application/haansofthwpx": "hwpx",
       "application/haansofthwp": "hwp", "application/x-hwp": "hwp"}


def main(results_dir, roster_path, out_dir):
    roster = json.loads(pathlib.Path(roster_path).read_text(encoding="utf-8"))
    want = {fid: (cls, sid, name)
            for cls, students in roster.items()
            for sid, (name, fid) in students.items()}

    saved, seen = {}, set()
    for f in sorted(pathlib.Path(results_dir).glob("*download_file_content*.txt")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        fid = d.get("id")
        if fid not in want:
            continue
        cls, sid, name = want[fid]
        ext = EXT.get(d.get("mimeType")) or d["title"].rsplit(".", 1)[-1].lower()
        dest = pathlib.Path(out_dir) / cls / f"{sid}_{name}.{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(d["content"]))
        saved.setdefault(cls, []).append(sid)
        seen.add(fid)

    for cls in sorted(roster, key=lambda c: int(c.replace("반", ""))):
        got = sorted(saved.get(cls, []))
        miss = sorted(set(roster[cls]) - set(got))
        print(f"{cls}: 저장 {len(got)}/{len(roster[cls])}" + (f" | 미수신 {miss}" if miss else ""))
    total_missing = sum(len(set(v) - set(saved.get(c, []))) for c, v in roster.items())
    print(f"총 미수신 {total_missing}건")


if __name__ == "__main__":
    main(*sys.argv[1:4])
