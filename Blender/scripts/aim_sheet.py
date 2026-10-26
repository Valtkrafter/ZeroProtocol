"""Comparison sheet of the aim pose stills (cropped around the character).
usage: python aim_sheet.py <aim dir with stills_<V>/> <out png> <variants, e.g. A,B,C> <views, e.g. front34,side> [cell width, default 300] [frame, default 0] [layout: rows|cols, default rows]
layout rows: one row per variant, one column per view.   layout cols: one column per variant, one row per view.
Needs Pillow (system python, not Blender)."""
import sys, os
from PIL import Image, ImageDraw

d, out, variants, views = sys.argv[1], sys.argv[2], sys.argv[3].split(','), sys.argv[4].split(',')
cw = int(sys.argv[5]) if len(sys.argv) > 5 else 300
frame = int(sys.argv[6]) if len(sys.argv) > 6 else 0
layout = sys.argv[7] if len(sys.argv) > 7 else 'rows'
CROP = (60, 40, 560, 680)                       # around the character in the 600 x 720 stills
ch = round(cw * (CROP[3] - CROP[1]) / (CROP[2] - CROP[0]))
head = 22
nc, nr = (len(views), len(variants)) if layout == 'rows' else (len(variants), len(views))
sheet = Image.new('RGB', (cw * nc, (ch + head) * nr), (20, 22, 26))
dr = ImageDraw.Draw(sheet)
for ri, v in enumerate(variants):
    for ci, view in enumerate(views):
        im = Image.open(os.path.join(d, 'stills_%s' % v, '%s_%03d.png' % (view, frame))).convert('RGB').crop(CROP).resize((cw, ch), Image.LANCZOS)
        c, r = (ci, ri) if layout == 'rows' else (ri, ci)
        sheet.paste(im, (c * cw, r * (ch + head) + head))
        dr.text((c * cw + 6, r * (ch + head) + 5), '%s  %s' % (v, view), fill=(255, 235, 120))
sheet.save(out)
print('sheet', out, sheet.size)
