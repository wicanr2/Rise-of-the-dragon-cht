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

## Framing progress — text is a 2-byte VDP-nametable word stream (counts only)
Decision (2026-06): pursue the **official Sega CD source only** — no machine-translation
interim. So the script must be fully reversed. Progress on the framing:
- **Pass/fail tool = Zipf concentration.** Real JP text → top-20 glyph codes cover ~40-50%;
  opcode/coord noise is near-uniform. `tools/segacd_encoding_probe.py` measures it.
- **Text is a 2-byte-word stream**, not 1-byte-opcode-interleaved as first thought. Even-aligned
  BE16 words restricted to [1,6144] give 3745 distinct codes @ 41.3% top-20 concentration =
  language-like. Out-of-range words (high byte ≥0x18) are control/formatting tokens.
- **Likely VDP nametable encoding:** each on-screen char = 16-bit word, low bits = font tile
  index, high bits = VDP attributes (palette/priority/flip; bit15=priority). Explains the
  `0x0X↔0x8X` frequency pairing (same glyph with/without priority bit) — though pairing is only
  partial, so the exact index mask is unconfirmed (tested 0x07ff/0x0fff/0x1fff/0x3fff/0x7fff —
  none beat the unmasked-in-range 41.3%).
- **Contamination found:** top words are `0x0101/0x0202/0x0303` = doubled-byte FILL runs, i.e.
  `0x10000` is NOT the clean text start for every file — sprite/fill data bleeds into the window
  and inflates the histogram. `0x0101`-type words are most likely the **blank/space padding tile**.
- **Resume here (next sub-tasks):** (1) per-file, parse the header to find the true text-section
  offset (notes: `@20` BE u32 ≈ 0x10000, but verify per file) and trim trailing fill; (2) on the
  clean sub-region, re-run Zipf — concentration should rise and doubled-word contamination drop;
  (3) identify the blank/space tile code; (4) pin the index mask; (5) THEN map index→char by
  rendering the font tiles (RISE.BIN/.CAT candidates) and OCR/JIS-matching the used set.

## CORRECTION (2026-06, sub-task 1): static analysis exhausted; pivot to dynamic
Deeper structural analysis overturned two earlier optimistic conclusions — record honestly:
- **`EDA:`/`ILF:`/`DFB:` are NOT chunk tags** — they are coincidental ASCII inside image data
  (each is followed by a colour ramp, not a chunk length; no `[A-Z]{3}:` occurrence has a
  plausible following size word). The SD4 is NOT an ASCII-tag DGDS container.
- **The "41.3% language-like Zipf" was a false positive** — it measured 4bpp IMAGE pixel
  statistics, not text. Tell-tale: the top "glyph" codes are doubled-small-byte words
  (`0x0101/0x0202/0x0303/0x0404`) = low-colour image data; nibble histogram is image-like
  (0x0=40%, top-4 nibbles 69%); byte autocorrelation at tile periods (16/24/32/64/128) is a
  flat ~0.04 (no clean tile grid → likely RLE/compressed, not raw tiles).
- **Header (verified across files):** 12 bytes = `@0` BE u32 (≈ filesize − 22 or − 32),
  `@4` BE u32 (= `@0` − 512 or − 1), `@8` = `0xffff0000` marker. File ends in `0x00` padding.
  No pointer to a text section. Bulk of the file = image data (colour ramps, byte runs, and
  high-entropy/low-repeat regions consistent with compression).
- **Why static RE can't finish this:** the dialogue is a SMALL embedded blob; image data mimics
  text's skewed value distribution, and compressed regions mimic varied glyph indices. Bulk
  statistics give false positives in both directions. Confirmed by exhaustive probing.

### The methodology that CAN crack it: dynamic analysis (emulator trace)
Reference-less + graphics-heavy + compressed ⇒ the right tool is to watch the game DECODE text
at runtime, giving ground truth (bytes → on-screen glyph). Concrete plan (Docker, host clean):
1. Run the JP CHD in a debuggable Mega-CD emulator (BlastEm/Genesis Plus GX/Exodus) headless.
2. Reach a known dialogue screen; dump VRAM — the on-screen text is a contiguous block of VDP
   nametable entries → reveals the glyph-tile indices actually used + the font's VRAM base.
3. Breakpoint the 68000 routine that writes those nametable words → trace back to where it reads
   the SD4 script → recover the real text record format + any decompression.
4. Dump the font tiles from VRAM (now we know the base) → render → OCR/JIS-match → index→char.
This is a substantial new sub-project but it is the only reliable path without a reference engine.

## ★ BREAKTHROUGH (2026-06-14): real Mega-CD BIOS → game BOOTS and RENDERS ★
User supplied a genuine Mega-CD BIOS set. `megacd_j.bin` = "SEGA MEGA DRIVE (C)SEGA 1991.NOV
MEGA-CD BOOT ROM ... 1.00p" (JP Model 1). Installed to `/home/anr2/emulator/bios/`.
`tools/segacd_emu_run.sh megacd_j <frames> <every> frames <input_after>`:
- **No more segfault.** Boots cleanly: MEGA-CD logo → Japanese "スタートボタンを押して下さい"
  (**confirms JP text renders!**) → title "Rise of the Dragon / PRESS START BUTTON / ©1992
  Dynamix" → English credits roll (~48s) → intro cutscene (character portraits, likely VOICED)
  → interactive gameplay = Blade's apartment (same layout as PC, clock 7/31 12:0x).
- Resolution 320×224; game palette is green-tinted (cyberpunk). All frames dumped as PPM.

