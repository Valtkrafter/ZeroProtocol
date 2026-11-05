"""
Yoru - WALK POLISH, round 2 (28.10.): the arms are rebuilt in the frame of the upper chest (clean swing plane, constant elbow direction,
pure elbow hinge, no extra upper-arm twist) on top of the v1 walk; legs = the round-1 knee fix.  Three arm variants as separate actions.
Run (background Blender, absolute paths; the input .blend is only read):
  blender -b --factory-startup <walk .blend, e.g. Blender/Yoru_Walk.blend> --python build_walk_polish_r2.py -- <out .blend> [KEY=VALUE ...]
  keys: VARIANTS=A,B,C   PICK=<variant assigned to the armature when saving, default the first>   PREFIX=Yoru_Walk_polish_r2   x_extra=0
Why (round 1 looked "weird" to the user; build_walk_polish_armtrace.py shows the causes):
  - the old walk defines the arms in world space while the chest rolls, so relative to the body each arm goes forward on an inner path and
    back on an outer path (elbow loop 3 cm, hand loop 6 cm wide, a quarter cycle out of phase with the swing).  With straight elbows it was
    hard to see; with the round-1 bend the forearm sticks out and it reads as flapping.  The inner path is where the forearm met the hip pouch.
  - round 1 twisted the upper arm (10..15 deg, wobbling twice per cycle) to keep the hand on that looping path; the back of the elbow turned
    3..5 deg inwards (old walk: 8 deg outwards), so the forearm splayed out from a tucked-in elbow.
Arm model, per frame (chest frame: x = her right, y = forward, z = up):
  upper arm pitch  = old pitch - fwd_cut * (0.5 + 0.5 cos phase), scaled about its mean by `swing`;
  upper arm spread = mean of the old spread - k_in * cos(phase)   (a touch inwards in front, out behind, in step with the swing: no loop);
  elbow            = the back of the elbow points eps deg out from straight back (constant); eps is solved so that the mean sideways wrist
                     position equals the old mean (+ x_extra), the hands stay as close to the body as before on average;
  elbow bend       = e_mid + e_amp * shape(phase - e_lag) about that hinge, forearm turned about itself by the old pronation (constant);
  hand             = the old hand-to-forearm relation (one reference frame) + trailing bend w0 + w_amp * cos(phase - w_lag) about the hinge.
Variants (one feature each, compared with A):
  A  clean plane: the round-1 bend (20..44 deg), swing and timing
  B  calmer: bend 26..38 deg and 30 % less upper-arm swing (shorter hand path)
  C  no drag: bend and hand move in step with the upper arm (e_lag 0 and w_lag 0.12 instead of 0.11 and 0.27)
Legs: the round-1 knee fix (lower leg smoothed only while the knee straightens before touchdown; foot (half) and toes in the first two
airborne frames).  Writes <out .blend> (actions <PREFIX>_<V>; the input action Yoru_Walk is kept) and <out>_numbers.json.
"""
import bpy, sys, os, math, json
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
VARIANTS = KV.get('VARIANTS', 'A,B,C').split(',')
PICK = KV.get('PICK', VARIANTS[0])
PREFIX = KV.get('PREFIX', 'Yoru_Walk_polish_r2')
X_EXTRA = float(KV.get('x_extra', 0.0))
BASE = dict(e_mid=32.0, e_amp=12.0, e_lag=0.11, e_h2=0.12, w0=8.0, w_amp=9.0, w_lag=0.27, swing=1.0, fwd_cut=6.0, k_in=1.5)
VAR = {'A': dict(), 'B': dict(e_amp=6.0, swing=0.7), 'C': dict(e_lag=0.0, w_lag=0.12)}
_HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
GLB = r'C:\Users\valen\ZeroProtocol\Blender\work\Yoru_V2.glb'
LIB = {'__name__': 'idle_lib', '__file__': os.path.join(_HERE, 'build_idle_v2_lib.py')}
exec(compile(open(LIB['__file__'], encoding='utf-8').read(), LIB['__file__'], 'exec'), LIB)
TWO_PI = 2.0 * math.pi

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
H = LIB['humanoid_map'](GLB)
rig = LIB['Rig'](arm, H)
pbs = arm.pose.bones
ad = arm.animation_data
old = bpy.data.actions['Yoru_Walk']
old.use_fake_user = True
NF = int(round(old.frame_range[1] - old.frame_range[0]))
SIDES = (('L', 'left'), ('R', 'right'))


def fcurves_of(act):
    out = []
    try:
        out = list(act.fcurves)
    except Exception:
        pass
    if not out:
        for l in act.layers:
            for s in l.strips:
                for cb in s.channelbags:
                    out += list(cb.fcurves)
    return out


