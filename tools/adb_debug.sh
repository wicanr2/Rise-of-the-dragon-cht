#!/usr/bin/env bash
# Drive the connected Android phone via adb INSIDE the rotd-adb Docker container
# (host stays clean). Confirms CPU ABI, installs the full APK, launches it, and
# captures the crash from logcat -- the decisive "why does it die on launch" signal.
#
# Prereq: USB debugging ON + this computer authorized on the phone.
# Usage: tools/adb_debug.sh [apk]   (default dist/rotd-cht-android-FULL.apk)
set -e
APK="${1:-dist/rotd-cht-android-FULL.apk}"
PKG="org.scummvm.scummvm.debug"
D() { docker exec rotd-adb bash -lc "$*"; }

echo "=== 1. 等待裝置 (USB 偵錯需已開 + 已授權) ==="
D "adb wait-for-device && adb devices -l"

echo "=== 2. 手機 CPU ABI (關鍵:有沒有 arm64-v8a) ==="
D "adb shell getprop ro.product.cpu.abilist; \
   echo -n 'model: '; adb shell getprop ro.product.model; \
   echo -n 'android: '; adb shell getprop ro.build.version.release"

echo "=== 3. 重新安裝 APK ==="
D "adb uninstall $PKG >/dev/null 2>&1 || true; adb install -r '$APK'"

echo "=== 4. 清 log、啟動、抓 crash (8 秒) ==="
D "adb logcat -c; \
   adb shell monkey -p $PKG -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; \
   sleep 8; \
   adb logcat -d -v brief 2>/dev/null | grep -iE 'AndroidRuntime|FATAL|scummvm|dlopen|UnsatisfiedLink|abort|SIGSEGV|libscummvm|$PKG' | tail -60"
