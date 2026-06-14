#!/usr/bin/env bash
# Cross-compile the patched ScummVM (dgds + CHT) into an Android APK, with the ROTD game +
# CJK assets bundled in (self-contained). Runs in Docker (host stays clean). Big build:
# downloads JDK17 + Android SDK + NDK 23.2.8568313 + Gradle 9.3 (~2GB) then compiles.
# Output: dist/rotd-cht-android.apk
set -e
cd "$(dirname "$0")/.."
SRC="${SCUMMVM_SRC:-/home/anr2/zak-zh/tools/scummvm-src}"
GAMES="$(pwd)/build/android_games"   # contains riseofthedragon/ (game + dcjk/dtr)
docker run --rm -v "$PWD":/work -v "$SRC":/src:ro -w /work ubuntu:24.04 bash -c '
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null 2>&1
  apt-get install -y -qq openjdk-17-jdk-headless wget unzip build-essential git >/dev/null 2>&1

  # --- Android SDK command-line tools ---
  export ANDROID_SDK_ROOT=/opt/android-sdk
  mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools"
  cd /tmp
  wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O cmdtools.zip
  unzip -q cmdtools.zip -d "$ANDROID_SDK_ROOT/cmdline-tools"
  mv "$ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools" "$ANDROID_SDK_ROOT/cmdline-tools/latest"
  export PATH="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH"
  yes | sdkmanager --licenses >/dev/null 2>&1 || true
  echo "Installing SDK packages (platform-tools, android-35, build-tools, ndk 23.2)..."
  sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0" "ndk;23.2.8568313" >/tmp/sdk.log 2>&1 || { echo SDKMGR_FAIL; tail -20 /tmp/sdk.log; exit 1; }
  export ANDROID_NDK_ROOT="$ANDROID_SDK_ROOT/ndk/23.2.8568313"

  # --- copy scummvm source (host tree untouched) ---
  mkdir -p /tmp/build && cp -a /src/. /tmp/build/ 2>/dev/null || true
  cd /tmp/build
  rm -f scummvm scummvm.exe config.log config.mk 2>/dev/null || true
  find . -name "*.o" -delete 2>/dev/null || true

  echo "=== configure (android-arm64-v8a, dgds-only) ==="
  ./configure --host=android-arm64-v8a --enable-release \
    --disable-all-engines --enable-engine=dgds \
    >/tmp/acfg.log 2>&1 || { echo CONFIGURE_FAIL; tail -40 /tmp/acfg.log; exit 1; }

  echo "=== build debug APK with bundled game (this takes a while) ==="
  make -j4 androiddebug GAMES_BUNDLE_DIRECTORY=/work/build/android_games >/tmp/amake.log 2>&1 \
    || { echo "MAKE androiddebug FAILED; trying without games bundle"; \
         make -j4 androiddebug >>/tmp/amake.log 2>&1 || { echo MAKE_FAIL; tail -50 /tmp/amake.log; exit 1; }; }

  APK=$(ls -1 *.apk 2>/dev/null | head -1)
  [ -n "$APK" ] || { echo NO_APK; ls -la; tail -30 /tmp/amake.log; exit 1; }
  cp "$APK" /work/dist/rotd-cht-android.apk
  echo "APK_BUILT: $(ls -la /work/dist/rotd-cht-android.apk | awk "{print \$5}") bytes"
  chmod a+rw /work/dist/rotd-cht-android.apk
'
ls -la dist/rotd-cht-android.apk 2>/dev/null && echo "Android APK -> dist/rotd-cht-android.apk"
