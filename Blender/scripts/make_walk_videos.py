"""Videos of the walk from the stills of render_walk_stills.py (views front, side_wide, back, top; frames 0 .. NF-1, one cycle).
usage: python make_walk_videos.py <stills dir> <out dir> [loops] [nf]
writes  walk_4views.mp4 / walk_4views.gif (2 x 2 grid: Front, Seite, Hinten, Oben) and one mp4 per view.
The centre line (world x = 0) is drawn into the front, back and top views: the head should not leave it.
Blender 5.1 in this setup has no video output, so the encoding happens here (OpenCV, mp4v) plus a GIF (loops by itself)."""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
loops = int(sys.argv[3]) if len(sys.argv) > 3 else 4
NF = int(sys.argv[4]) if len(sys.argv) > 4 else 26
os.makedirs(out, exist_ok=True)

CROP = {'front': (110, 30, 510, 700), 'side_wide': (0, 40, 600, 700), 'back': (110, 30, 510, 700), 'top': (60, 60, 540, 700)}
TITLE = {'front': 'VORNE', 'side_wide': 'SEITE', 'back': 'HINTEN', 'top': 'OBEN'}
CENTER = {'front': 300 - 110, 'back': 300 - 110, 'top': 300 - 60}          # image column of world x = 0 after the crop (the cameras look at x = 0)
CELL_W, CELL_H = 600, 690
try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
    FONT_S = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
except Exception:
    FONT = FONT_S = ImageFont.load_default()
# phase names of the classic poses (right step 0 .. 0.5 of the cycle, left step 0.5 .. 1): contact, down, passing, up
KEYS = {0.0: 'Contact', 0.115: 'Down', 0.27: 'Passing', 0.385: 'Up'}


def phase_label(f):
    p = f / float(NF)
    for side, off in (('rechts', 0.0), ('links', 0.5)):
        for k, name in KEYS.items():
            if abs(((p - off - k + 0.5) % 1.0) - 0.5) < 0.5 / NF:
                return '%s %s' % (name, side)
    return ''


def cell(view, f):
    im = Image.open(os.path.join(src, '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP[view])
    canvas = Image.new('RGB', (CELL_W, CELL_H), (112, 124, 140))
    ox, oy = (CELL_W - im.width) // 2, 34 + (CELL_H - 34 - im.height) // 2
    canvas.paste(im, (ox, oy))
    d = ImageDraw.Draw(canvas)
    if view in CENTER:
        cx = ox + CENTER[view]
        d.line([(cx, 34), (cx, CELL_H)], fill=(60, 230, 230), width=1)
    d.rectangle([0, 0, CELL_W, 30], fill=(30, 34, 42))
    d.text((10, 4), TITLE[view], fill=(255, 255, 255), font=FONT)
    return canvas


def frame_grid(f):
    cells = {v: cell(v, f) for v in CROP}
    g = Image.new('RGB', (CELL_W * 2, CELL_H * 2))
    g.paste(cells['front'], (0, 0))
    g.paste(cells['side_wide'], (CELL_W, 0))
    g.paste(cells['back'], (0, CELL_H))
    g.paste(cells['top'], (CELL_W, CELL_H))
    d = ImageDraw.Draw(g)
    lab = phase_label(f)
    d.text((CELL_W * 2 - 330, 6), 'Bild %02d / %d   %s' % (f, NF, lab), fill=(255, 220, 120), font=FONT)
    return g


def write_mp4(path, frames):
    h, w = frames[0].height, frames[0].width
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 30, (w, h))
    for _ in range(loops):
        for im in frames:
            vw.write(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
    vw.release()
    print('wrote', path, os.path.getsize(path) // 1024, 'KB')


grid = [frame_grid(f) for f in range(NF)]
write_mp4(os.path.join(out, 'walk_4views.mp4'), grid)
small = [g.resize((g.width // 2, g.height // 2), Image.LANCZOS) for g in grid]
gif = os.path.join(out, 'walk_4views.gif')
small[0].save(gif, save_all=True, append_images=small[1:] * 2, duration=30, loop=0, optimize=False)
print('wrote', gif, os.path.getsize(gif) // 1024, 'KB')
for v in CROP:
    frames = [cell(v, f) for f in range(NF)]
    write_mp4(os.path.join(out, 'walk_%s.mp4' % v), frames)
