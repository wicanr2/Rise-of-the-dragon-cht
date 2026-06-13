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

### Phase 1.5 — 高解析 24×24 中文字層 ✅
真正 24×24 中文疊在 2× 放大美術上（不再是 12px 拉大）。實作 = **虛擬螢幕間接層**：
- `initGraphics(640,400)`；新增 320×200 `_vscreen`，所有引擎繪圖經 `vLockScreen/vCopyRectToScreen/vUpdateScreen` 改畫到 `_vscreen`（5 檔 ~40 處 present point 全改）。
- `present2x()`：`_vscreen` nearest ×2 → 640×400 `_hiresBuffer`，再 `flushDeferred` 把 CJK 以 24×24 畫上去。
- CJK 改**延遲繪製**：dialog/menu/request hook 記錄 `{big5,x,y,w,col}`（320×200 座標），present 時 ×2 畫 24px。佈局用 `_w/2`（12）算寬高。
- **滑鼠座標修正**：backend 變 640×400 → 進來的滑鼠 `/2`、`warpMouse` `×2`（否則 hit-test 全錯）。
- 24×24 字型：`build_cjk_font.py --size 24`（Noto Sans CJK TC，glyph 置中）。
- [x] intro 選單實機驗證：跳過序章/播放序章 **真 24×24 crisp**（`screenshots/hires_intro.png`）。
- [x] 場景美術 2× 正確（`hires_apartment.png`），對話走同一 deferred 路徑。
- [ ] 待補：hi-res ASCII（選單數字目前小）、選單標題/按鈕垂直位置微調、ttm 轉場 2× 視覺確認。

### Phase 4 — 全量翻譯 ✅（初稿）
- [x] 譯名表定案：Blade→孟波、Karyn→阿香（City Hunter 梗，見 CONTEXT.md / README 譯名考古）
- [x] 多代理 workflow：18 批平行機翻 **2386 句**（套譯名表，Big5-safe，賽博龐克黑色語氣）
- [x] 合併 → 正規化 agent 雜訊（中點→·、尾巴亂碼）→ 驗證 **0 個非 Big5 字** → 打包 zh.dtr（2441 條，0 缺字）
- [x] 進遊戲確認對話渲染：log `CJK dialog 5:29 -> <Big5>` 證實 drawForeground CJK 分支執行繪字
- [ ] 逐場景排版/斷行 QA（含選單型對話 `1. xxx` 的 \r）
- [ ] 人工潤飾關鍵劇情對白
- [ ] 乾淨的對話泡泡截圖（headless 觸發 look 互動不穩，待更可靠的輸入腳本或實機）

### Phase 6 — 多模式顯示切換（使用者指定，待實作）
一個按鍵（**F8**；F7 已是 ScummVM 的 Load，不能用）循環「顯示模式」= (語言, 字級)：

| 模式 | 語言來源 | 字型 | 備註 |
|---|---|---|---|
| 英文（原始）| 遊戲本身 | DRAGON.FNT | overlay 關閉 |
| 中文 24×24 | `zh.dtr` | `dragon_zh24.dcjk` | 現況 |
| 中文 16×16 | `zh.dtr` | `dragon_zh16.dcjk`（新增）| 較小、較貼近原排版 |
| 日文 | `ja.dtr`（Sega CD 萃取）| JP 字型 | 見下 |
| 德文 | **獨立遊戲**（德版 VOLUME）| DRAGON.FNT | 特例：德文是另一套遊戲檔，非 overlay。要嘛跑德版遊戲、要嘛把德文做成 `de.dtr` 疊在英版上（待確認）|

實作：`CJKSupport` 改持有多顆字型（24/16）+ 多個 overlay（zh/ja），mode enum 循環；`flushDeferred` 用當前 mode 的字型/overlay。需 `build_cjk_font.py --size 16`。

### Phase 7 — 日文版（Sega CD）
來源：`Rise of the Dragon (Japan).chd`（Sega CD，**本地保留、不入 git**）。
- 萃取 CHD → cue/bin → data track（Sega CD DGDS 變體）→ 抽日文劇本 → `ja.dtr`（日文正確翻譯以此為準）。
- **語音 + CD 音軌**：Sega CD 版有數位語音與紅皮書音軌；評估能否把語音對應到對話、音軌當配樂（大型未來功能，PC 版原本無語音）。

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
