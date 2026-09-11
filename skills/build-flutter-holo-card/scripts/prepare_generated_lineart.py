#!/usr/bin/env python3
"""Normalize model-generated white line art into registered structure assets."""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--lineart", required=True, type=Path)
    parser.add_argument("--output-structure", required=True, type=Path)
    parser.add_argument("--output-transparent", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--background-cutoff", type=int, default=205)
    parser.add_argument("--full-line-level", type=int, default=245)
    parser.add_argument("--maximum-line-coverage", type=float, default=0.35)
    args = parser.parse_args()

    if not 0 <= args.background_cutoff < args.full_line_level <= 255:
        raise ValueError(
            "Background cutoff and full line level must satisfy 0 <= cutoff < full <= 255"
        )

    reference = ImageOps.exif_transpose(Image.open(args.reference)).convert("RGBA")
    generated = ImageOps.exif_transpose(Image.open(args.lineart)).convert("RGBA")
    original_canvas = generated.size
    generated = resize_full_canvas(generated, reference.size, "Generated line art")
    pixels = np.asarray(generated, dtype=np.uint8)
    luminance = np.asarray(generated.convert("L"), dtype=np.float32)
    alpha = pixels[..., 3].astype(np.float32) / 255.0
    has_real_transparency = bool(np.any(pixels[..., 3] < 250))

    if has_real_transparency:
        # 真实透明输出以 Alpha 为主，并用亮度抑制意外残留的深色内容。
        coverage = alpha * np.clip(luminance / 224.0, 0.0, 1.0)
    else:
        # 部分生图服务会把透明棋盘格烘焙进 RGB。只提取超过棋盘亮度
        # 上限的白线覆盖率，不从原图重新检测或重画任何边缘。
        span = args.full_line_level - args.background_cutoff
        coverage = np.clip(
            (luminance - args.background_cutoff) / span,
            0.0,
            1.0,
        )
        coverage = coverage * coverage * (3.0 - 2.0 * coverage)

    structure_pixels = np.rint(coverage * 255.0).astype(np.uint8)
    line_coverage = float((structure_pixels >= 128).mean())
    errors: list[str] = []
    if line_coverage <= 0.0001:
        errors.append("Generated line art is empty after background removal")
    if line_coverage >= args.maximum_line_coverage:
        errors.append("Generated line art is too dense for a highlight mask")

    args.output_structure.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(structure_pixels, mode="L").save(args.output_structure)
    if args.output_transparent:
        args.output_transparent.parent.mkdir(parents=True, exist_ok=True)
        white = np.full_like(structure_pixels, 255)
        transparent = np.stack(
            (white, white, white, structure_pixels),
            axis=2,
        )
        Image.fromarray(transparent, mode="RGBA").save(args.output_transparent)

    report = {
        "ok": not errors,
        "reference_canvas": list(reference.size),
        "generated_canvas": list(original_canvas),
        "resized_to_reference": original_canvas != reference.size,
        "source_had_real_transparency": has_real_transparency,
        "opaque_background_removed": not has_real_transparency,
        "background_cutoff": args.background_cutoff,
        "full_line_level": args.full_line_level,
        "strong_line_coverage": round(line_coverage, 6),
        "errors": errors,
        "required_visual_review": [
            "Confirm every retained stroke comes from the generated sketch, not its checkerboard backdrop.",
            "Confirm the resized full canvas remains globally registered before affine calibration.",
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
