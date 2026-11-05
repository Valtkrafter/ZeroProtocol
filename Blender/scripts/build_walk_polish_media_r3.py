"""
Yoru - WALK POLISH, round 3 video (system python, OpenCV + Pillow, no ffmpeg):
  python build_walk_polish_media_r3.py <work dir> <out mp4>
Columns OLD | C (round 2) | C + inward elbow (round 3); rows: close-up from the front (in place, 21-frame loop), game camera at real 1080p
pixel size (her walking through the world), game camera zoomed on arms and legs (rendered at 4480 x 2520 inside a window, not enlarged).
Images are pasted 1:1, centred in their cells.  3 cycles in real time twice, then the same 3 cycles at half speed.
"""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WORK, VIDEO = sys.argv[1], sys.argv[2]
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 19)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)
COLS = [('old', 'frames_old', 'OLD (in the game)'), ('r2C', 'frames_r2C', 'C  (round 2)'), ('r3', 'frames_r3', 'C + inward elbow (round 3)')]
N, NF = 63, 21


def load(path, box=None):
    im = Image.open(path).convert('RGB')
    return im.crop(box) if box else im


def size_of(sub):
    return Image.open(os.path.join(WORK, 'game3', sub, 'g_000.png')).size


cw = max(300, max(size_of(k + '_wide')[0] for k, _, _ in COLS), max(size_of(k + '_zoom')[0] for k, _, _ in COLS)) // 2 * 2
rh = [360, max(size_of(k + '_wide')[1] for k, _, _ in COLS), max(size_of(k + '_zoom')[1] for k, _, _ in COLS)]
top, bottom = 34, 28
VW, VH = cw * len(COLS), (top + sum(rh) + bottom) // 2 * 2


def frame(i, label):
    g = Image.new('RGB', (VW, VH), BG)
    d = ImageDraw.Draw(g)
    for c, (key, sub, title) in enumerate(COLS):
        cells = [load(os.path.join(WORK, sub, 'closeFront_%03d.png' % (i % NF)), (60, 40, 360, 400)),
                 load(os.path.join(WORK, 'game3', key + '_wide', 'g_%03d.png' % (i % N))),
                 load(os.path.join(WORK, 'game3', key + '_zoom', 'g_%03d.png' % (i % N)))]
        y = top
        for r, im in enumerate(cells):
            g.paste(im, (c * cw + (cw - im.width) // 2, y + (rh[r] - im.height) // 2))
            y += rh[r]
        d.text((c * cw + 8, 7), title, fill=(255, 226, 120), font=F_B)
        if c:
            d.line([(c * cw, top), (c * cw, top + sum(rh))], fill=BG, width=3)
    d.text((8, top + sum(rh) + 5), '%s   t = %.2f s   rows: front close-up | game camera (1080p size) | game camera zoomed' % (label, (i % N) / 30.0),
           fill=(150, 220, 255), font=F)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


vw = cv2.VideoWriter(VIDEO, cv2.VideoWriter_fourcc(*'mp4v'), 30, (VW, VH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + VIDEO)
for rep in range(2):
    for i in range(N):
        vw.write(frame(i, 'real time'))
for i in range(N):
    a = frame(i, 'half speed')
    vw.write(a)
    vw.write(a)
vw.release()
cap = cv2.VideoCapture(VIDEO)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()
print('video', VIDEO, os.path.getsize(VIDEO) // 1024, 'KB', '%d x %d' % (VW, VH), '%.1f s' % (n / 30.0), flush=True)
