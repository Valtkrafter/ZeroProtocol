"""Gait diagram of the run: which foot is on the ground, ground speed under the character (blue) and height of the pelvis (orange) over one cycle.
The speed is the model of build_run.py (speed_var: a dip while a foot is on the ground), the pelvis height is read from the finished keys.
usage: python make_run_plot.py <Blender dir> <out png>"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont

base, out = sys.argv[1], sys.argv[2]
g = json.load(open(os.path.join(base, 'Yoru_Run_gait.json')))
p = json.load(open(os.path.join(base, 'Yoru_Run_pose.json')))
sv = g['speed_variation']
NF = g['frames']
T = g['cycle_seconds']
B = sv['stance_share']
speed = sv['speed_per_frame']
z = [f['hips_world_offset'][2] for f in p['data'][:NF + 1]]
zm = sum(z[:NF]) / NF
z = [(v - zm) * 1000.0 for v in z]
try:
    F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    FB = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 24)
except Exception:
    F = FB = ImageFont.load_default()
W, H = 1400, 700
x0, x1, y0, y1 = 110, W - 110, 190, H - 100
im = Image.new('RGB', (W, H), (24, 27, 34))
d = ImageDraw.Draw(im)
d.text((x0, 18), 'Sprint: ein Doppelschritt (%.2f s, %.0f Schritte pro Minute, %.1f m/s)' % (T, g['steps_per_minute'], g['speed']), fill=(255, 255, 255), font=FB)
smin, smax = 4.5, 5.3
zmin_, zmax_ = -35.0, 35.0


def X(i):
    return x0 + (x1 - x0) * i / NF


def XP(ph):
    return x0 + (x1 - x0) * ph


def YS(v):
    return y1 - (y1 - y0) * (v - smin) / (smax - smin)


def YZ(v):
    return y1 - (y1 - y0) * (v - zmin_) / (zmax_ - zmin_)


# contact bars (right foot 0 .. B, left foot 0.5 .. 0.5 + B), flight in between
for row, (lab, off) in enumerate((('rechter Fuß', 0.0), ('linker Fuß', 0.5))):
    yy = 62 + row * 34
    d.text((x0 - 106, yy - 2), lab.replace(' Fuß', ' F.'), fill=(190, 190, 210), font=F)
    d.rectangle([x0, yy, x1, yy + 24], fill=(40, 44, 56))
    d.rectangle([XP(off), yy, XP(off + B), yy + 24], fill=(90, 210, 120))
    d.text((XP(off) + 6, yy), 'am Boden %.0f ms' % (1000.0 * B * T), fill=(10, 30, 15), font=F)
d.text((x0, 126), 'Flugphase: kein Fuß am Boden (%.0f ms nach jedem Schritt)' % (1000.0 * (0.5 - B) * T), fill=(255, 190, 90), font=F)
for v in (4.5, 4.7, 4.9, 5.1, 5.3):
    d.line([x0, YS(v), x1, YS(v)], fill=(56, 62, 76), width=1)
    d.text((x0 - 70, YS(v) - 11), '%.1f' % v, fill=(110, 190, 235), font=F)
for v in (-30, -20, -10, 0, 10, 20, 30):
    d.text((x1 + 14, YZ(v) - 11), '%+d' % v, fill=(240, 170, 90), font=F)
d.text((x0 - 100, y0 - 34), 'm/s', fill=(110, 190, 235), font=F)
d.text((x1 + 10, y0 - 58), 'Becken', fill=(240, 170, 90), font=F)
d.text((x1 + 10, y0 - 34), 'in mm', fill=(240, 170, 90), font=F)
for ph, lab in ((0.0, 'rechts setzt auf'), (0.5, 'links setzt auf'), (1.0, 'rechts setzt auf')):
    d.line([XP(ph), y0, XP(ph), y1], fill=(120, 120, 140), width=2)
    d.text((XP(ph) - 60, y1 + 8), lab, fill=(190, 190, 210), font=F)
d.line([x0, YS(g['speed']), x1, YS(g['speed'])], fill=(150, 210, 240), width=1)
d.text((x0 + 8, YS(g['speed']) - 26), 'Mittel %.1f m/s' % g['speed'], fill=(150, 210, 240), font=F)
d.line([(X(i), YZ(z[i])) for i in range(NF + 1)], fill=(240, 170, 90), width=3)
d.line([(X(i), YS(speed[i])) for i in range(NF + 1)], fill=(90, 200, 235), width=4)
lo, hi = min(speed), max(speed)
d.text((x0 + 8, y1 + 40), 'Tempo: langsamste Stelle %.2f m/s (Mitte der Standphase, Becken ganz unten), im Flug %.2f m/s = %.0f %% Schwankung; Becken %.0f mm Hub' % (
    lo, hi, 100 * (hi - lo) / (hi + lo), max(z) - min(z)), fill=(220, 220, 235), font=F)
im.save(out)
print('wrote', out, 'speed %.3f .. %.3f' % (lo, hi), 'pelvis %.1f mm' % (max(z) - min(z)))
