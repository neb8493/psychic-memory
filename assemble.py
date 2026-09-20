#!/usr/bin/env python3
"""
Assemble the finished 3-hour master for a 3AM Sessions episode.

Takes a rain (or other ambient) source, the narration rendered by render.py,
and a still frame, and produces the upload-ready mp4.

The rain never stops and never jumps. Every level move is a slow ramp defined
in TAPER below, and the long descent from 0:32:00 to 2:30:00 runs at about
0.07 dB per minute -- far under the threshold where anyone notices a change,
but by hour two the bed is quiet enough to meet a sleeper's lowered arousal
threshold.

Stages, each written to its own file under --work so you can listen to any of
them:

    1  analyse   the source, and refuse to loop something that isn't steady
    2  loop      a seamless unit, crossfaded so the wrap has no seam
    3  bed       tiled to full length with the taper envelope applied
    4  mix       narration over the bed
    5  master    loudness-normalised audio
    6  video     still frame + master -> mp4

Usage
    python assemble.py rain.wav --analyze-only
    python assemble.py rain.wav --narration narration.wav --still frame.png
    python assemble.py rain.wav --bed-only            # no voice: variant beds

Requires: pydub, numpy, and ffmpeg/ffprobe on PATH.
"""

from __future__ import annotations

import argparse
import json
import math
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# --- The spec ---------------------------------------------------------------

TOTAL = 3 * 3600                 # 3:00:00
VOICE_OUT = 23 * 60 + 52         # 0:23:52, measured from the Ep.1 render

# (seconds, rain level in dBFS). Levels ramp linearly in dB between points and
# hold at the last value. Times key off VOICE_OUT so a re-paced script moves
# the whole curve with it rather than desynchronising from the narration.
TAPER: list[tuple[float, float]] = [
    (0,                 -22.0),   # cold start, already at full
    (12,                -26.0),   # duck as the voice enters
    (17 * 60 + 40,      -26.0),   # held flat under narration
    (VOICE_OUT,         -21.0),   # rises as the voice thins out
    (32 * 60,           -19.0),   # rain takes the room
    (2 * 3600 + 30 * 60, -27.0),  # the long taper, ~8 dB over 118 minutes
    (TOTAL - 10,        -27.0),   # held
    (TOTAL,            -60.0),    # final fade out
]

TARGET_LUFS = -18.0
TARGET_TP = -3.0
DEFAULT_CROSSFADE = 20.0         # seconds; long enough to hide a wrap

# A source whose per-second level swings more than this is not steady rain.
# The Veo-generated clip measured 20.5 dB and would have surged every 8s.
STEADINESS_LIMIT_DB = 6.0
# Rain lives in the patter and hiss. A source that is mostly sub-200 Hz is a
# rumble bed, not rain, however it was labelled. The high-frequency floor alone
# is a weak test -- the Veo clip cleared it by 0.4% while being two-thirds
# rumble -- so the low-end ceiling is the one that actually discriminates.
MIN_HIGH_FRACTION = 0.08
MAX_LOW_FRACTION = 0.50


# --- Small helpers ----------------------------------------------------------

