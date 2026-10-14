"""Makes a video / GIF of the walk filmed in Unity (Tools/verify/film, made by WalkFilmTest): front three quarters | side | face.
usage: python make_unity_film.py <film dir> <out file without extension> [gif first frame] [gif last frame]"""
import sys, os, re
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
g0 = int(sys.argv[3]) if len(sys.argv) > 3 else 20
g1 = int(sys.argv[4]) if len(sys.argv) > 4 else 100
log = {}
for line in open(os.path.join(src, 'film_log.txt')):
    m = re.match(r'(\d+) blinkClock ([\d,\.]+) lid ([\d,\.]+) speed ([\d,\.]+)', line.strip())
    if m:
        log[int(m.group(1))] = (float(m.group(2).replace(',', '.')), float(m.group(3).replace(',', '.')), float(m.group(4).replace(',', '.')))
n = len([f for f in os.listdir(src) if f.startswith('A_')])
try:
    F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
except Exception:
    F = ImageFont.load_default()
TITLES = ('VORNE (Unity)', 'SEITE (Unity)', 'GESICHT (Unity)')


def frame(i):
    ims = []
    for k, tag in enumerate('ABC'):
        im = Image.open(os.path.join(src, '%s_%03d.png' % (tag, i))).convert('RGB')
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, im.width, 30], fill=(30, 34, 42))
        t = TITLES[k]
        if tag == 'A':
            t += '   Walk %.2f m/s' % log.get(i, (0, 0, 1.15))[2]
        if tag == 'C':
            t += '   Lid %3d %%' % round(log.get(i, (0, 0, 0))[1] * 100)
        d.text((10, 4), t, fill=(255, 255, 255), font=F)
        ims.append(im)
    g = Image.new('RGB', (sum(x.width for x in ims), ims[0].height))
    x = 0
    for im in ims:
        g.paste(im, (x, 0)); x += im.width
    return g


first = frame(0)
vw = cv2.VideoWriter(out + '.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, first.size)
for i in range(n):
    vw.write(cv2.cvtColor(np.array(frame(i)), cv2.COLOR_RGB2BGR))
vw.release()
print('wrote', out + '.mp4', os.path.getsize(out + '.mp4') // 1024, 'KB,', n, 'frames')
g1 = min(g1, n - 1)
small = []
for i in range(g0, g1 + 1):
    g = frame(i)
    small.append(g.resize((g.width * 45 // 100, g.height * 45 // 100), Image.LANCZOS))
small[0].save(out + '.gif', save_all=True, append_images=small[1:], duration=33, loop=0, optimize=False)
print('wrote', out + '.gif', os.path.getsize(out + '.gif') // 1024, 'KB, frames', g0, '..', g1)
