#!/usr/bin/env bash
# Launch ScummVM ROTD headless under Xvfb, capture a screenshot after N seconds.
# Usage: run_headless.sh <out.png> [seconds] [extra scummvm args...]
set -u
SV="${SCUMMVM:-/home/anr2/zak-zh/tools/scummvm-src/scummvm}"
GAME=/home/anr2/rise-of-the-dragon/game
OUT="${1:-/home/anr2/rise-of-the-dragon/screenshots/baseline.png}"; shift || true
SECS="${1:-8}"; shift || true
DISP=:99
Xvfb $DISP -screen 0 1280x960x24 >/tmp/xvfb.log 2>&1 &
XVFB_PID=$!
sleep 1
DISPLAY=$DISP $SV -p "$GAME" --no-fullscreen --gfx-mode=2x "$@" rise >/tmp/scummvm.log 2>&1 &
SV_PID=$!
sleep "$SECS"
DISPLAY=$DISP import -window root "$OUT" 2>/tmp/import.log
echo "screenshot -> $OUT ($(identify -format '%wx%h' "$OUT" 2>/dev/null))"
kill $SV_PID 2>/dev/null; sleep 1; kill -9 $SV_PID 2>/dev/null
kill $XVFB_PID 2>/dev/null
echo "=== scummvm log tail ==="; tail -8 /tmp/scummvm.log
