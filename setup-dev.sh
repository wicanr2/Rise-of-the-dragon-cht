#!/usr/bin/env bash
# Rebuild the ROTD CHT dev environment on a fresh machine: clone ScummVM at the patch base,
# apply the engine + Android patches, and build the dgds engine. Run from the repo root after
# extracting the dev tarball.  Needs: git, a C++ toolchain, SDL2/freetype/libpng dev headers
# (Debian/Ubuntu: build-essential libsdl2-dev libfreetype-dev libpng-dev).
set -e
cd "$(dirname "$0")"
ROOT="$PWD"
SCUMMVM_COMMIT=f4526cf007688d02b8c558f048f0889088545fd5   # keep in sync with .github/workflows/build.yml
SRC="$ROOT/scummvm-src"

echo "== 1/3  ScummVM source @ $SCUMMVM_COMMIT =="
if [ ! -d "$SRC/.git" ]; then
  git clone https://github.com/scummvm/scummvm "$SRC"
fi
cd "$SRC"
git checkout -f "$SCUMMVM_COMMIT"
git checkout -- . 2>/dev/null || true   # discard any prior patch so re-running is idempotent

echo "== 2/3  apply ROTD CHT patches =="
for p in dgds-cjk android-surface-race android-autostart-rise; do
  git apply "$ROOT/patches/$p.patch" || patch -p1 < "$ROOT/patches/$p.patch"
  echo "   applied patches/$p.patch"
done

echo "== 3/3  build (dgds engine only) =="
./configure --disable-all-engines --enable-engine=dgds --enable-release
make -j"$(nproc)"

cat <<EOF

✅ Built: $SRC/scummvm

Next — export these so the package scripts find the engine, then build packages:

  export SCUMMVM_SRC="$SRC"
  export SCUMMVM="$SRC/scummvm"

  # regenerate CJK assets if build/ is missing (needs fonts-noto-cjk + python3 freetype-py pillow):
  #   python3 tools/build_cjk_font.py --size 24 --out build/dragon_zh24.dcjk
  #   python3 tools/build_cjk_font.py --size 16 --out build/dragon_zh16.dcjk
  #   python3 tools/build_translation.py translations/zh.json build/zh.dtr

  bash scripts/package_linux.sh        # -> dist/rotd-cht-linux-x86_64
  bash scripts/package_appimage.sh     # -> AppImage
  bash scripts/build_windows.sh        # Docker mingw cross-build
  bash scripts/package_full.sh all     # FULL packages (engine + zh.dtr + game_en)

macOS .app + Android APK come from CI (.github/workflows/build.yml); see DEV-SETUP.md.
EOF
