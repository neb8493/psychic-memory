#!/usr/bin/env python3
"""
Synthesise a non-repeating rain bed matched to a short reference clip.

A 15-second clip cannot be a 3-hour bed. Even with a perfect crossfade the
CONTENT repeats -- the same droplet, the same rivulet, 700-odd times -- and a
listener lying awake at 3am is exactly the listener who will find it.

So instead of looping the reference, this measures it and rebuilds it. It
takes the clip's long-term average spectrum (its tonal fingerprint) and
imposes that on continuously fresh noise, overlap-added with random phase.
The result has the reference's character and never repeats, because every
block is new. Rain is close to spectrally-shaped noise with sparse transients,
so this is nearer to how rain actually behaves than any loop is.

What it does NOT reproduce is real rain's macro-structure -- gusts, squalls,
intensity drifting over minutes. For a sleep bed that is a feature: the spec
wants steady, and the only level move in the finished piece is the taper.

    python make_bed.py reference.mp4 --minutes 20 -o rainbed.wav
    python make_bed.py reference.mp4 --hours 3 -o rainbed.wav --droplets 0

Output feeds assemble.py as the rain source.

Requires: numpy, pydub, ffmpeg on PATH.
"""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

NFFT = 4096
OUT_SR = 44100
CHUNK_BLOCKS = 512          # blocks per disk write; keeps memory flat


def load_mono(path: Path) -> tuple[np.ndarray, int]:
    from pydub import AudioSegment
    seg = AudioSegment.from_file(path).set_channels(1)
    full = float(1 << (8 * seg.sample_width - 1))
    x = np.array(seg.get_array_of_samples(), dtype=np.float64) / full
    return x, seg.frame_rate


