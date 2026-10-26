"""Walk v2, round 4: comparison video R3 | R4a | R4b with three rows (close-up of the upper body from the front three-quarter, close-up from
the side, game camera with the whole body) from the frames of build_walk_v2_render_r4.py (25 frames per cycle).  Four cycles in real
time, then two at half speed (every frame twice).  Column names on a title bar, speed / time on a bar at the bottom, nothing overlaps.
usage: python build_walk_v2_media_r4.py <frames dir with R3/, R4a/, R4b/> <out mp4>"""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, video = sys.argv[1], sys.argv[2]
FPS, NF = 30, 25
COLS = [('R3', 'R3 (Runde 3)'), ('R4a', 'R4a fliessend'), ('R4b', 'R4b kompakt')]
cw, ch, top, bottom = 300, 360, 40, 30
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 21)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
VW, VH = cw * 3, top + 3 * ch + bottom


def cell(key, view, f):
    a = Image.open(os.path.join(src, key, '%s_%03d.png' % (view, f))).convert('RGB')
    if view == 'game':
        a = a.crop((105, 70, 315, 490)).resize((180, 360))
        c = Image.new('RGB', (cw, ch), a.getpixel((2, 2)))
        c.paste(a, ((cw - 180) // 2, 0))
        return c
    return a.crop((45, 40, 375, 436)).resize((cw, ch))


def frame(i, label):
    g = Image.new('RGB', (VW, VH), (22, 24, 29))
    d = ImageDraw.Draw(g)
    f = i % NF
    for c, (key, title) in enumerate(COLS):
        for r, view in enumerate(('upper34', 'upperSide', 'game')):
            g.paste(cell(key, view, f), (c * cw, top + r * ch))
        d.text((c * cw + 10, 9), title, fill=(255, 226, 120), font=F_B)
        if c > 0:
            d.line([(c * cw, top), (c * cw, top + 3 * ch)], fill=(22, 24, 29), width=3)
    d.text((10, top + 3 * ch + 6), '%s     t = %.2f s     oben: nah vorn schräg, Mitte: nah Seite, unten: Spielkamera' % (label, i / float(FPS)),
           fill=(150, 220, 255), font=F)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


vw = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (VW, VH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + video)
for i in range(4 * NF):
    vw.write(frame(i, 'Echtzeit'))
for i in range(2 * NF):
    a = frame(i, 'halbe Geschwindigkeit')
    vw.write(a)
    vw.write(a)
vw.release()
cap = cv2.VideoCapture(video)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()
print('video', video, os.path.getsize(video) // 1024, 'KB', '%d x %d' % (VW, VH), '%.1f s' % (8 * NF / float(FPS)), 'frames', n)
