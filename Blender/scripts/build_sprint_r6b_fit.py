"""
Yoru - SPRINT LEAN CORRECTION r6b: fits the shoulder motion of a lean variant to r5 with the design mode of build_sprint_r6b.py (saves only logs).
  python build_sprint_r6b_fit.py <LV> <log dir> [cny=10.3] [tg=1.5] [hls=0.6] [fit=cny,tg,hls] [KEY=VALUE ... passed to the builder]
Targets (r5 P2, sprint_measure.py): shoulder yaw p2p 28.67, shoulder roll p2p 16.70, head_x p2p 2.08 cm.
Unknowns: chest_net_yaw (cny, the twist amplitude), twist_gain (tg, how far the twist axis is tilted back to the r5 axis = yaw / roll split),
head_lock_share (hls, how much of the sideways head motion the trunk takes back).  Newton steps with a finite-difference Jacobian; every
evaluation is one background Blender run in design mode (a few seconds), the Jacobian columns run in parallel.
"""
import subprocess, sys, re, os, json
import numpy as np
from concurrent.futures import ThreadPoolExecutor

BL = r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
SCRIPT = r'C:\Users\valen\ZeroProtocol\Blender\scripts\build_sprint_r6b.py'
GLB = r'C:\Users\valen\ZeroProtocol\Blender\work\Yoru_V2.glb'
OUT = r'C:\Users\valen\ZeroProtocol\Blender\work\Sprint'
LV, LOGD = sys.argv[1], sys.argv[2]
KV = dict(a.split('=', 1) for a in sys.argv[3:] if '=' in a)
x = np.array([float(KV.pop('cny', 10.3)), float(KV.pop('tg', 1.5)), float(KV.pop('hls', 0.6))])
FIT = KV.pop('fit', 'cny,tg,hls').split(',')
NAMES = ['cny', 'tg', 'hls']
KEYS = {'cny': 'chest_net_yaw', 'tg': 'twist_gain', 'hls': 'head_lock_share'}
TGT = {'yaw': 28.67, 'roll': 16.70, 'hx': 2.08}
OUTS = {'cny': 'yaw', 'tg': 'roll', 'hls': 'hx'}                     # one target per unknown
EXTRA = ['%s=%s' % kv for kv in KV.items()]
os.makedirs(LOGD, exist_ok=True)
N = [0]


def run(v, tag):
    args = [BL, '-b', '--factory-startup', '--python', SCRIPT, '--', GLB, OUT, 'design', 'LV=' + LV] + \
           ['%s=%.4f' % (KEYS[n], v[i]) for i, n in enumerate(NAMES)] + EXTRA
    log = os.path.join(LOGD, 'fit_%s_%s.log' % (LV, tag))
    txt = subprocess.run(args, capture_output=True, text=True).stdout
    open(log, 'w').write(txt)
    b = re.search(r'BODY P2: lean .*?\(mean ([\d.\-]+)\) \| hips_z p2p ([\d.]+) cm \| head_x p2p ([\d.]+) cm \| shoulder yaw p2p ([\d.]+) \| shoulder roll p2p ([\d.]+)', txt)
    h = re.search(r'HEAD neck_tilt .*?\(mean ([\d.\-]+)\) \| head_pitch .*?\(mean ([\d.\-]+)\)', txt)
    bk = re.search(r'BACK lower back hips->upper chest mean ([\d.\-]+) \| upper back upper chest->neck mean ([\d.\-]+)', txt)
    if not b:
        raise SystemExit('no BODY line in ' + log)
    return {'lean': float(b.group(1)), 'hx': float(b.group(3)), 'yaw': float(b.group(4)), 'roll': float(b.group(5)),
            'neck_tilt': float(h.group(1)), 'head_pitch': float(h.group(2)), 'back_lo': float(bk.group(1)), 'back_hi': float(bk.group(2))}


def resid(m):
    return np.array([m[OUTS[n]] - TGT[OUTS[n]] for n in FIT])


idx = [NAMES.index(n) for n in FIT]
STEP = {'cny': 0.4, 'tg': 0.15, 'hls': 0.06}
jobs = [(x.copy(), 'base')]
for n in FIT:
    v = x.copy()
    v[NAMES.index(n)] += STEP[n]
    jobs.append((v, 'd%s' % n))
with ThreadPoolExecutor(len(jobs)) as ex:
    res = list(ex.map(lambda j: run(*j), jobs))
m0 = res[0]
J = np.column_stack([(resid(r) - resid(m0)) / STEP[n] for r, n in zip(res[1:], FIT)])
print('Jacobian (rows %s, columns %s):\n%s' % ([OUTS[n] for n in FIT], FIT, np.round(J, 3)), flush=True)
hist = []
for it in range(6):
    r0 = resid(m0)
    hist.append({'x': dict(zip(NAMES, [round(float(t), 4) for t in x])), 'm': m0})
    print('it %d  cny %.3f tg %.3f hls %.3f -> lean %.2f yaw %.2f roll %.2f head_x %.2f | neck %.2f skull %.2f | back lo %.2f hi %.2f' % (
        it, x[0], x[1], x[2], m0['lean'], m0['yaw'], m0['roll'], m0['hx'], m0['neck_tilt'], m0['head_pitch'], m0['back_lo'], m0['back_hi']), flush=True)
    if (abs(m0['yaw'] - TGT['yaw']) < 0.08 and abs(m0['roll'] - TGT['roll']) < 0.08
            and ('hls' not in FIT or abs(m0['hx'] - TGT['hx']) < 0.06)):
        break
    dx = np.linalg.solve(J, -r0)
    xn = x.copy()
    xn[idx] += dx
    m1 = run(xn.copy(), 'it%d' % (it + 1))                           # Broyden update of the Jacobian with the step just taken
    r1 = resid(m1)
    J = J + np.outer((r1 - r0) - J @ dx, dx) / float(dx @ dx)
    x, m0 = xn, m1
json.dump(hist, open(os.path.join(LOGD, 'fit_%s.json' % LV), 'w'), indent=1)
print('FIT %s: chest_net_yaw=%.3f twist_gain=%.3f head_lock_share=%.3f' % (LV, x[0], x[1], x[2]), flush=True)
