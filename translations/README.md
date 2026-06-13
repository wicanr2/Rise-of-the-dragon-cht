# translations/

語言包放這裡。
- `zh.json` — 繁體中文翻譯 overlay（對話以 `scene/num` 為 key，UI 以 REQ 識別為 key）。
- `ja.json` — （日後）日文。

原始英文檔不動，這些檔由 patched ScummVM 在執行時載入並可熱鍵切換。

## 翻譯流程（可重現）

1. `tools/extract_dialogs.py` 從英文 SDS 抽出 2,386 句 → `dialogs_en.json`（版權原文，gitignored）。
2. 切成 18 個 batch（`build/batches/`）。
3. `scripts/translate_workflow.js`（多代理 workflow）平行翻譯，套用譯名表（孟波/阿香）+ 1990s 賽博龐克黑色語氣 + Big5 安全。
4. `tools/merge_translations.py` 合併、正規化（中點→`·`）、驗證 0 個非 Big5 字。
5. `tools/build_translation.py translations/zh.json zh.dtr` 打包成引擎讀的 overlay。

譯名表見根目錄 [`CONTEXT.md`](../CONTEXT.md)。
