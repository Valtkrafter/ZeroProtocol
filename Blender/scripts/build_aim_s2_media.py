"""
Yoru - AIM SUITE STAGE 2: preview video and clearance diagram of the three transitions (system python, run with -I; OpenCV + Pillow, H.264 through
mp4_to_h264.py / PyAV; there is no ffmpeg).
  python -I C:/Users/valen/ZeroProtocol/Blender/scripts/build_aim_s2_media.py <frames dir> <report .json> <video .mp4> <plot .png> [still=<png>]
  e.g. python -I .../build_aim_s2_media.py C:/Users/valen/ZeroProtocol/Blender/previews/Aim/s2/frames_r1 C:/Users/valen/ZeroProtocol/Blender/work/Aim/Yoru_Aim_s2_report.json
       C:/Users/valen/ZeroProtocol/Blender/previews/Aim/s2/aim_in_out_preview.mp4 C:/Users/valen/ZeroProtocol/Blender/previews/Aim/s2/aim_in_out_clearance.png
Video (60 fps): per clip (Aim_In, Sprint_To_Aim, Aim_Out) three panels side by side (front 3/4, side, the real game camera 0.35 m right); first in slow
motion (every frame 4 times = 1/4 speed), then once in real time (every frame once, first and last frame held a little); below: frame number and
the least distance to the gear below / above the belt line (1.00 m) in that frame, with the part (forearm + hand, elbow end, pistol) and the elbow out.
Plot: per clip the least distance per frame below (limit 15 mm) and above (limit 5 mm) the belt line; holster frames shaded (pistol not counted).
"""
import sys, os, json, subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FRAMES, REPORT, VIDEO, PLOT = sys.argv[1:5]
KV = dict(a.split('=', 1) for a in sys.argv[5:] if '=' in a)
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(REPORT))
CLIPS = [('Yoru_Aim_In', 'Aim_In: Ziehen aus dem Idle (0,20 s)'), ('Yoru_Sprint_To_Aim', 'Sprint_To_Aim: aus dem Sprint ins Zielen (0,18 s)'),
         ('Yoru_Aim_Out', 'Aim_Out: zurück ins Idle (0,25 s)')]
VIEWS = [('front34', 'schräg von vorn'), ('side', 'Seite (rechts)'), ('game', 'echte Spielkamera (0,35 m rechts)')]
F_T = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 24)
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 18)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
F_S = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)
YEL, CYAN, RED, GRN = (255, 226, 120), (150, 220, 255), (255, 120, 110), (140, 220, 140)
PART = {'arm': 'Unterarm/Hand', 'elb': 'Ellbogenende', 'pis': 'Pistole'}


def de(x, n=1):
    return ('%.*f' % (n, x)).replace('.', ',')


def holster_frames(rows, clip):
    """frames in which the pistol is in / leaving / entering the holster (not counted for the pistol): at the idle end of the clip, the
    pistol cuts the gear or is closer than 10 mm"""
    out = {'R': set(), 'L': set()}
    if clip == 'Yoru_Sprint_To_Aim':
        return out
    order = rows if clip == 'Yoru_Aim_In' else rows[::-1]
    for s in 'RL':
        for r in order:
            if r['pcut_' + s] > 0 or r['pis_low_' + s] < 10.0:
                out[s].add(r['frame'])
            else:
                break
    if clip == 'Yoru_Aim_In':                                            # frame 1 = leaving the holster (the brief: until it has left)
        for s in 'RL':
            if 0 in out[s]:
                out[s].add(1)
    return out


def zone_min(r, zone, hol):
    best = (999.0, '', '')
    for s in 'RL':
        for part in ('arm', 'elb', 'pis'):
            if part == 'pis' and r['frame'] in hol[s]:
                continue
            v = r['%s_%s_%s' % (part, zone, s)]
            if v < best[0]:
                best = (v, part, s)
    return best


# ------------------------------------------------------------------ video
def panel_img(clip, view, f):
    return Image.open(os.path.join(FRAMES, clip, view, 'f_%03d.png' % f)).convert('RGB')


