# CONTEXT — Rise of the Dragon 繁體中文化

Domain glossary. Use these canonical terms in code, filenames, docs.

## Game / engine

- **ROTD** — Rise of the Dragon (Dynamix, 1990). The game being localized.
- **DGDS** — Dynamix Game Development System; the resource/script engine. ScummVM `dgds` engine plays it (game id `GID_DRAGON`). _Avoid_: "the SCUMM engine" (different engine; that was Zak).
- **Volume** — a `VOLUME.00x` archive holding resources. `VOLUME.VGA` is the **index** (salt + per-volume resource table). Format in `tools/dgds_volume.py`.
- **Resource** — a named entry inside a volume (e.g. `s10.sds`, `dragon.fnt`). 12-char name + size header precede the data.
- **Chunk** — a typed block inside a resource: 4-byte id ending in `:` (e.g. `SDS:`, `BIN:`, `FNT:`) + size. High bit of size = container. Some chunks are LZW/RLE packed.
- **SDS** — scene script resource (`s<NN>.sds`). Holds the **dialogue** (`_str` fields) plus hotspots/ops/triggers. Scene version is `" 1.211"`.
- **TTM / ADS** — animation / sequence scripts. Their readable strings are internal **TAG labels** (e.g. "SNAKE AIMS GUN"), _not_ player-facing text. _Avoid_: treating TAG text as dialogue.
- **REQ** — UI request (menu/inventory/dialog box) layout + button text.

## Localization

- **Dialog slot** — a single translatable unit, keyed by `(scene, num)`. Source text is one `_str`, lines separated by `\r`.
- **Base game** — the **English** release (`game_en/`). The German release (`game/`) is reference-only. Translate `dialogs_en.json`, inject into the English files.
- **Source encoding** — DOS **CP437**.
- **kChinaFont / CHINESE.FNT** — ScummVM dgds already renders a Chinese font for Heart of China (`_fontSize == 5`). Precedent for the ROTD CJK patch.
- **Game font** — `DRAGON.FNT` (`kGameFont`). **Dialog font** — `P6X6.FNT` (`kGameDlgFont`, proportional 6×6). Chosen per dialog `_fontSize` (1=8×8, 3=4×5, else dlg font).

## Flagged ambiguities

- _(resolved)_ Source language: translate from **English** (`dialogs_en.json`), base game = English release.
