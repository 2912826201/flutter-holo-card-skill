#!/usr/bin/env python3
"""Normalize an AI white-line/black-background guide to the source canvas."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import uuid

import numpy as np
from PIL import Image

from asset_pipeline import digest, write_json


def run(args):
    if args.mode == "low":
        raise ValueError("low has no lineart")
    source = Image.open(args.source).convert("RGBA")
    with Image.open(args.generated) as opened:
        generated = opened.copy()
    generated_size = generated.size
    if abs((generated.width / generated.height) / (source.width / source.height) - 1) > 0.03:
        raise ValueError("Generated lineart aspect ratio differs from source")
    if generated.size != source.size:
        generated = generated.resize(source.size, Image.Resampling.LANCZOS)
    if generated.mode == "RGBA" and np.asarray(generated.getchannel("A")).min() < 128:
        strength = np.asarray(generated.getchannel("A"))
    else:
        strength = np.asarray(generated.convert("L"))
        if getattr(args, "polarity", "light") == "dark":
            strength = 255 - strength
    if np.percentile(strength, 25) > 30:
        raise ValueError("Generated lineart background is not dark/transparent")
    guide = strength.astype("uint8")
    coverage = float((guide >= 32).mean())
    if coverage == 0 or coverage >= 0.95:
        raise ValueError("Generated lineart is empty or filled like a matte")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(args.output.name + "." + uuid.uuid4().hex + ".tmp.png")
    Image.fromarray(guide).save(temporary)
    os.replace(temporary, args.output)
    return {
        "mode": args.mode,
        "source_sha256": digest(args.source),
        "generated_sha256": digest(args.generated),
        "guide_sha256": digest(args.output),
        "canvas": list(source.size),
        "generated_canvas": list(generated_size),
        "line_coverage": round(coverage, 6),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("height", "medium", "low"), default="height")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--generated", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--polarity", choices=("light", "dark"), default="light")
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    paths = [args.output.resolve(), args.report.resolve()]
    if len(set(paths)) != 2 or set(paths) & {args.source.resolve(), args.generated.resolve()}:
        parser.error("Inputs, output and report must use distinct paths")
    args.output.unlink(missing_ok=True)
    try:
        result = run(args)
        write_json(args.report, {"status": "pass", **result})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        args.output.unlink(missing_ok=True)
        write_json(args.report, {"status": "failed", "mode": args.mode, "error": str(error)})
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
