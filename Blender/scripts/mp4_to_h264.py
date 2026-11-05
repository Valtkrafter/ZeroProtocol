"""
Re-encode an OpenCV 'mp4v' video as H.264 (yuv420p) so it plays everywhere (Chromium / the Claude app, phones), optionally repeating parts of it.
OpenCV's prebuilt ffmpeg cannot write H.264 here (no openh264 dll), but PyAV (pip package 'av') ships libx264.
  python mp4_to_h264.py <in.mp4> <out.mp4> [seq=0-53,0-53,54-89,54-89] [crf=20]
seq = frame ranges of the source (inclusive) in the order they are written; without it the whole video is copied once.
"""
import sys
import cv2
import av

src, dst = sys.argv[1], sys.argv[2]
kv = dict(a.split('=', 1) for a in sys.argv[3:] if '=' in a)
crf = kv.get('crf', '20')
cap0 = cv2.VideoCapture(src)
if not cap0.isOpened():
    raise SystemExit('cannot open ' + src)
fps = int(round(cap0.get(cv2.CAP_PROP_FPS) or 30))
n = int(cap0.get(cv2.CAP_PROP_FRAME_COUNT))
w, h = int(cap0.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap0.get(cv2.CAP_PROP_FRAME_HEIGHT))
cap0.release()
segs = [tuple(int(x) for x in p.split('-')) for p in kv['seq'].split(',')] if kv.get('seq') else [(0, n - 1)]
out = av.open(dst, 'w')
st = out.add_stream('libx264', rate=fps)
st.width, st.height, st.pix_fmt = w - w % 2, h - h % 2, 'yuv420p'
st.options = {'crf': crf, 'preset': 'medium'}
written = 0
for a, b in segs:
    cap = cv2.VideoCapture(src)
    for i in range(b + 1):
        ok, f = cap.read()
        if not ok:
            break
        if i < a:
            continue
        fr = av.VideoFrame.from_ndarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)[:st.height, :st.width], format='rgb24')
        for p in st.encode(fr):
            out.mux(p)
        written += 1
    cap.release()
for p in st.encode():
    out.mux(p)
out.close()
import os
print('wrote', dst, written, 'frames', fps, 'fps', '%d x %d' % (st.width, st.height), os.path.getsize(dst) // 1024, 'KB', flush=True)
