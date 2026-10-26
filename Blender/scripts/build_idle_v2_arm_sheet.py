"""Picture sheet of the arm close-ups of build_idle_v2_arm_diag.py.
usage: python build_idle_v2_arm_sheet.py <diag dir> <out png> <tag or tags, e.g. vorher or vorher,nachher> <frames, e.g. 0,90,200> [title]
One tag: columns = frames, rows = directions.  Two tags (before / after): columns = tag x frame, rows = directions.
Needs Pillow (system python)."""
import sys, os
from PIL import Image, ImageDraw, ImageFont

d, out = sys.argv[1], sys.argv[2]
tags = sys.argv[3].split(',')
frames = [int(x) for x in sys.argv[4].split(',')]
title = sys.argv[5] if len(sys.argv) > 5 else ''
DIRS = [('vornlinks', 'vorn schräg links'), ('vornrechts', 'vorn schräg rechts'), ('seiterechts', 'Seite rechts'),
        ('seitelinks', 'Seite links'), ('ruecken', 'Rücken')]
TAGNAME = {'vorher': 'vorher', 'nachher': 'nachher'}


def font(size, bold=False):
    p = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arialbd.ttf' if bold else 'arial.ttf')
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


F_H, F_R, F_T = font(18, True), font(15, True), font(15)
CW, CH = 240, 280
LEFT, TOP = 30, 62
cols = [(t, f) for t in tags for f in frames]
sheet = Image.new('RGB', (LEFT + CW * len(cols), TOP + CH * len(DIRS)), (22, 24, 29))
dr = ImageDraw.Draw(sheet)
dr.text((8, 6), title, font=F_T, fill=(200, 205, 215))
for ci, (t, f) in enumerate(cols):
    x0 = LEFT + ci * CW
    dr.text((x0 + 8, 34), '%s  Bild %d (%.1f s)' % (TAGNAME.get(t, t), f, f / 30.0), font=F_H, fill=(255, 226, 120) if t != 'nachher' else (140, 230, 160))
    for ri, (key, _) in enumerate(DIRS):
        p = os.path.join(d, '%s_%s_%03d.png' % (t, key, f))
        if os.path.exists(p):
            im = Image.open(p).convert('RGB').resize((CW, CH), Image.LANCZOS)
            sheet.paste(im, (x0, TOP + ri * CH))
    if ci:
        dr.line([(x0, 30), (x0, sheet.height)], fill=(22, 24, 29), width=3)
for ri, (_, lab) in enumerate(DIRS):
    tw = int(dr.textlength(lab, font=F_R))
    tmp = Image.new('RGB', (tw + 8, 22), (22, 24, 29))
    ImageDraw.Draw(tmp).text((4, 1), lab, font=F_R, fill=(200, 205, 215))
    tmp = tmp.rotate(90, expand=True)
    sheet.paste(tmp, (4, TOP + ri * CH + CH // 2 - tmp.size[1] // 2))
    if ri:
        dr.line([(0, TOP + ri * CH), (sheet.width, TOP + ri * CH)], fill=(22, 24, 29), width=3)
sheet.save(out)
print('sheet', out, sheet.size)
