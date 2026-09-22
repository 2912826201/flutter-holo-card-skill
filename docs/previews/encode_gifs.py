"""Encode deterministic Flutter drag recordings with one palette per animation."""
from pathlib import Path
from PIL import Image, ImageDraw
root = Path(__file__).resolve().parents[2]
frames_root = root / 'examples/akali_card/build/readme-frames'
for mode in ['height', 'medium', 'low']:
    frames = [Image.open(p).convert('RGB') for p in sorted((frames_root / mode).glob('*.png'))]
    assert len(frames) == 72
    atlas = Image.new('RGB', (360 * 12, 480))
    for i, frame in enumerate(frames[::6]):
        atlas.paste(frame, (360 * i, 0))
    palette = atlas.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    quantized = [frame.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for frame in frames]
    target = Path(__file__).parent / f'{mode}.gif'
    quantized[0].save(target, save_all=True, append_images=quantized[1:],
                      duration=[70 if i % 3 else 60 for i in range(72)], loop=0, optimize=False, disposal=1)
    with Image.open(target) as gif:
        assert gif.is_animated and gif.info['loop'] == 0
        print(mode, gif.n_frames, 'frames', round(target.stat().st_size / 1024), 'KiB')
# QA contact sheet uses uncompressed recording frames.
sheet = Image.new('RGB', (360*4, 500*3), '#101716')
draw = ImageDraw.Draw(sheet)
for row, mode in enumerate(['height','medium','low']):
    for col, frame in enumerate([0,18,36,54]):
        sheet.paste(Image.open(frames_root / mode / f'{frame:03}.png'), (col*360,row*500+20))
        draw.text((col*360+10,row*500+3),f'{mode} / frame {frame}',fill='white')
sheet.save(frames_root / 'contact-sheet.jpg')
