"""
Yoru - aim pose picture sheet (main agent, system python + Pillow, saves only the PNG).  Run with  python -I review_aim_r1.py ...
  python -I review_aim_r1.py <previews dir> <out png> [variants=A,B,C] [views=game_body,side,front34,ads] [h=420] [pad=10]
        [titles=A  one hand leads|B  both arms out|C  compact] [rows=from behind (game camera)|from the side|...] [head=Aim pose, round 1]
<previews dir>/<variant>/<view>.png  (the animator's stills).  Columns = variants, rows = views.  Every row is scaled to the same height h,
every column is as wide as its widest picture, so the grid stays tidy even when the crops differ.
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

D, OUT = sys.argv[1:3]
KV = dict(a.split('=', 1) for a in sys.argv[3:] if '=' in a)
VARS = KV.get('variants', 'A,B,C').split(',')
VIEWS = KV.get('views', 'game_body,side,front34,ads').split(',')
H = int(KV.get('h', 420))
PAD = int(KV.get('pad', 10))
TITLES = KV.get('titles', '').split('|') if KV.get('titles') else VARS
ROWS = KV.get('rows', '').split('|') if KV.get('rows') else VIEWS
HEAD = KV.get('head', '')
BG = (22, 24, 29)
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)
F_T = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 24)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)

cells = {}
for v in VARS:
    for w in VIEWS:
        p = os.path.join(D, v, w + '.png')
        im = Image.open(p).convert('RGB')
        cells[(v, w)] = im.resize((round(im.width * H / im.height), H), Image.LANCZOS)
colw = {v: max(cells[(v, w)].width for w in VIEWS) for v in VARS}
label_w = 190
top = 70 if HEAD else 52
W = label_w + sum(colw.values()) + PAD * (len(VARS) + 1)
Ht = top + len(VIEWS) * (H + PAD) + PAD
sheet = Image.new('RGB', (W, Ht), BG)
d = ImageDraw.Draw(sheet)
if HEAD:
    d.text((PAD + 4, 8), HEAD, fill=(255, 255, 255), font=F_T)
x = label_w + PAD
for v, t in zip(VARS, TITLES):
    d.text((x + 6, top - 34), t, fill=(255, 226, 120), font=F_B)
    x += colw[v] + PAD
for ri, (w, lab) in enumerate(zip(VIEWS, ROWS)):
    y = top + ri * (H + PAD)
    for li, line in enumerate(lab.split('/')):
        d.text((PAD + 4, y + H // 2 - 22 + li * 22), line.strip(), fill=(150, 220, 255), font=F)
    x = label_w + PAD
    for v in VARS:
        im = cells[(v, w)]
        sheet.paste(im, (x + (colw[v] - im.width) // 2, y))
        x += colw[v] + PAD
sheet.save(OUT)
print('sheet', OUT, sheet.size)
