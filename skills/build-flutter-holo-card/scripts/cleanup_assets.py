#!/usr/bin/env python3
"""Remove known holo-card intermediates after final asset validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


MERGED_FINAL_FILES = {
    "source.png",
    "background.png",
    "foreground.png",
    "character_contour.png",
    "character_bloom.png",
}

LAYERED_FINAL_FILES = MERGED_FINAL_FILES | {"character.png"}

TEMPORARY_FILES = {
    "alignment-overlay.png",
    "background-generated.png",
    "character-generated.png",
    "character-alpha-mask.png",
    "character-visible-mask.png",
    "character-selection.png",
    "character-visible-selection.png",
    "character-on-black.png",
    "character-on-white.png",
    "character-alignment-overlay.png",
    "character-report.json",
    "foreground-selection.png",
    "foreground-alpha-mask.png",
    "foreground-presence-mask.png",
    "foreground-visible-subject-mask.png",
    "foreground-opacity-selection.png",
    "foreground-opaque-subject-selection.png",
    "foreground-opaque-subject-mask.png",
    "foreground-alpha.png",
    "foreground-on-black.png",
    "foreground-on-white.png",
    "foreground-alignment-overlay.png",
    "foreground-report.json",
    "foreground-bridge-mask.png",
    "foreground-bridge-overlay.png",
    "foreground-bridge-on-black.png",
    "foreground-bridge-on-white.png",
    "foreground-bridge-report.json",
    "structure-sketch-generated-raw.png",
    "structure-lineart-generated-raw.png",
    "structure-generated.png",
    "structure-generated-transparent.png",
    "structure-generated-report.json",
    "structure-aligned.png",
    "structure-affine.json",
    "character-region-mask.png",
    "character-region-overlay.png",
    "character-region-report.json",
    "structure-local.png",
    "structure-local-overlay.png",
    "structure-local-report.json",
    "ui-occlusion-selection.png",
    "ui-occlusion.png",
    "ui-occlusion-overlay.png",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--effect-mode",
        choices=("merged-2d", "layered-3d"),
        default="merged-2d",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve(strict=True)
    if not output_dir.is_dir():
        raise ValueError("Output path is not a directory")

    final_files = (
        LAYERED_FINAL_FILES
        if args.effect_mode == "layered-3d"
        else MERGED_FINAL_FILES
    )
    missing = sorted(name for name in final_files if not (output_dir / name).is_file())
    if missing:
        raise ValueError(f"Refusing cleanup because final files are missing: {missing}")

    removed: list[str] = []
    temporary_files = set(TEMPORARY_FILES)
    if args.effect_mode == "merged-2d":
        temporary_files.add("character.png")
    for name in sorted(temporary_files):
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
                "effect_mode": args.effect_mode,
                "output_dir": str(output_dir),
                "kept": sorted(final_files),
                "removed": removed,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
