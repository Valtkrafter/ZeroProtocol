"""Walk v2, round 2: strips of 10 pictures over one gait cycle for Alt, Neu, Neu+ (rows: front three-quarter, game camera), one below the other.
usage: python build_walk_v2_strips.py <frames dir with Alt/, Neu/, NeuPlus/> <out png>
Alt has 21 frames per cycle, Neu / Neu+ 29: the 10 pictures are spread evenly over each cycle."""
import sys, os
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
ROWS = [('Alt', 'Alt  (0,70 s, 1,5 m/s, bisher in Unity)', 21), ('Neu', 'Neu  (0,97 s, 1,2 m/s)', 29), ('NeuPlus', 'Neu+  (0,97 s, 1,2 m/s, mehr Swagger)', 29)]
VIEWS = (('front34', 'vorn schräg'), ('game', 'Spielkamera'))
CROP = (60, 20, 360, 500)            # of 420 x 504 (70 %)
cw, ch, head = 200, 320, 34
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
im = Image.new('RGB', (cw * 10, len(ROWS) * (head + 2 * ch)), (20, 22, 27))
d = ImageDraw.Draw(im)
for j, (key, title, nf) in enumerate(ROWS):
    y0 = j * (head + 2 * ch)
    d.text((8, y0 + 6), title, fill=(255, 226, 120), font=F_B)
    frames = [int(round(i * nf / 10.0)) % nf for i in range(10)]
    for v, (view, vname) in enumerate(VIEWS):
        for i, f in enumerate(frames):
            a = Image.open(os.path.join(src, key, '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP).resize((cw, ch))
            im.paste(a, (i * cw, y0 + head + v * ch))
        d.text((6, y0 + head + v * ch + 4), vname, fill=(200, 210, 225), font=F)
    for i, f in enumerate(frames):
        d.text((i * cw + 6, y0 + head + 2 * ch - 22), 'Bild %d' % f, fill=(225, 230, 240), font=F)
im.save(out)
print('strips', out, im.size)
