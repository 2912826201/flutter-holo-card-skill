from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "build-flutter-holo-card" / "scripts"


class ScriptTests(unittest.TestCase):
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
