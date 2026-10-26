"""Finds the gait period from the vertical bobbing of the tracked hair centroid (autocorrelation in 48-frame windows).
usage: python -I find_period.py <track.json>.  A period of 10 frames means one step, a full cycle (two steps) is 20 frames."""
import json, numpy as np, sys
d = json.load(open(sys.argv[1]))
for name, r in d.items():
    cy = np.array(r['cy'], float); cx = np.array(r['cx'], float)
    n = len(cy)
    ok = np.isfinite(cy)
    cy = np.interp(np.arange(n), np.nonzero(ok)[0], cy[ok])
    cx = np.interp(np.arange(n), np.nonzero(ok)[0], cx[ok])
    print('==', name, 'frames', n)
    W = 48
    for s in range(0, n - W, 24):
        seg = cy[s:s + W]
        t = np.arange(W)
        seg = seg - np.polyval(np.polyfit(t, seg, 2), t)
        amp = seg.max() - seg.min()
        ac = np.correlate(seg, seg, 'full')[W - 1:]
        ac = ac / (ac[0] + 1e-9)
        # first peak after the first zero crossing within lag 6..30
        best = None
        for lag in range(6, 31):
            if ac[lag] > ac[lag - 1] and ac[lag] >= ac[lag + 1] and ac[lag] > 0.25:
                best = lag; break
        print('frames %3d-%3d  bob %.1f px  period %s  ac %.2f  cx speed %.1f px/frame' % (s, s + W, amp, best, ac[best] if best else 0, (cx[s + W - 1] - cx[s]) / (W - 1)))
