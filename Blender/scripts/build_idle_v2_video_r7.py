"""Video of the idle with the round 7 dynamics: four views side by side from build_idle_v2_render_r7.py (front34, head, tail, game).
usage: python build_idle_v2_video_r7.py <frames dir with stills_r7/> <out mp4> <curves json (round3_curves.json: breath and blink per frame)>
Two loops in real time, then one loop at half speed (every frame twice).  Every picture shows the frame, the time, a breath bar, a blink lamp
and a line with what happens right now (ear flick, listening ear, gust, tail curl, tail flick), so one knows where to look.
The event times are the ones of build_idle_v2_dynamics_r7.py (P7).  OpenCV mp4v.  Needs OpenCV and Pillow."""
import sys, os, json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out_mp4, curves = sys.argv[1], sys.argv[2], sys.argv[3]
C = json.load(open(curves))
NF, FPS = C['frames'], C['fps']
BREATH, BLINK = C['breath'], C['blink']
VIEWS = ['front34', 'head', 'tail', 'game']
TITLE_V = {'front34': 'VORN SCHRÄG', 'head': 'KOPF, OHREN, HAARE', 'tail': 'SCHWANZ (hinten schräg)', 'game': 'SPIELKAMERA'}
CROP = {'front34': (110, 30, 490, 700), 'head': (60, 0, 540, 720), 'tail': (60, 0, 540, 720), 'game': (110, 40, 490, 710)}
EVENTS = [(2.6, 3.0, 'Ohr links zuckt'), (3.4, 7.3, 'Ohr links lauscht'), (3.0, 4.9, 'Windböe'), (5.1, 5.5, 'Ohr rechts zuckt'),
          (5.3, 8.6, 'Schwanzspitze rollt ein und aus'), (7.4, 7.8, 'Ohr links zuckt leicht'), (7.9, 11.4, 'Ohr rechts lauscht'),
          (8.4, 10.2, 'Windböe'), (10.2, 10.8, 'Ohr rechts zuckt doppelt'), (10.6, 11.3, 'Spitzenflick')]
CW, CH, HEAD = 380, 670, 34
try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
    FONT_S = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    FONT_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
except Exception:
    FONT = FONT_S = FONT_B = ImageFont.load_default()


def cell(view, f):
    im = Image.open(os.path.join(src, 'stills_r7', '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP[view])
    if im.size != (CW, CH):
        sc = min(CW / im.width, CH / im.height)
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    canvas = Image.new('RGB', (CW, CH + HEAD), (30, 34, 42))
    canvas.paste(im, ((CW - im.width) // 2, HEAD + (CH - im.height) // 2))
    ImageDraw.Draw(canvas).text((10, 6), TITLE_V[view], fill=(255, 255, 255), font=FONT)
    return canvas


def composite(f, label):
    W = CW * len(VIEWS)
    g = Image.new('RGB', (W, CH + HEAD + 80), (22, 24, 29))
    for i, v in enumerate(VIEWS):
        g.paste(cell(v, f), (i * CW, 80))
    d = ImageDraw.Draw(g)
    t = f / float(FPS)
    d.text((12, 10), 'Yoru Idle v2, Runde 7: Ohren, Schwanz, Haare im Wind   Bild %3d / %d   t = %5.2f s' % (f, NF, t), fill=(255, 226, 120), font=FONT_B)
    x0, y0, bw, bh = W - 560, 14, 150, 14
    d.text((x0 - 50, 10), 'Atem', fill=(200, 205, 215), font=FONT_S)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], outline=(160, 170, 185))
    d.rectangle([x0, y0, x0 + int(bw * BREATH[f]), y0 + bh], fill=(120, 200, 140))
    lx = x0 + bw + 22
    d.ellipse([lx, y0 - 1, lx + 16, y0 + 15], fill=(250, 210, 90) if BLINK[f] > 0.05 else (60, 66, 78), outline=(200, 200, 215))
    d.text((lx + 22, 10), 'Lidschlag', fill=(200, 205, 215), font=FONT_S)
    d.text((W - 205, 10), label, fill=(150, 220, 255), font=FONT)
    now = [txt for a, b, txt in EVENTS if a <= t <= b]
    d.text((12, 46), 'Jetzt: ' + ('  |  '.join(now) if now else 'ruhig (leichter Wind, langsame Schwanzwelle)'), fill=(150, 230, 170), font=FONT)
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
