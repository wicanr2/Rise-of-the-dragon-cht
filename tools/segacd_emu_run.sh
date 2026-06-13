#!/usr/bin/env bash
# Fast-iteration Sega CD emulation runner (uses prebuilt rotd-emu image; no per-run apt).
# Usage: segacd_emu_run.sh <bios_basename> <frames> <every> [outdir]
#   bios_basename: file under /home/anr2/emulator/bios without .bin (e.g. mpr-18100)
set -u
cd "$(dirname "$0")/.."
BIOS="${1:-megacd_j}"; FRAMES="${2:-1800}"; EVERY="${3:-60}"; OUT="${4:-frames}"; INPUT_AFTER="${5:-1500}"
docker run --rm -v "/home/anr2/rise-of-the-dragon":/work -v /home/anr2/emulator/bios:/bios:ro \
  -w /work rotd-emu:latest bash -c "
  gcc -O2 tools/segacd_run.c -ldl -o /tmp/segacd_run 2>&1
  mkdir -p segacd_ja/system segacd_ja/$OUT
  rm -f segacd_ja/$OUT/*.ppm
  rm -f segacd_ja/system/bios_CD_*.bin
  cp -f /bios/$BIOS.bin segacd_ja/system/bios_CD_J.bin
  cp -f /bios/$BIOS.bin segacd_ja/system/bios_CD_U.bin
  cp -f /bios/$BIOS.bin segacd_ja/system/bios_CD_E.bin
  /tmp/segacd_run segacd_ja/genesis_plus_gx_libretro.so segacd_ja/disc.cue \
    segacd_ja/system segacd_ja/$OUT $FRAMES $EVERY $INPUT_AFTER 2>&1 | grep -E 'brightness|fault|core:|av:|FAIL'
  chmod -R a+rw segacd_ja/system segacd_ja/$OUT 2>/dev/null
"
