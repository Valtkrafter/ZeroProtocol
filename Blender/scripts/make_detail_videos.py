"""Close-up videos of the walk: panels side by side from the stills of render_walk_stills.py.
usage: python make_detail_videos.py <stills dir> <out file without extension> <view[,view...]> [loops] [nf] [scale]
e.g.   python make_detail_videos.py stills walk_chest chest_side,chest_front 4 26 0.8
writes <out>.mp4 (OpenCV mp4v, 30 fps) and <out>.gif (one cycle twice, loops by itself)."""
import sys, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

src, out, views = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
loops = int(sys.argv[4]) if len(sys.argv) > 4 else 4
NF = int(sys.argv[5]) if len(sys.argv) > 5 else 26
scale = float(sys.argv[6]) if len(sys.argv) > 6 else 0.8
TITLE = {'chest_side': 'BRUST SEITE', 'chest_front': 'BRUST VORNE', 'hand': 'HAND', 'feet': 'FUESSE', 'side_wide': 'SEITE', 'three': 'DREIVIERTEL',
         'back': 'HINTEN', 'front': 'VORNE', 'top': 'OBEN'}
try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
except Exception:
    FONT = ImageFont.load_default()


def panel(view, f):
    im = Image.open(os.path.join(src, '%s_%03d.png' % (view, f))).convert('RGB')
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 30], fill=(30, 34, 42))
    d.text((10, 4), '%s   Bild %02d / %d' % (TITLE.get(view, view), f, NF), fill=(255, 255, 255), font=FONT)
    return im


frames = []
for f in range(NF):
    ps = [panel(v, f) for v in views]
    w, h = ps[0].size
    g = Image.new('RGB', (w * len(ps), h))
    for i, im in enumerate(ps):
        g.paste(im, (i * w, 0))
    g = g.resize((int(g.width * scale) // 2 * 2, int(g.height * scale) // 2 * 2), Image.LANCZOS)
    frames.append(g)
vw = cv2.VideoWriter(out + '.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, (frames[0].width, frames[0].height))
for _ in range(loops):
    for im in frames:
        vw.write(cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR))
vw.release()
small = [g.resize((g.width // 2, g.height // 2), Image.LANCZOS) for g in frames]
small[0].save(out + '.gif', save_all=True, append_images=small[1:] * 2, duration=30, loop=0, optimize=False)
print('wrote', out + '.mp4', os.path.getsize(out + '.mp4') // 1024, 'KB;', out + '.gif', os.path.getsize(out + '.gif') // 1024, 'KB')
