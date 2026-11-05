"""
Yoru - NEW SPRINT, round 2 sheet (system python, Pillow):
  python build_sprint_r2_sheet.py <frames dir> <out dir> [rows, default ALT,S,M,L]
ONE sheet: 12 pictures over ONE cycle (every 3rd frame of 36 at 60 fps = every 0.05 s) from her right side (orthographic, in place), one row
per variant (ALT = the old sprint, S, M, L).  Writes <out dir>/sheet_r2_side.png.
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

FR, OUT = sys.argv[1], sys.argv[2]
VARS = sys.argv[3].split(',') if len(sys.argv) > 3 else ['ALT', 'S', 'M', 'L']
os.makedirs(OUT, exist_ok=True)
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)
TITLE = {'ALT': 'ALT', 'S': 'S +-20', 'M': 'M +-32', 'L': 'L +-42'}
FRAMES = list(range(0, 36, 3))
PHASE = {0: 'R setzt auf', 3: 'R Stand', 6: 'R Stand', 9: 'Flug', 12: 'Flug', 15: 'Flug', 18: 'L setzt auf', 21: 'L Stand', 24: 'L Stand',
         27: 'Flug', 30: 'Flug', 33: 'Flug'}
H_ROW = 400
rows = []
for v in VARS:
    ims = []
    for f in FRAMES:
        im = Image.open(os.path.join(FR, '%s_side' % v, 'side_%03d.png' % f)).convert('RGB')
        ims.append(im.resize((round(im.width * H_ROW / im.height), H_ROW), Image.LANCZOS))
    rows.append((v, ims))
cw = max(im.width for _, r in rows for im in r)
LW = 112
W, H = LW + cw * len(FRAMES), 40 + len(rows) * (H_ROW + 24) + 6
g = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(g)
d.text((10, 8), 'Sprint Runde 2, von rechts, ein Zyklus (0,60 s), alle 0,05 s.  Nur die Groesse des Armschwungs unterscheidet sich.', fill=(255, 226, 120), font=F_B)
for r, (v, ims) in enumerate(rows):
    y = 40 + r * (H_ROW + 24)
    d.text((8, y + H_ROW // 2 - 10), TITLE[v], fill=(255, 226, 120), font=F_B)
    for i, (f, im) in enumerate(zip(FRAMES, ims)):
        g.paste(im, (LW + i * cw + (cw - im.width) // 2, y))
        if r == len(rows) - 1:
            d.text((LW + i * cw + 6, y + H_ROW + 3), 'Bild %d  %s' % (f, PHASE[f]), fill=(150, 220, 255), font=F)
p = os.path.join(OUT, 'sheet_r2_side.png')
g.save(p)
print('sheet', p, g.size, flush=True)
