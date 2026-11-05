"""
Yoru - NEW SPRINT, round 1 video (system python, OpenCV + Pillow, no ffmpeg):
  python build_sprint_r1_media.py <frames dir> <out mp4>
Columns ALT (the old sprint) | A | B | C; rows: game camera at real 1080p pixel size (she runs through the world), game camera zoomed on arms,
pistols and upper body (rendered at 8960 x 5040 inside a window, not enlarged), close-up from the front (in place).
The renders are 60 fps (36 frames per 0.6 s cycle).  3 cycles in real time twice (30 fps video, every 2nd render), then the same 3 cycles at
half speed (every render).  Images are pasted 1:1, centred in their cells.
"""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FR, VIDEO = sys.argv[1], sys.argv[2]
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 19)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)
COLS = [('ALT', 'ALT (bisheriger Sprint)'), ('A', 'A  nah und tief'), ('B', 'B  weiches Mitschwingen'), ('C', 'C  tief und hinten')]
ROWS = [('wide', 'game_%03d.png', 108), ('body', 'game_%03d.png', 108), ('front', 'front_%03d.png', 36)]


def path(col, row, a):
    sub, pat, n = next(r for r in ROWS if r[0] == row)
    return os.path.join(FR, '%s_%s' % (col, sub), pat % (a % n))


size = {(c, r[0]): Image.open(path(c, r[0], 0)).size for c, _ in COLS for r in ROWS}
cw = max(w for w, h in size.values()) // 2 * 2 + 8
rh = [max(size[(c, r[0])][1] for c, _ in COLS) + 6 for r in ROWS]
top, bottom = 34, 30
VW, VH = cw * len(COLS), (top + sum(rh) + bottom) // 2 * 2


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
    d.text((8, top + sum(rh) + 6), '%s   t = %.3f s (Zyklus 0,60 s)   Zeilen: Spielkamera in 1080p-Größe | Spielkamera vergrößert (Arme, Pistolen) | vorn, auf der Stelle'
           % (label, (a % 36) / 60.0), fill=(150, 220, 255), font=F)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


vw = cv2.VideoWriter(VIDEO, cv2.VideoWriter_fourcc(*'mp4v'), 30, (VW, VH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + VIDEO)
for rep in range(2):
    for i in range(54):
        vw.write(frame(2 * i, 'Echtzeit'))
for i in range(108):
    vw.write(frame(i, 'halbe Geschwindigkeit'))
vw.release()
cap = cv2.VideoCapture(VIDEO)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()
print('video', VIDEO, os.path.getsize(VIDEO) // 1024, 'KB', '%d x %d' % (VW, VH), '%.1f s' % (n / 30.0), flush=True)
