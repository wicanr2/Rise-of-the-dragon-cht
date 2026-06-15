# 設計稿 — dgds 引擎 CJK overlay + 語言切換

> 對應 [`PLAN.md`](../PLAN.md) Phase 1–2。本文件描述「如何讓 ScummVM 的 `dgds` 引擎
> 顯示繁體中文、並能在執行時切換語言」的具體設計。技術 voice，給工程審閱用。

## 目標與限制

- 引擎原生繪圖解析度 **320×200**（`includes.h`），ScummVM ×2 → 640×480 視窗。
  → 中文字採 **12px native bitmap**，上畫面顯示為 24px。
- **不破壞遊戲檔**：原始英文 VOLUME 不動，中文是「疊」上去的 overlay。
- **執行時語言切換**：英文（原始）↔ 中文 ↔（日後）日文。
- 引擎內**不放 Unicode 轉換表**：譯文離線就編好 Big5 bytes，引擎只做 byte-level 查表。

## 資料流

```
 翻譯 (UTF-8, dialogs_en→人/機翻)          系統 TTF (wqy-zenhei sharp 12px / Noto TC)
        │                                          │
        │  tools/build_translation.py              │ tools/build_cjk_font.py
        ▼  (UTF-8 → Big5, 打包)                     ▼ (rasterize → Big5 linear index)
   translations/zh.dtr  ──────────┐      ┌──────  fonts/dragon_zh12.dcjk
   (DTRN binary)                  ▼      ▼        (DCJK binary)
                          ┌───────────────────────────┐
                          │   patched dgds engine      │
                          │  ┌─────────────────────┐   │
   Dialog::drawForeground │  │ TranslationOverlay  │   │  key = "<sceneNum>:<dlgNum>"
   ───────────────────────┼─▶│  .lookup(key,lang)  │   │
                          │  └─────────┬───────────┘   │
                          │            ▼ Big5 string    │
                          │  ┌─────────────────────┐   │
                          │  │   DgdsCJKFont        │   │  雙位元組 Big5 → glyph
                          │  │  .drawString()       │───┼──▶ 320×200 surface ─×2─▶ 畫面
                          │  └─────────────────────┘   │
                          │   LanguageState (hotkey)   │
                          └───────────────────────────┘
```

## 元件

### 1. DCJK 字型（已完成）
`tools/build_cjk_font.py` 產出。Big5 linear index：
`idx = (lead-0x81)*157 + trailoffset`，`trail 0x40–0x7E→0–62, 0xA1–0xFE→63–156`。
12×12、每列 `(w+7)/8=2` bytes、每字 24 bytes、19782 槽（13704 已繪）。

### 2. DgdsCJKFont（新增 class，`font.h/.cpp`）
繼承/包裝 `DgdsFont`，但理解雙位元組：

| 介面 | 行為 |
|---|---|
| `getFontHeight()` | 回 `_h`（12） |
| `getCharWidth(uint16 hi_lo)` | CJK 全形 → `_w`（12）；ASCII → fallback 原 dlg 字型 |
| `drawString(...)` | 逐 byte 掃：lead `>=0x81` 取下一 byte 組 Big5 → `bigIndex` → 畫寬字；ASCII byte → 用原英文 dlg 字型畫 |
| `wordWrapText(...)` | **每個 CJK 全形字都是合法斷點**（中文無空白）；`\r` 強制換行 |

混排規則：一行內可同時有 ASCII（原 dlg 字型，半形寬）與 CJK（12px 全形）。

### 3. TranslationOverlay（新增，`translation.h/.cpp`）
載入 `translations/<lang>.dtr`（DTRN binary）。格式（小端）：
```
"DTRN" u8 version u8 lang u16 pad  u32 count
count × { u16 keyLen, key[], u16 valLen, val[] }   # val = Big5 bytes，可含 \r
```
- 對話 key：`"<sceneNum>:<dialogNum>"`（sceneNum = `getScene()->getNum()`，== 檔名數字；dialogNum = `Dialog::_num`）。
- UI key（Phase 3）：`"REQ:<reqName>:<gadgetId>"`。
- API：`const char *lookup(const Common::String &key)`，查無回 `nullptr`（fallback 原文）。

### 4. LanguageState + 切換鍵（`dgds.h/.cpp`）
- enum `{ kLangOrig, kLangZH, kLangJA }`，預設 `kLangZH`（可由 config 設定）。
- 在主事件迴圈攔截熱鍵（暫定 `Ctrl+L`）→ 循環語言 → 標記重繪當前場景/對話。
- `kLangOrig` 時完全走原生路徑（行為與未修改版相同）。

