"""
Yoru - WALK POLISH, round 2 media (system python with OpenCV + Pillow, no ffmpeg).
  python build_walk_polish_media_r2.py variants <work dir> <out dir>
      walk_polish_r2_arm_varianten.mp4   columns Old | A | B | C, rows close-up side / close-up front; 4 loops real time, 2 at half speed
      walk_polish_r2_arm_bahnen.png      right arm seen from above and from the front (chest frame): wrist and elbow path, old / r1 / A
  python build_walk_polish_media_r2.py game <frames dir> <out dir> <label1=subdir1> <label2=subdir2> [...]
      walk_polish_r2_tempo_spielkamera.mp4   game-camera views side by side (frames from build_walk_polish_gameview.py), real time then half
"""
import sys, os, json, math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

MODE = sys.argv[1]
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 19)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)


def write_video(path, frames_fn, n_real, n_half, size):
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 30, size)
    if not vw.isOpened():
        raise SystemExit('video writer could not open ' + path)
    for i in range(n_real):
        vw.write(frames_fn(i, 'real time'))
    for i in range(n_half):
        a = frames_fn(i, 'half speed')
        vw.write(a)
        vw.write(a)
    vw.release()
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    print('video', path, os.path.getsize(path) // 1024, 'KB', size, '%.1f s' % (n / 30.0), flush=True)


if MODE == 'variants':
    WORK, OUT = sys.argv[2], sys.argv[3]
    os.makedirs(OUT, exist_ok=True)
    NF = 21
    COLS = [('frames_old', 'OLD (in the game)'), ('frames_r2A', 'A  clean plane'), ('frames_r2B', 'B  calmer'), ('frames_r2C', 'C  no drag')]
    ROWS = (('closeSide', (60, 0, 420, 430)), ('closeFront', (60, 40, 360, 400)))
    cw, ch, top, bottom = 270, 330, 36, 30
    VW, VH = cw * len(COLS), top + ch * len(ROWS) + bottom

    def frame(i, label):
        g = Image.new('RGB', (VW, VH), BG)
        d = ImageDraw.Draw(g)
        f = i % NF
        for c, (sub, title) in enumerate(COLS):
            for r, (view, box) in enumerate(ROWS):
                im = Image.open(os.path.join(WORK, sub, '%s_%03d.png' % (view, f))).convert('RGB').crop(box).resize((cw, ch), Image.LANCZOS)
                g.paste(im, (c * cw, top + r * ch))
            d.text((c * cw + 8, 8), title, fill=(255, 226, 120), font=F_B)
            if c:
                d.line([(c * cw, top), (c * cw, top + ch * len(ROWS))], fill=BG, width=3)
        d.text((8, top + ch * len(ROWS) + 6), '%s   frame %2d / 21   top: from her right side   bottom: from the front' % (label, f),
               fill=(150, 220, 255), font=F)
        return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)
    write_video(os.path.join(OUT, 'walk_polish_r2_arm_varianten.mp4'), frame, 4 * NF, 2 * NF, (VW, VH))

    # path plot: right arm, chest frame, centimetres from the shoulder joint
    tr = {k: json.load(open(os.path.join(WORK, 'trace_%s.json' % k))) for k in ('old', 'r1', 'r2A')}
    COL = {'old': (170, 170, 170), 'r1': (240, 90, 80), 'r2A': (90, 220, 120)}
    NAME = {'old': 'old walk', 'r1': 'round 1', 'r2A': 'round 2 A'}
    pw, ph_ = 460, 380
    img = Image.new('RGB', (2 * pw, ph_ + 70), BG)
    d = ImageDraw.Draw(img)

    def panel(x0, title, axis_h, axis_v, rng_h, rng_v, lab_h, lab_v):
        d.rectangle([x0 + 50, 40, x0 + pw - 20, ph_ - 10], outline=(80, 84, 92))
        d.text((x0 + 50, 12), title, fill=(255, 226, 120), font=F_B)
        d.text((x0 + 55, ph_ - 32), lab_h, fill=(150, 150, 150), font=F)
        d.text((x0 + 55, 44), lab_v, fill=(150, 150, 150), font=F)

        def P(v):
            h = x0 + 50 + (v[axis_h] - rng_h[0]) / (rng_h[1] - rng_h[0]) * (pw - 70)
            vv = ph_ - 10 - (v[axis_v] - rng_v[0]) / (rng_v[1] - rng_v[0]) * (ph_ - 50)
            return h, vv
        for k, t in tr.items():
            for joint, wdt in (('W', 3), ('E', 2)):
                pts = [P([100.0 * c for c in r[joint]]) for r in t['R']]
                d.line(pts, fill=COL[k], width=wdt)
                for q in pts[:-1]:
                    d.ellipse([q[0] - 2, q[1] - 2, q[0] + 2, q[1] + 2], fill=COL[k])
    panel(0, 'right arm seen from above', 1, 0, (-12, 26), (4, 19), 'forward ->', 'out to her right (up)')
    panel(pw, 'right arm seen from the front', 0, 2, (4, 19), (-44, -16), 'out to her right ->', 'up')
    y = ph_ + 8
    for i, k in enumerate(tr):
        d.line([(60 + i * 250, y + 10), (100 + i * 250, y + 10)], fill=COL[k], width=4)
        d.text((108 + i * 250, y + 2), NAME[k], fill=(230, 230, 230), font=F)
    d.text((60, y + 30), 'thick line = wrist, thin line = elbow, one dot per frame (21 per cycle); cm from the shoulder joint, in the chest frame',
           fill=(150, 150, 150), font=F)
    img.save(os.path.join(OUT, 'walk_polish_r2_arm_bahnen.png'))
    print('plot', os.path.join(OUT, 'walk_polish_r2_arm_bahnen.png'), flush=True)

elif MODE == 'game':
    SRC, OUT = sys.argv[2], sys.argv[3]
    cols = [a.split('=', 1) for a in sys.argv[4:]]
    os.makedirs(OUT, exist_ok=True)
    n = min(len([f for f in os.listdir(os.path.join(SRC, sub)) if f.endswith('.png')]) for _, sub in cols)
    w0, h0 = Image.open(os.path.join(SRC, cols[0][1], 'g_%03d.png' % 0)).size
    top, bottom = 34, 28
    VW, VH = w0 * len(cols), top + h0 + bottom

    def frame(i, label):
        g = Image.new('RGB', (VW, VH), BG)
        d = ImageDraw.Draw(g)
        for c, (title, sub) in enumerate(cols):
            g.paste(Image.open(os.path.join(SRC, sub, 'g_%03d.png' % (i % n))).convert('RGB'), (c * w0, top))
            d.text((c * w0 + 8, 7), title, fill=(255, 226, 120), font=F_B)
            if c:
                d.line([(c * w0, top), (c * w0, top + h0)], fill=BG, width=3)
        d.text((8, top + h0 + 5), '%s   t = %.2f s   game camera: behind, 4.4 m, pivot 1.35 m, shoulder offset 0.35 m, 15 deg down, 60 deg FOV'
               % (label, (i % n) / 30.0), fill=(150, 220, 255), font=F)
        return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)
    write_video(os.path.join(OUT, 'walk_polish_r2_tempo_spielkamera.mp4'), frame, n, n, (VW, VH))
