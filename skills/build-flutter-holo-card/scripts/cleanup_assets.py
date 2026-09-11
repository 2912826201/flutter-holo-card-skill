#!/usr/bin/env python3
"""Remove known holo-card intermediates after final asset validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FINAL_FILES = {
    "background.png",
    "foreground.png",
    "character_contour.png",
    "character_bloom.png",
}

TEMPORARY_FILES = {
    "alignment-overlay.png",
    "background-generated.png",
    "source.png",
    "foreground-selection.png",
    "foreground-alpha.png",
    "foreground-on-black.png",
    "foreground-on-white.png",
    "foreground-alignment-overlay.png",
    "foreground-report.json",
    "structure-generated.png",
    "structure-aligned.png",
    "structure-affine.json",
    "ui-occlusion-selection.png",
    "ui-occlusion.png",
    "ui-occlusion-overlay.png",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve(strict=True)
    if not output_dir.is_dir():
        raise ValueError("Output path is not a directory")

    missing = sorted(name for name in FINAL_FILES if not (output_dir / name).is_file())
    if missing:
        raise ValueError(f"Refusing cleanup because final files are missing: {missing}")

    removed: list[str] = []
    for name in sorted(TEMPORARY_FILES):
        candidate = (output_dir / name).resolve(strict=False)
        if candidate.parent != output_dir:
            raise ValueError(f"Refusing path outside output directory: {candidate}")
        if candidate.is_dir():
            raise ValueError(f"Refusing to remove directory: {candidate}")
        if candidate.is_file():
            candidate.unlink()
            removed.append(name)

    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(output_dir),
                "kept": sorted(FINAL_FILES),
                "removed": removed,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
