# Sega CD (Japan) reverse-engineering notes

Working notes for extracting the official Japanese script from the Sega CD release
(`Rise of the Dragon (Japan).chd`). Structure only — no game content reproduced.

## Disc layout (verified)
- CHD → `chdman extractcd` → `disc.bin`/`disc.cue` (MODE1/2352 data + 4 Red Book audio).
- Track 1 = ISO9660 (System id `SEGA MEGA-DRIVE MEGA-CD`), 1299 files.
- Tracks 2–5 = CD audio (music) → `rotd_0[2-5].wav`.
- Tooling: `tools/extract_segacd.sh` (runs in Docker; output in gitignored `segacd_ja/`).

## File inventory
- `*.SD4` ×1010, `*.SD5` ×9, `*.SD6` ×8 — scene scripts. `RD*.SD4` (×765) carry dialogue.
- `*.CAT` ×208 — assets (named like PC scenes: BBATH, BCABINET, BHALL…).
- `*.BIN` ×57, `*.PCM` ×3 (digitized speech), `*.TXT` ×3, `*.ROM` ×1 (Mega-CD boot).

## `RD*.SD4` format (partially RE'd)
- **Big-endian** (68000). Header: `@0` BE u32 ≈ file size; `@4` another size; `@8` = `0xffff0000` marker; `@20` BE u32 = `0x10000` = offset to the text/script section.
- `0x00000..0x10000`: sprite/image data.
- `0x10000..EOF`: **scene script with dialogue embedded inline** (Shift-JIS), interleaved
  with bytecode + control bytes (0x00 heavy, plus 0x01–0x07). NOT a clean string table —
  null-splitting yields mostly non-text fragments. Dialogue is woven into script ops,
  same shape as the PC SDS (dialogue records inside the scene structure).
- Naming `RD<4digit><A|B|C>`: screen + sub-state. Range 0101..9999.

## Open problems (why this is a full sub-project)
1. **No reference**: ScummVM has no Sega CD ROTD engine. The PC RE relied on the engine
   source; here it must be inferred purely from the binary.
2. **Script-op RE**: must reverse the Sega CD scene-script opcodes to isolate dialogue
   records (length-prefix? op-tagged?) and the in-line control/formatting codes.
3. **Slot alignment**: `RD<screen>` ↔ PC `(scene,num)` is a different numbering system.
   Candidate bridges: the `.CAT` asset names (match PC scene names), or matching dialogue
   order/count per scene against `dialogs_en.json`. Unproven.

## Alignment — tested, no clean bridge (the crux blocker)
- Dialogue records in the script section are **position-prefixed** (small coord/index bytes
  before each run), NOT length-prefixed (1/702 runs matched a preceding length word).
- `.CAT` asset names match PC scene names, BUT `RD*.SD4` scripts do **not** reference asset
  filenames (0/30 sampled) — assets are referenced by index/ID, not name. So the asset-name
  bridge to PC `(scene,num)` does not work.
- Remaining alignment options are fuzzy/uncertain: order-matching dialogue sequences per
  screen against the PC English, or a hand-built screen→scene map. Neither proven.

**Assessment:** extracting the Japanese *text* is feasible; producing a *slot-aligned* ja.dtr
keyed by PC `(scene,num)` is a hard, uncertain, multi-session effort with no reference.
Pragmatic alternative: machine-translate EN→JA now for a working 日文 mode (kDispJA reserved),
and keep Sega CD official-Japanese as a dedicated future project using these notes.

## CRITICAL: text is custom-encoded, not Shift-JIS
- Decoding the dense `RD*.SD4` text region as Shift-JIS yields kanji + katakana but
  **zero hiragana** — impossible for real Japanese prose (which is hiragana-heavy). So the
  bytes are NOT SJIS; the dialogue is stored as **glyph indices into the game's own
  Japanese font** (standard practice for Sega CD JP games). The user's translate-and-match
  alignment idea still applies, but FIRST the text must be decoded from the custom encoding.
- `RE*.SD4/.SD5/.SD6` (×237) are a second variant set — NOT English (no English phrases),
  so no English-bridge shortcut.
- **Font candidate: `RISE.BIN` = 196608 B = 6144 × 32 B** = a 16×16 1bpp glyph table
  (6144 glyphs ≈ full JIS X 0208 set), 65% ink (consistent with a bitmap font). First-pass
  16×16 linear render didn't resolve into clean glyphs → wrong bit/plane order, or compressed.

## RISE.BIN font-format RE (in progress)
- Entropy **5.50 bits/byte** → structured (NOT compressed); good sign for a raw bitmap font.
- A 16×16 / 32-byte-per-glyph, JIS-ku-ten-ordered read from offset 0 does NOT yield clean
  glyphs in MSB or LSB bit order (a ~12-row periodicity appears) → the cell size, bit layout,
  OR the table's start offset is different; or RISE.BIN is the loaded program image with the
  font at an interior offset (not a clean glyph table from byte 0).
