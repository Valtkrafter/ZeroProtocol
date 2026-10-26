"""Closing video of the final idle (round 5): four views side by side from build_idle_v2_render_r5.py (front34, side, game, face close-up).
usage: python build_idle_v2_video_r5.py <frames dir with stills_final/> <out mp4> <curves json (round3_curves.json: breath and blink per frame)>
Two loops in real time, then one loop at half speed (every frame twice); every picture shows the frame, the time, a breath bar and a blink lamp.
OpenCV mp4v (Blender 5.1 here has no video output, ffmpeg is not installed).  Needs OpenCV and Pillow."""
import sys, os, json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out_mp4, curves = sys.argv[1], sys.argv[2], sys.argv[3]
C = json.load(open(curves))
NF, FPS = C['frames'], C['fps']
BREATH, BLINK = C['breath'], C['blink']
VIEWS = ['front34', 'side', 'game', 'face']
TITLE_V = {'front34': 'VORN SCHRÄG', 'side': 'SEITE (von rechts)', 'game': 'SPIELKAMERA', 'face': 'GESICHT (85 mm)'}
CROP = {'front34': (110, 30, 490, 700), 'side': (110, 30, 490, 700), 'game': (110, 40, 490, 710), 'face': (110, 30, 490, 700)}
CW, CH, HEAD = 380, 670, 34
try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    FONT_S = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    FONT_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
except Exception:
    FONT = FONT_S = FONT_B = ImageFont.load_default()


def cell(view, f):
    im = Image.open(os.path.join(src, 'stills_final', '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP[view])
    canvas = Image.new('RGB', (CW, CH + HEAD), (30, 34, 42))
    canvas.paste(im, (0, HEAD))
    ImageDraw.Draw(canvas).text((10, 6), TITLE_V[view], fill=(255, 255, 255), font=FONT)
    return canvas


def composite(f, label):
    W = CW * len(VIEWS)
    g = Image.new('RGB', (W, CH + HEAD + 46), (22, 24, 29))
    for i, v in enumerate(VIEWS):
        g.paste(cell(v, f), (i * CW, 46))
    d = ImageDraw.Draw(g)
    d.text((12, 12), 'Yoru Idle v2, fertig (Ausdruck B kühl-wachsam)   Bild %3d / %d   t = %5.2f s' % (f, NF, f / float(FPS)), fill=(255, 226, 120), font=FONT_B)
    x0, y0, bw, bh = W - 560, 16, 150, 14
    d.text((x0 - 50, 12), 'Atem', fill=(200, 205, 215), font=FONT_S)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], outline=(160, 170, 185))
    d.rectangle([x0, y0, x0 + int(bw * BREATH[f]), y0 + bh], fill=(120, 200, 140))
    lx = x0 + bw + 22
    d.ellipse([lx, y0 - 1, lx + 16, y0 + 15], fill=(250, 210, 90) if BLINK[f] > 0.05 else (60, 66, 78), outline=(200, 200, 215))
    d.text((lx + 22, 12), 'Lidschlag', fill=(200, 205, 215), font=FONT_S)
    d.text((W - 205, 12), label, fill=(150, 220, 255), font=FONT)
    return g


first = composite(0, 'Echtzeit')
h, w = first.height, first.width
vw = cv2.VideoWriter(out_mp4, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (w, h))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + out_mp4)
buf = []
for f in range(NF):
    a = cv2.cvtColor(np.array(composite(f, 'Echtzeit')), cv2.COLOR_RGB2BGR)
    buf.append(cv2.imencode('.png', a)[1])
    vw.write(a)
for b in buf:
    vw.write(cv2.imdecode(b, cv2.IMREAD_COLOR))
del buf
for f in range(NF):
    a = cv2.cvtColor(np.array(composite(f, 'halbe Geschw.')), cv2.COLOR_RGB2BGR)
    vw.write(a)
    vw.write(a)
vw.release()
cap = cv2.VideoCapture(out_mp4)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
ok, fr = cap.read()
cap.release()
print('wrote', out_mp4, os.path.getsize(out_mp4) // 1024, 'KB', '%d x %d' % (w, h), '%.1f s' % (4 * NF / float(FPS)), '| read back frames', n, ok)
