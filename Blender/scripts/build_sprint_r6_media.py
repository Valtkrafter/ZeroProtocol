"""
Yoru - SPRINT LEAN CORRECTION r6 video (system python, OpenCV + Pillow, no ffmpeg); template build_sprint_r5_media.py:
  python build_sprint_r6_media.py <frames_r6 dir> <measure_r6.json> <out mp4> [scale, e.g. 0.9]
Columns R5 (now, baked) | L20 | L23 | L26, each titled with its measured mean lean hips->neck and skull tilt (sprint_measure.py);
rows: game camera at 1080p pixel size (rendered every 2nd frame), game camera zoomed on arms, pistols and upper body (6400 x 3600 inside a window),
side view 720 x 960 in place.  3 cycles in real time (30 fps video, every 2nd render), then 1 cycle at half speed (every render).
"""
import sys, os, json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FR, MEAS, VIDEO = sys.argv[1], sys.argv[2], sys.argv[3]
SCALE = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 21)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
BG = (22, 24, 29)
M = json.load(open(MEAS))
ACT = {'R5': 'Yoru_Sprint_r5_P2', 'L20': 'Yoru_Sprint_r6_L20', 'L23': 'Yoru_Sprint_r6_L23', 'L26': 'Yoru_Sprint_r6_L26'}
COLS = [(k, '%s%s: lean %.1f, skull %.1f deg' % (k, ' (now)' if k == 'R5' else '', M[a]['lean'][2], M[a]['head_pitch'][2])) for k, a in ACT.items()]
ROWS = [('wide', 'game_%03d.png', 108), ('body', 'game_%03d.png', 108), ('side', 'side_%03d.png', 36)]


def path(col, row, a):
    sub, pat, n = next(r for r in ROWS if r[0] == row)
    if row == 'wide':
        a = 2 * (a // 2)                                             # this row is rendered every 2nd frame
    return os.path.join(FR, '%s_%s' % (col, sub), pat % (a % n))


size = {(c, r[0]): Image.open(path(c, r[0], 0)).size for c, _ in COLS for r in ROWS}
cw = max(w for w, h in size.values()) // 2 * 2 + 8
rh = [max(size[(c, r[0])][1] for c, _ in COLS) + 6 for r in ROWS]
top, bottom = 36, 30
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
            d.line([(c * cw, top), (c * cw, top + sum(rh))], fill=(60, 64, 72), width=3)
    d.text((8, top + sum(rh) + 6), '%s   t = %.3f s (cycle 0.60 s)   rows: game camera 1080p | game camera zoomed | side view   lean = hips->neck, skull = head tilt'
           % (label, (a % 36) / 60.0), fill=(150, 220, 255), font=F)
    if SCALE != 1.0:
        g = g.resize((OW, OH), Image.LANCZOS)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


os.makedirs(os.path.dirname(VIDEO), exist_ok=True)
vw = cv2.VideoWriter(VIDEO, cv2.VideoWriter_fourcc(*'mp4v'), 30, (OW, OH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + VIDEO)
for i in range(54):                                                  # 3 cycles in real time
    vw.write(frame(2 * i, 'real time'))
for i in range(36):                                                  # 1 cycle at half speed
    vw.write(frame(i, 'half speed'))
vw.release()
print('video', VIDEO, os.path.getsize(VIDEO) // 1024, 'KB', '%d x %d' % (OW, OH), flush=True)
