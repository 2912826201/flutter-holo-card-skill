#!/usr/bin/env python3
"""Normalize a card image and establish one explicit static card-shape Alpha."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps


def resize_full_canvas(
    image: Image.Image,
    size: tuple[int, int],
    label: str,
) -> Image.Image:
    expected_aspect = size[0] / size[1]
    actual_aspect = image.width / image.height
    if abs(actual_aspect / expected_aspect - 1) > 0.01:
        raise ValueError(f"{label} aspect ratio differs from the source canvas")
    if image.size == size:
        return image
    return image.resize(size, Image.Resampling.LANCZOS)


def rounded_card_mask(size: tuple[int, int], radius_ratio: float) -> Image.Image:
    scale = 4
    width, height = size
    high_size = (width * scale, height * scale)
    radius = max(1, round(width * radius_ratio * scale))
    high = Image.new("L", high_size, 0)
    ImageDraw.Draw(high).rounded_rectangle(
        (0, 0, high_size[0] - 1, high_size[1] - 1),
        radius=radius,
        fill=255,
    )
    return high.resize(size, Image.Resampling.LANCZOS)


def corner_alpha_report(alpha: Image.Image) -> list[int]:
    width, height = alpha.size
    return [
        alpha.getpixel((0, 0)),
        alpha.getpixel((width - 1, 0)),
        alpha.getpixel((0, height - 1)),
        alpha.getpixel((width - 1, height - 1)),
    ]


def has_usable_card_shape(alpha: Image.Image) -> bool:
    values = np.asarray(alpha, dtype=np.uint8)
    return bool(
        values.max() >= 250
        and (values <= 4).any()
        and all(value <= 4 for value in corner_alpha_report(alpha))
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--width", type=int, default=1000)
    shape_group = parser.add_mutually_exclusive_group()
    shape_group.add_argument("--card-mask", type=Path)
    shape_group.add_argument("--corner-radius-ratio", type=float)
    args = parser.parse_args()

    if args.width < 256:
        raise ValueError("Working width must be at least 256 pixels")
    if args.corner_radius_ratio is not None and not (
        0.005 <= args.corner_radius_ratio <= 0.25
    ):
        raise ValueError("Corner radius ratio must be between 0.005 and 0.25")

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    height = round(source.height * args.width / source.width)
    normalized = source.resize((args.width, height), Image.Resampling.LANCZOS)
    source_alpha = normalized.getchannel("A")

    card_mask_mode: str
    if args.card_mask is not None:
        mask_image = ImageOps.exif_transpose(Image.open(args.card_mask))
        if mask_image.mode not in ("1", "L"):
            raise ValueError("Card-shape mask must use grayscale L or 1 mode")
        card_mask = resize_full_canvas(
            mask_image.convert("L"), normalized.size, "Card-shape mask"
        )
        card_mask_mode = "explicit_mask"
    elif args.corner_radius_ratio is not None:
        card_mask = rounded_card_mask(normalized.size, args.corner_radius_ratio)
        card_mask_mode = "rounded_rectangle"
    elif has_usable_card_shape(source_alpha):
        card_mask = source_alpha
        card_mask_mode = "source_alpha"
    else:
        raise ValueError(
            "Opaque or rectangular source has no usable rounded card-shape Alpha; "
            "pass --corner-radius-ratio or a reviewed grayscale --card-mask"
        )

    final_alpha = (
        source_alpha
        if card_mask_mode == "source_alpha"
        else ImageChops.multiply(source_alpha, card_mask)
    )
    corner_alphas = corner_alpha_report(final_alpha)
    if any(value > 4 for value in corner_alphas):
        raise ValueError("Normalized card-shape Alpha leaves opaque corner pixels")
    alpha_pixels = np.asarray(final_alpha, dtype=np.uint8)
    alpha_coverage = float((alpha_pixels >= 128).mean())
    if alpha_coverage <= 0.8:
        raise ValueError("Card-shape Alpha covers too little of the full canvas")

    normalized.putalpha(final_alpha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    normalized.save(args.output)
    print(
        json.dumps(
            {
                "source_canvas": list(source.size),
                "working_canvas": list(normalized.size),
                "cropped": False,
                "card_mask_mode": card_mask_mode,
                "corner_radius_ratio": args.corner_radius_ratio,
                "card_alpha_coverage": round(alpha_coverage, 6),
                "corner_alphas": corner_alphas,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
