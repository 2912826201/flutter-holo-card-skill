#!/usr/bin/env python3
"""Check machine-verifiable parts of the Flutter holo-card asset contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat


def alpha(image: Image.Image) -> Image.Image:
    return (
        image.getchannel("A")
        if "A" in image.getbands()
        else Image.new("L", image.size, 255)
    )


def coverage(mask: Image.Image, threshold: int = 128) -> float:
    histogram = mask.convert("L").histogram()
    return sum(histogram[threshold:]) / (mask.width * mask.height)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--background", required=True, type=Path)
    parser.add_argument("--foreground", required=True, type=Path)
    parser.add_argument("--character", type=Path)
    parser.add_argument("--opaque-subject-mask", required=True, type=Path)
    parser.add_argument("--contour", required=True, type=Path)
    parser.add_argument("--bloom", required=True, type=Path)
    parser.add_argument("--occlusion-mask", type=Path)
    parser.add_argument(
        "--ui-crossing-mode",
        choices=("none", "completed"),
    )
    parser.add_argument("--foreground-completion-mask", type=Path)
    args = parser.parse_args()

    background = ImageOps.exif_transpose(Image.open(args.background)).convert("RGBA")
    foreground = ImageOps.exif_transpose(Image.open(args.foreground)).convert("RGBA")
    character = (
        ImageOps.exif_transpose(Image.open(args.character)).convert("RGBA")
        if args.character
        else None
    )
    opaque_subject_mask = ImageOps.exif_transpose(
        Image.open(args.opaque_subject_mask)
    ).convert("L")
    contour = ImageOps.exif_transpose(Image.open(args.contour)).convert("RGBA")
    bloom = ImageOps.exif_transpose(Image.open(args.bloom)).convert("RGBA")
    images = {
        "background": background,
        "foreground": foreground,
        "contour": contour,
        "bloom": bloom,
    }
    if character is not None:
        images["character"] = character
    source = (
        ImageOps.exif_transpose(Image.open(args.source)).convert("RGBA")
        if args.source
        else None
    )
    if source is not None:
        images["source"] = source
    foreground_completion_mask = (
        ImageOps.exif_transpose(
            Image.open(args.foreground_completion_mask)
        ).convert("L")
        if args.foreground_completion_mask
        else None
    )
    if foreground_completion_mask is not None:
        images["foreground_completion_mask"] = foreground_completion_mask

    errors: list[str] = []
    warnings: list[str] = []
    review_items: list[str] = []
    sizes = {name: image.size for name, image in images.items()}
    if len(set(sizes.values())) != 1:
        errors.append(f"Canvas mismatch: {sizes}")

    subject_coverage = coverage(opaque_subject_mask)
    subject_fully_opaque = False
    subject_layer = character if character is not None else foreground
    effect_mode = "layered-3d" if character is not None else "merged-2d"
    if character is not None and args.ui_crossing_mode is None:
        errors.append(
            "Layered mode requires explicit --ui-crossing-mode none or completed"
        )
    if character is None and (
        args.ui_crossing_mode is not None or foreground_completion_mask is not None
    ):
        errors.append("UI crossing completion is valid only in layered mode")
    if args.ui_crossing_mode == "completed" and foreground_completion_mask is None:
        errors.append(
            "Completed UI crossing mode requires --foreground-completion-mask"
        )
    if args.ui_crossing_mode == "none" and foreground_completion_mask is not None:
        errors.append("UI crossing mode none cannot include a completion mask")
    if opaque_subject_mask.size != subject_layer.size:
        errors.append("Opaque subject mask canvas differs from its subject layer")
    elif subject_coverage <= 0.001:
        errors.append("Opaque subject mask is empty")
    else:
        foreground_alpha_pixels = np.asarray(alpha(subject_layer), dtype=np.uint8)
        subject_pixels = np.asarray(opaque_subject_mask, dtype=np.uint8) >= 128
        subject_fully_opaque = bool(
            np.all(foreground_alpha_pixels[subject_pixels] == 255)
        )
        if not subject_fully_opaque:
            errors.append(
                "Main subject contains transparent character pixels"
                if character is not None
                else "Main subject contains transparent foreground pixels"
            )

    background_alpha = alpha(background)
    background_coverage = coverage(background_alpha)
    background_missing_card_coverage = None
    if source is not None and source.size == background.size:
        source_card_pixels = np.asarray(alpha(source), dtype=np.uint8) > 4
        missing_background_pixels = np.logical_and(
            source_card_pixels,
            np.asarray(background_alpha, dtype=np.uint8) < 250,
        )
        background_missing_card_coverage = float(missing_background_pixels.mean())
        if missing_background_pixels.any():
            errors.append("Background is not opaque across the source card shape")
    elif source is None and background_coverage < 0.9:
        warnings.append(
            "Background coverage is below the review guide; pass --source to validate the actual card shape"
        )

    foreground_coverage = coverage(alpha(foreground))
    if foreground_coverage <= 0.001:
        errors.append("Foreground alpha is empty")
    elif foreground_coverage >= 0.999:
        errors.append("Foreground has no transparent scenery region")

    foreground_completion_coverage = 0.0
    completion_fully_covered = None
    completion_inside_subject_occlusion = None
    completion_pixels = np.zeros(foreground.size[::-1], dtype=bool)
    if foreground_completion_mask is not None:
        foreground_completion_coverage = coverage(foreground_completion_mask)
        if foreground_completion_mask.size == foreground.size:
            requested_completion = np.asarray(
                foreground_completion_mask, dtype=np.uint8
            )
            completion_pixels = requested_completion > 4
            foreground_alpha_pixels = np.asarray(
                alpha(foreground), dtype=np.uint8
            )
            completion_fully_covered = (
                bool(
                    np.all(
                        foreground_alpha_pixels[completion_pixels].astype(np.int16)
                        + 4
                        >= requested_completion[completion_pixels].astype(np.int16)
                    )
                )
                if completion_pixels.any()
                else False
            )
            if foreground_completion_coverage <= 0.0001:
                errors.append("Foreground completion mask is empty")
            elif not completion_fully_covered:
                errors.append("Foreground alpha does not cover the UI completion mask")
            if opaque_subject_mask.size == foreground.size:
                # 被人物遮挡的 UI 补全只能填在源人物占据的区域。按画布尺寸给
                # 抗锯齿边缘保留约 1/500 画宽的容差，禁止借补全扩大或重绘 UI。
                edge_margin = max(1, round(foreground.width / 500))
                allowed_occlusion = opaque_subject_mask.filter(
                    ImageFilter.MaxFilter(edge_margin * 2 + 1)
                )
                allowed_pixels = np.asarray(allowed_occlusion, dtype=np.uint8) > 4
                completion_outside_subject = np.logical_and(
                    completion_pixels, ~allowed_pixels
                )
                completion_inside_subject_occlusion = not bool(
                    completion_outside_subject.any()
                )
                if not completion_inside_subject_occlusion:
                    errors.append(
                        "Foreground completion mask extends outside the source-visible subject occlusion"
                    )

    character_coverage = None
    if character is not None:
        character_coverage = coverage(alpha(character))
        if character_coverage <= 0.001:
            errors.append("Character alpha is empty")
        elif character_coverage >= 0.9:
            warnings.append(
                "Character covers most of the canvas; confirm this is a genuinely large subject rather than retained scenery"
            )

    source_rgb_preserved = None
    opaque_source_rgb_preserved = None
    if source is not None:
        if source.size != foreground.size:
            errors.append("Source canvas differs from foreground")
            source_rgb_preserved = False
        else:
            source_pixels = np.asarray(source, dtype=np.uint8)
            foreground_pixels = np.asarray(foreground, dtype=np.uint8)
            rgb_mismatch = np.any(
                source_pixels[..., :3] != foreground_pixels[..., :3], axis=2
            )
            source_rgb_preserved = not bool(rgb_mismatch.any())
            opaque_pixels = np.logical_and(
                foreground_pixels[..., 3] >= 250,
                ~completion_pixels,
            )
            opaque_source_rgb_preserved = not bool(
                np.logical_and(rgb_mismatch, opaque_pixels).any()
            )
            if not opaque_source_rgb_preserved:
                errors.append(
                    "Opaque source-owned foreground RGB differs from the normalized source"
                )
            elif not source_rgb_preserved:
                warnings.append(
                    "Translucent foreground RGB differs from source; confirm it is intentional material-color decontamination"
                )

    red, green, blue, contour_alpha = contour.split()
    if ImageChops.difference(red, green).getbbox() or ImageChops.difference(
        red, blue
    ).getbbox():
        errors.append("Contour must be grayscale RGB, not a packed colored map")
    if contour_alpha.getextrema() != (255, 255):
        errors.append("Contour canvas must be opaque")
    line_coverage = coverage(red)
    contour_enabled = red.getextrema()[1] > 1
    if contour_enabled and line_coverage <= 0.0001:
        errors.append("Contour signal is present but effectively empty")
    elif line_coverage >= 0.12:
        warnings.append(
            "Contour exceeds the density review guide; inspect for fills, shading, or texture"
        )
    contour_owner_alpha = alpha(subject_layer)
    contour_outside_owner = np.logical_and(
        np.asarray(red, dtype=np.uint8) > 4,
        np.asarray(contour_owner_alpha, dtype=np.uint8) <= 4,
    )
    if contour_outside_owner.any():
        errors.append("Contour spills outside its character or merged-foreground owner")

    bloom_red, bloom_green, bloom_blue, bloom_alpha = bloom.split()
    bloom_enabled = max(
        bloom_red.getextrema()[1],
        bloom_green.getextrema()[1],
    ) > 1
    if contour_enabled != bloom_enabled:
        errors.append("Contour and bloom enabled states do not match")
    if ImageStat.Stat(bloom_blue).extrema[0][1] > 1:
        errors.append("Bloom B channel must remain zero")
    if bloom_alpha.getextrema() != (255, 255):
        errors.append("Bloom canvas must be opaque")

    if args.occlusion_mask:
        occlusion = ImageOps.exif_transpose(Image.open(args.occlusion_mask)).convert("L")
        if occlusion.size != contour.size:
            errors.append("Occlusion mask canvas differs from contour")
        else:
            spill = ImageChops.multiply(red, occlusion)
            if spill.getextrema()[1] > 4:
                errors.append("Contour spills into the declared occlusion mask")

    review_items.extend(
        [
            "Visually confirm that the background contains no subject, text, or frame residue.",
            "Visually confirm the opaque subject mask covers every source-visible main-subject pixel and nothing else.",
            (
                "Visually confirm character is continuous, fully opaque over every source-visible subject pixel, and contains no scenery, text, panels, or card frame."
                if character is not None
                else "Visually confirm foreground contains only the fully opaque main subject, subject-linked elements that orbit, surround, frame, overlap, or are emitted or controlled by it, the card frame, panels, and information; reject unrelated scenery."
            ),
            (
                "Visually confirm foreground contains the complete upper interface, text, panels, and frame, including smooth generated continuation wherever the source character interrupted them, with no duplicated character or unrelated scenery."
                if character is not None
                else "Merged foreground mode is active; no independent character layer is expected."
            ),
        ]
    )
    if contour_enabled:
        review_items.append(
            "Inspect the red contour overlay: accept registered source-visible internal defining contours and do not treat contour as external silhouette only; reject lines absent from the source, inferred hidden lines, invented features or decoration, and shading or texture strokes."
        )
    else:
        review_items.append(
            "Contour and bloom are neutral black maps; line emission is intentionally disabled."
        )
    if character is not None:
        review_items.append(
            "Confirm the runtime stacking is always background -> character -> complete UI. If ui_crossing_mode is none, verify the source character never interrupts a continuous frame, panel, or UI stroke. If completed, verify the restored segment covers the moving character without a gap and changes no source-visible UI pixel."
        )
    report = {
        "ok": not errors,
        "canvas": list(foreground.size),
        "effect_mode": effect_mode,
        "background_coverage": round(background_coverage, 6),
        "background_missing_card_coverage": (
            round(background_missing_card_coverage, 6)
            if background_missing_card_coverage is not None
            else None
        ),
        "foreground_coverage": round(foreground_coverage, 6),
        "ui_crossing_mode": args.ui_crossing_mode,
        "foreground_completion_coverage": round(
            foreground_completion_coverage, 6
        ),
        "foreground_completion_fully_covered": completion_fully_covered,
        "foreground_completion_inside_subject_occlusion": (
            completion_inside_subject_occlusion
        ),
        "character_coverage": (
            round(character_coverage, 6)
            if character_coverage is not None
            else None
        ),
        "opaque_subject_coverage": round(subject_coverage, 6),
        "subject_fully_opaque": subject_fully_opaque,
        "source_rgb_preserved": source_rgb_preserved,
        "opaque_source_rgb_preserved": opaque_source_rgb_preserved,
        "contour_enabled": contour_enabled,
        "strong_line_coverage": round(line_coverage, 6),
        "errors": errors,
        "warnings": warnings,
        "required_visual_review": review_items,
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
