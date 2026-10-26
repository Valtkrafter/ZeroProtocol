"""Lauf v2: comparison video NTE (left) against Yoru (right), two rows: side (NTE clip 194135 from frame 96) and from behind (game camera;
NTE clip 194448 from frame 0).  30 fps; Yoru's 60 fps frames are taken every second frame and aligned to the NTE phase:
  side: NTE n <-> Yoru frame (2 n - 181) mod 40      back: NTE n <-> Yoru frame (2 n - 119) mod 40
(right touchdown at NTE side 110.5 / back 59.5 = Yoru frame 0).  6 cycles in real time, then 3 cycles at half speed (every frame twice).
NTE crops follow the character (hair track smoothed over +-10 frames), the same size as the strips.  Titles on a bar above, the speed on a
bar below, nothing overlaps the pictures.
usage: python -I build_lauf_v2_media.py <frames dir with Neu/> <out mp4> [side view name] [back view name]"""
import sys, os, json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, video = sys.argv[1], sys.argv[2]
SV = sys.argv[3] if len(sys.argv) > 3 else 'side95'
BV = sys.argv[4] if len(sys.argv) > 4 else 'back88'
REF = r'C:\Users\valen\ZeroProtocol\Blender\previews\ref_nte'
TR = json.load(open(os.path.join(REF, 'nte_track_hair.json')))
FPS, NF = 30, 40
CW, CH, TOP, BOT = 380, 500, 44, 34
ROWS = [dict(clip='194135', n0=96, off=-181, view=SV, cw=380, label='Seite'),
        dict(clip='194448', n0=0, off=-119, view=BV, cw=360, label='Hinten (Spielkamera)')]
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
VW, VH = 2 * CW, TOP + 2 * CH + BOT


class Clip:
    def __init__(self, row):
        self.row = row
        self.cap = cv2.VideoCapture(os.path.join(REF, 'clips', 'Aufzeichnung 2026-10-23 %s.mp4' % row['clip']))
        tr = TR[row['clip']]
        cx = np.array(tr['cx'], dtype=float)
        cy = np.array(tr['cy'], dtype=float)
        n0 = row['n0']
        k = np.ones(21) / 21.0
        pad = np.pad(cx, 10, mode='edge')
        self.cx = np.convolve(pad, k, mode='valid')
        self.cy0 = float(np.nanmean(cy[n0:n0 + 120]))
        self.cache = {}

    def frame(self, n):
        if n in self.cache:
            return self.cache[n]
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, n)
        ok, f = self.cap.read()
        cw = self.row['cw']
        x = int(max(0, min(f.shape[1] - cw, self.cx[n] - cw / 2)))
        y = int(max(0, min(f.shape[0] - CH, self.cy0 - CH * 0.18)))
        c = cv2.cvtColor(f[y:y + CH, x:x + cw], cv2.COLOR_BGR2RGB)
        im = Image.new('RGB', (CW, CH), (22, 24, 29))
        im.paste(Image.fromarray(c), ((CW - cw) // 2, 0))
        self.cache[n] = im
        return im


clips = [Clip(r) for r in ROWS]
ycache = {}


def yoru(view, fr, cw):
    key = (view, fr)
    if key not in ycache:
        a = Image.open(os.path.join(src, 'Neu', '%s_%03d.png' % (view, fr))).convert('RGB').resize((cw, CH))
        im = Image.new('RGB', (CW, CH), a.getpixel((2, 2)))
        im.paste(a, ((CW - cw) // 2, 0))
        ycache[key] = im
    return ycache[key]


def compose(i, label):
    g = Image.new('RGB', (VW, VH), (22, 24, 29))
    d = ImageDraw.Draw(g)
    d.text((10, 11), 'NTE (Referenz)', fill=(255, 226, 120), font=F_B)
    d.text((CW + 10, 11), 'Yoru: Lauf W, Runde 1', fill=(255, 226, 120), font=F_B)
    for r, (row, clip) in enumerate(zip(ROWS, clips)):
        n = row['n0'] + i
        fr = (2 * n + row['off']) % NF
        y0 = TOP + r * CH
        g.paste(clip.frame(n), (0, y0))
        g.paste(yoru(row['view'], fr, row['cw']), (CW, y0))
        for x0 in (0, CW):
            d.rectangle([x0 + 6, y0 + 6, x0 + 14 + 9 * len(row['label']), y0 + 28], fill=(22, 24, 29))
            d.text((x0 + 10, y0 + 8), row['label'], fill=(200, 210, 225), font=F)
    d.line([(CW, TOP), (CW, TOP + 2 * CH)], fill=(22, 24, 29), width=3)
    d.line([(0, TOP + CH), (VW, TOP + CH)], fill=(22, 24, 29), width=3)
    d.text((10, TOP + 2 * CH + 8), '%s    Zyklus %d    t = %.2f s' % (label, i // 20 + 1, i / float(FPS)), fill=(150, 220, 255), font=F)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


vw = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (VW, VH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + video)
for i in range(6 * 20):
    vw.write(compose(i, 'Echtzeit'))
for i in range(3 * 20):
    a = compose(i, 'halbe Geschwindigkeit')
    vw.write(a)
    vw.write(a)
vw.release()
cap = cv2.VideoCapture(video)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()
print('video', video, os.path.getsize(video) // 1024, 'KB', '%d x %d' % (VW, VH), 'frames', n, '%.1f s' % (n / float(FPS)))
