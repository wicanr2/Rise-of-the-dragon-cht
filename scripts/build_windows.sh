#!/usr/bin/env bash
# Cross-compile the patched ScummVM (dgds engine only) for Windows x86_64 using
# mingw-w64 + SDL2, entirely in Docker (host stays clean; source is copied, not built
# in place). Produces dist/rotd-cht-windows-x86_64/ with scummvm.exe + SDL2.dll + assets.
set -e
cd "$(dirname "$0")/.."
SRC="${SCUMMVM_SRC:-/home/anr2/zak-zh/tools/scummvm-src}"
SDL2VER=2.30.9
docker run --rm \
  -v "$PWD":/work -v "$SRC":/src:ro -w /work rotd-emu:latest bash -c '
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null 2>&1
  apt-get install -y -qq g++-mingw-w64-x86-64 mingw-w64-tools curl xz-utils >/dev/null 2>&1
  # SDL2 mingw development libraries
  cd /tmp
  curl -fsSL -o sdl2.tar.gz \
    https://github.com/libsdl-org/SDL/releases/download/release-'"$SDL2VER"'/SDL2-devel-'"$SDL2VER"'-mingw.tar.gz
  tar xf sdl2.tar.gz
  SDLDIR=/tmp/SDL2-'"$SDL2VER"'/x86_64-w64-mingw32
  export PATH="$SDLDIR/bin:$PATH"
  # copy source (exclude vcs/build artifacts) so the host tree is untouched
  mkdir -p /tmp/build
  cp -a /src/. /tmp/build/ 2>/dev/null || true
  cd /tmp/build
  rm -f scummvm scummvm.exe config.log config.mk 2>/dev/null || true
  find . -name "*.o" -delete 2>/dev/null || true
  HOST=x86_64-w64-mingw32
  ./configure \
    --host=$HOST \
    --disable-all-engines --enable-engine=dgds \
    --with-sdl-prefix="$SDLDIR/bin" \
    --disable-fluidsynth --disable-flac --disable-mad --disable-vorbis \
    --disable-theoradec --disable-faad --disable-mpeg2 --disable-a52 \
    --disable-libcurl --disable-sndio --disable-timidity --disable-sparkle \
    --disable-nuked-opl --disable-eventrecorder \
    >/tmp/wincfg.log 2>&1 || { echo "CONFIGURE FAILED"; tail -30 /tmp/wincfg.log; exit 1; }
  echo "=== configure OK; building (this takes a few min) ==="
  make -j4 >/tmp/winmake.log 2>&1 || { echo "MAKE FAILED"; tail -40 /tmp/winmake.log; exit 1; }
  ls -la scummvm.exe
  mkdir -p /work/dist/rotd-cht-windows-x86_64
  cp scummvm.exe /work/dist/rotd-cht-windows-x86_64/
  cp "$SDLDIR/bin/SDL2.dll" /work/dist/rotd-cht-windows-x86_64/ 2>/dev/null || true
  # bundle mingw runtime DLLs the exe needs
  for dll in libgcc_s_seh-1 libstdc++-6 libwinpthread-1; do
    f=$(find /usr/lib/gcc/$HOST -name "$dll.dll" 2>/dev/null | head -1)
    [ -n "$f" ] && cp "$f" /work/dist/rotd-cht-windows-x86_64/ || true
  done
  echo "BUILD_OK"
  x86_64-w64-mingw32-objdump -p scummvm.exe 2>/dev/null | grep -i "DLL Name" | head -20
  chmod -R a+rw /work/dist/rotd-cht-windows-x86_64
'
