"""
Yoru - WALK POLISH, round 1 (27.10.): polishes the v1 walk (Blender/Yoru_Walk.blend, action Yoru_Walk, built by build_walk.py) without
rebuilding it.  The old action stays untouched inside the copy (fake user); the polished keys go into a new action (default name
Yoru_Walk_polish_r1) that is assigned to the armature.  Yoru_Walk.blend itself is never written.
Run (background Blender, absolute paths):
  blender -b --factory-startup C:/Users/valen/ZeroProtocol/Blender/Yoru_Walk.blend --python build_walk_polish_r1.py -- <out .blend> [KEY=VALUE ...]
  keys: e_mid e_amp e_lag e_h2 fwd_cut w0 w_amp w_lag leg_smooth pen_tol name  (defaults below)
Unchanged: hips (location and rotation), spine, chest, upper chest, neck, head, clavicles, fingers, tail / ears / hair / bust, and the legs
in every frame in which the shoe touches the floor (planted-foot timing, ground speed 1.5 m/s, the +-5 % wobble, the knee after touchdown).
Changes:
  1. elbows never straight: bend e_mid +- e_amp deg (angle upper arm / forearm from joint to joint; old walk 12 .. 27 deg), the bend peaks
     e_lag of a cycle after the upper arm is furthest forward (the forearm drags behind the upper arm).  Hinge = the elbow axis of the old
     pose, so the elbow keeps pointing where it pointed.
  2. upper arm: fwd_cut deg less forward swing (the bent elbow already carries the hand forward; the hand path stays about as long, no rowing).
  3. wrists: the hand trails the forearm, w0 +- w_amp deg about the elbow axis, furthest forward w_lag of a cycle after the arm.
  4. sideways: a bend about the old hinge pulls the hand inwards (into the thigh pouch, try 1: 29 mm deep).  The upper arm turns about
     its own axis (elbow stays put) until the middle of the hand is as far out as in the old walk; where the mesh test still finds the
     forearm in the hip or the elbow end of the upper arm in the vest (> pen_tol mm), the elbow swivels out about the shoulder -> wrist
     line (up to swv_max deg, smooth bumps; the wrist stays where it is, only the elbow moves out).  Earlier tries, not kept as method:
     pushing the hand out (no help near the elbow, upper arm twist jumped 13 deg in a frame) and opening the whole upper arm sideways
     while the twist held the hand (twist ran into its 35 deg limit, upper arm 16 mm in the vest, 30 deg jumps).
     The swivel itself only got the forearm from 18 to 13 mm at 24 deg, so round 1 ships with swv_max=0: the forearm / hip-pouch and
     upper-arm / vest contacts stay as in the old walk (old 19 / 14 mm, new 18 / 13 mm), open question for the user.
  5. swing legs: [1 2 1] smoothing only where the old steps were too big: the lower leg while the knee straightens before touchdown, foot
     and toes in the first two airborne frames.  Upper legs untouched (try 1 smoothed everything and lost 9 mm of foot lift).
Writes <out .blend> and <out>_numbers.json (per frame elbow, wrist, hand position, arm penetration, leg steps).
try 1 (Yoru_Walk_polish_r1_try1.blend, kept): old hinge only + extra elbow bend against the gear -> hands 5 cm further in, 29 mm inside.
"""
import bpy, sys, os, math, json
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
P = {k: float(KV.get(k, d)) for k, d in (('e_mid', 32.0), ('e_amp', 12.0), ('e_lag', 0.11), ('e_h2', 0.12), ('fwd_cut', 6.0),
                                         ('w0', 8.0), ('w_amp', 9.0), ('w_lag', 0.27), ('leg_smooth', 1.0), ('foot_smooth', 0.5),
                                         ('pen_tol', 1.5), ('swv_max', 0.0))}
NAME = KV.get('name', 'Yoru_Walk_polish_r1')
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
new = old.copy()
new.name = NAME
new.use_fake_user = True
ad.action = new
if getattr(ad, 'action_slot', None) is None and len(new.slots):
    ad.action_slot = new.slots[0]
NF = int(round(old.frame_range[1] - old.frame_range[0]))            # 21 frames, key 21 = key 0
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


FC, FC_OLD = qmap(new), qmap(old)


def q_old(b, f):
    return Quaternion([FC_OLD[(b, i)].evaluate(f % NF) for i in range(4)])


def set_q(b, f, q):
    q = q.normalized()
    if q.dot(q_old(b, f)) < 0.0:
        q = Quaternion((-q.w, -q.x, -q.y, -q.z))
    for i in range(4):
        fc = FC[(b, i)]
        for kp in fc.keyframe_points:
            if abs(kp.co.x - f) < 1e-3 or (f == 0 and abs(kp.co.x - NF) < 1e-3):
                d = q[i] - kp.co.y
                kp.co.y = q[i]
                kp.handle_left.y += d
                kp.handle_right.y += d


