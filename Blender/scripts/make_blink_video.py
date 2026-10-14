"""Videos of the blink: the whole body from the front + the face close-up + a graph of the lid closure with a moving cursor.
usage: python make_blink_video.py <body stills dir (front_000.png ..)> <blink stills dir (face_fNNN.png, eyes_fNNN.png)> <Yoru_Blink.json> <out dir>
writes  walk_blink.mp4 (full timeline, 30 fps), walk_blink_doppel.gif (the double blink, 2x slower), blink_augen.mp4 (eyes close-up + graph),
        blink_streifen.png (one blink frame by frame, eyes), blink_kurve.png (the curve of all blinks)"""
import sys, os, json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

body_dir, blink_dir, jpath, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
D = json.load(open(jpath))
W = D['weights_per_frame']
NFR = len(W)
FPS = D['fps']
PER = D['gait_period_frames']
try:
    F22 = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
    F18 = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
    F30 = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 30)
except Exception:
    F22 = F18 = F30 = ImageFont.load_default()

blink_frames = [(i, b) for i, b in enumerate(D['blinks'])]
labels = {}
for g in D['groups']:
    if len(g) == 2:
        labels[round(g[0]['start'], 4)] = 'Doppel'
        labels[round(g[1]['start'], 4)] = None
for i, b in blink_frames:
    if b['amp'] < 0.9 and round(b['start'], 4) not in labels:
        labels[round(b['start'], 4)] = 'leicht'


def open_img(path):
    return Image.open(path).convert('RGB')


def face_img(kind, f):
    p = os.path.join(blink_dir, '%s_f%03d.png' % (kind, f))
    if not os.path.exists(p):
        p = os.path.join(blink_dir, '%s_f%03d.png' % (kind, f % PER))
    return open_img(p)


def bar(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 30], fill=(30, 34, 42))
    d.text((10, 4), text, fill=(255, 255, 255), font=F22)
    return im


def graph(width, height, f, x0=70, x1=None, label=True):
    """weight over time (the whole timeline) with a cursor at frame f"""
    x1 = width - 25 if x1 is None else x1
    g = Image.new('RGB', (width, height), (24, 27, 34))
    d = ImageDraw.Draw(g)
    top, bot = 34, height - 28
    d.text((8, 2), 'Lid-Schluss', fill=(190, 200, 215), font=F18)
    for frac, txt in ((1.0, '100%'), (0.5, '50%'), (0.0, '0%')):
        y = bot - frac * (bot - top)
        d.line([x0, y, x1, y], fill=(60, 66, 80), width=1)
        d.text((x0 - 46, y - 9), txt, fill=(150, 160, 175), font=F18)
    secs = NFR / FPS
    for s in range(0, int(secs) + 1):
        x = x0 + (x1 - x0) * s / secs
        d.line([x, bot, x, bot + 5], fill=(150, 160, 175))
        if s % 2 == 0:
            d.text((x - 8, bot + 6), '%ds' % s, fill=(150, 160, 175), font=F18)
    pts = [(x0 + (x1 - x0) * i / (NFR - 1), bot - W[i] * (bot - top)) for i in range(NFR)]
    poly = [(x0, bot)] + pts + [(x1, bot)]
    d.polygon(poly, fill=(52, 96, 120))
    d.line(pts, fill=(90, 200, 235), width=2)
    for i, b in blink_frames:
        key = round(b['start'], 4)
        if key in labels and labels[key]:
            x = x0 + (x1 - x0) * b['start'] / secs
            d.text((x - 18, top - 20), labels[key], fill=(255, 210, 120), font=F18)
    if f is not None:
        x = x0 + (x1 - x0) * f / (NFR - 1)
        d.line([x, top - 4, x, bot], fill=(255, 90, 90), width=2)
    return g


def compose(f):
    body = open_img(os.path.join(body_dir, 'front_%03d.png' % (f % PER)))
    face = face_img('face', f).resize((960, 720), Image.LANCZOS)
    bar(body, 'GANZER KÖRPER VORNE')
    bar(face, 'GESICHT   Zeit %5.2f s   Lid %3d %%' % (f / FPS, round(W[f] * 100)))
    top = Image.new('RGB', (body.width + face.width, 720))
    top.paste(body, (0, 0))
    top.paste(face, (body.width, 0))
    g = graph(top.width, 130, f)
    im = Image.new('RGB', (top.width, 720 + 130))
    im.paste(top, (0, 0))
    im.paste(g, (0, 720))
    return im


