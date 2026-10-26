"""Dense strip of EVERY frame of one gait cycle (cropped around the tracked character) from a screen recording.
usage: python -I dense_strip.py <folder with mp4> <track.json> <out folder> <clip id e.g. 194135> <first frame> <count> <columns> <tag> [cell width] [cell height]
example: python -I dense_strip.py clips track.json out 194135 100 20 5 side_run 380 500"""
import cv2, numpy as np, json, sys, os
src = sys.argv[1]; trackp = sys.argv[2]; out = sys.argv[3]
name, f0, nfr, cols, tag = sys.argv[4], int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), sys.argv[8]
CW, CH = (int(sys.argv[9]), int(sys.argv[10])) if len(sys.argv) > 10 else (420, 540)
track = json.load(open(trackp))[name]
cx = np.array(track['cx']); cy = np.array(track['cy'])
cap = cv2.VideoCapture(os.path.join(src, 'Aufzeichnung 2026-10-23 %s.mp4' % name))
cap.set(cv2.CAP_PROP_POS_FRAMES, f0)
# fixed crop centre = mean hair position over the strip (so the body bobbing stays visible), horizontal follows the hair slowly
ims = []
cx0 = np.nanmean(cx[f0:f0 + nfr]); cy0 = np.nanmean(cy[f0:f0 + nfr])
for k in range(nfr):
    ok, f = cap.read()
    if not ok: break
    x0 = int(cx0 - CW / 2); y0 = int(cy0 - CH * 0.18)
    x0 = max(0, min(f.shape[1] - CW, x0)); y0 = max(0, min(f.shape[0] - CH, y0))
    c = f[y0:y0 + CH, x0:x0 + CW].copy()
    cv2.putText(c, '%d' % (f0 + k), (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    ims.append(c)
rows = (len(ims) + cols - 1) // cols
sheet = np.zeros((rows * CH, cols * CW, 3), np.uint8)
for k, im in enumerate(ims):
    r, c = divmod(k, cols)
    sheet[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = im
cv2.imwrite(os.path.join(out, 'dense_%s.jpg' % tag), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
print(tag, sheet.shape)
