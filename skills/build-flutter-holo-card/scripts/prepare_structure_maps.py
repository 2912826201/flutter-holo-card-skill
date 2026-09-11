#!/usr/bin/env python3
"""Prepare aligned Flutter contour and two-scale bloom maps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps


def parse_affine(value: str) -> tuple[float, float, float, float, float, float]:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 6:
        raise argparse.ArgumentTypeError("Expected six comma-separated affine values")
    a, b, c, d, e, f = parts
    if abs(a * e - b * d) < 1e-9:
        raise argparse.ArgumentTypeError("Affine transform must be invertible")
    return a, b, c, d, e, f


def inverse_affine(
    matrix: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    a, b, c, d, e, f = matrix
    determinant = a * e - b * d
    inverse_a = e / determinant
    inverse_b = -b / determinant
    inverse_d = -d / determinant
    inverse_e = a / determinant
    inverse_c = -(inverse_a * c + inverse_b * f)
    inverse_f = -(inverse_d * c + inverse_e * f)
    return inverse_a, inverse_b, inverse_c, inverse_d, inverse_e, inverse_f


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
    red = Image.new("RGBA", foreground.size, (255, 24, 24, 0))
    red.putalpha(core.point(lambda value: round(value * 0.9)))
    Image.alpha_composite(composite, red).convert("RGB").save(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--foreground", required=True, type=Path)
    parser.add_argument("--structure", type=Path)
    parser.add_argument("--disable-contour", action="store_true")
    parser.add_argument("--output-contour", required=True, type=Path)
    parser.add_argument("--output-bloom", required=True, type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--occlusion-mask", type=Path)
    parser.add_argument("--forward-affine", type=parse_affine)
    parser.add_argument("--near-radius", type=float, default=7.0)
    parser.add_argument("--wide-radius", type=float, default=20.0)
    args = parser.parse_args()

    if args.disable_contour and args.structure:
        raise ValueError("Do not provide --structure with --disable-contour")
    if not args.disable_contour and not args.structure:
        raise ValueError("Provide --structure or use --disable-contour")
    if args.disable_contour and args.forward_affine:
        raise ValueError("Do not provide --forward-affine with --disable-contour")

    foreground = ImageOps.exif_transpose(Image.open(args.foreground)).convert("RGBA")
    canvas = foreground.size
    if args.disable_contour:
        core = Image.new("L", canvas, 0)
    else:
        structure = ImageOps.exif_transpose(Image.open(args.structure)).convert("L")
        structure = resize_full_canvas(structure, canvas, "Structure")

        if args.forward_affine:
            structure = structure.transform(
                canvas,
                Image.Transform.AFFINE,
                inverse_affine(args.forward_affine),
                resample=Image.Resampling.BICUBIC,
                fillcolor=0,
            )

        core = normalize_structure(structure)
        core = ImageChops.multiply(core, foreground.getchannel("A"))

        if args.occlusion_mask:
            occlusion = ImageOps.exif_transpose(Image.open(args.occlusion_mask)).convert(
                "L"
            )
            occlusion = resize_full_canvas(occlusion, canvas, "Occlusion mask")
            core = ImageChops.multiply(core, ImageOps.invert(occlusion))

        if not core.getbbox():
            raise ValueError("Prepared structure is empty")

    args.output_contour.parent.mkdir(parents=True, exist_ok=True)
    args.output_bloom.parent.mkdir(parents=True, exist_ok=True)
    opaque = Image.new("L", canvas, 255)
    zero = Image.new("L", canvas, 0)
    Image.merge("RGBA", (core, core, core, opaque)).save(args.output_contour)

    scale = foreground.width / 1000.0
    near = core.filter(ImageFilter.GaussianBlur(max(0.1, args.near_radius * scale)))
    wide = core.filter(ImageFilter.GaussianBlur(max(0.1, args.wide_radius * scale)))
    Image.merge("RGBA", (near, wide, zero, opaque)).save(args.output_bloom)

    if args.output_overlay:
        args.output_overlay.parent.mkdir(parents=True, exist_ok=True)
        save_overlay(foreground, core, args.output_overlay)

    histogram = core.histogram()
    strong = sum(histogram[128:]) / (foreground.width * foreground.height)
    print(
        json.dumps(
            {
                "canvas": list(canvas),
                "contour_enabled": not args.disable_contour,
                "strong_line_coverage": round(strong, 6),
                "affine_applied": (
                    not args.disable_contour and args.forward_affine is not None
                ),
                "occlusion_applied": (
                    not args.disable_contour and args.occlusion_mask is not None
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
