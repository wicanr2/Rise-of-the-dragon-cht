#!/usr/bin/env python3
"""Build a Big5-indexed bitmap CJK font for the patched dgds engine.

Output format (little-endian), read directly by the engine patch:
  magic   "DCJK"           (4 bytes)
  version u8 = 1
  width   u8   (e.g. 12)
  height  u8   (e.g. 12)
  bytesPerRow u8 = (width+7)//8
  encoding u8  (0 = Big5 linear index)
  reserved u8 x2
  numGlyphs u32
  glyphs[ numGlyphs * (bytesPerRow*height) ]  -- 1bpp, MSB-first per row

Glyph index = big5_linear(lead, trail):
  lead  0x81..0xFE  (126 leads)
  trail 0x40..0x7E (offset 0..62) | 0xA1..0xFE (offset 63..156)  -> 157 per lead
  index = (lead-0x81)*157 + trailoffset      (max 126*157 = 19782)
"""
import struct, argparse, sys
import freetype

LEAD_LO, LEAD_HI = 0x81, 0xFE
PER_LEAD = 157
NUM_GLYPHS = (LEAD_HI - LEAD_LO + 1) * PER_LEAD  # 19782

def trail_offset(trail):
    if 0x40 <= trail <= 0x7E: return trail - 0x40        # 0..62
    if 0xA1 <= trail <= 0xFE: return 63 + (trail - 0xA1)  # 63..156
    return -1

def big5_index(lead, trail):
    to = trail_offset(trail)
    if not (LEAD_LO <= lead <= LEAD_HI) or to < 0: return -1
    return (lead - LEAD_LO) * PER_LEAD + to

def make_renderer(size):
    if size <= 14:
        face = freetype.Face('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', index=2)  # Zen Hei Sharp (embedded bitmap)
    else:
        face = freetype.Face('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', index=0)
    face.set_pixel_sizes(0, size)
    return face

def render_glyph(face, ch, width, height, bpr):
    """Return bytesPerRow*height bytes, 1bpp MSB-first, glyph baseline-positioned."""
    out = bytearray(bpr * height)
    try:
        face.load_char(ch, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
    except Exception:
        return out
    bmp = face.glyph.bitmap
    bw, bh, pitch = bmp.width, bmp.rows, bmp.pitch
    # position: left = bitmap_left, top baseline ~ size*0.8; center if smaller
    top = face.size.ascender >> 6
    ox = max(0, face.glyph.bitmap_left)
    oy = top - face.glyph.bitmap_top
    # clamp into cell
    for ry in range(bh):
        ty = oy + ry
        if ty < 0 or ty >= height: continue
        for rx in range(bw):
            tx = ox + rx
            if tx < 0 or tx >= width: continue
            byte = bmp.buffer[ry*pitch + (rx>>3)]
            if byte & (0x80 >> (rx & 7)):
                out[ty*bpr + (tx>>3)] |= (0x80 >> (tx & 7))
    return out

def preview(face, text, width, height, bpr):
    for ch in text:
        g = render_glyph(face, ch, width, height, bpr)
        b = ch.encode('big5','replace')
        idx = big5_index(b[0], b[1]) if len(b)==2 else -1
        print(f"--- {ch!r}  big5={b.hex()}  idx={idx} ---")
        for ry in range(height):
            row = ''.join('█' if g[ry*bpr+(x>>3)] & (0x80>>(x&7)) else '·' for x in range(width))
            print(row)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=12)
    ap.add_argument('--out')
    ap.add_argument('--preview')
    args = ap.parse_args()
    w = h = args.size
    bpr = (w + 7)//8
    face = make_renderer(args.size)
    if args.preview:
        preview(face, args.preview, w, h, bpr); return
    # full Big5 font
    data = bytearray()
    data += b'DCJK' + struct.pack('<BBBBBxx I', 1, w, h, bpr, 0, NUM_GLYPHS)
    blank = bytes(bpr*h)
    glyphs = [blank]*NUM_GLYPHS
    rendered = 0
    for lead in range(LEAD_LO, LEAD_HI+1):
        for trail in list(range(0x40,0x7F))+list(range(0xA1,0xFF)):
            idx = big5_index(lead, trail)
            try:
                ch = bytes([lead,trail]).decode('big5')
            except Exception:
                continue
            if not ch or ord(ch) < 0x80: continue
            g = render_glyph(face, ch, w, h, bpr)
            if any(g):
                glyphs[idx] = bytes(g); rendered += 1
    for g in glyphs: data += g
    with open(args.out,'wb') as f: f.write(data)
    print(f"# wrote {args.out}: {w}x{h}, {NUM_GLYPHS} slots, {rendered} rendered, {len(data)} bytes", file=sys.stderr)

if __name__=='__main__': main()
