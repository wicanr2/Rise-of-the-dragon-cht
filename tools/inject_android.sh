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
[ -f build/android_libs/libc++_shared.so ] || { echo "missing build/android_libs/libc++_shared.so (arm64, from NDK r26d sysroot) -- liboboe.so needs it"; exit 1; }

# Refresh the localization assets from the canonical build/ artifacts so a stale snapshot in
# android_games/ can't silently ship an old translation (this bit us: desktop got the new zh.dtr
# but the APK kept the old one). Game data (VOLUME.*) in android_games/ is the static base.
for a in zh.dtr dragon_zh24.dcjk dragon_zh16.dcjk; do
  [ -f "build/$a" ] && cp -f "build/$a" "$GAMES/riseofthedragon/$a"
done
echo "android_games zh.dtr md5: $(md5sum "$GAMES/riseofthedragon/zh.dtr" | cut -d' ' -f1)"

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
  rm -rf /tmp/stage
  # ScummVM extracts the APK inner "assets/" tree (assets/assets/...) to files/assets and, when
  # assets_updated, mass-adds any game found under files/assets/games to the launcher. So the game
  # must live at assets/assets/games/<id> (DOUBLE assets) AND be listed in assets/MD5SUMS -- otherwise
  # it is neither extracted nor detected (launcher shows an empty game list).
  mkdir -p /tmp/stage/assets/assets/games
  cp -r build/android_games/riseofthedragon /tmp/stage/assets/assets/games/
  cp "'"$BASE"'" /tmp/work.apk

  # Runtime native-lib closure the CI base APK is missing (-> insta-crash on launch):
  #   libscummvm.so --NEEDED--> liboboe.so --NEEDED--> libc++_shared.so
  # CI only linked oboe in the build sysroot and never packaged the runtime .so; the prebuilt
  # oboe is c++_shared so it also needs libc++_shared.so. Bundle BOTH (arm64-v8a;
  # extractNativeLibs=true so plain deflate + no special page-align needed).
  mkdir -p /tmp/stage/lib/arm64-v8a
  wget -q https://dl.google.com/dl/android/maven2/com/google/oboe/oboe/1.9.0/oboe-1.9.0.aar -O /tmp/oboe.aar
  unzip -q -o /tmp/oboe.aar -d /tmp/oboe
  cp "$(find /tmp/oboe -name liboboe.so -path "*arm64*" | head -1)" /tmp/stage/lib/arm64-v8a/liboboe.so
  cp build/android_libs/libc++_shared.so /tmp/stage/lib/arm64-v8a/libc++_shared.so

  # Append the game files to MD5SUMS (paths are relative to files/, i.e. "assets/games/<id>/<f>").
  # A changed MD5SUMS makes ScummVM treat assets as updated -> it re-extracts the inner assets tree
  # (now incl. the game) and runs the one-shot bundled-game mass-add that registers it in the launcher.
  unzip -o -q /tmp/work.apk "assets/MD5SUMS" -d /tmp/md5
  ( cd /tmp/stage/assets && find assets/games -type f | sort | xargs md5sum ) >> /tmp/md5/assets/MD5SUMS
  cp /tmp/md5/assets/MD5SUMS /tmp/stage/assets/MD5SUMS

  # inject game (assets/assets/games) + libs (lib/) + updated MD5SUMS, drop the old signature
  ( cd /tmp/stage && zip -qr /tmp/work.apk assets lib )
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
