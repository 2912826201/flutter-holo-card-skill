#!/usr/bin/env python3
"""Export accepted runtime images, foil and a portable audit record."""
import argparse
from pathlib import Path
import shutil
import tempfile
from asset_pipeline import check, read_json, write_json, digest, RUNTIME


def export(bundle, mode, output):
    check(bundle, mode)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Export destination already exists; choose a new version")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".holo-export-", dir=output.parent))
    try:
        for name in RUNTIME[mode]:
            shutil.copy2(bundle / name, stage / name)
        template = Path(__file__).resolve().parents[1] / "assets/flutter"
        shutil.copy2(
            template / "assets/holographic_foil.png", stage / "holographic_foil.png"
        )
        shutil.copytree(template / "licenses", stage / "licenses")
        audit = stage / "audit"
        audit.mkdir()
        original = read_json(bundle / "manifest.json")
        evidence = {}
        for index, (path, expected) in enumerate(
            original["visual"]["evidence"].items()
        ):
            name = str(index) + "-" + Path(path).name
            shutil.copy2(path, audit / name)
            evidence["audit/" + name] = expected
        portable = {
            k: v
            for k, v in original.items()
            if k not in ("inputs", "support", "temporary_files")
        }
        portable["files"]["holographic_foil.png"] = digest(
            stage / "holographic_foil.png"
        )
        portable["visual"]["evidence"] = evidence
        portable["visual"]["files"] = dict(portable["files"])
        portable["visual"].pop("support", None)
        portable["provenance"] = {
            Path(path).name: value for path, value in original["inputs"].items()
        }
        if "foreground_review" in portable:
            upstream = dict(portable["foreground_review"])
            upstream["inputs"] = {
                Path(path).name: value for path, value in upstream["inputs"].items()
            }
            copied = {}
            for index, (path, value) in enumerate(upstream["evidence"].items()):
                name = "upstream-" + str(index) + "-" + Path(path).name
                shutil.copy2(path, audit / name)
                copied["audit/" + name] = value
            upstream["evidence"] = copied
            portable["foreground_review"] = upstream
        portable["audit_files"] = {}
        for name in original.get("support", {}):
            shutil.copy2(bundle / name, audit / name)
            portable["audit_files"]["audit/" + name] = digest(audit / name)
        portable["kind"] = "accepted-export"
        write_json(stage / "manifest.json", portable)
        stage.rename(output)
    except Exception:
        shutil.rmtree(stage)
        raise
    return output


def verify_export(output, mode):
    output = Path(output).resolve()
    manifest = read_json(output / "manifest.json")
    if manifest.get("kind") != "accepted-export" or manifest["mode"] != mode:
        raise ValueError("Wrong export mode or manifest kind")
    if set(manifest["files"]) != set(RUNTIME[mode] + ["holographic_foil.png"]):
        raise ValueError("Wrong runtime resource set")
    if (
        manifest["visual"]["status"] != "pass"
        or manifest["visual"]["files"] != manifest["files"]
    ):
        raise ValueError("Failed or stale export review")
    files = {
        **manifest["files"],
        **manifest["visual"]["evidence"],
        **manifest.get("audit_files", {}),
        **manifest.get("foreground_review", {}).get("evidence", {}),
    }
    for name, expected in files.items():
        path = (output / name).resolve()
        if output not in path.parents or digest(path) != expected:
            raise ValueError("Missing, modified or unsafe export resource: " + name)
    return {"accepted": True, "mode": mode, "portable": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=tuple(RUNTIME), default="height")
    p.add_argument("--bundle", type=Path)
    p.add_argument("--verify", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.verify:
        print(verify_export(a.verify, a.mode))
    elif a.bundle and a.output:
        print(export(a.bundle, a.mode, a.output))
    else:
        p.error("Pass --bundle and --output, or --verify")


if __name__ == "__main__":
    main()
