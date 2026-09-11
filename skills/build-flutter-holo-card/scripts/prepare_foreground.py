#!/usr/bin/env python3
"""Build an original-pixel foreground from an AI chroma selection plate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
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
        raise ValueError(f"{label} aspect ratio differs from the source canvas")
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS)


def smoothstep(value: np.ndarray, lower: float, upper: float) -> np.ndarray:
    normalized = np.clip((value - lower) / (upper - lower), 0.0, 1.0)
    return normalized * normalized * (3.0 - 2.0 * normalized)


def extract_green_matte(selection: Image.Image) -> Image.Image:
    rgb = np.asarray(selection.convert("RGB"), dtype=np.float32)
    red = rgb[..., 0]
    green = rgb[..., 1]
    blue = rgb[..., 2]
    dominance = green - np.maximum(red, blue)

    # 选择板的绿色只表达“场景应透明”。双门限同时约束亮度与色相优势，
    # 可避免把人物的自然绿色眼睛、阴影或低饱和印刷色误当成底色。
    dominance_weight = smoothstep(dominance, 24.0, 72.0)
    brightness_weight = smoothstep(green, 118.0, 210.0)
    matte = dominance_weight * brightness_weight
    matte_u8 = np.rint(matte * 255.0).astype(np.uint8)
    return Image.fromarray(matte_u8, mode="L")


def composite_preview(foreground: Image.Image, value: int) -> Image.Image:
    base = Image.new("RGBA", foreground.size, (value, value, value, 255))
    return Image.alpha_composite(base, foreground).convert("RGB")


def save_edge_overlay(source: Image.Image, foreground_alpha: Image.Image, path: Path) -> None:
    minimum = foreground_alpha.filter(ImageFilter.MinFilter(3))
    maximum = foreground_alpha.filter(ImageFilter.MaxFilter(3))
    edge = ImageChops.subtract(maximum, minimum)
    base = source.convert("RGBA")
    red = Image.new("RGBA", source.size, (255, 24, 24, 0))
    red.putalpha(edge.point(lambda value: round(value * 0.92)))
    Image.alpha_composite(base, red).convert("RGB").save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--output-foreground", required=True, type=Path)
    parser.add_argument("--output-mask", type=Path)
    parser.add_argument("--output-black-preview", type=Path)
    parser.add_argument("--output-white-preview", type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--forward-affine", type=parse_affine)
    parser.add_argument("--feather-radius", type=float, default=0.45)
    args = parser.parse_args()

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    selection = ImageOps.exif_transpose(Image.open(args.selection)).convert("RGB")
    selection = resize_full_canvas(selection, source.size, "Selection")

    matte = extract_green_matte(selection)
    if args.forward_affine:
        matte = matte.transform(
            source.size,
            Image.Transform.AFFINE,
            inverse_affine(args.forward_affine),
            resample=Image.Resampling.BICUBIC,
            fillcolor=0,
        )

    foreground_alpha = ImageOps.invert(matte)
    if args.feather_radius > 0:
        scale = source.width / 1000.0
        foreground_alpha = foreground_alpha.filter(
            ImageFilter.GaussianBlur(max(0.05, args.feather_radius * scale))
        )
    foreground_alpha = ImageChops.multiply(foreground_alpha, source.getchannel("A"))

    foreground = source.copy()
    foreground.putalpha(foreground_alpha)

    strong_foreground = np.asarray(foreground_alpha, dtype=np.uint8) >= 128
    foreground_coverage = float(strong_foreground.mean())
    matte_coverage = 1.0 - foreground_coverage
    errors: list[str] = []
    if matte_coverage < 0.03:
        errors.append("Selection contains too little chroma scenery matte")
    if matte_coverage > 0.92:
        errors.append("Selection removes too much of the card")
    if foreground_alpha.getextrema() == (255, 255):
        errors.append("Foreground contains no transparent scenery")

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

    source_rgb = np.asarray(source, dtype=np.uint8)[..., :3]
    output_rgb = np.asarray(foreground, dtype=np.uint8)[..., :3]
    report = {
        "ok": not errors,
        "canvas": list(source.size),
        "foreground_coverage": round(foreground_coverage, 6),
        "scenery_matte_coverage": round(matte_coverage, 6),
        "source_rgb_preserved": bool(np.array_equal(source_rgb, output_rgb)),
        "affine_applied": args.forward_affine is not None,
        "errors": errors,
        "required_visual_review": [
            "Inspect black and white previews for missing character, text, panels, symbols, credits, or frame pixels.",
            "Inspect the red edge overlay for local silhouette drift and retained scenery islands.",
            "Reject local anatomy changes; use affine only for uniform full-canvas framing drift.",
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
