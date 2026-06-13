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
- 01:30 — **Track A BIOS 關卡（誠實更正）**：原以為 `/emulator/bios` 有 Mega-CD BIOS，實際
  三個檔全是 **Sega Saturn** BIOS（`SEGA SEGASATURN`）。全系統（含 MAME romset）查無 128KB
  Mega-CD boot ROM。GPGX 餵 Saturn BIOS → CD sub-CPU 跑非法指令 → frame ~280 穩定 segfault
  （gdb：`scd_update→m68k_op_1010→ctrl_io_write_word`）。**動態路線硬卡在缺 Mega-CD BIOS**
  （受版權、不可下載）。harness 已就緒：使用者放入 BIOS 即可 `tools/segacd_emu_run.sh`。
- 02:00 — **Track B AppImage ✅**：`scripts/package_appimage.sh`（AppDir on host +
  appimagetool in Docker）產出 `dist/Rise-of-the-Dragon-CHT-x86_64.AppImage`(27M)，實測可執行。
- 02:25 — **Phase 4 QA ✅**：autopilot 擷取場景 5 獨白於 EN/ZH24/ZH16/DE 四模式，
  `docs/GAME_TEST_REPORT.md`（含 committed 圖 + 排版觀察）。EN/ZH24/ZH16 乾淨；記錄 DE 循環
  時序 + autopilot↔GTSTATE 熱區枚舉缺口為後續。
- 03:00 — **AppImage 驗證 ✅**：實測 AppImage headless 跑遊戲、渲染中文（`screenshots/showcase/appimage_zh.png`）。
- 03:10 — **翻譯品質稽核 ✅**：2386 句全譯、0 殘留英文人名、譯名一致（孟波×459/阿香×236）、
  全形冒號 1667/0、**無溢出風險**（中文視覺寬度短於原英文）、語氣忠實（抽樣）。結論：機翻品質高。
  靜態字型嘗試：RISE.BIN 在 1bpp/4bpp offset 0 皆雜訊 → 是 sub-CPU 程式非字型（記錄）。
- 03:40 — **Windows 交叉編譯 ✅✅**：`scripts/build_windows.sh`（Docker + mingw-w64 + SDL2，
  dgds-only）成功 build `scummvm.exe`，strip 後 **27.5MB**。相依僅 SDL2.dll + Windows 系統 DLL
  （libstdc++/libgcc 靜態連結）。Windows bundle 組好並 zip（12MB，exe + SDL2.dll + extra/ + .bat + README）。
- 04:00 — **Windows 驗證註記**：headless wine 跑不出來，但實測 **wine 連 trivial hello.exe 都跑不動**
  （exit 53、無輸出）→ 是這台 wine(11.0)/headless 壞掉，**非 build 缺陷**。build 編譯/連結乾淨、
  PE32+ 有效 → 判定 build 健全，待實機 Windows 驗證。README 已誠實標註。

## 醒來速覽（成果總表）
| 項目 | 狀態 |
|---|---|
| Linux AppImage + tar.gz | ✅ 實機 headless 驗證渲染中文 |
| Windows zip（交叉編譯）| ✅ build 健全；待實機驗證（本機 wine 壞） |
| macOS | ⬜ 需 macOS host（未做） |
| 全 2386 句翻譯品質稽核 | ✅ 完整/一致/語氣/無溢出皆過 |
| 排版 QA（場景5 四模式）| ✅ EN/ZH24/ZH16 乾淨 |
| Sega CD 官方日文（動態）| 🚧 harness 就緒，**硬卡缺 Mega-CD BIOS**（需你提供 128KB boot ROM） |
| Sega CD 靜態解碼 | 🚧 編碼/字型多條死路已記錄（`docs/SEGACD_RE_NOTES.md`） |

**給你的待辦**：(1) 實機 Windows 測 `dist/rotd-cht-windows-x86_64.zip`。(2) 若要官方日文，
放一顆 Mega-CD BIOS 到 `/home/anr2/emulator/bios/` 即可跑 `tools/segacd_emu_run.sh` 動態抽日文。
(3) commits 都在本地，未 push（你 review 後再 push）。
