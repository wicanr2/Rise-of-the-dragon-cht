#!/usr/bin/env bash
# Build the patched ScummVM (dgds + CHT) for macOS and bundle a .app. RUN THIS ON A MAC
# (macOS can't be cross-compiled from Linux without the proprietary SDK). Documented recipe
# to complete Phase 5; mirrors the Linux/Windows builds.
#
# Prereqs on the Mac:
#   - Xcode command line tools (xcode-select --install)
#   - Homebrew + deps: brew install sdl2 freetype libpng libvorbis flac mad faad2 fluid-synth
#   - The patched ScummVM source tree (this repo's patches/dgds-cjk.patch applied), e.g.:
#       git clone https://github.com/scummvm/scummvm && cd scummvm
#       git apply /path/to/rise-of-the-dragon/patches/dgds-cjk.patch
#   - The CHT language assets built (build/zh.dtr de.dtr dragon_zh24.dcjk dragon_zh16.dcjk)
set -euo pipefail
SRC="${SCUMMVM_SRC:?set SCUMMVM_SRC to the patched scummvm source dir}"
ASSETS_DIR="${ASSETS_DIR:-$(cd "$(dirname "$0")/.." && pwd)/build}"
OUT="${OUT:-$(cd "$(dirname "$0")/.." && pwd)/dist}"
APP="$OUT/Rise of the Dragon CHT.app"

cd "$SRC"
# dgds-only build keeps it small; drop --disable-all-engines to build the full ScummVM.
./configure --disable-all-engines --enable-engine=dgds --enable-release
make -j"$(sysctl -n hw.ncpu)"

# ScummVM's bundle target produces ScummVM.app; or assemble manually:
make bundle 2>/dev/null || true
rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/extra"
cp scummvm "$APP/Contents/MacOS/"
cp "$ASSETS_DIR"/zh.dtr "$ASSETS_DIR"/de.dtr \
   "$ASSETS_DIR"/dragon_zh24.dcjk "$ASSETS_DIR"/dragon_zh16.dcjk \
   "$APP/Contents/Resources/extra/"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Rise of the Dragon CHT</string>
  <key>CFBundleExecutable</key><string>scummvm</string>
  <key>CFBundleIdentifier</key><string>org.scummvm.rotd-cht</string>
  <key>CFBundlePackageType</key><string>APPL</string>
</dict></plist>
PLIST

# Bundle dylibs so it runs on other Macs (otool/dylibbundler):
#   brew install dylibbundler
#   dylibbundler -od -b -x "$APP/Contents/MacOS/scummvm" -d "$APP/Contents/libs" -p @executable_path/../libs
echo "Built: $APP"
echo "Run:   open '$APP'  (then add your ROTD game; set Extra Path to Contents/Resources/extra)"
echo "       In-game F8 cycles EN / ZH24 / ZH16 / DE."
