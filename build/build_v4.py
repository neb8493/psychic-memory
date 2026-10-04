#!/usr/bin/env python3
"""Jack & Lexie's Big Day Out, v4 (council round 1 fixes).

Builds, from src2/ (original clips) and new/ (regenerated clips):
  out/episode_v4.mp4   8:00 single upload: cards, title band, VO, end card
  out/loop_unit.mp4    7:40 seamless loop unit: no cards, no title band, no VO, no end card;
                       last frame dissolves into the first, audio crossfades into itself
  out/loop_1h.mp4      loop_unit x 8 (61:20), stream-copied

Changes vs build_v2.sh:
  - S25, S28, V11, V13 replaced by on-model regenerations (new/)
  - V11 and V13 tell a one-way story, so they play once and the hold ping-pongs only their tail
  - store (V7, S18, S19), sunset (S36) and porch (S34, S35) graded toward blue/yellow (grade.py)
  - chapter cards dissolve from/to the neighbouring frames instead of dipping through black
  - audio: Lyria 3.5 bed arranged so every join sits under a chapter card, compressed to a
    narrow loudness range; park ambience outdoors, crickets at bedtime, one yip, one squeak
"""
import os, subprocess, json, sys
from pathlib import Path

W, H, FPS = 1920, 1080, 24
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONTR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SEG, OUT = Path("seg4"), Path("out"); SEG.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
NEW = {"S25", "S28", "V11", "V13"}
GRADE = {"V7": "store", "S18": "store", "S19": "store", "S36": "sunset", "S34": "green", "S35": "green"}

# name | kind | arg | seconds | mode         (identical order and durations to v2 = 480 s)
TL = """
001|gen|S1|3|direct
002|gen|V1|6|direct
003|gen|V2|6|direct
004|title|V2|5|pp
010|card|1. Good Morning|2|-
011|gen|V3|8|pp
013|gen|S5|10|direct
014|gen|V4|15|pp
016|gen|S7|17|pp
017|gen|V5|10|pp
019|gen|S9|8|direct
020|card|2. The Walk|2|-
021|gen|S13|20|fwd
022|gen|S14|10|direct
023|gen|V6|15|pp
025|gen|S16|13|fwd
026|gen|V7|10|pp
028|gen|S18|10|direct
029|gen|S19|10|direct
030|card|3. The Park|2|-
031|gen|V8|10|pp
033|gen|S21|8|direct
034|gen|S22|18|pp
035|gen|S23|7|direct
036|gen|S24|20|pp
037|gen|S25|7|direct
038|gen|V9|13|pp
040|gen|S27|10|direct
041|gen|S28|25|pp
050|card|4. Snack Time|2|-
051|gen|V10|13|pp
053|gen|S30|15|pp
054|gen|V11|12|tail
056|gen|S32|18|pp
060|card|5. Heading Home|2|-
061|gen|S36|30|fwd
062|gen|V12|8|pp
064|gen|S34|8|direct
065|gen|S35|12|direct
070|card|6. Bedtime|2|-
071|gen|V13|18|tail
073|gen|S38|12|direct
074|gen|S39|8|direct
075|gen|V14|12|pp
077|end||8|-
"""
ROWS = [r.split("|") for r in TL.strip().splitlines()]

def ff(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *map(str, args)], check=True)

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))

def norm(k):
    o = SEG / f"n_{k}.mp4"
    if o.exists(): return o
    src = Path("new" if k in NEW else "src2") / f"{k}.mp4"
    tmp = SEG / f"n0_{k}.mp4"
    ff("-i", src, "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p", *ENC, tmp)
    if k in GRADE:
        subprocess.run([sys.executable, "grade.py", GRADE[k], str(tmp), str(o)], check=True); tmp.unlink()
    else:
        tmp.rename(o)
    return o

def pingpong(src, o):
    if not o.exists():
        ff("-i", src, "-filter_complex", "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1[o]", "-map", "[o]", *ENC, o)
    return o

