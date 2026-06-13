#!/usr/bin/env bash
# Headless smoke test: launch the packaged bundle and screenshot it, to prove the
# relocatable bundle renders the game (and Chinese) end-to-end.
set -u
B="$(cd "$(dirname "$0")/.." && pwd)/dist/rotd-cht-linux-x86_64"
GAME="${1:-$(cd "$(dirname "$0")/.." && pwd)/game_en/riseofthedragon}"
OUT="${2:-$(cd "$(dirname "$0")/.." && pwd)/screenshots/bundle_test.png}"
DISP=:97
Xvfb $DISP -screen 0 1280x960x24 >/tmp/xvfb97.log 2>&1 &
XV=$!
sleep 2
DISPLAY=$DISP "$B/rotd-cht.sh" "$GAME" >/tmp/bundle_render.log 2>&1 &
SV=$!
sleep 9
DISPLAY=$DISP import -window root "$OUT" 2>/dev/null
echo "screenshot: $(identify -format '%wx%h' "$OUT" 2>/dev/null || echo none)"
kill "$SV" 2>/dev/null; sleep 1; kill -9 "$SV" 2>/dev/null
kill "$XV" 2>/dev/null
echo "--- bundle render log tail ---"
tail -6 /tmp/bundle_render.log
