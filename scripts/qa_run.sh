#!/usr/bin/env bash
# Run a ScummVM ROTD autopilot headless with a chosen debug level, capture the log.
# Usage: qa_run.sh <autopilot.txt> <out.log> [seconds] [debuglevel]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SV="${SCUMMVM:-/home/anr2/zak-zh/tools/scummvm-src/scummvm}"
GAME="$ROOT/game_en/riseofthedragon"
AP="${1:?autopilot}"; LOG="${2:?log}"; SECS="${3:-35}"; DBG="${4:-2}"
cp "$AP" "$GAME/autopilot.txt"
DISP=:95
Xvfb $DISP -screen 0 1280x960x24 >/tmp/xvfb95.log 2>&1 &
XV=$!
sleep 2
DISPLAY=$DISP "$SV" -d"$DBG" -p "$GAME" --no-fullscreen rise >"$LOG" 2>&1 &
SV_PID=$!
sleep "$SECS"
kill "$SV_PID" 2>/dev/null; sleep 1; kill -9 "$SV_PID" 2>/dev/null
kill "$XV" 2>/dev/null
echo "done: log=$LOG ($(wc -l <"$LOG") lines)"