# ---------------------------------------------------------------- 1. full video
first = compose(0)
vw = cv2.VideoWriter(os.path.join(out, 'walk_blink.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), FPS, first.size)
for f in range(NFR):
    vw.write(cv2.cvtColor(np.array(compose(f)), cv2.COLOR_RGB2BGR))
vw.release()
print('walk_blink.mp4', os.path.getsize(os.path.join(out, 'walk_blink.mp4')) // 1024, 'KB')

# ---------------------------------------------------------------- 2. eyes close-up video + graph
vw = cv2.VideoWriter(os.path.join(out, 'blink_augen.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), FPS, (800, 600 + 110))
for f in range(NFR):
    e = bar(face_img('eyes', f), 'AUGEN   Zeit %5.2f s   Lid %3d %%' % (f / FPS, round(W[f] * 100)))
    g = graph(800, 110, f, x0=60, x1=775)
    im = Image.new('RGB', (800, 710))
    im.paste(e, (0, 0))
    im.paste(g, (0, 600))
    vw.write(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
vw.release()
print('blink_augen.mp4', os.path.getsize(os.path.join(out, 'blink_augen.mp4')) // 1024, 'KB')

# ---------------------------------------------------------------- 3. the double blink as a GIF, half speed
dbl = [b for g in D['groups'] if len(g) == 2 for b in g]
if dbl:
    f0 = max(0, int(dbl[0]['start'] * FPS) - 6)
    f1 = min(NFR - 1, int(dbl[1]['end'] * FPS) + 6)
    frames = []
    for f in range(f0, f1 + 1):
        im = compose(f)
        frames.append(im.resize((im.width * 6 // 10, im.height * 6 // 10), Image.LANCZOS))
    frames[0].save(os.path.join(out, 'walk_blink_doppel.gif'), save_all=True, append_images=frames[1:], duration=int(2000 / FPS), loop=0, optimize=False)
    print('walk_blink_doppel.gif', os.path.getsize(os.path.join(out, 'walk_blink_doppel.gif')) // 1024, 'KB', 'frames', f0, '..', f1, '(half speed)')

# ---------------------------------------------------------------- 4. film strip of one full blink (eyes)
full = [b for b in D['blinks'] if b['amp'] > 0.99]
if full:
    b = full[len(full) // 2]
    f0 = int(b['start'] * FPS) - 1
    f1 = int(b['end'] * FPS) + 2
    fs = list(range(f0, f1 + 1))
    cols = 4
    rows = (len(fs) + cols - 1) // cols
    tw, th = 400, 300
    sheet = Image.new('RGB', (cols * tw, rows * (th + 0)), (20, 22, 28))
    for k, f in enumerate(fs):
        im = face_img('eyes', f).resize((tw, th), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, tw, 26], fill=(30, 34, 42))
        d.text((8, 3), 'Bild %d   %.0f ms   Lid %3d %%' % (f, (f - f0) * 1000.0 / FPS, round(W[f] * 100)), fill=(255, 255, 255), font=F18)
        sheet.paste(im, ((k % cols) * tw, (k // cols) * th))
    sheet.save(os.path.join(out, 'blink_streifen.png'))
    print('blink_streifen.png', sheet.size, 'frames', fs[0], '..', fs[-1])

# ---------------------------------------------------------------- 5. the curve of one blink (smooth) with the 30 fps samples as dots, and of the double blink
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blink_model as bm
Wd, Hd = 1500, 560
cv = Image.new('RGB', (Wd, Hd), (24, 27, 34))
d = ImageDraw.Draw(cv)


def plot(box, blinks, t0, t1, title, note=None):
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], outline=(70, 78, 94))
    d.text((x0 + 8, y0 + 4), title, fill=(255, 255, 255), font=F22)
    for frac in (0.0, 0.5, 1.0):
        y = y1 - 30 - frac * (y1 - y0 - 80)
        d.line([x0, y, x1, y], fill=(52, 58, 72))
        d.text((x0 - 44, y - 9), '%d%%' % (frac * 100), fill=(150, 160, 175), font=F18)
    ms = int((t1 - t0) * 1000)
    for m in range(0, ms + 1, 100):
        x = x0 + (x1 - x0) * m / ms
        d.line([x, y1 - 30, x, y1 - 24], fill=(150, 160, 175))
        d.text((x - 14, y1 - 22), '%d ms' % m, fill=(150, 160, 175), font=F18)
    pts = []
    n = 800
    for k in range(n + 1):
        t = t0 + (t1 - t0) * k / n
        w = max((b.lid(t) for b in blinks), default=0.0)
        pts.append((x0 + (x1 - x0) * k / n, y1 - 30 - w * (y1 - y0 - 80)))
    d.line(pts, fill=(90, 200, 235), width=3)
    f_a = int(np.ceil(t0 * FPS))
    f_b = int(np.floor(t1 * FPS))
    for f in range(f_a, f_b + 1):
        t = f / FPS
        w = max((b.lid(t) for b in blinks), default=0.0)
        x = x0 + (x1 - x0) * (t - t0) / (t1 - t0)
        y = y1 - 30 - w * (y1 - y0 - 80)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 190, 80), outline=(255, 255, 255))
    if note:
        d.text((x0 + 150, y0 + 70), note, fill=(190, 200, 215), font=F18)


one = full[len(full) // 2] if full else D['blinks'][0]
b1 = bm.Blink(one['start'], one['amp'], one['close'], one['hold'], one['open'])
plot((60, 10, 760, 540), [b1], b1.start - 0.04, b1.start + 0.42,
     'Ein Blinzeln (Kurve) und die Bilder bei 30 fps (Punkte)',
     'schließt in %d ms, zu %d ms, öffnet in %d ms' % (round(b1.close * 1000), round(b1.hold * 1000), round(b1.open * 1000)))
if dbl:
    bb = [bm.Blink(x['start'], x['amp'], x['close'], x['hold'], x['open']) for x in dbl]
    plot((800, 10, 1480, 540), bb, bb[0].start - 0.04, bb[0].start + 0.62,
         'Doppelblinzeln: das 2. beginnt, während das Lid noch öffnet',
         '2. Blinzeln %d ms nach dem Start des 1., Stärke %d %%' % (round((bb[1].start - bb[0].start) * 1000), round(bb[1].amp * 100)))
cv.save(os.path.join(out, 'blink_kurve.png'))
print('blink_kurve.png')
