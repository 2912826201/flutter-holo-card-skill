#!/usr/bin/env python3
"""Lock enclosed ambiguous scenery pockets into the foreground depth layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


def parse_seed(value: str) -> tuple[int, int]:
    parts = value.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Expected a seed formatted as x,y")
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError as error:
        raise argparse.ArgumentTypeError("Seed coordinates must be integers") from error


def composite_preview(foreground: Image.Image, value: int) -> Image.Image:
    base = Image.new("RGBA", foreground.size, (value, value, value, 255))
    return Image.alpha_composite(base, foreground).convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--foreground", required=True, type=Path)
    parser.add_argument("--seed", required=True, action="append", type=parse_seed)
    parser.add_argument("--output-foreground", required=True, type=Path)
    parser.add_argument("--output-mask", type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--output-black-preview", type=Path)
    parser.add_argument("--output-white-preview", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--alpha-threshold", type=int, default=128)
    parser.add_argument("--max-bridge-coverage", type=float, default=0.12)
    args = parser.parse_args()

    if not 1 <= args.alpha_threshold <= 254:
        raise ValueError("Alpha threshold must be between 1 and 254")
    if not 0 < args.max_bridge_coverage < 1:
        raise ValueError("Maximum bridge coverage must be between 0 and 1")

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    foreground = ImageOps.exif_transpose(Image.open(args.foreground)).convert("RGBA")
    if foreground.size != source.size:
        raise ValueError("Foreground canvas must match the source canvas exactly")

    source_pixels = np.asarray(source, dtype=np.uint8)
    foreground_pixels = np.asarray(foreground, dtype=np.uint8)
    source_alpha = source_pixels[..., 3]
    foreground_alpha = foreground_pixels[..., 3]

    # 只连接卡片可见范围内的透明像素，避免把圆角外部透明区误锁进前景。
    transparent = np.logical_and(
        foreground_alpha < args.alpha_threshold,
        source_alpha >= args.alpha_threshold,
    ).astype(np.uint8)
    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(
        transparent, connectivity=8
    )

    height, width = transparent.shape
    selected_labels: set[int] = set()
    components: list[dict[str, object]] = []
    for x, y in args.seed:
        if not 0 <= x < width or not 0 <= y < height:
            raise ValueError(f"Seed {x},{y} is outside the {width}x{height} canvas")
        label = int(labels[y, x])
        if label == 0:
            raise ValueError(
                f"Seed {x},{y} is not inside a transparent foreground pocket"
            )
        if label in selected_labels:
            continue

        component_x, component_y, component_width, component_height, area = map(
            int, stats[label]
        )
        touches_canvas_edge = (
            component_x == 0
            or component_y == 0
            or component_x + component_width == width
            or component_y + component_height == height
        )
        if touches_canvas_edge:
            raise ValueError(
                f"Seed {x},{y} selects an open region touching the canvas edge"
            )

        selected_labels.add(label)
        components.append(
            {
                "seed": [x, y],
                "area": area,
                "bbox": [
                    component_x,
                    component_y,
                    component_width,
                    component_height,
                ],
            }
        )

    if component_count <= 1 or not selected_labels:
        raise ValueError("No enclosed transparent foreground pocket was selected")

    bridge_mask = np.isin(labels, list(selected_labels))
    bridge_pixels = int(bridge_mask.sum())
    bridge_coverage = bridge_pixels / float(width * height)
    if bridge_coverage > args.max_bridge_coverage:
        raise ValueError(
            "Selected bridge covers "
            f"{bridge_coverage:.4%}, above the configured "
            f"{args.max_bridge_coverage:.4%} limit"
        )

    # 输出 RGB 始终来自原图，只改变选中封闭区域的 Alpha 和景深归属。
    output_pixels = source_pixels.copy()
    output_alpha = foreground_alpha.copy()
    output_alpha[bridge_mask] = source_alpha[bridge_mask]
    output_pixels[..., 3] = output_alpha
    output = Image.fromarray(output_pixels, mode="RGBA")

    args.output_foreground.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.output_foreground)

    if args.output_mask:
        args.output_mask.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(
            np.where(bridge_mask, 255, 0).astype(np.uint8), mode="L"
        ).save(args.output_mask)
    if args.output_overlay:
        args.output_overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay = source_pixels.copy()
        overlay[bridge_mask, :3] = np.rint(
            source_pixels[bridge_mask, :3] * 0.25
            + np.array([255, 24, 24], dtype=np.float32) * 0.75
        ).astype(np.uint8)
        Image.fromarray(overlay, mode="RGBA").convert("RGB").save(
            args.output_overlay
        )
    if args.output_black_preview:
        args.output_black_preview.parent.mkdir(parents=True, exist_ok=True)
        composite_preview(output, 20).save(args.output_black_preview)
    if args.output_white_preview:
        args.output_white_preview.parent.mkdir(parents=True, exist_ok=True)
        composite_preview(output, 255).save(args.output_white_preview)

    source_rgb_preserved = bool(
        np.array_equal(source_pixels[..., :3], output_pixels[..., :3])
    )
    report = {
        "ok": source_rgb_preserved,
        "canvas": [width, height],
        "component_count": len(components),
        "components": components,
        "bridge_pixels": bridge_pixels,
        "bridge_coverage": round(bridge_coverage, 6),
        "foreground_coverage_before": round(
            float((foreground_alpha >= args.alpha_threshold).mean()), 6
        ),
        "foreground_coverage_after": round(
            float((output_alpha >= args.alpha_threshold).mean()), 6
        ),
        "source_rgb_preserved": source_rgb_preserved,
        "required_visual_review": [
            "Confirm the red bridge overlay covers only the intended enclosed ambiguous pocket.",
            "Confirm no bridge boundary crosses open scenery or a visible subject contour.",
            "Confirm enough unbridged scenery remains for useful background parallax.",
        ],
    }
    rendered = json.dumps(report, indent=2)
    if args.output_report:
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
