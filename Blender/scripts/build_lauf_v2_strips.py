"""Lauf v2: dense strip of Yoru like the NTE strips: every frame of ONE cycle at 30 fps (= every second frame of the 60 fps clip), 5 columns x 4
rows, frame numbers in yellow (30 fps index and, in brackets, the 60 fps frame).
usage: python build_lauf_v2_strips.py <frames dir (with Neu/)> <view> <first 60 fps frame> <out png> [key] [scale]"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

src, view, f0, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
key = sys.argv[5] if len(sys.argv) > 5 else 'Neu'
scale = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
NF = 40
F = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
ims = []
for k in range(20):
    f = (f0 + 2 * k) % NF
    a = Image.open(os.path.join(src, key, '%s_%03d.png' % (view, f))).convert('RGB')
    if scale != 1.0:
        a = a.resize((int(a.width * scale), int(a.height * scale)))
    d = ImageDraw.Draw(a)
    d.text((6, 4), '%d  (f%d)' % (k, f), fill=(255, 255, 0), font=F)
    ims.append(a)
w, h = ims[0].size
sheet = Image.new('RGB', (5 * w, 4 * h), (0, 0, 0))
for k, a in enumerate(ims):
    r, c = divmod(k, 5)
    sheet.paste(a, (c * w, r * h))
sheet.save(out)
print('strip', out, sheet.size)
