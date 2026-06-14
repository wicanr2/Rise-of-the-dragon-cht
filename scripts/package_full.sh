#!/usr/bin/env bash
# Build a SELF-CONTAINED "full" package = patched ScummVM bundle + CJK assets + the actual
# ROTD game data, so it plays by just running the launcher. FOR PERSONAL ARCHIVAL of a game
# you legally own -- the game data is copyrighted; do NOT redistribute this package.
# Output -> dist/<name>/ + dist/<name>.tar.gz  (gitignored).
#
# Usage: scripts/package_full.sh [game-data-dir]   (default: game_en/riseofthedragon)
set -euo pipefail
cd "$(dirname "$0")/.."
GAMESRC="${1:-game_en/riseofthedragon}"
BUNDLE="dist/rotd-cht-linux-x86_64"
NAME="rotd-cht-FULL-linux-x86_64"
OUT="dist/$NAME"

[ -d "$BUNDLE" ] || { echo "run scripts/package_linux.sh first (need $BUNDLE)"; exit 1; }
[ -f "$GAMESRC/VOLUME.VGA" ] || [ -f "$GAMESRC/volume.vga" ] || { echo "no ROTD game data in $GAMESRC"; exit 1; }

rm -rf "$OUT"; mkdir -p "$OUT/game"
# copy the runnable bundle (bin/lib/share/launcher) — but NOT its README (we write a full one)
cp -r "$BUNDLE/bin" "$BUNDLE/lib" "$BUNDLE/share" "$BUNDLE/rotd-cht.sh" "$OUT/"
# copy ONLY the original game files (exclude the CJK overlay assets + dev cruft)
( cd "$GAMESRC" && \
  find . -maxdepth 1 -type f \
    ! -iname '*.dcjk' ! -iname '*.dtr' ! -iname 'autopilot.txt' \
    -exec cp {} "$OLDPWD/$OUT/game/" \; )

cat > "$OUT/README.txt" <<'DOC'
Rise of the Dragon 繁體中文版 — 完整自留包 (Linux)
==================================================

★ 這是「整包」：patched ScummVM + 繁中語言資產 + 遊戲本體，放著就能玩。

玩法
  執行  ./rotd-cht.sh   —— 啟動器會自動偵測同目錄下的 game/ 並用中文啟動。
  預設中文 24×24；遊戲中按 F8 循環 中文24 / 中文16 / 德文 / 英文。

內容
  rotd-cht.sh          啟動器（自動偵測 game/）
  bin/scummvm + lib/   patched ScummVM（dgds 引擎 + CJK 模組）+ 隨附函式庫
  share/rotd-cht/      語言資產：zh.dtr de.dtr dragon_zh24/16.dcjk
  game/                《Rise of the Dragon》遊戲資料（你合法擁有的那份）

⚠ 版權與用途
  本包含有受版權的遊戲本體（Dynamix / Sierra 之權利繼承者）。
  僅供「你個人、對你合法擁有之遊戲」的存檔與遊玩，**請勿散布／公開分享**。
  中文化部分（patch / 譯文 / 字型）為衍生作品。
DOC
chmod +x "$OUT/rotd-cht.sh"

mkdir -p dist
( cd dist && tar czf "$NAME.tar.gz" "$NAME" )
echo "----"
echo "完整包資料夾: $OUT"
echo "完整包壓縮檔: dist/$NAME.tar.gz ($(du -h "dist/$NAME.tar.gz" | cut -f1))"
echo "game/ 檔案: $(ls "$OUT/game" | wc -l) 個"
