#!/usr/bin/env python3
"""Build a Shift-JIS-indexed 24x24 bitmap Japanese font for the patched dgds engine (kDispJA).

Same DCJK container as build_cjk_font.py but encoding=1 (Shift-JIS) and the glyph index is
sjis_linear(lead, trail). The whisper-transcribed JP subtitles (ja.dtr) are Shift-JIS encoded;
the engine reads SJIS double-byte and looks the glyph up here. Rendered from Noto Sans CJK JP.

SJIS double-byte: lead 0x81-0x9F | 0xE0-0xFC (60 leads); trail 0x40-0x7E | 0x80-0xFC (189, no 0x7F).
  index = leadoff*189 + trailoff   (max 60*189 = 11340)
"""
import struct, argparse, sys
import freetype

PER_LEAD = 189
NUM_GLYPHS = 60 * PER_LEAD  # 11340

def lead_off(lead):
    if 0x81 <= lead <= 0x9F: return lead - 0x81          # 0..30
    if 0xE0 <= lead <= 0xFC: return 31 + (lead - 0xE0)    # 31..59
    return -1

def trail_off(trail):
    if 0x40 <= trail <= 0x7E: return trail - 0x40          # 0..62
    if 0x80 <= trail <= 0xFC: return 63 + (trail - 0x80)   # 63..188
    return -1

def sjis_index(lead, trail):
    lo, to = lead_off(lead), trail_off(trail)
    if lo < 0 or to < 0: return -1
    return lo * PER_LEAD + to

def render_glyph(face, ch, width, height, bpr):
    out = bytearray(bpr * height)
    try:
        face.load_char(ch, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
    except Exception:
        return out
    bmp = face.glyph.bitmap
    bw, bh, pitch = bmp.width, bmp.rows, bmp.pitch
    ox = max(0, (width - bw) // 2)   # CJK hi-res: center the ink in the cell
    oy = max(0, (height - bh) // 2)
    for ry in range(bh):
        ty = oy + ry
        if ty < 0 or ty >= height: continue
        for rx in range(bw):
            tx = ox + rx
            if tx < 0 or tx >= width: continue
            if bmp.buffer[ry * pitch + (rx >> 3)] & (0x80 >> (rx & 7)):
                out[ty * bpr + (tx >> 3)] |= (0x80 >> (tx & 7))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=24)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    w = h = args.size
    bpr = (w + 7) // 8
    face = freetype.Face('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', index=0)  # Noto Sans CJK JP
    face.set_pixel_sizes(0, w)
    data = bytearray(b'DCJK' + struct.pack('<BBBBBxx I', 1, w, h, bpr, 1, NUM_GLYPHS))  # encoding=1 (SJIS)
    blank = bytes(bpr * h)
    glyphs = [blank] * NUM_GLYPHS
    rendered = 0
    for lead in list(range(0x81, 0xA0)) + list(range(0xE0, 0xFD)):
        for trail in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            idx = sjis_index(lead, trail)
            if idx < 0: continue
            try:
                ch = bytes([lead, trail]).decode('shift_jis')
            except Exception:
                continue
            if not ch or ord(ch) < 0x80: continue
            g = render_glyph(face, ch, w, h, bpr)
            if any(g):
                glyphs[idx] = bytes(g); rendered += 1
    for g in glyphs: data += g
    open(args.out, 'wb').write(data)
    print(f"# wrote {args.out}: {w}x{h}, {NUM_GLYPHS} slots, {rendered} rendered, {len(data)} bytes", file=sys.stderr)

if __name__ == '__main__':
    main()
