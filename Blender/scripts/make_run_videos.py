"""Videos of the run from the stills of render_walk_stills.py (views front, side_wide, back, top; frames 0 .. NF-1, one cycle at 60 fps).
usage: python make_run_videos.py <stills dir> <out dir> [loops] [nf] [fps] [stance share]
writes  run_4views.mp4 (real time), run_4views_slow.mp4 (a quarter of the speed), run_4views.gif (about half speed, loops by itself) and one mp4 per view.
The centre line (world x = 0) is drawn into the front, back and top views; two lamps show which foot is on the ground (both dark = flight).
Blender 5.1 in this setup has no video output, so the encoding happens here (OpenCV, mp4v) plus a GIF."""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
loops = int(sys.argv[3]) if len(sys.argv) > 3 else 8
NF = int(sys.argv[4]) if len(sys.argv) > 4 else 36
FPS = int(sys.argv[5]) if len(sys.argv) > 5 else 60
PH_TO = float(sys.argv[6]) if len(sys.argv) > 6 else 0.2222
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
# the poses of one step (right foot 0 .. 0.5 of the cycle, left foot 0.5 .. 1)
KEYS = {0.0: 'Aufsetzen', 0.111: 'Stütze (tiefster Punkt)', PH_TO: 'Absprung', 0.36: 'Flug'}


def phase_label(f):
    p = f / float(NF)
    for side, off in (('rechts', 0.0), ('links', 0.5)):
        for k, name in KEYS.items():
            if abs(((p - off - k + 0.5) % 1.0) - 0.5) < 0.5 / NF:
                return '%s %s' % (name, side)
    return ''


def foot_down(f, off):
    return ((f / float(NF) + off) % 1.0) < PH_TO


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


def lamps(d, x, y, f):
    """two lamps: right and left foot on the ground"""
    for i, (lab, off) in enumerate((('R', 0.0), ('L', 0.5))):
        on = foot_down(f, off)
        cx = x + i * 60
        d.ellipse([cx, y, cx + 22, y + 22], fill=(90, 230, 120) if on else (60, 66, 78), outline=(200, 200, 215))
        d.text((cx + 28, y + 1), lab, fill=(220, 220, 235), font=FONT_S)
    if not foot_down(f, 0.0) and not foot_down(f, 0.5):
        d.text((x + 130, y + 1), 'FLUG', fill=(255, 190, 90), font=FONT_S)


def frame_grid(f):
    cells = {v: cell(v, f) for v in CROP}
    g = Image.new('RGB', (CELL_W * 2, CELL_H * 2))
    g.paste(cells['front'], (0, 0))
    g.paste(cells['side_wide'], (CELL_W, 0))
    g.paste(cells['back'], (0, CELL_H))
    g.paste(cells['top'], (CELL_W, CELL_H))
    d = ImageDraw.Draw(g)
    d.text((CELL_W * 2 - 430, 6), 'Bild %02d / %d   %s' % (f, NF, phase_label(f)), fill=(255, 220, 120), font=FONT)
    lamps(d, CELL_W + 20, 40, f)
    return g


def write_mp4(path, frames, fps, repeat):
    h, w = frames[0].height, frames[0].width
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    for _ in range(repeat):
        for im in frames:
            vw.write(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
    vw.release()
    print('wrote', path, os.path.getsize(path) // 1024, 'KB')


grid = [frame_grid(f) for f in range(NF)]
write_mp4(os.path.join(out, 'run_4views.mp4'), grid, FPS, loops)
write_mp4(os.path.join(out, 'run_4views_slow.mp4'), grid, FPS // 4, max(2, loops // 3))
small = [g.resize((g.width // 2, g.height // 2), Image.LANCZOS) for g in grid]
gif = os.path.join(out, 'run_4views.gif')
small[0].save(gif, save_all=True, append_images=small[1:] * 2, duration=33, loop=0, optimize=False)    # 30 fps = half speed
print('wrote', gif, os.path.getsize(gif) // 1024, 'KB')
for v in CROP:
    frames = [cell(v, f) for f in range(NF)]
    write_mp4(os.path.join(out, 'run_%s.mp4' % v), frames, FPS, loops)
