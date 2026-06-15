#!/usr/bin/env python3
"""Extract every TTM-displayed string (SET STRING op 0xf1X0) from the game's .ttm
resources. The script lives in the TT3: chunk; TAG: holds non-displayed frame labels.
Usage: extract_ttm_strings.py <extracted-res-dir>  -> prints {file: [strings]}"""
import sys, os, glob, struct
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from dgds_chunks import iter_chunks, decompress_blob

def parse_tt3(blob):
    p=0; n=len(blob); out=[]
    def u16():
        nonlocal p
        v=struct.unpack_from('<H',blob,p)[0]; p+=2; return v
    while p+2<=n:
        code=u16(); op=code&0xFFF0; count=code&0x000F
        if count==0x0F:
            if code in (0xaf1f,0xaf2f):
                if p+2>n: break
                npts=u16()
                p+=npts*4
            else:
                e=blob.find(b'\0',p)
                if e<0: break
                s=blob[p:e].decode('latin1')
                slen=e-p+1
                if slen%2: slen+=1            # pad to even
                p+=slen
                if 0xf100<=op<=0xf190:        # SET STRING 0..9 = displayed text
                    out.append(s)
        else:
            p+=count*2
    return out

res=sys.argv[1] if len(sys.argv)>1 else "/tmp/res"
allstr={}
for f in sorted(glob.glob(os.path.join(res,"*.ttm"))):
    data=open(f,"rb").read()
    for idstr,size,cont,start,payload in iter_chunks(data):
        if idstr=='TT3:':
            try: blob=decompress_blob(payload)
            except Exception: blob=payload
            ss=[s for s in parse_tt3(blob) if s.strip()]
            if ss: allstr[os.path.basename(f)]=ss
if __name__=="__main__" and "--json" not in sys.argv:
    # 驗證:vidfone.ttm 的字串
    print("=== vidfone.ttm (驗證) ===")
    for s in allstr.get("vidfone.ttm",[]): print(f"   {s!r}")
    print("=== clvidfne.ttm (Chen Lu 電話) ===")
    for s in allstr.get("clvidfne.ttm",[]): print(f"   {s!r}")
    print(f"\n總計 {sum(len(v) for v in allstr.values())} 個顯示字串,{len(allstr)} 個 TTM")
