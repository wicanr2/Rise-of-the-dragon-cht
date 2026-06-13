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

## Next steps
- Parse the `0x10000+` script section: find the record delimiter for dialogue (look for a
  consistent op byte preceding each Shift-JIS run; the per-run leading control bytes seen
  in analysis are the likely record tags).
- Build `RD<screen>` → PC-scene map via `.CAT` names, then align dialogue order.
- Output `translations/ja.json` (keyed `scene:num`) → `ja.dtr` → wire into the F8 cycle
  (`kDispJA` is already reserved in `cjk.h`).
