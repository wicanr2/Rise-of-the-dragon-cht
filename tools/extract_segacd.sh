#!/usr/bin/env bash
# Extract the Sega CD Japanese ROTD disc for Japanese-text harvesting + audio.
# Runs entirely in a throwaway Docker container so the host stays clean.
# Output -> segacd_ja/ (gitignored, copyrighted disc data, local only).
set -e
cd "$(dirname "$0")/.."
CHD="Rise of the Dragon - A Blade Hunter Mystery (Japan).chd"
docker run --rm -v "$PWD":/work -w /work ubuntu:24.04 bash -c '
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null
  apt-get install -y -qq mame-tools bchunk genisoimage python3 python3-pycdlib >/dev/null
  mkdir -p segacd_ja/files
  # 1) CHD -> bin/cue (track 1 data MODE1/2352, tracks 2+ Red Book audio)
  chdman extractcd -i "'"$CHD"'" -o segacd_ja/disc.cue -ob segacd_ja/disc.bin -f
  # 2) split -> data track ISO + audio WAVs
  ( cd segacd_ja && bchunk -w disc.bin disc.cue rotd_ )
  # 3) walk the ISO9660 data track, extract every file
  python3 - <<PY
import pycdlib, os
iso=pycdlib.PyCdlib(); iso.open("segacd_ja/rotd_01.iso")
n=0
for dn, _, files in iso.walk(iso_path="/"):
    for f in files:
        with open("segacd_ja/files/"+f.split(";")[0],"wb") as o:
            iso.get_file_from_iso_fp(o, iso_path=dn.rstrip("/")+"/"+f)
        n+=1
iso.close(); print("extracted", n, "files")
PY
  chmod -R a+rw segacd_ja
'
echo "Done. Game files in segacd_ja/files/ ; CD audio in segacd_ja/rotd_0[2-5].wav"
# Structure (verified): 1010 *.SD4 + 9 *.SD5 + 8 *.SD6 scene scripts (RD*.SD4 carry the
# Shift-JIS Japanese dialogue, chunk tags EDA:/ILF:/DFB: -- NOT at offset 0, a header
# precedes them), 208 *.CAT assets, 57 *.BIN, 3 *.PCM (digitized speech), 3 *.TXT.
# The Sega CD DGDS variant differs from the PC SDS format and needs its own RE before
# ja.dtr can be built.
