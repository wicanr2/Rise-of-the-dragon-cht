#!/usr/bin/env python3
"""Generate German TTS dub for Rise of the Dragon via edge-tts (de-DE voices).

Runs INSIDE the rotd-tts:latest container. Reads:
  build/voice.map        -> list of scene:num keys to dub (~1309)
  dialogs_de.json        -> official German line text per scene:num
  translations/zh.json   -> Chinese line; speaker name = text before 全形冒號 (：)

Writes ONLY to de_voice/:
  de_voice/<scene>_<num>.wav   (16276 Hz mono s16le)
  de_voice/_voicemap.json      (per-line speaker/voice/rate/pitch/de text)
  de_voice/_progress.json      (resume state)
  de_voice/_failed.txt         (failed keys, one per line)

Resumable: existing target wav is skipped. Per-line 25s timeout + exponential
backoff retry on edge-tts throttling.
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = "/work"
VOICE_MAP = os.path.join(ROOT, "build/voice.map")
DIALOGS_DE = os.path.join(ROOT, "dialogs_de.json")
ZH_JSON = os.path.join(ROOT, "translations/zh.json")
OUT_DIR = os.path.join(ROOT, "de_voice")

SAMPLE_RATE = 16276  # match original DGDS voice clip rate


def dump_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

# --- Speaker (zh canonical name) -> (de voice, rate, pitch) -----------------
# NOTE: edge-tts only ships 6 real de-DE voices. The task table's named voices
# (Bernd/Klaus/Louisa/Ralf/Christoph/Kasper...) do NOT exist, so each is remapped
# to the closest real voice and the character is kept distinct via rate/pitch.
#   Male:   de-DE-ConradNeural, de-DE-FlorianMultilingualNeural, de-DE-KillianNeural
#   Female: de-DE-KatjaNeural,  de-DE-AmalaNeural, de-DE-SeraphinaMultilingualNeural
DEFAULT_MALE = ("de-DE-ConradNeural", "+0%", "-2Hz")
DEFAULT_FEMALE = ("de-DE-KatjaNeural", "+0%", "+4Hz")
NARRATION = ("de-DE-ConradNeural", "+0%", "-2Hz")

# canonical voice profiles (task table intent -> real voice + rate/pitch)
VOICE = {
    "孟波": ("de-DE-ConradNeural", "+0%", "-2Hz"),                       # cold-hard male lead
    "阿香": ("de-DE-KatjaNeural", "+0%", "+4Hz"),                        # girlfriend
    "文森奇市長": ("de-DE-FlorianMultilingualNeural", "-5%", "-4Hz"),     # was Bernd: stern politician
    "張力": ("de-DE-KillianNeural", "-15%", "-6Hz"),                     # was Klaus: aged fortune teller
    "老傑克": ("de-DE-KillianNeural", "+0%", "-2Hz"),                     # gruff informant
    "珍妮": ("de-DE-AmalaNeural", "+5%", "+8Hz"),                        # perky
    "甜甜": ("de-DE-SeraphinaMultilingualNeural", "+3%", "+6Hz"),        # was Louisa: young woman
    "蛇仔": ("de-DE-FlorianMultilingualNeural", "+0%", "-1Hz"),          # was Ralf: sinister
    "巴哈姆特之聲": ("de-DE-FlorianMultilingualNeural", "-10%", "-18Hz"), # was Christoph: demon-god, very low
    "陳路": ("de-DE-KillianNeural", "-4%", "-6Hz"),                       # was Kasper: gang boss
}

# Map every zh.json speaker variant seen in voice.map to a canonical profile.
# Names that are clearly female get DEFAULT_FEMALE, male get a distinct voice
# where possible, otherwise DEFAULT_MALE.
ALIAS = {
    # Blade / 孟波 (protagonist)
    "孟波": "孟波",
    # 阿香 / Karin
    "阿香": "阿香",
    # Jake the fixer -> 老傑克 profile
    "傑克": "老傑克",
    "老傑克": "老傑克",
    "傑克哥": "老傑克",
    # Jenni
    "珍妮": "珍妮",
    # Mayor Vincenzi
    "文森奇市長": "文森奇市長",
    "市長": "文森奇市長",
    # Chang Li fortune teller -> 張力
    "張力": "張力",
    "張黎": "張力",
    # Candi / 甜甜 / 錢迪
    "甜甜": "甜甜",
    "坎蒂": "甜甜",
    "錢迪": "甜甜",
    # Snake -> 蛇仔
    "蛇哥": "蛇仔",
    # Voice of Bahamut
    "巴哈姆特之聲": "巴哈姆特之聲",
    "巴胡馬特之聲": "巴哈姆特之聲",
    # Deng Hwang gang boss -> 陳路 (黑幫頭目) profile
    "鄧黃": "陳路",
    "鄧": "陳路",
}

# additional supporting cast, mapped onto the 6 real voices + rate/pitch so the
# dub keeps variety without inventing nonexistent voices.
#   M: Conrad / Florian / Killian   F: Katja / Amala / Seraphina
EXTRA = {
    # --- female supporting cast ---
    "布麗絲": ("de-DE-SeraphinaMultilingualNeural", "+2%", "+5Hz"),  # Rose
    "羅蓮": ("de-DE-KatjaNeural", "+0%", "+2Hz"),                    # Lorain
    "蘿琳": ("de-DE-KatjaNeural", "+0%", "+2Hz"),
    "黛賽兒": ("de-DE-AmalaNeural", "+0%", "+6Hz"),                  # Darcelle
    "接待員": ("de-DE-AmalaNeural", "+2%", "+4Hz"),                  # receptionist
    "櫃台小姐": ("de-DE-AmalaNeural", "+2%", "+4Hz"),
    "瑪莎": ("de-DE-KatjaNeural", "-3%", "+0Hz"),                    # Martha (older)
    "凱西·瓊斯": ("de-DE-SeraphinaMultilingualNeural", "+0%", "+2Hz"),  # Casey Jones (reporter)
    "信徒們": ("de-DE-KatjaNeural", "-3%", "+0Hz"),
    # --- male supporting cast ---
    "史倫": ("de-DE-FlorianMultilingualNeural", "+0%", "+2Hz"),      # Slen
    "史蘭": ("de-DE-FlorianMultilingualNeural", "+0%", "+2Hz"),
    "穆賈藍波": ("de-DE-FlorianMultilingualNeural", "-6%", "-8Hz"),  # Mujalambo (mystic)
    "強尼·阿廣": ("de-DE-FlorianMultilingualNeural", "+5%", "+0Hz"),  # Jonny Qwong
    "強尼阿廣": ("de-DE-FlorianMultilingualNeural", "+5%", "+0Hz"),
    "流浪漢": ("de-DE-KillianNeural", "-4%", "-3Hz"),                # Penner
    "獨眼龍": ("de-DE-KillianNeural", "+2%", "-4Hz"),                # Patch (one-eyed)
    "范海倫副警長": ("de-DE-ConradNeural", "-2%", "-4Hz"),           # Van Halen
    "尚菲爾": ("de-DE-KillianNeural", "-4%", "-3Hz"),               # Xamphir
    "阿瑞斯": ("de-DE-FlorianMultilingualNeural", "+0%", "-2Hz"),    # Arreis
    "亞瑞斯": ("de-DE-FlorianMultilingualNeural", "+0%", "-2Hz"),
    "阿霸": ("de-DE-KillianNeural", "+3%", "-2Hz"),                  # Fu Bar
    "實驗室技師": ("de-DE-ConradNeural", "+3%", "+2Hz"),             # laborant
    "警衛": ("de-DE-FlorianMultilingualNeural", "+0%", "-2Hz"),      # Wache
    "守衛": ("de-DE-FlorianMultilingualNeural", "+0%", "-2Hz"),
    "獄警": ("de-DE-KillianNeural", "-2%", "-3Hz"),
    "打手": ("de-DE-FlorianMultilingualNeural", "+2%", "-3Hz"),      # Schlaegertyp
    "嘍囉甲": ("de-DE-FlorianMultilingualNeural", "+3%", "+0Hz"),
    "嘍囉乙": ("de-DE-KillianNeural", "+3%", "+0Hz"),
    "警員一": ("de-DE-ConradNeural", "+0%", "-3Hz"),
    "警員二": ("de-DE-FlorianMultilingualNeural", "+0%", "-3Hz"),
    "警官": ("de-DE-ConradNeural", "-2%", "-4Hz"),
    "警察中尉": ("de-DE-ConradNeural", "-4%", "-5Hz"),
    "警方調度員": ("de-DE-KillianNeural", "+0%", "-2Hz"),
    "狙擊手": ("de-DE-FlorianMultilingualNeural", "+2%", "-3Hz"),
    "清潔工": ("de-DE-FlorianMultilingualNeural", "+0%", "-2Hz"),
    "上班族": ("de-DE-KillianNeural", "+2%", "-1Hz"),
    "市民": ("de-DE-FlorianMultilingualNeural", "+0%", "-2Hz"),
    "老者": ("de-DE-KillianNeural", "-12%", "-5Hz"),
    "第 41 小隊": ("de-DE-ConradNeural", "+0%", "-3Hz"),
    "孟巴二手車行": ("de-DE-ConradNeural", "+0%", "-2Hz"),
}

# zh names that are clearly female -> female default if not otherwise mapped
FEMALE_HINT = set()


def fixup_german(t: str) -> str:
    """Repair the corrupted 'ß' (rendered as U+2591 '░') and normalise CR."""
    t = t.replace("░", "ß")
    # collapse carriage returns / form-feeds into spaces for TTS
    t = t.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    t = t.replace("\f", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def strip_nameplate(t: str) -> str:
    """Strip a leading 'NAME:' / 'NAME: ' speaker name-plate prefix."""
    # German name-plates are uppercase-ish words then ':' then the line.
    m = re.match(r"^([^:]{1,30}):\s+(.+)$", t, re.S)
    if m:
        prefix, rest = m.group(1), m.group(2)
        # only strip if prefix has no sentence-ending punctuation (it's a label)
        if not re.search(r"[.!?…]", prefix):
            return rest.strip()
    return t


def zh_speaker(zt):
    if not zt:
        return None
    m = re.match(r"^([^：\r\n]{1,10})：", zt)
    return m.group(1) if m else None


def resolve_voice(speaker):
    """speaker (zh canonical name) -> (voice, rate, pitch, label)."""
    if speaker is None:
        return (*NARRATION, "旁白")
    if speaker in EXTRA:
        return (*EXTRA[speaker], speaker)
    canon = ALIAS.get(speaker)
    if canon and canon in VOICE:
        return (*VOICE[canon], canon)
    if speaker in VOICE:
        return (*VOICE[speaker], speaker)
    # unknown speaker -> guess by female hint else male default
    if speaker in FEMALE_HINT:
        return (*DEFAULT_FEMALE, speaker)
    return (*DEFAULT_MALE, speaker)


def adjust_for_tone(text, speaker, rate, pitch):
    """Light per-line tone tweak via punctuation cues (esp. 阿香)."""
    canon = ALIAS.get(speaker, speaker)
    if canon == "阿香":
        if "！" in text or "!" in text or "混蛋" in text or "白痴" in text:
            return "+12%", pitch  # 吵架: faster
        if "……" in text or "..." in text:
            return "-8%", "+8Hz"  # 溫柔: slower, higher
    # generic punctuation cue
    if text.endswith("！") or text.endswith("!"):
        rate = bump_rate(rate, +4)
    return rate, pitch


def bump_rate(rate, delta):
    m = re.match(r"([+-]?\d+)%", rate)
    base = int(m.group(1)) if m else 0
    return f"{base + delta:+d}%"


def load():
    vkeys = []
    for line in open(VOICE_MAP, encoding="utf-8"):
        line = line.strip()
        if line:
            vkeys.append(line.split()[0])

    d = json.load(open(DIALOGS_DE, encoding="utf-8"))
    de = {}
    for e in d:
        s = e["scene"]
        s = s[1:] if s.startswith("s") else s
        s = s[:-4] if s.endswith(".sds") else s
        de[f"{s}:{e['num']}"] = e["text"]

    z = json.load(open(ZH_JSON, encoding="utf-8"))
    return vkeys, de, z


async def synth(text, voice, rate, pitch, mp3_path, timeout=25):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await asyncio.wait_for(comm.save(mp3_path), timeout=timeout)


def to_wav(mp3_path, wav_path):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", mp3_path,
         "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", wav_path],
        check=True,
    )


async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    vkeys, de, z = load()

    prog_path = os.path.join(OUT_DIR, "_progress.json")
    vmap_path = os.path.join(OUT_DIR, "_voicemap.json")
    failed_path = os.path.join(OUT_DIR, "_failed.txt")

    voicemap = {}
    if os.path.exists(vmap_path):
        try:
            voicemap = json.load(open(vmap_path, encoding="utf-8"))
        except Exception:
            voicemap = {}

    done = 0
    failed = []
    no_de = []
    total = len(vkeys)

    for i, key in enumerate(vkeys):
        scene, num = key.split(":")
        wav_path = os.path.join(OUT_DIR, f"{scene}_{num}.wav")

        raw = de.get(key)
        if not raw or not raw.strip():
            no_de.append(key)
            continue

        text = fixup_german(strip_nameplate(fixup_german(raw)))
        if not text:
            no_de.append(key)
            continue

        speaker = zh_speaker(z.get(key))
        voice, rate, pitch, label = resolve_voice(speaker)
        rate, pitch = adjust_for_tone(text, speaker, rate, pitch)

        voicemap[key] = {
            "file": f"{scene}_{num}.wav",
            "speaker": label,
            "zh_speaker": speaker,
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "de_text": text,
        }

        if os.path.exists(wav_path) and os.path.getsize(wav_path) > 44:
            done += 1
            continue

        ok = False
        backoff = 2
        for attempt in range(4):
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                    mp3 = tf.name
                await synth(text, voice, rate, pitch, mp3, timeout=25)
                if os.path.getsize(mp3) == 0:
                    raise RuntimeError("empty mp3")
                to_wav(mp3, wav_path)
                os.unlink(mp3)
                ok = True
                break
            except Exception as e:
                err = str(e)
                try:
                    if os.path.exists(mp3):
                        os.unlink(mp3)
                except Exception:
                    pass
                if attempt < 3:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    failed.append(f"{key}\t{voice}\t{err[:120]}")

        if ok:
            done += 1

        if (i + 1) % 25 == 0 or i + 1 == total:
            dump_json(prog_path, {"processed": i + 1, "total": total,
                                  "done": done, "failed": len(failed)})
            dump_json(vmap_path, voicemap)
            print(f"[{i+1}/{total}] done={done} failed={len(failed)} no_de={len(no_de)}",
                  flush=True)

    dump_json(vmap_path, voicemap)
    with open(failed_path, "w", encoding="utf-8") as f:
        f.write("\n".join(failed) + ("\n" if failed else ""))
    dump_json(prog_path, {"processed": total, "total": total, "done": done,
                          "failed": len(failed), "no_de": no_de})

    print(f"\nDONE. wav={done} failed={len(failed)} no_de={len(no_de)}")
    if no_de:
        print("no German text for:", no_de)


if __name__ == "__main__":
    asyncio.run(main())