s0 = [panel_img('Yoru_Aim_In', v, 0) for v, _ in VIEWS]
PH = 640
PW = [int(round(im.width * PH / im.height)) for im in s0]
GAP, TOP, BOT = 6, 70, 64
VW = (sum(PW) + GAP * 2 + 1) // 2 * 2
VH = (TOP + PH + BOT + 1) // 2 * 2


def frame(clip, title, f, mode, rows, hol):
    g = Image.new('RGB', (VW, VH), BG)
    d = ImageDraw.Draw(g)
    x = 0
    for (v, lab), w in zip(VIEWS, PW):
        im = panel_img(clip, v, f).resize((w, PH), Image.LANCZOS)
        g.paste(im, (x, TOP))
        d.rectangle([x + 4, TOP + 6, x + d.textlength(lab, font=F_B) + 14, TOP + 30], fill=(20, 22, 26))
        d.text((x + 9, TOP + 8), lab, fill=CYAN, font=F_B)
        x += w + GAP
    d.text((10, 8), title, fill=YEL, font=F_T)
    d.text((10, 40), mode, fill=(225, 228, 235), font=F_B)
    r = rows[f]
    lo, up = zone_min(r, 'low', hol), zone_min(r, 'up', hol)
    hs = [s for s in 'RL' if f in hol[s]]
    line = 'Bild %d (%s s)   |   unter der Gürtellinie min %s mm (%s %s)   |   über der Gürtellinie min %s mm (%s %s)   |   Ellbogen außen R %s / L %s cm' % (
        f, de(f / 60.0, 3), de(lo[0]), PART[lo[1]], lo[2], de(up[0]), PART[up[1]], up[2], de(r['elbow_out_R']), de(r['elbow_out_L']))
    col_lo = RED if lo[0] < 15.0 else GRN
    d.text((10, TOP + PH + 8), line, fill=(225, 228, 235), font=F)
    d.rectangle([10, TOP + PH + 34, 24, TOP + PH + 48], fill=col_lo)
    d.text((30, TOP + PH + 33), 'unten >= 15 mm', fill=(200, 200, 205), font=F_S)
    d.rectangle([170, TOP + PH + 34, 184, TOP + PH + 48], fill=RED if up[0] < 5.0 else GRN)
    d.text((190, TOP + PH + 33), 'oben >= 5 mm', fill=(200, 200, 205), font=F_S)
    if hs:
        d.text((330, TOP + PH + 33), 'Pistole %s im / am Holster (zählt nicht)' % '+'.join(hs), fill=(200, 200, 205), font=F_S)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


os.makedirs(os.path.dirname(VIDEO), exist_ok=True)
tmp = os.path.join(FRAMES, os.path.splitext(os.path.basename(VIDEO))[0] + '_mp4v.mp4')
vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*'mp4v'), 60, (VW, VH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + tmp)
HOL = {}
n_out = 0
for clip, title in CLIPS:
    rows = D['clips'][clip]['rows']
    hol = holster_frames(rows, clip)
    HOL[clip] = {s: sorted(v) for s, v in hol.items()}
    N = len(rows) - 1
    for f in range(N + 1):                                             # slow motion: every frame 4 times (1/4 speed)
        im = frame(clip, title, f, 'Zeitlupe 1/4 (jedes Bild einzeln)', rows, hol)
        for _ in range(4 if f not in (0, N) else 30):
            vw.write(im)
            n_out += 1
    for f in range(N + 1):                                             # real time, first / last frame held
        im = frame(clip, title, f, 'Echtzeit (60 Bilder/s)', rows, hol)
        for _ in range(1 if f not in (0, N) else 40):
            vw.write(im)
            n_out += 1
vw.release()
subprocess.run([sys.executable, '-I', os.path.join(HERE, 'mp4_to_h264.py'), tmp, VIDEO], check=True)
if KV.get('still'):
    rows = D['clips']['Yoru_Aim_In']['rows']
    cv2.imwrite(KV['still'], frame('Yoru_Aim_In', CLIPS[0][1], 4, 'Standbild Bild 4', rows, holster_frames(rows, 'Yoru_Aim_In')))
