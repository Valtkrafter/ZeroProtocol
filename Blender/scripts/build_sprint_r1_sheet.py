"""
Yoru - NEW SPRINT, round 1 sheets (system python, Pillow):
  python build_sprint_r1_sheet.py <frames dir> <out dir> [variants, default A,B,C]
Per variant one sheet: 12 pictures over ONE cycle (every 3rd frame of 36 at 60 fps = every 0.05 s), top row from behind at the game camera's
angle (rendered at 3840 x 2160 inside a window), bottom row from her right side (orthographic, in place).  Writes <out dir>/sheet_<V>.png.
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

FR, OUT = sys.argv[1], sys.argv[2]
VARS = sys.argv[3].split(',') if len(sys.argv) > 3 else ['A', 'B', 'C']
os.makedirs(OUT, exist_ok=True)
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)
TITLE = {'A': 'A  nah und tief', 'B': 'B  weiches Mitschwingen', 'C': 'C  tief und hinten', 'ALT': 'ALT (bisheriger Sprint)'}
FRAMES = list(range(0, 36, 3))
PHASE = {0: 'R setzt auf', 3: 'R Stand', 6: 'R Stand', 9: 'Flug', 12: 'Flug', 15: 'Flug', 18: 'L setzt auf', 21: 'L Stand', 24: 'L Stand',
         27: 'Flug', 30: 'Flug', 33: 'Flug'}
H_ROW = 380
for v in VARS:
    rows = []
    for sub, pat in (('back', 'game_%03d.png'), ('side', 'side_%03d.png')):
        ims = []
        for f in FRAMES:
            im = Image.open(os.path.join(FR, '%s_%s' % (v, sub), pat % f)).convert('RGB')
            ims.append(im.resize((round(im.width * H_ROW / im.height), H_ROW), Image.LANCZOS))
        rows.append(ims)
    cw = max(im.width for r in rows for im in r)
    W, H = cw * len(FRAMES), 40 + 2 * (H_ROW + 26) + 10
    g = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(g)
    d.text((10, 8), '%s   ein Zyklus (0,60 s), alle 0,05 s   oben: von hinten (Spielkamera)   unten: von rechts' % TITLE[v], fill=(255, 226, 120), font=F_B)
    for r, ims in enumerate(rows):
        y = 40 + r * (H_ROW + 26)
        for i, (f, im) in enumerate(zip(FRAMES, ims)):
            g.paste(im, (i * cw + (cw - im.width) // 2, y))
            d.text((i * cw + 6, y + H_ROW + 4), 'Bild %d  %s' % (f, PHASE[f]), fill=(150, 220, 255), font=F)
    p = os.path.join(OUT, 'sheet_%s.png' % v)
    g.save(p)
    print('sheet', p, g.size, flush=True)
