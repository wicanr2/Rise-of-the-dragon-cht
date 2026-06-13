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
