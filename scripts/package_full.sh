#!/usr/bin/env bash
# Build SELF-CONTAINED "full" packages = patched ScummVM + CJK assets + the actual ROTD game
# data, so it plays by just running the launcher (auto-detects the bundled game/). FOR PERSONAL
# ARCHIVAL of a game you legally own -- the game data is copyrighted; do NOT redistribute.
# Output -> dist/<name>/ (+ .tar.gz/.zip), all gitignored.
#
# Usage: scripts/package_full.sh [linux|appimage|windows|all] [game-data-dir]
set -euo pipefail
cd "$(dirname "$0")/.."
PLAT="${1:-linux}"
GAMESRC="${2:-game_en/riseofthedragon}"
BUNDLE="dist/rotd-cht-linux-x86_64"
WINBUN="dist/rotd-cht-windows-x86_64"
APPIMG="dist/Rise-of-the-Dragon-CHT-x86_64.AppImage"

[ -f "$GAMESRC/VOLUME.VGA" ] || [ -f "$GAMESRC/volume.vga" ] || { echo "no ROTD game data in $GAMESRC"; exit 1; }

# copy ONLY original game files (exclude CJK overlay assets + dev cruft) into $1/game
copy_game() {
  mkdir -p "$1/game"
  ( cd "$GAMESRC" && find . -maxdepth 1 -type f \
      ! -iname '*.dcjk' ! -iname '*.dtr' ! -iname 'autopilot.txt' \
      -exec cp {} "$OLDPWD/$1/game/" \; )
}
readme() {  # $1 = dir, $2 = "執行的東西" line
  cat > "$1/README.txt" <<DOC
Rise of the Dragon 繁體中文版 — 完整自留包
==========================================
★ 整包：patched ScummVM + 繁中資產 + 遊戲本體(game/)，放著就能玩。

玩法
  $2
  預設中文 24×24；遊戲中按 F8 循環 中文24 / 中文16 / 德文 / 英文。

⚠ 版權：本包含受版權的遊戲本體(Dynamix / Sierra 之權利繼承者)。
  僅供你個人、對你合法擁有之遊戲的存檔與遊玩，請勿散布／公開分享。
DOC
}
archive_tar() { ( cd dist && tar czf "$1.tar.gz" "$1" ); echo "  -> dist/$1.tar.gz ($(du -h "dist/$1.tar.gz"|cut -f1))"; }
archive_zip() { docker run --rm -v "$PWD":/work -w /work rotd-emu:latest bash -c \
  "(command -v zip>/dev/null)||{ apt-get update -qq>/dev/null 2>&1; apt-get install -y -qq zip>/dev/null 2>&1;}; cd dist && rm -f '$1.zip' && zip -qr '$1.zip' '$1' && chmod a+rw '$1.zip'"; echo "  -> dist/$1.zip ($(du -h "dist/$1.zip"|cut -f1))"; }

build_linux() {
  [ -d "$BUNDLE" ] || { echo "run package_linux.sh first"; return 1; }
  local N=rotd-cht-FULL-linux-x86_64 O=dist/rotd-cht-FULL-linux-x86_64
  rm -rf "$O"; mkdir -p "$O"
  cp -r "$BUNDLE/bin" "$BUNDLE/lib" "$BUNDLE/share" "$BUNDLE/rotd-cht.sh" "$O/"
  copy_game "$O"; readme "$O" "執行 ./rotd-cht.sh —— 會自動偵測同目錄的 game/ 並用中文啟動。"
  chmod +x "$O/rotd-cht.sh"; echo "[linux] $O"; archive_tar "$N"
}
build_appimage() {
  [ -f "$APPIMG" ] || { echo "run package_appimage.sh first"; return 1; }
  local N=rotd-cht-FULL-appimage O=dist/rotd-cht-FULL-appimage
  rm -rf "$O"; mkdir -p "$O"
  cp "$APPIMG" "$O/"
  copy_game "$O"; readme "$O" "執行旁邊的 Rise-of-the-Dragon-CHT-x86_64.AppImage —— 會自動偵測同目錄的 game/。"
  echo "[appimage] $O"; archive_tar "$N"
}
build_windows() {
  [ -d "$WINBUN" ] || { echo "run build_windows.sh first"; return 1; }
  local N=rotd-cht-FULL-windows-x86_64 O=dist/rotd-cht-FULL-windows-x86_64
  rm -rf "$O"; mkdir -p "$O"
  cp "$WINBUN/scummvm.exe" "$WINBUN/SDL2.dll" "$WINBUN/play-rotd-cht.bat" "$O/"
  cp -r "$WINBUN/extra" "$O/"
  copy_game "$O"; readme "$O" "雙擊 play-rotd-cht.bat —— 會自動偵測同目錄的 game/ 並用中文啟動。"
  echo "[windows] $O"; archive_zip "$N"
}

build_mac() {
  # macOS binary can't be cross-compiled from Linux (needs Apple's SDK). Ship a template:
  # game + CJK assets + the engine patch + native-build recipe. User builds scummvm on a Mac.
  local N=rotd-cht-FULL-mac-template O=dist/rotd-cht-FULL-mac-template
  rm -rf "$O"; mkdir -p "$O/share/rotd-cht" "$O/patches" "$O/bin"
  cp build/zh.dtr build/de.dtr build/dragon_zh24.dcjk build/dragon_zh16.dcjk "$O/share/rotd-cht/" 2>/dev/null || true
  cp patches/dgds-cjk.patch "$O/patches/" 2>/dev/null || true
  cp scripts/build_macos.sh "$O/" 2>/dev/null || true
  copy_game "$O"
  cat > "$O/README.txt" <<'DOC'
Rise of the Dragon 繁體中文版 — Mac 完整包「模板」
==================================================
⚠ 這包少了一樣東西：bin/scummvm（macOS 執行檔）。Apple 的 macOS SDK 受版權，
  無法從 Linux 交叉編譯，所以這顆 binary 必須「在 Mac 上」編。其餘都備齊了。

在 Mac 上完成（一次）
  1) brew install sdl2 freetype libpng libvorbis flac mad faad2 fluid-synth
  2) git clone https://github.com/scummvm/scummvm && cd scummvm
     git apply /path/to/patches/dgds-cjk.patch
  3) bash /path/to/build_macos.sh   （或見其中註解手動 configure && make）
  4) 把產生的 scummvm 放進本資料夾的 bin/，然後執行：
        bin/scummvm --extrapath=share/rotd-cht --path=game rise
  預設中文；F8 循環 中24/中16/德/英。

內容
  game/               遊戲本體（你合法擁有的那份）
  share/rotd-cht/      語言資產 zh/de + dragon_zh24/16.dcjk
  patches/dgds-cjk.patch  繁中引擎 patch
  build_macos.sh      native 編譯腳本（在 Mac 上跑）
⚠ 含受版權遊戲本體，僅供你個人存檔／遊玩，請勿散布。
DOC
  echo "[mac-template] $O"; archive_tar "$N"
}

case "$PLAT" in
  linux)    build_linux ;;
  appimage) build_appimage ;;
  windows)  build_windows ;;
  mac)      build_mac ;;
  all)      build_linux; build_appimage; build_windows; build_mac ;;
  *) echo "usage: $0 [linux|appimage|windows|mac|all] [game-dir]"; exit 1 ;;
esac
