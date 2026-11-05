"""
Yoru - NEW SPRINT, round 3: NTE against our figure at the same phases (system python, Pillow).
  python build_sprint_r3_nte.py <frames_r3 dir> <ref_nte dir> <out png>
Phase k/6 of the cycle, k = 0..5 (0 = the right foot touches down).  NTE (30 fps, 20 frames per cycle): side clip, right foot down at f110.5 ->
f110, 114, 117, 100, 104, 107; back clip, right foot down at about f59.5 -> f60, 63, 66, 70, 73, 76.  Ours (60 fps, 36 frames): 0, 6, 12, 18, 24, 30.
Rows: NTE side | P1 side | P2 side | NTE from behind | P1 from behind (game camera) | P2 from behind.  The NTE strips are 5 x 4 tiles.
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

FR, REF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)
H = 300
OURS = [0, 6, 12, 18, 24, 30]
NTE = {'side': ('NTE_lauf_seite_zyklus_f100-119.jpg', 100, [110, 114, 117, 100, 104, 107]),
       'back': ('NTE_lauf_hinten_zyklus_f60-79.jpg', 60, [60, 63, 66, 70, 73, 76])}


def tile(view, f):
    name, f0, _ = NTE[view]
    im = Image.open(os.path.join(REF, name)).convert('RGB')
    tw, th = im.width / 5.0, im.height / 4.0
    i = f - f0
    r, c = divmod(i, 5)
    return im.crop((round(c * tw), round(r * th), round((c + 1) * tw), round((r + 1) * th)))


def fit(im):
    return im.resize((round(im.width * H / im.height), H), Image.LANCZOS)


rows = []
for view, our_sub in (('side', 'side'), ('back', 'back')):
    rows.append(('NTE ' + ('Seite' if view == 'side' else 'hinten'), [fit(tile(view, f)) for f in NTE[view][2]], ['f%d' % f for f in NTE[view][2]]))
    for v in ('P1', 'P2'):
        pat = 'side_%03d.png' if view == 'side' else 'game_%03d.png'
        rows.append(('%s %s' % (v, 'Seite' if view == 'side' else 'hinten'), [fit(Image.open(os.path.join(FR, '%s_%s' % (v, our_sub), pat % f)).convert('RGB')) for f in OURS],
                     ['Bild %d' % f for f in OURS]))
cw = max(im.width for _, r, _ in rows for im in r)
LW = 130
W, Ht = LW + cw * 6, 44 + len(rows) * (H + 22)
g = Image.new('RGB', (W, Ht), BG)
d = ImageDraw.Draw(g)
d.text((10, 10), 'NTE gegen Yoru (Runde 3), gleiche Phasen: Spalte k = k/6 Zyklus, 0 = rechter Fuß setzt auf', fill=(255, 226, 120), font=F_B)
for r, (label, ims, names) in enumerate(rows):
    y = 44 + r * (H + 22)
    d.text((8, y + H // 2 - 10), label, fill=(255, 226, 120), font=F_B)
    for i, im in enumerate(ims):
        g.paste(im, (LW + i * cw + (cw - im.width) // 2, y))
        d.text((LW + i * cw + 6, y + H + 2), names[i], fill=(150, 220, 255), font=F)
g.save(OUT)
print('nte sheet', OUT, g.size, flush=True)
