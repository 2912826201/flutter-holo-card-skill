#!/usr/bin/env python3
"""Build the source-faithful combined foreground from one reviewed alpha mask."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps


def resize_full_canvas(
    image: Image.Image, size: tuple[int, int], label: str
) -> Image.Image:
    expected_aspect = size[0] / size[1]
    actual_aspect = image.width / image.height
    if abs(actual_aspect / expected_aspect - 1) > 0.01:
        raise ValueError(f"{label} aspect ratio differs from the source canvas")
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS)


def composite_preview(layer: Image.Image, value: int) -> Image.Image:
    base = Image.new("RGBA", layer.size, (value, value, value, 255))
    return Image.alpha_composite(base, layer).convert("RGB")


def save_edge_overlay(source: Image.Image, alpha: Image.Image, path: Path) -> None:
    minimum = alpha.filter(ImageFilter.MinFilter(3))
    maximum = alpha.filter(ImageFilter.MaxFilter(3))
    edge = ImageChops.subtract(maximum, minimum)
    red = Image.new("RGBA", source.size, (255, 24, 24, 0))
    red.putalpha(edge.point(lambda value: round(value * 0.92)))
    Image.alpha_composite(source.convert("RGBA"), red).convert("RGB").save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--alpha-mask", required=True, type=Path)
    parser.add_argument("--output-foreground", required=True, type=Path)
    parser.add_argument("--output-mask", type=Path)
    parser.add_argument("--output-black-preview", type=Path)
    parser.add_argument("--output-white-preview", type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--output-report", type=Path)
    args = parser.parse_args()

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    mask_image = ImageOps.exif_transpose(Image.open(args.alpha_mask))
    if mask_image.mode not in ("1", "L"):
        raise ValueError("Foreground alpha mask must use grayscale L or 1 mode")
    foreground_alpha = resize_full_canvas(
        mask_image.convert("L"), source.size, "Foreground alpha mask"
    )
    foreground_alpha = ImageChops.multiply(
        foreground_alpha, source.getchannel("A")
    )

    alpha_pixels = np.asarray(foreground_alpha, dtype=np.uint8)
    strong_pixels = alpha_pixels >= 128
    opaque_pixels = alpha_pixels >= 250
    transition_pixels = np.logical_and(alpha_pixels > 4, alpha_pixels < 250)
    coverage = float(strong_pixels.mean())
    opaque_coverage = float(opaque_pixels.mean())
    transition_coverage = float(transition_pixels.mean())

    errors: list[str] = []
    warnings: list[str] = []
    if coverage <= 0.001:
        errors.append("Foreground alpha is empty")
    if coverage >= 0.999:
        errors.append("Foreground contains no transparent scenery region")
    if opaque_coverage <= 0.001:
        errors.append("Foreground contains no opaque source-owned element")
    if transition_coverage >= 0.08:
        warnings.append(
            "Foreground has unusually broad partial alpha; inspect for a gray matte or guessed translucency"
        )

    foreground = source.copy()
    foreground.putalpha(foreground_alpha)

    args.output_foreground.parent.mkdir(parents=True, exist_ok=True)
    foreground.save(args.output_foreground)
    if args.output_mask:
        args.output_mask.parent.mkdir(parents=True, exist_ok=True)
        foreground_alpha.save(args.output_mask)
    if args.output_black_preview:
        args.output_black_preview.parent.mkdir(parents=True, exist_ok=True)
        composite_preview(foreground, 20).save(args.output_black_preview)
    if args.output_white_preview:
        args.output_white_preview.parent.mkdir(parents=True, exist_ok=True)
        composite_preview(foreground, 255).save(args.output_white_preview)
    if args.output_overlay:
        args.output_overlay.parent.mkdir(parents=True, exist_ok=True)
        save_edge_overlay(source, foreground_alpha, args.output_overlay)

    report = {
        "ok": not errors,
        "canvas": list(source.size),
        "foreground_coverage": round(coverage, 6),
        "opaque_coverage": round(opaque_coverage, 6),
        "partial_alpha_coverage": round(transition_coverage, 6),
        "source_rgb_preserved": (
            source.convert("RGB").tobytes() == foreground.convert("RGB").tobytes()
        ),
        "errors": errors,
        "warnings": warnings,
        "required_visual_review": [
            "Inspect black and white previews: retain every character, foreground object/effect, glyph, panel, credit, inset, logo, and decorative frame.",
            "Reject independently moving scenery, missing enclosed gaps, gray matte, jagged edges, and scenery islands.",
            "Confirm the red edge overlay stays registered to the source and that no source-visible foreground RGB changed.",
        ],
    }
    rendered = json.dumps(report, indent=2)
    if args.output_report:
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
