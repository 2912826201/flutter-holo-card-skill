"""Recorded, card-specific mask repair; not a general semantic segmentation algorithm."""

from pathlib import Path
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

p = Path(__file__).resolve().parent
source = Image.open(p.parents[1] / "assets/card/source.png").convert("RGBA")
raw = Image.open(p / "raw-mask.png").convert("L")
if abs(raw.width / raw.height / (source.width / source.height) - 1) > 0.01:
    raise ValueError("Mask aspect mismatch")
mask = raw.resize(source.size, Image.Resampling.LANCZOS).point(
    lambda v: 255 if v >= 128 else 0
)
# Printed panels are surfaces, not individual glyph holes. Coordinates on 1000x1397 source.
d = ImageDraw.Draw(mask)
d.polygon([(0, 0), (185, 0), (185, 101), (156, 122), (156, 234), (0, 234)], fill=255)
d.rectangle((0, 232, 78, 790), fill=255)
d.rectangle((35, 986, 967, 1102), fill=255)
d.polygon([(0, 1218), (1000, 1218), (1000, 1397), (0, 1397)], fill=255)
# Fill small interior black islands (dark armor seams/barrels), retain large true limb gaps.
a = np.asarray(mask).copy()
seen = np.zeros(a.shape, bool)
h, w = a.shape
for yy, xx in zip(*np.where(a == 0)):
    if seen[yy, xx]:
        continue
    queue = deque([(yy, xx)])
    seen[yy, xx] = True
    component = []
    boundary = False
    while queue:
        y, x = queue.popleft()
        component.append((y, x))
        boundary |= y in (0, h - 1) or x in (0, w - 1)
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and a[ny, nx] == 0:
                seen[ny, nx] = True
                queue.append((ny, nx))
    if not boundary and len(component) < 1800:
        ys, xs = zip(*component)
        a[ys, xs] = 255
mask = Image.fromarray(a)
d = ImageDraw.Draw(mask)
# Rear green robot's body is a filled foreground surface, including outline-only armor.
d.polygon(
    [
        (610, 115),
        (680, 154),
        (705, 218),
        (680, 263),
        (650, 281),
        (625, 365),
        (579, 397),
        (538, 342),
        (470, 279),
        (436, 322),
        (435, 413),
        (395, 443),
        (278, 420),
        (270, 393),
        (310, 300),
        (325, 263),
        (362, 247),
        (378, 197),
    ],
    fill=255,
)
d.rectangle((925, 0, 999, 1396), fill=255)
d.rectangle((0, 0, 85, 1396), fill=255)
d.rectangle((0, 0, 999, 27), fill=255)
d.polygon(
    [(0, 970), (335, 730), (470, 765), (252, 979), (90, 1070), (0, 1130)], fill=255
)
d.polygon(
    [(630, 80), (747, 151), (745, 294), (677, 387), (570, 417), (576, 275)], fill=255
)
d.polygon(
    [(849, 1110), (999, 1070), (999, 1396), (0, 1396), (0, 1210), (793, 1210)], fill=255
)
mask = mask.filter(ImageFilter.MaxFilter(5))
d = ImageDraw.Draw(mask)
d.rectangle((0, 0, 999, 1396), outline=255, width=3)
mask.save(p / "owner-mask.png")
overlay = source.copy()
tint = Image.new("RGBA", source.size, (255, 40, 110, 0))
tint.putalpha(mask.point(lambda v: round(v * 0.30)))
overlay.alpha_composite(tint)
overlay.save(p / "owner-overlay.png")
fg = source.copy()
fg.putalpha(mask)
fg.save(p / "foreground-preview.png")
bg = Image.open(p / "clean-background.png").convert("RGBA")
if abs(bg.width / bg.height / (1160 / 1621) - 1) > 0.01:
    raise ValueError("Background aspect mismatch")
bg.resize((1160, 1621), Image.Resampling.LANCZOS).save(p / "extended-background.png")
