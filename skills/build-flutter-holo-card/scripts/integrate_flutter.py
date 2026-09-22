#!/usr/bin/env python3
"""Copy the portable package and accepted card assets into a Flutter project."""
import argparse
from pathlib import Path
import shutil
import tempfile
import json
import uuid
import yaml
from asset_pipeline import check, digest, RUNTIME


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=tuple(RUNTIME), default="height")
    p.add_argument("--bundle", required=True, type=Path)
    p.add_argument("--project", required=True, type=Path)
    p.add_argument("--name", default="holographic_card")
    a = p.parse_args()
    check(a.bundle, a.mode)
    if not a.name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric asset name")
    project = a.project.resolve()
    pubspec = project / "pubspec.yaml"
    config = yaml.safe_load(pubspec.read_text())
    dep = "build_flutter_holo_card_template"
    dependency = {"path": "packages/" + dep}
    dependencies = config.setdefault("dependencies", {})
    if dep in dependencies and dependencies[dep] != dependency:
        raise ValueError(
            "Existing package dependency has a different source; reconcile it explicitly"
        )
    package = project / "packages" / dep
    assets = project / "assets" / a.name / a.mode
    # Never overwrite an unregistered/user-owned output directory.
    if assets.exists():
        raise ValueError(
            "Destination exists. Choose a fresh asset name/project or review the previous integration before updating"
        )
    template = Path(__file__).resolve().parents[1] / "assets/flutter"
    with tempfile.TemporaryDirectory(prefix="holo-install-") as tmp:
        staged = Path(tmp) / dep
        shutil.copytree(
            template,
            staged,
            ignore=shutil.ignore_patterns(
                ".dart_tool", "build", "pubspec.lock", "test"
            ),
        )
        package_pubspec = staged / "pubspec.yaml"
        package_config = yaml.safe_load(package_pubspec.read_text())
        package_config["flutter"]["shaders"] = [
            s for s in package_config["flutter"]["shaders"] if not s.startswith("test/")
        ]
        package_pubspec.write_text(yaml.safe_dump(package_config, sort_keys=False))
        existing_package = package.exists()
        if existing_package:
            for file in staged.rglob("*"):
                if file.is_file() and (
                    not (package / file.relative_to(staged)).is_file()
                    or digest(file) != digest(package / file.relative_to(staged))
                ):
                    raise ValueError(
                        "Existing shared package differs from this skill; inspect the package update before replacing"
                    )
        dependencies[dep] = dependency
        flutter = config.setdefault("flutter", {})
        registrations = flutter.setdefault("assets", [])
        asset_key = assets.relative_to(project).as_posix() + "/"
        if asset_key not in registrations:
            registrations.append(asset_key)
        updated = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
        backup = pubspec.with_name("pubspec.yaml.holo-backup-" + uuid.uuid4().hex[:8])
        evidence = project / "holo-reports" / a.name / a.mode
        if evidence.exists():
            raise ValueError("Existing evidence directory would be overwritten")
        shutil.copy2(pubspec, backup)
        try:
            package.parent.mkdir(parents=True, exist_ok=True)
            if not existing_package:
                shutil.copytree(staged, package)
            assets.mkdir(parents=True)
            for name in RUNTIME[a.mode]:
                shutil.copy2(a.bundle / name, assets / name)
            # Retain review and source provenance outside the runtime asset directory.
            evidence = project / "holo-reports" / a.name / a.mode
            shutil.copytree(a.bundle, evidence)
            temp = pubspec.with_suffix(".tmp")
            temp.write_text(updated)
            temp.replace(pubspec)
        except Exception:
            if package.exists() and not existing_package:
                shutil.rmtree(package)
            if assets.exists():
                shutil.rmtree(assets)
            if evidence.exists():
                shutil.rmtree(evidence)
            shutil.copy2(backup, pubspec)
            raise
    print(
        json.dumps(
            {
                "package": str(package),
                "assets": str(assets),
                "mode": a.mode,
                "next": "flutter pub get; flutter analyze; flutter test; flutter build web",
            }
        )
    )


if __name__ == "__main__":
    main()
