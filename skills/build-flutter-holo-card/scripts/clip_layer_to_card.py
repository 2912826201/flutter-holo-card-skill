#!/usr/bin/env python3
"""Intersect an existing movable color layer with source card-shape Alpha."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageOps

from prepare_foreground import resize_full_canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--layer", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    layer = ImageOps.exif_transpose(Image.open(args.layer)).convert("RGBA")
    layer = resize_full_canvas(layer, source.size, "Movable layer")
    before_alpha = np.asarray(layer.getchannel("A"), dtype=np.uint8)
    source_alpha = source.getchannel("A")
    if any(
        source_alpha.getpixel(point) > 4
        for point in (
            (0, 0),
            (source.width - 1, 0),
            (0, source.height - 1),
            (source.width - 1, source.height - 1),
        )
    ):
        raise ValueError("Source does not contain transparent card corners")

    final_alpha = ImageChops.multiply(layer.getchannel("A"), source_alpha)
    final_alpha_pixels = np.asarray(final_alpha, dtype=np.uint8)
    removed = np.logical_and(before_alpha > 4, final_alpha_pixels <= 4)
    layer.putalpha(final_alpha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    layer.save(args.output)
    print(
        json.dumps(
            {
                "canvas": list(source.size),
                "removed_outside_card_coverage": round(float(removed.mean()), 6),
                "rgb_preserved": True,
                "corner_alphas": [
                    final_alpha.getpixel((0, 0)),
                    final_alpha.getpixel((source.width - 1, 0)),
                    final_alpha.getpixel((0, source.height - 1)),
                    final_alpha.getpixel((source.width - 1, source.height - 1)),
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
