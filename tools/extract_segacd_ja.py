#!/usr/bin/env python3
"""DEPRECATED — assumed Shift-JIS, which is now DISPROVEN.

`tools/segacd_encoding_probe.py` shows the RD*.SD4 text is NOT Shift-JIS (max 12.5% /
median 1.0% hiragana vs ~40% for real prose) — it is a custom glyph-index encoding
interleaved with 1-byte script opcodes. This SJIS extractor therefore over-extracts noise.
Kept only for reference; see docs/SEGACD_RE_NOTES.md for the correct decode roadmap.

Extract Japanese dialogue units from Sega CD RD*.SD4 scene scripts.
Scans the script section (>=0x10000), pulls Shift-JIS runs, merges runs split only
by short control bytes (in-line line breaks) into dialogue units. Output is LOCAL
(segacd_ja/ja_raw.json, gitignored) for translate+align — never printed."""
import glob, os, json, struct, sys

def is_sjis(b, t):
    return (0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef) and (0x40 <= t <= 0x7e or 0x80 <= t <= 0xfc)

def extract_units(d, base=0x10000, min_chars=4, max_gap=3):
    seg = d[base:]
    n = len(seg)
    runs = []  # (start, end) byte offsets of SJIS runs
    i = 0
    while i < n - 1:
        if is_sjis(seg[i], seg[i+1]) or 0xa1 <= seg[i] <= 0xdf:
            s = i; ch = 0
            while i < n - 1 and (is_sjis(seg[i], seg[i+1]) or 0xa1 <= seg[i] <= 0xdf):
                i += 2 if is_sjis(seg[i], seg[i+1]) else 1; ch += 1
            if ch >= 2:
                runs.append((s, i, ch))
        else:
            i += 1
    # merge runs separated by <= max_gap control bytes (line breaks within one dialogue)
    units = []
    cur = None
    for s, e, ch in runs:
        if cur and s - cur[1] <= max_gap:
            cur = (cur[0], e, cur[2] + ch)
        else:
            if cur and cur[2] >= min_chars: units.append(cur)
            cur = (s, e, ch)
    if cur and cur[2] >= min_chars: units.append(cur)
    out = []
    for s, e, ch in units:
        try:
            txt = seg[s:e].decode('shift_jis', 'ignore')
            if sum(1 for c in txt if '぀' <= c <= 'ヿ' or '一' <= c <= '鿿') >= min_chars:
                out.append(txt)
        except Exception:
            pass
    return out

def main():
    fs = sorted(glob.glob('segacd_ja/files/RD*.SD4'))
    allunits = {}
    total = 0
    for f in fs:
        d = open(f, 'rb').read()
        if len(d) < 0x10000: continue
        units = extract_units(d)
        if units:
            allunits[os.path.basename(f)] = units
            total += len(units)
    json.dump(allunits, open('segacd_ja/ja_raw.json', 'w'), ensure_ascii=False)
    print(f"# {len(allunits)} RD files, {total} Japanese dialogue units -> segacd_ja/ja_raw.json", file=sys.stderr)

if __name__ == '__main__':
    main()