def touched_update():
    for fc in FC.values():
        fc.update()


def rot3(m):
    return m.to_3x3().normalized()


# ---------------------------------------------------------------- old pose, per frame (world = armature space, the object is identity)
body = rig.body
vis = LIB['visible_vertices'](body)
dom = LIB['vertex_groups_by_bone'](rig)
shoe = {s: [i for i, n in enumerate(dom) if vis[i] and n in (H[side + 'Foot'], H[side + 'Toes'])] for s, side in SIDES}
D = {s: [] for s, _ in SIDES}
sole = {s: [] for s, _ in SIDES}
knee_old = {s: [] for s, _ in SIDES}
for f in range(NF):
    scene.frame_set(f)
    lat = rot3(pbs[H['upperChest']].matrix).col[0].normalized()     # the body's right
    for s, side in SIDES:
        u, l, h_, k = (pbs[H[side + p]] for p in ('UpperArm', 'LowerArm', 'Hand', 'MiddleProximal'))
        D[s].append(dict(S=u.head.copy(), E=l.head.copy(), W=h_.head.copy(), K=k.head.copy(), Ru=rot3(u.matrix), Rf=rot3(l.matrix),
                         Rh=rot3(h_.matrix), Rsh=rot3(u.parent.matrix), lat=lat.copy(), hips=pbs[H['hips']].head.copy(),
                         fwd=-rot3(pbs[H['upperChest']].matrix).col[2].normalized()))
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

# elbow hinge in the frame of the upper arm, taken from the old pose where the old bend is clear (> 20 deg)
h_local = {}
for s, _ in SIDES:
    acc = Vector((0, 0, 0))
    for d in D[s]:
        du, df = (d['E'] - d['S']).normalized(), (d['W'] - d['E']).normalized()
        if math.degrees(du.angle(df)) > 20.0:
            acc += d['Ru'].inverted() @ du.cross(df).normalized()
    h_local[s] = acc.normalized()

_grid = [math.cos(TWO_PI * i / 720.0) + P['e_h2'] * math.cos(2.0 * TWO_PI * i / 720.0 - 0.6) for i in range(720)]
_lo, _hi = min(_grid), max(_grid)


def c2(x):
    v = math.cos(TWO_PI * x) + P['e_h2'] * math.cos(2.0 * TWO_PI * x - 0.6)
    return 2.0 * (v - _lo) / (_hi - _lo) - 1.0


def phase(s, f):
    return (f / float(NF)) if s == 'L' else ((f - NF / 2.0) / float(NF))   # 0 = this arm furthest forward


def rotq(axis, deg_):
    return Quaternion(axis, math.radians(deg_))


def signed(a, b, axis):
    return math.degrees(math.atan2(axis.dot(a.cross(b)), a.dot(b)))


swv = {s: [0.0] * NF for s, _ in SIDES}                              # elbow swivel out (deg), set by the clearance passes


