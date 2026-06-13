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

## 譯名表（character / proper-noun glossary）

翻譯時一律使用，確保全劇本一致。`✓` = 已定案，`?` = 草稿待確認。

| 英文 | 中文 | 備註 |
|---|---|---|
| Blade（William "Blade" Hunter）✓ | **孟波** | 主角。致敬《城市獵人》(City Hunter) 盜版主角名，呼應 1990s 軟體世界引進台灣的時代梗 |
| Hunter | 獵人 | Blade 的姓；「孟波」本身已扣 City Hunter，姓視語境用「獵人」或省略 |
| Karyn ? | 凱琳 | 孟波女友，後遭綁架（City Hunter 同人梗可改「阿香」，待確認） |
| Jake ? | 傑克 | 孟波的線人/友人 |
| Chen / Chen Lu ? | 陳路 | 唐人街黑幫頭目 |
| Chandra ? | 錢德拉 | 反派，「新黎明教團」首領 |
| Chandi ? | 錢迪 | |
| Qwong / Quong ? | 阿廣 | 唐人街角色 |
| Hwang ? | 黃 | 唐人街角色 |
| MTZ ? | MTZ | 劇情核心毒品（保留英文代號）|
| NaPent ? | 神經素 NaPent | 道具（麻醉噴劑）|
| Pleasure Dome ? | 歡愉穹頂 | 夜店場景 |

說話人標籤格式：`BLADE:` → `孟波：`（全形冒號）。

## Flagged ambiguities

- _(resolved)_ Source language: translate from **English** (`dialogs_en.json`), base game = English release.
- 譯名表 `?` 項待使用者確認；尤其 Karyn 是否延伸 City Hunter 同人梗（阿香）。
