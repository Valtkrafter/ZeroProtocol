"""Walk v2: picture sheet and video of the three variants from the frames of build_walk_v2_render.py.
usage: python build_walk_v2_media.py <frames dir (with A/, B/, C/)> <sheet png> <video mp4> [contact frame, default 0] [passing frame, default 7]
Sheet: columns A, B, C; rows contact front34, contact side, contact game camera, passing game camera.
Video: two rows (front three-quarter, game camera) x three columns, four cycles in real time, then two cycles at half speed (every frame
twice), the variant names on top.  OpenCV mp4v (ffmpeg is not installed), Pillow for the text."""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, sheet_png, video = sys.argv[1], sys.argv[2], sys.argv[3]
CONTACT = int(sys.argv[4]) if len(sys.argv) > 4 else 0
PASSING = int(sys.argv[5]) if len(sys.argv) > 5 else 7
NF, FPS = 29, 30
KEYS = ('A', 'B', 'C')
NAMES = {'A': 'A  kontrolliert', 'B': 'B  Swagger', 'C': 'C  Catwalk'}
SUB = {'A': ('Fußspur 11 cm, Hüftdrehung ±4°', 'Beckenkippen ±3°, Schultern ±3°'),
       'B': ('Fußspur 5 cm, Hüftdrehung ±7°', 'Beckenkippen ±5°, Schultern ±5°'),
       'C': ('Fußspur 1,5 cm, Hüftdrehung ±9°', 'Beckenkippen ±6°, Schultern ±6°')}
try:
    F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)
    F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
except Exception:
    F_B = F = ImageFont.load_default()
CROP = {'front34': (45, 10, 375, 504), 'side': (45, 10, 375, 504), 'game': (45, 10, 375, 504)}


def cell(k, view, f):
    return Image.open(os.path.join(src, k, '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP[view])


# ------------------------------------------------------------------ sheet
rows = [('Kontaktpose (Ferse setzt auf), vorn schräg', 'front34', CONTACT), ('Kontaktpose, Seite', 'side', CONTACT),
        ('Kontaktpose, Spielkamera', 'game', CONTACT), ('Passing-Pose, Spielkamera', 'game', PASSING)]
cw, ch = 330, 494
head, rowh = 84, 26
sheet = Image.new('RGB', (cw * 3, head + len(rows) * (ch + rowh)), (24, 26, 32))
d = ImageDraw.Draw(sheet)
for i, k in enumerate(KEYS):
    d.text((i * cw + 10, 8), NAMES[k], fill=(255, 226, 120), font=F_B)
    d.text((i * cw + 10, 36), SUB[k][0], fill=(200, 205, 215), font=F)
    d.text((i * cw + 10, 56), SUB[k][1], fill=(200, 205, 215), font=F)
for j, (title, view, f) in enumerate(rows):
    y0 = head + j * (ch + rowh)
    d.text((10, y0 + 4), '%s   (Bild %d)' % (title, f), fill=(150, 220, 255), font=F)
    for i, k in enumerate(KEYS):
        sheet.paste(cell(k, view, f), (i * cw, y0 + rowh))
sheet.save(sheet_png)
print('sheet', sheet_png, sheet.size)

# ------------------------------------------------------------------ video
VW = cw * 3
VH = 44 + 2 * ch


def frame_img(f, label):
    g = Image.new('RGB', (VW, VH), (22, 24, 29))
    for i, k in enumerate(KEYS):
        g.paste(cell(k, 'front34', f), (i * cw, 44))
        g.paste(cell(k, 'game', f), (i * cw, 44 + ch))
    dd = ImageDraw.Draw(g)
    for i, k in enumerate(KEYS):
        dd.text((i * cw + 10, 10), NAMES[k], fill=(255, 226, 120), font=F_B)
    dd.text((VW - 250, 14), '%s   Bild %2d / %d' % (label, f, NF), fill=(150, 220, 255), font=F)
    dd.text((8, 44 + ch + 6), 'Spielkamera', fill=(220, 220, 230), font=F)
    dd.text((8, 50), 'vorn schräg', fill=(220, 220, 230), font=F)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


vw = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (VW, VH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + video)
rt = [frame_img(f, 'Echtzeit') for f in range(NF)]
for _ in range(4):
    for a in rt:
        vw.write(a)
for _ in range(2):
    for f in range(NF):
        a = frame_img(f, 'halbe Geschw.')
        vw.write(a)
        vw.write(a)
vw.release()
cap = cv2.VideoCapture(video)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()
print('video', video, os.path.getsize(video) // 1024, 'KB', '%d x %d' % (VW, VH), '%.1f s' % ((4 * NF + 4 * NF) / float(FPS)), 'frames', n)
