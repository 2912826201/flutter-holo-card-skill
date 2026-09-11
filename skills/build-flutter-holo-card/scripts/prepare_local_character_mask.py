#!/usr/bin/env python3
"""Build a reviewed coarse character region mask without image generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps


def parse_rect(value: str) -> tuple[int, int, int, int]:
    try:
        parts = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Rectangle coordinates must be integers") from error
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Expected rectangle x0,y0,x1,y1")
    return parts


def parse_polygon(value: str) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for pair in value.split(";"):
        try:
            x, y = (int(part.strip()) for part in pair.split(","))
        except (ValueError, TypeError) as error:
            raise argparse.ArgumentTypeError(
                "Expected polygon x1,y1;x2,y2;x3,y3"
            ) from error
        points.append((x, y))
    if len(points) < 3:
        raise argparse.ArgumentTypeError("Polygon requires at least three points")
    return points


def validate_points(
    points: list[tuple[int, int]], size: tuple[int, int], label: str
) -> None:
    width, height = size
    if any(not 0 <= x < width or not 0 <= y < height for x, y in points):
        raise ValueError(f"{label} extends outside the {width}x{height} canvas")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--foreground", required=True, type=Path)
    parser.add_argument("--output-mask", required=True, type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--include-rect", action="append", type=parse_rect, default=[])
    parser.add_argument(
        "--include-polygon", action="append", type=parse_polygon, default=[]
    )
    parser.add_argument("--exclude-rect", action="append", type=parse_rect, default=[])
    parser.add_argument(
        "--exclude-polygon", action="append", type=parse_polygon, default=[]
    )
    args = parser.parse_args()

    if not args.include_rect and not args.include_polygon:
        raise ValueError("At least one include rectangle or polygon is required")

    reference = ImageOps.exif_transpose(Image.open(args.reference)).convert("RGBA")
    foreground = ImageOps.exif_transpose(Image.open(args.foreground)).convert("RGBA")
    if foreground.size != reference.size:
        raise ValueError("Foreground canvas must match the reference canvas exactly")
    mask = Image.new("L", reference.size, 0)
    draw = ImageDraw.Draw(mask)

    for rect in args.include_rect:
        x0, y0, x1, y1 = rect
        if x1 <= x0 or y1 <= y0:
            raise ValueError("Include rectangle must have positive width and height")
        validate_points([(x0, y0), (x1, y1)], reference.size, "Include rectangle")
        draw.rectangle(rect, fill=255)
    for polygon in args.include_polygon:
        validate_points(polygon, reference.size, "Include polygon")
        draw.polygon(polygon, fill=255)

    for rect in args.exclude_rect:
        x0, y0, x1, y1 = rect
        if x1 <= x0 or y1 <= y0:
            raise ValueError("Exclude rectangle must have positive width and height")
        validate_points([(x0, y0), (x1, y1)], reference.size, "Exclude rectangle")
        draw.rectangle(rect, fill=0)
    for polygon in args.exclude_polygon:
        validate_points(polygon, reference.size, "Exclude polygon")
        draw.polygon(polygon, fill=0)

    mask_pixels = np.asarray(mask, dtype=np.uint8)
    source_alpha = np.asarray(reference.getchannel("A"), dtype=np.uint8)
    foreground_alpha = np.asarray(foreground.getchannel("A"), dtype=np.uint8)
    mask_pixels = np.minimum.reduce((mask_pixels, source_alpha, foreground_alpha))
    mask = Image.fromarray(mask_pixels, mode="L")
    coverage = float((mask_pixels >= 128).mean())
    if coverage < 0.005:
        raise ValueError("Character region mask is effectively empty")
    if coverage > 0.8:
        raise ValueError("Character region mask is too broad for local contour extraction")

    args.output_mask.parent.mkdir(parents=True, exist_ok=True)
    mask.save(args.output_mask)
    if args.output_overlay:
        args.output_overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay = reference.copy()
        green = Image.new("RGBA", reference.size, (32, 255, 96, 0))
        green.putalpha(mask.point(lambda value: round(value * 0.5)))
        Image.alpha_composite(overlay, green).convert("RGB").save(args.output_overlay)

    report = {
        "ok": True,
        "canvas": list(reference.size),
        "coverage": round(coverage, 6),
        "include_shape_count": len(args.include_rect) + len(args.include_polygon),
        "exclude_shape_count": len(args.exclude_rect) + len(args.exclude_polygon),
        "required_visual_review": [
            "Confirm green covers every visible character part that should emit contour light.",
            "Confirm text, panels, frame, portraits, symbols, and scenery stay outside green.",
        ],
    }
    rendered = json.dumps(report, indent=2)
    if args.output_report:
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