def hms(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def run(cmd: list[str], quiet: bool = True) -> None:
    if not quiet:
        print("   $", " ".join(shlex.quote(c) for c in cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-12:]
        raise RuntimeError("ffmpeg failed:\n  " + "\n  ".join(tail))


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def need_tools() -> None:
    missing = [t for t in ("ffmpeg", "ffprobe") if not shutil.which(t)]
    if missing:
        raise SystemExit(f"Not on PATH: {', '.join(missing)}")


# --- Stage 1: is this source usable at all? ---------------------------------

@dataclass
class SourceReport:
    seconds: float
    sample_rate: int
    spread_db: float
    high_fraction: float
    low_fraction: float
    band_pct: dict[str, float]
    has_audio: bool

    @property
    def steady(self) -> bool:
        return self.spread_db <= STEADINESS_LIMIT_DB

    @property
    def bright_enough(self) -> bool:
        return self.high_fraction >= MIN_HIGH_FRACTION

    @property
    def not_rumble(self) -> bool:
        return self.low_fraction <= MAX_LOW_FRACTION

    @property
    def usable(self) -> bool:
        return (self.has_audio and self.steady
                and self.bright_enough and self.not_rumble)


def analyse(path: Path) -> SourceReport:
    """Measure steadiness and spectral balance before committing to a loop."""
    import numpy as np
    from pydub import AudioSegment

    info = probe(path)
    has_audio = any(s.get("codec_type") == "audio" for s in info["streams"])
    if not has_audio:
        return SourceReport(0.0, 0, 0.0, 0.0, 0.0, {}, False)

    seg = AudioSegment.from_file(path).set_channels(1)
    sr = seg.frame_rate
    x = np.array(seg.get_array_of_samples(), dtype=float)
    x /= float(1 << (8 * seg.sample_width - 1))

    # Per-second RMS: a steady bed barely moves, a generated swell does not.
    n_sec = max(1, int(len(x) / sr))
    rms = [20 * math.log10(float(np.sqrt(np.mean(x[i * sr:(i + 1) * sr] ** 2))) + 1e-12)
           for i in range(n_sec)]
    spread = (max(rms) - min(rms)) if len(rms) > 1 else 0.0

    window = x[: sr * 30] if len(x) > sr * 30 else x
    spec = np.abs(np.fft.rfft(window * np.hanning(len(window))))
    freq = np.fft.rfftfreq(len(window), 1 / sr)
    power = spec ** 2
    total = float(power.sum()) or 1.0
    bands = {"low rumble": (20, 200), "body": (200, 1000),
             "patter": (1000, 4000), "hiss": (4000, 10000), "air": (10000, 20000)}
    band_pct = {k: 100 * float(power[(freq >= lo) & (freq < hi)].sum()) / total
                for k, (lo, hi) in bands.items()}
    high = (band_pct["patter"] + band_pct["hiss"] + band_pct["air"]) / 100
    low = band_pct["low rumble"] / 100

    return SourceReport(len(x) / sr, sr, spread, high, low, band_pct, True)


def print_report(r: SourceReport, path: Path) -> None:
    print(f"\nSource: {path.name}")
    if not r.has_audio:
        print("  No audio stream in this file. It is video only.")
        return
    print(f"  duration            {r.seconds:8.1f}s")
    print(f"  sample rate         {r.sample_rate:8d} Hz")
    mark = "ok" if r.steady else "FAIL"
    print(f"  level spread        {r.spread_db:8.1f} dB   [{mark}] "
          f"steady rain stays under {STEADINESS_LIMIT_DB:.0f} dB")
    mark = "ok" if r.bright_enough else "FAIL"
    print(f"  energy above 1 kHz  {r.high_fraction * 100:7.1f}%    [{mark}] "
          f"rain texture needs at least {MIN_HIGH_FRACTION * 100:.0f}%")
    mark = "ok" if r.not_rumble else "FAIL"
    print(f"  energy below 200 Hz {r.low_fraction * 100:7.1f}%    [{mark}] "
          f"rain is not a rumble bed; stay under {MAX_LOW_FRACTION * 100:.0f}%")
    print("  spectrum:")
    for name, pct in r.band_pct.items():
        print(f"      {name:12s} {pct:5.1f}%")
    if r.seconds < 60:
        print(f"\n  Note: {r.seconds:.0f}s is short for a 3-hour bed "
              f"({TOTAL / max(r.seconds, 1):.0f} repetitions). "
              "Aim for 10-15 minutes.")


# --- Stage 2: a loop unit with no audible wrap ------------------------------

def build_loop_unit(src: Path, out: Path, crossfade_s: float) -> float:
    """body + crossfade(tail, head), which tiles with no seam at the wrap.

    The crossfade is EQUAL POWER (cos/sin), not equal gain (linear). Rain is
    uncorrelated with itself, so two linearly-faded copies sum in power rather
    than amplitude and the overlap loses 3 dB at its midpoint -- an audible
    lull on every repetition. cos^2 + sin^2 = 1 holds the power flat instead.
    """
    import numpy as np
    from pydub import AudioSegment

    seg = AudioSegment.from_file(src).set_frame_rate(44100).set_channels(2)
    sr, width = seg.frame_rate, seg.sample_width
    x_ms = int(crossfade_s * 1000)
    if len(seg) < 3 * x_ms:
        x_ms = max(250, len(seg) // 3)
        print(f"  source is short; crossfade reduced to {x_ms / 1000:.1f}s")

    full = float(1 << (8 * width - 1))
    a = np.array(seg.get_array_of_samples(), dtype=np.float64).reshape(-1, 2) / full
    x = int(sr * x_ms / 1000)

    head, tail, body = a[:x], a[-x:], a[x:-x]
    ramp = np.linspace(0.0, 1.0, x, endpoint=False)[:, None]
    seam = tail * np.cos(ramp * np.pi / 2) + head * np.sin(ramp * np.pi / 2)

    unit = np.clip(np.vstack([body, seam]), -1.0, 1.0)   # len = len(a) - x
    pcm = (unit * (full - 1)).astype(np.int16)
    AudioSegment(pcm.tobytes(), frame_rate=sr, sample_width=2,
                 channels=2).export(out, format="wav")
    return len(unit) / sr


# --- Stage 3: tile to length and apply the taper ----------------------------

def taper_expression(points: list[tuple[float, float]]) -> str:
    """Piecewise-linear dB envelope as a flat (non-nested) ffmpeg expression."""
    terms = []
    for (t0, d0), (t1, d1) in zip(points, points[1:]):
        span = max(t1 - t0, 1e-6)
        slope = (d1 - d0) / span
        terms.append(
            f"(gte(t,{t0:.3f})*lt(t,{t1:.3f})*({d0:.4f}+{slope:.8f}*(t-{t0:.3f})))")
    t_last, d_last = points[-1]
    terms.append(f"(gte(t,{t_last:.3f})*{d_last:.4f})")
    return f"pow(10\\,({'+'.join(terms)})/20)"


def build_bed(unit: Path, unit_s: float, out: Path, total_s: float,
              points: list[tuple[float, float]], verbose: bool) -> None:
    loops = math.ceil(total_s / unit_s)
    run(["ffmpeg", "-v", "error", "-y",
         "-stream_loop", str(loops), "-i", str(unit),
         "-t", f"{total_s:.3f}",
         "-af", f"volume=volume='{taper_expression(points)}':eval=frame",
         "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(out)],
        quiet=not verbose)


# --- Stages 4-6: mix, normalise, encode -------------------------------------

def normalise(src: Path, out: Path, verbose: bool) -> None:
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
         "-af", f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11",
         "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(out)],
        quiet=not verbose)


def mix(bed: Path, narration: Path, out: Path, verbose: bool) -> None:
    # The narration carries its own 12s of leading silence from the script's
    # opening [P 12], so it lines up at t=0 with no offset.
    run(["ffmpeg", "-v", "error", "-y", "-i", str(bed), "-i", str(narration),
         "-filter_complex",
         "[1:a]apad[v];[0:a][v]amix=inputs=2:duration=first:"
         "dropout_transition=0:normalize=0[out]",
         "-map", "[out]", "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
         str(out)], quiet=not verbose)


def encode(still: Path, audio: Path, out: Path, fps: int, verbose: bool) -> None:
    run(["ffmpeg", "-v", "error", "-y",
         "-loop", "1", "-framerate", str(fps), "-i", str(still),
         "-i", str(audio),
         "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
         "-crf", "23", "-pix_fmt", "yuv420p", "-r", str(fps),
         # The frame never changes, so nearly all the bitrate goes to
         # keyframes. A 5-minute GOP cut a 3-hour encode from 478 MB to
         # 96 MB in testing. B-frames help here; -bf 0 nearly doubled it.
         "-g", str(max(fps * 300, 2)),
         "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
         "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", str(out)], quiet=not verbose)


# --- Verification -----------------------------------------------------------

def verify_bed(bed: Path, points: list[tuple[float, float]]) -> None:
    """Measure the rendered bed at each breakpoint and compare with the spec."""
    print("\nTaper check (measured against spec):")
    print(f"  {'time':>9}{'spec':>9}{'measured':>11}{'delta':>8}")
    worst = 0.0
    for t, want in points[:-1]:
        probe_at = min(t + 5, TOTAL - 5)
        out = subprocess.run(
            ["ffmpeg", "-v", "info", "-ss", f"{probe_at:.2f}", "-t", "3",
             "-i", str(bed), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True, text=True).stderr
        got = next((float(l.split(":")[1].strip().split()[0])
                    for l in out.splitlines() if "mean_volume" in l), None)
        if got is None:
            continue
        # mean_volume is RMS of the material, not its peak; what matters is
        # that the *shape* tracks, so report the delta and flag drift.
        delta = got - want
        worst = max(worst, abs(delta - 0))
        print(f"  {hms(t):>9}{want:8.1f}dB{got:10.1f}dB{delta:+7.1f}")
    print("\n  The absolute offset reflects the source's own RMS; what matters")
    print("  is that the measured column falls monotonically after 0:32:00.")


# --- Driver -----------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rain", help="rain / ambient source file")
    p.add_argument("--narration", help="narration.wav from render.py")
    p.add_argument("--still", help="still frame (png/jpg)")
    p.add_argument("--out", default="master.mp4")
    p.add_argument("--work", default="build", help="directory for stage files")
    p.add_argument("--total", type=float, default=TOTAL, help="length in seconds")
    p.add_argument("--crossfade", type=float, default=DEFAULT_CROSSFADE)
    p.add_argument("--fps", type=int, default=1,
                   help="a still needs no more; low fps keeps the file small")
    p.add_argument("--analyze-only", action="store_true",
                   help="report on the source and stop")
    p.add_argument("--bed-only", action="store_true",
                   help="build the rain bed with no narration")
    p.add_argument("--force", action="store_true",
                   help="proceed even if the source fails the checks")
    p.add_argument("--verify", action="store_true",
                   help="measure the rendered bed against the taper")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    need_tools()
    rain = Path(args.rain)
    if not rain.exists():
        print(f"No such file: {rain}", file=sys.stderr)
        return 1

    print("Stage 1  analysing source")
    report = analyse(rain)
    print_report(report, rain)
    if args.analyze_only:
        return 0 if report.usable else 2
    if not report.usable and not args.force:
        print("\nThis source will not hold up as a 3-hour bed.")
        if not report.has_audio:
            print("  It has no audio track.")
        if report.has_audio and not report.steady:
            print(f"  It swings {report.spread_db:.1f} dB, so every repetition "
                  f"surges. At {report.seconds:.0f}s that is "
                  f"{args.total / max(report.seconds, 1):.0f} surges over three hours.")
        if report.has_audio and not report.bright_enough:
            print(f"  Only {report.high_fraction * 100:.1f}% of its energy is "
                  "above 1 kHz; the rain texture is missing.")
        if report.has_audio and not report.not_rumble:
            print(f"  {report.low_fraction * 100:.0f}% of its energy is below "
                  "200 Hz. That is a rumble bed, not rain.")
        print("\nPass --force to build it anyway.")
        return 2

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    unit, bed = work / "loop_unit.wav", work / "rain_bed.wav"
    mixed, master = work / "mixed.wav", work / "master.wav"

    print(f"\nStage 2  building loop unit (crossfade {args.crossfade:.0f}s)")
    unit_s = build_loop_unit(rain, unit, args.crossfade)
    reps = args.total / unit_s
    print(f"  unit {unit_s:.1f}s -> {reps:.1f} repetitions over {hms(args.total)}")

    points = [(t, d) for t, d in TAPER if t <= args.total]
    if points[-1][0] < args.total:
        points.append((args.total, TAPER[-1][1]))

    print(f"\nStage 3  tiling to {hms(args.total)} and applying the taper")
    build_bed(unit, unit_s, bed, args.total, points, args.verbose)
    if args.verify:
        verify_bed(bed, points)

    if args.bed_only or not args.narration:
        if not args.bed_only:
            print("\n  No --narration given; building the bed alone.")
        print("\nStage 4  normalising")
        normalise(bed, master, args.verbose)
    else:
        voice = Path(args.narration)
        if not voice.exists():
            print(f"No such file: {voice}", file=sys.stderr)
            return 1
        vn = work / "narration_norm.wav"
        print("\nStage 4  normalising narration and mixing over the bed")
        normalise(voice, vn, args.verbose)
        mix(bed, vn, mixed, args.verbose)
        normalise(mixed, master, args.verbose)

    if not args.still:
        print(f"\nDone (audio only): {master}")
        return 0

    still = Path(args.still)
    if not still.exists():
        print(f"No such file: {still}", file=sys.stderr)
        return 1

    print(f"\nStage 5  encoding {hms(args.total)} of video at {args.fps} fps")
    out = Path(args.out)
    encode(still, master, out, args.fps, args.verbose)

    info = probe(out)
    dur = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / 1e6
    print(f"\nWrote {out}")
    print(f"  duration  {hms(dur)}")
    print(f"  size      {size_mb:.0f} MB")
    print(f"  stages    {work}/  (listen to any of them before you upload)")
    if not args.bed_only and args.narration:
        print(f"\n  Check nothing exists after {hms(VOICE_OUT)}, and listen to "
              "the last 10 minutes at sleeping volume.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
