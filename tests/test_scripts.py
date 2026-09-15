from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "build-flutter-holo-card"
SCRIPTS = SKILL / "scripts"


def rounded_card(
    size: tuple[int, int], color: tuple[int, int, int]
) -> Image.Image:
    image = Image.new("RGBA", size, (*color, 0))
    radius = max(3, round(size[0] * 0.08))
    ImageDraw.Draw(image).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1),
        radius=radius,
        fill=(*color, 255),
    )
    return image


def run_script(
    name: str, *args: object, check: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *(str(arg) for arg in args)],
        check=check,
        capture_output=True,
        text=True,
    )


def build_valid_bundle(root: Path, size: tuple[int, int] = (100, 140)) -> None:
    source = rounded_card(size, (25, 60, 100))
    draw = ImageDraw.Draw(source)
    draw.ellipse((25, 25, 75, 108), fill=(210, 75, 145, 255))
    draw.rounded_rectangle(
        (7, 7, 92, 132), radius=5, outline=(238, 238, 230, 255), width=3
    )
    source.save(root / "source.png")

    Image.new("RGBA", size, (25, 60, 100, 255)).save(root / "background.png")

    foreground = source.copy()
    foreground_alpha = Image.new("L", size, 0)
    alpha_draw = ImageDraw.Draw(foreground_alpha)
    alpha_draw.ellipse((25, 25, 75, 108), fill=255)
    alpha_draw.rounded_rectangle(
        (7, 7, 92, 132), radius=5, outline=255, width=3
    )
    foreground_alpha = ImageChops.multiply(
        foreground_alpha, source.getchannel("A")
    )
    foreground.putalpha(foreground_alpha)
    foreground.save(root / "foreground.png")

    structure = Image.new("L", size, 0)
    structure_draw = ImageDraw.Draw(structure)
    structure_draw.ellipse((25, 25, 75, 108), outline=255, width=2)
    structure_draw.rounded_rectangle(
        (7, 7, 92, 132), radius=5, outline=255, width=2
    )
    structure.save(root / "structure.png")
    run_script(
        "prepare_structure_maps.py",
        "--foreground",
        root / "foreground.png",
        "--structure",
        root / "structure.png",
        "--output-contour",
        root / "foreground_contour.png",
        "--output-bloom",
        root / "foreground_bloom.png",
        check=True,
    )


def check_bundle(root: Path, *extra: object) -> subprocess.CompletedProcess[str]:
    return run_script(
        "check_assets.py",
        "--source",
        root / "source.png",
        "--background",
        root / "background.png",
        "--foreground",
        root / "foreground.png",
        "--contour",
        root / "foreground_contour.png",
        "--bloom",
        root / "foreground_bloom.png",
        *extra,
    )


