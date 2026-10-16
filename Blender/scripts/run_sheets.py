"""Contact sheets (front, side, back, top) of the key poses of the run for both steps.
usage: python run_sheets.py <stills dir> <out dir> [frames, comma separated; default for 36 frames: 0,4,8,13,18,22,26,31]
The stills must exist as <view>_<frame>.png (made by render_walk_stills.py).  Pose names: touchdown, mid stance, toe off, flight (right step, then left)."""
import sys, os
from PIL import Image, ImageDraw, ImageFont

d, out = sys.argv[1], sys.argv[2]
frames = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [0, 4, 8, 13, 18, 22, 26, 31]
names = ['Aufsetzen', 'Stütze', 'Absprung', 'Flug']
try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
except Exception:
    FONT = ImageFont.load_default()
os.makedirs(out, exist_ok=True)
crops = {'front': (110, 30, 510, 700), 'side_wide': (0, 40, 600, 700), 'back': (110, 30, 510, 700), 'top': (60, 60, 540, 700)}
for view in crops:
    ims = []
    for i, f in enumerate(frames):
        fn = os.path.join(d, '%s_%03d.png' % (view, f))
        if not os.path.exists(fn):
            continue
        im = Image.open(fn).convert('RGB').crop(crops[view])
        ImageDraw.Draw(im).text((8, 6), '%s  Bild %d  (%s %s)' % (view, f, names[i % 4], 'rechts' if i < 4 else 'links'), fill=(255, 255, 255), font=FONT)
        ims.append(im)
    if not ims:
        continue
    cols = 4
    rows = (len(ims) + cols - 1) // cols
    w, h = ims[0].size
    sheet = Image.new('RGB', (w * cols, h * rows))
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * w, (k // cols) * h))
    path = os.path.join(out, 'sheet_%s.png' % view)
    sheet.save(path)
    print(path, sheet.size)
