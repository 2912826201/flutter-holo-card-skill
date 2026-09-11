#!/usr/bin/env python3
"""Normalize an AI UI plate into a conservative contour-occlusion mask."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


def resize_full_canvas(
    image: Image.Image, size: tuple[int, int], label: str
) -> Image.Image:
    expected_aspect = size[0] / size[1]
    actual_aspect = image.width / image.height
    if abs(actual_aspect / expected_aspect - 1) > 0.01:
        raise ValueError(f"{label} aspect ratio differs from the reference canvas")
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--output-mask", required=True, type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--safety-radius", type=float, default=3.0)
    args = parser.parse_args()

    reference = ImageOps.exif_transpose(Image.open(args.reference)).convert("RGBA")
    selection = ImageOps.exif_transpose(Image.open(args.selection)).convert("L")
    selection = resize_full_canvas(selection, reference.size, "Occlusion selection")
    mask = selection.point(lambda value: 255 if value >= 128 else 0)

    if args.safety_radius > 0:
        scaled_radius = max(1, round(args.safety_radius * reference.width / 1000.0))
        mask = mask.filter(ImageFilter.MaxFilter(scaled_radius * 2 + 1))

    histogram = mask.histogram()
    coverage = sum(histogram[128:]) / (mask.width * mask.height)
    errors: list[str] = []
    if coverage < 0.02:
        errors.append("Occlusion mask is nearly empty")
    if coverage > 0.72:
        errors.append("Occlusion mask hides too much of the card")

    args.output_mask.parent.mkdir(parents=True, exist_ok=True)
    mask.save(args.output_mask)
    if args.output_overlay:
        args.output_overlay.parent.mkdir(parents=True, exist_ok=True)
        red = Image.new("RGBA", reference.size, (255, 20, 20, 0))
        red.putalpha(mask.point(lambda value: round(value * 0.62)))
        Image.alpha_composite(reference, red).convert("RGB").save(args.output_overlay)

    report = {
        "ok": not errors,
        "canvas": list(reference.size),
        "occlusion_coverage": round(coverage, 6),
        "safety_radius_at_1000px": args.safety_radius,
        "errors": errors,
        "required_visual_review": [
            "White must cover every panel, text row, logo, credit, symbol, and frame that may occlude the character.",
            "White must not cover character-only regions away from interface elements.",
        ],
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
