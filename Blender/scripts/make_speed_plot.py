"""Picture of the walking speed within one gait cycle: ground speed under the character (blue) and height of the pelvis (orange),
with the heel strikes. The speed is the model of build_walk.py (speed_var), the pelvis height is read from the finished keys.
usage: python make_speed_plot.py <Blender dir> <out png>"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

base, out = sys.argv[1], sys.argv[2]
g = json.load(open(os.path.join(base, 'Yoru_Walk_gait.json')))
p = json.load(open(os.path.join(base, 'Yoru_Walk_pose.json')))
sv = g['speed_variation']
NF = g['frames']
T = g['cycle_seconds']
speed = sv['speed_per_frame']                                   # NF + 1 values, m/s
z = [f['hips_world_offset'][2] for f in p['data'][:NF + 1]]
zm = sum(z[:NF]) / NF
z = [(v - zm) * 1000.0 for v in z]                              # mm around the mean
try:
    F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    FB = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 24)
except Exception:
    F = FB = ImageFont.load_default()
W, H = 1400, 620
x0, x1, y0, y1 = 110, W - 110, 80, H - 90
im = Image.new('RGB', (W, H), (24, 27, 34))
d = ImageDraw.Draw(im)
d.text((x0, 20), 'Gehgeschwindigkeit innerhalb eines Doppelschritts (%.2f s)' % T, fill=(255, 255, 255), font=FB)
smin, smax = 1.05, 1.25
zmin_, zmax_ = -16.0, 16.0


def X(i):
    return x0 + (x1 - x0) * i / NF


def YS(v):
    return y1 - (y1 - y0) * (v - smin) / (smax - smin)


def YZ(v):
    return y1 - (y1 - y0) * (v - zmin_) / (zmax_ - zmin_)


for v in (1.05, 1.10, 1.15, 1.20, 1.25):
    d.line([x0, YS(v), x1, YS(v)], fill=(56, 62, 76), width=1)
    d.text((x0 - 70, YS(v) - 11), '%.2f' % v, fill=(110, 190, 235), font=F)
for v in (-15, -10, -5, 0, 5, 10, 15):
    d.text((x1 + 14, YZ(v) - 11), '%+d' % v, fill=(240, 170, 90), font=F)
d.text((x0 - 100, y0 - 38), 'm/s', fill=(110, 190, 235), font=F)
d.text((x1 + 10, y0 - 62), 'Becken', fill=(240, 170, 90), font=F)
d.text((x1 + 10, y0 - 38), 'in mm', fill=(240, 170, 90), font=F)
# heel strikes
for ph, lab in ((0.0, 'rechte Ferse'), (0.5, 'linke Ferse'), (1.0, 'rechte Ferse')):
    xx = x0 + (x1 - x0) * ph
    d.line([xx, y0, xx, y1], fill=(120, 120, 140), width=2)
    d.text((xx - 50, y1 + 8), lab, fill=(190, 190, 210), font=F)
# double support bands (10 % after each heel strike)
for a in (0.0, 0.5):
    d.rectangle([x0 + (x1 - x0) * a, y0, x0 + (x1 - x0) * (a + 0.10), y1], outline=None, fill=None)
    d.text((x0 + (x1 - x0) * (a + 0.012), y0 + 4), 'beide Füße am Boden', fill=(150, 150, 170), font=F)
# mean line
d.line([x0, YS(g['speed']), x1, YS(g['speed'])], fill=(150, 210, 240), width=1)
d.text((x0 + 8, YS(g['speed']) - 26), 'Mittel %.2f m/s' % g['speed'], fill=(150, 210, 240), font=F)
pts = [(X(i), YZ(z[i])) for i in range(NF + 1)]
d.line(pts, fill=(240, 170, 90), width=3)
pts = [(X(i), YS(speed[i])) for i in range(NF + 1)]
d.line(pts, fill=(90, 200, 235), width=4)
for i in range(NF + 1):
    d.ellipse([X(i) - 4, YS(speed[i]) - 4, X(i) + 4, YS(speed[i]) + 4], fill=(90, 200, 235))
lo, hi = min(speed), max(speed)
d.text((x0 + 8, y1 + 40), 'Schnellste Stelle %.3f m/s (Ferse setzt auf, Becken ganz unten), langsamste %.3f m/s (Becken ganz oben) = +-%.0f %% um den Mittelwert' % (hi, lo, 100 * (hi - lo) / (hi + lo)),
       fill=(220, 220, 235), font=F)
im.save(out)
print('wrote', out, 'speed %.3f .. %.3f' % (lo, hi))
