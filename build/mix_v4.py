#!/usr/bin/env python3
"""Audio for v4: chapter-aligned Lyria bed, narrow loudness range, ambience and cues.

  out/mix_ep.wav    8:00, with VO (ducked bed under it) and end fade
  out/mix_loop.wav  loop-unit length, no VO, last 3 s crossfaded into the head so it repeats seamlessly
"""
import subprocess, numpy as np
from pathlib import Path
from build_v4 import ROWS, timeline

SR = 48000
OUT = Path("out")
# where in the Lyria take each chapter's music starts (s); usable take = 0..158 s (it fades out after)
OFFSETS = {"cold+1": 0, "2": 65, "3": 25, "4": 90, "5": 10, "6": 0}
XF = 2.0

def load(p, mono=False):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"])
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

def ffwav(x, p):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", str(p)], input=x.astype(np.float32).tobytes(), check=True)

def ep_curves(n):
    t = np.linspace(0, np.pi / 2, n)[:, None]; return np.cos(t), np.sin(t)   # equal power

def lufs(p):
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", str(p), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float(out.split("Integrated loudness:")[1].split("I:")[1].split("LUFS")[0])
    LRA = float(out.split("Loudness range:")[1].split("LRA:")[1].split("LU")[0])
    return I, LRA

def gain_to(x, target, tmp):
    ffwav(x, tmp); I, _ = lufs(tmp); return x * 10 ** ((target - I) / 20)

def chapter_bounds(include_cards):
    starts, total = timeline(include_cards)
    names = [r[0] for r in ROWS]
    first_after = lambda card: names[names.index(card) + 1]
    # chapter music changes under the card (episode) or at the first shot of the chapter (loop)
    keys = ["020", "030", "050", "060", "070"]
    b = [starts[k] if include_cards else starts[first_after(k)] for k in keys]
    return [0.0] + b + [total], total, starts

def music(include_cards, take):
    bounds, total, _ = chapter_bounds(include_cards)
    offs = list(OFFSETS.values())
    n = int((total + 4) * SR); out = np.zeros((n, 2), np.float32); xn = int(XF * SR)
    fo, fi = ep_curves(xn)
    for i in range(len(offs)):
        a, b = bounds[i], bounds[i + 1]
        lead = 0                                                          # crossfade sits in [b, b+XF]: under the card in the episode, first 2 s of the chapter in the loop
        s0 = int((a - lead) * SR); length = int((b - a + lead + XF) * SR)
        seg = take[int(offs[i] * SR): int(offs[i] * SR) + length].copy()
        if i > 0: seg[:xn] *= fi
        if i < len(offs) - 1: seg[-xn:] *= fo
        out[s0:s0 + len(seg)] += seg
    return out, total

def tile(bed, seconds):
    n = int(seconds * SR); xn = 2 * SR; fo, fi = ep_curves(xn); out = np.zeros((n + len(bed), 2), np.float32); pos = 0
    while pos < n:
        seg = bed.copy(); seg[:xn] *= fi; seg[-xn:] *= fo
        out[pos:pos + len(seg)] += seg; pos += len(seg) - xn
    return out[:n]

def place(dst, clip, t, fade_in=0.0, fade_out=0.0):
    c = clip.copy(); s = int(t * SR)
    if fade_in: k = int(fade_in * SR); c[:k] *= np.linspace(0, 1, k)[:, None]
    if fade_out: k = int(fade_out * SR); c[-k:] *= np.linspace(1, 0, k)[:, None]
    e = min(len(dst), s + len(c)); dst[s:e] += c[:e - s]

def compress(inp, outp):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(inp), "-af",
                    "acompressor=threshold=-28dB:ratio=3.5:attack=400:release=2500:knee=6,"
                    "acompressor=threshold=-20dB:ratio=2:attack=800:release=4000", str(outp)], check=True)

def build(include_cards):
    tag = "ep" if include_cards else "loop"
    take = load("src2/lyria.mp3")
    m, total = music(include_cards, take)
    ffwav(m, OUT / f"m_raw_{tag}.wav"); compress(OUT / f"m_raw_{tag}.wav", OUT / f"m_c_{tag}.wav")
    m = gain_to(load(OUT / f"m_c_{tag}.wav"), -19.0, OUT / "tmp.wav")
    mix = m.copy()
    _, _, starts = chapter_bounds(include_cards)
    names = [r[0] for r in ROWS]
    end_of = lambda k: starts[k] + float(ROWS[names.index(k)][3])
    park = gain_to(tile(load("sfx/bed_park.mp3"), end_of("065") - starts["021"]), -37.0, OUT / "tmp.wav")
    place(mix, park, starts["021"], 4, 4)
    crk_len = (total if not include_cards else end_of("075")) - starts["071"]
    crk = gain_to(tile(load("sfx/bed_crk.mp3"), crk_len), -39.0, OUT / "tmp.wav")
    place(mix, crk, starts["071"], 5, 3 if include_cards else 0.5)
    yip = load("sfx/yip4.mp3"); yip *= 10 ** ((-20 - 20 * np.log10(np.abs(yip).max())) / 20)     # peak -20 dBFS
    place(mix, yip, starts["003"] + 0.5)
    sq = load("sfx/sq3.mp3"); sq *= 10 ** ((-22 - 20 * np.log10(np.abs(sq).max())) / 20)
    place(mix, sq, starts["041"] + 20.0)
    if include_cards:
        vo = gain_to(load("src2/vo.mp3"), -20.0, OUT / "tmp.wav")
        t0 = 14.0; s, e = int((t0 - 1.0) * SR), int((t0 + len(vo) / SR + 1.0) * SR)
        duck = np.ones(len(mix), np.float32); k = int(1.0 * SR)
        duck[s:e] = 0.5; duck[s:s + k] = np.linspace(1, 0.5, k); duck[e - k:e] = np.linspace(0.5, 1, k)
        mix *= duck[:, None]; place(mix, vo, t0)
        mix = mix[:int(total * SR)]
        f = int(4 * SR); mix[-f:] *= np.linspace(1, 0, f)[:, None]
    else:
        L = int(total * SR); x = int(3 * SR); fo, fi = ep_curves(x)
        head = mix[:x] * fi + mix[L:L + x] * fo                          # tail beyond L folds onto the head
        mix = mix[:L].copy(); mix[:x] = head
    ffwav(mix, OUT / f"mix_pre_{tag}.wav")
    # two-pass linear loudnorm: level only, no extra dynamics
    meas = subprocess.run(["ffmpeg", "-v", "info", "-i", str(OUT / f"mix_pre_{tag}.wav"), "-af",
                           "loudnorm=I=-16:TP=-2:LRA=7:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    import json; j = json.loads(meas[meas.rindex("{"):])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(OUT / f"mix_pre_{tag}.wav"), "-af",
                    f"loudnorm=I=-16:TP=-2:LRA=7:linear=true:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
                    f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}",
                    "-ar", str(SR), str(OUT / f"mix_{tag}.wav")], check=True)
    print(tag, "total", total, "LUFS/LRA", lufs(OUT / f"mix_{tag}.wav"))

if __name__ == "__main__":
    build(True); build(False)