class ScriptTests(unittest.TestCase):
    def test_skill_exposes_only_the_two_layer_contract(self) -> None:
        files = [
            SKILL / "SKILL.md",
            SKILL / "references" / "resource-workflow.md",
            SKILL / "references" / "rendering-contract.md",
            SKILL / "agents" / "openai.yaml",
            SKILL / "assets" / "flutter" / "lib" / "holographic_card.dart",
            SKILL
            / "assets"
            / "flutter"
            / "lib"
            / "holographic_card_painter.dart",
            SKILL
            / "assets"
            / "flutter"
            / "shaders"
            / "holographic_card.frag",
        ]
        contract = "\n".join(path.read_text(encoding="utf-8") for path in files)
        self.assertIn("background -> foreground", contract)
        self.assertIn("foreground_contour.png", contract)
        self.assertIn("uniform sampler2D uForeground;", contract)
        for obsolete in (
            "character.png",
            "uCharacter",
            "uLayeredCharacter",
            "layered-3d",
            "merged-2d",
            "ui-crossing-mode",
            "effect=auto",
        ):
            self.assertNotIn(obsolete, contract)
        self.assertFalse((SCRIPTS / "prepare_generated_character.py").exists())

    def test_normalize_source_requires_and_builds_card_alpha(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.png"
            output = root / "source.png"
            Image.new("RGBA", (50, 70), (20, 40, 60, 255)).save(source)

            rejected = run_script(
                "normalize_source.py",
                "--source",
                source,
                "--output",
                output,
                "--width",
                1000,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("no usable rounded card-shape Alpha", rejected.stderr)

            accepted = run_script(
                "normalize_source.py",
                "--source",
                source,
                "--output",
                output,
                "--width",
                1000,
                "--corner-radius-ratio",
                0.05,
                check=True,
            )
            report = json.loads(accepted.stdout)
            self.assertEqual(report["corner_alphas"], [0, 0, 0, 0])
            with Image.open(output) as normalized:
                self.assertEqual(normalized.size, (1000, 1400))

    def test_prepare_foreground_preserves_all_source_rgb(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = rounded_card((100, 140), (30, 70, 120))
            ImageDraw.Draw(source).ellipse(
                (24, 24, 76, 112), fill=(215, 80, 150, 255)
            )
            source.save(root / "source.png")
            mask = Image.new("L", (200, 280), 0)
            ImageDraw.Draw(mask).ellipse((48, 48, 152, 224), fill=255)
            mask.save(root / "foreground-alpha-mask.png")

            prepared = run_script(
                "prepare_foreground.py",
                "--source",
                root / "source.png",
                "--alpha-mask",
                root / "foreground-alpha-mask.png",
                "--output-foreground",
                root / "foreground.png",
                "--output-mask",
                root / "foreground-alpha.png",
                "--output-black-preview",
                root / "black.png",
                "--output-white-preview",
                root / "white.png",
                "--output-overlay",
                root / "overlay.png",
                check=True,
            )
            report = json.loads(prepared.stdout)
            foreground = Image.open(root / "foreground.png").convert("RGBA")
            self.assertTrue(report["source_rgb_preserved"])
            self.assertEqual(
                source.convert("RGB").tobytes(),
                foreground.convert("RGB").tobytes(),
            )
            self.assertEqual(foreground.getpixel((0, 0))[3], 0)
            self.assertEqual(foreground.getpixel((50, 70))[3], 255)

    def test_lineart_accepts_transparent_white_lines_for_all_foreground(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            foreground = Image.new("RGBA", (100, 140), (0, 0, 0, 0))
            draw = ImageDraw.Draw(foreground)
            draw.ellipse((24, 24, 76, 108), fill=(210, 80, 145, 255))
            draw.rectangle((10, 116, 90, 130), fill=(245, 245, 245, 255))
            foreground.save(root / "foreground.png")

            lineart = Image.new("RGBA", foreground.size, (255, 255, 255, 0))
            line_draw = ImageDraw.Draw(lineart)
            line_draw.ellipse((24, 24, 76, 108), outline=(255, 255, 255, 255), width=2)
            line_draw.rectangle(
                (10, 116, 90, 130), outline=(255, 255, 255, 255), width=2
            )
            lineart.save(root / "lineart.png")

            result = run_script(
                "prepare_generated_lineart.py",
                "--reference",
                root / "foreground.png",
                "--lineart",
                root / "lineart.png",
                "--output-structure",
                root / "structure.png",
                "--output-transparent",
                root / "structure-transparent.png",
                check=True,
            )
            report = json.loads(result.stdout)
            self.assertEqual(report["input_mode"], "transparent_white_lines")
            self.assertGreater(report["strong_line_coverage"], 0)
            self.assertEqual(report["signal_spill_coverage"], 0)

    def test_lineart_rejects_bright_checkerboard_matte(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            foreground = Image.new("RGBA", (100, 140), (0, 0, 0, 0))
            ImageDraw.Draw(foreground).ellipse(
                (24, 24, 76, 108), fill=(210, 80, 145, 255)
            )
            foreground.save(root / "foreground.png")
            checker = Image.new("RGB", foreground.size, (204, 204, 204))
            checker_draw = ImageDraw.Draw(checker)
            for y in range(0, 140, 10):
                for x in range(0, 100, 10):
                    if (x // 10 + y // 10) % 2:
                        checker_draw.rectangle(
                            (x, y, x + 9, y + 9), fill=(255, 255, 255)
                        )
            checker_draw.ellipse((24, 24, 76, 108), outline=255, width=2)
            checker.save(root / "checker.png")

            result = run_script(
                "prepare_generated_lineart.py",
                "--reference",
                root / "foreground.png",
                "--lineart",
                root / "checker.png",
                "--output-structure",
                root / "structure.png",
            )
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertIn(
                "Opaque line art must use a uniform solid-black matte; bright or checkerboard matte detected",
                report["errors"],
            )

    def test_structure_maps_create_a_real_halo_outside_the_core(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            foreground = Image.new("RGBA", (100, 140), (200, 80, 140, 0))
            ImageDraw.Draw(foreground).rectangle(
                (15, 15, 84, 124), fill=(200, 80, 140, 255)
            )
            foreground.save(root / "foreground.png")
            structure = Image.new("L", foreground.size, 0)
            ImageDraw.Draw(structure).line((50, 30, 50, 110), fill=255, width=1)
            structure.save(root / "structure.png")

            run_script(
                "prepare_structure_maps.py",
                "--foreground",
                root / "foreground.png",
                "--structure",
                root / "structure.png",
                "--output-contour",
                root / "foreground_contour.png",
                "--output-bloom",
                root / "foreground_bloom.png",
                check=True,
            )
            contour = Image.open(root / "foreground_contour.png").convert("RGBA")
            bloom = Image.open(root / "foreground_bloom.png").convert("RGBA")
            self.assertEqual(contour.getpixel((45, 70))[0], 0)
            self.assertGreater(bloom.getpixel((49, 70))[0], 0)
            self.assertGreater(bloom.getpixel((48, 70))[1], 0)

    def test_check_assets_accepts_valid_bundle_and_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_valid_bundle(root)
            result = check_bundle(
                root, "--output-report", root / "check-report.json"
            )
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(report["ok"])
            self.assertTrue(report["source_rgb_preserved"])
            self.assertTrue((root / "check-report.json").is_file())

    def test_check_assets_rejects_changed_foreground_rgb(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_valid_bundle(root)
            foreground = Image.open(root / "foreground.png").convert("RGBA")
            foreground.putpixel((50, 70), (1, 2, 3, 255))
            foreground.save(root / "foreground.png")
            result = check_bundle(root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "Foreground RGB differs from the normalized source",
                json.loads(result.stdout)["errors"],
            )

    def test_check_assets_reports_canvas_mismatch_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_valid_bundle(root)
            Image.new("RGBA", (101, 140), (0, 0, 0, 255)).save(
                root / "foreground_contour.png"
            )
            result = check_bundle(root)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertIn("Canvas mismatch", report["errors"][0])
            self.assertNotIn("Traceback", result.stderr)

    def test_check_assets_rejects_transparent_background(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_valid_bundle(root)
            background = Image.open(root / "background.png").convert("RGBA")
            background.putpixel((0, 0), (25, 60, 100, 0))
            background.save(root / "background.png")
            result = check_bundle(root)
            self.assertIn(
                "Background must be opaque across the complete full-bleed canvas",
                json.loads(result.stdout)["errors"],
            )

    def test_check_assets_rejects_contour_outside_foreground(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_valid_bundle(root)
            contour = Image.open(root / "foreground_contour.png").convert("RGBA")
            contour.putpixel((50, 15), (255, 255, 255, 255))
            contour.save(root / "foreground_contour.png")
            result = check_bundle(root)
            self.assertIn(
                "Contour spills outside its foreground owner",
                json.loads(result.stdout)["errors"],
            )

    def test_cleanup_keeps_only_five_runtime_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "source.png",
                "background.png",
                "foreground.png",
                "foreground_contour.png",
                "foreground_bloom.png",
            ):
                (root / name).write_bytes(b"runtime")
            (root / "alignment-overlay.png").write_bytes(b"temporary")
            (root / "foreground-report.json").write_bytes(b"temporary")
            unrelated = root / "notes.txt"
            unrelated.write_text("keep", encoding="utf-8")

            result = run_script(
                "cleanup_assets.py", "--output-dir", root, check=True
            )
            report = json.loads(result.stdout)
            self.assertEqual(
                set(report["kept"]),
                {
                    "source.png",
                    "background.png",
                    "foreground.png",
                    "foreground_contour.png",
                    "foreground_bloom.png",
                },
            )
            self.assertFalse((root / "alignment-overlay.png").exists())
            self.assertFalse((root / "foreground-report.json").exists())
            self.assertTrue(unrelated.is_file())


if __name__ == "__main__":
    unittest.main()
