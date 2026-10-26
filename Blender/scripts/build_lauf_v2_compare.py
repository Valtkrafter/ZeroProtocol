"""Lauf v2: comparison sheet NTE (rows 1 and 3) against Yoru (rows 2 and 4) at the same phase of the cycle.
usage: python -I build_lauf_v2_compare.py <frames dir with Neu/> <view side|back> <NTE first frame> <Yoru 60 fps frame at that NTE frame> <out png> [Yoru view name]
NTE frames n, n+2, .. n+18 (every second recording frame = one cycle); Yoru frame = y0 + 2 * (k * 2) (60 fps, mod 40).
NTE crops as dense_strip.py (centre = mean hair position over the cycle; side 380 x 500, back 360 x 500)."""
import sys, os, json
import cv2
import numpy as np

src, view, n0, y0, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
YVIEW = sys.argv[6] if len(sys.argv) > 6 else view
REF = r'C:\Users\valen\ZeroProtocol\Blender\previews\ref_nte'
CLIP = {'side': '194135', 'back': '194448'}[view]
CW, CH = {'side': (380, 500), 'back': (360, 500)}[view]
track = json.load(open(os.path.join(REF, 'nte_track_hair.json')))[CLIP]
cx, cy = np.array(track['cx']), np.array(track['cy'])
cap = cv2.VideoCapture(os.path.join(REF, 'clips', 'Aufzeichnung 2026-10-23 %s.mp4' % CLIP))
cx0, cy0 = np.nanmean(cx[n0:n0 + 20]), np.nanmean(cy[n0:n0 + 20])


def nte(n):
    cap.set(cv2.CAP_PROP_POS_FRAMES, n)
    ok, f = cap.read()
    x = int(max(0, min(f.shape[1] - CW, cx0 - CW / 2)))
    y = int(max(0, min(f.shape[0] - CH, cy0 - CH * 0.18)))
    c = f[y:y + CH, x:x + CW].copy()
    cv2.putText(c, 'NTE %d' % n, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    return c


def yoru(fr):
    a = cv2.imread(os.path.join(src, 'Neu', '%s_%03d.png' % (YVIEW, fr)))
    a = cv2.resize(a, (CW, CH))
    cv2.putText(a, 'Yoru f%d' % fr, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    return a


rows = []
for half in range(2):
    top, bot = [], []
    for k in range(5):
        i = half * 5 + k
        top.append(nte(n0 + 2 * i))
        bot.append(yoru((y0 + 4 * i) % 40))
    rows.append(np.hstack(top))
    rows.append(np.hstack(bot))
sheet = np.vstack(rows)
cv2.imwrite(out, sheet)
print('compare', out, sheet.shape)
