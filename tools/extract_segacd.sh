#!/usr/bin/env bash
# Extract the Sega CD Japanese ROTD disc for Japanese-text harvesting.
# Needs chdman (mame-tools). Output stays local (gitignored).
set -e
CHD="Rise of the Dragon - A Blade Hunter Mystery (Japan).chd"
OUT=segacd_ja
chdman extractcd -i "$CHD" -o "$OUT/disc.cue" -ob "$OUT/disc.bin" -f
echo "=== tracks (cue) ==="; cat "$OUT/disc.cue"
# Track 1 = data (DGDS volumes in ISO9660); tracks 2+ = Red Book audio (music/voice).
# Convert to plain ISO + WAV audio tracks:
bchunk -w "$OUT/disc.bin" "$OUT/disc.cue" "$OUT/rotd_" || true
echo "=== data track / iso contents (look for VOLUME.* / *.SDS) ==="
ls -la "$OUT"/ | head
