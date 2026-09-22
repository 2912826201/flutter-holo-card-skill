from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/build-flutter-holo-card/scripts"))
import asset_pipeline as pipeline


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.png"
        self.mask = self.root / "mask.png"
        self.bg = self.root / "generated.png"
        self.review = self.root / "review.json"
        source = Image.new("RGBA", (100, 140), (20, 60, 100, 0))
        d = ImageDraw.Draw(source)
        d.rounded_rectangle((0, 0, 99, 139), radius=8, fill=(20, 60, 100, 255))
        d.rectangle((25, 30, 75, 110), fill=(220, 80, 100, 255))
        d.line((35, 45, 65, 95), fill=(10, 15, 20), width=3)
        source.save(self.source)
        mask = Image.new("L", source.size)
        ImageDraw.Draw(mask).rectangle((25, 30, 75, 110), fill=255)
        mask.save(self.mask)
        Image.new("RGBA", (116, 164), (35, 75, 115, 255)).save(self.bg)

    def prepare(self, mode="height"):
        pipeline.write_json(
            self.review,
            {
                "mode": mode,
                "decision": "pass",
                "inputs": pipeline.bind([self.source, self.mask]),
                "evidence": pipeline.bind([self.mask]),
                "notes": "Synthetic owner rectangle matched against fixture coordinates.",
            },
        )
        a = argparse.Namespace(
            mode=mode,
            source=self.source,
            mask=self.mask,
            mask_review=self.review,
            background=self.bg,
            output=self.root / mode,
        )
        pipeline.build(a)
        return a, a.output / "candidate"

    def accept(self, bundle, mode="height"):
        pipeline.review(
            argparse.Namespace(
                bundle=bundle,
                mode=mode,
                decision="pass",
                evidence=[self.source],
                notes="Synthetic fixture has exact registration and expected background colors.",
            )
        )

    def test_mode_specific_runtime_counts(self):
        for mode, count in [("height", 5), ("medium", 3), ("low", 1)]:
            _, b = self.prepare(mode)
            m = pipeline.read_json(b / "manifest.json")
            self.assertEqual(len(m["files"]), count)
            self.assertEqual(pipeline.check(b, mode, False)["visual"], "pending")
            with self.assertRaises(ValueError):
                pipeline.check(b, mode)
            self.accept(b, mode)
            self.assertTrue(pipeline.check(b, mode)["accepted"])
            if mode != "height":
                self.assertFalse((b / "foreground.png").exists())
                self.assertFalse((b / "background.png").exists())

    def test_low_does_not_need_mask_or_generation(self):
        a = argparse.Namespace(
            mode="low",
            source=self.source,
            mask=None,
            mask_review=None,
            background=None,
            output=self.root / "low",
        )
        pipeline.build(a)
        self.assertTrue((a.output / "candidate/source.png").exists())

    def test_known_background_restored_and_foreground_rgb_preserved(self):
        _, b = self.prepare()
        source = np.asarray(Image.open(self.source))
        bg = np.asarray(Image.open(b / "background.png"))
        fg = np.asarray(Image.open(b / "foreground.png"))
        self.assertTrue(np.array_equal(source[:, :, :3], fg[:, :, :3]))
        self.assertEqual(bg[22, 18, :3].tolist(), [20, 60, 100])
        self.assertLess(np.max(np.abs(bg[62, 58, :3].astype(int) - [20, 60, 100])), 3)

    def test_gray_mask_rejected_and_failed_retry_retires_old_candidate(self):
        a, b = self.prepare()
        self.accept(b)
        Image.new("L", (100, 140), 128).save(self.mask)
        with self.assertRaises(ValueError):
            pipeline.build(a)
        self.assertFalse(b.exists())
        self.assertEqual(
            pipeline.read_json(a.output / "status.json")["status"], "failed"
        )
        self.assertTrue(list((a.output / "diagnostics").glob("attempt-*/failure.json")))

    def test_stale_input_report_and_missing_resource_rejected(self):
        _, b = self.prepare()
        self.accept(b)
        (b / "foreground_contour.png").unlink()
        with self.assertRaises(FileNotFoundError):
            pipeline.check(b, "height")
        _, b = self.prepare()
        self.accept(b)
        self.review.write_text("{}")
        with self.assertRaises(ValueError):
            pipeline.check(b, "height")

    def test_cross_mode_upstream_and_bundle_rejected(self):
        a, b = self.prepare("medium")
        with self.assertRaises(ValueError):
            pipeline.check(b, "height")
        a.mode = "height"
        with self.assertRaises(ValueError):
            pipeline.build(a)

    def mutate(self, b, name, change):
        im = Image.open(b / name).convert("RGBA")
        change(im)
        im.save(b / name)
        # Even a producer that recomputes a file hash cannot bless bad geometry.
        m = pipeline.read_json(b / "manifest.json")
        m["files"][name] = pipeline.digest(b / name)
        pipeline.write_json(b / "manifest.json", m)

    def test_shifted_lineart_rejected_even_with_updated_hash(self):
        _, b = self.prepare()
        self.mutate(b, "foreground_contour.png", lambda im: im.paste(im, (2, 0)))
        with self.assertRaisesRegex(ValueError, "extraction"):
            pipeline.check(b, "height", False)

    def test_checkerboard_and_spill_are_not_accepted_as_contour(self):
        for kind in ["checker", "spill"]:
            _, b = self.prepare()

            def alter(im):
                if kind == "spill":
                    im.putpixel((2, 2), (255, 255, 255, 255))
                else:
                    d = ImageDraw.Draw(im)
                    for y in range(0, 140, 10):
                        for x in range(0, 100, 10):
                            d.rectangle(
                                (x, y, x + 9, y + 9),
                                fill=(
                                    (200, 200, 200, 255)
                                    if (x + y) // 10 % 2
                                    else (255, 255, 255, 255)
                                ),
                            )

            self.mutate(b, "foreground_contour.png", alter)
            with self.assertRaises(ValueError):
                pipeline.check(b, "height", False)

    def test_background_recolor_rejected(self):
        _, b = self.prepare()
        self.mutate(
            b, "background.png", lambda im: im.putpixel((18, 22), (1, 2, 3, 255))
        )
        with self.assertRaisesRegex(ValueError, "background colors"):
            pipeline.check(b, "height", False)

    def test_visual_evidence_stale_or_failed_never_passes(self):
        _, b = self.prepare()
        self.accept(b)
        m = pipeline.read_json(b / "manifest.json")
        m["visual"]["status"] = "fail"
        pipeline.write_json(b / "manifest.json", m)
        with self.assertRaises(ValueError):
            pipeline.check(b, "height")
        self.accept(b)
        m = pipeline.read_json(b / "manifest.json")
        m["visual"]["files"] = {}
        pipeline.write_json(b / "manifest.json", m)
        with self.assertRaises(ValueError):
            pipeline.check(b, "height")

    def test_cleanup_only_registered_temporary_files_preserves_evidence(self):
        _, b = self.prepare()
        self.accept(b)
        (b / "temp.bin").write_bytes(b"temporary")
        (b / "unrelated.txt").write_text("keep")
        m = pipeline.read_json(b / "manifest.json")
        m["temporary_files"] = ["temp.bin"]
        pipeline.write_json(b / "manifest.json", m)
        pipeline.cleanup(argparse.Namespace(bundle=b, mode="height"))
        self.assertFalse((b / "temp.bin").exists())
        self.assertTrue((b / "contour-overlay.png").exists())
        self.assertTrue((b / "unrelated.txt").exists())

    def test_invalid_background_does_not_publish(self):
        a, b = self.prepare()
        Image.new("RGB", (100, 140)).save(self.bg)
        with self.assertRaises(ValueError):
            pipeline.build(a)
        self.assertFalse(b.exists())

    def test_owner_mask_cannot_be_replaced_after_review(self):
        a, b = self.prepare()
        m = Image.open(self.mask)
        m.putpixel((10, 10), 255)
        m.save(self.mask)
        with self.assertRaises(ValueError):
            pipeline.build(a)

    def test_wrong_canvas_rejected(self):
        a, b = self.prepare()
        Image.new("L", (101, 140)).save(self.mask)
        with self.assertRaisesRegex(ValueError, "aligned"):
            pipeline.build(a)

    def test_export_and_two_modes_integrate_into_one_project(self):
        import export_assets

        project = self.root / "app"
        project.mkdir()
        (project / "pubspec.yaml").write_text(
            "name: fixture_app\nenvironment:\n  sdk: ^3.9.0\ndependencies:\n  flutter:\n    sdk: flutter\n"
        )
        script = ROOT / "skills/build-flutter-holo-card/scripts/integrate_flutter.py"
        for mode in ["low", "medium"]:
            _, bundle = self.prepare(mode)
            self.accept(bundle, mode)
            exported = export_assets.export(
                bundle, mode, self.root / ("export-" + mode)
            )
            self.assertTrue((exported / "holographic_foil.png").exists())
            self.assertTrue(export_assets.verify_export(exported, mode)["accepted"])
            self.assertTrue(
                (exported / "licenses/pokemon-cards-css.GPL-3.0.txt").exists()
            )
            run = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--mode",
                    mode,
                    "--bundle",
                    str(bundle),
                    "--project",
                    str(project),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            runtime = project / "assets/holographic_card" / mode
            self.assertEqual(
                {f.name for f in runtime.iterdir()}, set(pipeline.RUNTIME[mode])
            )
        import yaml

        pubspec = yaml.safe_load((project / "pubspec.yaml").read_text())
        self.assertEqual(len(pubspec["flutter"]["assets"]), 2)
        package = project / "packages/build_flutter_holo_card_template"
        self.assertTrue((package / "shaders/foil_material.glsl").exists())
        self.assertNotIn("test/", (package / "pubspec.yaml").read_text())

    def test_export_rejects_pending_and_failed_review(self):
        import export_assets

        _, bundle = self.prepare("low")
        with self.assertRaises(ValueError):
            export_assets.export(bundle, "low", self.root / "bad-export")
        self.assertFalse((self.root / "bad-export").exists())

    def test_upstream_review_evidence_change_is_rejected(self):
        _, bundle = self.prepare()
        evidence = self.root / "evidence.txt"
        evidence.write_text("seen")
        manifest = pipeline.read_json(bundle / "manifest.json")
        manifest["foreground_review"]["evidence"] = pipeline.bind([evidence])
        pipeline.write_json(bundle / "manifest.json", manifest)
        evidence.write_text("changed")
        with self.assertRaisesRegex(ValueError, "evidence"):
            pipeline.check(bundle, "height", False)

    def test_normalized_background_mapping_cannot_disagree(self):
        _, bundle = self.prepare()
        manifest = pipeline.read_json(bundle / "manifest.json")
        manifest["background_source_rect"][0] = 0
        pipeline.write_json(bundle / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "mapping"):
            pipeline.check(bundle, "height", False)

    def test_failed_normalization_invalidates_old_source(self):
        script = ROOT / "skills/build-flutter-holo-card/scripts/normalize_source.py"
        output = self.root / "normalized/source.png"
        run = subprocess.run(
            [
                sys.executable,
                str(script),
                "--mode",
                "low",
                "--source",
                str(self.source),
                "--output",
                str(output),
                "--width",
                "256",
            ],
            capture_output=True,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        args = argparse.Namespace(
            mode="low",
            source=output,
            mask=None,
            mask_review=None,
            background=None,
            output=self.root / "normalized-low",
        )
        pipeline.build(args)
        failed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--mode",
                "low",
                "--source",
                str(self.root / "missing.png"),
                "--output",
                str(output),
            ],
            capture_output=True,
        )
        self.assertNotEqual(failed.returncode, 0)
        with self.assertRaisesRegex(ValueError, "normalization"):
            pipeline.build(args)
        self.assertFalse((args.output / "candidate").exists())


if __name__ == "__main__":
    unittest.main()
