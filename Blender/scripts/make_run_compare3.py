"""Stage 3 comparison of the run: arms, head and tail frame by frame (36 frames = 0.6 s) of two builds next to the targets of the order, and a side by
side video (side view and front view) of the two builds.
usage: python make_run_compare3.py <old tables.json> <new tables.json> <old stills dir> <new stills dir> <out dir> [labels "old|new"]
The tables come from dump_s3_tables.py (per frame: arm angles, head yaw / pitch, tail directions); the stills are <view>_<frame>.png of render_walk_stills.py."""
import os, sys, json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

old_t, new_t, old_s, new_s, out = sys.argv[1:6]
labels = sys.argv[6].split('|') if len(sys.argv) > 6 else ['Stufe 2 (vorher)', 'Stufe 3 (jetzt)']
os.makedirs(out, exist_ok=True)
A, B = json.load(open(old_t)), json.load(open(new_t))
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
FB = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 24)
W, H = 1500, 1860
im = Image.new('RGB', (W, H), (24, 27, 34))
d = ImageDraw.Draw(im)
d.text((40, 14), 'Arme, Kopf und Schwanz: Winkel Bild für Bild (36 Bilder = 0,6 s), linker Arm', fill=(255, 255, 255), font=FB)
d.rectangle([40, 52, 60, 66], fill=(130, 136, 150))
d.text((68, 48), labels[0], fill=(170, 175, 190), font=F)
d.rectangle([330, 52, 350, 66], fill=(255, 190, 90))
d.text((358, 48), labels[1], fill=(255, 210, 140), font=F)
d.rectangle([600, 52, 620, 66], fill=(70, 120, 90))
d.text((628, 48), 'Zielbereich der Vorgabe', fill=(160, 210, 175), font=F)
x0, x1 = 120, W - 40


def panel(top, height, title, keys, ymin, ymax, ticks, bands, unit_fmt='%+d'):
    y0, y1 = top, top + height
    d.rectangle([x0, y0, x1, y1], outline=(70, 76, 92))
    d.text((x0, y0 - 28), title, fill=(255, 255, 255), font=F)
    X = lambda i: x0 + (x1 - x0) * i / 36.0
    Y = lambda v: y1 - (y1 - y0) * (min(max(v, ymin), ymax) - ymin) / (ymax - ymin)
    for lo, hi, txt in bands:
        d.rectangle([x0 + 1, Y(hi), x1 - 1, Y(lo)], fill=(40, 70, 56))
        d.text((x1 - 360, Y(hi) + 1), txt, fill=(140, 200, 160), font=F)
    for t in ticks:
        d.line([x0, Y(t), x1, Y(t)], fill=(60, 66, 80), width=1)
        d.text((x0 - 56, Y(t) - 10), unit_fmt % t if t else '0', fill=(190, 190, 205), font=F)
    for i in range(0, 37, 6):
        d.line([X(i), y0, X(i), y1], fill=(50, 56, 70), width=1)
        d.text((X(i) - 8, y1 + 4), str(i), fill=(150, 155, 170), font=F)
    for key, col_old, col_new in keys:
        pts = [(X(i), Y(A[i % 36][key])) for i in range(37)]
        for k in range(len(pts) - 1):
            if k % 2 == 0:
                d.line([pts[k], pts[k + 1]], fill=col_old, width=3)
        pts = [(X(i), Y(B[i % 36][key])) for i in range(37)]
        d.line(pts, fill=col_new, width=4)
        for i in range(36):
            d.ellipse([X(i) - 3, Y(B[i][key]) - 3, X(i) + 3, Y(B[i][key]) + 3], fill=col_new)


G, O = (130, 136, 150), (255, 190, 90)
G2, O2 = (110, 150, 170), (120, 210, 255)
panel(110, 220, 'Oberarm (Grad aus der Senkrechten, + = vor)', [('up_L', G, O)], -50, 50, [-40, -20, 0, 20, 40], [(-38, -38, 'Vorgabe hinten -38'), (38, 38, 'Vorgabe vorn +38')])
panel(400, 220, 'Ellbogenbeugung (Grad)', [('el_L', G, O)], 30, 120, [40, 60, 80, 100, 120], [(95, 100, 'Vorgabe vorn 95..100'), (40, 48, 'Vorgabe hinten 40..48')])
panel(690, 220, 'Unterarm-Richtung (0 = waagerecht nach vorn, + = nach oben, - = nach unten)', [('fa_L', G, O)], -90, 70, [-60, -30, 0, 30, 60], [])
panel(980, 220, 'Handgelenk gegenüber der Schulter (mm, 0 = Schulterhöhe, - = darunter)', [('wr_z_L', G, O)], -380, 0, [-300, -200, -100, 0], [], '%+d')
panel(1270, 200, 'Kopf: Drehung (Gelb/Orange) und Nicken (Hellblau) der Welt (Grad)', [('head_yaw', G, O), ('head_pitch', G2, O2)], -12, -6 + 10, [-10, -8, -4, 0, 2, 4], [(-2.0, 2.0, 'Vorgabe Drehung +-2,0')])
panel(1550, 200, 'Schwanz: Richtung über der Waagerechten, Basis (Orange) und Spitze (Hellblau), Grad', [('tail1_el', G, O), ('tail6_el', G2, O2)], -25, 40, [-20, 0, 20, 30, 40], [(25, 32, 'Vorgabe Basis +25..+32')])
d.text((x0, H - 36), 'Bild 0 = rechter Fuß setzt auf, linker Arm ist vorn', fill=(190, 190, 205), font=F)
im.save(os.path.join(out, 'run_arme_kopf_schwanz.png'))
print('wrote', os.path.join(out, 'run_arme_kopf_schwanz.png'))

# side by side video: side view above, front view below, old left, new right
CROP = {'side_wide': (0, 40, 600, 700), 'front': (110, 30, 510, 700)}
CW = {'side_wide': 600, 'front': 400}
CH = 660
FPS_REAL = 60


def cell(folder, view, f, label):
    c = Image.open(os.path.join(folder, '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP[view])
    cv = Image.new('RGB', (600, CH + 34), (112, 124, 140))
    cv.paste(c, ((600 - c.width) // 2, 34))
    dd = ImageDraw.Draw(cv)
    dd.rectangle([0, 0, 600, 30], fill=(30, 34, 42))
    dd.text((10, 4), label, fill=(255, 255, 255), font=F)
    dd.text((600 - 100, 4), 'Bild %02d' % f, fill=(255, 220, 120), font=F)
    return cv


frames = []
for f in range(36):
    g = Image.new('RGB', (600 * 2, (CH + 34) * 2))
    g.paste(cell(old_s, 'side_wide', f, labels[0] + ' - Seite'), (0, 0))
    g.paste(cell(new_s, 'side_wide', f, labels[1] + ' - Seite'), (600, 0))
    g.paste(cell(old_s, 'front', f, labels[0] + ' - vorne'), (0, CH + 34))
    g.paste(cell(new_s, 'front', f, labels[1] + ' - vorne'), (600, CH + 34))
    frames.append(g)


def write(path, fps, repeat):
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (frames[0].width, frames[0].height))
    for _ in range(repeat):
        for g in frames:
            vw.write(cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR))
    vw.release()
    print('wrote', path, os.path.getsize(path) // 1024, 'KB')


write(os.path.join(out, 'run_vergleich_stufe3.mp4'), FPS_REAL, 8)
write(os.path.join(out, 'run_vergleich_stufe3_slow.mp4'), FPS_REAL // 4, 3)
