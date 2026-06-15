#!/usr/bin/env bash
# Inject the ROTD game + CJK assets into the CI-built base APK (assets/games/riseofthedragon/)
# and re-sign with a debug key -> a self-contained 繁中 Android APK that installs and plays.
# The game data is injected LOCALLY (never goes to GitHub/CI). Runs in Docker (host clean).
# FOR PERSONAL ARCHIVAL of a game you legally own -- do NOT redistribute.
#
# Usage: tools/inject_android.sh [base.apk]   (default: dist/ci/rotd-cht-android.apk)
set -e
cd "$(dirname "$0")/.."
BASE="${1:-dist/ci/rotd-cht-android.apk}"
GAMES="build/android_games"   # contains riseofthedragon/ (game + dcjk/dtr)
[ -f "$BASE" ] || { echo "base APK not found: $BASE"; exit 1; }
[ -d "$GAMES/riseofthedragon" ] || { echo "no game bundle at $GAMES/riseofthedragon"; exit 1; }

docker run --rm -v "$PWD":/work -w /work ubuntu:24.04 bash -c '
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null 2>&1
  apt-get install -y -qq openjdk-17-jdk-headless wget unzip zip >/dev/null 2>&1
  # Android build-tools (apksigner + zipalign) via cmdline-tools (small, no NDK)
  export ANDROID_SDK_ROOT=/opt/asdk
  mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools"
  cd /tmp
  wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O ct.zip
  unzip -q ct.zip -d "$ANDROID_SDK_ROOT/cmdline-tools"
  mv "$ANDROID_SDK_ROOT/cmdline-tools/cmdline-tools" "$ANDROID_SDK_ROOT/cmdline-tools/latest"
  yes | "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null 2>&1 || true
  "$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" "build-tools;35.0.0" >/dev/null
  BT="$ANDROID_SDK_ROOT/build-tools/35.0.0"

  cd /work
  rm -rf /tmp/stage; mkdir -p /tmp/stage/assets/games
  cp -r build/android_games/riseofthedragon /tmp/stage/assets/games/
  cp "'"$BASE"'" /tmp/work.apk

  # inject game+assets into the APK, drop the old signature
  ( cd /tmp/stage && zip -qr /tmp/work.apk assets )
  zip -q -d /tmp/work.apk "META-INF/*" >/dev/null 2>&1 || true

  # align (uncompressed entries to 4 bytes) then sign with a generated debug key
  "$BT/zipalign" -p -f 4 /tmp/work.apk /tmp/aligned.apk
  keytool -genkeypair -keystore /tmp/debug.ks -alias rotd -storepass android -keypass android \
    -dname "CN=ROTD-CHT" -keyalg RSA -keysize 2048 -validity 10000 >/dev/null 2>&1
  "$BT/apksigner" sign --ks /tmp/debug.ks --ks-pass pass:android --key-pass pass:android \
    --out /work/dist/rotd-cht-android-FULL.apk /tmp/aligned.apk
  "$BT/apksigner" verify /work/dist/rotd-cht-android-FULL.apk && echo "SIGNED OK"
  chmod a+rw /work/dist/rotd-cht-android-FULL.apk
'
ls -la dist/rotd-cht-android-FULL.apk 2>/dev/null && \
  echo "完整中文 APK -> dist/rotd-cht-android-FULL.apk (全新安裝即可)"
