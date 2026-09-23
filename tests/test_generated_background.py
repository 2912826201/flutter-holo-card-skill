from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/build-flutter-holo-card/scripts/prepare_generated_background.py"
)


class GeneratedBackgroundTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.png"
        self.generated = self.root / "generated.png"
        self.output = self.root / "extended.png"
        self.report = self.root / "normalization.json"
        Image.new("RGBA", (100, 140), (30, 50, 70, 255)).save(self.source)

    def execute(self, mode="height"):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--mode",
                mode,
                "--source",
                str(self.source),
                "--generated",
                str(self.generated),
                "--output",
                str(self.output),
                "--report",
                str(self.report),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_resizes_entire_opaque_generated_canvas_and_reports_binding(self):
        image = Image.new("RGB", (232, 328), (20, 30, 40))
        drawing = ImageDraw.Draw(image)
        colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))
        boxes = ((0, 0, 30, 30), (201, 0, 231, 30),
                 (0, 297, 30, 327), (201, 297, 231, 327))
        for box, color in zip(boxes, colors):
            drawing.rectangle(box, fill=color)
        image.save(self.generated)

        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(self.report.read_text())
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["source_rect_pixels"], [8, 12, 100, 140])
        self.assertEqual(report["generated_canvas"], [232, 328])
        self.assertEqual(report["output_canvas"], [116, 164])
        self.assertEqual(report["normalization"], "whole-canvas-lanczos")
        self.assertIn(str(self.source.resolve()), report["inputs"])
        self.assertIn(str(self.generated.resolve()), report["inputs"])
        with Image.open(self.output) as normalized:
            self.assertEqual(normalized.mode, "RGB")
            self.assertEqual(normalized.size, (116, 164))
            for point, color in zip(((0, 0), (115, 0), (0, 163), (115, 163)), colors):
                self.assertEqual(normalized.getpixel(point), color)

    def test_exact_canvas_preserves_pixels_and_opaque_rgba(self):
        Image.new("RGBA", (116, 164), (47, 89, 131, 255)).save(self.generated)
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with Image.open(self.output) as normalized:
            self.assertEqual(normalized.mode, "RGBA")
            self.assertEqual(normalized.getpixel((80, 90)), (47, 89, 131, 255))
        self.assertEqual(json.loads(self.report.read_text())["normalization"], "none")

    def test_bad_aspect_removes_stale_success_file_and_writes_only_diagnostic(self):
        Image.new("RGB", (116, 164), (30, 40, 50)).save(self.generated)
        self.assertEqual(self.execute().returncode, 0)
        self.assertTrue(self.output.exists())
        Image.new("RGB", (1024, 1024), (30, 40, 50)).save(self.generated)
        failed = self.execute()
        self.assertEqual(failed.returncode, 1)
        self.assertFalse(self.output.exists())
        report = json.loads(self.report.read_text())
        self.assertEqual(report["status"], "failed")
        self.assertIn("aspect ratio", report["error"])

    def test_transparency_and_cross_mode_are_rejected(self):
        Image.new("RGBA", (116, 164), (30, 40, 50, 254)).save(self.generated)
        self.assertEqual(self.execute().returncode, 1)
        self.assertFalse(self.output.exists())
        self.assertIn("fully opaque", json.loads(self.report.read_text())["error"])
        Image.new("RGB", (116, 164), (30, 40, 50)).save(self.generated)
        self.assertEqual(self.execute("medium").returncode, 1)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
