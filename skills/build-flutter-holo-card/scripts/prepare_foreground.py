#!/usr/bin/env python3
"""Read image-generated alpha or a generated owner matte; never segment or crop."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
from asset_pipeline import digest, mask_pixels, write_json


def run(args):
    if args.mode != "height":
        raise ValueError("Only height needs a generated foreground")
    source = Image.open(args.source).convert("RGBA")
    with Image.open(args.generated) as opened:
        generated = opened.copy()
    original_size = generated.size
    if abs((generated.width / generated.height) / (source.width / source.height) - 1) > 0.03:
        raise ValueError("Generated foreground aspect ratio differs from source by over 3%")
    kind = getattr(args, "generated_kind", "alpha")
    if kind == "alpha":
        if "A" not in generated.getbands():
            raise ValueError("Generated foreground needs real alpha; request a generated matte if unsupported")
        matte = generated.getchannel("A")
    elif kind == "mask":
        matte = generated.convert("L")
    else:
        raise ValueError("generated-kind must be alpha or mask")
    if matte.size != source.size:
        matte = matte.resize(source.size, Image.Resampling.LANCZOS)
    alpha = np.asarray(matte)
    if alpha.min() > 4 or alpha.max() < 251:
        raise ValueError("Generated foreground has no transparent/opaque separation")
    args.mask.parent.mkdir(parents=True, exist_ok=True)
    matte.save(args.mask)
    mask_pixels(args.mask, source.size)
    colors = np.asarray(source.convert("RGB"), dtype=np.float32)
    tint = alpha[:, :, None].astype(float) / 255 * 0.45
    overlay = colors * (1 - tint) + np.array((245, 35, 75)) * tint
    args.overlay.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(overlay, 0, 255).astype("uint8")).save(args.overlay)
    return {
        "mode": args.mode, "source_sha256": digest(args.source),
        "generated_sha256": digest(args.generated), "mask_sha256": digest(args.mask),
        "canvas": list(source.size), "generated_canvas": list(original_size),
        "normalization": "whole-canvas", "generated_kind": kind,
        "foreground_coverage": round(float((alpha >= 128).mean()), 6),
        "visual_registration": "pending", "alpha_preserved": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("height", "medium", "low"), default="height")
    for key in ("source", "generated", "mask", "overlay", "report"):
        p.add_argument("--" + key, required=True, type=Path)
    p.add_argument("--generated-kind", choices=("alpha", "mask"), default="alpha")
    args = p.parse_args()
    inputs = {args.source.resolve(), args.generated.resolve()}
    outputs = [args.mask.resolve(), args.overlay.resolve(), args.report.resolve()]
    if inputs.intersection(outputs) or len(set(outputs)) != 3:
        p.error("Inputs, outputs and report must use distinct paths")
    for path in (args.mask, args.overlay):
        path.unlink(missing_ok=True)
    try:
        result = run(args)
        write_json(args.report, {"status": "pass", **result})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        for path in (args.mask, args.overlay):
            path.unlink(missing_ok=True)
        write_json(args.report, {"status": "failed", "error": str(error)})
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
