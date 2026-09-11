#!/usr/bin/env python3
"""Build an original-pixel foreground from a chroma or opacity selection plate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
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


def extract_three_state_alpha(
    selection: Image.Image, translucent_alpha: int
) -> tuple[Image.Image, np.ndarray, float, float, float]:
    rgb = np.asarray(selection.convert("RGB"), dtype=np.uint8)
    luminance = np.asarray(selection.convert("L"), dtype=np.uint8)

    # 三态板只表达景深归属：黑色是独立背景，中灰是透光材质，白色是
    # 不透明前景。先量化再统一羽化，避免模型输出的轻微灰阶波动改变材质透明度。
    alpha = np.zeros(luminance.shape, dtype=np.uint8)
    translucent = np.logical_and(luminance >= 64, luminance <= 192)
    opaque = luminance > 192
    alpha[translucent] = translucent_alpha
    alpha[opaque] = 255

    channel_spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(
        np.int16
    )
    neutral_coverage = float((channel_spread <= 18).mean())
    translucent_coverage = float(translucent.mean())
    opaque_coverage = float(opaque.mean())
    return (
        Image.fromarray(alpha, mode="L"),
        translucent,
        neutral_coverage,
        translucent_coverage,
        opaque_coverage,
    )


def decontaminate_translucent_rgb(
    source_rgb: np.ndarray,
    translucent: np.ndarray,
    radius: float,
) -> np.ndarray:
    if radius <= 0 or not translucent.any():
        return source_rgb.copy()

    weights = translucent.astype(np.float32)
    denominator = cv2.GaussianBlur(weights, (0, 0), sigmaX=radius)
    safe_denominator = np.maximum(denominator, 1e-5)
    result = source_rgb.astype(np.float32).copy()
    for channel in range(3):
        weighted = source_rgb[..., channel].astype(np.float32) * weights
        numerator = cv2.GaussianBlur(weighted, (0, 0), sigmaX=radius)
        tint = numerator / safe_denominator
        result[..., channel][translucent] = tint[translucent]
    return np.rint(np.clip(result, 0.0, 255.0)).astype(np.uint8)


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
    selection_group = parser.add_mutually_exclusive_group(required=True)
    selection_group.add_argument("--selection", type=Path)
    selection_group.add_argument("--opacity-selection", type=Path)
    parser.add_argument("--presence-selection", type=Path)
    parser.add_argument("--output-foreground", required=True, type=Path)
    parser.add_argument("--output-mask", type=Path)
    parser.add_argument("--output-black-preview", type=Path)
    parser.add_argument("--output-white-preview", type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--forward-affine", type=parse_affine)
    parser.add_argument("--feather-radius", type=float, default=0.45)
    parser.add_argument("--translucent-alpha", type=int, default=144)
    parser.add_argument("--material-color-radius", type=float, default=24.0)
    args = parser.parse_args()

    if not 1 <= args.translucent_alpha <= 254:
        raise ValueError("Translucent alpha must be between 1 and 254")
    if not 0 <= args.material_color_radius <= 160:
        raise ValueError("Material color radius must be between 0 and 160")

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    selection_path = args.opacity_selection or args.selection
    selection = ImageOps.exif_transpose(Image.open(selection_path)).convert("RGB")
    selection = resize_full_canvas(selection, source.size, "Selection")
    if args.opacity_selection and not args.presence_selection:
        raise ValueError(
            "Opacity selection requires a chroma --presence-selection"
        )

    neutral_coverage = None
    translucent_coverage = 0.0
    opaque_coverage = 0.0
    translucent_pixels = np.zeros(source.size[::-1], dtype=bool)
    if args.opacity_selection:
        (
            _,
            requested_translucent_pixels,
            neutral_coverage,
            _,
            _,
        ) = extract_three_state_alpha(selection, args.translucent_alpha)
        presence = ImageOps.exif_transpose(
            Image.open(args.presence_selection)
        ).convert("RGB")
        presence = resize_full_canvas(presence, source.size, "Presence selection")
        presence_alpha = ImageOps.invert(extract_green_matte(presence))
        presence_pixels = np.asarray(presence_alpha, dtype=np.uint8)
        translucent_pixels = np.logical_and(
            requested_translucent_pixels, presence_pixels >= 32
        )
        combined_alpha = presence_pixels.copy()
        combined_alpha[translucent_pixels] = np.minimum(
            combined_alpha[translucent_pixels], args.translucent_alpha
        )
        foreground_alpha = Image.fromarray(combined_alpha, mode="L")
        translucent_coverage = float(translucent_pixels.mean())
        opaque_coverage = float(
            np.logical_and(presence_pixels >= 128, ~translucent_pixels).mean()
        )
        selection_mode = "three_state_opacity"
    else:
        matte = extract_green_matte(selection)
        foreground_alpha = ImageOps.invert(matte)
        selection_mode = "chroma"

    if args.forward_affine:
        inverse = inverse_affine(args.forward_affine)
        foreground_alpha = foreground_alpha.transform(
            source.size,
            Image.Transform.AFFINE,
            inverse,
            resample=Image.Resampling.BICUBIC,
            fillcolor=0,
        )
        if args.opacity_selection:
            translucent_mask = Image.fromarray(
                np.where(translucent_pixels, 255, 0).astype(np.uint8), mode="L"
            ).transform(
                source.size,
                Image.Transform.AFFINE,
                inverse,
                resample=Image.Resampling.NEAREST,
                fillcolor=0,
            )
            translucent_pixels = np.asarray(translucent_mask) >= 128

    if args.feather_radius > 0:
        scale = source.width / 1000.0
        foreground_alpha = foreground_alpha.filter(
            ImageFilter.GaussianBlur(max(0.05, args.feather_radius * scale))
        )
    foreground_alpha = ImageChops.multiply(foreground_alpha, source.getchannel("A"))

    source_pixels = np.asarray(source, dtype=np.uint8)
    output_pixels = source_pixels.copy()
    material_rgb_decontaminated = bool(
        args.opacity_selection
        and args.material_color_radius > 0
        and translucent_pixels.any()
    )
    if material_rgb_decontaminated:
        material_radius = args.material_color_radius * (source.width / 1000.0)
        output_pixels[..., :3] = decontaminate_translucent_rgb(
            source_pixels[..., :3], translucent_pixels, material_radius
        )
    foreground = Image.fromarray(output_pixels, mode="RGBA")
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
    if args.opacity_selection:
        if neutral_coverage is not None and neutral_coverage < 0.9:
            errors.append("Opacity selection must use neutral black, gray, and white")
        if translucent_coverage < 0.002:
            errors.append("Opacity selection contains no translucent material")

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

    source_rgb = source_pixels[..., :3]
    output_rgb = np.asarray(foreground, dtype=np.uint8)[..., :3]
    full_rgb_preserved = bool(np.array_equal(source_rgb, output_rgb))
    opaque_pixels = np.asarray(foreground_alpha, dtype=np.uint8) >= 250
    opaque_rgb_preserved = bool(
        np.array_equal(source_rgb[opaque_pixels], output_rgb[opaque_pixels])
    )
    report = {
        "ok": not errors,
        "canvas": list(source.size),
        "foreground_coverage": round(foreground_coverage, 6),
        "scenery_matte_coverage": round(matte_coverage, 6),
        "selection_mode": selection_mode,
        "presence_selection_used": args.presence_selection is not None,
        "translucent_material_coverage": round(translucent_coverage, 6),
        "opaque_selection_coverage": round(opaque_coverage, 6),
        "neutral_selection_coverage": (
            round(neutral_coverage, 6) if neutral_coverage is not None else None
        ),
        "translucent_alpha": (
            args.translucent_alpha if args.opacity_selection else None
        ),
        "source_rgb_preserved": full_rgb_preserved,
        "opaque_source_rgb_preserved": opaque_rgb_preserved,
        "translucent_rgb_decontaminated": material_rgb_decontaminated,
        "material_color_radius_at_1000px": (
            args.material_color_radius if args.opacity_selection else None
        ),
        "affine_applied": args.forward_affine is not None,
        "errors": errors,
        "required_visual_review": [
            "Inspect black and white previews for missing character, text, panels, symbols, credits, or frame pixels.",
            "For a three-state plate, confirm scenery visible through translucent material is black, the material itself is gray, and opaque text or strokes are white.",
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
