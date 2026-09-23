#!/usr/bin/env python3
"""Build a portable Flutter Web playground from accepted same-source bundles."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import yaml
from asset_pipeline import check, digest, read_json, RUNTIME, MODES

SKILL = Path(__file__).resolve().parents[1]


def create_demo(bundles, output, title="全息卡实验台"):
    if not bundles or any(mode not in RUNTIME for mode in bundles):
        raise ValueError("Supply at least one supported mode")
    manifests = {}
    for mode, bundle in bundles.items():
        check(Path(bundle), mode)
        manifests[mode] = read_json(Path(bundle) / "manifest.json")
    if len({digest(Path(b) / "source.png") for b in bundles.values()}) != 1:
        raise ValueError("Demo modes must share the exact same source image")
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Destination exists; use a fresh demo directory")
    modes = [mode for mode in MODES if mode in bundles]
    first = modes[0]
    manifest = manifests[first]
    card = {"title": title, "width": manifest["canvas"][0], "height": manifest["canvas"][1],
            "sourceRect": manifests.get("height", {}).get("background_source_rect", [0, 0, 1, 1])}
    settings = {"mode": first, "effect": .8, "foil": 1.0, "contour": .55,
                "depth": 2.0, "motion": 3.0, "sensitivity": 1.0, "tilt": .2,
                "auto": True, "physical": True, "poseX": None, "poseY": None}
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".holo-demo-", dir=output.parent))
    try:
        shutil.copytree(SKILL / "assets/demo", stage, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".dart_tool", "build", "pubspec.lock"))
        package = stage / "packages/build_flutter_holo_card_template"
        shutil.copytree(SKILL / "assets/flutter", package,
                        ignore=shutil.ignore_patterns(".dart_tool", "build", "pubspec.lock", "test"))
        config = yaml.safe_load((package / "pubspec.yaml").read_text())
        config["flutter"]["shaders"] = [s for s in config["flutter"]["shaders"] if not s.startswith("test/")]
        (package / "pubspec.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
        config = yaml.safe_load((stage / "pubspec.yaml").read_text())
        images = ["packages/build_flutter_holo_card_template/assets/holographic_foil.png"]
        for mode in modes:
            target = stage / "assets/holographic_card" / mode
            target.mkdir(parents=True)
            config["flutter"]["assets"].append(target.relative_to(stage).as_posix() + "/")
            for name in RUNTIME[mode]:
                shutil.copy2(Path(bundles[mode]) / name, target / name)
                images.append((target / name).relative_to(stage).as_posix())
        (stage / "pubspec.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
        # JSON is also a valid Dart constant literal for this scalar/list/map data.
        (stage / "lib/demo_defaults.dart").write_text(
            f"const initialSettings = {json.dumps(settings, ensure_ascii=False)};\n"
            f"const demoCard = {json.dumps(card, ensure_ascii=False).replace(chr(36), chr(92) + chr(36))};\n"
            f"const availableModes = {json.dumps(modes)};\n")
        sources = {p.relative_to(stage).as_posix(): p.read_text()
                   for p in stage.rglob("*") if p.is_file() and p.suffix != ".png"}
        (stage / "assets/export_payload.json").write_text(json.dumps({
            "sources": sources, "images": images, "modes": modes, "card": card,
        }, ensure_ascii=False))
        stage.rename(output)
    except Exception:
        shutil.rmtree(stage)
        raise
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["all", *RUNTIME], default="all")
    for mode in RUNTIME:
        parser.add_argument("--" + mode, type=Path, help=f"Accepted {mode} candidate")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", default="全息卡实验台")
    args = parser.parse_args()
    modes = list(MODES) if args.mode == "all" else [args.mode]
    if any(getattr(args, m) is None for m in modes):
        parser.error("Pass an accepted bundle for each requested mode: " + ", ".join(modes))
    print(create_demo({m: getattr(args, m) for m in modes}, args.output, args.title))


if __name__ == "__main__":
    main()
