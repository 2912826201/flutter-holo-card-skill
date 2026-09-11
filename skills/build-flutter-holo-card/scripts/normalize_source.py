#!/usr/bin/env python3
"""Normalize a card image to one uncropped working canvas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--width", type=int, default=1000)
    args = parser.parse_args()

    if args.width < 256:
        raise ValueError("Working width must be at least 256 pixels")
    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    height = round(source.height * args.width / source.width)
    normalized = source.resize((args.width, height), Image.Resampling.LANCZOS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    normalized.save(args.output)
    print(
        json.dumps(
            {
                "source_canvas": list(source.size),
                "working_canvas": list(normalized.size),
                "cropped": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
