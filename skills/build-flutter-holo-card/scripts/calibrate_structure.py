#!/usr/bin/env python3
"""Estimate and apply a safe global affine registration for semantic line art."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
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


def normalize_structure(structure: Image.Image) -> np.ndarray:
    array = np.asarray(structure.convert("L"), dtype=np.float32) / 255.0
    return np.clip((array - 24.0 / 255.0) / (207.0 / 255.0), 0.0, 1.0)


def invert_affine(matrix: np.ndarray) -> np.ndarray:
    homogeneous = np.vstack((matrix, np.array((0.0, 0.0, 1.0), dtype=np.float32)))
    return np.linalg.inv(homogeneous)[:2].astype(np.float32)


def validate_warp(warp: np.ndarray, width: int, height: int) -> list[str]:
    errors: list[str] = []
    scale_x = math.hypot(float(warp[0, 0]), float(warp[1, 0]))
    scale_y = math.hypot(float(warp[0, 1]), float(warp[1, 1]))
    rotation = math.degrees(math.atan2(float(warp[1, 0]), float(warp[0, 0])))
    if not 0.90 <= scale_x <= 1.10 or not 0.90 <= scale_y <= 1.10:
        errors.append("Estimated scale exceeds the safe global-registration range")
    if abs(rotation) > 4.0:
        errors.append("Estimated rotation exceeds the safe global-registration range")
    if abs(float(warp[0, 2])) > width * 0.06 or abs(float(warp[1, 2])) > height * 0.06:
        errors.append("Estimated translation exceeds the safe global-registration range")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--structure", required=True, type=Path)
    parser.add_argument("--output-structure", required=True, type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--max-iterations", type=int, default=180)
    args = parser.parse_args()

    reference = ImageOps.exif_transpose(Image.open(args.reference)).convert("RGB")
    structure_image = ImageOps.exif_transpose(Image.open(args.structure)).convert("L")
    structure_image = resize_full_canvas(structure_image, reference.size, "Structure")
    structure = normalize_structure(structure_image)
    if not np.any(structure >= 0.25):
        raise ValueError("Structure is empty")

    rgb = np.asarray(reference, dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    source_edges = cv2.Canny(cv2.GaussianBlur(gray, (0, 0), 0.8), 50, 120)
    distance = cv2.distanceTransform(255 - source_edges, cv2.DIST_L2, 5)
    edge_field = np.exp(-(distance * distance) / (2.0 * 3.0 * 3.0)).astype(np.float32)

    line_region = cv2.dilate(
        (structure >= 0.15).astype(np.uint8), np.ones((17, 17), dtype=np.uint8)
    )
    input_mask = line_region * 255
    warp = np.eye(2, 3, dtype=np.float32)
    criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
        args.max_iterations,
        1e-6,
    )
    correlation, warp = cv2.findTransformECC(
        edge_field,
        structure,
        warp,
        cv2.MOTION_AFFINE,
        criteria,
        input_mask,
        5,
    )
    errors = validate_warp(warp, reference.width, reference.height)
    if correlation < 0.12:
        errors.append("Structure-to-source edge correlation is too low")

    # ECC returns the destination-to-source sampling matrix. The recorded forward
    # coefficients map generated structure coordinates onto the source canvas.
    forward = invert_affine(warp)
    aligned = cv2.warpAffine(
        structure,
        warp,
        reference.size,
        flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    aligned_u8 = np.rint(np.clip(aligned, 0.0, 1.0) * 255.0).astype(np.uint8)
    args.output_structure.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(aligned_u8, mode="L").save(args.output_structure)

    coefficients = [float(value) for value in forward.reshape(-1)]
    report = {
        "ok": not errors,
        "canvas": list(reference.size),
        "edge_correlation": round(float(correlation), 6),
        "forward_affine": [round(value, 9) for value in coefficients],
        "forward_affine_cli": ",".join(f"{value:.9f}" for value in coefficients),
        "errors": errors,
        "required_visual_review": [
            "Inspect eyes, fingers, face, and long silhouette runs in the alignment overlay.",
            "Reject local anatomical mismatch even when global edge correlation passes.",
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
