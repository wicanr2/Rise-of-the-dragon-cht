#!/usr/bin/env bash
# Package the patched ScummVM + ROTD-CHT language assets into a relocatable Linux
# bundle (bin + bundled libs + assets + launcher) and a .tar.gz. Pure host file-ops;
# nothing installed system-wide. Output: dist/.
#
# The bundle relies on the user's SYSTEM glibc + display stack (GL/X11/wayland) and
# bundles everything else (SDL2, freetype, fluidsynth, codecs) so it runs on most
# modern x86_64 Linux. The user supplies their own legally-owned ROTD game data.
set -euo pipefail
cd "$(dirname "$0")/.."
SV="${SCUMMVM:-/home/anr2/zak-zh/tools/scummvm-src/scummvm}"
NAME="rotd-cht-linux-x86_64"
OUT="dist/$NAME"
ASSETS=(build/zh.dtr build/de.dtr build/ja.dtr build/dragon_zh24.dcjk build/dragon_zh16.dcjk build/dragon_ja24.dcjk)

[ -x "$SV" ] || { echo "ERROR: scummvm binary not found at $SV"; exit 1; }
rm -rf "$OUT"; mkdir -p "$OUT/bin" "$OUT/lib" "$OUT/share/rotd-cht"

cp "$SV" "$OUT/bin/scummvm"

# Keep these from the user's SYSTEM (glibc/kernel + GPU/display stack must match host).
KEEP_SYSTEM='ld-linux|/libc\.|/libm\.|/libdl\.|/libpthread\.|/librt\.|/libresolv\.|linux-vdso|/libGL|/libGLX|/libGLdispatch|/libX11|/libxcb|/libXext|/libXcursor|/libXi|/libXrandr|/libXfixes|/libXrender|/libwayland|/libdrm|/libgbm|/libEGL|/libOpenGL'
echo "Bundling libraries (excluding system glibc/display stack)..."
ldd "$SV" | awk '{print $3}' | grep -E '^/' | sort -u | while read -r lib; do
  if echo "$lib" | grep -qE "$KEEP_SYSTEM"; then continue; fi
  cp -L "$lib" "$OUT/lib/" 2>/dev/null && echo "  + $(basename "$lib")"
done

# Language assets
for a in "${ASSETS[@]}"; do
  [ -f "$a" ] && cp "$a" "$OUT/share/rotd-cht/" || echo "  ! missing asset $a"
done

# Launcher: bundles libs via LD_LIBRARY_PATH; --extrapath makes the engine find the
# CJK/German assets via SearchMan regardless of the user's game directory.
cat > "$OUT/rotd-cht.sh" <<'LAUNCH'
#!/usr/bin/env bash
# Rise of the Dragon 繁體中文版 launcher.
# 用法: ./rotd-cht.sh [你的遊戲資料夾]
#   給遊戲資料夾 -> 直接啟動並載入；不給 -> 開啟 ScummVM 啟動器自行加入遊戲。
# 遊戲中按 F8 循環顯示模式：中文24 / 中文16 / 德文 / 日文 / 英文。F9 循環語音。
HERE="$(cd "$(dirname "$0")" && pwd)"
export LD_LIBRARY_PATH="$HERE/lib:${LD_LIBRARY_PATH:-}"
SV="$HERE/bin/scummvm"; EXTRA="$HERE/share/rotd-cht"
has_game() { [ -f "$1/volume.vga" ] || [ -f "$1/VOLUME.VGA" ] || [ -f "$1/RESOURCE.MAP" ]; }
if [ $# -ge 1 ] && [ -d "$1" ]; then
  exec "$SV" --extrapath="$EXTRA" --path="$1" rise
fi
# auto-detect a ROTD game folder next to this launcher or in CWD
for base in "$HERE" "$PWD"; do
  has_game "$base" && exec "$SV" --extrapath="$EXTRA" --path="$base" rise
  for d in "$base"/*/; do
    [ -d "$d" ] && has_game "$d" && exec "$SV" --extrapath="$EXTRA" --path="$d" rise
  done
done
exec "$SV" --extrapath="$EXTRA"
LAUNCH
chmod +x "$OUT/rotd-cht.sh"

# Readme (繁中)
cat > "$OUT/README.txt" <<'DOC'
Rise of the Dragon 繁體中文版 (patched ScummVM bundle)
======================================================

這是把 Dynamix《Rise of the Dragon》(1990) 中文化的 patched ScummVM。
中文是「疊」在原始英文遊戲上的 overlay，不會改動你的遊戲檔。

需要準備
  你自己合法擁有的一份《Rise of the Dragon》遊戲資料夾（內含 VOLUME.VGA 等）。

啟動（三選一）
  1) 自動偵測（最省事）：把本資料夾放到「你的遊戲資料夾旁邊」或「遊戲資料夾裡」，
     直接執行 ./rotd-cht.sh —— 會自動找到遊戲、用中文啟動。
  2) 指定路徑：   ./rotd-cht.sh /路徑/到/你的/遊戲資料夾
  3) 用啟動器：   ./rotd-cht.sh （找不到遊戲時）會開 ScummVM 介面，手動加入遊戲一次即可。

預設就是中文（24×24）。遊戲中按 F8 循環：中文 24×24 → 中文 16×16 → 德文 → 日文 → 英文(原始)。
語音：按 F9 循環語音語言（英 / 日 / 中 / 德 / 關），可獨立於字幕語言。

內容
  bin/scummvm          patched ScummVM（dgds 引擎 + CJK 模組）
  lib/                 隨附函式庫（SDL2、freetype、fluidsynth、codecs…）
  share/rotd-cht/      語言資產：zh.dtr(中文)、de.dtr(德文)、ja.dtr(日文)、dragon_zh24/16.dcjk + dragon_ja24.dcjk(點陣字型)

說明
  - 本套件相依你系統的 glibc 與顯示(GL/X11/Wayland)堆疊，適用多數現代 x86_64 Linux。
  - 若 share/ 裡的資產沒被讀到，可改放到你的遊戲資料夾旁（引擎也會從那裡找）。
  - 不含、也不重新發布任何遊戲原始檔；版權屬 Dynamix / Sierra 之權利繼承者。
DOC

# Tarball
mkdir -p dist
( cd dist && tar czf "$NAME.tar.gz" "$NAME" )
echo "----"
echo "bundle : $OUT"
echo "tarball: dist/$NAME.tar.gz ($(du -h "dist/$NAME.tar.gz" | cut -f1))"
echo "libs bundled: $(ls "$OUT/lib" | wc -l)"
