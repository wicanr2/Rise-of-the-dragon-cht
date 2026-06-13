#!/usr/bin/env python3
"""Reproducible encoding probes for the Sega CD (Japan) ROTD script text.

Runs decisive pass/fail tests on the dialogue encoding of RD*.SD4 WITHOUT reproducing
any game content — it prints only category COUNTS / fractions. Real Japanese prose is
~40% hiragana, so hiragana fraction is a sharp signal for "is this readable Japanese?".

Findings recorded in docs/SEGACD_RE_NOTES.md (both hypotheses ELIMINATED):
  1. Shift-JIS            -> max 12.5% / median 1.0% hiragana  (not SJIS)
  2. 2-byte JIS-X-0208    -> 83-98% kanji at every base offset (noise signature)
Conclusion: custom glyph-index encoding, interleaved with 1-byte script opcodes.

Usage: python3 tools/segacd_encoding_probe.py [segacd_ja/files]   (disc data gitignored)
"""
import glob, os, sys, statistics
from collections import Counter

FILES_DIR = sys.argv[1] if len(sys.argv) > 1 else "segacd_ja/files"


def sjis_hiragana_scan(files):
    """Test 1: proper byte-synced Shift-JIS parse; report best hiragana fraction per file."""
    def categorize(d, start, end):
        i = start
        c = {"hira": 0, "kata": 0, "kanji": 0, "ascii": 0, "bad": 0}
        while i < end - 1:
            b = d[i]
            if 0x20 <= b < 0x7f:
                c["ascii"] += 1; i += 1; continue
            if 0xa1 <= b <= 0xdf:
                c["kata"] += 1; i += 1; continue  # half-width kana
            t = d[i + 1]
            if b == 0x82 and 0x9f <= t <= 0xf1:
                c["hira"] += 1; i += 2; continue
            if b == 0x83 and 0x40 <= t <= 0x96:
                c["kata"] += 1; i += 2; continue
            if (0x88 <= b <= 0x9f or 0xe0 <= b <= 0xea) and (0x40 <= t <= 0xfc and t != 0x7f):
                c["kanji"] += 1; i += 2; continue
            c["bad"] += 1; i += 1
        return c

    best = []
    for f in files:
        d = open(f, "rb").read()
        s = 0x10000 if len(d) > 0x10000 else 0
        bf = None
        for off in range(s, len(d) - 512, 256):
            c = categorize(d, off, off + 512)
            cjk = c["hira"] + c["kata"] + c["kanji"]
            if cjk < 20:
                continue
            frac = c["hira"] / cjk
            if bf is None or frac > bf:
                bf = frac
        if bf is not None:
            best.append(bf)
    if best:
        print(f"[Test 1: Shift-JIS]  files={len(best)}  "
              f"median best-hira={statistics.median(best)*100:.1f}%  max={max(best)*100:.1f}%")
        print("  -> real JP prose ~40%; this is noise-level => NOT Shift-JIS")


def jis_index_scan(files):
    """Test 2: interpret text as 2-byte BE indices in JIS X 0208 ku-ten order."""
    def idx_to_char(idx, base):
        n = idx - base
        if n < 0:
            return None
        ku, ten = n // 94 + 1, n % 94 + 1
        if not (1 <= ku <= 94 and 1 <= ten <= 94):
            return None
        try:
            return bytes([0xa0 + ku, 0xa0 + ten]).decode("euc_jp")
        except Exception:
            return None

    print("[Test 2: 2-byte BE JIS-X-0208 indices]")
    for base in (0, 1, 32, 188, 256, 282, 376):
        th = tj = tk = 0
        for f in files:
            d = open(f, "rb").read()
            s = 0x10000 if len(d) > 0x10000 else 0
            for i in range(s, min(len(d), s + 0x8000) - 1, 2):
                c = idx_to_char((d[i] << 8) | d[i + 1], base)
                if c is None:
                    continue
                if "぀" <= c <= "ゟ": th += 1
                elif "゠" <= c <= "ヿ": tk += 1
                elif "一" <= c <= "鿿": tj += 1
        cjk = th + tk + tj
        if cjk > 50:
            print(f"  base={base:4d}: hira={th/cjk*100:4.1f}% kata={tk/cjk*100:4.1f}% "
                  f"kanji={tj/cjk*100:4.1f}%  -> kanji-dominated = noise")


def highbyte_pairing(files):
    """Structural clue: BE16 high-byte freqs pair 0x0X<->0x8X (high bit = flag)."""
    hi = Counter()
    for f in files[:40]:
        d = open(f, "rb").read()
        s = 0x10000 if len(d) > 0x10000 else 0
        for i in range(s, min(len(d), s + 0x6000) - 1, 2):
            hi[d[i]] += 1
    print("[Structural] top BE16 high bytes (note 0x0X ~= 0x8X pairing, high bit = flag):")
    print("  " + "  ".join(f"0x{b:02x}:{c}" for b, c in hi.most_common(10)))


def zipf_framing(files):
    """Framing test: is the 2-byte-word stream language-like? Zipf concentration =
    top-20 codes' share of all in-range codes. Real JP text ~40-50%; noise ~uniform.
    Restricting even-aligned BE16 words to the valid index range [1,6144] yields a
    language-like ~41% with ~3700 distinct codes (consistent with VDP-nametable text;
    out-of-range words are control/attribute tokens). Caveat: doubled-byte fill runs
    (0x0101/0x0202 = blank-tile padding) still contaminate until the clean text
    sub-region is isolated per file."""
    in_range = Counter()
    for f in files:
        d = open(f, "rb").read()
        s = 0x10000 if len(d) > 0x10000 else 0
        seg = d[s:]
        for i in range(0, len(seg) - 1, 2):
            w = (seg[i] << 8) | seg[i + 1]
            if 1 <= w <= 6144:
                in_range[w] += 1
    tot = sum(in_range.values())
    if tot < 200:
        return
    top = sum(c for _, c in in_range.most_common(20))
    print(f"[Framing] BE16 words in [1,6144]: kept={tot} distinct={len(in_range)} "
          f"top20-concentration={top/tot*100:.1f}%  (language-like if >25%)")


def main():
    files = sorted(glob.glob(os.path.join(FILES_DIR, "RD*.SD4")))
    if not files:
        print(f"No RD*.SD4 under {FILES_DIR} (disc data is gitignored; run extract_segacd.sh first)")
        return
    sjis_hiragana_scan(files)
    jis_index_scan(files)
    highbyte_pairing(files)
    zipf_framing(files)


if __name__ == "__main__":
    main()
