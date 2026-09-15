#!/usr/bin/env python3
"""Prepare foreground sketch-core and packed two-scale bloom maps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps


def resize_full_canvas(
    image: Image.Image, size: tuple[int, int], label: str
) -> Image.Image:
    expected_aspect = size[0] / size[1]
    actual_aspect = image.width / image.height
    if abs(actual_aspect / expected_aspect - 1) > 0.01:
        raise ValueError(f"{label} aspect ratio differs from the foreground canvas")
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS)


def normalize_structure(structure: Image.Image) -> Image.Image:
    lut = [
        round(max(0.0, min(1.0, (value - 24) / 207)) * 255)
        for value in range(256)
    ]
    return structure.point(lut)


def save_overlay(foreground: Image.Image, core: Image.Image, output: Path) -> None:
    neutral = Image.new("RGBA", foreground.size, (28, 30, 36, 255))
    composite = Image.alpha_composite(neutral, foreground)
    white = Image.new("RGBA", foreground.size, (255, 255, 255, 0))
    white.putalpha(core.point(lambda value: round(value * 0.92)))
    Image.alpha_composite(composite, white).convert("RGB").save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--foreground", required=True, type=Path)
    parser.add_argument("--structure", required=True, type=Path)
    parser.add_argument("--output-contour", required=True, type=Path)
    parser.add_argument("--output-bloom", required=True, type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--near-radius", type=float, default=7.0)
    parser.add_argument("--wide-radius", type=float, default=20.0)
    args = parser.parse_args()

    if args.near_radius <= 0:
        raise ValueError("Near bloom radius must be positive")
    if args.wide_radius <= args.near_radius:
        raise ValueError("Wide bloom radius must be greater than near radius")

    foreground = ImageOps.exif_transpose(Image.open(args.foreground)).convert("RGBA")
    structure = ImageOps.exif_transpose(Image.open(args.structure)).convert("L")
    structure = resize_full_canvas(structure, foreground.size, "Structure")

    core = normalize_structure(structure)
    core = ImageChops.multiply(core, foreground.getchannel("A"))
    if not core.getbbox():
        raise ValueError("Prepared structure is empty")

    args.output_contour.parent.mkdir(parents=True, exist_ok=True)
    args.output_bloom.parent.mkdir(parents=True, exist_ok=True)
    opaque = Image.new("L", foreground.size, 255)
    zero = Image.new("L", foreground.size, 0)
    Image.merge("RGBA", (core, core, core, opaque)).save(args.output_contour)

    scale = foreground.width / 1000.0
    near = core.filter(ImageFilter.GaussianBlur(args.near_radius * scale))
    wide = core.filter(ImageFilter.GaussianBlur(args.wide_radius * scale))
    Image.merge("RGBA", (near, wide, zero, opaque)).save(args.output_bloom)

    if args.output_overlay:
        args.output_overlay.parent.mkdir(parents=True, exist_ok=True)
        save_overlay(foreground, core, args.output_overlay)

    histogram = core.histogram()
    strong = sum(histogram[128:]) / (foreground.width * foreground.height)
    print(
        json.dumps(
            {
                "ok": True,
                "canvas": list(foreground.size),
                "strong_line_coverage": round(strong, 6),
                "near_radius_at_1000px": args.near_radius,
                "wide_radius_at_1000px": args.wide_radius,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