def qmap(act):
    m = {}
    for fc in fcurves_of(act):
        if fc.data_path.startswith('pose.bones["') and fc.data_path.endswith('rotation_quaternion'):
            m[(fc.data_path.split('"')[1], fc.array_index)] = fc
    return m


FC_OLD = qmap(old)
FC = {}


def q_old(b, f):
    return Quaternion([FC_OLD[(b, i)].evaluate(f % NF) for i in range(4)])


def set_q(b, f, q):
    q = q.normalized()
    if q.dot(q_old(b, f)) < 0.0:
        q = Quaternion((-q.w, -q.x, -q.y, -q.z))
    for i in range(4):
        for kp in FC[(b, i)].keyframe_points:
            if abs(kp.co.x - f) < 1e-3 or (f == 0 and abs(kp.co.x - NF) < 1e-3):
                d = q[i] - kp.co.y
                kp.co.y = q[i]
                kp.handle_left.y += d
                kp.handle_right.y += d


def use_action(act):
    ad.action = act
    if getattr(ad, 'action_slot', None) is None and len(act.slots):
        ad.action_slot = act.slots[0]


def rot3(m):
    return m.to_3x3().normalized()


def rotq(axis, deg_):
    return Quaternion(axis, math.radians(deg_))


def perp(v, axis):
    return (v - axis * v.dot(axis)).normalized()


def signed(a, b, axis):
    return math.degrees(math.atan2(axis.dot(a.cross(b)), a.dot(b)))


def F3(a, b):
    c = a.cross(b)
    return Matrix((a, b, c)).transposed()                              # columns a, b, a x b


# ---------------------------------------------------------------- old pose, per frame
use_action(old)
body = rig.body
vis = LIB['visible_vertices'](body)
dom = LIB['vertex_groups_by_bone'](rig)
shoe = {s: [i for i, n in enumerate(dom) if vis[i] and n in (H[side + 'Foot'], H[side + 'Toes'])] for s, side in SIDES}
D = {s: [] for s, _ in SIDES}
sole = {s: [] for s, _ in SIDES}
knee_old = {s: [] for s, _ in SIDES}
for f in range(NF):
    scene.frame_set(f)
    mc = rot3(pbs[H['upperChest']].matrix)
    rt, fw, up = mc.col[0].normalized(), -mc.col[2].normalized(), mc.col[1].normalized()
    for s, side in SIDES:
        sx = -1.0 if s == 'L' else 1.0
        u, l, h_, k = (pbs[H[side + p]] for p in ('UpperArm', 'LowerArm', 'Hand', 'MiddleProximal'))
        S, E, W, K = u.head.copy(), l.head.copy(), h_.head.copy(), k.head.copy()
        ud = (E - S).normalized()
        D[s].append(dict(S=S, E=E, W=W, K=K, Ru=rot3(u.matrix), Rf=rot3(l.matrix), Rh=rot3(h_.matrix), Rsh=rot3(u.parent.matrix),
                         rt=rt, fw=fw, up=up, pitch=math.degrees(math.atan2(ud.dot(fw), -ud.dot(up))),
                         spread=math.degrees(math.atan2(sx * ud.dot(rt), -ud.dot(up))), wx=sx * rt.dot(W - S)))
        hp, kn, an = (pbs[H[side + p]].head for p in ('UpperLeg', 'LowerLeg', 'Foot'))
        knee_old[s].append(math.degrees((kn - hp).angle(an - kn)))
    me = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    for s, _ in SIDES:
        sole[s].append(min(me.vertices[i].co.z for i in shoe[s]))
    body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()


def rest_c(bname):
    b = arm.data.bones[bname]
    return (b.parent.matrix_local.inverted() @ b.matrix_local).to_3x3().normalized()


C = {s: {p: rest_c(H[side + p]) for p in ('UpperArm', 'LowerArm', 'Hand')} for s, side in SIDES}


def phase(s, f):
    return (f / float(NF)) if s == 'L' else ((f - NF / 2.0) / float(NF))   # 0 = this arm furthest forward


