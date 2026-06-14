#!/usr/bin/env bash
# Build a single-file AppImage from the relocatable bundle. The AppDir (host binary +
# host-compatible bundled libs + assets) is assembled on the host; appimagetool runs in
# Docker (no host pollution). Output: dist/Rise-of-the-Dragon-CHT-x86_64.AppImage
set -euo pipefail
cd "$(dirname "$0")/.."
BUNDLE="dist/rotd-cht-linux-x86_64"
APPDIR="dist/ROTD-CHT.AppDir"
[ -d "$BUNDLE" ] || { echo "run scripts/package_linux.sh first (need $BUNDLE)"; exit 1; }

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/share/rotd-cht"
cp "$BUNDLE/bin/scummvm"        "$APPDIR/usr/bin/"
cp -r "$BUNDLE/lib/."           "$APPDIR/usr/lib/"
cp -r "$BUNDLE/share/rotd-cht/." "$APPDIR/usr/share/rotd-cht/"

# AppRun: launches the game directly. Order of preference for the game folder:
#   1) a path given as an argument (drag-drop / terminal)
#   2) AUTO-DETECT: a ROTD folder (has volume.vga) next to the AppImage or in CWD
#   3) otherwise open the ScummVM launcher (user adds the game once)
# --extrapath makes the engine find the bundled CJK/DE assets -> Chinese by default.
cat > "$APPDIR/AppRun" <<'RUN'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export LD_LIBRARY_PATH="$HERE/usr/lib:${LD_LIBRARY_PATH:-}"
SV="$HERE/usr/bin/scummvm"
EXTRA="$HERE/usr/share/rotd-cht"
has_game() { [ -f "$1/volume.vga" ] || [ -f "$1/VOLUME.VGA" ] || [ -f "$1/RESOURCE.MAP" ]; }
# 1) explicit path
if [ $# -ge 1 ] && [ -d "$1" ]; then
  exec "$SV" --extrapath="$EXTRA" --path="$1" rise
fi
# 2) auto-detect near the .AppImage file and the current dir (and one level of subdirs)
APPDIR_OF_IMG="$(dirname "$(readlink -f "${APPIMAGE:-$0}")")"
for base in "$APPDIR_OF_IMG" "$PWD"; do
  has_game "$base" && exec "$SV" --extrapath="$EXTRA" --path="$base" rise
  for d in "$base"/*/; do
    [ -d "$d" ] && has_game "$d" && exec "$SV" --extrapath="$EXTRA" --path="$d" rise
  done
done
# 3) fallback: launcher (Extra Path preset so an added game still renders Chinese)
exec "$SV" --extrapath="$EXTRA"
RUN
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/rotd-cht.desktop" <<'DESK'
[Desktop Entry]
Type=Application
Name=Rise of the Dragon CHT
Comment=繁體中文版 (patched ScummVM)
Exec=AppRun
Icon=rotd-cht
Categories=Game;
Terminal=false
DESK

# Icon: a crop of the Chinese dialogue showcase (256x256), else a solid placeholder.
if command -v convert >/dev/null 2>&1 && [ -f screenshots/bundle_zh.png ]; then
  convert screenshots/bundle_zh.png -gravity center -crop 400x400+0-40 +repage \
    -resize 256x256 "$APPDIR/rotd-cht.png" 2>/dev/null || \
    convert -size 256x256 xc:black -fill white -gravity center -pointsize 40 \
      -annotate 0 "龍" "$APPDIR/rotd-cht.png"
else
  : > "$APPDIR/rotd-cht.png"
fi
cp "$APPDIR/rotd-cht.png" "$APPDIR/.DirIcon" 2>/dev/null || true

# appimagetool in Docker (extract-and-run: no FUSE needed)
docker run --rm -v "$PWD":/work -w /work rotd-emu:latest bash -c '
  set -e
  apt-get install -y -qq curl file >/dev/null 2>&1 || true
  command -v curl >/dev/null || { apt-get update -qq >/dev/null 2>&1; apt-get install -y -qq curl file >/dev/null 2>&1; }
  cd /tmp
  curl -fsSL -o appimagetool.AppImage \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x appimagetool.AppImage
  ./appimagetool.AppImage --appimage-extract >/dev/null 2>&1
  cd /work
  ARCH=x86_64 /tmp/squashfs-root/AppRun dist/ROTD-CHT.AppDir \
    dist/Rise-of-the-Dragon-CHT-x86_64.AppImage 2>&1 | tail -5
  chmod a+rwx dist/Rise-of-the-Dragon-CHT-x86_64.AppImage 2>/dev/null || true
'
ls -la dist/Rise-of-the-Dragon-CHT-x86_64.AppImage 2>/dev/null && \
  echo "AppImage built." || echo "AppImage build did not produce output (check log above)."
