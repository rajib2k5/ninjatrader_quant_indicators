#!/usr/bin/env python3
"""crop.py - cut one or more regions out of a full-screen NinjaTrader screenshot.

Usage: python crop.py SCREENSHOT.png OUT_DIR NAME:x0,y0,x1,y1 [NAME:x0,y0,x1,y1 ...]
Each NAME becomes OUT_DIR/NAME.png. Coordinates are full-resolution pixels of the screenshot.
A region taller than 1200 px or wider than 1800 px is scaled down proportionally so the README
images stay reasonable; nothing else is altered.
"""
import sys
from pathlib import Path

from PIL import Image

MAX_W, MAX_H = 1800, 1200


def main():
    if len(sys.argv) < 4:
        print(__doc__); sys.exit(2)
    src = Image.open(sys.argv[1]).convert("RGB")
    out_dir = Path(sys.argv[2]); out_dir.mkdir(parents=True, exist_ok=True)
    for spec in sys.argv[3:]:
        name, box = spec.split(":", 1)
        x0, y0, x1, y1 = (int(v) for v in box.split(","))
        img = src.crop((x0, y0, x1, y1))
        w, h = img.size
        scale = min(1.0, MAX_W / w, MAX_H / h)
        if scale < 1.0:
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        p = out_dir / f"{name}.png"
        img.save(p, optimize=True)
        print(f"{p}  {img.size[0]}x{img.size[1]}")


if __name__ == "__main__":
    main()
