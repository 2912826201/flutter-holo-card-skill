#!/usr/bin/env python3
"""Normalize white sketch line art for the complete combined foreground."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


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


def smoothstep(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--lineart", required=True, type=Path)
    parser.add_argument("--output-structure", required=True, type=Path)
    parser.add_argument("--output-transparent", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--black-level", type=int, default=32)
    parser.add_argument("--full-line-level", type=int, default=220)
    parser.add_argument("--maximum-line-ratio", type=float, default=0.48)
    args = parser.parse_args()

    if not 0 <= args.black_level < args.full_line_level <= 255:
        raise ValueError(
            "Black and full-line levels must satisfy 0 <= black < full <= 255"
        )
    if not 0.05 <= args.maximum_line_ratio <= 0.9:
        raise ValueError("Maximum line ratio must be between 0.05 and 0.9")

    reference = ImageOps.exif_transpose(Image.open(args.reference)).convert("RGBA")
    generated = ImageOps.exif_transpose(Image.open(args.lineart)).convert("RGBA")
    original_canvas = generated.size
    generated = resize_full_canvas(generated, reference.size, "Generated line art")

    pixels = np.asarray(generated, dtype=np.uint8)
    luminance = np.asarray(generated.convert("L"), dtype=np.float32)
    generated_alpha = pixels[..., 3].astype(np.float32) / 255.0
    transparent_fraction = float((pixels[..., 3] <= 4).mean())
    has_real_transparency = transparent_fraction >= 0.001

    if has_real_transparency:
        raw_coverage = generated_alpha * np.clip(luminance / 224.0, 0.0, 1.0)
        input_mode = "transparent_white_lines"
    else:
        span = args.full_line_level - args.black_level
        raw_coverage = smoothstep((luminance - args.black_level) / span)
        input_mode = "white_lines_on_black"

    owner_alpha = (
        np.asarray(reference.getchannel("A"), dtype=np.float32) / 255.0
    )
    owner_pixels = owner_alpha >= 0.5
    outside_owner = owner_alpha <= (4.0 / 255.0)
    spill_pixels = np.logical_and(raw_coverage >= 0.02, outside_owner)
    spill_coverage = float(spill_pixels.mean())
    outside_bright_ratio = (
        float((luminance[outside_owner] > args.black_level).mean())
        if outside_owner.any()
        else 0.0
    )

    coverage = raw_coverage * owner_alpha
    structure_pixels = np.rint(np.clip(coverage, 0.0, 1.0) * 255.0).astype(
        np.uint8
    )
    strong_pixels = structure_pixels >= 128
    line_coverage = float(strong_pixels.mean())
    owner_coverage = float(owner_pixels.mean())
    line_ratio = (
        float(strong_pixels[owner_pixels].mean()) if owner_pixels.any() else 0.0
    )

    errors: list[str] = []
    warnings: list[str] = []
    if owner_coverage <= 0.001:
        errors.append("Foreground reference alpha is empty")
    if line_coverage <= 0.0001:
        errors.append("Generated sketch line art is empty")
    if spill_coverage > 0.0005:
        errors.append("Sketch line signal spills outside the foreground owner")
    if not has_real_transparency and outside_bright_ratio > 0.005:
        errors.append(
            "Opaque line art must use a uniform solid-black matte; bright or checkerboard matte detected"
        )
    if line_ratio >= args.maximum_line_ratio:
        warnings.append(
            "Sketch lines cover much of the foreground; inspect for white fills, shading, or retained matte"
        )

    args.output_structure.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(structure_pixels, mode="L").save(args.output_structure)
    if args.output_transparent:
        args.output_transparent.parent.mkdir(parents=True, exist_ok=True)
        white = np.full_like(structure_pixels, 255)
        transparent = np.stack((white, white, white, structure_pixels), axis=2)
        Image.fromarray(transparent, mode="RGBA").save(args.output_transparent)

    report = {
        "ok": not errors,
        "reference_canvas": list(reference.size),
        "generated_canvas": list(original_canvas),
        "resized_to_reference": original_canvas != reference.size,
        "input_mode": input_mode,
        "source_had_real_transparency": has_real_transparency,
        "foreground_owner_coverage": round(owner_coverage, 6),
        "strong_line_coverage": round(line_coverage, 6),
        "strong_line_ratio_within_foreground": round(line_ratio, 6),
        "signal_spill_coverage": round(spill_coverage, 6),
        "opaque_outside_bright_ratio": round(outside_bright_ratio, 6),
        "errors": errors,
        "warnings": warnings,
        "required_visual_review": [
            "Confirm white sketch contours cover every foreground category: characters, objects, effects, typography, symbols, panels, credits, insets, logos, and decorative frame.",
            "Reject scenery edges, filled glyph or panel regions, shading, hatching, texture strokes, invented lines, and matte residue.",
            "Confirm the full canvas and every local contour remain registered; regenerate a shifted result instead of warping it.",
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
