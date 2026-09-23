import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/build-flutter-holo-card/scripts'
sys.path.insert(0, str(SCRIPTS))
import prepare_generated_lineart


class GeneratedSketchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.args = argparse.Namespace(mode='medium', source=self.root/'source.png',
            generated=self.root/'generated.png', output=self.root/'guide.png', polarity='light')
        Image.new('RGB', (100, 140), 'gray').save(self.args.source)

    def test_sketch_brightness_and_soft_lines_are_preserved(self):
        sketch = Image.new('L', (100, 140), 0)
        d = ImageDraw.Draw(sketch)
        d.line((30, 30, 70, 100), fill=160, width=2)
        sketch.save(self.args.generated)
        prepare_generated_lineart.run(self.args)
        self.assertEqual(Image.open(self.args.output).tobytes(), sketch.tobytes())

    def test_black_on_white_is_only_inverted_not_traced(self):
        sketch = Image.new('L', (100, 140), 255)
        ImageDraw.Draw(sketch).line((30, 30, 70, 100), fill=30, width=2)
        sketch.save(self.args.generated)
        self.args.polarity = 'dark'
        prepare_generated_lineart.run(self.args)
        self.assertEqual(Image.open(self.args.output).getpixel((30, 30)), 225)
        self.assertEqual(Image.open(self.args.output).getpixel((0, 0)), 0)

    def test_empty_sketch_fails(self):
        Image.new('L', (100, 140), 0).save(self.args.generated)
        with self.assertRaisesRegex(ValueError, 'empty'):
            prepare_generated_lineart.run(self.args)

    def test_retired_guide_does_not_generate_or_modify_images(self):
        result = subprocess.run([sys.executable, str(SCRIPTS/'prepare_background_guide.py'),
            '--output', str(self.args.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.args.output.exists())