def arm_pose(s, f):
    d = D[s][f]
    ph = phase(s, f)
    S, E, W, K = d['S'], d['E'], d['W'], d['K']
    # 2. upper arm: less forward swing, about the body's lateral axis through the shoulder joint
    dp = -P['fwd_cut'] * (0.5 + 0.5 * math.cos(TWO_PI * ph))
    sx = -1.0 if s == 'L' else 1.0
    Du = rotq(d['lat'], dp)
    Ru = Du.to_matrix() @ d['Ru']
    E1 = S + Du @ (E - S)
    W1 = S + Du @ (W - S)
    K1 = S + Du @ (K - S)
    Rf1 = Du.to_matrix() @ d['Rf']
    Rh1 = Du.to_matrix() @ d['Rh']
    # 1. elbow: bend to the target about the old hinge
    h = (Ru @ h_local[s]).normalized()
    du = (E1 - S).normalized()
    df1 = (W1 - E1).normalized()
    e_t = P['e_mid'] + P['e_amp'] * c2(ph - P['e_lag'])
    th = e_t - math.degrees(du.angle(df1))
    for _ in range(8):                                                 # secant on the joint-to-joint angle
        g0 = math.degrees(du.angle(rotq(h, th) @ df1)) - e_t
        g1 = math.degrees(du.angle(rotq(h, th + 0.5) @ df1)) - e_t
        if abs(g0) < 0.01 or abs(g1 - g0) < 1e-6:
            break
        th -= g0 * 0.5 / (g1 - g0)
    Qe = rotq(h, th)
    Rf = Qe.to_matrix() @ Rf1
    W2 = E1 + Qe @ (W1 - E1)
    K2 = E1 + Qe @ (K1 - E1)
    Rh2 = Qe.to_matrix() @ Rh1
    # 3. wrist: the hand trails the forearm
    df = (W2 - E1).normalized()
    dh = (K2 - W2).normalized()
    w_t = P['w0'] + P['w_amp'] * math.cos(TWO_PI * (ph - P['w_lag']))
    dw = w_t - signed(df, dh, h)
    Qw = rotq(h, dw)
    Rh = Qw.to_matrix() @ Rh2
    K3 = W2 + Qw @ (K2 - W2)
    # 4. sideways: turn the upper arm about its own axis (S -> E, the elbow stays) until the middle of the hand is as far out as before
    lat, hips = d['lat'], d['hips']
    x_t = sx * lat.dot(0.5 * (W + K) - hips)

    def out_of(tau):
        q_ = rotq(du, tau)
        return sx * lat.dot(S + q_ @ (0.5 * (W2 + K3) - S) - hips)
    tau = 0.0
    for _ in range(10):
        g0 = out_of(tau) - x_t
        g1 = out_of(tau + 0.5) - x_t
        if abs(g0) < 2e-4 or abs(g1 - g0) < 1e-9:
            break
        tau -= g0 * 0.5 / (g1 - g0)
        tau = max(-35.0, min(35.0, tau))
    Qt = rotq(du, tau).to_matrix()
    Ru, Rf, Rh = Qt @ Ru, Qt @ Rf, Qt @ Rh
    # 5. clearance: swivel the elbow out about the shoulder -> wrist line (the wrist stays where it is, the hand turns along)
    if swv[s][f]:
        W3 = S + rotq(du, tau) @ (W2 - S)
        ax = (W3 - S).normalized()
        sgn = 1.0 if sx * lat.dot(rotq(ax, 1.0) @ (E1 - S) - (E1 - S)) > 0 else -1.0
        Qs = rotq(ax, sgn * swv[s][f]).to_matrix()
        Ru, Rf, Rh = Qs @ Ru, Qs @ Rf, Qs @ Rh
    Bu = C[s]['UpperArm'].inverted() @ d['Rsh'].inverted() @ Ru
    Bf = C[s]['LowerArm'].inverted() @ Ru.inverted() @ Rf
    Bh = C[s]['Hand'].inverted() @ Rf.inverted() @ Rh
    return (Bu.to_quaternion(), Bf.to_quaternion(), Bh.to_quaternion()), dict(e=e_t, w=w_t, dp=dp, th=th, dw=dw, tau=tau)


def write_arms():
    info = {s: [] for s, _ in SIDES}
    for s, side in SIDES:
        for f in range(NF):
            qs, inf = arm_pose(s, f)
            for p, q in zip(('UpperArm', 'LowerArm', 'Hand'), qs):
                set_q(H[side + p], f, q)
            info[s].append(inf)
    touched_update()
    return info


def measure_arms():
    out = {s: [] for s, _ in SIDES}
    for f in range(NF):
        scene.frame_set(f)
        pen = LIB['arm_penetration'](rig)
        for s, side in SIDES:
            S, E, W, K = (pbs[H[side + p]].head for p in ('UpperArm', 'LowerArm', 'Hand', 'MiddleProximal'))
            hips = pbs[H['hips']].head
            out[s].append(dict(pen=round(pen[s][3] * 1000.0, 1), pen_up=round(pen[s][2] * 1000.0, 1), where=pen[s][4],
                               where_all=pen[s][1], e=round(math.degrees((E - S).angle(W - E)), 1),
                               w=round(math.degrees((W - E).angle(K - W)), 1), hand_y=round(W.y - hips.y, 3), hand_z=round(W.z, 3),
                               hand_x=round(W.x - hips.x, 3)))
    return out


info = write_arms()
meas = measure_arms()
for it in range(10 if P['swv_max'] > 0 else 0):                       # 5. clearance swivel (off by default, see the header)
    bad = [(s, f) for s, _ in SIDES for f in range(NF) if max(meas[s][f]['pen'], meas[s][f]['pen_up']) > P['pen_tol']]
    print('clearance pass', it, 'inside:', [(s, f, meas[s][f]['pen'], meas[s][f]['pen_up']) for s, f in bad], flush=True)
    if not bad:
        break
    for s, f in bad:
        for df_, a in ((0, 3.0), (-1, 1.5), (1, 1.5), (-2, 0.75), (2, 0.75)):
            g = (f + df_) % NF
            swv[s][g] = min(swv[s][g] + a, P['swv_max'])
    info = write_arms()
    meas = measure_arms()
