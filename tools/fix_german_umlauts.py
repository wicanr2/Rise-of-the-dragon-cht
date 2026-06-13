#!/usr/bin/env python3
"""Rebuild de.dtr substituting German umlauts -> ASCII digraphs so they render with the
English DRAGON.FNT (which lacks ä/ö/ü/ß glyphs -> they showed blank). Faithful repack:
reads the existing de.dtr, only transforms the text, preserves DTRN format/keys/lang.

  ä->ae ö->oe ü->ue Ä->Ae Ö->Oe Ü->Ue ß->ss

Usage: fix_german_umlauts.py in.dtr out.dtr
"""
import struct, sys

SUB = {'ä':'ae','ö':'oe','ü':'ue','Ä':'Ae','Ö':'Oe','Ü':'Ue','ß':'ss',
       'á':'a','é':'e','è':'e','ê':'e','à':'a','ç':'c','î':'i','ô':'o','û':'u','â':'a'}

def main():
    inp, out = sys.argv[1], sys.argv[2]
    d = open(inp, 'rb').read()
    assert d[:4] == b'DTRN', d[:4]
    ver, lang, pad, count = struct.unpack('<BBHI', d[4:12])
    off = 12
    items = []
    changed = 0
    for _ in range(count):
        kl = struct.unpack('<H', d[off:off+2])[0]; off += 2
        key = d[off:off+kl]; off += kl
        vl = struct.unpack('<H', d[off:off+2])[0]; off += 2
        val = d[off:off+vl]; off += vl
        txt = val.decode('cp437', 'replace')
        new = ''.join(SUB.get(c, c) for c in txt)
        if new != txt:
            changed += 1
        # after substitution the text is pure ASCII/Latin-1; cp437 keeps ASCII identical
        items.append((key, new.encode('cp437', 'replace')))
    buf = bytearray(b'DTRN') + struct.pack('<BBHI', ver, lang, 0, len(items))
    for key, vb in items:
        buf += struct.pack('<H', len(key)) + key + struct.pack('<H', len(vb)) + vb
    open(out, 'wb').write(buf)
    print(f"# {out}: {len(items)} entries, {changed} had umlauts substituted, {len(buf)} bytes")

if __name__ == '__main__':
    main()
