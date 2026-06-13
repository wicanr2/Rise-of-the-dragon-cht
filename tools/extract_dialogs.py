#!/usr/bin/env python3
"""Parse DGDS SDS scene files (Rise of the Dragon, ver 1.211) and extract dialogue.
Faithful port of ScummVM engines/dgds/scene.cpp SDSScene::parse + readDialogList."""
import sys, os, io, struct, json, glob
sys.path.insert(0, os.path.dirname(__file__))
from dgds_chunks import iter_chunks, decompress_blob

class R:
    def __init__(self, data): self.d=data; self.p=0
    def u16(self):
        v=struct.unpack_from('<H',self.d,self.p)[0]; self.p+=2; return v
    def s16(self):
        v=struct.unpack_from('<h',self.d,self.p)[0]; self.p+=2; return v
    def u32(self):
        v=struct.unpack_from('<I',self.d,self.p)[0]; self.p+=4; return v
    def cstr(self):
        e=self.d.index(b'\0',self.p); s=self.d[self.p:e]; self.p=e+1; return s.decode('latin1')
    def fixedstr(self, n):
        raw=self.d[self.p:self.p+n]; self.p+=n
        z=raw.find(b'\0')
        return (raw if z<0 else raw[:z]).decode('cp437')
    def rem(self): return len(self.d)-self.p

# version " 1.211" precomputed predicates
def over(v):   # isVersionOver: " 1.211" > v ?
    return " 1.211" > v
def under(v):
    return " 1.211" < v   # NOTE strncmp uses len(_version)=6; both args len6 -> plain compare ok

def read_condlist(r):
    num=r.u16()
    for _ in range(num):
        r.u16(); r.u16(); r.s16()
def read_oplist(r):
    n=r.u16()
    for _ in range(n):
        read_condlist(r)
        op=r.u16()
        nvals=r.u16()
        for _ in range(nvals//2): r.u16()
def read_hotarea(r):
    r.u16();r.u16();r.u16();r.u16()  # rect
    r.u16()  # num
    r.u16()  # cursorNum
    if over(" 1.217"): r.u16()
    if over(" 1.218"):
        oirn=r.u16()
    read_condlist(r)
    read_oplist(r); read_oplist(r); read_oplist(r)
def read_hotarealist(r):
    n=r.u16()
    for _ in range(n): read_hotarea(r)
def read_objinteractionlist(r):
    n=r.u16()
    for _ in range(n):
        if not over(" 1.205"):
            r.u16();r.u16();r.u16()
        else:
            r.u16();r.u16()
        read_oplist(r)
def read_dialogactionlist(r):
    n=r.u16()
    for _ in range(n):
        r.u16(); r.u16()  # strStart strEnd
        read_oplist(r)
def read_dialoglist(r, out, fname):
    nitems=r.u16()
    for _ in range(nitems):
        num=r.u16()
        rx,ry,rw,rh=r.u16(),r.u16(),r.u16(),r.u16()
        bg=r.u16(); fg=r.u16()
        if under(" 1.209"):
            selbg,selfg=bg,fg
        else:
            selbg=r.u16(); selfg=r.u16()
        fontsize=r.u16()
        if under(" 1.210"):
            flags=r.u16()
        else:
            flags=r.u32()&0xffff
        frametype=r.u16(); time=r.u16()
        if over(" 1.215"): nextfile=r.u16()
        if over(" 1.207"): nextdlg=r.u16()
        if over(" 1.216"): r.u16(); r.u16()
        nbytes=r.u16()
        s=""
        if nbytes>0:
            s=r.fixedstr(nbytes)
        read_dialogactionlist(r)
        if s:
            out.append(dict(scene=fname, num=num, rect=[rx,ry,rw,rh],
                            bg=bg, fg=fg, fontsize=fontsize, text=s))

def parse_sds(path):
    data=open(path,'rb').read()
    fname=os.path.basename(path)
    dialogs=[]
    for idstr,size,cont,start,payload in iter_chunks(data):
        if idstr=='SDS:' and not cont:
            raw=decompress_blob(payload)
            r=R(raw)
            magic=r.u32(); ver=r.cstr()
            assert ver==" 1.211", f"{fname}: unexpected ver {ver!r}"
            num=r.u16()
            read_oplist(r)  # enter
            read_oplist(r)  # leave
            if over(" 1.206"): read_oplist(r)  # preTick
            read_oplist(r)  # postTick
            r.u16()  # field6
            adsfile=r.cstr()
            read_hotarealist(r)
            read_objinteractionlist(r)
            if over(" 1.205"): read_objinteractionlist(r)
            if under(" 1.214"): read_dialoglist(r, dialogs, fname)
            # triggers / conditional ops follow but we stop; record remaining
            return dialogs, r.rem(), ver
    return dialogs, -1, None

def main():
    files=sorted(glob.glob(os.path.join(sys.argv[1],'*.sds')))
    alldlg=[]; bad=0
    for f in files:
        try:
            dlg, rem, ver = parse_sds(f)
            alldlg += dlg
        except Exception as e:
            print(f"FAIL {os.path.basename(f)}: {e}", file=sys.stderr); bad+=1
    print(f"# {len(files)} scenes, {len(alldlg)} dialogs, {bad} parse failures", file=sys.stderr)
    if len(sys.argv)>2:
        json.dump(alldlg, open(sys.argv[2],'w'), ensure_ascii=False, indent=1)
        print(f"# wrote {sys.argv[2]}", file=sys.stderr)

if __name__=='__main__': main()
