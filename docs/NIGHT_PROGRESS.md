# 夜間自動推進進度 (2026-06-14 01:00 → 07:00)

使用者就寢，授權自動推進兩條線到早上 7 點。本檔即時記錄成果，醒來可一次讀完。
原則：不問問題、合理決策即執行並記錄理由、邊做邊 commit、不污染 host（工具裝 Docker）、
不把任何受版權資料（CHD/BIOS/遊戲檔）入 git。

## 兩條線
- **Track A — Sega CD 官方日文（動態分析）**：BIOS 已找到（`mpr-18100.bin` 日版），Docker 內建
  Genesis Plus GX 核心 → headless 跑日版 → dump VRAM 抽字型 tile → OCR → index→字元。
- **Track B — 中文版 ship（解鎖中、主交付）**：Phase 5 打包（Linux bundle/AppImage）+ Phase 4
  逐場景排版 QA。

## 進度 log（新到舊）
- 01:04 — 確認時間/環境：JP game(region J) + JP BIOS + Docker 齊備；GPGX 核心背景建置中。
  ScummVM 已 build（23MB），CJK 資產齊（zh/de dtr + 12/16/24 dcjk）。開始 Track B 打包。
- 01:10 — **Track A 重大進展**：GPGX 核心建好 → `tools/segacd_run.c`（libretro headless 前端）
  + `tools/segacd_dynamic.sh`（Docker build/run）成功 **boot 日版 disc**（core v1.7.4、av 256x192）
  並 dump 出 PPM frames。**策略確立**：直接 render 日版 → OCR 螢幕上的官方日文，**繞過 SD4 編碼**。
  目前卡在 retro_run 在 frame ~280（仍在 BIOS 開機黑畫面）穩定 segfault，gdb 追蹤中。
- 01:12 — **Track B 完成並驗證 ✅**：`scripts/package_linux.sh` 產出可重定位 Linux bundle
  (patched scummvm + 106 隨附 libs + 語言資產 + 繁中啟動器) + tar.gz(28M)。Headless 實測：
  bundle 載入全部 libs、boot 遊戲、**渲染中文對話**（`screenshots/bundle_zh.png`：孟波公寓
  「兩百億人口……」全程繁中 24×24）。Phase 5 Linux 打包達成。
