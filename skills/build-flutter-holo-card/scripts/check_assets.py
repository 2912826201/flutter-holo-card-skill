#!/usr/bin/env python3
"""Check machine-verifiable parts of the two-layer holo-card asset contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageOps, ImageStat


def alpha(image: Image.Image) -> Image.Image:
    return image.getchannel("A")


def coverage(mask: Image.Image, threshold: int = 128) -> float:
    histogram = mask.convert("L").histogram()
    return sum(histogram[threshold:]) / (mask.width * mask.height)


def emit(report: dict[str, object], output: Path | None) -> int:
    rendered = json.dumps(report, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["ok"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--background", required=True, type=Path)
    parser.add_argument("--foreground", required=True, type=Path)
    parser.add_argument("--contour", required=True, type=Path)
    parser.add_argument("--bloom", required=True, type=Path)
    parser.add_argument("--output-report", type=Path)
    args = parser.parse_args()

    images = {
        "source": ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA"),
        "background": ImageOps.exif_transpose(
            Image.open(args.background)
        ).convert("RGBA"),
        "foreground": ImageOps.exif_transpose(
            Image.open(args.foreground)
        ).convert("RGBA"),
        "contour": ImageOps.exif_transpose(Image.open(args.contour)).convert(
            "RGBA"
        ),
        "bloom": ImageOps.exif_transpose(Image.open(args.bloom)).convert("RGBA"),
    }
    sizes = {name: list(image.size) for name, image in images.items()}
    if len({tuple(size) for size in sizes.values()}) != 1:
        return emit(
            {
                "ok": False,
                "canvas": sizes["source"],
                "errors": [f"Canvas mismatch: {sizes}"],
                "warnings": [],
                "required_visual_review": [],
            },
            args.output_report,
        )

    source = images["source"]
    background = images["background"]
    foreground = images["foreground"]
    contour = images["contour"]
    bloom = images["bloom"]
    errors: list[str] = []
    warnings: list[str] = []

    source_alpha = alpha(source)
    source_alpha_pixels = np.asarray(source_alpha, dtype=np.uint8)
    corner_alphas = [
        source_alpha.getpixel((0, 0)),
        source_alpha.getpixel((source.width - 1, 0)),
        source_alpha.getpixel((0, source.height - 1)),
        source_alpha.getpixel((source.width - 1, source.height - 1)),
    ]
    source_coverage = coverage(source_alpha)
    source_card_mask_valid = bool(
        source_alpha.getextrema()[0] <= 4
        and source_alpha.getextrema()[1] >= 250
        and all(value <= 4 for value in corner_alphas)
        and source_coverage > 0.8
    )
    if not source_card_mask_valid:
        errors.append(
            "Source Alpha must contain an opaque card interior, transparent corners, and useful card-shape coverage"
        )

    background_alpha = alpha(background)
    background_coverage = coverage(background_alpha, threshold=250)
    if background_alpha.getextrema()[0] < 250:
        errors.append("Background must be opaque across the complete full-bleed canvas")

    foreground_alpha = alpha(foreground)
    foreground_alpha_pixels = np.asarray(foreground_alpha, dtype=np.uint8)
    foreground_coverage = coverage(foreground_alpha)
    if foreground_coverage <= 0.001:
        errors.append("Foreground alpha is empty")
    elif foreground_coverage >= 0.999:
        errors.append("Foreground has no transparent scenery region")

    spill_pixels = np.logical_and(
        foreground_alpha_pixels > 4, source_alpha_pixels <= 4
    )
    foreground_spill_coverage = float(spill_pixels.mean())
    if spill_pixels.any():
        errors.append("Foreground Alpha spills outside the source card shape")

    source_rgb = np.asarray(source, dtype=np.uint8)[..., :3]
    foreground_rgb = np.asarray(foreground, dtype=np.uint8)[..., :3]
    source_rgb_preserved = bool(np.array_equal(source_rgb, foreground_rgb))
    if not source_rgb_preserved:
        errors.append("Foreground RGB differs from the normalized source")

    red, green, blue, contour_alpha = contour.split()
    contour_grayscale = not (
        ImageChops.difference(red, green).getbbox()
        or ImageChops.difference(red, blue).getbbox()
    )
    if not contour_grayscale:
        errors.append("Contour must be grayscale RGB")
    if contour_alpha.getextrema() != (255, 255):
        errors.append("Contour canvas must be opaque")
    line_coverage = coverage(red)
    contour_enabled = red.getextrema()[1] > 1
    if not contour_enabled or line_coverage <= 0.0001:
        errors.append("Contour signal is empty")
    elif line_coverage >= 0.18:
        warnings.append(
            "Contour is unusually dense; inspect for filled regions, shading, or texture"
        )
    contour_spill = np.logical_and(
        np.asarray(red, dtype=np.uint8) > 4, foreground_alpha_pixels <= 4
    )
    contour_spill_coverage = float(contour_spill.mean())
    if contour_spill.any():
        errors.append("Contour spills outside its foreground owner")

    bloom_red, bloom_green, bloom_blue, bloom_alpha = bloom.split()
    bloom_enabled = max(
        bloom_red.getextrema()[1], bloom_green.getextrema()[1]
    ) > 1
    if not bloom_enabled:
        errors.append("Bloom signal is empty")
    if ImageStat.Stat(bloom_blue).extrema[0][1] > 1:
        errors.append("Bloom B channel must remain zero")
    if bloom_alpha.getextrema() != (255, 255):
        errors.append("Bloom canvas must be opaque")

    review_items = [
        "Compare background at full size and confirm it contains no character, foreground object/effect, typography, panel, credit, logo, inset, or frame residue.",
        "Inspect foreground over black and white and confirm it contains every non-background element, preserves source overlap order, and contains no moving scenery island.",
        "Compare background + foreground at neutral UV with source.png before enabling foil or contour light.",
        "Inspect the white alignment overlay and confirm sketch contours cover all foreground categories while excluding scenery, fills, shading, hatching, and invented lines.",
        "Tilt at depth -2, 0, and +2 and reject holes, duplication, edge matte, contour drift, illegible text, and clipped positive-depth foreground.",
    ]
    report = {
        "ok": not errors,
        "canvas": list(source.size),
        "source_card_mask_valid": source_card_mask_valid,
        "source_corner_alphas": corner_alphas,
        "source_card_coverage": round(source_coverage, 6),
        "background_full_bleed_coverage": round(background_coverage, 6),
        "foreground_coverage": round(foreground_coverage, 6),
        "foreground_spill_coverage": round(foreground_spill_coverage, 6),
        "source_rgb_preserved": source_rgb_preserved,
        "strong_line_coverage": round(line_coverage, 6),
        "contour_spill_coverage": round(contour_spill_coverage, 6),
        "errors": errors,
        "warnings": warnings,
        "required_visual_review": review_items,
    }
    return emit(report, args.output_report)


if __name__ == "__main__":
    raise SystemExit(main())