print('video', VIDEO, n_out, 'frames', flush=True)

# ------------------------------------------------------------------ plot
W, H = 1500, 1260
img = Image.new('RGB', (W, H), (250, 250, 252))
d = ImageDraw.Draw(img)
d.text((40, 14), 'Kleinster Abstand zum Netz je Bild (Unterarm + Hand, Ellbogenende, Pistole; beide Seiten)', fill=(20, 20, 30), font=F_T)
_lx = 40
for _col, _lab in (((220, 110, 30), 'unter der Gürtellinie (Hüft- und Gürteltaschen, Oberschenkel), Grenze 15 mm'),
                   ((40, 110, 220), 'über der Gürtellinie (Weste, Brust), Grenze 5 mm'), ((200, 200, 200), 'grau: Pistole im / am Holster')):
    d.rectangle([_lx, 52, _lx + 18, 64], fill=_col)
    d.text((_lx + 24, 48), _lab, fill=(40, 40, 50), font=F_S)
    _lx += 24 + d.textlength(_lab, font=F_S) + 30
COL = dict(low=(220, 110, 30), up=(40, 110, 220), elb=(40, 110, 220))
L_, R_ = 110, 1290
YMAX = 60.0
for k, (clip, title) in enumerate(CLIPS):
    rows = D['clips'][clip]['rows']
    N = len(rows) - 1
    hol = HOL[clip]
    y0, y1 = 120 + k * 380, 120 + k * 380 + 290
    d.text((L_, y0 - 34), title, fill=(30, 30, 40), font=F_B)
    d.rectangle([L_, y0, R_, y1], outline=(160, 160, 170))

    def X(f):
        return L_ + f / float(N) * (R_ - L_)

    def Y(v):
        return y1 - min(v, YMAX) / YMAX * (y1 - y0)
    for f in range(N + 1):
        if f in hol['R'] or f in hol['L']:
            d.rectangle([X(f) - (R_ - L_) / (2.0 * N), y0 + 1, X(f) + (R_ - L_) / (2.0 * N), y1 - 1], fill=(236, 236, 236))
    for v in range(0, int(YMAX) + 1, 10):
        d.line([(L_, Y(v)), (R_, Y(v))], fill=(225, 225, 232))
        d.text((L_ - 34, Y(v) - 9), str(v), fill=(90, 90, 100), font=F_S)
    for f in range(N + 1):
        d.text((X(f) - 5, y1 + 6), str(f), fill=(90, 90, 100), font=F_S)
    d.text((R_ + 12, y1 + 6), 'Bild', fill=(90, 90, 100), font=F_S)
    d.text((L_ - 100, y0 - 4), 'mm', fill=(90, 90, 100), font=F_S)
    for lim, col, lab in ((15, COL['low'], '15 unten'), (5, COL['up'], '5 oben')):
        xx = L_
        while xx < R_:
            d.line([(xx, Y(lim)), (min(xx + 12, R_), Y(lim))], fill=col, width=2)
            xx += 20
        d.text((R_ + 8, Y(lim) - 9), lab, fill=col, font=F_S)
    for zone, col in (('low', COL['low']), ('up', COL['up'])):
        pts = [(X(r['frame']), Y(zone_min(r, zone, hol)[0])) for r in rows]
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=col, width=3)
        for p in pts:
            d.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=col)
    # the elbow end alone (the part that touches the vest side)
d.text((L_, H - 34), 'Gürtellinie z = 1,00 m (Oberkante der Hüft-Gear, wie aim_transition_scan.py). Werte über 60 mm sind oben abgeschnitten.',
       fill=(70, 70, 80), font=F_S)
os.makedirs(os.path.dirname(PLOT), exist_ok=True)
img.save(PLOT)
json.dump(HOL, open(os.path.splitext(PLOT)[0] + '_holster_frames.json', 'w'))
print('plot', PLOT, '| holster frames', HOL, flush=True)
