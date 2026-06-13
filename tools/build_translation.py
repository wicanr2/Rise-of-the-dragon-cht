#!/usr/bin/env python3
"""Pack a UTF-8 translation JSON into the engine's DTRN overlay (Big5-encoded).

Input JSON: { "<sceneNum>:<dialogNum>": "繁體中文 (\\r for line break)", ... }
Output DTRN (little-endian):
  "DTRN" u8 version=1  u8 lang  u16 pad  u32 count
  count * { u16 keyLen, key(ascii), u16 valLen, val(Big5 bytes) }
"""
import json, struct, sys, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json')
    ap.add_argument('out')
    ap.add_argument('--lang', type=int, default=1)  # 1=ZH
    args = ap.parse_args()
    d = json.load(open(args.json, encoding='utf-8'))
    items = []
    miss = 0
    for k, v in d.items():
        kb = k.encode('ascii')
        try:
            vb = v.encode('big5')
        except UnicodeEncodeError as e:
            # report which char failed; skip-encode replacement so build still works
            bad = v[e.start:e.end]
            print(f"  WARN {k}: char {bad!r} not in Big5; using '?'", file=sys.stderr)
            vb = v.encode('big5', 'replace'); miss += 1
        items.append((kb, vb))
    out = bytearray()
    out += b'DTRN' + struct.pack('<BBH I', 1, args.lang, 0, len(items))
    for kb, vb in items:
        out += struct.pack('<H', len(kb)) + kb + struct.pack('<H', len(vb)) + vb
    open(args.out, 'wb').write(out)
    print(f"# wrote {args.out}: {len(items)} entries, {miss} with missing glyphs, {len(out)} bytes", file=sys.stderr)

if __name__ == '__main__':
    main()
