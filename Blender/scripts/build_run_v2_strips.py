"""Run v2 (polish of the old sprint): dense strip of ONE cycle, every second 60 fps frame (= every frame at 30 fps like the NTE strips),
frame numbers in yellow.  Tiles come from <frames dir>/<key>/<view>_<frame:03d>.png (rendered by build_lauf_v2_render.py).
usage: python -I build_run_v2_strips.py <frames dir> <key> <view> <out png> [cols=6] [scale=1.0] [nf=36] [step=2]
A second key after a plus sign (e.g. 'Alt+Neu') stacks the rows of both keys one above the other (before / after), same frames."""
import sys, os
from PIL import Image, ImageDraw, ImageFont

src, key, view, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 6
scale = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
NF = int(sys.argv[7]) if len(sys.argv) > 7 else 36
STEP = int(sys.argv[8]) if len(sys.argv) > 8 else 2
F = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 18)
keys = key.split('+')
frames = list(range(0, NF, STEP))


def tile(k, f):
    a = Image.open(os.path.join(src, k, '%s_%03d.png' % (view, f))).convert('RGB')
    if scale != 1.0:
        a = a.resize((int(a.width * scale), int(a.height * scale)))
    d = ImageDraw.Draw(a)
    d.text((6, 4), '%s %d' % (k if len(keys) > 1 else '', f), fill=(255, 255, 0), font=F)
    return a


w, h = tile(keys[0], frames[0]).size
rows = (len(frames) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w, rows * h * len(keys)), (0, 0, 0))
for r in range(rows):
    for ki, k in enumerate(keys):
        for c in range(cols):
            i = r * cols + c
            if i < len(frames):
                sheet.paste(tile(k, frames[i]), (c * w, (r * len(keys) + ki) * h))
sheet.save(out)
print('strip', out, sheet.size)
