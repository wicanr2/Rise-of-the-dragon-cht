#!/usr/bin/env python3
"""Merge/validate dialogue translations and report coverage vs dialogs_en.json.
Usage:
  merge_translations.py coverage                 # report % of 2386 slots translated
  merge_translations.py merge batch.json         # merge {scene:num -> zh} into translations/zh.json
"""
import json, sys, re

ZH='translations/zh.json'; EN='dialogs_en.json'

def load(p):
    try: return json.load(open(p, encoding='utf-8'))
    except FileNotFoundError: return {}

def dialog_keys():
    en=json.load(open(EN, encoding='utf-8'))
    out={}
    for x in en:
        m=re.search(r's(\d+)\.sds', x['scene'])
        if m: out[f"{int(m.group(1))}:{x['num']}"]=x['text']
    return out

def check_big5(zh):
    bad=[]
    for k,v in zh.items():
        try: v.encode('big5')
        except UnicodeEncodeError as e:
            bad.append((k, v[e.start:e.end]))
    return bad

def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'coverage'
    zh=load(ZH); keys=dialog_keys()
    if cmd=='merge':
        batch=json.load(open(sys.argv[2], encoding='utf-8'))
        added=0
        for k,v in batch.items():
            if k not in zh: added+=1
            zh[k]=v
        json.dump(zh, open(ZH,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"# merged {len(batch)} entries ({added} new) -> {ZH}")
    dlg_done=sum(1 for k in keys if k in zh and zh[k])
    ui=sum(1 for k in zh if k.startswith('UI:'))
    bad=check_big5(zh)
    print(f"dialogue: {dlg_done}/{len(keys)} slots translated ({100*dlg_done//max(1,len(keys))}%)")
    print(f"UI: {ui} strings")
    if bad:
        print(f"!! {len(bad)} entries have non-Big5 chars:")
        for k,c in bad[:10]: print(f"   {k}: {c!r}")

if __name__=='__main__': main()
