"""Walk v2, round 4: close-up strips of the upper body, 12 pictures over one gait cycle (25 frames), for R3, R4a, R4b one below the other
(rows: front three-quarter close-up 'upper34', side close-up 'upperSide').
usage: python build_walk_v2_strips_r4.py <frames dir with R3/, R4a/, R4b/> <out png>"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
NF = 25
ROWS = [('R3', 'R3  (Runde 3, Neu 0,83)'), ('R4a', 'R4a  fliessend'), ('R4b', 'R4b  kompakt')]
VIEWS = (('upper34', 'Nahaufnahme vorn schräg'), ('upperSide', 'Nahaufnahme Seite'))
CROP = (40, 30, 380, 470)            # of 420 x 504 (70 %)
cw, ch, head = 170, 220, 34
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 14)
frames = [int(round(i * NF / 12.0)) % NF for i in range(12)]
im = Image.new('RGB', (cw * 12, len(ROWS) * (head + 2 * ch)), (20, 22, 27))
d = ImageDraw.Draw(im)
for j, (key, title) in enumerate(ROWS):
    y0 = j * (head + 2 * ch)
    d.text((8, y0 + 6), title, fill=(255, 226, 120), font=F_B)
    for v, (view, vname) in enumerate(VIEWS):
        for i, f in enumerate(frames):
            a = Image.open(os.path.join(src, key, '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP).resize((cw, ch))
            im.paste(a, (i * cw, y0 + head + v * ch))
        d.text((6, y0 + head + v * ch + 4), vname, fill=(200, 210, 225), font=F)
    for i, f in enumerate(frames):
        d.text((i * cw + 6, y0 + head + 2 * ch - 20), 'Bild %d' % f, fill=(225, 230, 240), font=F)
im.save(out)
print('strips', out, im.size)
