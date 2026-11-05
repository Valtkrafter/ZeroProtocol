"""
Yoru - WALK POLISH, round 1: before / after media from the stills of build_walk_polish_render.py (21 frames per cycle, 30 fps).
usage: python build_walk_polish_media_r1.py <old frames dir> <new frames dir> <out dir> [tag, default r1]
Writes into <out dir>:
  walk_polish_<tag>_vorher_nachher.mp4   two columns (before = old walk, after = polish), three rows (close-up front three-quarter,
                                         close-up from the side, game camera); 4 loops in real time, then 2 loops at half speed
  walk_polish_<tag>_sheet.png            12 frames over one cycle (0.70 s): rows old / new close-up front three-quarter, old / new side
Needs OpenCV and Pillow (system python, not Blender).  No ffmpeg.
"""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OLD, NEW, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
TAG = sys.argv[4] if len(sys.argv) > 4 else 'r1'
os.makedirs(OUT, exist_ok=True)
FPS, NF = 30, 21
cw, ch, top, bottom = 300, 360, 40, 30
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
COLS = [(OLD, 'BEFORE (old walk)'), (NEW, 'AFTER (polish round 1)')]
ROWS = ('close34', 'closeSide', 'game')
VW, VH = cw * len(COLS), top + len(ROWS) * ch + bottom


def cell(src, view, f):
    a = Image.open(os.path.join(src, '%s_%03d.png' % (view, f))).convert('RGB')
    if view == 'game':
        a = a.crop((110, 50, 310, 490)).resize((164, 360), Image.LANCZOS)
        c = Image.new('RGB', (cw, ch), a.getpixel((2, 2)))
        c.paste(a, ((cw - 164) // 2, 0))
        return c
    return a.resize((cw, ch), Image.LANCZOS)


def frame(i, label):
    g = Image.new('RGB', (VW, VH), (22, 24, 29))
    d = ImageDraw.Draw(g)
    f = i % NF
    for c, (src, title) in enumerate(COLS):
        for r, view in enumerate(ROWS):
            g.paste(cell(src, view, f), (c * cw, top + r * ch))
        d.text((c * cw + 10, 9), title, fill=(255, 226, 120), font=F_B)
    d.line([(cw, top), (cw, top + len(ROWS) * ch)], fill=(22, 24, 29), width=3)
    d.text((10, top + len(ROWS) * ch + 6), '%s   frame %2d / 21   t = %.2f s' % (label, f, i / float(FPS)), fill=(150, 220, 255), font=F)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


video = os.path.join(OUT, 'walk_polish_%s_vorher_nachher.mp4' % TAG)
vw = cv2.VideoWriter(video, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (VW, VH))
if not vw.isOpened():
    raise SystemExit('video writer could not open ' + video)
for i in range(4 * NF):
    vw.write(frame(i, 'real time'))
for i in range(2 * NF):
    a = frame(i, 'half speed')
    vw.write(a)
    vw.write(a)
vw.release()
cap = cv2.VideoCapture(video)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cap.release()
print('video', video, os.path.getsize(video) // 1024, 'KB', '%d x %d' % (VW, VH), '%.1f s' % (n / float(FPS)), 'frames', n)

# contact sheet: 12 frames spread over one cycle
FR = [int(round(i * NF / 12.0)) for i in range(12)]
sw, sh = 168, 202
lab = 22
sheet = Image.new('RGB', (sw * len(FR), 4 * (sh + lab)), (22, 24, 29))
d = ImageDraw.Draw(sheet)
rows = [(OLD, 'close34', 'BEFORE, front three-quarter'), (NEW, 'close34', 'AFTER, front three-quarter'),
        (OLD, 'closeSide', 'BEFORE, side'), (NEW, 'closeSide', 'AFTER, side')]
for r, (src, view, title) in enumerate(rows):
    y0 = r * (sh + lab)
    d.text((6, y0 + 3), title + '   (12 frames over one cycle of 0.70 s; frame number top left)', fill=(255, 226, 120), font=F)
    for c, f in enumerate(FR):
        im = Image.open(os.path.join(src, '%s_%03d.png' % (view, f))).convert('RGB').crop((20, 0, 400, 457)).resize((sw, sh), Image.LANCZOS)
        ImageDraw.Draw(im).text((4, 2), str(f), fill=(255, 255, 0), font=F)
        sheet.paste(im, (c * sw, y0 + lab))
out_sheet = os.path.join(OUT, 'walk_polish_%s_sheet.png' % TAG)
sheet.save(out_sheet)
print('sheet', out_sheet, sheet.size, 'frames', FR)
