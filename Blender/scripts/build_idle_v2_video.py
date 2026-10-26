"""Video and strip of the idle v2 loop from the rendered frames (build_idle_v2_render_r2.py, views front34, side, game, frames 0 .. NF-1).
usage: python build_idle_v2_video.py <frames dir with stills_A2/> <out mp4> <out strip png> [nf=240] [fps=30] [variant=A2]
The mp4 shows the three views side by side: two loops in real time, then one loop at half speed (every frame twice).  Every picture shows
the frame, the time and a bar for the breath (in / out).  The strip shows 10 pictures spread evenly over the loop (front three-quarter view).
Blender 5.1 here has no video output, so the encoding happens here (OpenCV, mp4v; ffmpeg is not installed).  Needs OpenCV and Pillow.
The breath curve is the one of build_idle_v2_loop.py (same numbers, repeated here because this script runs outside Blender)."""
import sys, os, math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out_mp4, out_strip = sys.argv[1], sys.argv[2], sys.argv[3]
NF = int(sys.argv[4]) if len(sys.argv) > 4 else 240
FPS = int(sys.argv[5]) if len(sys.argv) > 5 else 30
VAR = sys.argv[6] if len(sys.argv) > 6 else 'A2'
LOOP = NF / float(FPS)
TAU = 2.0 * math.pi


def breath(t, period=4.0, warp=0.15, depth2=0.84):
    ph = (t / period) % 1.0
    w = ph + warp * math.sin(TAU * ph)
    b = 0.5 - 0.5 * math.cos(TAU * w)
    depth = 0.5 * (1.0 + depth2) + 0.5 * (1.0 - depth2) * math.cos(TAU / LOOP * (t - 1.7))
    return b * depth


CROP = {'front34': (110, 30, 490, 700), 'side': (110, 30, 490, 700), 'game': (110, 40, 490, 710)}
TITLE = {'front34': 'VORN SCHRÄG', 'side': 'SEITE (von rechts)', 'game': 'SPIELKAMERA (hinten rechts)'}
VIEWS = ['front34', 'side', 'game']
CW, CH = 380, 670
HEAD = 34
try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    FONT_S = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    FONT_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
except Exception:
    FONT = FONT_S = FONT_B = ImageFont.load_default()


def frame_path(view, f):
    return os.path.join(src, 'stills_%s' % VAR, '%s_%03d.png' % (view, f))


def cell(view, f):
    im = Image.open(frame_path(view, f)).convert('RGB').crop(CROP[view])
    canvas = Image.new('RGB', (CW, CH + HEAD), (30, 34, 42))
    canvas.paste(im, (0, HEAD))
    d = ImageDraw.Draw(canvas)
    d.text((10, 6), TITLE[view], fill=(255, 255, 255), font=FONT)
    return canvas


def composite(f, label):
    cells = [cell(v, f) for v in VIEWS]
    W = CW * len(VIEWS)
    g = Image.new('RGB', (W, CH + HEAD + 46), (22, 24, 29))
    for i, c in enumerate(cells):
        g.paste(c, (i * CW, 46))
    d = ImageDraw.Draw(g)
    t = f / float(FPS)
    b = breath(t)
    d.text((12, 12), 'Yoru Idle v2 (A2), Blockout   Bild %3d / %d   t = %4.2f s' % (f, NF, t), fill=(255, 226, 120), font=FONT_B)
    d.text((W - 300, 14), label, fill=(150, 220, 255), font=FONT)
    # breath bar
    x0, y0, bw, bh = W - 520, 16, 180, 14
    d.rectangle([x0, y0, x0 + bw, y0 + bh], outline=(160, 170, 185))
    d.rectangle([x0, y0, x0 + int(bw * b), y0 + bh], fill=(120, 200, 140))
    d.text((x0 - 62, 12), 'Atem', fill=(200, 205, 215), font=FONT_S)
    return g


first = composite(0, 'Echtzeit')
h, w = first.height, first.width
vw = cv2.VideoWriter(out_mp4, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (w, h))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + out_mp4)
rt = []                                                   # the real-time pictures are kept as BGR arrays for the second loop
for f in range(NF):
    a = cv2.cvtColor(np.array(composite(f, 'Echtzeit')), cv2.COLOR_RGB2BGR)
    rt.append(cv2.imencode('.png', a)[1])
    vw.write(a)
for buf in rt:
    vw.write(cv2.imdecode(buf, cv2.IMREAD_COLOR))
del rt
for f in range(NF):
    a = cv2.cvtColor(np.array(composite(f, 'halbe Geschwindigkeit')), cv2.COLOR_RGB2BGR)
    vw.write(a)
    vw.write(a)
vw.release()
print('wrote', out_mp4, os.path.getsize(out_mp4) // 1024, 'KB', '%d x %d' % (w, h), '%.1f s' % ((2 * NF + 2 * NF) / float(FPS)))
# check: read the video back
cap = cv2.VideoCapture(out_mp4)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
ok, fr = cap.read()
cap.release()
print('read back: frames', n, 'first frame ok', ok, fr.shape if ok else None)

# strip: 10 pictures spread over the loop (front three-quarter), with time and breath
picks = [int(round(i * NF / 10.0)) for i in range(10)]
SW, SH = 190, 410
strip = Image.new('RGB', (SW * 10, SH + 70), (22, 24, 29))
ds = ImageDraw.Draw(strip)
ds.text((10, 8), 'Yoru Idle v2 (A2), Blockout: 10 Bilder über die Schleife (%.0f s, %d fps), Ansicht vorn schräg' % (LOOP, FPS), fill=(255, 226, 120), font=FONT_S)
for i, f in enumerate(picks):
    im = Image.open(frame_path('front34', f)).convert('RGB').crop((150, 40, 450, 690)).resize((SW, SH), Image.LANCZOS)
    strip.paste(im, (i * SW, 34))
    t = f / float(FPS)
    b = breath(t)
    ds.text((i * SW + 8, SH + 38), 'Bild %d  t %.1f s' % (f, t), fill=(220, 225, 235), font=FONT_S)
    ds.rectangle([i * SW + 8, SH + 58, i * SW + 8 + 120, SH + 66], outline=(150, 160, 175))
    ds.rectangle([i * SW + 8, SH + 58, i * SW + 8 + int(120 * b), SH + 66], fill=(120, 200, 140))
strip.save(out_strip)
print('wrote', out_strip, strip.size)