print('TAU', {s: [round(i['tau'], 1) for i in info[s]] for s in info}, flush=True)
print('SWIVEL', {s: [round(x, 2) for x in swv[s]] for s in swv}, flush=True)

# ---------------------------------------------------------------- 5. swing legs: [1 2 1] smoothing in the airborne frames
leg_parts = ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')
windows = {}
for s, side in SIDES:
    air = [f for f in range(NF) if sole[s][f] > 0.003]
    # the airborne frames form one run around the cycle; find its start (a frame whose predecessor is on the ground)
    start = next(f for f in air if (f - 1) % NF not in air)
    run = []
    g = start
    while g in air:
        run.append(g)
        g = (g + 1) % NF
    windows[s] = run[1:-1]
    ko = knee_old[s]
    extend = [f for f in windows[s] if ko[f] < ko[(f - 1) % NF]]          # the knee straightens before touchdown
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
            set_q(b, f, c.slerp(m, P['foot_smooth'] if p == 'Foot' else P['leg_smooth']))
touched_update()

# ---------------------------------------------------------------- report: joint steps, knees, soles
keyed = sorted({k[0] for k in FC})
humanoid = set(H.values())
steps = []
for b in keyed:
    if b not in humanoid:
        continue
    qs = [Quaternion([FC[(b, i)].evaluate(f) for i in range(4)]) for f in range(NF + 1)]
    for f in range(NF):
        a_ = math.degrees(qs[f].rotation_difference(qs[f + 1]).angle)
        steps.append((round(min(a_, 360.0 - a_), 2), b, '%d->%d' % (f, f + 1)))
steps.sort(reverse=True)
knee_new = {s: [] for s, _ in SIDES}
sole_new = {s: [] for s, _ in SIDES}
for f in range(NF):
    scene.frame_set(f)
    for s, side in SIDES:
        hp, kn, an = (pbs[H[side + p]].head for p in ('UpperLeg', 'LowerLeg', 'Foot'))
        knee_new[s].append(round(math.degrees((kn - hp).angle(an - kn)), 1))
    me = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    for s, _ in SIDES:
        sole_new[s].append(round(min(me.vertices[i].co.z for i in shoe[s]) * 1000.0, 1))
    body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()

res = {'params': P, 'action': NAME, 'h_local': {s: tuple(round(x, 3) for x in h_local[s]) for s in h_local},
       'swivel_deg': swv, 'tau_deg': {s: [round(i['tau'], 2) for i in info[s]] for s in info}, 'leg_windows': windows, 'joint_step_top': steps[:8],
       'knee_old': {s: [round(x, 1) for x in knee_old[s]] for s in knee_old}, 'knee_new': knee_new,
       'sole_old_mm': {s: [round(x * 1000.0, 1) for x in sole[s]] for s in sole}, 'sole_new_mm': sole_new,
       'arms': {s: [{k: v for k, v in m.items() if k not in ('where', 'where_all')} for m in meas[s]] for s in meas},
       'arm_where': {s: [(f, m['pen'], m['where'], m['pen_up'], m['where_all']) for f, m in enumerate(meas[s]) if m['pen'] > 0 or m['pen_up'] > 0]
                     for s in meas}}
for s, _ in SIDES:
    ms = meas[s]
    print('ARM', s, 'elbow %.1f..%.1f' % (min(m['e'] for m in ms), max(m['e'] for m in ms)),
          'wrist %.1f..%.1f' % (min(m['w'] for m in ms), max(m['w'] for m in ms)),
          'hand_y %.3f..%.3f' % (min(m['hand_y'] for m in ms), max(m['hand_y'] for m in ms)),
          'hand_z %.3f..%.3f' % (min(m['hand_z'] for m in ms), max(m['hand_z'] for m in ms)),
          'hand_x %.3f..%.3f' % (min(m['hand_x'] for m in ms), max(m['hand_x'] for m in ms)),
          'pen max %.1f  pen_upper max %.1f' % (max(m['pen'] for m in ms), max(m['pen_up'] for m in ms)), flush=True)
    print('  where', res['arm_where'][s][:4], flush=True)
    print('KNEE', s, 'window', windows[s], 'old', res['knee_old'][s], 'new', knee_new[s], flush=True)
    print('SOLE', s, 'old', res['sole_old_mm'][s], 'new', sole_new[s], flush=True)
print('STEPS', steps[:8], flush=True)
with open(os.path.splitext(OUT)[0] + '_numbers.json', 'w') as fh:
    json.dump(res, fh, indent=1, default=str)
scene.frame_set(0)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('SAVED', OUT, flush=True)