### 5. 掛鉤點：`Dialog::drawForeground()`（`dialog.cpp`）
```cpp
void Dialog::drawForeground(surface, fontcol, txt) {
    if (lang != kLangOrig) {
        const char *zh = overlay->lookup(sceneNum + ":" + _num);
        if (zh) { drawCJK(surface, zh, ...); return; }   // 用 DgdsCJKFont + CJK 斷行
    }
    ... 原本英文流程 ...
}
```
`getDlgTextFont()` 在 CJK 模式回傳 `DgdsCJKFont`。

## 編碼決策：為何 Big5

- 譯文離線（Python，有完整 codec）就轉成 Big5 → 引擎零 Unicode 表，**窄介面**。
- 字型與譯文用**同一套 Big5 索引**，由同一工具產出，不會對不上。
- 繁體原生編碼，符合專案定位。日後日文版改用 Shift-JIS 索引的 `ja.dcjk` + `ja.dtr`，機制相同。

## 整合與建置

- 改動檔（全在 `engines/dgds/`，與 zak 的 scumm patch 不衝突）：
  `font.h/.cpp`、`dialog.cpp`、`dgds.h/.cpp`，新增 `translation.h/.cpp`、`module.mk`。
- 以 `git diff -- engines/dgds` 擷取成 `patches/dgds-cjk.patch`（可重現、可 revert）。
- 開發期 build：`./configure --disable-all-engines --enable-engine=dgds`（快）。
- Release：日後 vendor 乾淨 ScummVM source，三平台打包（AppImage / Windows / macOS）。

## 分期

1. **PoC**：硬塞一句中文到一個對話 → 上畫面（驗證 DgdsCJKFont + 掛鉤）。
2. **Overlay**：載 `.dtr`、查表替換、語言切換鍵。
3. **UI/REQ**：按鈕、選單、存讀檔（`request.cpp`）。
4. **全量翻譯 + 排版 QA**。
5. **日文版**併入（同機制）。

## 已知風險

- **中文比原文高**：原 dlg 字型 P6X6≈6–8px，CJK 12px → 同一泡泡 `_rect` 容納行數變少，
  長對話可能溢出 → Phase 2/4 需做自動分頁（click-to-continue）或縮放泡泡。
- **REQ 文字定位**：按鈕文字在 `request.cpp` 如何 keying，Phase 3 確認。
- **切語言重繪**：需強制 redraw 當前場景；對話進行中切換的狀態保留待測。

---

# 實作後記（與設計稿的差異 + 硬核學習）

> 以下記錄**實際做出來**之後與上面設計稿的偏離，以及反覆踩坑換來的非顯然結論。
> 設計稿是規劃；本段是 ground truth。維護時以本段為準。完整可重用 SOP 另見全域 skill `rise-of-the-dragon-cht`。

## 與設計稿的偏離

| 設計稿 | 實際 |
|---|---|
| `DgdsCJKFont` + `TranslationOverlay` 兩個 class | 合併成單一 **`CJKSupport`**（`cjk.h/.cpp`），含字型 + 譯文 + 顯示模式 |
| `Ctrl+L` 切語言 | **F8**（`metaengine.cpp` keymapper action `TOGGLE_LANG`，也綁 `C+S+l`） |
| CJK 直接畫進 320×200 surface | ⭐ **hi-res overlay**：`deferLine()` 收集行 → `flushDeferred()` 在 `present2x()` 把 24px bitmap 畫進 **640×400 `_hiresBuffer`**（不是 320 inline）。CJK 永遠以真實 24px 畫、不被 2x 放大糊掉 |
| `fontHeight()` = 12 | 仍是 12（**320 空間**的行高；deferLine 座標都是 320 空間，render 時 ×2） |
| 只有對話一條路徑 | **三條獨立路徑**（見下），漏一條就有英文殘留 |

## 三條繪字路徑（最重要 — 換遊戲必先確認都 hook 到）

| 路徑 | hook | 查表 |
|---|---|---|
| 對話內文 | `dialog.cpp drawForeground` | `lookupDialog(scene,num)` |
| 對話名牌 / 選單 / REQ 標題 | `request.cpp drawHeader` | `lookupUI(header)`（名牌 = 對話冒號前，**用英文 key**，補 `UI:<英文名牌>` 即中文化，純資料）。⚠️ 名牌字的 y 用 `htop+2` 是對齊小英文 font baseline，CJK glyph 高 12（320-space）會往下沉壓進對話框 → 改成在框 `[htop, htop+hheight]` 內置中：`htop + (hheight - cjk.fontHeight())/2`（`hheight` 讀活的 font，免寫死）|
| **TTM 畫面文字**（電腦/視訊電話/捷運/保全鍵盤）| `ttm.cpp` drawString op `0xa2X0` | `lookupUI(str)`（用 `tools/extract_ttm_strings.py` 從 `TT3:` chunk 抽 SET STRING `0xf1X0`，**別瞎玩遊戲找字**）|

