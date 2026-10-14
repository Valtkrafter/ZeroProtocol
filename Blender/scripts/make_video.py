"""Stitches the preview PNG frames of build_idle.py (front 3/4 view + side view) into one side-by-side video.
usage: python make_video.py <previews dir> <out name without extension> [loops]
Blender 5.1 in this setup has no video output, so the encoding happens here (OpenCV, mp4v) plus a small GIF."""
import sys, os, glob
import cv2
from PIL import Image

prev, out = sys.argv[1], sys.argv[2]
loops = int(sys.argv[3]) if len(sys.argv) > 3 else 3
a = sorted(glob.glob(os.path.join(prev, 'Yoru_Idle_front34_*.png')))
b = sorted(glob.glob(os.path.join(prev, 'Yoru_Idle_side_*.png')))
n = min(len(a), len(b))
print('frames', len(a), len(b), '->', n)
im0 = cv2.imread(a[0])
h, w = im0.shape[:2]
vw = cv2.VideoWriter(out + '.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 30, (w * 2, h))
frames_small = []
for loop in range(loops):
    for i in range(n):
        fa, fb = cv2.imread(a[i]), cv2.imread(b[i])
        both = cv2.hconcat([fa, fb])
        vw.write(both)
        if loop == 0 and i % 2 == 0:
            small = cv2.resize(both, (w, h // 2), interpolation=cv2.INTER_AREA)
            frames_small.append(Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)))
vw.release()
frames_small[0].save(out + '.gif', save_all=True, append_images=frames_small[1:], duration=66, loop=0, optimize=False)
print('wrote', out + '.mp4', os.path.getsize(out + '.mp4') // 1024, 'KB;', out + '.gif', os.path.getsize(out + '.gif') // 1024, 'KB')
