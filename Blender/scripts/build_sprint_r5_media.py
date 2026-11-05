"""
Yoru - NEW SPRINT, round 5 video (system python, OpenCV + Pillow, no ffmpeg):
  python build_sprint_r5_media.py <frames_r5 dir> <frames_r4 dir (game rows of r4 P2)> <out mp4> [scale, e.g. 0.9]
Columns r4 P2 | r5 P2 (side view 480 x 640 for both, rendered in frames_r5); rows: game camera at 1080p pixel size (rendered every 2nd frame), game camera zoomed on arms, pistols and upper
body (6400 x 3600 inside a window), side view in place.
3 cycles in real time (30 fps video, every 2nd render), then the same 3 cycles at half speed (every render).
"""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FR3, FR2, VIDEO = sys.argv[1], sys.argv[2], sys.argv[3]
SCALE = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 19)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)
COLS = [('R4', 'Runde 4  P2'), ('R5', 'Runde 5  P2 (Kopf, Neigung, Haare)')]
ROWS = [('wide', 'game_%03d.png', 108), ('body', 'game_%03d.png', 108), ('side', 'side_%03d.png', 36)]


def path(col, row, a):
    sub, pat, n = next(r for r in ROWS if r[0] == row)
    if row == 'wide':
        a = 2 * (a // 2)                                             # this row is rendered every 2nd frame
    if col == 'R4' and row != 'side':
        return os.path.join(FR2, 'P2_%s' % sub, pat % (a % n))
    return os.path.join(FR3, '%s_%s' % (col, sub), pat % (a % n))


size = {(c, r[0]): Image.open(path(c, r[0], 0)).size for c, _ in COLS for r in ROWS}
cw = max(w for w, h in size.values()) // 2 * 2 + 8
rh = [max(size[(c, r[0])][1] for c, _ in COLS) + 6 for r in ROWS]
top, bottom = 34, 30
VW, VH = cw * len(COLS), (top + sum(rh) + bottom) // 2 * 2
OW, OH = int(VW * SCALE) // 2 * 2, int(VH * SCALE) // 2 * 2


def frame(a, label):
    g = Image.new('RGB', (VW, VH), BG)
    d = ImageDraw.Draw(g)
    for c, (key, title) in enumerate(COLS):
        y = top
        for r, (row, _, _) in enumerate(ROWS):
            im = Image.open(path(key, row, a)).convert('RGB')
            g.paste(im, (c * cw + (cw - im.width) // 2, y + (rh[r] - im.height) // 2))
            y += rh[r]
        d.text((c * cw + 8, 7), title, fill=(255, 226, 120), font=F_B)
        if c:
            d.line([(c * cw, top), (c * cw, top + sum(rh))], fill=BG, width=4)
    d.text((8, top + sum(rh) + 6), '%s   t = %.3f s (Zyklus 0,60 s)   Zeilen: Spielkamera 1080p | Spielkamera vergrößert | von rechts' % (label, (a % 36) / 60.0),
           fill=(150, 220, 255), font=F)
    if SCALE != 1.0:
        g = g.resize((OW, OH), Image.LANCZOS)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


vw = cv2.VideoWriter(VIDEO, cv2.VideoWriter_fourcc(*'mp4v'), 30, (OW, OH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + VIDEO)
for i in range(54):
    vw.write(frame(2 * i, 'Echtzeit'))
for i in range(108):
    vw.write(frame(i, 'halbe Geschwindigkeit'))
vw.release()
print('video', VIDEO, os.path.getsize(VIDEO) // 1024, 'KB', '%d x %d' % (OW, OH), flush=True)