## TTM 持久層 — 最深的坑（committed-flag + STORE AREA）

TTM 畫面文字**畫一次然後 ADS hold**（不像對話框每幀重畫）。英文持久靠 STORE AREA op `0x4200` 把 composition 區域存進 `_storedAreaBuffer` 每幀 transBlit；CJK 是 hi-res overlay（present 時最後畫），兩者像素模型不同步 → 一連串症狀：

| 症狀 | 正解 |
|---|---|
| 訊息閃一幀就消失 | 獨立持久層 `_deferredBg`（per-frame `clearDeferred()` 不碰它）|
| 切 NEXT/PREV 多則疊加 | 每行帶 `committed` 旗標；`commitBg(rect)`（ttm `0x4200`）移除 rect 內舊 committed 行、把新行標 committed |
| 沒 STORE AREA 的畫面（捷運 `emp1.ttm` 0 個）| 行維持未 committed、持續顯示；`clearDeferredBg()` 在 **F8 切語言 + 換場景** 清 |
| ⭐ 標題浮在「會動的臉」上 | **視訊電話的臉 = 普通 ttm DRAW SPRITE（`136×87 @ 65,9`），不是 talking-head！** 在 `ttm.cpp` doDrawSprite 後 `clearDeferredBgRect(spriteRect)` 清掉被臉蓋住的 overlay。訊息清單 header 不受影響，因為「先畫圖→後 defer header」的順序 |

**教訓**：先確認每個 ttm **有/沒有 STORE AREA**、臉到底哪個 op 畫的，**別假設**。`runScript haveHead=0 hasScript=0` 證實視訊臉不走 CDS/talking-head。

## 對話框溢出 → 自動長高（解掉設計稿的「已知風險」）

24px 中文（12 單位/行）比英文小字（~4 單位/行）高 3 倍，3+ 行對話溢出框底。
**`dialog.cpp drawType2`**：兩個 draw stage 從 `_rect` 算框/文字區之前，先 `wrapText` 量 CJK 行數，
`_rect.height` 不夠就**往下長高**（clamp 在螢幕內）。保留 24px 可讀性、不縮字、不溢出。

## 除錯方法論（這次定位視訊臉的關鍵）

headless（Xvfb 無真實音訊）下**視訊臉不 render**（音訊/影片驅動），所以本機重現不出來。解法：
1. **用玩家存檔**（`~/.local/share/scummvm/saves/rise.00N`）`scummvm -x N` 直接載到目標畫面。
2. 在 hook 點加 `warning("ROTDDBG ...")` 印**繪圖 op 的位置+大小**，build debug 版。
3. **在玩家自己的桌面 session 跑**（不是從別的 process context 啟動 — GNOME 收不進視窗、alt-tab 看不到）：
   `XAUTHORITY` 要用 session 的、輸出導到檔案我讀。或乾脆請玩家在自己終端機跑、貼 log。
4. 從 log 的 `ttmdraw at 65,9 sz 136x87`（出現 78 次 = 動畫幀）直接認出臉 → 精準 hook。

> 陷阱：`game_en/.../autopilot.txt` 一存在 dgds 就跑 game-tester 腳本（結尾 `quit` → 一開就退、或 `hot area NN not found` → crash）。測試腳本會偷寫它，跑遊戲前先清掉。`getenv` 是 ScummVM 禁用符號。

## Android 注入（遊戲不上 GitHub，本地組）

CI 只編引擎+資產。`tools/inject_android.sh` 注入遊戲 + 三顆缺的 `.so`：
`libscummvm.so → liboboe.so → libc++_shared.so`（configure 硬連 `-loboe`、oboe 無法關）。
遊戲要放 APK **雙層** `assets/assets/games/<id>` + 登錄 `assets/MD5SUMS` 才會展開 + mass-add。
`patches/android-surface-race.patch` 修 S25+/Android16 `eglCreateWindowSurface` 秒退；
`patches/android-autostart-rise.patch` 直接 boot 遊戲。`extractNativeLibs=true` 所以 16KB 警告非致命。
