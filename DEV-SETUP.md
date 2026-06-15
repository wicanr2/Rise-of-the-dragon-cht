# 在另一台電腦重建開發環境

這份說明如何從 dev tarball（或 GitHub clone + game_en）在新機器上重建、編譯、打包。

## 這包裡有什麼

| 路徑 | 是什麼 | 來源 |
|---|---|---|
| `patches/` | ScummVM dgds 引擎 CHT + Android patch（**source of truth**） | git |
| `translations/zh.json` | 譯文（UTF-8）→ `build/zh.dtr` | git |
| `tools/` | 抽字 / 建字型 / 建 dtr / Android 注入 / adb debug | git |
| `scripts/` | Linux/AppImage/Windows/Mac 打包 | git |
| `docs/DESIGN-cjk-engine.md` | 設計稿 + **實作後記**（三條繪字路徑、TTM STORE-AREA 持久層、除錯方法論）| git |
| `CONTEXT.md` | 譯名表 / ubiquitous language | git |
| `build/` | 編好的 CJK 資產（`dragon_zh{16,24}.dcjk`、`zh.dtr`、`android_games/`、`android_libs/libc++_shared.so`） | 可由 tools 重建 |
| `game_en/riseofthedragon/` | **遊戲本體**（VOLUME.* + CJK 資產）— 受版權，僅供你個人，勿散布 | 你的合法副本 |
| `setup-dev.sh` | clone ScummVM + 套 patch + build | — |
| ~~`scummvm-src/`~~ | **不在包裡**（893MB）— 由 `setup-dev.sh` clone 重建 | — |
| ~~`dist/`~~ | **不在包裡** — 打包輸出，重建即生成 | — |

## 重建步驟

```bash
tar xzf rotd-cht-DEV-ENV.tar.gz && cd rise-of-the-dragon

# 依賴 (Debian/Ubuntu)
sudo apt install build-essential git libsdl2-dev libfreetype-dev libpng-dev \
                 python3-pip docker.io
python3 -m pip install --user freetype-py pillow   # 重建字型用

# 1. 重建 patched ScummVM (clone + patch + build dgds)
bash setup-dev.sh

# 2. 設環境變數 (package 腳本靠這個找引擎)
export SCUMMVM_SRC="$PWD/scummvm-src"
export SCUMMVM="$SCUMMVM_SRC/scummvm"

# 3. 打包桌面三平台 (含遊戲的 FULL 包)
bash scripts/package_linux.sh
bash scripts/package_appimage.sh
bash scripts/build_windows.sh            # Docker mingw 交叉編譯
bash scripts/package_full.sh all         # -> dist/rotd-cht-FULL-*
```

## 改東西時

- **只改翻譯**：編 `translations/zh.json` → `python3 tools/build_translation.py translations/zh.json build/zh.dtr` → 部署各平台的 `zh.dtr`（Linux `share/rotd-cht/`、Win/Mac `extra/`、Android bundle、AppImage 在映像內）。**免重編引擎**。撈沒翻到的 TTM 字：`tools/extract_ttm_strings.py`。
- **改引擎**：改 `scummvm-src/engines/dgds/*` → `make` → 重產 patch：`(cd scummvm-src && git diff HEAD -- engines/dgds) > patches/dgds-cjk.patch` → 全平台重編。
- **commit/push**：repo remote = `git@github.com:wicanr2/Rise-of-the-dragon-cht.git`。遊戲/`dist/`/`game_en/`/`screenshots/` 全 gitignore，**永不 push**。

## Mac / Android（走 CI）

macOS `.app` 與 Android 空殼 APK 由 GitHub Actions 編（`.github/workflows/build.yml`，push `patches/**`、`translations/**`、`tools/**` 觸發）：

```bash
gh run download <run-id> -n rotd-cht-macos  -D dist/ci   # -> 套進 package_full.sh mac
gh run download <run-id> -n rotd-cht-android -D dist/ci  # -> tools/inject_android.sh 注入遊戲
```

完整 SOP 與所有踩過的坑見 `docs/DESIGN-cjk-engine.md` 的「實作後記」。
