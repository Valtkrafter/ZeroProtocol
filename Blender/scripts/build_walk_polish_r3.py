"""
Yoru - WALK POLISH, round 3 (28.10.): the user's pick, variant C of round 2 (no drag), plus a small inward angle at the elbow seen from the
front: the forearm angles a little toward the body's midline instead of running on in the line of the upper arm, the hands come a bit closer
to the centre.
Method: the elbow's bend plane is tilted (the back of the elbow points a little further outwards, i.e. the upper arm is turned a little
inwards), so the bend carries the forearm forwards AND inwards; the inward angle grows with the bend.  The tilt is solved so that the mean
extra inward angle in the front view (angle upper arm / forearm projected on the chest's front plane, against variant C) is `inward` deg.
Tried from 12 down to 4 deg; the largest one that keeps forearm / hand out of the hip and thigh pouches (mesh test arm_penetration,
<= pen_ok mm) is kept, otherwise the one with the least overlap.
Run (background Blender; reads Yoru_Walk.blend, never writes it):
  blender -b --factory-startup C:/Users/valen/ZeroProtocol/Blender/Yoru_Walk.blend --python build_walk_polish_r3.py -- <out .blend>
          [pen_ok=3] [tries=12,10,8,6,4]
Everything else is variant C of build_walk_polish_r2.py (no drag, round-1 bend 20..44 deg, round-1 swing minus fwd_cut, legs with the
round-1 knee fix, 0.70 s / 1.5 m/s).  Action Yoru_Walk_polish_r3_C (the input Yoru_Walk is kept); numbers in <out>_numbers.json.
"""
import bpy, sys, os, math, json

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
PEN_OK = float(KV.get('pen_ok', 3.0))
TRIES = [float(x) for x in KV.get('tries', '12,10,8,6,4').split(',')]
R2 = r'C:\Users\valen\ZeroProtocol\Blender\scripts\build_walk_polish_r2.py'
ns = {'__name__': 'r2lib', '__file__': R2, 'R2_LIBRARY_MODE': True}
exec(compile(open(R2, encoding='utf-8').read(), R2, 'exec'), ns)
SIDES, D, NF = ns['SIDES'], ns['D'], ns['NF']
P = dict(ns['BASE'])
P.update(ns['VAR']['C'])


def front_angles(s, eps):
    """per frame: inward angle at the elbow seen from the front (deg) and the sideways wrist position (m, + = out)"""
    sx = -1.0 if s == 'L' else 1.0
    fr = ns['arm_frames'](s, P, eps)
    ang, wx = [], []
    for f in range(NF):
        d, n = D[s][f], fr[f]
        u, fo = n['E'] - d['S'], n['W'] - n['E']
        a_u = math.atan2(sx * d['rt'].dot(u), -d['up'].dot(u))
        a_f = math.atan2(sx * d['rt'].dot(fo), -d['up'].dot(fo))
        ang.append(math.degrees(a_u - a_f))
        wx.append(sx * d['rt'].dot(n['W'] - d['S']))
    return ang, wx


def mean(v):
    return sum(v) / len(v)


eps_C = {s: ns['solve_eps'](s, P) for s, _ in SIDES}
base = {s: front_angles(s, eps_C[s]) for s, _ in SIDES}


def eps_for(s, inward):
    target = mean(base[s][0]) + inward
    lo, hi = eps_C[s], eps_C[s] + 70.0                                 # more tilt -> the bend brings the forearm further in
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if mean(front_angles(s, mid)[0]) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


old = ns['old']
act = old.copy()
act.name = 'Yoru_Walk_polish_r3_C'
act.use_fake_user = True
ns['FC'] = ns['qmap'](act)
windows = ns['write_legs']()
tries = []
for inward in TRIES:
    eps = {s: eps_for(s, inward) for s, _ in SIDES}
    ns['write_arms'](P, eps_fix=eps)
    for fc in ns['FC'].values():
        fc.update()
    pen, steps = ns['measure'](act)
    pm = max(max(x[0] for x in pen[s]) for s in pen)
    tries.append(dict(inward=inward, eps=eps, pen_max=pm, pen_upper_max=max(max(x[1] for x in pen[s]) for s in pen), steps=steps[:3], pen=pen))
    print('TRY inward %.0f deg: eps L %.1f R %.1f (C: %.1f / %.1f), forearm/hand overlap %.1f mm, upper arm %.1f mm' % (
        inward, eps['L'], eps['R'], eps_C['L'], eps_C['R'], pm, tries[-1]['pen_upper_max']), flush=True)
    if pm <= PEN_OK:
        break
ok = [t for t in tries if t['pen_max'] <= PEN_OK]
pick = ok[0] if ok else min(tries, key=lambda t: t['pen_max'])
if pick is not tries[-1]:
    ns['write_arms'](P, eps_fix=pick['eps'])
    for fc in ns['FC'].values():
        fc.update()
summary = {}
for s, _ in SIDES:
    a0, w0 = base[s]
    a1, w1 = front_angles(s, pick['eps'][s])
    summary[s] = dict(front_inward_C=(round(min(a0), 1), round(mean(a0), 1), round(max(a0), 1)),
                      front_inward_r3=(round(min(a1), 1), round(mean(a1), 1), round(max(a1), 1)),
                      wrist_out_cm_C=(round(min(w0) * 100, 1), round(mean(w0) * 100, 1), round(max(w0) * 100, 1)),
                      wrist_out_cm_r3=(round(min(w1) * 100, 1), round(mean(w1) * 100, 1), round(max(w1) * 100, 1)),
                      eps_C=round(eps_C[s], 1), eps_r3=round(pick['eps'][s], 1))
print('PICK inward %.0f deg' % pick['inward'], json.dumps(summary), 'steps', pick['steps'], flush=True)
ns['use_action'](act)
with open(os.path.splitext(OUT)[0] + '_numbers.json', 'w') as fh:
    json.dump({'pick': pick['inward'], 'pen_ok_mm': PEN_OK, 'summary': summary, 'leg_windows': windows,
               'tries': [{k: v for k, v in t.items()} for t in tries]}, fh, indent=1, default=str)
bpy.context.scene.frame_set(0)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('SAVED', OUT, 'assigned', ns['ad'].action.name, flush=True)
