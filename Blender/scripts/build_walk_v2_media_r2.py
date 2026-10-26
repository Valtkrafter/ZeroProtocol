"""Walk v2, round 2: comparison video Alt | Neu | Neu+ (top: front three-quarter, bottom: game camera) from the frames of
build_walk_v2_render_r2.py.  Four cycles of the new walk in real time (116 frames; Alt runs on with its own frames 0..115 = 5.5 of its
0.70 s cycles), then two cycles at half speed (every frame twice).  Column names on a title bar, the speed / time on a separate bar at the
bottom (nothing overlaps).  OpenCV mp4v (ffmpeg is not installed), Pillow for the text.
usage: python build_walk_v2_media_r2.py <frames dir with Alt/, Neu/, NeuPlus/> <out mp4>"""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, video = sys.argv[1], sys.argv[2]
FPS, NF = 30, 29
COLS = [('Alt', 'Alt (bisher, 0,70 s)'), ('Neu', 'Neu (0,97 s, 1,2 m/s)'), ('NeuPlus', 'Neu+ (mehr Swagger)')]
CROP = (45, 10, 375, 504)
cw, ch, top, bottom = 330, 494, 40, 30
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 21)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
VW, VH = cw * 3, top + 2 * ch + bottom


def cell(key, view, f):
    return Image.open(os.path.join(src, key, '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP)


def frame(i, label):
    g = Image.new('RGB', (VW, VH), (22, 24, 29))
    d = ImageDraw.Draw(g)
    for c, (key, title) in enumerate(COLS):
        f = i if key == 'Alt' else i % NF
        g.paste(cell(key, 'front34', f), (c * cw, top))
        g.paste(cell(key, 'game', f), (c * cw, top + ch))
        d.text((c * cw + 10, 9), title, fill=(255, 226, 120), font=F_B)
        if c > 0:
            d.line([(c * cw, top), (c * cw, top + 2 * ch)], fill=(22, 24, 29), width=3)
    d.text((10, top + 2 * ch + 5), '%s     t = %.2f s     oben: vorn schräg, unten: Spielkamera' % (label, i / float(FPS)), fill=(150, 220, 255), font=F)
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