def shot(name, k, d, mode, out):
    n = norm(k)
    if mode == "direct":
        ff("-i", n, "-t", d, *ENC, out)
    elif mode == "pp":
        ff("-stream_loop", 40, "-i", pingpong(n, SEG / f"p_{k}.mp4"), "-t", d, *ENC, out)
    elif mode == "fwd":
        ff("-stream_loop", 40, "-i", n, "-t", d, *ENC, out)
    elif mode == "tail":   # play once, then hold by ping-ponging only the last 2 s (the settled pose)
        L = dur(n); tail = SEG / f"t_{k}.mp4"
        ff("-ss", L - 2, "-i", n, *ENC, tail)
        ff("-i", n, "-stream_loop", 40, "-i", pingpong(tail, SEG / f"tp_{k}.mp4"),
           "-filter_complex", f"[0:v][1:v]concat=n=2:v=1[c];[c]trim=0:{d},setpts=PTS-STARTPTS[o]", "-map", "[o]", *ENC, out)

def frame(p, which, out):
    if which == "first": ff("-i", p, "-frames:v", 1, out)
    else: ff("-sseof", -0.1, "-i", p, "-update", 1, "-frames:v", 1, out)
    return out

def card(name, text, d, prev, nxt, out):
    """Card dissolves in from the previous shot's last frame and out to the next shot's first frame."""
    (SEG / f"{name}.txt").write_text(text)
    a = frame(prev, "last", SEG / f"{name}_a.png"); b = frame(nxt, "first", SEG / f"{name}_b.png")
    x = 0.4
    ff("-f", "lavfi", "-i", f"color=c=0x1F4E9A:s={W}x{H}:d={d}:r={FPS}",
       "-loop", 1, "-t", d, "-i", a, "-loop", 1, "-t", d, "-i", b,
       "-filter_complex",
       f"[0:v]drawtext=fontfile={FONT}:textfile={SEG}/{name}.txt:fontcolor=0xFFD23F:fontsize=96:x=(w-tw)/2:y=(h-th)/2[c];"
       f"[1:v]format=yuva420p,fade=t=out:st=0:d={x}:alpha=1[a];"
       f"[2:v]format=yuva420p,fade=t=in:st={d - x - 1 / FPS}:d={x}:alpha=1[b];"   # fully opaque on the last frame
       f"[c][a]overlay=format=auto[ca];[ca][b]overlay=format=auto,format=yuv420p[o]",
       "-map", "[o]", "-t", d, *ENC, out)

def title(d, out, band=True):
    n = pingpong(norm("V2"), SEG / "p_V2.mp4")
    vf = "format=yuv420p"
    if band:
        (SEG / "t1.txt").write_text("Jack & Lexie's Big Day Out"); (SEG / "t2.txt").write_text("Dog TV in mostly blue and yellow, the colors dogs see best")
        vf = (f"drawbox=x=0:y=ih-360:w=iw:h=360:color=0x1F4E9A@0.88:t=fill,"
              f"drawtext=fontfile={FONT}:textfile={SEG}/t1.txt:fontcolor=0xFFD23F:fontsize=100:x=(w-tw)/2:y=h-300,"
              f"drawtext=fontfile={FONTR}:textfile={SEG}/t2.txt:fontcolor=0xFFF6D6:fontsize=40:x=(w-tw)/2:y=h-150,format=yuv420p")
    if band:   # band fades out over the last 0.8 s so it never overlaps the first chapter card's dissolve
        ff("-stream_loop", 20, "-i", n, "-t", d, "-filter_complex",
           f"[0:v]split[p][q];[q]{vf},format=yuva420p,fade=t=out:st={d - 0.8}:d=0.6:alpha=1[b];[p][b]overlay=format=auto,format=yuv420p[o]",
           "-map", "[o]", *ENC, out)
    else:
        ff("-stream_loop", 20, "-i", n, "-t", d, "-vf", vf, *ENC, out)

