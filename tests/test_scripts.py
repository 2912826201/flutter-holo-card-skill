from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw, ImageStat


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "build-flutter-holo-card" / "scripts"


class ScriptTests(unittest.TestCase):
    def test_cleanup_assets_keeps_only_final_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final_names = (
                "source.png",
                "background.png",
                "foreground.png",
                "character_contour.png",
                "character_bloom.png",
            )
            for name in final_names:
                (root / name).write_bytes(b"final")
            (root / "background-generated.png").write_bytes(b"temporary")
            (root / "foreground-alpha.png").write_bytes(b"temporary")
            (root / "alignment-overlay.png").write_bytes(b"temporary")
            (root / "foreground-bridge-mask.png").write_bytes(b"temporary")
            (root / "foreground-bridge-overlay.png").write_bytes(b"temporary")
            (root / "notes-owned-by-user.txt").write_text("keep", encoding="utf-8")

            cleaned = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "cleanup_assets.py"),
                    "--output-dir",
                    str(root),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(cleaned.stdout)
            self.assertTrue(report["ok"])
            self.assertFalse((root / "background-generated.png").exists())
            self.assertFalse((root / "foreground-alpha.png").exists())
            self.assertFalse((root / "alignment-overlay.png").exists())
            self.assertFalse((root / "foreground-bridge-mask.png").exists())
            self.assertFalse((root / "foreground-bridge-overlay.png").exists())
            self.assertTrue((root / "notes-owned-by-user.txt").is_file())
            for name in final_names:
                self.assertTrue((root / name).is_file())

    def test_cleanup_assets_requires_runtime_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "background.png",
                "foreground.png",
                "character_contour.png",
                "character_bloom.png",
            ):
                (root / name).write_bytes(b"final")
            (root / "alignment-overlay.png").write_bytes(b"temporary")

            cleaned = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "cleanup_assets.py"),
                    "--output-dir",
                    str(root),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(cleaned.returncode, 0)
            self.assertIn("source.png", cleaned.stderr)
            self.assertTrue((root / "alignment-overlay.png").is_file())

    def test_calibrate_structure_recovers_small_global_drift(self) -> None:
        try:
            import cv2  # noqa: F401
        except ImportError:
            self.skipTest("opencv-python-headless is not installed")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            structure = root / "structure.png"
            aligned = root / "aligned.png"
            report_path = root / "report.json"

            reference_image = Image.new("RGB", (300, 420), (24, 30, 38))
            reference_lines = Image.new("L", reference_image.size, 0)
            draw = ImageDraw.Draw(reference_lines)
            draw.ellipse((78, 50, 230, 214), outline=255, width=4)
            draw.line((92, 118, 210, 310), fill=255, width=4)
            draw.line((54, 330, 242, 350), fill=255, width=4)
            reference_image.paste((235, 235, 235), mask=reference_lines)
            reference_image.save(reference)

            generated = reference_lines.resize((288, 403), Image.Resampling.BICUBIC)
            structure_image = Image.new("L", reference_image.size, 0)
            structure_image.paste(generated, (7, 9))
            structure_image.save(structure)

            before = ImageStat.Stat(
                ImageChops.difference(reference_lines, structure_image)
            ).mean[0]
            calibrated = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "calibrate_structure.py"),
                    "--reference",
                    str(reference),
                    "--structure",
                    str(structure),
                    "--output-structure",
                    str(aligned),
                    "--output-report",
                    str(report_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(calibrated.stdout)
            self.assertTrue(report["ok"])
            self.assertGreater(report["edge_correlation"], 0.12)
            after = ImageStat.Stat(
                ImageChops.difference(
                    reference_lines, Image.open(aligned).convert("L")
                )
            ).mean[0]
            self.assertLess(after, before)
            self.assertTrue(report_path.is_file())

    def test_prepare_occlusion_mask_expands_ui_safely(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            selection = root / "selection.png"
            output = root / "occlusion.png"
            overlay = root / "overlay.png"
            Image.new("RGBA", (100, 140), (80, 100, 120, 255)).save(reference)
            selection_image = Image.new("L", (200, 280), 0)
            ImageDraw.Draw(selection_image).rectangle((20, 20, 180, 45), fill=255)
            ImageDraw.Draw(selection_image).rectangle((35, 220, 165, 265), fill=255)
            selection_image.save(selection)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_occlusion_mask.py"),
                    "--reference",
                    str(reference),
                    "--selection",
                    str(selection),
                    "--output-mask",
                    str(output),
                    "--output-overlay",
                    str(overlay),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(prepared.stdout)
            self.assertTrue(report["ok"])
            self.assertEqual(report["canvas"], [100, 140])
            self.assertGreater(report["occlusion_coverage"], 0.1)
            self.assertTrue(output.is_file())
            self.assertTrue(overlay.is_file())

    def test_normalize_source_preserves_aspect_without_crop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            output = root / "normalized.png"
            Image.new("RGBA", (50, 70), (20, 40, 60, 255)).save(source)
            normalized = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "normalize_source.py"),
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                    "--width",
                    "1000",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(normalized.stdout)
            self.assertEqual(report["working_canvas"], [1000, 1400])
            self.assertFalse(report["cropped"])
            with Image.open(output) as normalized_image:
                self.assertEqual(normalized_image.size, (1000, 1400))

    def test_prepare_foreground_preserves_source_rgb(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            selection = root / "selection.png"
            foreground = root / "foreground.png"
            mask = root / "mask.png"
            black_preview = root / "black.png"
            white_preview = root / "white.png"
            overlay = root / "overlay.png"

            source_image = Image.new("RGBA", (100, 140), (30, 70, 120, 255))
            ImageDraw.Draw(source_image).rounded_rectangle(
                (1, 1, 98, 138), radius=8, outline=(240, 240, 240, 255), width=5
            )
            ImageDraw.Draw(source_image).ellipse(
                (28, 30, 72, 108), fill=(215, 80, 150, 255)
            )
            source_image.save(source)

            selection_image = Image.new("RGB", (200, 280), (0, 255, 0))
            ImageDraw.Draw(selection_image).rounded_rectangle(
                (2, 2, 197, 277), radius=16, outline=(240, 240, 240), width=10
            )
            ImageDraw.Draw(selection_image).ellipse(
                (56, 60, 144, 216), fill=(210, 70, 145)
            )
            selection_image.save(selection)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_foreground.py"),
                    "--source",
                    str(source),
                    "--selection",
                    str(selection),
                    "--output-foreground",
                    str(foreground),
                    "--output-mask",
                    str(mask),
                    "--output-black-preview",
                    str(black_preview),
                    "--output-white-preview",
                    str(white_preview),
                    "--output-overlay",
                    str(overlay),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(prepared.stdout)
            self.assertTrue(report["ok"])
            self.assertTrue(report["source_rgb_preserved"])
            self.assertEqual(report["canvas"], [100, 140])

            source_rgb = Image.open(source).convert("RGB")
            foreground_image = Image.open(foreground).convert("RGBA")
            self.assertEqual(source_rgb.tobytes(), foreground_image.convert("RGB").tobytes())
            self.assertLess(foreground_image.getchannel("A").getextrema()[0], 10)
            self.assertGreater(foreground_image.getchannel("A").getextrema()[1], 245)
            self.assertTrue(mask.is_file())
            self.assertTrue(black_preview.is_file())
            self.assertTrue(white_preview.is_file())
            self.assertTrue(overlay.is_file())

    def test_bridge_foreground_locks_enclosed_source_pixel_pocket(self) -> None:
        try:
            import cv2  # noqa: F401
        except ImportError:
            self.skipTest("opencv-python-headless is not installed")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            foreground = root / "foreground.png"
            output = root / "output.png"
            mask = root / "mask.png"
            overlay = root / "overlay.png"
            report_path = root / "report.json"

            source_image = Image.new("RGBA", (100, 140), (30, 70, 120, 255))
            ImageDraw.Draw(source_image).rectangle(
                (30, 45, 70, 95), fill=(220, 80, 150, 255)
            )
            source_image.save(source)

            foreground_image = source_image.copy()
            alpha = Image.new("L", source_image.size, 255)
            ImageDraw.Draw(alpha).rectangle((38, 54, 62, 86), fill=0)
            foreground_image.putalpha(alpha)
            foreground_image.save(foreground)

            bridged = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "bridge_foreground.py"),
                    "--source",
                    str(source),
                    "--foreground",
                    str(foreground),
                    "--seed",
                    "50,70",
                    "--output-foreground",
                    str(output),
                    "--output-mask",
                    str(mask),
                    "--output-overlay",
                    str(overlay),
                    "--output-report",
                    str(report_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(bridged.stdout)
            self.assertTrue(report["ok"])
            self.assertTrue(report["source_rgb_preserved"])
            self.assertEqual(report["component_count"], 1)
            self.assertGreater(report["bridge_coverage"], 0.04)
            self.assertEqual(Image.open(output).convert("RGBA").getpixel((50, 70))[3], 255)
            self.assertEqual(
                Image.open(source).convert("RGB").tobytes(),
                Image.open(output).convert("RGB").tobytes(),
            )
            self.assertTrue(mask.is_file())
            self.assertTrue(overlay.is_file())
            self.assertTrue(report_path.is_file())

    def test_bridge_foreground_rejects_open_scenery(self) -> None:
        try:
            import cv2  # noqa: F401
        except ImportError:
            self.skipTest("opencv-python-headless is not installed")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            foreground = root / "foreground.png"
            Image.new("RGBA", (100, 140), (30, 70, 120, 255)).save(source)
            foreground_image = Image.new("RGBA", (100, 140), (30, 70, 120, 255))
            alpha = Image.new("L", foreground_image.size, 255)
            ImageDraw.Draw(alpha).rectangle((0, 40, 65, 100), fill=0)
            foreground_image.putalpha(alpha)
            foreground_image.save(foreground)

            bridged = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "bridge_foreground.py"),
                    "--source",
                    str(source),
                    "--foreground",
                    str(foreground),
                    "--seed",
                    "30,70",
                    "--output-foreground",
                    str(root / "output.png"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(bridged.returncode, 0)
            self.assertIn("touching the canvas edge", bridged.stderr)

    def test_prepare_and_check_asset_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            background = root / "background.png"
            foreground = root / "foreground.png"
            structure = root / "structure.png"
            occlusion = root / "occlusion.png"
            contour = root / "contour.png"
            bloom = root / "bloom.png"
            overlay = root / "overlay.png"

            background_image = Image.new("RGBA", (100, 140), (0, 0, 0, 0))
            ImageDraw.Draw(background_image).rounded_rectangle(
                (1, 1, 98, 138), radius=8, fill=(20, 60, 100, 255)
            )
            background_image.save(background)
            foreground_image = Image.new("RGBA", (100, 140), (0, 0, 0, 0))
            ImageDraw.Draw(foreground_image).rectangle(
                (12, 10, 88, 130), fill=(220, 80, 120, 255)
            )
            foreground_image.save(foreground)

            structure_image = Image.new("L", (100, 140), 0)
            ImageDraw.Draw(structure_image).line(
                (20, 20, 75, 110), fill=255, width=2
            )
            structure_image.save(structure)

            occlusion_image = Image.new("L", (100, 140), 0)
            ImageDraw.Draw(occlusion_image).rectangle(
                (45, 55, 60, 85), fill=255
            )
            occlusion_image.save(occlusion)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_structure_maps.py"),
                    "--foreground",
                    str(foreground),
                    "--structure",
                    str(structure),
                    "--output-contour",
                    str(contour),
                    "--output-bloom",
                    str(bloom),
                    "--output-overlay",
                    str(overlay),
                    "--occlusion-mask",
                    str(occlusion),
                    "--forward-affine",
                    "1,0,5,0,1,6",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(prepared.stdout)
            self.assertEqual(report["canvas"], [100, 140])
            self.assertTrue(report["occlusion_applied"])
            self.assertTrue(report["affine_applied"])

            contour_image = Image.open(contour).convert("RGBA")
            red, green, blue, alpha = contour_image.split()
            self.assertEqual(red.tobytes(), green.tobytes())
            self.assertEqual(red.tobytes(), blue.tobytes())
            self.assertEqual(alpha.getextrema(), (255, 255))
            self.assertGreater(red.crop((23, 24, 30, 32)).getextrema()[1], 0)
            self.assertEqual(red.crop((45, 55, 61, 86)).getextrema()[1], 0)

            bloom_image = Image.open(bloom).convert("RGBA")
            self.assertEqual(bloom_image.getchannel("B").getextrema(), (0, 0))
            self.assertTrue(overlay.is_file())

            checked = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "check_assets.py"),
                    "--background",
                    str(background),
                    "--foreground",
                    str(foreground),
                    "--contour",
                    str(contour),
                    "--bloom",
                    str(bloom),
                    "--occlusion-mask",
                    str(occlusion),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            checked_report = json.loads(checked.stdout)
            self.assertTrue(checked_report["ok"])
            self.assertGreater(checked_report["background_coverage"], 0.9)

    def test_check_assets_rejects_changed_foreground_rgb(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            background = root / "background.png"
            foreground = root / "foreground.png"
            contour = root / "contour.png"
            bloom = root / "bloom.png"
            Image.new("RGBA", (40, 56), (20, 40, 60, 255)).save(source)
            Image.new("RGBA", (40, 56), (20, 40, 60, 255)).save(background)
            changed = Image.new("RGBA", (40, 56), (21, 40, 60, 0))
            ImageDraw.Draw(changed).rectangle((10, 10, 30, 45), fill=(21, 40, 60, 255))
            changed.save(foreground)
            line = Image.new("RGBA", (40, 56), (0, 0, 0, 255))
            ImageDraw.Draw(line).line((12, 12, 28, 40), fill=(255, 255, 255, 255))
            line.save(contour)
            Image.new("RGBA", (40, 56), (20, 30, 0, 255)).save(bloom)

            checked = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "check_assets.py"),
                    "--source",
                    str(source),
                    "--background",
                    str(background),
                    "--foreground",
                    str(foreground),
                    "--contour",
                    str(contour),
                    "--bloom",
                    str(bloom),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(checked.returncode, 0)
            report = json.loads(checked.stdout)
            self.assertFalse(report["source_rgb_preserved"])
            self.assertIn(
                "Foreground RGB differs from the normalized source", report["errors"]
            )

    def test_prepare_rejects_different_aspect_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            foreground = root / "foreground.png"
            structure = root / "structure.png"
            Image.new("RGBA", (100, 140), (255, 0, 0, 128)).save(foreground)
            Image.new("L", (100, 100), 255).save(structure)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_structure_maps.py"),
                    "--foreground",
                    str(foreground),
                    "--structure",
                    str(structure),
                    "--output-contour",
                    str(root / "contour.png"),
                    "--output-bloom",
                    str(root / "bloom.png"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("aspect ratio differs", result.stderr)


if __name__ == "__main__":
    unittest.main()
