"""Stage comparison of the run: joint angles of the right leg frame by frame (thigh, knee, ankle) of two builds next to the targets of the order, and a side by
side video (side view) of the two builds.
usage: python make_run_compare.py <old table.txt> <new table.txt> <old stills dir> <new stills dir> <out dir> [labels "old|new"] [stance frames]
The tables are the per-frame leg tables of the audit (lines  frame phase | thigh | knee | ankle | ...); the stills are side_wide_<frame>.png of render_walk_stills.py."""
import os, re, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

old_t, new_t, old_s, new_s, out = sys.argv[1:6]
labels = sys.argv[6].split('|') if len(sys.argv) > 6 else ['Stufe 1 (vorher)', 'Stufe 2 (jetzt)']
STANCE = int(sys.argv[7]) if len(sys.argv) > 7 else 9
os.makedirs(out, exist_ok=True)
ROW = re.compile(r'^\s*(\d+)\s+([0-9.]+)\s*\|\s*([-+0-9.]+)\s*\|\s*([-+0-9.]+)\s*\|\s*([-+0-9.]+)\s*\|')


def table(path):
    rows = {}
    for ln in open(path, encoding='utf-8', errors='replace'):
        m = ROW.match(ln)
        if m:
            rows[int(m.group(1))] = (float(m.group(3)), float(m.group(4)), float(m.group(5)))
    assert len(rows) >= 36, (path, len(rows))
    return [rows[i] for i in range(36)]


A, B = table(old_t), table(new_t)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
FB = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 24)
W, H = 1500, 1150
im = Image.new('RGB', (W, H), (24, 27, 34))
d = ImageDraw.Draw(im)
d.text((40, 14), 'Rechtes Bein: Gelenkwinkel Bild für Bild (36 Bilder = 0,6 s), grün unterlegt = Fuß am Boden', fill=(255, 255, 255), font=FB)
d.rectangle([40, 52, 60, 66], fill=(130, 136, 150))
d.text((68, 48), labels[0], fill=(170, 175, 190), font=F)
d.rectangle([330, 52, 350, 66], fill=(255, 190, 90))
d.text((358, 48), labels[1], fill=(255, 210, 140), font=F)
d.rectangle([600, 52, 620, 66], fill=(70, 120, 90))
d.text((628, 48), 'Zielbereich der Vorgabe', fill=(160, 210, 175), font=F)

x0, x1 = 120, W - 40


def panel(top, height, title, idx, ymin, ymax, ticks, bands):
    y0, y1 = top, top + height
    d.rectangle([x0, y0, x1, y1], outline=(70, 76, 92))
    d.text((x0, y0 - 28), title, fill=(255, 255, 255), font=F)
    X = lambda i: x0 + (x1 - x0) * i / 36.0
    Y = lambda v: y1 - (y1 - y0) * (v - ymin) / (ymax - ymin)
    d.rectangle([X(0), y0 + 1, X(STANCE), y1 - 1], fill=(30, 46, 40))
    for lo, hi, txt in bands:
        d.rectangle([x0 + 1, Y(hi), x1 - 1, Y(lo)], fill=(40, 70, 56))
        d.text((x1 - 330, Y(hi) + 1), txt, fill=(140, 200, 160), font=F)
    for t in ticks:
        d.line([x0, Y(t), x1, Y(t)], fill=(60, 66, 80), width=1)
        d.text((x0 - 56, Y(t) - 10), '%+d' % t if t else '0', fill=(190, 190, 205), font=F)
    for i in range(0, 37, 6):
        d.line([X(i), y0, X(i), y1], fill=(50, 56, 70), width=1)
        d.text((X(i) - 8, y1 + 4), str(i), fill=(150, 155, 170), font=F)
    # old build: dashed
    pts = [(X(i), Y(A[i % 36][idx])) for i in range(37)]
    for k in range(len(pts) - 1):
        if k % 2 == 0:
            d.line([pts[k], pts[k + 1]], fill=(130, 136, 150), width=3)
    pts = [(X(i), Y(B[i % 36][idx])) for i in range(37)]
    d.line(pts, fill=(255, 190, 90), width=4)
    for i in range(36):
        d.ellipse([X(i) - 3, Y(B[i][idx]) - 3, X(i) + 3, Y(B[i][idx]) + 3], fill=(255, 190, 90))


panel(130, 280, 'Oberschenkel (Grad, + = Knie vor der Hüfte)', 0, -40, 80, [-30, -20, -10, 0, 10, 20, 30, 40, 50, 60, 70],
      [(-25, -22, 'Vorgabe hinten -22..-25'), (52, 55, 'Vorgabe vorn +52..+55')])
panel(500, 280, 'Knie (Grad Beugung)', 1, 0, 120, [0, 20, 40, 60, 80, 100],
      [(15, 20, 'Absprung 15..20'), (35, 42, 'Stütze 35..42')])
panel(870, 220, 'Sprunggelenk (Grad, + = Zehen zum Schienbein, - = Fuß gestreckt)', 2, -40, 35, [-30, -20, -10, 0, 10, 20, 30],
      [(-24, -20, 'Absprung -22'), (18, 22, 'Schwung +18..+22')])
d.text((x0, H - 36), 'Bild 0 = rechter Fuß setzt auf, Bild 9 = Absprung, Bild 18 = linker Fuß setzt auf', fill=(190, 190, 205), font=F)
im.save(os.path.join(out, 'run_winkel_vergleich.png'))
print('wrote', os.path.join(out, 'run_winkel_vergleich.png'))

# side by side video
CROP = (0, 40, 600, 700)
CW, CH = 600, 660
FPS_REAL = 60


def cell(folder, f, label):
    c = Image.open(os.path.join(folder, 'side_wide_%03d.png' % f)).convert('RGB').crop(CROP)
    cv = Image.new('RGB', (CW, CH + 34), (112, 124, 140))
    cv.paste(c, (0, 34))
    dd = ImageDraw.Draw(cv)
    dd.rectangle([0, 0, CW, 30], fill=(30, 34, 42))
    dd.text((10, 4), label, fill=(255, 255, 255), font=F)
    dd.text((CW - 150, 4), 'Bild %02d' % f, fill=(255, 220, 120), font=F)
    return cv


frames = []
for f in range(36):
    a, b = cell(old_s, f, labels[0]), cell(new_s, f, labels[1])
    g = Image.new('RGB', (CW * 2, CH + 34))
    g.paste(a, (0, 0))
    g.paste(b, (CW, 0))
    frames.append(g)


def write(path, fps, repeat):
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (frames[0].width, frames[0].height))
    for _ in range(repeat):
        for g in frames:
            vw.write(cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR))
    vw.release()
    print('wrote', path, os.path.getsize(path) // 1024, 'KB')


write(os.path.join(out, 'run_vergleich.mp4'), FPS_REAL, 8)
write(os.path.join(out, 'run_vergleich_slow.mp4'), FPS_REAL // 4, 3)
