from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageStat


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "build-flutter-holo-card" / "scripts"


class ScriptTests(unittest.TestCase):
    def test_effect_modes_only_fallback_on_explicit_safety_refusal(self) -> None:
        skill = (
            ROOT / "skills" / "build-flutter-holo-card" / "SKILL.md"
        ).read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        shader = (
            ROOT
            / "skills"
            / "build-flutter-holo-card"
            / "assets"
            / "flutter"
            / "shaders"
            / "holographic_card.frag"
        ).read_text(encoding="utf-8")
        foreground_preparer = (SCRIPTS / "prepare_foreground.py").read_text(
            encoding="utf-8"
        )
        workflow = (
            ROOT
            / "skills"
            / "build-flutter-holo-card"
            / "references"
            / "resource-workflow.md"
        ).read_text(encoding="utf-8")

        self.assertIn("effect=auto (default)", skill)
        self.assertIn("Start and remain on `layered-3d`", skill)
        self.assertIn("Only an explicit refusal payload returned by", skill)
        self.assertIn(
            "The agent's own quality judgment is never refusal evidence", skill
        )
        self.assertIn("report that primary stage as blocked", skill)
        self.assertIn("Never change effect mode", skill)
        self.assertIn("never leave a transparent notch around the character", skill)
        self.assertIn("character -> complete UI", skill)
        self.assertIn("--ui-crossing-mode", workflow)
        self.assertIn("--completion-image", workflow)
        self.assertNotIn("does not pass visual review, continue with merged-2d", skill)
        self.assertIn("requested_effect", skill)
        self.assertIn("effect=layered-3d", readme)
        self.assertIn("effect=merged-2d", readme)
        self.assertIn("uniform float uLayeredCharacter;", shader)
        self.assertIn("uniform sampler2D uCharacter;", shader)
        self.assertIn("(outputPoint - vec2(0.5)) * 1.6", shader)
        self.assertNotIn("extract_green_matte", foreground_preparer)
        self.assertNotIn('add_argument("--selection"', foreground_preparer)

    def test_contour_contract_is_source_based_not_outer_silhouette_only(self) -> None:
        skill = (
            ROOT / "skills" / "build-flutter-holo-card" / "SKILL.md"
        ).read_text(encoding="utf-8")
        workflow = (
            ROOT
            / "skills"
            / "build-flutter-holo-card"
            / "references"
            / "resource-workflow.md"
        ).read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        normalizer = (
            SCRIPTS / "prepare_generated_lineart.py"
        ).read_text(encoding="utf-8")
        checker = (SCRIPTS / "check_assets.py").read_text(encoding="utf-8")

        self.assertIn("Contour is provenance-based, not position-based", skill)
        self.assertIn("defining internal lines", skill)
        self.assertIn("add no absent line", skill)
        self.assertIn("Contour does not mean only the outer silhouette", workflow)
        self.assertIn("Internal source-visible contours are valid", workflow)
        self.assertIn("visible eyes, mouth lines, facial markings", workflow)
        self.assertIn("眼睛、嘴巴、面部标记", readme)
        self.assertNotIn(
            "add facial, anatomical, hair, fur, fabric, surface",
            skill + workflow,
        )
        self.assertIn('default=0.12', normalizer)
        self.assertIn('line_coverage >= 0.12', checker)
        self.assertIn('"warnings": warnings', normalizer)
        self.assertIn('"warnings": warnings', checker)

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
            (root / "foreground-completion-generated.png").write_bytes(
                b"temporary"
            )
            (root / "foreground-completion-selection.png").write_bytes(
                b"temporary"
            )
            (root / "foreground-completion-mask.png").write_bytes(b"temporary")
            (root / "foreground-visible-subject-mask.png").write_bytes(
                b"temporary"
            )
            (root / "foreground-opacity-selection.png").write_bytes(b"temporary")
            (root / "foreground-opaque-subject-selection.png").write_bytes(
                b"temporary"
            )
            (root / "foreground-opaque-subject-mask.png").write_bytes(b"temporary")
            (root / "alignment-overlay.png").write_bytes(b"temporary")
            (root / "foreground-bridge-mask.png").write_bytes(b"temporary")
            (root / "foreground-bridge-overlay.png").write_bytes(b"temporary")
            (root / "character-region-mask.png").write_bytes(b"temporary")
            (root / "structure-local.png").write_bytes(b"temporary")
            (root / "structure-sketch-generated-raw.png").write_bytes(b"temporary")
            (root / "structure-lineart-generated-raw.png").write_bytes(b"temporary")
            (root / "structure-generated-transparent.png").write_bytes(b"temporary")
            (root / "structure-generated-report.json").write_bytes(b"temporary")
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
            self.assertFalse(
                (root / "foreground-completion-generated.png").exists()
            )
            self.assertFalse(
                (root / "foreground-completion-selection.png").exists()
            )
            self.assertFalse((root / "foreground-completion-mask.png").exists())
            self.assertFalse(
                (root / "foreground-visible-subject-mask.png").exists()
            )
            self.assertFalse((root / "foreground-opacity-selection.png").exists())
            self.assertFalse(
                (root / "foreground-opaque-subject-selection.png").exists()
            )
            self.assertFalse((root / "foreground-opaque-subject-mask.png").exists())
            self.assertFalse((root / "alignment-overlay.png").exists())
            self.assertFalse((root / "foreground-bridge-mask.png").exists())
            self.assertFalse((root / "foreground-bridge-overlay.png").exists())
            self.assertFalse((root / "character-region-mask.png").exists())
            self.assertFalse((root / "structure-local.png").exists())
            self.assertFalse((root / "structure-sketch-generated-raw.png").exists())
            self.assertFalse((root / "structure-lineart-generated-raw.png").exists())
            self.assertFalse((root / "structure-generated-transparent.png").exists())
            self.assertFalse((root / "structure-generated-report.json").exists())
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

    def test_cleanup_assets_keeps_six_layered_runtime_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final_names = (
                "source.png",
                "background.png",
                "character.png",
                "foreground.png",
                "character_contour.png",
                "character_bloom.png",
            )
            for name in final_names:
                (root / name).write_bytes(b"final")
            (root / "character-on-black.png").write_bytes(b"temporary")
            (root / "character-report.json").write_bytes(b"temporary")

            cleaned = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "cleanup_assets.py"),
                    "--output-dir",
                    str(root),
                    "--effect-mode",
                    "layered-3d",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(cleaned.stdout)
            self.assertEqual(report["effect_mode"], "layered-3d")
            self.assertFalse((root / "character-on-black.png").exists())
            self.assertFalse((root / "character-report.json").exists())
            for name in final_names:
                self.assertTrue((root / name).is_file())

    def test_prepare_generated_character_preserves_visible_opaque_subject(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            generated = root / "generated.png"
            visible = root / "visible.png"
            output = root / "character.png"
            output_mask = root / "subject-mask.png"

            Image.new("RGBA", (100, 140), (40, 60, 80, 255)).save(source)
            generated_image = Image.new("RGBA", (100, 140), (0, 0, 0, 0))
            ImageDraw.Draw(generated_image).ellipse(
                (20, 20, 80, 120), fill=(230, 150, 80, 255)
            )
            generated_image.save(generated)
            visible_image = Image.new("L", (100, 140), 0)
            ImageDraw.Draw(visible_image).ellipse((24, 24, 76, 116), fill=255)
            visible_image.save(visible)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_generated_character.py"),
                    "--source",
                    str(source),
                    "--character",
                    str(generated),
                    "--visible-subject-selection",
                    str(visible),
                    "--output-character",
                    str(output),
                    "--output-visible-subject-mask",
                    str(output_mask),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(prepared.stdout)
            self.assertTrue(report["ok"])
            self.assertTrue(report["visible_subject_fully_opaque"])
            self.assertEqual(report["visible_subject_missing_coverage"], 0)
            final_alpha = np.asarray(Image.open(output).getchannel("A"))
            visible_pixels = np.asarray(Image.open(output_mask)) >= 128
            self.assertTrue(np.all(final_alpha[visible_pixels] == 255))

    def test_prepare_generated_character_uses_exact_mask_not_global_color_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            generated = root / "generated.png"
            alpha_mask = root / "alpha-mask.png"
            visible = root / "visible.png"
            output = root / "character.png"

            Image.new("RGBA", (100, 140), (40, 60, 80, 255)).save(source)
            generated_image = Image.new("RGBA", (100, 140), (128, 128, 128, 255))
            ImageDraw.Draw(generated_image).ellipse(
                (20, 20, 80, 120), fill=(20, 220, 40, 255)
            )
            generated_image.save(generated)
            exact_alpha = Image.new("L", generated_image.size, 0)
            ImageDraw.Draw(exact_alpha).ellipse((20, 20, 80, 120), fill=255)
            exact_alpha.save(alpha_mask)
            visible_mask = Image.new("L", generated_image.size, 0)
            ImageDraw.Draw(visible_mask).ellipse((24, 24, 76, 116), fill=255)
            visible_mask.save(visible)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_generated_character.py"),
                    "--source",
                    str(source),
                    "--character",
                    str(generated),
                    "--alpha-mask",
                    str(alpha_mask),
                    "--visible-subject-mask",
                    str(visible),
                    "--output-character",
                    str(output),
                    "--output-visible-subject-mask",
                    str(root / "subject-mask.png"),
                    "--feather-radius",
                    "0",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(prepared.stdout)
            self.assertTrue(report["alpha_mask_used"])
            result = Image.open(output).convert("RGBA")
            self.assertEqual(result.getpixel((50, 70)), (20, 220, 40, 255))
            self.assertEqual(result.getpixel((2, 2))[3], 0)

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

    def test_prepare_generated_lineart_removes_baked_checkerboard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            lineart = root / "lineart.png"
            structure = root / "structure.png"
            transparent = root / "transparent.png"

            Image.new("RGBA", (100, 140), (60, 80, 100, 255)).save(reference)
            generated = Image.new("RGB", (110, 154), (140, 140, 140))
            draw = ImageDraw.Draw(generated)
            for y in range(0, 154, 12):
                for x in range(0, 110, 12):
                    if (x // 12 + y // 12) % 2:
                        draw.rectangle((x, y, x + 11, y + 11), fill=(190, 190, 190))
            draw.line((20, 20, 90, 134), fill=(255, 255, 255), width=5)
            generated.save(lineart)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_generated_lineart.py"),
                    "--reference",
                    str(reference),
                    "--lineart",
                    str(lineart),
                    "--output-structure",
                    str(structure),
                    "--output-transparent",
                    str(transparent),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(prepared.stdout)
            self.assertTrue(report["ok"])
            self.assertTrue(report["opaque_background_removed"])
            self.assertTrue(report["resized_to_reference"])
            structure_image = Image.open(structure).convert("L")
            self.assertEqual(structure_image.size, (100, 140))
            self.assertEqual(structure_image.getpixel((3, 3)), 0)
            self.assertGreater(structure_image.getextrema()[1], 240)
            transparent_image = Image.open(transparent).convert("RGBA")
            self.assertEqual(
                transparent_image.getchannel("A").getbbox(),
                structure_image.getbbox(),
            )
            self.assertEqual(transparent_image.getchannel("R").getextrema(), (255, 255))

    def test_prepare_generated_lineart_reports_density_without_rejecting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            lineart = root / "lineart.png"

            Image.new("RGBA", (100, 140), (60, 80, 100, 255)).save(reference)
            generated = Image.new("RGBA", (100, 140), (255, 255, 255, 0))
            ImageDraw.Draw(generated).rectangle(
                (10, 10, 50, 79), fill=(255, 255, 255, 255)
            )
            generated.save(lineart)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_generated_lineart.py"),
                    "--reference",
                    str(reference),
                    "--lineart",
                    str(lineart),
                    "--output-structure",
                    str(root / "structure.png"),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(prepared.returncode, 0)
            report = json.loads(prepared.stdout)
            self.assertGreaterEqual(report["strong_line_coverage"], 0.12)
            self.assertFalse(report["errors"])
            self.assertTrue(report["warnings"])

    def test_disabled_contour_keeps_five_asset_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            background = root / "background.png"
            foreground = root / "foreground.png"
            subject_mask = root / "foreground-opaque-subject-mask.png"
            contour = root / "character_contour.png"
            bloom = root / "character_bloom.png"

            source_image = Image.new("RGBA", (100, 140), (80, 100, 120, 255))
            source_image.save(source)
            source_image.save(background)
            foreground_image = source_image.copy()
            foreground_alpha = Image.new("L", source_image.size, 255)
            ImageDraw.Draw(foreground_alpha).rectangle((35, 35, 65, 105), fill=0)
            foreground_image.putalpha(foreground_alpha)
            foreground_image.save(foreground)
            subject_mask_image = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(subject_mask_image).rectangle((8, 8, 24, 24), fill=255)
            subject_mask_image.save(subject_mask)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_structure_maps.py"),
                    "--foreground",
                    str(foreground),
                    "--disable-contour",
                    "--output-contour",
                    str(contour),
                    "--output-bloom",
                    str(bloom),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            prepare_report = json.loads(prepared.stdout)
            self.assertFalse(prepare_report["contour_enabled"])
            self.assertEqual(prepare_report["strong_line_coverage"], 0.0)
            self.assertIsNone(Image.open(contour).convert("RGB").getbbox())
            self.assertIsNone(Image.open(bloom).convert("RGB").getbbox())

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
                    "--opaque-subject-mask",
                    str(subject_mask),
                    "--contour",
                    str(contour),
                    "--bloom",
                    str(bloom),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            check_report = json.loads(checked.stdout)
            self.assertTrue(check_report["ok"])
            self.assertFalse(check_report["contour_enabled"])

    def test_check_assets_accepts_independent_character_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            background = root / "background.png"
            foreground = root / "foreground.png"
            character = root / "character.png"
            subject_mask = root / "subject-mask.png"
            structure = root / "structure.png"
            contour = root / "character_contour.png"
            bloom = root / "character_bloom.png"

            source_image = Image.new("RGBA", (100, 140), (70, 90, 120, 255))
            source_image.save(source)
            source_image.save(background)

            foreground_image = source_image.copy()
            foreground_alpha = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(foreground_alpha).rectangle((4, 4, 95, 15), fill=255)
            foreground_image.putalpha(foreground_alpha)
            foreground_image.save(foreground)

            character_image = Image.new("RGBA", source_image.size, (0, 0, 0, 0))
            ImageDraw.Draw(character_image).ellipse(
                (25, 25, 75, 115), fill=(220, 150, 90, 255)
            )
            character_image.save(character)
            subject_mask_image = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(subject_mask_image).ellipse((28, 28, 72, 112), fill=255)
            subject_mask_image.save(subject_mask)
            structure_image = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(structure_image).ellipse(
                (25, 25, 75, 115), outline=255, width=1
            )
            structure_image.save(structure)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_structure_maps.py"),
                    "--foreground",
                    str(character),
                    "--structure",
                    str(structure),
                    "--output-contour",
                    str(contour),
                    "--output-bloom",
                    str(bloom),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
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
                    "--character",
                    str(character),
                    "--ui-crossing-mode",
                    "none",
                    "--opaque-subject-mask",
                    str(subject_mask),
                    "--contour",
                    str(contour),
                    "--bloom",
                    str(bloom),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(checked.stdout)
            self.assertTrue(report["ok"])
            self.assertEqual(report["effect_mode"], "layered-3d")
            self.assertTrue(report["subject_fully_opaque"])
            self.assertIsNotNone(report["character_coverage"])

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
            selection = root / "alpha-mask.png"
            foreground = root / "foreground.png"
            subject_selection = root / "subject-selection.png"
            subject_mask = root / "subject-mask.png"
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

            selection_image = Image.new("L", (200, 280), 0)
            ImageDraw.Draw(selection_image).rounded_rectangle(
                (2, 2, 197, 277), radius=16, outline=255, width=10
            )
            ImageDraw.Draw(selection_image).ellipse(
                (56, 60, 144, 216), fill=255
            )
            selection_image.save(selection)

            subject_selection_image = Image.new("L", (200, 280), 0)
            ImageDraw.Draw(subject_selection_image).ellipse(
                (56, 60, 144, 216), fill=255
            )
            subject_selection_image.save(subject_selection)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_foreground.py"),
                    "--source",
                    str(source),
                    "--alpha-mask",
                    str(selection),
                    "--opaque-subject-selection",
                    str(subject_selection),
                    "--output-foreground",
                    str(foreground),
                    "--output-opaque-subject-mask",
                    str(subject_mask),
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
            self.assertTrue(report["subject_fully_opaque"])
            self.assertEqual(report["opaque_subject_missing_coverage"], 0.0)
            self.assertEqual(report["canvas"], [100, 140])
            self.assertEqual(report["selection_mode"], "exact_alpha_mask")

            source_rgb = Image.open(source).convert("RGB")
            foreground_image = Image.open(foreground).convert("RGBA")
            self.assertEqual(source_rgb.tobytes(), foreground_image.convert("RGB").tobytes())
            self.assertLess(foreground_image.getchannel("A").getextrema()[0], 10)
            self.assertGreater(foreground_image.getchannel("A").getextrema()[1], 245)
            self.assertTrue(mask.is_file())
            self.assertTrue(subject_mask.is_file())
            self.assertTrue(black_preview.is_file())
            self.assertTrue(white_preview.is_file())
            self.assertTrue(overlay.is_file())

    def test_prepare_foreground_restores_character_occluded_ui_below_source_pixels(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            visible_mask = root / "foreground-alpha-mask.png"
            completion_image = root / "foreground-completion-generated.png"
            completion_selection = root / "foreground-completion-selection.png"
            foreground = root / "foreground.png"
            completion_mask = root / "foreground-completion-mask.png"

            source_image = Image.new("RGBA", (100, 140), (30, 70, 120, 255))
            source_draw = ImageDraw.Draw(source_image)
            source_draw.rectangle((5, 64, 39, 75), fill=(245, 245, 245, 255))
            source_draw.rectangle((61, 64, 94, 75), fill=(245, 245, 245, 255))
            source_draw.rectangle((40, 38, 60, 105), fill=(205, 70, 125, 255))
            source_image.save(source)

            visible = Image.new("L", source_image.size, 0)
            visible_draw = ImageDraw.Draw(visible)
            visible_draw.rectangle((5, 64, 39, 75), fill=255)
            visible_draw.rectangle((61, 64, 94, 75), fill=255)
            visible.save(visible_mask)

            generated = Image.new("RGBA", source_image.size, (0, 0, 0, 255))
            ImageDraw.Draw(generated).rectangle(
                (40, 64, 60, 75), fill=(238, 232, 210, 255)
            )
            generated.save(completion_image)
            completion = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(completion).rectangle((40, 64, 60, 75), fill=255)
            completion.save(completion_selection)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_foreground.py"),
                    "--source",
                    str(source),
                    "--alpha-mask",
                    str(visible_mask),
                    "--layer-role",
                    "interface",
                    "--completion-image",
                    str(completion_image),
                    "--completion-mask",
                    str(completion_selection),
                    "--output-completion-mask",
                    str(completion_mask),
                    "--output-foreground",
                    str(foreground),
                    "--feather-radius",
                    "0",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(prepared.stdout)
            output = Image.open(foreground).convert("RGBA")
            final_completion = Image.open(completion_mask).convert("L")

            self.assertTrue(report["ok"])
            self.assertTrue(report["hidden_ui_completion_used"])
            self.assertGreater(report["hidden_ui_completion_coverage"], 0)
            self.assertFalse(report["source_rgb_preserved"])
            self.assertTrue(report["opaque_source_rgb_preserved"])
            self.assertEqual(output.getpixel((20, 70)), (245, 245, 245, 255))
            self.assertEqual(output.getpixel((50, 70)), (238, 232, 210, 255))
            self.assertEqual(output.getpixel((20, 30))[3], 0)
            self.assertEqual(final_completion.getpixel((50, 70)), 255)
            self.assertEqual(final_completion.getpixel((20, 70)), 0)

    def test_check_assets_requires_and_validates_layered_ui_crossing_mode(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            background = root / "background.png"
            visible_mask = root / "foreground-alpha-mask.png"
            completion_image = root / "foreground-completion-generated.png"
            completion_selection = root / "foreground-completion-selection.png"
            completion_mask = root / "foreground-completion-mask.png"
            foreground = root / "foreground.png"
            character = root / "character.png"
            subject_mask = root / "subject-mask.png"
            contour = root / "contour.png"
            bloom = root / "bloom.png"

            source_image = Image.new("RGBA", (100, 140), (30, 70, 120, 255))
            source_draw = ImageDraw.Draw(source_image)
            source_draw.rectangle((5, 64, 39, 75), fill=(245, 245, 245, 255))
            source_draw.rectangle((61, 64, 94, 75), fill=(245, 245, 245, 255))
            source_draw.rectangle((40, 38, 60, 105), fill=(205, 70, 125, 255))
            source_image.save(source)
            Image.new("RGBA", source_image.size, (30, 70, 120, 255)).save(
                background
            )

            visible = Image.new("L", source_image.size, 0)
            visible_draw = ImageDraw.Draw(visible)
            visible_draw.rectangle((5, 64, 39, 75), fill=255)
            visible_draw.rectangle((61, 64, 94, 75), fill=255)
            visible.save(visible_mask)
            generated = Image.new("RGBA", source_image.size, (0, 0, 0, 255))
            ImageDraw.Draw(generated).rectangle(
                (40, 64, 60, 75), fill=(238, 232, 210, 255)
            )
            generated.save(completion_image)
            completion = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(completion).rectangle((40, 64, 60, 75), fill=255)
            completion.save(completion_selection)

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_foreground.py"),
                    "--source",
                    str(source),
                    "--alpha-mask",
                    str(visible_mask),
                    "--layer-role",
                    "interface",
                    "--completion-image",
                    str(completion_image),
                    "--completion-mask",
                    str(completion_selection),
                    "--output-completion-mask",
                    str(completion_mask),
                    "--output-foreground",
                    str(foreground),
                    "--feather-radius",
                    "0",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            character_image = Image.new("RGBA", source_image.size, (0, 0, 0, 0))
            ImageDraw.Draw(character_image).rectangle(
                (40, 38, 60, 105), fill=(205, 70, 125, 255)
            )
            character_image.save(character)
            subject = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(subject).rectangle((40, 38, 60, 105), fill=255)
            subject.save(subject_mask)
            Image.new("RGBA", source_image.size, (0, 0, 0, 255)).save(contour)
            Image.new("RGBA", source_image.size, (0, 0, 0, 255)).save(bloom)

            base_command = [
                sys.executable,
                str(SCRIPTS / "check_assets.py"),
                "--source",
                str(source),
                "--background",
                str(background),
                "--foreground",
                str(foreground),
                "--character",
                str(character),
                "--opaque-subject-mask",
                str(subject_mask),
                "--contour",
                str(contour),
                "--bloom",
                str(bloom),
            ]
            missing_mode = subprocess.run(
                base_command,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(missing_mode.returncode, 0)
            self.assertIn(
                "Layered mode requires explicit --ui-crossing-mode none or completed",
                json.loads(missing_mode.stdout)["errors"],
            )

            checked = subprocess.run(
                [
                    *base_command,
                    "--ui-crossing-mode",
                    "completed",
                    "--foreground-completion-mask",
                    str(completion_mask),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(checked.stdout)
            self.assertTrue(report["ok"])
            self.assertEqual(report["ui_crossing_mode"], "completed")
            self.assertGreater(report["foreground_completion_coverage"], 0)
            self.assertTrue(report["foreground_completion_fully_covered"])
            self.assertTrue(
                report["foreground_completion_inside_subject_occlusion"]
            )
            self.assertTrue(report["opaque_source_rgb_preserved"])

            invalid_completion = root / "foreground-completion-outside-subject.png"
            invalid_mask = Image.open(completion_mask).convert("L")
            ImageDraw.Draw(invalid_mask).rectangle((8, 66, 12, 72), fill=255)
            invalid_mask.save(invalid_completion)
            rejected = subprocess.run(
                [
                    *base_command,
                    "--ui-crossing-mode",
                    "completed",
                    "--foreground-completion-mask",
                    str(invalid_completion),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(
                "Foreground completion mask extends outside the source-visible subject occlusion",
                json.loads(rejected.stdout)["errors"],
            )

    def test_prepare_foreground_preserves_translucent_panel_depth(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            selection = root / "opacity-selection.png"
            presence = root / "presence-mask.png"
            subject_selection = root / "subject-selection.png"
            subject_mask = root / "subject-mask.png"
            foreground = root / "foreground.png"
            report_path = root / "report.json"

            source_image = Image.new("RGBA", (100, 140), (28, 65, 110, 255))
            source_draw = ImageDraw.Draw(source_image)
            source_draw.ellipse((20, 18, 78, 92), fill=(205, 75, 145, 255))
            source_draw.rectangle((8, 98, 92, 132), fill=(120, 155, 205, 255))
            for x in range(10, 91, 8):
                source_draw.rectangle(
                    (x, 99, min(x + 3, 92), 131),
                    fill=(55, 95, 145, 255),
                )
            source_draw.line((18, 112, 82, 112), fill=(245, 245, 245, 255), width=3)
            source_image.save(source)

            opacity = Image.new("L", source_image.size, 0)
            opacity_draw = ImageDraw.Draw(opacity)
            opacity_draw.ellipse((20, 18, 78, 92), fill=128)
            opacity_draw.rectangle((8, 98, 92, 132), fill=128)
            opacity_draw.line((18, 112, 82, 112), fill=255, width=3)
            opacity.save(selection)

            presence_image = Image.new("L", source_image.size, 0)
            presence_draw = ImageDraw.Draw(presence_image)
            presence_draw.ellipse((20, 18, 78, 92), fill=255)
            presence_draw.rectangle((8, 98, 92, 132), fill=255)
            presence_draw.line((18, 112, 82, 112), fill=255, width=3)
            presence_image.save(presence)

            subject_selection_image = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(subject_selection_image).ellipse(
                (20, 18, 78, 92), fill=255
            )
            subject_selection_image.save(subject_selection)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_foreground.py"),
                    "--source",
                    str(source),
                    "--opacity-selection",
                    str(selection),
                    "--presence-mask",
                    str(presence),
                    "--opaque-subject-selection",
                    str(subject_selection),
                    "--output-foreground",
                    str(foreground),
                    "--output-opaque-subject-mask",
                    str(subject_mask),
                    "--output-report",
                    str(report_path),
                    "--feather-radius",
                    "0",
                    "--translucent-alpha",
                    "144",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(prepared.stdout)
            self.assertTrue(report["ok"])
            self.assertEqual(report["selection_mode"], "three_state_opacity")
            self.assertTrue(report["presence_mask_used"])
            self.assertGreater(report["translucent_material_coverage"], 0.1)
            self.assertEqual(report["translucent_alpha"], 144)
            self.assertFalse(report["source_rgb_preserved"])
            self.assertTrue(report["opaque_source_rgb_preserved"])
            self.assertTrue(report["translucent_rgb_decontaminated"])
            self.assertTrue(report["subject_fully_opaque"])
            self.assertEqual(report["opaque_subject_missing_coverage"], 0.0)

            output = Image.open(foreground).convert("RGBA")
            self.assertEqual(output.getpixel((2, 70))[3], 0)
            self.assertEqual(output.getpixel((12, 102))[3], 144)
            self.assertEqual(output.getpixel((50, 112))[3], 255)
            self.assertEqual(output.getpixel((50, 50))[3], 255)
            self.assertEqual(Image.open(subject_mask).convert("L").getpixel((50, 50)), 255)
            self.assertEqual(
                source_image.convert("RGBA").getpixel((50, 50))[:3],
                output.getpixel((50, 50))[:3],
            )
            self.assertNotEqual(
                source_image.convert("RGBA").getpixel((12, 102))[:3],
                output.getpixel((12, 102))[:3],
            )
            self.assertTrue(report_path.is_file())

    def test_prepare_foreground_rejects_subject_missing_from_presence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            selection = root / "selection.png"
            subject_selection = root / "subject-selection.png"

            source_image = Image.new("RGBA", (100, 140), (30, 70, 120, 255))
            source_image.save(source)
            selection_image = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(selection_image).rectangle(
                (20, 25, 55, 105), fill=255
            )
            selection_image.save(selection)
            subject_selection_image = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(subject_selection_image).rectangle(
                (20, 25, 75, 105), fill=255
            )
            subject_selection_image.save(subject_selection)

            prepared = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "prepare_foreground.py"),
                    "--source",
                    str(source),
                    "--alpha-mask",
                    str(selection),
                    "--opaque-subject-selection",
                    str(subject_selection),
                    "--output-foreground",
                    str(root / "foreground.png"),
                    "--output-opaque-subject-mask",
                    str(root / "subject-mask.png"),
                    "--feather-radius",
                    "0",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(prepared.returncode, 0)
            report = json.loads(prepared.stdout)
            self.assertGreater(report["opaque_subject_missing_coverage"], 0.0)
            self.assertIn(
                "Foreground presence selection misses pixels from the opaque subject",
                report["errors"],
            )

    def test_check_assets_allows_translucent_material_color_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            background = root / "background.png"
            foreground = root / "foreground.png"
            subject_mask = root / "subject-mask.png"
            contour = root / "contour.png"
            bloom = root / "bloom.png"

            source_image = Image.new("RGBA", (40, 56), (20, 40, 60, 255))
            source_image.save(source)
            source_image.save(background)

            source_pixels = np.asarray(source_image, dtype=np.uint8)
            foreground_pixels = source_pixels.copy()
            foreground_pixels[..., 3] = 0
            foreground_pixels[12:45, 8:32, 3] = 144
            foreground_pixels[20:38, 14:26, :3] = (70, 90, 130)
            foreground_pixels[23:32, 18:22, :3] = source_pixels[23:32, 18:22, :3]
            foreground_pixels[23:32, 18:22, 3] = 255
            Image.fromarray(foreground_pixels, mode="RGBA").save(foreground)
            subject_mask_image = Image.new("L", source_image.size, 0)
            ImageDraw.Draw(subject_mask_image).rectangle((18, 23, 21, 31), fill=255)
            subject_mask_image.save(subject_mask)

            contour_image = Image.new("RGBA", source_image.size, (0, 0, 0, 255))
            ImageDraw.Draw(contour_image).line(
                (18, 23, 21, 31), fill=(255, 255, 255, 255), width=1
            )
            contour_image.save(contour)
            bloom_image = Image.new("RGBA", source_image.size, (0, 0, 0, 255))
            ImageDraw.Draw(bloom_image).line(
                (18, 23, 21, 31), fill=(180, 90, 0, 255), width=3
            )
            bloom_image.save(bloom)

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
                    "--opaque-subject-mask",
                    str(subject_mask),
                    "--contour",
                    str(contour),
                    "--bloom",
                    str(bloom),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(checked.stdout)
            self.assertTrue(report["ok"])
            self.assertFalse(report["source_rgb_preserved"])
            self.assertTrue(report["opaque_source_rgb_preserved"])
            self.assertTrue(report["required_visual_review"])

    def test_prepare_and_check_asset_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            background = root / "background.png"
            foreground = root / "foreground.png"
            subject_mask = root / "subject-mask.png"
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
            subject_mask_image = Image.new("L", foreground_image.size, 0)
            ImageDraw.Draw(subject_mask_image).rectangle((15, 15, 30, 35), fill=255)
            subject_mask_image.save(subject_mask)

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
                    "--opaque-subject-mask",
                    str(subject_mask),
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
            subject_mask = root / "subject-mask.png"
            contour = root / "contour.png"
            bloom = root / "bloom.png"
            Image.new("RGBA", (40, 56), (20, 40, 60, 255)).save(source)
            Image.new("RGBA", (40, 56), (20, 40, 60, 255)).save(background)
            changed = Image.new("RGBA", (40, 56), (21, 40, 60, 0))
            ImageDraw.Draw(changed).rectangle((10, 10, 30, 45), fill=(21, 40, 60, 255))
            changed.save(foreground)
            subject_mask_image = Image.new("L", changed.size, 0)
            ImageDraw.Draw(subject_mask_image).rectangle((12, 12, 18, 20), fill=255)
            subject_mask_image.save(subject_mask)
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
                    "--opaque-subject-mask",
                    str(subject_mask),
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
                "Opaque source-owned foreground RGB differs from the normalized source",
                report["errors"],
            )

    def test_check_assets_rejects_transparent_subject(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            background = root / "background.png"
            foreground = root / "foreground.png"
            subject_mask = root / "subject-mask.png"
            contour = root / "contour.png"
            bloom = root / "bloom.png"

            Image.new("RGBA", (40, 56), (20, 40, 60, 255)).save(background)
            foreground_image = Image.new("RGBA", (40, 56), (0, 0, 0, 0))
            ImageDraw.Draw(foreground_image).rectangle(
                (8, 8, 31, 47), fill=(200, 80, 120, 255)
            )
            foreground_image.putpixel((16, 16), (200, 80, 120, 254))
            foreground_image.save(foreground)

            subject_mask_image = Image.new("L", foreground_image.size, 0)
            ImageDraw.Draw(subject_mask_image).rectangle((12, 12, 20, 24), fill=255)
            subject_mask_image.save(subject_mask)
            Image.new("RGBA", foreground_image.size, (0, 0, 0, 255)).save(contour)
            Image.new("RGBA", foreground_image.size, (0, 0, 0, 255)).save(bloom)

            checked = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "check_assets.py"),
                    "--background",
                    str(background),
                    "--foreground",
                    str(foreground),
                    "--opaque-subject-mask",
                    str(subject_mask),
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
            self.assertFalse(report["subject_fully_opaque"])
            self.assertIn(
                "Main subject contains transparent foreground pixels",
                report["errors"],
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
