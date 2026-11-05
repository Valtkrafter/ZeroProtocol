"""
Yoru - sprint lean correction (r6), main-agent review sheets (system python, Pillow).  Saves only the PNG.
  python review_sprint_r6.py <frames_r6 dir> <ref_nte dir> <mode> <out png> [cols=R5,L20,L23,L26] [phases=0,6,12,18,24,30] [h=300] [alt=L20/wide=L20b,L20/body=L20b] [titles=a|b|c]
modes:
  side   rows: NTE side | one row per column (side view).  NTE phases k/6: right foot down at f110.5 -> f110,114,117,100,104,107.
  back   rows: NTE from behind | one row per column (game camera, crop wide, every 2nd frame so use even phases).
  body   rows: upper half of the NTE back tiles | one row per column (game camera, zoomed upper body).
  still  the picture for the user: columns = variants, rows = game camera zoomed (frame p) | game camera wide | side view (frame p), p = first phase
Ours: 60 fps, 36 frames per cycle (0 = right foot touches down); NTE 30 fps, 20 frames per cycle.
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

FR, REF, MODE, OUT = sys.argv[1:5]
KV = dict(a.split('=', 1) for a in sys.argv[5:] if '=' in a)
COLS = KV.get('cols', 'R5,L20,L23,L26').split(',')
PH = [int(x) for x in KV.get('phases', '0,6,12,18,24,30').split(',')]
H = int(KV.get('h', 300))
TITLES = dict(zip(COLS, KV.get('titles', '').split('|'))) if KV.get('titles') else {}
ALT = {tuple(a.split('=')[0].split('/')): a.split('=')[1] for a in KV.get('alt', '').split(',') if a}      # e.g. alt=L20/wide=L20b,L20/body=L20b (frame folder <name>_<row>)
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 19)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 14)
BG = (22, 24, 29)
NTE = {'side': ('NTE_lauf_seite_zyklus_f100-119.jpg', 100, {0: 110, 6: 114, 12: 117, 18: 100, 24: 104, 30: 107}),
       'back': ('NTE_lauf_hinten_zyklus_f60-79.jpg', 60, {0: 60, 6: 63, 12: 66, 18: 70, 24: 73, 30: 76})}


def nte_tile(view, ph):
    name, f0, m = NTE[view]
    im = Image.open(os.path.join(REF, name)).convert('RGB')
    tw, th = im.width / 5.0, im.height / 4.0
    i = m[ph] - f0
    r, c = divmod(i, 5)
    return im.crop((round(c * tw), round(r * th), round((c + 1) * tw), round((r + 1) * th))), 'NTE f%d' % m[ph]


def fit(im, h=H):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


def ours(col, row, ph):
    sub, pat = {'side': ('side', 'side_%03d.png'), 'wide': ('wide', 'game_%03d.png'), 'body': ('body', 'game_%03d.png')}[row]
    if row == 'wide':
        ph = 2 * (ph // 2)
    return Image.open(os.path.join(FR, '%s_%s' % (ALT.get((col, row), col), sub), pat % ph)).convert('RGB')


def sheet(rows, title, out, label_w=110):
    cw = max(im.width for _, ims, _ in rows for im in ims)
    n = max(len(ims) for _, ims, _ in rows)
    W, Ht = label_w + cw * n, 40 + len(rows) * (H + 20)
    g = Image.new('RGB', (W, Ht), BG)
    d = ImageDraw.Draw(g)
    d.text((10, 10), title, fill=(255, 226, 120), font=F_B)
    for r, (label, ims, names) in enumerate(rows):
        y = 40 + r * (H + 20)
        d.text((8, y + H // 2 - 10), label, fill=(255, 226, 120), font=F_B)
        for i, im in enumerate(ims):
            g.paste(im, (label_w + i * cw + (cw - im.width) // 2, y))
            d.text((label_w + i * cw + 4, y + H + 2), names[i], fill=(150, 220, 255), font=F)
    g.save(out)
    print('sheet', out, g.size, flush=True)


if MODE in ('side', 'back', 'body'):
    rows = []
    if MODE == 'body':
        tiles = [nte_tile('back', p) for p in PH]
        rows.append(('NTE back', [fit(t.crop((0, 0, t.width, int(t.height * 0.5))), H) for t, _ in tiles], [n for _, n in tiles]))
    else:
        tiles = [nte_tile(MODE, p) for p in PH]
        rows.append(('NTE', [fit(t) for t, _ in tiles], [n for _, n in tiles]))
    for c in COLS:
        row = {'side': 'side', 'back': 'wide', 'body': 'body'}[MODE]
        rows.append((c, [fit(ours(c, row, p)) for p in PH], ['frame %d' % p for p in PH]))
    sheet(rows, 'NTE and %s, %s, same phases (column k = k/6 of the cycle, 0 = right foot down)' % (', '.join(COLS), MODE), OUT)
else:
    p = PH[0]
    spec = [('body', 'behind, zoomed'), ('wide', 'behind, game camera'), ('side', 'from the side')]
    tiles = {(c, r): ours(c, r, p) for c in COLS for r, _ in spec}
    heights = {'body': H, 'wide': int(H * 0.8), 'side': H}
    rows_im = {r: [fit(tiles[(c, r)], heights[r]) for c in COLS] for r, _ in spec}
    cw = max(im.width for r in rows_im.values() for im in r) + 6
    top = 34
    Wd = cw * len(COLS)
    Ht = top + sum(heights[r] + 6 for r, _ in spec) + 26
    g = Image.new('RGB', (Wd, Ht), BG)
    d = ImageDraw.Draw(g)
    for ci, c in enumerate(COLS):
        d.text((ci * cw + 8, 8), TITLES.get(c, c), fill=(255, 226, 120), font=F_B)
    y = top
    for r, name in spec:
        for ci, im in enumerate(rows_im[r]):
            g.paste(im, (ci * cw + (cw - im.width) // 2, y))
        y += heights[r] + 6
    d.text((8, Ht - 20), 'rows: behind zoomed | behind with the game camera | from the side.  Same moment of the run in every column (frame %d).' % p, fill=(150, 220, 255), font=F)
    g.save(OUT)
    print('still', OUT, g.size, flush=True)