# reference frame per side (old pose): the upper arm passes the plumb line on its way forward
REF = {}
for s, _ in SIDES:
    pt = [d['pitch'] for d in D[s]]
    fr = min((f for f in range(NF) if pt[(f + 1) % NF] > pt[f]), key=lambda f: abs(pt[f]))
    d = D[s][fr]
    u0 = (d['E'] - d['S']).normalized()
    f0 = (d['W'] - d['E']).normalized()
    k0 = (d['K'] - d['W']).normalized()
    b0 = perp(d['Ru'] @ Vector((0, 0, 1)), u0)
    h0 = u0.cross(f0).normalized()
    e0 = math.degrees(u0.angle(f0))
    Rf_zero = rotq(h0, e0).to_matrix() @ d['Ru']
    pron = signed(perp(Rf_zero @ Vector((0, 0, 1)), f0), perp(d['Rf'] @ Vector((0, 0, 1)), f0), f0)
    REF[s] = dict(frame=fr, u0=u0, b0=b0, Ru=d['Ru'], pron=pron, Lh=d['Rf'].transposed() @ d['Rh'], w_ref=signed(f0, k0, h0),
                  k_local=d['Rh'].transposed() @ (d['K'] - d['W']), Lu=(d['E'] - d['S']).length, Lf=(d['W'] - d['E']).length,
                  spread_mean=sum(x['spread'] for x in D[s]) / NF, wx_mean=sum(x['wx'] for x in D[s]) / NF)


def make_shape(h2):
    grid = [math.cos(TWO_PI * i / 720.0) + h2 * math.cos(2.0 * TWO_PI * i / 720.0 - 0.6) for i in range(720)]
    lo, hi = min(grid), max(grid)
    return lambda x: 2.0 * ((math.cos(TWO_PI * x) + h2 * math.cos(2.0 * TWO_PI * x - 0.6)) - lo) / (hi - lo) - 1.0


def arm_frames(s, P, eps):
    """the new arm for every frame: (Ru, Rf, Rh, E, W, K) in world space"""
    sx = -1.0 if s == 'L' else 1.0
    R = REF[s]
    shape = make_shape(P['e_h2'])
    cut = [D[s][f]['pitch'] - P['fwd_cut'] * (0.5 + 0.5 * math.cos(TWO_PI * phase(s, f))) for f in range(NF)]
    mean_p = sum(cut) / NF
    out = []
    for f in range(NF):
        d = D[s][f]
        ph = phase(s, f)
        rt, fw, up = d['rt'], d['fw'], d['up']
        p = mean_p + P['swing'] * (cut[f] - mean_p)
        a = R['spread_mean'] - P['k_in'] * math.cos(TWO_PI * ph)
        u = rotq(rt, p) @ (rotq(fw, -sx * a) @ (-up))
        b = perp(math.cos(math.radians(eps)) * (-fw) + math.sin(math.radians(eps)) * sx * rt, u)
        Ru = F3(u, b) @ F3(R['u0'], R['b0']).transposed() @ R['Ru']
        e = P['e_mid'] + P['e_amp'] * shape(ph - P['e_lag'])
        hinge = b.cross(u).normalized()
        Qe = rotq(hinge, e)
        fd = Qe @ u
        Rf = rotq(fd, R['pron']).to_matrix() @ Qe.to_matrix() @ Ru
        w = P['w0'] + P['w_amp'] * math.cos(TWO_PI * (ph - P['w_lag']))
        Rh = rotq(hinge, w - R['w_ref']).to_matrix() @ Rf @ R['Lh']
        E = d['S'] + R['Lu'] * u
        W = E + R['Lf'] * fd
        K = W + Rh @ R['k_local']
        out.append(dict(Ru=Ru, Rf=Rf, Rh=Rh, E=E, W=W, K=K, e=e, w=w, p=p, a=a))
    return out


