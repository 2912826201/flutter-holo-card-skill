#!/usr/bin/env python3
"""Mode-bound, hash-bound card preparation. Candidates are never accepted implicitly."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
import uuid

import numpy as np
from PIL import Image, ImageFilter
from quality_review import REQUIRED, record as quality_record, verify as verify_quality

MODES = ("height", "medium", "low")
RUNTIME = {
    "low": ["source.png"],
    "medium": ["source.png", "foreground_contour.png", "foreground_bloom.png"],
    "height": [
        "source.png",
        "background.png",
        "foreground.png",
        "foreground_contour.png",
        "foreground_bloom.png",
    ],
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text())


def bind(paths):
    return {str(Path(p).resolve()): digest(p) for p in paths}


def verify_binding(record, mode, paths):
    if (
        record.get("mode") != mode
        or record.get("decision") != "pass"
        or record.get("inputs") != bind(paths)
    ):
        raise ValueError("Failed, stale or cross-mode upstream review")
    verify_quality(record.get("quality"), ("foreground",))
    if not record.get("notes") or not record.get("evidence"):
        raise ValueError("Visual review requires notes and evidence")
    for path, expected in record["evidence"].items():
        if digest(path) != expected:
            raise ValueError("Stale visual evidence")


def mask_pixels(path, size):
    with Image.open(path) as opened:
        image = opened.copy()
    if image.mode not in ("1", "L") or image.size != size:
        raise ValueError("Mask must be grayscale and exactly aligned to source canvas")
    pixels = np.asarray(image.convert("L"))
    # Natural antialiasing and translucency belong to the generated matte.
    if not (pixels > 4).any() or not (pixels < 251).any():
        raise ValueError("Mask needs both foreground and background")
    return pixels


def bloom_from_core(core, width):
    radius = max(0.7, width / 1000 * 2)
    bloom = Image.merge(
        "RGBA",
        (
            core.filter(ImageFilter.GaussianBlur(radius)),
            core.filter(ImageFilter.GaussianBlur(radius * 3)),
            Image.new("L", core.size, 0),
            Image.new("L", core.size, 255),
        ),
    )
    return core.convert("RGBA"), bloom


def guided_maps(source, mask, guide_path):
    """Use the generated sketch itself as the light map; inspect, never snap it.

    Original-art edges are used only as a tolerance-based registration check.
    Heuristics are diagnostics only; the visual scorecard decides usability.
    """
    with Image.open(guide_path) as opened:
        guide = opened.copy()
    if guide.mode not in ("1", "L") or guide.size != source.size:
        raise ValueError("AI sketch must be grayscale and source-aligned")
    pixels = np.asarray(guide.convert("L"))
    lines = pixels >= 32
    coverage = float(lines.mean())
    if coverage == 0 or coverage >= 0.95:
        raise ValueError("AI sketch is empty or filled like a matte")
    tolerance = max(2, round(source.width * 0.006))
    neighborhood = 2 * tolerance + 1
    scope = np.asarray(
        Image.fromarray(np.where(mask >= 128, 255, 0).astype("uint8")).filter(
            ImageFilter.MaxFilter(neighborhood)
        )
    ) > 0
    card = np.asarray(source.getchannel("A")) > 4
    source_gray = source.convert("L").filter(ImageFilter.GaussianBlur(0.6))
    source_edges = np.asarray(source_gray.filter(ImageFilter.FIND_EDGES)) >= 32
    source_edges &= card & (mask >= 128)
    nearby = np.asarray(
        Image.fromarray(source_edges.astype("uint8") * 255).filter(
            ImageFilter.MaxFilter(neighborhood)
        )
    ) > 0
    line_count = int(lines.sum())
    registration = {
        "line_pixels": line_count,
        "line_coverage": round(coverage, 6),
        "tolerance_pixels": tolerance,
        "near_source_edges_fraction": round(
            float((lines & nearby).sum()) / line_count, 6
        ),
        "outside_foreground_fraction": round(
            float((lines & ~scope).sum()) / line_count, 6
        ),
        "outside_card_fraction": round(float((lines & ~card).sum()) / line_count, 6),
    }
    registration["warnings"] = []
    if registration["near_source_edges_fraction"] < 0.35:
        registration["warnings"].append("Low source-edge agreement; inspect placement visually")
    if registration["outside_foreground_fraction"] > 0.03:
        registration["warnings"].append("Some lines outside matte; inspect foreground scope visually")
    if coverage < 0.001 or coverage > 0.30:
        registration["warnings"].append("Unusual line density; inspect visual usefulness")
    core, bloom = bloom_from_core(guide.convert("L"), source.width)
    return core, bloom, registration


def review_mask(args):
    # Invalidate any previous pass before a new review, even if scoring fails.
    write_json(args.report, {"mode": args.mode, "decision": "pending"})
    source = Image.open(args.source).convert("RGBA")
    mask_pixels(args.mask, source.size)
    record = {
        "quality": quality_record(read_json(args.quality), ("foreground",), args.decision),
        "kind": "foreground-scope",
        "mode": args.mode,
        "decision": args.decision,
        "inputs": bind([args.source, args.mask]),
        "evidence": bind(args.evidence),
        "notes": args.notes,
    }
    if args.mode == "low":
        raise ValueError("low has no segmentation step")
    write_json(args.report, record)
    return record


def build(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Remove the active candidate BEFORE validation; old success cannot survive a failed retry.
    diagnostics = out / "diagnostics"
    diagnostics.mkdir(exist_ok=True)
    if (out / "candidate").exists():
        old_manifest = out / "candidate/manifest.json"
        if old_manifest.exists():
            previous = read_json(old_manifest)
            previous["visual"] = {
                "status": "retired",
                "reason": "A new attempt superseded this candidate",
            }
            write_json(old_manifest, previous)
        shutil.move(
            str(out / "candidate"), str(diagnostics / ("previous-" + uuid.uuid4().hex))
        )
    write_json(out / "status.json", {"mode": args.mode, "status": "building"})
    stage = Path(tempfile.mkdtemp(prefix="attempt-", dir=diagnostics))
    try:
        source = Image.open(args.source).convert("RGBA")
        pixels = np.asarray(source)
        alpha = pixels[:, :, 3]
        if (
            min(source.size) < 16
            or not (alpha >= 250).any()
            or any(alpha[y, x] > 4 for y, x in [(0, 0), (-1, 0), (0, -1), (-1, -1)])
        ):
            raise ValueError(
                "Source needs an explicit card-shape alpha and valid canvas"
            )
        inputs = [args.source]
        normalization = None
        sidecar = args.source.with_suffix(".json")
        if sidecar.exists():
            normalization = read_json(sidecar)
            if (
                normalization.get("kind") != "normalized-source"
                or normalization.get("status") != "pass"
                or normalization.get("output_sha256") != digest(args.source)
            ):
                raise ValueError("Failed or stale source normalization")
            for path, expected in normalization.get("inputs", {}).items():
                if digest(path) != expected:
                    raise ValueError("Original input changed after normalization")
            inputs += [sidecar] + [
                Path(path) for path in normalization.get("inputs", {})
            ]
        source.save(stage / "source.png")
        manifest = {
            "schema": 2,
            "mode": args.mode,
            "canvas": list(source.size),
            "source_input_sha256": digest(args.source),
            "temporary_files": [],
            "format": {"status": "pass"},
            "geometry": {"status": "pass"},
            "visual": {"status": "pending"},
        }
        if args.mode != "low":
            lineart = getattr(args, "lineart", None)
            if not lineart:
                raise ValueError("A generated sketch is required; no automatic edge extraction")
            if args.mask and args.mask_review:
                mask = mask_pixels(args.mask, source.size)
                verify_binding(
                    read_json(args.mask_review), args.mode, [args.source, args.mask]
                )
                manifest["foreground_review"] = read_json(args.mask_review)
                inputs += [args.mask, args.mask_review]
                shutil.copy2(args.mask, stage / "owner-mask.png")
            elif (
                args.mode == "medium"
                and lineart
                and not args.mask
                and not args.mask_review
            ):
                mask = np.full((source.height, source.width), 255, dtype="uint8")
            else:
                raise ValueError(
                    "height needs a reviewed AI foreground mask; medium needs generated lineart"
                )
            contour, bloom, registration = guided_maps(
                source, np.minimum(mask, alpha), lineart
            )
            shutil.copy2(lineart, stage / "lineart-guide.png")
            inputs.append(lineart)
            manifest["contour_source"] = "generated-sketch-v2"
            manifest["lineart_registration"] = registration
            contour.save(stage / "foreground_contour.png")
            bloom.save(stage / "foreground_bloom.png")
            overlay = source.copy()
            overlay.alpha_composite(
                Image.merge(
                    "RGBA",
                    (Image.new("L", source.size, 255),) * 3
                    + (contour.getchannel("R"),),
                )
            )
            overlay.save(stage / "contour-overlay.png")
            if args.mode == "height":
                if not args.background:
                    raise ValueError("height requires generated extended background")
                inputs.append(args.background)
                px, py = math.ceil(source.width * 0.08), math.ceil(source.height * 0.08)
                size = (source.width + 2 * px, source.height + 2 * py)
                bg_image = Image.open(args.background).convert("RGBA")
                if bg_image.size != size or np.asarray(bg_image)[:, :, 3].min() != 255:
                    raise ValueError(
                        f"Extended background must be opaque and exactly {size}; do not stretch it silently"
                    )
                bg_image.save(stage / "background.png")
                manifest["background_composite"] = "generated-background-v3"
                manifest["background_generation_input"] = str(args.background.resolve())
                fg = pixels.copy()
                fg[:, :, 3] = np.round(mask.astype(float) * alpha / 255).astype("uint8")
                Image.fromarray(fg).save(stage / "foreground.png")
                manifest["background_source_rect_pixels"] = [
                    px,
                    py,
                    source.width,
                    source.height,
                ]
                manifest["background_source_rect"] = [
                    px / size[0],
                    py / size[1],
                    source.width / size[0],
                    source.height / size[1],
                ]
        if normalization:
            manifest["normalization"] = normalization
        manifest["inputs"] = bind(inputs)
        manifest["files"] = {name: digest(stage / name) for name in RUNTIME[args.mode]}
        manifest["support"] = {
            p.name: digest(p)
            for p in stage.iterdir()
            if p.is_file() and p.name not in manifest["files"]
        }
        write_json(stage / "manifest.json", manifest)
        check(stage, args.mode, require_visual=False)
        stage.rename(out / "candidate")
        write_json(
            out / "status.json",
            {"mode": args.mode, "status": "candidate", "accepted": False},
        )
        return {
            "status": "candidate",
            "accepted": False,
            "path": str(out / "candidate"),
        }
    except Exception as error:
        report = {
            "mode": args.mode,
            "status": "failed",
            "accepted": False,
            "error": str(error),
        }
        write_json(stage / "failure.json", report)
        write_json(out / "status.json", report)
        raise


def check(bundle, mode, require_visual=True):
    bundle = Path(bundle)
    m = read_json(bundle / "manifest.json")
    if (
        m.get("schema") != 2
        or m["mode"] != mode
        or set(m["files"]) != set(RUNTIME[mode])
    ):
        raise ValueError("Invalid manifest or cross-mode resources")
    for path, expected in m["inputs"].items():
        if digest(path) != expected:
            raise ValueError("Stale input/upstream report")
    for name, expected in {**m["files"], **m.get("support", {})}.items():
        path = bundle / name
        if path.resolve().parent != bundle.resolve() or digest(path) != expected:
            raise ValueError("Missing, modified or unsafe resource: " + name)
    source = Image.open(bundle / "source.png").convert("RGBA")
    src = np.asarray(source)
    if list(source.size) != m["canvas"]:
        raise ValueError("Source canvas changed")
    for name in RUNTIME[mode]:
        with Image.open(bundle / name) as opened:
            im = opened.copy()
        if name != "background.png" and im.size != source.size:
            raise ValueError("Canvas mismatch: " + name)
    if mode != "low":
        upstream = m.get("foreground_review")
        if upstream:
            verify_binding(upstream, mode, list(upstream["inputs"]))
            mask = mask_pixels(bundle / "owner-mask.png", source.size)
        elif mode == "medium" and m.get("contour_source") == "generated-sketch-v2":
            mask = np.full((source.height, source.width), 255, dtype="uint8")
        else:
            raise ValueError("Missing upstream foreground review")
        if m.get("contour_source") == "generated-sketch-v2":
            if m.get("lineart_refusal") or m.get("lineart_refusal_input"):
                raise ValueError("Generated sketch cannot also claim edge fallback")
            expected_core, expected_bloom, registration = guided_maps(
                source, np.minimum(mask, src[:, :, 3]), bundle / "lineart-guide.png"
            )
            if registration != m.get("lineart_registration"):
                raise ValueError("Generated sketch registration report changed")
        else:
            raise ValueError("Unknown contour source")
        for name, expected in [
            ("foreground_contour.png", expected_core),
            ("foreground_bloom.png", expected_bloom),
        ]:
            actual = Image.open(bundle / name).convert("RGBA")
            if actual.tobytes() != expected.tobytes():
                values = np.asarray(actual)[:, :, 0]
                outside = mask < 128
                spill = (
                    int(((values > 4) & outside).sum())
                    if name == "foreground_contour.png"
                    else 0
                )
                # A broad two-tone opaque matte is distinct from a thin spilled line.
                matte = values[outside]
                bright_matte = bool(matte.size and (matte > 100).mean() > 0.5)
                checkerboard = False
                if bright_matte:
                    for step in range(4, 33):
                        same = outside[:, step * 2 :] & outside[:, : -step * 2]
                        alternate = outside[:, step:] & outside[:, :-step]
                        if same.any() and alternate.any():
                            repeated = np.abs(
                                values[:, step * 2 :].astype(int)
                                - values[:, : -step * 2]
                            )[same]
                            changed = np.abs(
                                values[:, step:].astype(int) - values[:, :-step]
                            )[alternate]
                            if (repeated < 3).mean() > 0.9 and (
                                changed > 20
                            ).mean() > 0.7:
                                checkerboard = True
                                break
                raise ValueError(
                    "Contour/bloom differs from bound generated sketch: "
                    + name
                    + f"; line_spill_pixels={spill}; bright_matte={bright_matte}; checkerboard_pattern={checkerboard}"
                )
        if mode == "height":
            bg = np.asarray(Image.open(bundle / "background.png").convert("RGBA"))
            x, y, w, h = m["background_source_rect_pixels"]
            if (
                (x, y, w, h)
                != (
                    math.ceil(w * 0.08),
                    math.ceil(h * 0.08),
                    source.width,
                    source.height,
                )
                or bg.shape[:2] != (h + 2 * y, w + 2 * x)
                or bg[:, :, 3].min() != 255
            ):
                raise ValueError("Invalid extended background geometry/alpha")
            expected_rect = [
                x / bg.shape[1],
                y / bg.shape[0],
                w / bg.shape[1],
                h / bg.shape[0],
            ]
            if m.get("background_source_rect") != expected_rect:
                raise ValueError(
                    "Normalized background mapping disagrees with pixel rectangle"
                )
            generated_path = m.get("background_generation_input")
            if (m.get("background_composite") != "generated-background-v3"
                    or generated_path not in m["inputs"]):
                raise ValueError("Missing bound AI background input")
            generated = np.asarray(Image.open(generated_path).convert("RGBA"))
            if not np.array_equal(bg, generated):
                raise ValueError("Generated background pixels were modified")
            fg = np.asarray(Image.open(bundle / "foreground.png").convert("RGBA"))
            if not np.array_equal(fg[:, :, :3], src[:, :, :3]) or not np.array_equal(
                fg[:, :, 3],
                np.round(mask.astype(float) * src[:, :, 3] / 255).astype("uint8"),
            ):
                raise ValueError("Foreground colors or owner alpha changed")
    if m["format"]["status"] != "pass" or m["geometry"]["status"] != "pass":
        raise ValueError("Failed upstream format/geometry stage")
    if require_visual:
        v = m["visual"]
        verify_quality(v.get("quality"), REQUIRED[mode])
        if (
            v.get("status") != "pass"
            or v.get("files") != m["files"]
            or v.get("support") != m.get("support")
        ):
            raise ValueError("Visual review is pending, failed or stale")
        if not v.get("notes") or not v.get("evidence"):
            raise ValueError("Visual review lacks evidence")
        for path, expected in v["evidence"].items():
            if digest(path) != expected:
                raise ValueError("Visual evidence changed")
    return {
        "mode": mode,
        "format": "pass",
        "geometry": "pass",
        "visual": m["visual"]["status"],
        "accepted": require_visual,
    }


def review(args):
    check(args.bundle, args.mode, require_visual=False)
    m = read_json(args.bundle / "manifest.json")
    m["visual"] = {"status": "pending"}
    write_json(args.bundle / "manifest.json", m)
    status = args.bundle.parent / "status.json"
    if args.bundle.name == "candidate" and status.exists():
        write_json(status, {"mode": args.mode, "status": "reviewing", "accepted": False})
    m["visual"] = {
        "status": args.decision,
        "quality": quality_record(read_json(args.quality), REQUIRED[args.mode], args.decision),
        "files": m["files"],
        "support": m["support"],
        "evidence": bind(args.evidence),
        "notes": args.notes,
    }
    write_json(args.bundle / "manifest.json", m)
    status = args.bundle.parent / "status.json"
    if args.bundle.name == "candidate" and status.exists():
        write_json(
            status,
            {
                "mode": args.mode,
                "status": "accepted" if args.decision == "pass" else "visual-failed",
                "accepted": args.decision == "pass",
            },
        )
    return {"visual": args.decision, "accepted": args.decision == "pass"}


def cleanup(args):
    check(args.bundle, args.mode)
    m = read_json(args.bundle / "manifest.json")
    removed = []
    for name in m.get("temporary_files", []):
        p = args.bundle / name
        if (
            p.resolve().parent != args.bundle.resolve()
            or p.suffix in (".json", ".md")
            or name in m["files"]
            or name in m["support"]
        ):
            raise ValueError("Unsafe cleanup registration")
        if p.exists():
            p.unlink()
            removed.append(name)
    return {"removed": removed, "evidence_preserved": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    for action in ("build", "check", "review", "review-mask", "cleanup"):
        q = sub.add_parser(action)
        q.add_argument("--mode", choices=MODES, default="height")
        if action == "build":
            q.add_argument("--source", required=True, type=Path)
            q.add_argument("--output", required=True, type=Path)
            for key in ("mask", "mask-review", "background", "lineart"):
                q.add_argument("--" + key, type=Path)
        elif action == "review-mask":
            for key in ("source", "mask", "report"):
                q.add_argument("--" + key, type=Path, required=True)
        else:
            q.add_argument("--bundle", type=Path, required=True)
        if action in ("review", "review-mask"):
            q.add_argument("--quality", type=Path, required=True)
            q.add_argument("--decision", choices=("pass", "fail"), required=True)
            q.add_argument("--evidence", type=Path, nargs="+", required=True)
            q.add_argument("--notes", required=True)
        if action == "check":
            q.add_argument(
                "--candidate",
                action="store_true",
                help="Check format/geometry only; never returns accepted=true",
            )
    args = p.parse_args()
    try:
        result = (
            check(args.bundle, args.mode, not args.candidate)
            if args.action == "check"
            else globals()[args.action.replace("-", "_")](args)
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(
            json.dumps(
                {"accepted": False, "error": str(error)}, ensure_ascii=False, indent=2
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
