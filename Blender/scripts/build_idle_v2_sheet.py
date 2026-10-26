"""Picture sheet of the idle v2 stand candidates: one COLUMN per variant (labelled), one ROW per view (labelled), cropped around the character.
usage: python build_idle_v2_sheet.py <dir with stills_<V>/> <out png> <variants, e.g. A,B,C> <views, e.g. front34,side,back> [cell width, default 300] [title]
                                     [column labels 'V=Title;line 1;line 2|V2=...'] [frame, default 0]
Needs Pillow (system python, not Blender).  Template: aim_sheet.py (same crop of the 600 x 720 stills).
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

d, out, variants, views = sys.argv[1], sys.argv[2], sys.argv[3].split(','), sys.argv[4].split(',')
cw = int(sys.argv[5]) if len(sys.argv) > 5 else 300
title = sys.argv[6] if len(sys.argv) > 6 else ''
CROP = (110, 40, 490, 700)                      # around the character in the 600 x 720 stills
ch = round(cw * (CROP[3] - CROP[1]) / (CROP[2] - CROP[0]))
NAMES = {'A': ('A  Kontrapost', 'Gewicht rechts, Hüfte seitlich,', 'freies Knie nach innen'),
         'B': ('B  Catwalk', 'Füße hintereinander auf einer Linie,', 'Becken leicht gedreht'),
         'C': ('C  Kompakt', 'Füße eng und mittig,', 'aufrecht, Gewicht gleich'),
         'haengend': ('Arme hängend', 'locker eng am Gear,', 'wie auf dem Hauptblatt'),
         'vorn': ('Hände vorn', 'links hält rechtes Handgelenk,', 'Ellbogen müssen zur Seite')}
VIEWS = {'front34': 'vorn schräg', 'side': 'Seite', 'back': 'Rücken', 'back34': 'hinten schräg', 'game': 'Spielkamera', 'front': 'vorn'}
if len(sys.argv) > 7 and sys.argv[7]:
    for part in sys.argv[7].split('|'):
        k, v = part.split('=', 1)
        bits = (v.split(';') + ['', ''])[:3]
        NAMES[k] = tuple(bits)
FRAME = int(sys.argv[8]) if len(sys.argv) > 8 else 0


def font(size, bold=False):
    for name in (('arialbd.ttf', 'calibrib.ttf') if bold else ('arial.ttf', 'calibri.ttf', 'segoeui.ttf')):
        p = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


f_head, f_sub, f_row, f_title = font(24, True), font(15), font(17, True), font(16)
left = 34                                         # column for the row labels (written vertically)
top = 78 + (28 if title else 0)
W, Hh = left + cw * len(variants), top + ch * len(views)
sheet = Image.new('RGB', (W, Hh), (22, 24, 29))
dr = ImageDraw.Draw(sheet)
if title:
    dr.text((10, 8), title, font=f_title, fill=(200, 205, 215))
for ci, v in enumerate(variants):
    x0 = left + ci * cw
    name, s1, s2 = NAMES.get(v, (v, '', ''))
    y = top - 74
    dr.text((x0 + 10, y), name, font=f_head, fill=(255, 226, 120))
    dr.text((x0 + 10, y + 30), s1, font=f_sub, fill=(215, 218, 225))
    dr.text((x0 + 10, y + 49), s2, font=f_sub, fill=(215, 218, 225))
    for ri, view in enumerate(views):
        im = Image.open(os.path.join(d, 'stills_%s' % v, '%s_%03d.png' % (view, FRAME))).convert('RGB')
        if im.size == (600, 720):
            im = im.crop(CROP)
        im = im.resize((cw, ch), Image.LANCZOS)
        sheet.paste(im, (x0, top + ri * ch))
    if ci > 0:
        dr.line([(x0, top - 74), (x0, Hh)], fill=(22, 24, 29), width=3)
for ri, view in enumerate(views):
    lab = VIEWS.get(view, view)
    tw = int(dr.textlength(lab, font=f_row))
    tmp = Image.new('RGB', (tw + 8, 24), (22, 24, 29))
    ImageDraw.Draw(tmp).text((4, 1), lab, font=f_row, fill=(200, 205, 215))
    tmp = tmp.rotate(90, expand=True)
    sheet.paste(tmp, (5, top + ri * ch + ch // 2 - tmp.size[1] // 2))
    if ri > 0:
        dr.line([(0, top + ri * ch), (W, top + ri * ch)], fill=(22, 24, 29), width=3)
sheet.save(out)
print('sheet', out, sheet.size)
