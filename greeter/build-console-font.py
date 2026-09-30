#!/usr/bin/env python3
"""Patch a Terminus PSF2 console font for the tuigreet login screen: box
corners ┌┐└┘ become rounded arcs (tuigreet always draws square ones).

usage: build-console-font.py SRC.psf[.gz] DST.psf.gz   (12x24 fonts only)
"""
import gzip, math, struct, sys

src, dst = sys.argv[1], sys.argv[2]
raw = open(src, "rb").read()
d = bytearray(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
magic, ver, hs, flags, n, cs, h, w = struct.unpack("<8I", d[:32])
assert magic == 0x864AB572 and flags & 1, "need a PSF2 font with a unicode table"
assert (w, h) == (12, 24), "tuned for 12x24 (ter-v24*)"
bpr = (w + 7) // 8

# unicode table: one entry per glyph, terminated by 0xFF
entries = [bytearray(e) for e in d[hs + n * cs:].split(b"\xff")[:n]]
umap = {}
for g, e in enumerate(entries):
    for ch in e.split(b"\xfe")[0].decode():
        umap.setdefault(ch, g)

def get(g):
    o = hs + g * cs
    return [[(d[o + r * bpr + c // 8] >> (7 - c % 8)) & 1 for c in range(w)] for r in range(h)]

def put(g, px):
    o = hs + g * cs
    for r in range(h):
        for cb in range(bpr):
            d[o + r * bpr + cb] = 0
        for c in range(w):
            if px[r][c]:
                d[o + r * bpr + c // 8] |= 0x80 >> (c % 8)

# --- rounded corners, with line position and thickness taken from ─ and │
hz, vt = get(umap["─"]), get(umap["│"])
rows = [r for r in range(h) if any(hz[r])]
cols = [c for c in range(w) if any(vt[r][c] for r in range(h))]
r0, r1, c0, c1 = rows[0], rows[-1], cols[0], cols[-1]
t = r1 - r0 + 1
cy, cx, R = (r0 + r1 + 1) / 2, (c0 + c1 + 1) / 2, w * 0.5

def corner(dx, dy):  # dx=+1: the line leaves to the right; dy=+1: downwards
    ax, ay = cx + dx * R, cy + dy * R
    px = [[0] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            x, y = c + 0.5, r + 0.5
            onh = r0 <= r <= r1 and (x - ax) * dx >= 0
            onv = c0 <= c <= c1 and (y - ay) * dy >= 0
            arc = (x - ax) * dx <= 0 and (y - ay) * dy <= 0 and abs(math.hypot(x - ax, y - ay) - R) < t / 2 + 0.35
            px[r][c] = int(onh or onv or arc)
    return px

for ch, (dx, dy) in {"┌": (1, 1), "┐": (-1, 1), "└": (1, -1), "┘": (-1, -1)}.items():
    put(umap[ch], corner(dx, dy))

out = bytes(d[:hs + n * cs]) + b"".join(bytes(e) + b"\xff" for e in entries)
with gzip.open(dst, "wb") as f:
    f.write(out)