def solve_eps(s, P):
    target = REF[s]['wx_mean'] + X_EXTRA
    sx = -1.0 if s == 'L' else 1.0

    def mean_wx(eps):
        fr = arm_frames(s, P, eps)
        return sum(sx * D[s][f]['rt'].dot(fr[f]['W'] - D[s][f]['S']) for f in range(NF)) / NF
    lo, hi = -30.0, 60.0                                               # more eps -> the bend pulls the hand further in
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if mean_wx(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def write_arms(P, eps_fix=None):
    info = {}
    for s, side in SIDES:
        eps = eps_fix[s] if eps_fix else solve_eps(s, P)
        fr = arm_frames(s, P, eps)
        for f in range(NF):
            d, n = D[s][f], fr[f]
            Bu = C[s]['UpperArm'].transposed() @ d['Rsh'].transposed() @ n['Ru']
            Bf = C[s]['LowerArm'].transposed() @ n['Ru'].transposed() @ n['Rf']
            Bh = C[s]['Hand'].transposed() @ n['Rf'].transposed() @ n['Rh']
            for p_, B in (('UpperArm', Bu), ('LowerArm', Bf), ('Hand', Bh)):
                set_q(H[side + p_], f, B.to_quaternion())
        sx = -1.0 if s == 'L' else 1.0
        ex = [sx * D[s][f]['rt'].dot(fr[f]['E'] - D[s][f]['S']) for f in range(NF)]
        wx = [sx * D[s][f]['rt'].dot(fr[f]['W'] - D[s][f]['S']) for f in range(NF)]
        info[s] = dict(eps=round(eps, 2), elbow_x_cm=(round(min(ex) * 100, 1), round(max(ex) * 100, 1)),
                       wrist_x_cm=(round(min(wx) * 100, 1), round(max(wx) * 100, 1)),
                       bend=(round(min(x['e'] for x in fr), 1), round(max(x['e'] for x in fr), 1)),
                       pitch=(round(min(x['p'] for x in fr), 1), round(max(x['p'] for x in fr), 1)))
    return info


def write_legs():
    leg_parts = ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')
    windows = {}
    for s, side in SIDES:
        air = [f for f in range(NF) if sole[s][f] > 0.003]
        start = next(f for f in air if (f - 1) % NF not in air)
        run, g = [], start
        while g in air:
            run.append(g)
            g = (g + 1) % NF
        windows[s] = run[1:-1]
        ko = knee_old[s]
        extend = [f for f in windows[s] if ko[f] < ko[(f - 1) % NF]]
        for p in leg_parts:
            b = H[side + p]
            qs = {f: q_old(b, f) for f in range(NF)}
            todo = extend if p == 'LowerLeg' else (windows[s][:2] if p in ('Foot', 'Toes') else [])
            for f in todo:
                a, c, e = qs[(f - 1) % NF], qs[f], qs[(f + 1) % NF]
                if a.dot(c) < 0:
                    a = Quaternion((-a.w, -a.x, -a.y, -a.z))
                if e.dot(c) < 0:
                    e = Quaternion((-e.w, -e.x, -e.y, -e.z))
                m = Quaternion((0.25 * a.w + 0.5 * c.w + 0.25 * e.w, 0.25 * a.x + 0.5 * c.x + 0.25 * e.x,
                                0.25 * a.y + 0.5 * c.y + 0.25 * e.y, 0.25 * a.z + 0.5 * c.z + 0.25 * e.z)).normalized()
                set_q(b, f, c.slerp(m, 0.5 if p == 'Foot' else 1.0))
    return windows


def measure(act):
    use_action(act)
    out = {s: [] for s, _ in SIDES}
    for f in range(NF):
        scene.frame_set(f)
        pen = LIB['arm_penetration'](rig)
        for s, _ in SIDES:
            out[s].append((round(pen[s][3] * 1000.0, 1), round(pen[s][2] * 1000.0, 1)))
    fcs = qmap(act)
    steps = []
    for b in sorted({k[0] for k in fcs}):
        if b not in set(H.values()):
            continue
        qs = [Quaternion([fcs[(b, i)].evaluate(f) for i in range(4)]) for f in range(NF + 1)]
        for f in range(NF):
            a_ = math.degrees(qs[f].rotation_difference(qs[f + 1]).angle)
            steps.append((round(min(a_, 360.0 - a_), 2), b, '%d->%d' % (f, f + 1)))
    steps.sort(reverse=True)
    return out, steps[:5]


def main():                                                           # (round 3 execs this file with R2_LIBRARY_MODE = True and skips main)
    global FC
    res = {'NF': NF, 'ref': {s: dict(frame=REF[s]['frame'], pron=round(REF[s]['pron'], 2), w_ref=round(REF[s]['w_ref'], 2),
                                      spread_mean=round(REF[s]['spread_mean'], 2), wx_mean_cm=round(REF[s]['wx_mean'] * 100, 2)) for s in REF},
           'variants': {}}
    print('REF', res['ref'], flush=True)
    for V in VARIANTS:
        P = dict(BASE)
        P.update(VAR[V])
        act = old.copy()
        act.name = '%s_%s' % (PREFIX, V)
        act.use_fake_user = True
        FC = qmap(act)
        info = write_arms(P)
        windows = write_legs()
        for fc in FC.values():
            fc.update()
        pen, steps = measure(act)
        res['variants'][V] = dict(params=P, arms=info, leg_windows=windows, steps_top=steps, pen_mm=pen,
                                  pen_max={s: max(x[0] for x in pen[s]) for s in pen}, pen_upper_max={s: max(x[1] for x in pen[s]) for s in pen})
        print('VARIANT', V, act.name, json.dumps(info), 'pen max', res['variants'][V]['pen_max'], 'pen_upper max',
              res['variants'][V]['pen_upper_max'], 'steps', steps[:3], flush=True)
    use_action(bpy.data.actions['%s_%s' % (PREFIX, PICK)])
    with open(os.path.splitext(OUT)[0] + '_numbers.json', 'w') as fh:
        json.dump(res, fh, indent=1, default=str)
    scene.frame_set(0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    print('SAVED', OUT, 'assigned', ad.action.name, flush=True)


if not globals().get('R2_LIBRARY_MODE'):
    main()
