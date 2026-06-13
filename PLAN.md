# PLAN — Rise of the Dragon 繁體中文化

工程計畫與進度。術語見 [`CONTEXT.md`](CONTEXT.md)。

## 目標

把 Dynamix《Rise of the Dragon》(1990) 做成可玩的**繁體中文版**，透過自製 patch 的 ScummVM 渲染。
- 對話、UI 按鈕、選單全中文。
- 真實 24×24 點陣中文字（畫面放大到 640×480 時清晰）。
- **執行時語言切換鍵**：英文（原始）↔ 中文 ↔（日後）日文。
- Ship 三平台：Linux AppImage、Windows、macOS。
- **不重新發布遊戲本體**；本 repo 只放工具、patch、譯文、文件。

## 架構決策（ADR 摘要）

1. **基底 = 英文版**。德文版（最初的 zip）僅作參照。英文是原典，CLAUDE.md 要求英翻中。
   兩版 `(scene, num)` 槽位對齊 2384/2384。
2. **翻譯用「引擎端 overlay」，不做破壞性注入**。
   原始遊戲檔保持不動；ScummVM 在繪字當下查翻譯表並改用 CJK 字型。
   - 理由：要支援**語言切換**與**多語言（中/日）**，overlay 是唯一乾淨解。
   - 反面（注入進 VOLUME）會鎖死成單一語言、且需重建封裝校驗，已否決。
3. **翻譯包格式**：外部 JSON/二進位，key 穩定。
   - 對話：`(scene, dialog num)` → 中文。
   - UI：REQ 內每個文字 gadget 的識別 → 中文。
4. **CJK 字型**：24×24 雙位元組點陣字，從 Noto Sans CJK TC / AR PL UMing TW rasterize。
   內部索引用 Big5（繁體原生）或自訂連續索引；譯文以該編碼餵給引擎。
5. **語言切換鍵**：在 dgds 引擎註冊一個熱鍵（如 `Ctrl+L`）循環語言並重繪。

## 元件（deep modules，窄介面）

| 元件 | 路徑 | 狀態 |
|---|---|---|
| 封裝抽取 | `tools/dgds_volume.py` | ✅ |
| Chunk 解壓（RLE/LZW） | `tools/dgds_chunks.py` | ✅ |
| 對話抽取（SDS→JSON） | `tools/extract_dialogs.py` | ✅ |
| UI 文字抽取（REQ→JSON） | `tools/extract_req.py` | ⬜ |
| 字型產生器（Big5 點陣字） | `tools/build_cjk_font.py` | ✅ |
| 翻譯打包（JSON→DTRN） | `tools/build_translation.py` | ✅ |
| 翻譯包（zh / 日後 ja） | `translations/zh.json` | 🚧 starter |
| ScummVM dgds patch | `patches/dgds-cjk.patch` | ✅ PoC |
| 無頭測試 + 截圖 | `scripts/run_headless.sh` | ✅ |
| 三平台打包 | `scripts/` | ⬜ |

## 階段與進度

### Phase 0 — 逆向 & 抽取 ✅
- [x] VOLUME.VGA 索引 / chunk / RLE+LZW 解壓
- [x] SDS 場景解析（ver 1.211），抽出 2386 句英文對話
- [x] ScummVM 基線可跑（無頭 + 截圖，確認德文 intro 畫面）
- [x] 英文/德文槽位對齊驗證

### Phase 1 — 字型 + 引擎渲染 PoC ✅
- [x] 產生 Big5 點陣字（`tools/build_cjk_font.py`，12px=native，2× 後顯示 24px；已 ASCII 驗證 中/文/龍/跳/過）
- [x] patch dgds：`CJKSupport` 模組（載入 DCJK 字型 + `drawString` 雙位元組 Big5 + CJK 逐字斷行）
- [x] 翻譯 overlay 最小版：DTRN pack，UI 按鈕（`UI:<src>`）+ 對話（`scene:num`）
- [x] **驗收訊號**：intro 按鈕渲染為「跳過序章 / 播放序章」（`screenshots/poc_zh_intro.png`）
- [x] 語言切換鍵：F8（dgds keymap 自訂動作，`kDgdsKeyToggleLanguage`）
- [x] 切語言**即時重繪**：`Menu::redrawCurrent()`，modal menu/REQ 立刻更新（場景對話本就逐幀重繪）

