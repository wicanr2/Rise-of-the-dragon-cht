#!/usr/bin/env python3
"""DGDS chunk reader + decompressor (RLE/LZW), mirrors ScummVM decompress.cpp & resource.cpp."""
import struct, io

def rle_decompress(data, out_size):
    out = bytearray(); i = 0; n = len(data)
    while len(out) < out_size and i < n:
        lenR = data[i]; i += 1
        if lenR == 128:
            pass
        elif lenR <= 127:
            lenW = min(lenR, out_size - len(out))
            out += data[i:i+lenW]; i += lenR
        else:
            lenW = min(lenR & 0x7F, out_size - len(out))
            val = data[i]; i += 1
            out += bytes([val])*lenW
    return bytes(out)

class LZW:
    def __init__(self): self.reset()
    def reset(self):
        self.table = [[c] for c in range(256)] + [[] for _ in range(0x4000-256)]
        self.size=0x101; self.maxt=0x200; self.full=False
        self.csize=9; self.clen=0; self.cur=[0]*256
        self.cache=0; self.bd=0; self.bs=0
    def getcode(self, total, st):
        masks=[0,1,3,7,0xF,0x1F,0x3F,0x7F,0xFF]
        numBits=total; res=0
        while numBits>0:
            if st.tell()>=self._len: return 0xFFFFFFFF
            if self.bs==0:
                self.bs=8; self.bd=st.read(1)[0]
            use=min(numBits,8,self.bs)
            res |= (self.bd & masks[use]) << (total-numBits)
            numBits-=use; self.bs-=use; self.bd>>=use
        return res
    def decompress(self, data, out_size):
        st=io.BytesIO(data); self._len=len(data)
        self.bd=0; self.bs=0; self.reset()
        out=bytearray(); self.cache=0
        while len(out)<out_size:
            code=self.getcode(self.csize, st)
            if code==0xFFFFFFFF: break
            self.cache+=self.csize
            if self.cache>=self.csize*8: self.cache-=self.csize*8
            if code==0x100:
                if self.cache>0: self.getcode(self.csize*8-self.cache, st)
                self.reset()
            else:
                if code>=self.size and not self.full:
                    self.cur[self.clen]=self.cur[0]; self.clen+=1
                    for i in range(self.clen):
                        if len(out)>=out_size: break
                        out.append(self.cur[i])
                else:
                    for b in self.table[code]:
                        if len(out)>=out_size: break
                        out.append(b)
                    self.cur[self.clen]=self.table[code][0]; self.clen+=1
                if self.clen>=2:
                    if not self.full:
                        if self.size==self.maxt and self.csize==12:
                            self.full=True; i=self.size
                        else:
                            i=self.size; self.size+=1; self.cache=0
                        if self.size==self.maxt and self.csize<12:
                            self.csize+=1; self.maxt<<=1
                        self.table[i]=self.cur[:self.clen]
                    self.cur[:self.table[code].__len__()]=self.table[code]
                    self.clen=len(self.table[code])
        return bytes(out)

def decompress_blob(data):
    """data starts with compression byte + uint32 uncompressedSize + payload."""
    comp=data[0]; usize=struct.unpack_from('<I',data,1)[0]; payload=data[5:]
    if comp==0: return payload[:usize]
    if comp==1: return rle_decompress(payload, usize)
    if comp==2: return LZW().decompress(payload, usize)
    raise ValueError(f"unknown compression {comp}")

DGDS_TYPENAME_MAX=4
def iter_chunks(data):
    """Yield (idstr, size, container, start_offset, raw_payload) for each chunk."""
    st=io.BytesIO(data); n=len(data)
    while st.tell()<n:
        idb=st.read(DGDS_TYPENAME_MAX)
        if len(idb)<4: break
        idstr=idb.decode('latin1')
        if idstr[3]!=':':
            break
        size=struct.unpack('<I',st.read(4))[0]
        container=bool(size & 0x80000000); size &= ~0x80000000
        start=st.tell()
        if container:
            # container: no payload consumed here, continue reading nested
            yield (idstr, size, True, start, b'')
            continue
        payload=st.read(size)
        yield (idstr, size, False, start, payload)

if __name__=='__main__':
    import sys
    data=open(sys.argv[1],'rb').read()
    for idstr,size,cont,start,payload in iter_chunks(data):
        print(f"{idstr!r} size={size} container={cont} start={start}")
