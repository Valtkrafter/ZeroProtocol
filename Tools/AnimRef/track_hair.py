"""Tracks the purple hair of a game character in screen recordings (HSV mask) and writes the centroid per frame. Used to crop dense reference strips.
usage: python -I track_hair.py <folder with mp4> (writes ../nte_track.json next to the folder)"""
import cv2, numpy as np, glob, os, sys, json
src = sys.argv[1]
res = {}
for p in sorted(glob.glob(os.path.join(src, '*.mp4'))):
    name = os.path.basename(p).replace('Aufzeichnung 2026-10-23 ', '').replace('.mp4', '')
    cap = cv2.VideoCapture(p)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); w = int(cap.get(3)); h = int(cap.get(4))
    cx = np.full(n, np.nan); cy = np.full(n, np.nan); area = np.zeros(n)
    for i in range(n):
        ok, f = cap.read()
        if not ok: break
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
        m = cv2.inRange(hsv, (125, 90, 60), (150, 255, 255))      # purple hair
        m[:60, :] = 0                                            # skip the HUD
        m[:, int(w * 0.93):] = 0
        ys, xs = np.nonzero(m)
        area[i] = len(xs)
        if len(xs) > 400:
            cx[i] = xs.mean(); cy[i] = ys.mean()
    res[name] = dict(n=n, w=w, h=h, cx=cx.tolist(), cy=cy.tolist(), area=area.tolist())
    print(name, 'frames', n, 'found', int(np.isfinite(cx).sum()))
json.dump(res, open(os.path.join(src, '..', 'nte_track.json'), 'w'))