def steadiest_window(x: np.ndarray, sr: int, limit_db: float = 6.0
                     ) -> tuple[int, int]:
    """Longest span whose half-second RMS stays inside limit_db."""
    hop = max(sr // 2, 1)
    n = len(x) // hop
    if n < 4:
        return 0, len(x)
    r = np.array([20 * np.log10(np.sqrt(np.mean(x[i*hop:(i+1)*hop] ** 2)) + 1e-12)
                  for i in range(n)])
    best = (0, 0)
    for a in range(n):
        for b in range(a + 4, n + 1):
            seg = r[a:b]
            if seg.max() - seg.min() <= limit_db and (b - a) > (best[1] - best[0]):
                best = (a, b)
    if best[1] - best[0] < 4:          # nothing steady enough; use it all
        return 0, len(x)
    return best[0] * hop, best[1] * hop


def reference_spectrum(ref: np.ndarray, src_sr: int) -> np.ndarray:
    """Long-term average spectrum, resampled onto the output frequency grid.

    A reference recorded at 32 kHz carries nothing above 16 kHz. Rain does
    have air up there, and leaving the top octave empty reads as muffled, so
    the envelope is extrapolated past the reference's Nyquist along its own
    existing slope rather than cut to zero.
    """
    win = np.hanning(NFFT)
    acc, count = np.zeros(NFFT // 2 + 1), 0
    for i in range(0, max(len(ref) - NFFT, 1), NFFT // 2):
        acc += np.abs(np.fft.rfft(ref[i:i + NFFT] * win)) ** 2
        count += 1
    ltas = np.sqrt(acc / max(count, 1))

    src_f = np.fft.rfftfreq(NFFT, 1 / src_sr)
    out_f = np.fft.rfftfreq(NFFT, 1 / OUT_SR)
    env = np.interp(out_f, src_f, ltas, left=ltas[0], right=0.0)

    nyq = src_sr / 2
    above = out_f >= nyq
    if above.any():
        # continue the reference's own top-octave slope, in dB per octave
        band = (src_f >= nyq / 2) & (src_f < nyq)
        if band.sum() > 2:
            lo = float(np.mean(ltas[(src_f >= nyq / 2) & (src_f < nyq * 0.75)]) + 1e-12)
            hi = float(np.mean(ltas[(src_f >= nyq * 0.75) & (src_f < nyq)]) + 1e-12)
            slope = np.clip(20 * np.log10(hi / lo), -24, -3)
        else:
            slope = -12.0
        edge = float(env[~above][-1]) if (~above).any() else 1e-6
        octaves = np.log2(np.maximum(out_f[above], nyq) / nyq)
        env[above] = edge * 10 ** (slope * octaves / 20)
    return env


def shaped_block(rng, env: np.ndarray, win: np.ndarray) -> np.ndarray:
    """One overlap-add block of noise carrying the reference's spectrum."""
    S = np.fft.rfft(rng.normal(0, 1, NFFT) * win)
    return np.fft.irfft(S / (np.abs(S) + 1e-12) * env, NFFT) * win


def synth(out_path: Path, env: np.ndarray, seconds: float, droplets: float,
          seed: int, width: float) -> None:
    """Overlap-add fresh shaped noise straight to disk.

    Gain is fixed for the whole file. Normalising each chunk to its own peak
    would make a loud droplet in one chunk quieten everything around it --
    which measured as an 11 dB level swing, the exact fault this tool exists
    to avoid.
    """
    rng = np.random.default_rng(seed)
    win = np.hanning(NFFT)
    hop = NFFT // 2
    total = int(seconds * OUT_SR)

    # Establish the gain once, from a short probe, then never touch it again.
    probe = np.zeros(64 * hop + NFFT)
    for b in range(64):
        probe[b*hop:b*hop + NFFT] += shaped_block(rng, env, win)
    rms = float(np.sqrt(np.mean(probe[hop:-NFFT] ** 2))) or 1.0
    gain = 0.12 / rms                      # ~-18 dBFS RMS, ample headroom

    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(OUT_SR)

        # one hop of overlap carried between chunks so seams are continuous
        tail = np.zeros((hop, 2))
        written = 0
        next_pct = 0
        while written < total:
            nblk = CHUNK_BLOCKS
            buf = np.zeros((nblk * hop + NFFT, 2))
            buf[:hop] = tail
            for ch in range(2):
                for b in range(nblk):
                    buf[b*hop:b*hop + NFFT, ch] += shaped_block(rng, env, win)

            if droplets > 0:
                # Droplets are cut from the SAME shaped noise, not from white
                # noise. A white impulse is spectrally flat and a few per
                # second drags the whole bed bright; a shaped one carries the
                # reference's own timbre.
                span = nblk * hop
                for _ in range(int(droplets * span / OUT_SR)):
                    src = shaped_block(rng, env, win)
                    ln = int(rng.integers(60, 400))
                    off = int(rng.integers(0, NFFT - ln))
                    imp = src[off:off + ln] * np.exp(-np.linspace(0, 7, ln))
                    imp *= 0.9 * rng.random() / (np.max(np.abs(imp)) + 1e-12)
                    i = int(rng.integers(0, span))
                    for ch in range(2):
                        j = max(0, min(i + int(rng.integers(-40, 40)),
                                       len(buf) - ln))
                        buf[j:j+ln, ch] += imp * rms

            # decorrelate the channels for width without phasiness
            mid = buf.mean(axis=1, keepdims=True)
            buf = mid * (1 - width) + buf * width

            body, tail = buf[:nblk * hop], buf[nblk * hop:nblk * hop + hop]
            take = min(len(body), total - written)
            block = body[:take] * gain
            wav.writeframes((np.clip(block, -1, 1)
                             * 32767).astype(np.int16).tobytes())
            written += take

            pct = int(100 * written / total)
            if pct >= next_pct:
                print(f"\r  {pct:3d}%  {written/OUT_SR/60:6.1f} min", end="", flush=True)
                next_pct = pct + 5
        print()


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("reference", help="short clip to match (video or audio)")
    p.add_argument("-o", "--out", default="rainbed.wav")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--minutes", type=float)
    g.add_argument("--hours", type=float)
    p.add_argument("--droplets", type=float, default=14.0,
                   help="transients per second; 0 for pure shaped noise")
    p.add_argument("--width", type=float, default=0.85,
                   help="0 = mono, 1 = fully decorrelated channels")
    p.add_argument("--seed", type=int, default=0, help="0 picks a random one")
    args = p.parse_args()

    ref_path = Path(args.reference)
    if not ref_path.exists():
        print(f"No such file: {ref_path}", file=sys.stderr)
        return 1

    seconds = (args.hours * 3600 if args.hours
               else (args.minutes * 60 if args.minutes else 20 * 60))

    print(f"Reading {ref_path.name}")
    x, sr = load_mono(ref_path)
    a, b = steadiest_window(x, sr)
    ref = x[a:b]
    print(f"  {len(x)/sr:.1f}s at {sr} Hz")
    print(f"  steadiest window {a/sr:.1f}s - {b/sr:.1f}s "
          f"({len(ref)/sr:.1f}s) -- matching this")
    if sr < OUT_SR:
        print(f"  reference stops at {sr/2/1000:.1f} kHz; "
              "extrapolating the top octave")

    env = reference_spectrum(ref, sr)
    seed = args.seed or int(np.random.SeedSequence().entropy % (2**31))
    print(f"\nSynthesising {seconds/60:.0f} min "
          f"(droplets {args.droplets:g}/s, width {args.width:g}, seed {seed})")
    synth(Path(args.out), env, seconds, args.droplets, seed, args.width)

    mb = Path(args.out).stat().st_size / 1e6
    print(f"\nWrote {args.out}  ({mb:.0f} MB, {seconds/60:.0f} min, never repeats)")
    print(f"  Check it:  python assemble.py {args.out} --analyze-only")
    print(f"  Then:      python assemble.py {args.out} --narration narration.wav "
          "--still frame.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