### Boot/navigation map (verified by frame capture)
1. BIOS "スタートボタンを押して下さい" (JP, BIOS font) — press START.
2. **Mega-CD BIOS CONTROL PANEL** (CD-ROM / CDG / OPEN/STOP/PLAY / TRACK 05 …) — GPGX does
   NOT auto-boot the game; you must select **CD-ROM** here to boot the disc.
3. Game title "Rise of the Dragon / ▶START CONTINUE / PRESS START BUTTON" — waits for input
   (does NOT auto-advance; confirmed by a boot-only run sitting here forever). Press START.
4. **SKIP / CONTINUE 劇情 choice** (appears right after the title) — press an ACTION button
   (A/B/C = libretro Y/B/A) to confirm SKIP (default). START here = CONTINUE (plays the intro).
5. After SKIP → Blade's apartment (gameplay) where the opening monologue is.
Else (CONTINUE): English credits roll (~48s) → voiced intro cutscene (portraits, no text) →
apartment.

**Navigation is the bottleneck:** scripting these 4 menus with blind frame-timed input is
unreliable (each emulation run ~40s; the title→choice window is ~40 frames and a stray START
selects CONTINUE). Best unblock = a GPGX-compatible **savestate at a JP dialogue** from the
user, OR exact per-menu input timing. The emulation itself is fully working.

**Remaining blocker = reaching in-game DIALOGUE text.** The SD4 dialogue (speech bubbles, like
PC) only shows on point-and-click interaction. The harness only presses START (boots/advances
cutscenes); it does NOT move the cursor, so gameplay look-dialogues aren't triggered. The intro
cutscene appears voiced (no on-screen text). Options to get the Japanese text:
  - A) add D-pad cursor + button input to the harness, navigate the apartment, trigger Blade's
    look-monologue → screenshot → OCR (tesseract-jpn/manga-ocr in Docker).
  - B) VRAM dump while dialogue shows → glyph tiles (only currently-displayed glyphs fit in 64KB).
    NOTE: GPGX libretro does not expose RETRO_MEMORY_VIDEO_RAM — needs retro_serialize savestate
    parsing instead.
  - C) trace the game's font load from disc (which file/offset it DMAs into VRAM) → that's the
    full font → decode SD4 indices statically.
The hard wall (no BIOS) is GONE; what remains is input-scripting / OCR — tractable iteration.

## Dynamic-analysis harness BUILT — but BIOS-BLOCKED (2026-06-14, overnight)
Built the full headless pipeline to render the JP disc and OCR the official Japanese
(sidestepping the SD4 encoding): `tools/segacd_run.c` (libretro frontend) +
`tools/segacd_dynamic.sh` / `tools/segacd_emu_run.sh` (Docker, Genesis Plus GX v1.7.4).
It loads the disc and runs (`av: 256x192`), confirming the harness works.

**BLOCKER: no Mega-CD BIOS on the system.** Genesis Plus GX (like every accurate Sega CD
emulator) needs the real 128KB Mega-CD boot ROM. The files in `/home/anr2/emulator/bios`
(`mpr-18100/mpr-17933/sega_101`) were mis-assumed to be Mega-CD — they are all **Sega Saturn**
BIOS (`SEGA SEGASATURN`/`SEGA SATURN SYS`). Feeding a Saturn BIOS to GPGX makes the CD sub-CPU
run illegal instructions → consistent SIGSEGV at ~frame 280 (`scd_update → m68k_op_1010 →
ctrl_io_write_word`), screen never leaves black. A system-wide search (incl. MAME romsets) found
NO 128KB Mega-CD BIOS. Cannot legally download it.

**To unblock (needs user):** drop a Mega-CD/Sega-CD boot ROM (128KB, e.g. `bios_CD_J.bin` for
the JP disc — mpr-14088/mpr-15045/etc.) into `/home/anr2/emulator/bios/`, then
`tools/segacd_emu_run.sh <biosname> 1800 60` renders frames → OCR pipeline. The harness is ready.


## Static font render attempt (RISE.BIN) — negative (overnight)
Rendered RISE.BIN (196608 B = 6144x32 or 1536x128, entropy 5.50 = structured) at offset 0 as
1bpp-16x16 (MSB/LSB), 4bpp-8x8 tiles, and 4bpp-16x16 (TL/TR/BL/BR) -> all NOISE, no glyph grid.
Conclusion: RISE.BIN is the sub-CPU PROGRAM binary, not the font. The JP font is elsewhere / at
an interior offset (a .CAT or a sub-region). Without the dynamic VRAM ground-truth (BIOS-blocked),
locating it statically remains the hard open problem. Renders kept local only (copyrighted glyphs).

## RISE.BIN font question — RESOLVED as NEGATIVE (overnight, definitive)
Tested whether RISE.BIN is the JP font, thoroughly:
- Ink-distribution test looked font-like (1628 blank 32B-cells, mean ink 33%, spread 30-60%).
  BUT that signature is ALSO produced by 68000 program code + zero-padding regions.
- Rendered RISE.BIN at offset 0 in **7+ glyph layouts** — 16×16 linear (MSB/LSB), 4×(8×8) tiles
  in orders {TL,TR,BL,BR}/{TL,BL,TR,BR} (1bpp & 4bpp), left/right 8×16 half-columns, 8×16 — 
  **every one is noise, no recognizable kana/kanji.**
- Conclusion: RISE.BIN is the **sub-CPU program** (matches the name + the gdb crash context
  `scd_update→m68k_run`), NOT the font. The font is elsewhere (compressed, non-32-aligned, or
  only materialized in VRAM at runtime). It is NOT locatable by static layout-guessing.
- **The font format is best cracked DYNAMICALLY**: dump VRAM after a JP text screen (font tiles
  appear in VRAM in known VDP 4bpp format), then match back to a disc file to learn the static
  encoding. This is BIOS-gated (see blocker above). Static font search is closed until then.

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
