from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
p=Path(__file__).parent
source=Image.open(p/'source.png').convert('RGBA')
raw=Image.open(p/'raw-mask.png').convert('L')
assert abs((raw.width/raw.height)/(450/629)-1)<.01
mask=np.array(raw.resize(source.size,Image.Resampling.LANCZOS))>=128
# Black printed border, panels and emblems belong to the fixed card plane.
window=Image.new('L',source.size,0)
ImageDraw.Draw(window).polygon([(96,43),(352,41),(371,87),(403,98),(411,123),(416,190),(413,279),(420,346),(42,346),(38,307),(39,198),(32,143),(50,128),(53,91),(83,77)],fill=255)
mask |= np.array(window)==0
mask[326:348,42:86]=True # red spell label
im=Image.fromarray((mask*255).astype('uint8')).filter(ImageFilter.MaxFilter(5))
im.save(p/'owner-mask.png')
over=Image.new('RGBA',source.size,(255,30,100,0));over.putalpha(im.point(lambda x:int(x*.30)))
Image.alpha_composite(source,over).save(p/'owner-overlay.png')