### Phase 2 — 翻譯 overlay + 語言切換 ✅（機制）
- [x] 引擎載入 `zh.dtr`（對話 + UI）
- [x] 繪 SDS 對話 / REQ 按鈕時查表替換
- [x] 語言切換熱鍵 F8：英 ↔ 中（架構預留 日）+ 即時重繪
- [x] 驗收：遊戲中 F8 即時切換中/英（intro 選單實測）

### Phase 3 — UI / 按鈕中文化 🚧
- [x] `tools/extract_ui.py`：用引擎 `-d3` dump 抽出**全部 58 個 UI 字串**（按鈕 + 文字項）
- [x] 三個繪字點全 hook：按鈕（`_buttonName`）+ 標題（`drawHeader`）+ 文字項（`drawMenuText`）
- [x] 58 UI 字串全翻譯 → 主選單實機全中文（`screenshots/poc_zh_menu.png`）
- [ ] 排版微調：CJK 比原字高，選單標題位置略偏上需下移
- [ ] inventory（DINV.REQ 走 `drawInvType`，目前 text item 會 error，需單獨處理）

### Phase 1.5 — 高解析 24×24 中文字層（使用者指定）
引擎在 320×200 繪圖、ScummVM ×2 → 640×480。現況中文 12px 被一起放大成 24px（blocky）。
目標：中文以**真正 24×24** 疊在放大後的美術上（更銳利）。
設計（present 路徑改造）：
- `dgds.cpp:819` 是唯一的 `copyRectToScreen(_compositionBuffer 320×200)`。
- 改 `initGraphics(640,400)`；present 時把 320×200 美術 nearest ×2 放進 640×400 暫存。
- CJK 改「**延遲繪製**」：對話/選單 hook 不直接畫進 320×200，而是記錄 `{big5, x, y, w, col}`，
  在 ×2 之後以 24×24 字型畫到 640×400 暫存，再 copyRectToScreen。
- menu 走 `lockScreen` 自己的路徑，需一併處理（gadget 座標 ×2）。
- 需產生 24×24 字型：`build_cjk_font.py --size 24`（已支援，改用 Noto Sans CJK TC outline）。
- [ ] 待 Phase 4 譯文合併後實作 + 逐畫面截圖驗證。

### Phase 4 — 全量翻譯 🚧
- [x] 譯名表定案：Blade→孟波、Karyn→阿香（City Hunter 梗，見 CONTEXT.md / README 譯名考古）
- [x] 多代理 workflow：18 批平行機翻 2386 句（套譯名表，Big5-safe，賽博龐克黑色語氣）
- [ ] 合併 → 驗證 Big5 → 打包 → 逐場景排版/斷行 QA
- [ ] 人工潤飾關鍵劇情對白

### Phase 5 — 打包
- [ ] Linux：patched ScummVM → AppImage
- [ ] Windows：交叉編譯 → zip
- [ ] macOS：universal `.app` / `.dmg`

## 風險 / 待解

- **24×24 vs 12×12**：dgds 原生在 320×200 繪字。24×24 太大會擠爆泡泡 → 可能需要把文字繪進 2× 內部畫布（640×400），或先用 12×12 經 2× 放大成 24×24（先求渲染通，再求清晰）。Phase 1 PoC 會敲定。
- **REQ 文字定位**：按鈕文字在 REQ 內如何 keying，須讀 `request.cpp` 確認。
- **語言切換重繪時機**：切語言後需強制重繪當前場景/對話。
- **日文版**：日後併入 overlay（同機制，換字型 + `ja.json`）。

## 參考

- ScummVM `dgds` 引擎原始碼（格式權威）：`/home/anr2/zak-zh/tools/scummvm-src/engines/dgds/`
- 前作經驗：Zak McKracken CHT（`zak-cht`，雙位元組字型 + patched ScummVM 的範本）
