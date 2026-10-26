"""Run v2 (polish): comparison video  ALT (left) against POLIERT (right), 60 fps, both on a floor that scrolls with the ground speed.
Per character a column of two rows: the side view and the game camera from behind (row 1), the arm close-up from the side (row 2).
10 cycles in real time, then 4 cycles at half speed (every frame twice).
usage: python -I build_run_v2_media.py <frames dir with Alt/ and Neu/> <out mp4> [title of the right side, default 'Poliert'] [title of the left side]
needs <frames dir>/<Alt|Neu>/side_NNN.png, back_NNN.png, armSideX_NNN.png for NNN = 0 .. 35 (build_run_v2_render.py, jobs 'Alt,Neu|side,back,armSideX|0-35')"""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, video = sys.argv[1], sys.argv[2]
TITLE_R = sys.argv[3] if len(sys.argv) > 3 else 'Poliert'
TITLE_L = sys.argv[4] if len(sys.argv) > 4 else 'Alt: Rennen'
NF, FPS = 36, 60
SW, BW, RH = 380, 360, 500            # side, back, row height
AW, AH = 740, 592                     # arm close-up
COLW = SW + BW
TOP, BOT = 44, 34
VW, VH = 2 * COLW, TOP + RH + AH + BOT
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
cache = {}


def img(key, view, f):
    k = (key, view, f)
    if k not in cache:
        cache[k] = Image.open(os.path.join(src, key, '%s_%03d.png' % (view, f))).convert('RGB')
    return cache[k]


def compose(i, label):
    f = i % NF
    g = Image.new('RGB', (VW, VH), (22, 24, 29))
    d = ImageDraw.Draw(g)
    for c, (key, title) in enumerate((('Alt', TITLE_L), ('Neu', TITLE_R))):
        x0 = c * COLW
        d.text((x0 + 12, 10), title, fill=(255, 226, 120), font=F_B)
        g.paste(img(key, 'side', f), (x0, TOP))
        g.paste(img(key, 'back', f), (x0 + SW, TOP))
        g.paste(img(key, 'armSideX', f), (x0, TOP + RH))
    d.line([(COLW, TOP), (COLW, TOP + RH + AH)], fill=(22, 24, 29), width=4)
    d.text((10, TOP + RH + AH + 8), '%s    Zyklus %d' % (label, i // NF + 1), fill=(150, 220, 255), font=F)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


vw = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (VW, VH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + video)
for i in range(10 * NF):
    vw.write(compose(i, 'Echtzeit'))
for i in range(4 * NF):
    a = compose(i, 'halbe Geschwindigkeit')
    vw.write(a)
    vw.write(a)
vw.release()
cap = cv2.VideoCapture(video)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()
print('video', video, os.path.getsize(video) // 1024, 'KB', '%d x %d' % (VW, VH), 'frames', n, '%.1f s' % (n / float(FPS)))
