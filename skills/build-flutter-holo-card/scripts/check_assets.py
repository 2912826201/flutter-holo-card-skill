#!/usr/bin/env python3
"""Check machine-verifiable parts of the Flutter holo-card asset contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
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
    parser.add_argument("--source", type=Path)
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

    source_rgb_preserved = None
    opaque_source_rgb_preserved = None
    if args.source:
        source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
        if source.size != foreground.size:
            errors.append("Source canvas differs from foreground")
            source_rgb_preserved = False
        else:
            source_pixels = np.asarray(source, dtype=np.uint8)
            foreground_pixels = np.asarray(foreground, dtype=np.uint8)
            rgb_mismatch = np.any(
                source_pixels[..., :3] != foreground_pixels[..., :3], axis=2
            )
            source_rgb_preserved = not bool(rgb_mismatch.any())
            opaque_pixels = foreground_pixels[..., 3] >= 250
            opaque_source_rgb_preserved = not bool(
                np.logical_and(rgb_mismatch, opaque_pixels).any()
            )
            if not opaque_source_rgb_preserved:
                errors.append(
                    "Opaque foreground RGB differs from the normalized source"
                )
            elif not source_rgb_preserved:
                warnings.append(
                    "Translucent foreground RGB differs from source; confirm it is intentional material-color decontamination"
                )

    red, green, blue, contour_alpha = contour.split()
    if ImageChops.difference(red, green).getbbox() or ImageChops.difference(
        red, blue
    ).getbbox():
        errors.append("Contour must be grayscale RGB, not a packed colored map")
    if contour_alpha.getextrema() != (255, 255):
        errors.append("Contour canvas must be opaque")
    line_coverage = coverage(red)
    contour_enabled = red.getextrema()[1] > 1
    if contour_enabled and line_coverage <= 0.0001:
        errors.append("Contour signal is present but effectively empty")
    elif line_coverage >= 0.35:
        errors.append("Contour coverage is too dense for a foreground highlight map")

    bloom_red, bloom_green, bloom_blue, bloom_alpha = bloom.split()
    bloom_enabled = max(
        bloom_red.getextrema()[1],
        bloom_green.getextrema()[1],
    ) > 1
    if contour_enabled != bloom_enabled:
        errors.append("Contour and bloom enabled states do not match")
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
        ]
    )
    if contour_enabled:
        warnings.append(
            "Inspect the red contour overlay for full-foreground line registration."
        )
    else:
        warnings.append(
            "Contour and bloom are neutral black maps; line emission is intentionally disabled."
        )
    report = {
        "ok": not errors,
        "canvas": list(foreground.size),
        "background_coverage": round(background_coverage, 6),
        "foreground_coverage": round(foreground_coverage, 6),
        "source_rgb_preserved": source_rgb_preserved,
        "opaque_source_rgb_preserved": opaque_source_rgb_preserved,
        "contour_enabled": contour_enabled,
        "strong_line_coverage": round(line_coverage, 6),
        "errors": errors,
        "required_visual_review": warnings,
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
