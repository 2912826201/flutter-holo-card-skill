#!/usr/bin/env python3
"""Normalize a model-generated continuous character layer and validate its alpha."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps

from prepare_foreground import resize_full_canvas


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
    parser.add_argument("--character", required=True, type=Path)
    parser.add_argument("--alpha-mask", type=Path)
    parser.add_argument(
        "--visible-subject-mask",
        "--visible-subject-selection",
        dest="visible_subject_mask",
        required=True,
        type=Path,
    )
    parser.add_argument("--output-character", required=True, type=Path)
    parser.add_argument("--output-visible-subject-mask", required=True, type=Path)
    parser.add_argument("--output-black-preview", type=Path)
    parser.add_argument("--output-white-preview", type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--feather-radius", type=float, default=0.45)
    args = parser.parse_args()

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    generated = ImageOps.exif_transpose(Image.open(args.character)).convert("RGBA")
    generated = resize_full_canvas(generated, source.size, "Generated character")
    generated_pixels = np.asarray(generated, dtype=np.uint8).copy()
    alpha = generated.getchannel("A")

    if args.alpha_mask:
        mask_image = ImageOps.exif_transpose(Image.open(args.alpha_mask))
        if mask_image.mode not in ("1", "L"):
            raise ValueError("Character alpha mask must use grayscale L or 1 mode")
        selected_alpha = resize_full_canvas(
            mask_image.convert("L"), source.size, "Character alpha mask"
        )
        alpha = ImageChops.multiply(alpha, selected_alpha)
    elif alpha.getextrema() == (255, 255):
        raise ValueError(
            "Opaque generated character requires a reviewed grayscale --alpha-mask"
        )

    if args.feather_radius > 0:
        radius = max(0.05, args.feather_radius * source.width / 1000.0)
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius))
    alpha = ImageChops.multiply(alpha, source.getchannel("A"))

    visible_selection = ImageOps.exif_transpose(
        Image.open(args.visible_subject_mask)
    ).convert("L")
    visible_selection = resize_full_canvas(
        visible_selection, source.size, "Visible subject selection"
    ).point(lambda value: 255 if value >= 128 else 0)
    source_alpha = np.asarray(source.getchannel("A"), dtype=np.uint8)
    visible_pixels = np.logical_and(
        np.asarray(visible_selection, dtype=np.uint8) >= 128,
        source_alpha > 0,
    )
    visible_coverage = float(visible_pixels.mean())
    alpha_pixels = np.asarray(alpha, dtype=np.uint8)
    missing_visible = np.logical_and(visible_pixels, alpha_pixels < 128)
    missing_coverage = float(missing_visible.mean())

    final_alpha_pixels = alpha_pixels.copy()
    final_alpha_pixels[visible_pixels] = 255
    final_alpha = Image.fromarray(final_alpha_pixels, mode="L")
    character = Image.fromarray(generated_pixels, mode="RGBA")
    character.putalpha(final_alpha)

    character_coverage = float((final_alpha_pixels >= 128).mean())
    errors: list[str] = []
    if visible_coverage <= 0.001:
        errors.append("Visible subject selection is empty")
    if missing_visible.any():
        errors.append("Generated character alpha misses source-visible subject pixels")
    if character_coverage <= 0.001:
        errors.append("Generated character alpha is empty")
    if final_alpha.getextrema() == (255, 255):
        errors.append("Generated character has no transparent region")

    args.output_character.parent.mkdir(parents=True, exist_ok=True)
    character.save(args.output_character)
    args.output_visible_subject_mask.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(
        np.where(visible_pixels, 255, 0).astype(np.uint8), mode="L"
    ).save(args.output_visible_subject_mask)
    if args.output_black_preview:
        args.output_black_preview.parent.mkdir(parents=True, exist_ok=True)
        composite_preview(character, 20).save(args.output_black_preview)
    if args.output_white_preview:
        args.output_white_preview.parent.mkdir(parents=True, exist_ok=True)
        composite_preview(character, 255).save(args.output_white_preview)
    if args.output_overlay:
        args.output_overlay.parent.mkdir(parents=True, exist_ok=True)
        save_edge_overlay(source, final_alpha, args.output_overlay)

    report = {
        "ok": not errors,
        "canvas": list(source.size),
        "character_coverage": round(character_coverage, 6),
        "visible_subject_coverage": round(visible_coverage, 6),
        "visible_subject_missing_coverage": round(missing_coverage, 6),
        "visible_subject_fully_opaque": (
            bool(np.all(final_alpha_pixels[visible_pixels] == 255))
            if visible_pixels.any()
            else False
        ),
        "alpha_mask_used": args.alpha_mask is not None,
        "errors": errors,
        "required_visual_review": [
            "Compare the generated color layer with the source at full size; reject any changed visible feature, pose, scale, or position.",
            "Confirm the character is one continuous layer across small interface crossings, with no scenery, text, panels, frame, or unrelated decoration.",
            "Inspect black and white previews for clean antialiased alpha, complete pale and dark details, and no checkerboard residue.",
            "Reject invented hidden anatomy or broad reconstruction beyond the minimum local continuity required for parallax.",
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