- **Next sub-task = systematic font detection:** scan RISE.BIN (and the .CAT/.BIN set) over
  candidate (offset, stride∈{18=12×12, 32=16×16, 72=24×24}, bit-order, planar?) and score
  each region for "font-likeness" (a blank SPACE glyph at the table head, then a plausible
  ink-density distribution, recognizable simple kana). Confirm by rendering a known kana.

## Font-region scan (numerical, no glyph reproduction)
- Scored all *.BIN/*.CAT/*.SD5 over 32-byte cells by avg horizontal bit-transitions per row
  (CJK strokes = smooth/long runs ≈ <2.6; code/random ≈ 7-8) + inky-cell fraction.
- Top candidates: `CHEN_VD.CAT @0x8000` (tr≈1.21), several `*SE.CAT @0x1a000` (tr≈1.62),
  `RD0201D.SD5 @0xa000`. **Caveat:** the smooth+inky heuristic also matches solid image
  regions (sprite/background fills), so these are candidates, not confirmed glyph tables.
- RISE.BIN scored worse → not a clean offset-0 font table (likely program image).
- **Resume here:** for each candidate region, render a strip and confirm it's a glyph grid
  (repeating cell pattern of kana/kanji-shaped marks) vs a single image; then identify the
  index→character mapping. This is the current frontier of the multi-week decode.

## Decisive encoding tests (counts only, no content reproduced)
Two hypotheses tested with hard pass/fail signals (hiragana fraction — real JP prose ≈ 40%):
1. **Shift-JIS — ELIMINATED.** Proper byte-synced SJIS parse over all 754 RD*.SD4 text
   regions: max hiragana fraction 12.5% (one outlier), median best 1.0%. Nowhere near prose
   levels → the bytes are not SJIS. (Random bytes-as-SJIS look kanji-heavy with ~0% hiragana,
   which is what we see — so the earlier "zero hiragana" was NOT a wrong-region artifact.)
2. **2-byte BE indices in JIS X 0208 ku-ten order — ELIMINATED.** Index→(ku,ten)→EUC-JP→Unicode
   over bases {0,1,32,188,256,282,376,658,752,2048,4096}: every base yields 83–98% kanji,
   <14% hiragana. That is the noise signature (JIS rows 16–94 are kanji, so any byte
   distribution looks kanji-heavy) — not a real script. The font is not a plain JIS-ordered
   table read as 2-byte words.
3. **Structural clue (the way forward):** high-byte frequencies of BE16 words pair exactly —
   `0x0X` and `0x8X` occur at near-equal counts (high bit `0x80` = a flag), `0x00` dominates.
   Consistent with the earlier "position-prefixed" finding: glyph-index runs are **interleaved
   with 1-byte control/coordinate opcodes**, so word-aligned sampling is half-misaligned.
   **Implication:** no statistical shortcut — the Sega CD scene-script opcodes must be reversed
   to isolate the glyph-index runs *before* any index→char mapping can be tested cleanly.

## Honest ROI assessment (2026-06)
The official-Japanese extraction is the single hardest, least-certain part of the whole
project: no ScummVM reference engine, custom (non-SJIS, non-JIS-index) encoding, script-opcode
RE required before decoding, AND an unsolved PC-slot alignment problem on top. Realistic: a
dedicated multi-session/multi-week RE with uncertain payoff. **Recommended dual-track:**
- **Now (ships a working 日文 mode):** machine-translate EN→JA from `dialogs_en.json` →
  `translations/ja.json` → `ja.dtr`, render with a JP bitmap font via the reserved `kDispJA`.
  Same proven overlay mechanism as zh/de; gives players a Japanese mode immediately.
- **Long-track (official source):** keep reversing the Sega CD script per these notes; when it
  cracks, swap the machine JA for the official Sega CD script. These notes make it resumable.

## Decode roadmap (multi-week)
1. Reverse `RISE.BIN` glyph format (bit order / planar? / compression) → render clean 16×16 glyphs.
2. Determine the index→character mapping:
   - test JIS X 0208 ku-ten order (glyph N at a known JIS code renders as that char → direct decode), else
   - render every glyph + Japanese OCR / manual ID to build an index→Unicode table.
3. Decode `RD*.SD4` dialogue (indices → chars) → per-screen Japanese.
4. Align via the user's method: machine-translate each JP line → fuzzy-match vs `dialogs_en.json`
   → assign `(scene,num)` → `translations/ja.json` → `ja.dtr` → wire `kDispJA` (needs JP font in engine).

## Next steps
- Parse the `0x10000+` script section: find the record delimiter for dialogue (look for a
  consistent op byte preceding each Shift-JIS run; the per-run leading control bytes seen
  in analysis are the likely record tags).
- Build `RD<screen>` → PC-scene map via `.CAT` names, then align dialogue order.
- Output `translations/ja.json` (keyed `scene:num`) → `ja.dtr` → wire into the F8 cycle
  (`kDispJA` is already reserved in `cjk.h`).
