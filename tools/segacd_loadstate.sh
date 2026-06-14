#!/usr/bin/env bash
# Load a user-provided Genesis Plus GX savestate captured at a Japanese DIALOGUE screen,
# render it, and dump the frame (for OCR) + attempt a VRAM dump (for font extraction).
# The savestate MUST be from a matching GPGX version (this harness uses v1.7.4 c7ecd07);
# the harness prints "unserialize OK/FAILED" so version mismatch is obvious.
#
# Usage: tools/segacd_loadstate.sh <savestate-file>
set -e
cd "$(dirname "$0")/.."
STATE="${1:?path to a .state savestate}"
mkdir -p segacd_ja
cp "$STATE" segacd_ja/state.bin
docker run --rm -v "$PWD":/work -v /home/anr2/emulator/bios:/bios:ro -w /work \
  -e ROTD_STATE=/work/segacd_ja/state.bin rotd-emu:latest bash -c '
  gcc -O2 tools/segacd_run.c -ldl -o /tmp/segacd_run
  mkdir -p segacd_ja/system segacd_ja/state_out
  cp -f /bios/megacd_j.bin segacd_ja/system/bios_CD_J.bin
  cp -f /bios/megacd_u.bin segacd_ja/system/bios_CD_U.bin 2>/dev/null || true
  cp -f /bios/megacd_e.bin segacd_ja/system/bios_CD_E.bin 2>/dev/null || true
  rm -f segacd_ja/state_out/*.ppm
  # no input (state is already at the dialogue); a few frames so it renders; dump frame+VRAM
  /tmp/segacd_run segacd_ja/genesis_plus_gx_libretro.so segacd_ja/disc.cue \
    segacd_ja/system segacd_ja/state_out 30 30 999999 2>&1 | grep -E "STATE|VRAM|wrote|av:|core:"
  chmod -R a+rw segacd_ja/state_out segacd_ja/state.bin 2>/dev/null || true
'
# convert the rendered dialogue frame for inspection / OCR
[ -f segacd_ja/state_out/frame_final.ppm ] && \
  convert segacd_ja/state_out/frame_final.ppm -filter point -resize 300% screenshots/state_dialogue.png 2>/dev/null
echo "frame -> screenshots/state_dialogue.png ; VRAM(if any) -> segacd_ja/state_out/vram.bin"
