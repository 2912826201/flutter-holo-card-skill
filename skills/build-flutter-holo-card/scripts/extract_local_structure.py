#!/usr/bin/env python3
"""Extract a policy-safe pixel-aligned structure map from accepted local assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


def load_exact(path: Path, mode: str, size: tuple[int, int], label: str) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(path)).convert(mode)
    if image.size != size:
        raise ValueError(f"{label} canvas must match the source canvas exactly")
    return image


def channel_edges(
    channel: np.ndarray,
    valid: np.ndarray,
    quantile: float,
    low_ratio: float,
) -> tuple[np.ndarray, float]:
    gradient_x = cv2.Sobel(channel, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(channel, cv2.CV_32F, 0, 1, ksize=3)
    magnitude = cv2.magnitude(gradient_x, gradient_y)
    samples = magnitude[np.logical_and(valid, magnitude > 0.01)]
    if samples.size == 0:
        return np.zeros_like(channel, dtype=np.uint8), 0.0
    high = max(8.0, float(np.quantile(samples, quantile)))
    low = max(2.0, high * low_ratio)
    return cv2.Canny(channel, low, high, L2gradient=True), high


def remove_tiny_components(edges: np.ndarray, minimum_area: int) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        (edges > 0).astype(np.uint8), connectivity=8
    )
    kept = np.zeros_like(edges)
    for label in range(1, count):
        if int(stats[label, cv2.CC_STAT_AREA]) >= minimum_area:
            kept[labels == label] = 255
    return kept


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--foreground", required=True, type=Path)
    parser.add_argument("--character-mask", required=True, type=Path)
    parser.add_argument("--occlusion-mask", type=Path)
    parser.add_argument("--output-structure", required=True, type=Path)
    parser.add_argument("--output-overlay", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--edge-quantile", type=float, default=0.93)
    parser.add_argument("--low-threshold-ratio", type=float, default=0.42)
    parser.add_argument("--minimum-component-area", type=float, default=12.0)
    parser.add_argument("--maximum-line-coverage", type=float, default=0.12)
    args = parser.parse_args()

    if not 0.5 <= args.edge_quantile <= 0.98:
        raise ValueError("Edge quantile must be between 0.5 and 0.98")
    if not 0.1 <= args.low_threshold_ratio <= 0.9:
        raise ValueError("Low threshold ratio must be between 0.1 and 0.9")
    if args.minimum_component_area < 1:
        raise ValueError("Minimum component area must be positive")

    source = ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
    foreground = load_exact(args.foreground, "RGBA", source.size, "Foreground")
    character_mask = load_exact(
        args.character_mask, "L", source.size, "Character mask"
    )
    occlusion = (
        load_exact(args.occlusion_mask, "L", source.size, "Occlusion mask")
        if args.occlusion_mask
        else Image.new("L", source.size, 0)
    )

    source_pixels = np.asarray(source, dtype=np.uint8)
    foreground_alpha = np.asarray(foreground.getchannel("A"), dtype=np.uint8)
    character_pixels = np.asarray(character_mask, dtype=np.uint8)
    occlusion_pixels = np.asarray(occlusion, dtype=np.uint8)
    valid = np.logical_and.reduce(
        (
            source_pixels[..., 3] >= 32,
            foreground_alpha >= 32,
            character_pixels >= 128,
            occlusion_pixels < 128,
        )
    )
    valid_coverage = float(valid.mean())
    if valid_coverage < 0.003:
        raise ValueError("Visible character region is effectively empty")

    rgb = source_pixels[..., :3]
    # 双边滤波压低印刷网点和压缩噪声，同时保留真实墨线与明暗折线。
    filtered = cv2.bilateralFilter(rgb, d=7, sigmaColor=32, sigmaSpace=5)
    lab = cv2.cvtColor(filtered, cv2.COLOR_RGB2LAB)
    channels = cv2.split(lab)
    edges: list[np.ndarray] = []
    thresholds: list[float] = []
    for index, channel in enumerate(channels):
        channel_quantile = min(0.98, args.edge_quantile + (0.04 if index else 0))
        channel_edge, threshold = channel_edges(
            channel,
            valid,
            channel_quantile,
            args.low_threshold_ratio,
        )
        edges.append(channel_edge)
        thresholds.append(threshold)

    combined = np.maximum.reduce(edges)
    combined[~valid] = 0
    scaled_minimum_area = max(
        1, round(args.minimum_component_area * source.width / 1000.0)
    )
    combined = remove_tiny_components(combined, scaled_minimum_area)
    combined[~valid] = 0

    # 轻微模糊只做像素级抗锯齿，不扩张或重画任何结构。
    antialiased = cv2.GaussianBlur(combined, (0, 0), sigmaX=0.42)
    antialiased[~valid] = 0
    strong_coverage = float((antialiased >= 128).mean())
    errors: list[str] = []
    if strong_coverage < 0.0001:
        errors.append("Local structure is empty or too sparse")
    if strong_coverage > args.maximum_line_coverage:
        errors.append("Local structure is too dense; raise --edge-quantile")

    args.output_structure.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(antialiased, mode="L").save(args.output_structure)
    if args.output_overlay:
        args.output_overlay.parent.mkdir(parents=True, exist_ok=True)
        overlay = source_pixels.copy()
        line_weight = antialiased.astype(np.float32)[..., None] / 255.0 * 0.9
        overlay[..., :3] = np.rint(
            overlay[..., :3] * (1.0 - line_weight)
            + np.array([255, 24, 24], dtype=np.float32) * line_weight
        ).astype(np.uint8)
        Image.fromarray(overlay, mode="RGBA").convert("RGB").save(
            args.output_overlay
        )

    report = {
        "ok": not errors,
        "method": "local_pixel_edges",
        "image_generation_used": False,
        "native_pixel_alignment": True,
        "canvas": list(source.size),
        "visible_character_coverage": round(valid_coverage, 6),
        "strong_line_coverage": round(strong_coverage, 6),
        "edge_quantile": args.edge_quantile,
        "channel_high_thresholds": [round(value, 3) for value in thresholds],
        "minimum_component_area": scaled_minimum_area,
        "occlusion_applied": args.occlusion_mask is not None,
        "errors": errors,
        "required_visual_review": [
            "Confirm lines follow only visible character edges and meaningful source shading.",
            "Reject print grain, foil texture, scenery, typography, panels, frame, and portraits.",
            "Do not infer or restore any structure hidden by foreground graphics.",
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
