#!/usr/bin/env python3
"""DGDS volume (VOLUME.VGA index + VOLUME.00x) reader/extractor.
Mirrors ScummVM engines/dgds/resource.cpp exactly."""
import os, struct, sys, argparse

FILENAME_LENGTH = 12

def read_index(game_dir):
    """Return list of (resname, volume_idx, pos, size, checksum)."""
    idx_path = None
    for name in ("VOLUME.VGA","volume.vga","VOLUME.EGA","VOLUME.RMF","RESOURCE.MAP"):
        p = os.path.join(game_dir, name)
        if os.path.exists(p):
            idx_path = p; break
    if not idx_path:
        raise SystemExit("no index file found")
    with open(idx_path,'rb') as f:
        idx = f.read()
    off = 0
    salt = struct.unpack_from('<I', idx, off)[0]; off += 4
    nvol = struct.unpack_from('<H', idx, off)[0]; off += 2
    resources = []
    volumes = {}
    for vi in range(nvol):
        fn = idx[off:off+FILENAME_LENGTH].split(b'\0')[0].decode('latin1'); off += FILENAME_LENGTH
        off += 1  # unknown sbyte
        entries = struct.unpack_from('<H', idx, off)[0]; off += 2
        vol_path = os.path.join(game_dir, fn)
        if vi not in volumes:
            volumes[vi] = open(vol_path,'rb')
        vf = volumes[vi]
        for j in range(entries):
            checksum = struct.unpack_from('<I', idx, off)[0]; off += 4
            pos = struct.unpack_from('<I', idx, off)[0]; off += 4
            vf.seek(pos)
            hdr = vf.read(FILENAME_LENGTH+1+4)
            resname = hdr[:FILENAME_LENGTH].split(b'\0')[0].decode('latin1').lower()
            size = struct.unpack_from('<I', hdr, FILENAME_LENGTH+1)[0]
            datapos = pos + FILENAME_LENGTH+1+4
            if not resname or size == 0:
                continue
            resources.append((resname, vi, fn, datapos, size, checksum))
    return resources, volumes

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('game_dir')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--extract', metavar='OUTDIR')
    args = ap.parse_args()
    resources, volumes = read_index(args.game_dir)
    # group by extension
    from collections import Counter
    exts = Counter(r[0].split('.')[-1] for r in resources)
    print(f"# {len(resources)} resources, extensions: {dict(exts)}", file=sys.stderr)
    if args.list:
        for resname, vi, fn, pos, size, cs in sorted(resources):
            print(f"{resname:14s} vol={fn} pos={pos:9d} size={size:8d}")
    if args.extract:
        os.makedirs(args.extract, exist_ok=True)
        for resname, vi, fn, pos, size, cs in resources:
            vf = volumes[vi]; vf.seek(pos)
            data = vf.read(size)
            with open(os.path.join(args.extract, resname),'wb') as o:
                o.write(data)
        print(f"# extracted {len(resources)} files to {args.extract}", file=sys.stderr)

if __name__ == '__main__':
    main()
