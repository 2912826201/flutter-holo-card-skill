#!/usr/bin/env python3
"""Fit a generated height background to its exact extended canvas.

The model owns every pixel. This step only resizes the entire output; it never
crops, pads, paints, composites, or applies an artistic color correction.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import uuid

from PIL import Image

from asset_pipeline import bind, digest, write_json


MAX_ASPECT_ERROR = 0.03
EXTENSION_FRACTION = 0.08


def run(args):
    if args.mode != "height":
        raise ValueError("Only height uses an extended generated background")
    if args.output.resolve() == args.report.resolve():
        raise ValueError("Output image and report must use different paths")
    for name, path in (("source", args.source), ("generated", args.generated)):
        if path.resolve() in (args.output.resolve(), args.report.resolve()):
            raise ValueError(f"{name} input must not be an output or report")

    with Image.open(args.source) as opened:
        source_size = opened.size
    with Image.open(args.generated) as opened:
        generated = opened.copy()
    if generated.mode not in ("RGB", "RGBA"):
        raise ValueError("Generated background must be an RGB or RGBA image")
    if generated.mode == "RGBA" and generated.getchannel("A").getextrema() != (255, 255):
        raise ValueError("Generated background must be fully opaque")

    source_width, source_height = source_size
    pad_x = math.ceil(source_width * EXTENSION_FRACTION)
    pad_y = math.ceil(source_height * EXTENSION_FRACTION)
    target_size = (source_width + 2 * pad_x, source_height + 2 * pad_y)
    target_ratio = target_size[0] / target_size[1]
    generated_ratio = generated.width / generated.height
    aspect_error = abs(generated_ratio / target_ratio - 1)
    if aspect_error > MAX_ASPECT_ERROR:
        raise ValueError(
            "Generated background aspect ratio differs from extended canvas "
            f"by {aspect_error:.2%}; maximum is {MAX_ASPECT_ERROR:.0%}"
        )

    generated_size = generated.size
    if generated_size != target_size:
        generated = generated.resize(target_size, Image.Resampling.LANCZOS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(
        args.output.name + "." + uuid.uuid4().hex + ".tmp.png"
    )
    try:
        generated.save(temporary, format="PNG")
        os.replace(temporary, args.output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "mode": "height",
        "inputs": bind([args.source, args.generated]),
        "source_sha256": digest(args.source),
        "generated_sha256": digest(args.generated),
        "output_sha256": digest(args.output),
        "source_canvas": list(source_size),
        "generated_canvas": list(generated_size),
        "output_canvas": list(target_size),
        "source_rect_pixels": [pad_x, pad_y, source_width, source_height],
        "padding_pixels": [pad_x, pad_y],
        "aspect_error": round(aspect_error, 8),
        "normalization": "none" if generated_size == target_size else "whole-canvas-lanczos",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("height", "medium", "low"), default="height")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--generated", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.report.resolve() in (args.source.resolve(), args.generated.resolve()):
        print(
            json.dumps(
                {"status": "failed", "error": "Report must not overwrite an input image"},
                ensure_ascii=False,
            )
        )
        return 1
    # An input/output alias is invalid, but must never delete the supplied image.
    if args.output.resolve() not in (args.source.resolve(), args.generated.resolve()):
        args.output.unlink(missing_ok=True)
    try:
        result = run(args)
        write_json(args.report, {"status": "pass", **result})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        if args.output.resolve() not in (args.source.resolve(), args.generated.resolve()):
            args.output.unlink(missing_ok=True)
        write_json(
            args.report,
            {"status": "failed", "mode": args.mode, "error": str(error)},
        )
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