def endcard(d, prev, out):
    for i, t in enumerate(["Jack & Lexie will be back soon.", "Subscribe so your dog never watches alone.", "Made for dogs. Loved by their people."]):
        (SEG / f"e{i}.txt").write_text(t)
    a = frame(prev, "last", SEG / "end_a.png")
    ff("-f", "lavfi", "-i", f"color=c=0x1F4E9A:s={W}x{H}:d={d}:r={FPS}", "-loop", 1, "-t", d, "-i", a,
       "-filter_complex",
       f"[0:v]drawtext=fontfile={FONT}:textfile={SEG}/e0.txt:fontcolor=0xFFD23F:fontsize=84:x=(w-tw)/2:y=h*0.12,"
       f"drawtext=fontfile={FONT}:textfile={SEG}/e1.txt:fontcolor=0xFFD23F:fontsize=60:x=(w-tw)/2:y=h*0.12+130,"
       f"drawtext=fontfile={FONTR}:textfile={SEG}/e2.txt:fontcolor=0xFFF6D6:fontsize=40:x=(w-tw)/2:y=h*0.12+230[c];"
       f"[1:v]format=yuva420p,fade=t=out:st=0:d=0.6:alpha=1[a];[c][a]overlay=format=auto,fade=t=out:st={d - 2}:d=2,format=yuv420p[o]",
       "-map", "[o]", "-t", d, *ENC, out)

def build_video():
    # 1) all shots
    for name, kind, arg, d, mode in ROWS:
        o = SEG / f"{name}.mp4"
        if kind == "gen" and not o.exists(): shot(name, arg, float(d), mode, o); print("shot", name, arg, flush=True)
    if not (SEG / "004.mp4").exists(): title(5, SEG / "004.mp4")
    if not (SEG / "004L.mp4").exists(): title(5, SEG / "004L.mp4", band=False)
    # 2) cards need their neighbours
    for i, (name, kind, arg, d, mode) in enumerate(ROWS):
        o = SEG / f"{name}.mp4"
        if kind == "card" and not o.exists():
            card(name, arg, float(d), SEG / f"{ROWS[i - 1][0]}.mp4", SEG / f"{ROWS[i + 1][0]}.mp4", o)
        if kind == "end" and not o.exists():
            endcard(float(d), SEG / f"{ROWS[i - 1][0]}.mp4", o)
    # 3) episode
    (SEG / "ep.txt").write_text("".join(f"file '{n}.mp4'\n" for n, *_ in ROWS))
    ff("-f", "concat", "-safe", 0, "-i", SEG / "ep.txt", "-c", "copy", OUT / "video_ep.mp4")
    # 4) loop unit: drop cards + end card, plain title shot, last shot dissolves into the first frame
    loop = [("004L" if n == "004" else n) for n, k, *_ in ROWS if k not in ("card", "end")]
    first = frame(SEG / "001.mp4", "first", SEG / "loop_first.png")
    last = SEG / f"{loop[-1]}.mp4"; L = dur(last); x = 6.0   # slow night-to-morning ramp, no lights-on jump
    ff("-i", last, "-loop", 1, "-t", L, "-i", first, "-filter_complex",
       f"[1:v]format=yuva420p,fade=t=in:st={L - x - 1 / FPS}:d={x}:alpha=1[b];[0:v][b]overlay=format=auto,format=yuv420p[o]",
       "-map", "[o]", "-t", L, *ENC, SEG / "075X.mp4")
    loop[-1] = "075X"
    (SEG / "loop.txt").write_text("".join(f"file '{n}.mp4'\n" for n in loop))
    ff("-f", "concat", "-safe", 0, "-i", SEG / "loop.txt", "-c", "copy", OUT / "video_loop.mp4")

def timeline(include_cards):
    """Start time of every row in the given variant."""
    t, starts = 0.0, {}
    for n, k, a, d, m in ROWS:
        if not include_cards and k in ("card", "end"): continue
        starts[n] = t; t += float(d)
    return starts, t

if __name__ == "__main__":
    build_video()
    print(json.dumps({"episode": dur(OUT / "video_ep.mp4"), "loop": dur(OUT / "video_loop.mp4")}))
