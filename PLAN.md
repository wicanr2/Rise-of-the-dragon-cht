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
| 字型產生器（→ 24×24 點陣） | `tools/build_cjk_font.py` | ⬜ |
| 翻譯包（zh / 日後 ja） | `translations/zh.json` | ⬜ |
| ScummVM dgds patch | `patches/dgds-cjk.patch` | ⬜ |
| 無頭測試 + 截圖 | `scripts/run_headless.sh` | ✅ |
| 三平台打包 | `scripts/` | ⬜ |

## 階段與進度

### Phase 0 — 逆向 & 抽取 ✅
- [x] VOLUME.VGA 索引 / chunk / RLE+LZW 解壓
- [x] SDS 場景解析（ver 1.211），抽出 2386 句英文對話
- [x] ScummVM 基線可跑（無頭 + 截圖，確認德文 intro 畫面）
- [x] 英文/德文槽位對齊驗證

### Phase 1 — 字型 + 引擎渲染 PoC（進行中）
- [ ] 產生 24×24 繁中點陣字（單元驗證：ASCII 預覽幾個字正確）
- [ ] patch dgds：載入 CJK 字型 + `drawString` 雙位元組路徑 + CJK 逐字斷行
- [ ] 翻譯 overlay 最小版：硬寫一句中文到 intro REQ + 一個對話泡泡
- [ ] **驗收訊號**：無頭跑 → 截圖看到中文 intro 按鈕

### Phase 2 — 翻譯 overlay + 語言切換
- [ ] 引擎載入 `translations/zh.json`（對話 + UI）
- [ ] 繪 SDS 對話 / REQ 按鈕時查表替換
- [ ] 語言切換熱鍵：英 ↔ 中（架構預留 日）
- [ ] 驗收：遊戲中按鍵即時切換中/英

### Phase 3 — UI / 按鈕中文化
- [ ] `extract_req.py` 抽出所有 REQ 文字 gadget
- [ ] intro / inventory / save-load / VCR 控制列 全中文

### Phase 4 — 全量翻譯
- [ ] 機翻 2386 句英文 → 繁中初稿，人工潤飾
- [ ] 1990s 賽博龐克語感、人名地名譯名表（見 CONTEXT.md）
- [ ] 泡泡寬度 / 斷行 QA（逐場景截圖）

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
