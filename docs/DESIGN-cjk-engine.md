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
