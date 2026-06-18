#!/usr/bin/env python3
"""Build build/voice.map from RiseOfDragonAudioCopy/audiocopy/audio.csv.

Each game dialog (scene:num) maps to one or more Sega CD voice clips. A long line is
split across disc files (RD.. = part 1, RE.. = part 2, ...) so the value is an ORDERED,
comma-separated list of clip base names; the engine (VoiceSupport) queues them in order.
The clip names are identical across the US/JP discs, so this one map serves every voice set.

    voice.map line:  <sceneNum>:<dlgNum> <clip>[,<clip>...]
"""
import re, collections, os, sys

CSV = "RiseOfDragonAudioCopy/audiocopy/audio.csv"
OUT = "build/voice.map"

def main():
    d = collections.defaultdict(list)   # "scene:num" -> [clip base names]
    skipped = 0
    for line in open(CSV, encoding="utf-8", errors="replace").read().splitlines():
        c = [x.strip() for x in line.split(",")]
        if not c or not c[0].lower().endswith(".wav"):
            continue
        base = c[0][:-4]
        scene = c[2] if len(c) > 2 else ""
        if "SDS" not in scene.upper():
            skipped += 1
            continue
        sc = re.sub(r"[^0-9]", "", scene)          # S8.SDS -> 8
        for n in c[3:]:
            if n.isdigit():
                d[f"{sc}:{n}"].append(base.upper())  # clip files are UPPERCASE RDxxxx; audio.csv casing varies
    os.makedirs("build", exist_ok=True)
    multi = 0
    with open(OUT, "w") as f:
        for k in sorted(d, key=lambda x: (int(x.split(":")[0]), int(x.split(":")[1]))):
            parts = sorted(set(d[k]))               # RD.. < RE.. < RF.. by name = play order
            if len(parts) > 1:
                multi += 1
            f.write(f"{k} {','.join(parts)}\n")
    print(f"wrote {OUT}: {len(d)} dialogs ({multi} multi-part), {skipped} rows skipped (no scene)")

if __name__ == "__main__":
    main()
