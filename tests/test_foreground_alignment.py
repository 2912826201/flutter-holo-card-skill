"""Generated geometry must survive adaptation unchanged, including imperfect edges."""
import argparse
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/build-flutter-holo-card/scripts"))
import prepare_foreground


class ForegroundTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.args = argparse.Namespace(mode="height", source=self.root / "source.png",
            generated=self.root / "generated.png", mask=self.root / "mask.png",
            overlay=self.root / "overlay.png", generated_kind="alpha")
        Image.new("RGBA", (100, 140), (10, 20, 30, 255)).save(self.args.source)

    def test_soft_alpha_inset_and_one_pixel_gap_are_preserved_not_repaired(self):
        cutout = Image.new("RGBA", (100, 140), (200, 0, 0, 0))
        d = ImageDraw.Draw(cutout)
        d.rectangle((4, 6, 95, 138), fill=(200, 0, 0, 255))
        d.line((4, 6, 4, 138), fill=(200, 0, 0, 130))
        cutout.save(self.args.generated)
        prepare_foreground.run(self.args)
        self.assertEqual(Image.open(self.args.mask).tobytes(), cutout.getchannel("A").tobytes())
        self.assertEqual(Image.open(self.args.mask).getpixel((50, 139)), 0)

    def test_generated_matte_is_read_without_local_segmentation(self):
        matte = Image.new("L", (100, 140), 0)
        ImageDraw.Draw(matte).rectangle((20, 20, 80, 120), fill=255)
        matte.save(self.args.generated)
        self.args.generated_kind = "mask"
        prepare_foreground.run(self.args)
        self.assertEqual(Image.open(self.args.mask).tobytes(), matte.tobytes())

    def test_full_canvas_resize_preserves_composition(self):
        cutout = Image.new("RGBA", (200, 280), (200, 0, 0, 0))
        ImageDraw.Draw(cutout).rectangle((40, 40, 160, 240), fill=(200, 0, 0, 255))
        cutout.save(self.args.generated)
        prepare_foreground.run(self.args)
        expected = cutout.getchannel("A").resize((100, 140), Image.Resampling.LANCZOS)
        self.assertTrue(np.array_equal(np.asarray(Image.open(self.args.mask)), np.asarray(expected)))

    def test_opaque_cutout_and_wrong_aspect_still_fail(self):
        Image.new("RGBA", (100, 140), (50, 60, 70, 255)).save(self.args.generated)
        with self.assertRaisesRegex(ValueError, "separation"):
            prepare_foreground.run(self.args)
        Image.new("RGBA", (100, 100), (50, 60, 70, 0)).save(self.args.generated)
        with self.assertRaisesRegex(ValueError, "aspect"):
            prepare_foreground.run(self.args)
