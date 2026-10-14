"""Four contact sheets (front, side, back, top) of the classic walk poses for both steps.
usage: python walk_sheets.py <stills dir> <out dir> [frames, comma separated; default for 28 frames: 0,3,7,11,14,17,21,25]
The stills must exist as <view>_<frame>.png (made by render_walk_stills.py)."""
import sys, os
from PIL import Image, ImageDraw

d, out = sys.argv[1], sys.argv[2]
frames = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else [0, 3, 7, 10, 13, 16, 20, 23]
names = ['Contact', 'Down', 'Passing', 'Up']
os.makedirs(out, exist_ok=True)
crops = {'front': (110, 30, 510, 700), 'side': (90, 30, 560, 700), 'side_wide': (0, 40, 600, 700), 'back': (110, 30, 510, 700), 'top': (60, 60, 540, 700)}
for view in ('front', 'side', 'side_wide', 'back', 'top'):
    ims = []
    for i, f in enumerate(frames):
        fn = os.path.join(d, '%s_%03d.png' % (view, f))
        if not os.path.exists(fn):
            continue
        im = Image.open(fn).convert('RGB').crop(crops[view])
        ImageDraw.Draw(im).text((8, 6), '%s  frame %d  (%s %s)' % (view, f, names[i % 4], 'R' if i < 4 else 'L'), fill=(255, 255, 255))
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
