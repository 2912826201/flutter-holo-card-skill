#!/usr/bin/env python3
"""Check machine-verifiable parts of the Flutter holo-card asset contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageOps, ImageStat


def alpha(image: Image.Image) -> Image.Image:
    return (
        image.getchannel("A")
        if "A" in image.getbands()
        else Image.new("L", image.size, 255)
    )


def coverage(mask: Image.Image, threshold: int = 128) -> float:
    histogram = mask.convert("L").histogram()
    return sum(histogram[threshold:]) / (mask.width * mask.height)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", required=True, type=Path)
    parser.add_argument("--foreground", required=True, type=Path)
    parser.add_argument("--contour", required=True, type=Path)
    parser.add_argument("--bloom", required=True, type=Path)
    parser.add_argument("--occlusion-mask", type=Path)
    args = parser.parse_args()

    background = ImageOps.exif_transpose(Image.open(args.background)).convert("RGBA")
    foreground = ImageOps.exif_transpose(Image.open(args.foreground)).convert("RGBA")
    contour = ImageOps.exif_transpose(Image.open(args.contour)).convert("RGBA")
    bloom = ImageOps.exif_transpose(Image.open(args.bloom)).convert("RGBA")
    images = {
        "background": background,
        "foreground": foreground,
        "contour": contour,
        "bloom": bloom,
    }

    errors: list[str] = []
    warnings: list[str] = []
    sizes = {name: image.size for name, image in images.items()}
    if len(set(sizes.values())) != 1:
        errors.append(f"Canvas mismatch: {sizes}")

    background_alpha = alpha(background)
    background_coverage = coverage(background_alpha)
    if background_coverage < 0.9:
        errors.append(
            "Background alpha leaves too much of the card empty; only exterior corners may be transparent"
        )

    foreground_coverage = coverage(alpha(foreground))
    if foreground_coverage <= 0.001:
        errors.append("Foreground alpha is empty")
    elif foreground_coverage >= 0.999:
        errors.append("Foreground has no transparent scenery region")

    red, green, blue, contour_alpha = contour.split()
    if ImageChops.difference(red, green).getbbox() or ImageChops.difference(
        red, blue
    ).getbbox():
        errors.append("Contour must be grayscale RGB, not a packed colored map")
    if contour_alpha.getextrema() != (255, 255):
        errors.append("Contour canvas must be opaque")
    line_coverage = coverage(red)
    if line_coverage <= 0.0001:
        errors.append("Contour is empty")
    elif line_coverage >= 0.2:
        errors.append("Contour coverage is too dense for selected semantic lines")

    _, _, bloom_blue, bloom_alpha = bloom.split()
    if ImageStat.Stat(bloom_blue).extrema[0][1] > 1:
        errors.append("Bloom B channel must remain zero")
    if bloom_alpha.getextrema() != (255, 255):
        errors.append("Bloom canvas must be opaque")

    if args.occlusion_mask:
        occlusion = ImageOps.exif_transpose(Image.open(args.occlusion_mask)).convert("L")
        if occlusion.size != contour.size:
            errors.append("Occlusion mask canvas differs from contour")
        else:
            spill = ImageChops.multiply(red, occlusion)
            if spill.getextrema()[1] > 4:
                errors.append("Contour spills into the declared occlusion mask")

    warnings.extend(
        [
            "Visually confirm that the background contains no subject, text, or frame residue.",
            "Visually confirm original foreground RGB and lettering over black and white.",
            "Inspect the red contour overlay for eyes, hands, silhouette, text, and frame alignment.",
        ]
    )
    report = {
        "ok": not errors,
        "canvas": list(foreground.size),
        "background_coverage": round(background_coverage, 6),
        "foreground_coverage": round(foreground_coverage, 6),
        "strong_line_coverage": round(line_coverage, 6),
        "errors": errors,
        "required_visual_review": warnings,
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
