#!/usr/bin/env bash
# Dynamic analysis of the Sega CD (Japan) disc: boot it in Genesis Plus GX (headless,
# in Docker) and render frames to PPM so we can OCR the OFFICIAL Japanese text directly
# (sidesteps the custom SD4 text encoding). Host stays clean; all data stays gitignored.
#
# Prereqs already on disk:
#   segacd_ja/genesis_plus_gx_libretro.so   (built by the earlier docker step)
#   segacd_ja/disc.cue + disc.bin           (extracted from the CHD)
#   /home/anr2/emulator/bios/mpr-18100.bin  (Mega-CD Japan BIOS)
set -e
cd "$(dirname "$0")/.."
BIOS=/home/anr2/emulator/bios
FRAMES="${1:-900}"; EVERY="${2:-30}"
docker run --rm \
  -v "$PWD":/work -v "$BIOS":/bios:ro -w /work ubuntu:24.04 bash -c '
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null 2>&1
  apt-get install -y -qq build-essential curl >/dev/null 2>&1
  [ -f tools/libretro.h ] || curl -fsSL \
    https://raw.githubusercontent.com/libretro/libretro-common/master/include/libretro.h \
    -o tools/libretro.h
  gcc -O2 tools/segacd_run.c -ldl -o /tmp/segacd_run
  # Genesis Plus GX looks for the Sega/Mega CD BIOS in the system dir by region name.
  mkdir -p segacd_ja/system segacd_ja/frames
  cp -f /bios/mpr-18100.bin segacd_ja/system/bios_CD_J.bin
  cp -f /bios/mpr-17933.bin segacd_ja/system/bios_CD_U.bin 2>/dev/null || true
  cp -f /bios/sega_101.bin  segacd_ja/system/bios_CD_E.bin 2>/dev/null || true
  rm -f segacd_ja/frames/*.ppm
  /tmp/segacd_run \
    segacd_ja/genesis_plus_gx_libretro.so \
    segacd_ja/disc.cue \
    segacd_ja/system \
    segacd_ja/frames \
    '"$FRAMES"' '"$EVERY"'
  ls -1 segacd_ja/frames | tail -5
  chmod -R a+rw segacd_ja/system segacd_ja/frames
'
echo "Frames -> segacd_ja/frames/ (PPM, gitignored)"
