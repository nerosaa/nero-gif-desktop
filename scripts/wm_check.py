#!/usr/bin/env python3
"""Measure whether a GIF carries the bottom-right watermark.

Compares the GIF's first frame with a reference GIF rendered by plain ffmpeg
(same fps/scale/palette, NO drawtext). Prints mean abs diff of the
bottom-right corner; exit 0 if the result matches --expect (wm|clean).

  python scripts/wm_check.py OUT.gif SOURCE.mp4 --width 320 --fps 10 --expect wm
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def corner_diff(a: Path, b: Path) -> float:
    ia = Image.open(a).convert("RGB")
    ib = Image.open(b).convert("RGB")
    w, h = ia.size
    box = (int(w * 0.45), int(h * 0.85), w, h)
    st = ImageStat.Stat(ImageChops.difference(ia.crop(box), ib.crop(box)))
    return sum(st.mean) / 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gif")
    ap.add_argument("source")
    ap.add_argument("--width", type=int, default=320)
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--expect", choices=["wm", "clean"], required=True)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "ref.gif"
        pal = Path(td) / "pal.png"
        vf = f"fps={a.fps},scale={a.width}:-1:flags=lanczos"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", "2", "-i", a.source,
                        "-vf", f"{vf},palettegen=stats_mode=diff", str(pal)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", "2", "-i", a.source, "-i", str(pal),
                        "-lavfi", f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
                        "-loop", "0", str(ref)], check=True)
        d = corner_diff(Path(a.gif), ref)
    got = "wm" if d > 4.0 else "clean"
    print(f"{a.gif}: corner diff vs no-watermark reference = {d:.2f} -> {got} (expected {a.expect})")
    return 0 if got == a.expect else 1


if __name__ == "__main__":
    raise SystemExit(main())
