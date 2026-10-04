#!/usr/bin/env python3
"""Renders the Vayu boot logo animation (M1: "draw in, then flow") into the
PNG frames the Plymouth theme plays (splash/theme/). Re-run after changing
the logo or the timing, and commit the frames with it:

    splash/make-frames.py

Needs rsvg-convert (librsvg). The frames are transparent; vayu.script
paints the black background and centres them.

  intro-NNN.png  the letters write themselves, then the wind line sweeps
                 out and curls (played once)
  logo.png       the finished logo, shown under every glow frame
  glow-NNN.png   a soft light running along the wind line (looped)

Dash lengths are computed here from the path geometry rather than with
SVG's pathLength, so the result doesn't depend on the renderer.
"""
import math
import os
import re
import subprocess
import sys
import tempfile

FPS = 25
# Canvas in logo units, and the pixel size of a frame at 1920x1080
# (vayu.script scales the frames to other screen heights).
VIEW = (-12, -8, 318, 126)
WIDTH = 541
HEIGHT = round(WIDTH * VIEW[3] / VIEW[2])

LETTERS = [  # V, A (no crossbar), Y, U
    "M0 0 L22 52 L44 0",
    "M84 52 L106 0 L128 52",
    "M168 0 L190 27 L212 0 M190 27 V52",
    "M252 0 V32 C252 45 262 52 274 52 C286 52 296 45 296 32 V0",
]
WIND = "M-6 80 H262 C284 80 300 90 294 102 C289 111 276 109 277 99"

# Timing, in seconds, as in the approved browser preview.
LETTER_DUR, LETTER_STAGGER = 0.9, 0.15
WIND_START, WIND_DUR = 0.9, 1.2
INTRO_END = 2.2
GLOW_PERIOD = 2.4
GLOW_LEN = 0.12  # fraction of the wind line lit at once

GRADIENT = ('<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="0" '
            'x2="300" y2="0"><stop offset="0" stop-color="#cba6f7"/>'
            '<stop offset="1" stop-color="#f5e0dc"/></linearGradient>')


def path_length(d):
    """Length of a path made of absolute M/L/H/V/C commands."""
    tokens = re.findall(r"[MLHVC]|-?[\d.]+", d)
    total, x, y, i, cmd = 0.0, 0.0, 0.0, 0, None
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
        nums = lambda n: [float(t) for t in tokens[i:i + n]]
        if cmd == "M":
            x, y = nums(2); i += 2
        elif cmd in "LHV":
            if cmd == "L":
                nx, ny = nums(2); i += 2
            elif cmd == "H":
                nx, ny = nums(1)[0], y; i += 1
            else:
                nx, ny = x, nums(1)[0]; i += 1
            total += math.hypot(nx - x, ny - y)
            x, y = nx, ny
        elif cmd == "C":
            x1, y1, x2, y2, nx, ny = nums(6); i += 6
            px, py = x, y
            for k in range(1, 201):
                t = k / 200
                mt = 1 - t
                bx = mt**3 * x + 3 * mt * mt * t * x1 + 3 * mt * t * t * x2 + t**3 * nx
                by = mt**3 * y + 3 * mt * mt * t * y1 + 3 * mt * t * t * y2 + t**3 * ny
                total += math.hypot(bx - px, by - py)
                px, py = bx, by
            x, y = nx, ny
    return total


def bezier(x1, y1, x2, y2):
    """CSS cubic-bezier() easing as a function of progress 0..1."""
    def f(p):
        if p <= 0 or p >= 1:
            return min(max(p, 0.0), 1.0)
        lo, hi = 0.0, 1.0
        for _ in range(40):  # solve x(t) = p by bisection
            t = (lo + hi) / 2
            x = 3 * (1 - t)**2 * t * x1 + 3 * (1 - t) * t * t * x2 + t**3
            lo, hi = (t, hi) if x < p else (lo, t)
        t = (lo + hi) / 2
        return 3 * (1 - t)**2 * t * y1 + 3 * (1 - t) * t * t * y2 + t**3
    return f


draw_letter = bezier(.6, 0, .3, 1)
draw_wind = bezier(.5, 0, .2, 1)
run_glow = bezier(.45, 0, .25, 1)


def stroke(d, width, drawn):
    """A gradient stroke with only the first `drawn` fraction visible. Each
    subpath (the Y's stem) is its own <path>, drawn after the one before:
    cairo restarts the dash at every moveto, which left a dot there."""
    subpaths = ["M" + s for s in d.split("M") if s.strip()]
    lengths = [path_length(s) for s in subpaths]
    left = sum(lengths) * drawn
    out = ""
    for s, length in zip(subpaths, lengths):
        if left <= 0:
            break
        dash = "" if left >= length else (
            f' stroke-dasharray="{left:.3f} {length * 2:.3f}"')
        out += (f'<path d="{s.strip()}" fill="none" stroke="url(#g)" stroke-width="{width}" '
                f'stroke-linecap="round" stroke-linejoin="round"{dash}/>')
        left -= length
    return out


def svg(body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(map(str, VIEW))}" '
            f'width="{WIDTH}" height="{HEIGHT}"><defs>{GRADIENT}{defs}</defs>{body}</svg>')


def progress(t, start, dur, ease):
    return ease(min(max((t - start) / dur, 0.0), 1.0))


def intro_frame(t):
    body = "".join(stroke(d, 4, progress(t, i * LETTER_STAGGER, LETTER_DUR, draw_letter))
                   for i, d in enumerate(LETTERS))
    return svg(body + stroke(WIND, 3, progress(t, WIND_START, WIND_DUR, draw_wind)))


def glow_frame(t):
    """The light: a blurred white dash travelling along the wind line,
    fading in over the first 15% of its run and out over the last."""
    p = t / GLOW_PERIOD
    opacity = 0.9 * min(1.0, p / 0.15, (1 - p) / 0.15)
    length = path_length(WIND)
    offset = (GLOW_LEN - (1 + GLOW_LEN) * run_glow(p)) * length
    blur = ('<filter id="b" x="-20%" y="-50%" width="140%" height="200%">'
            '<feGaussianBlur stdDeviation="1.6"/></filter>')
    body = (f'<path d="{WIND}" fill="none" stroke="#fff" stroke-width="3.5" '
            f'stroke-linecap="round" stroke-dasharray="{GLOW_LEN * length:.3f} {length * 2:.3f}" '
            f'stroke-dashoffset="{offset:.3f}" opacity="{opacity:.3f}" filter="url(#b)"/>')
    return svg(body, blur)


def render(svg_text, out):
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
        f.write(svg_text)
    try:
        subprocess.run(["rsvg-convert", f.name, "-o", out], check=True)
    finally:
        os.unlink(f.name)


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme")
    os.makedirs(out, exist_ok=True)
    for name in os.listdir(out):
        if re.fullmatch(r"(intro|glow)-\d{3}\.png|logo\.png", name):
            os.unlink(os.path.join(out, name))
    intro = round(INTRO_END * FPS)
    glow = round(GLOW_PERIOD * FPS)
    for n in range(intro):
        render(intro_frame(n / FPS), f"{out}/intro-{n:03d}.png")
    render(intro_frame(INTRO_END), f"{out}/logo.png")
    for n in range(glow):
        render(glow_frame(n / FPS), f"{out}/glow-{n:03d}.png")
    print(f"{intro} intro + {glow} glow frames, {WIDTH}x{HEIGHT}, in {out}")


if __name__ == "__main__":
    sys.exit(main())
