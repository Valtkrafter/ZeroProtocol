"""Videos of the dodge from the stills of render_walk_stills.py (views front, side_wide, back, top; frames 0 .. NFD-1 at 60 fps, the clip is one-shot, played in place).
usage: python make_dodge_videos.py <stills dir> <gait json> <out dir> [loops] [hold frames]
writes  dodge_4views.mp4 (real time, every loop ends with a short hold), dodge_4views_slow.mp4 (a quarter of the speed), dodge_4views.gif and one mp4 per view.
Every picture shows the frame number, the phase, the ground speed of the pelvis and the distance travelled; two lamps show which foot is on the ground (both dark = flight).
Blender 5.1 in this setup has no video output, so the encoding happens here (OpenCV, mp4v) plus a GIF."""
import sys, os, json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, gait_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
loops = int(sys.argv[4]) if len(sys.argv) > 4 else 6
hold = int(sys.argv[5]) if len(sys.argv) > 5 else 12
os.makedirs(out, exist_ok=True)
G = json.load(open(gait_json))
NFD, FPS = G['frames'], G['fps']
SPEED, TRAVEL = G['speed_per_frame'], G['travel_per_frame']

CROP = {'front': (110, 30, 510, 700), 'side_wide': (0, 40, 600, 700), 'back': (110, 30, 510, 700), 'top': (60, 60, 540, 700)}
TITLE = {'front': 'VORNE', 'side_wide': 'SEITE', 'back': 'HINTEN', 'top': 'OBEN'}
CENTER = {'front': 300 - 110, 'back': 300 - 110, 'top': 300 - 60}
CELL_W, CELL_H = 600, 690
try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
    FONT_S = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
except Exception:
    FONT = FONT_S = ImageFont.load_default()


STANCE_NAMES = G.get('stance_names') or ['Abdruck', 'Sprintschritt', 'Sprintschritt', 'Bremsschritt', 'Auslaufschritt']
SIDE_DE = {'R': 'rechts', 'L': 'links'}


def stance_at(f):
    for i, s in enumerate(G['stances']):
        td = 0.0 if s['td'] is None else s['td']
        to = 1e9 if s['to'] is None else s['to']
        if td <= f <= to:
            return i, s
    return None, None


def phase(f):
    ph = G.get('phases')
    if ph:
        txt = ph[0][1]
        for f0, tx in ph:
            if f >= f0:
                txt = tx
        return txt
    i, s = stance_at(f)
    if s is None:
        return 'FLUG'
    tail = ', geht in Run oder Joggen über' if s['to'] is None else ''
    return '%s, %s%s' % (STANCE_NAMES[i] if i < len(STANCE_NAMES) else 'Schritt', SIDE_DE[s['side']], tail)


def foot_down(side, f):
    for w in G.get('ground', {}).get(side, []):
        if w[0] <= f <= w[1]:
            return True
    for s in G['stances']:
        td = 0.0 if s['td'] is None else s['td']
        to = 1e9 if s['to'] is None else s['to']
        if s['side'] == side and td <= f <= to:
            return True
    return False


def cell(view, f):
    im = Image.open(os.path.join(src, '%s_%03d.png' % (view, f))).convert('RGB').crop(CROP[view])
    canvas = Image.new('RGB', (CELL_W, CELL_H), (112, 124, 140))
    ox, oy = (CELL_W - im.width) // 2, 34 + (CELL_H - 34 - im.height) // 2
    canvas.paste(im, (ox, oy))
    d = ImageDraw.Draw(canvas)
    if view in CENTER:
        cx = ox + CENTER[view]
        d.line([(cx, 34), (cx, CELL_H)], fill=(60, 230, 230), width=1)
    d.rectangle([0, 0, CELL_W, 30], fill=(30, 34, 42))
    d.text((10, 4), TITLE[view], fill=(255, 255, 255), font=FONT)
    return canvas


def frame_grid(f):
    cells = {v: cell(v, f) for v in CROP}
    g = Image.new('RGB', (CELL_W * 2, CELL_H * 2))
    g.paste(cells['front'], (0, 0))
    g.paste(cells['side_wide'], (CELL_W, 0))
    g.paste(cells['back'], (0, CELL_H))
    g.paste(cells['top'], (CELL_W, CELL_H))
    d = ImageDraw.Draw(g)
    d.text((CELL_W + 110, 6), 'Bild %02d / %d   %s' % (f, NFD - 1, phase(f)), fill=(255, 220, 120), font=FONT)
    d.text((CELL_W + 110, 40), 'Tempo %.1f m/s   Weg %.2f m' % (SPEED[f], TRAVEL[f]), fill=(220, 230, 255), font=FONT_S)
    for i, (lab, side) in enumerate((('R', 'R'), ('L', 'L'))):
        on = foot_down(side, f)
        cx = CELL_W + 20 + i * 60
        d.ellipse([cx, 70, cx + 22, 92], fill=(90, 230, 120) if on else (60, 66, 78), outline=(200, 200, 215))
        d.text((cx + 28, 71), lab, fill=(220, 220, 235), font=FONT_S)
    if not foot_down('R', f) and not foot_down('L', f):
        d.text((CELL_W + 150, 71), 'FLUG', fill=(255, 190, 90), font=FONT_S)
    return g


def write_mp4(path, frames, fps):
    h, w = frames[0].height, frames[0].width
    vw = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    for im in frames:
        vw.write(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
    vw.release()
    print('wrote', path, os.path.getsize(path) // 1024, 'KB')


grid = [frame_grid(f) for f in range(NFD)]
seq = (grid + [grid[-1]] * hold) * loops
write_mp4(os.path.join(out, 'dodge_4views.mp4'), seq, FPS)
write_mp4(os.path.join(out, 'dodge_4views_slow.mp4'), (grid + [grid[-1]] * 4) * max(2, loops // 2), FPS // 4)
small = [g.resize((g.width // 2, g.height // 2), Image.LANCZOS) for g in grid]
gif = os.path.join(out, 'dodge_4views.gif')
(small + [small[-1]] * 8)[0].save(gif, save_all=True, append_images=(small + [small[-1]] * 8)[1:] * 2, duration=33, loop=0, optimize=False)
print('wrote', gif, os.path.getsize(gif) // 1024, 'KB')
for v in CROP:
    write_mp4(os.path.join(out, 'dodge_%s.mp4' % v), ([cell(v, f) for f in range(NFD)] + [cell(v, NFD - 1)] * hold) * loops, FPS)
