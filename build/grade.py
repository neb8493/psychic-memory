#!/usr/bin/env python3
"""Dog-vision grade for specific shots: push greens toward yellow, swap red walls
for blue (store plate only), and give the sunset sky a blue top (sunset plate only).
Dogs and props are protected by hue/region/brightness rules, not by tracking.

usage: grade.py MODE IN.mp4 OUT.mp4     MODE in {store, sunset, green}
"""
import subprocess, sys, numpy as np

mode, src, dst = sys.argv[1:4]
W, H, FPS = 1920, 1080, 24
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
REDZONE = ((xx < 0.20 * W) & (yy < 0.62 * H)) | ((xx > 0.82 * W) & (yy < 0.42 * H))
SKYRAMP = np.clip(1 - yy / (0.30 * H), 0, 1)[..., None]          # 1 at top -> 0 at 30% height
SKYBLUE = np.array([110, 170, 225], np.float32)
WALLBLUE = np.array([91, 125, 184], np.float32)

def rgb_to_hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1); d = mx - mn + 1e-6
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-6), 0)
    return h, s, mx

def hsv_to_rgb(h, s, v):
    c = v * s; x = c * (1 - np.abs((h / 60) % 2 - 1)); m = v - c
    z = np.zeros_like(h); k = (h // 60).astype(int) % 6
    r = np.choose(k, [c, x, z, z, x, c]); g = np.choose(k, [x, c, c, x, z, z]); b = np.choose(k, [z, z, x, c, c, x])
    return np.stack([r + m, g + m, b + m], -1)

def greens_to_yellow(a):
    h, s, v = rgb_to_hsv(a)
    sel = (h > 70) & (h < 125) & (s > 0.08)                      # greens only; teal collar (measured 131-162) excluded
    h2 = np.where(sel, 62 + (h - 70) * 0.08, h)                 # fold green into yellow-olive
    out = hsv_to_rgb(h2, s, v)
    return np.where(sel[..., None], out, a)

def grade(a):
    a = a.astype(np.float32)
    a = greens_to_yellow(a)
    if mode == "store":
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        red = (r > g + 35) & (r > b + 35) & REDZONE
        # maroon wall right of the awning shares a region with Jack's head: select it by its muted
        # saturation (measured ~0.52) so his pure-red collar (saturation ~1.0) is untouched
        h, s, v = rgb_to_hsv(a)
        red |= ((h < 15) | (h > 345)) & (s > 0.35) & (s < 0.65) & (v > 150) & (xx > 0.74 * W) & (yy < 0.50 * H)
        L = (0.3 * r + 0.59 * g + 0.11 * b)[..., None]
        blue = WALLBLUE * (L / (0.3 * 91 + 0.59 * 125 + 0.11 * 184))
        a = np.where(red[..., None], blue, a)
    if mode == "sunset":
        # houses, fence, Lexie and Jack's tan all sit at hue ~30, so colour selection can't separate
        # them. Cool the whole warm cast multiplicatively instead (black stays black, so Jack keeps his
        # coat), then lift only the most saturated orange (the fence, s ~0.78; Lexie tops out ~0.61)
        # toward yellow.
        a = a * np.array([0.88, 0.98, 1.24], np.float32)
        h, s, v = rgb_to_hsv(np.clip(a, 0, 255))
        fence = (h > 20) & (h < 40) & (s > 0.70) & (v > 150)
        a = np.where(fence[..., None], hsv_to_rgb(np.where(fence, h + 14, h), s, v), a)
        L = (0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2])[..., None]
        bright = np.clip((L - 150) / 40, 0, 1)                   # sky only, never the black dog
        w = SKYRAMP * bright * 0.85
        a = a * (1 - w) + SKYBLUE * (L / 170) * w
    return np.clip(a, 0, 255).astype(np.uint8)

dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-an", dst], stdin=subprocess.PIPE)
n = W * H * 3
while True:
    buf = dec.stdout.read(n)
    if len(buf) < n: break
    enc.stdin.write(grade(np.frombuffer(buf, np.uint8).reshape(H, W, 3)).tobytes())
enc.stdin.close(); enc.wait(); dec.wait()
