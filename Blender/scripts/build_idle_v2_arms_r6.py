"""
Yoru - IDLE v2, round 6: the ARMS rest on the gear.  Only the arm chains (upper arm, forearm, hand, fingers, thumb, both sides) are
recomputed; every other curve of the loop is copied bit for bit.
Causes found in the round 5 file (build_idle_v2_arm_diag.py): the elbow pole pointed 55 deg out from straight back, so the upper arm was
turned in by about 45 deg; a world-space palm target then rolled the forearm back by about 40 deg, and with no twist bones in the rig that
counter-roll shows at elbow and wrist ('the elbows bend oddly'); the hand targets hung in space 17 to 38 mm in front of the gear ('floating').
Now:
  - the hands are ANCHORED to points on the gear surface (right: the outer face of the thigh holster / pouch on the right thigh; left: the
    outer side of the left hip / thigh).  The anchor rides on the bone the gear is skinned to (thigh or pelvis), so the hand breathes and sways
    with the body; it also slides a few millimetres on the surface over the loop.  The palm lies on the surface (calibrated so the hand
    vertices stay 0 to 3 mm off the gear).
  - the elbows point back (pole only a little out), the elbow bends about its hinge; the forearm roll is the hinge roll plus at most
    TWIST_MAX deg towards the palm, the rest goes to the wrist (also limited), so nothing corkscrews.
  - the fingers settle a little once or twice per loop (smooth, at uneven times), the thumbs relax.
The steps that made the final file (live, split into calls under a minute each):
  par = conform(arm, 'Yoru_Idle_v2', curls=(0.0,))              # hand placement on the gear at frame 0 (gap along the gear normal, tilt)
  params = {s: par[s][:3] for s in 'LR'}
  fit_fingers(arm, 'Yoru_Idle_v2', params)                        # every finger laid on the gear (fills FINGER_FIT)
  gL = gap_bisect(arm, 'Yoru_Idle_v2', params, 'L', range(360))   # per frame the gap that keeps the deepest hand point 1.2 mm above the gear
  (the right side needed no bisection: gap_step() twice converged to 1.17 .. 1.23 mm)
  bake_arms(arm, 'Yoru_Idle_v2', 'Yoru_Idle_v2_r6', {'L': [...], 'R': [...]}, tilts, curls)
  The parameters of the final bake are stored on the armature as the custom property 'idle_v2_r6_arms' (json) in
  Blender/work/Idle_v2/Yoru_Idle_v2_round6.blend.
  Measuring: signed_to_gear() against the OUTWARD gear faces of the side only (_gear_polys): thin straps have back faces that point inwards
  and made points behind them read as 'inside' (a false -25 mm); nearest-vertex depths (KD tree) also read too deep on curved gear.
Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>).read(), ns); print(ns['build_arms'](bpy.data.objects['Yoru_A2']))
             (build_arms runs all steps with the older contact_pass2 instead of the bisection; it can exceed the MCP time limit)
Background:  blender -b <stage .blend> --python build_idle_v2_arms_r6.py -- <out .blend> [armature, default Yoru_A2]
"""
import bpy, sys, os, math
import numpy as np
from mathutils import Vector, Quaternion, Euler, Matrix
from mathutils.kdtree import KDTree

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_idle_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'


def _load(name):
    ns = {'__file__': os.path.join(_HERE, name)}
    exec(compile(open(os.path.join(_HERE, name), encoding='utf-8').read(), os.path.join(_HERE, name), 'exec'), ns)
    return ns


R3 = _load('build_idle_v2_loop_r3.py')
L = R3['L']
NF, FPS, LOOP = R3['NF'], R3['FPS'], R3['LOOP']
TAU = 2.0 * math.pi
W = TAU / LOOP
FINGERS = ('Index', 'Middle', 'Ring', 'Little')
PARTS = ('Proximal', 'Intermediate', 'Distal')

# per side: where the hand rests (a guess near the gear, relative to the pelvis at frame 0; the real anchor is the nearest gear vertex that
# faces the hand), how the fingers point along the surface (in the anchor bone frame at frame 0), the elbow pole, the slide on the surface
SIDES = {
    # thumbs lie flat along the hand (an opposed thumb dug into the pouch); fingers only lightly curved so they follow the surface
    # right: the hand rests on the middle of the thigh holster (higher made the elbow bend 52 deg and stick out behind the back, lower
    # straightens the arm completely); the elbow points almost straight back
    'R': dict(bones=('J_Bip_R_UpperLeg', 'J_Bip_C_Hips'), guess=Vector((0.178, 0.000, -0.080)),
              finger_dir=Vector((0.0, 0.30, -1.0)), pole_out=6.0, slide=(0.0035, 0.0015), slide_phase=0.6,
              curl={'Index': (6, 9, 6), 'Middle': (7, 10, 7), 'Ring': (9, 12, 8), 'Little': (11, 14, 9)},
              thumb=(6.0, -3.0, -3.0), settle=((3.4, 1.3, ('Index', 'Middle'), -5.0),)),
    # left: the hand rests on the outer side of the left hip / top of the thigh, the forearm leans on the belt pouch on its way down
    # (the elbow a little further out than the right one: with less the forearm pressed into the pouch)
    # (with -0.068 the arm could not reach when the body rose on the in-breath: 10 mm short, the hand slid off; with -0.052 the anchor
    #  jumped onto the belt pouch and the elbow bent 55 deg)
    'L': dict(bones=('J_Bip_L_UpperLeg',), guess=Vector((-0.163, 0.030, -0.062)),
              # the thumb ball slid over a ridge of the gear with a larger slide: smaller slide, the thumb flatter along the hand
              finger_dir=Vector((0.0, 0.45, -1.0)), pole_out=20.0, slide=(0.0026, 0.0012), slide_phase=2.4,
              curl={'Index': (7, 10, 7), 'Middle': (9, 12, 8), 'Ring': (11, 14, 9), 'Little': (13, 16, 10)},
              thumb=(10.0, -3.0, -3.0), settle=((7.9, 1.5, ('Ring', 'Little'), -3.0), (10.6, 1.1, ('Index',), -3.0))),
}
# per-finger extra curl (deg) so that every fingertip rests on the gear; filled by fit_fingers()
FINGER_FIT = {'L': {fn: 0.0 for fn in FINGERS}, 'R': {fn: 0.0 for fn in FINGERS}}
TWIST_MAX = 18.0         # deg the forearm may roll away from its hinge roll
WRIST_MAX = 40.0         # deg the hand may bend away from the forearm
HAND_AXIS_TO_PALM = 0.045    # m from the wrist joint along the hand to the middle of the palm


def D_of(arm, name):
    return arm.pose.bones[name].matrix.to_quaternion() @ arm.data.bones[name].matrix_local.to_quaternion().inverted()


def perp(v, axis):
    w = v - axis * v.dot(axis)
    return w.normalized() if w.length > 1e-9 else None


def bump(t, center, width):
    """smooth periodic bump 0..1..0 around center (s), half-width width (s)"""
    d = (t - center + LOOP / 2.0) % LOOP - LOOP / 2.0
    return 0.5 * (1.0 + math.cos(math.pi * d / width)) if abs(d) < width else 0.0


def find_anchors(arm, rig):
    """at the current frame: per side the gear vertex nearest to the guess that faces outwards, its normal, its bone, and the hand thickness"""
    H = rig.H
    body = rig.body
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    co = [v.co.copy() for v in me.vertices]
    nr = [v.normal.copy() for v in me.vertices]
    ev.to_mesh_clear()
    hips = arm.pose.bones[H['hips']].head.copy()
    out = {}
    for side, sx in (('L', -1.0), ('R', 1.0)):
        S = SIDES[side]
        g = hips + S['guess']
        best = None
        for i, n in enumerate(dom):
            if not vis[i] or n not in S['bones']:
                continue
            if nr[i].x * sx < 0.6:                          # must face outwards, towards the hand
                continue
            d = (co[i] - g).length
            if best is None or d < best[0]:
                best = (d, i)
        d, i = best
        # average normal of the neighbourhood (smoother than one vertex)
        acc = Vector((0.0, 0.0, 0.0))
        for j, n in enumerate(dom):
            if vis[j] and n == dom[i] and (co[j] - co[i]).length < 0.02:
                acc += nr[j]
        N = acc.normalized()
        bone = dom[i]
        M = arm.pose.bones[bone].matrix
        out[side] = dict(bone=bone, A_local=M.inverted() @ co[i], N_local=(M.to_3x3().inverted() @ N).normalized(),
                         F_local=(M.to_3x3().inverted() @ S['finger_dir']).normalized(), dist_guess=d, A=co[i].copy(), N=N.copy())
    return out


def solve_arm(arm, rig, side, anchor, t, gap, extra_slide=0.0, tilt=0.0):
    """world deltas D for the arm chain of one side at the current (evaluated) frame.
    tilt (deg): the fingers turn towards the surface (+) about the axis across the hand, so the hand follows a surface that falls away"""
    sx = -1.0 if side == 'L' else 1.0
    S = SIDES[side]
    nm = rig.nm
    M = arm.pose.bones[anchor['bone']].matrix
    R3x3 = M.to_3x3()
    N = (R3x3 @ anchor['N_local']).normalized()
    F = perp((R3x3 @ anchor['F_local']).normalized(), N)
    if tilt:
        F = (F * math.cos(math.radians(tilt)) - N * math.sin(math.radians(tilt))).normalized()
        N = perp(N, F)
    T = N.cross(F).normalized()                              # along the surface, across the fingers
    ph = S['slide_phase']
    s1 = (math.sin(W * t + ph) + 0.35 * math.sin(2 * W * t + 1.7 * ph)) / 1.35
    s2 = (math.sin(W * t + ph + 1.9) + 0.30 * math.sin(3 * W * t + ph)) / 1.30
    A = M @ anchor['A_local'] + F * (S['slide'][1] * s2) + T * (S['slide'][0] * s1 + extra_slide)
    palm_out = -N                                            # the palm faces the surface
    axis_pt = A + N * gap                                    # a point on the hand axis above the palm surface
    wrist = axis_pt - F * HAND_AXIS_TO_PALM
    sh = arm.pose.bones[nm(side, 'UpperArm')].head.copy()
    L1 = (rig.HEAD0[nm(side, 'LowerArm')] - rig.HEAD0[nm(side, 'UpperArm')]).length
    L2 = (rig.HEAD0[nm(side, 'Hand')] - rig.HEAD0[nm(side, 'LowerArm')]).length
    po = math.radians(S['pole_out'])
    pole = Vector((sx * math.sin(po), -math.cos(po), -0.15))
    K, Teff, deficit = L['two_bone_ik'](sh, wrist, pole, L1, L2)
    du, df = (K - sh).normalized(), (Teff - K).normalized()
    rest_dir = Vector((sx, 0.0, 0.0))
    biceps = perp(df, du) or perp(Vector((0, 1, 0)), du)
    Du = L['aim'](rest_dir, Vector((0, 1, 0)), du, biceps)
    # forearm: hinge roll + limited twist towards the palm
    flex = du.angle(df)
    hinge = Du @ Vector((0.0, 0.0, sx))
    sgn = 1.0 if hinge.dot(du.cross(df)) >= 0 else -1.0
    Df0 = Quaternion(hinge, sgn * flex) @ Du
    n0 = perp(Df0 @ Vector((0.0, 0.0, -1.0)), df)
    nt = perp(palm_out, df) or n0
    ang = math.atan2(n0.cross(nt).dot(df), n0.dot(nt))
    ang_c = max(-math.radians(TWIST_MAX), min(math.radians(TWIST_MAX), ang))
    nf = Quaternion(df, ang_c) @ n0
    Df = L['aim'](rest_dir, Vector((0, 0, -1)), df, nf)
    # hand: fingers along the surface, palm on it; the bend against the forearm is limited
    dh = F.copy()
    a = df.angle(dh)
    if a > math.radians(WRIST_MAX):
        dh = df.slerp(dh, math.radians(WRIST_MAX) / a)
    nh = perp(palm_out, dh) or perp(nf, dh)
    Dh = L['aim'](rest_dir, Vector((0, 0, -1)), dh, nh)
    return dict(Du=Du, Df=Df, Dh=Dh, flex=math.degrees(flex), twist=math.degrees(ang), twist_used=math.degrees(ang_c),
                wrist_bend=math.degrees(df.angle(dh)), deficit=deficit, elbow=K, wrist=wrist)


def finger_rel(side, t, curl_add=0.0):
    """curl_add: one number for all fingers, or a dict per finger; FINGER_FIT is added on top"""
    sx = -1.0 if side == 'L' else 1.0
    S = SIDES[side]
    rel = {}
    extra = {fn: (curl_add.get(fn, 0.0) if isinstance(curl_add, dict) else curl_add) + FINGER_FIT[side][fn] for fn in FINGERS}
    for center, width, fingers, amount in S['settle']:
        b = bump(t, center, width)
        for fn in fingers:
            extra[fn] += amount * b
    for fn in FINGERS:
        for part, c in zip(PARTS, S['curl'][fn]):
            rel[(fn, part)] = Quaternion((0, 1, 0), math.radians(sx * (c + extra[fn] * (1.0 if part == 'Proximal' else 0.6))))
    t1, t2, t3 = S['thumb']
    rel[('Thumb', 'Proximal')] = L['eul'](rx=t1)
    rel[('Thumb', 'Intermediate')] = L['eul'](rz=sx * t2)
    rel[('Thumb', 'Distal')] = L['eul'](rz=sx * t3)
    return rel


def chain_Q(arm, rig, side, sol, t, curl_add=0.0):
    """basis rotations of the arm chain from the world deltas (Q = R^-1 Dp^-1 D R)"""
    nm = rig.nm
    R = rig.R
    out = {}
    Dclav = D_of(arm, nm(side, 'Shoulder'))
    chain = ((nm(side, 'UpperArm'), Dclav, sol['Du']), (nm(side, 'LowerArm'), sol['Du'], sol['Df']), (nm(side, 'Hand'), sol['Df'], sol['Dh']))
    for name, Dp, D in chain:
        out[name] = R[name].inverted() @ Dp.inverted() @ D @ R[name]
    rel = finger_rel(side, t, curl_add)
    for (fn, part), q in rel.items():
        key = fn + part if fn != 'Thumb' else 'Thumb' + part
        name = nm(side, key)
        out[name] = R[name].inverted() @ q @ R[name]            # D = Dp @ rel  ->  Q = R^-1 rel R
    return out


def arm_chain_names(rig):
    names = []
    for side in ('L', 'R'):
        names += [rig.nm(side, p) for p in ('UpperArm', 'LowerArm', 'Hand')]
        names += [rig.nm(side, fn + part) for fn in FINGERS for part in PARTS]
        names += [rig.nm(side, 'Thumb' + part) for part in PARTS]
    return names


def _set_base(arm, base_name):
    ad = arm.animation_data
    base = bpy.data.actions[base_name]
    ad.action = base
    if hasattr(ad, 'action_slot') and base.slots:
        ad.action_slot = base.slots[0]
    return base


def conform(arm, base_name='Yoru_Idle_v2', gaps=tuple(0.014 + 0.002 * k for k in range(13)), tilts=tuple(5.0 * k for k in range(7)),
            curls=tuple(5.0 * k for k in range(7)), pen_lo=-0.0015, pen_hi=0.0020):
    """at frame 0: per side the hand placement (gap above the gear, tilt of the fingers towards it, extra finger curl) like a real resting hand:
    the highest point of the hand (ball of the thumb / heel of the hand) lies ON the gear (pen_lo .. pen_hi), the fingertips lie as close as
    possible without sinking in, the middle of the palm may stay hollow.  Returns {side: (gap, tilt, curl, metrics)}."""
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    nm = rig.nm
    scene = bpy.context.scene
    _set_base(arm, base_name)
    scene.frame_set(0)
    anchors = find_anchors(arm, rig)
    body = rig.body
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    co0 = L['evaluated_coords'](body)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    nr0 = [v.normal.copy() for v in me.vertices]
    ev.to_mesh_clear()
    gear = [i for i, n in enumerate(dom) if vis[i] and (n in (H['hips'], H['leftUpperLeg'], H['rightUpperLeg']) or
                                                       (n.startswith('J_Sec_') and 'Hair' not in n and 'Bust' not in n))]
    kd = KDTree(len(gear))
    for k, i in enumerate(gear):
        kd.insert(co0[i], k)
    kd.balance()
    from mathutils.bvhtree import BVHTree
    polys, _hands = _gear_polys(rig)
    bvhs = {s: BVHTree.FromPolygons(co0, polys[s], all_triangles=False) for s in 'LR'}   # the gear does not move while the arm is tried
    ad = arm.animation_data
    keep_action = ad.action
    ad.action = None                                         # the pose of frame 0 stays; the arm chain is set by hand per candidate
    names = {s: [n for n in arm_chain_names(rig) if n.startswith('J_Bip_%s_' % s)] for s in 'LR'}
    result = {}
    for side in ('L', 'R'):
        groups = {'palm': {nm(side, 'Hand')}, 'all': {nm(side, 'Hand')} | {nm(side, f + p) for f in FINGERS for p in PARTS} | {nm(side, 'Thumb' + p) for p in PARTS}}
        tips = {f: nm(side, f + 'Distal') for f in FINGERS}
        ids_all = [i for i, n in enumerate(dom) if vis[i] and n in groups['all']]
        best = None
        for gap in gaps:
            for tilt in tilts:
                for curl in curls:
                    sol = solve_arm(arm, rig, side, anchors[side], 0.0, gap, tilt=tilt)
                    Q = chain_Q(arm, rig, side, sol, 0.0, curl)
                    for n, q in Q.items():
                        pb = arm.pose.bones[n]
                        pb.rotation_mode = 'QUATERNION'
                        pb.rotation_quaternion = q
                    bpy.context.view_layer.update()
                    co = L['evaluated_coords'](body)
                    dist = {i: signed_to_gear(bvhs[side], co[i]) for i in ids_all}
                    pen = min(dist.values())
                    palm = min(dist[i] for i in ids_all if dom[i] == nm(side, 'Hand'))
                    tip_each = [min(dist[i] for i in ids_all if dom[i] == tips[f]) for f in FINGERS]
                    tip = max(tip_each)
                    # the heel / ball of the hand on the gear, the palm as close as it goes; the fingers are fitted one by one afterwards
                    score = 100.0 * max(0.0, pen_lo - pen) + 10.0 * max(0.0, pen - pen_hi) + 0.5 * max(0.0, palm - 0.006) \
                        + 100.0 * max(0.0, pen_lo - min(tip_each))
                    if best is None or score < best[0]:
                        best = (score, gap, tilt, curl, dict(pen_mm=round(pen * 1000, 1), palm_mm=round(palm * 1000, 1), farthest_tip_mm=round(tip * 1000, 1),
                                                             flex=round(sol['flex'], 1), wrist=round(sol['wrist_bend'], 1)))
        result[side] = best[1:]
    ad.action = keep_action
    scene.frame_set(0)
    return result


def bake_arms(arm, base_name='Yoru_Idle_v2', new_name='Yoru_Idle_v2_r6', gaps=None, tilts=None, curls=None):
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    scene = bpy.context.scene
    base = _set_base(arm, base_name)
    ad = arm.animation_data
    scene.frame_set(0)
    anchors = find_anchors(arm, rig)
    gaps = gaps or {'L': 0.016, 'R': 0.016}
    tilts = tilts or {'L': 0.0, 'R': 0.0}
    curls = curls or {'L': 0.0, 'R': 0.0}
    names = arm_chain_names(rig)
    series = {n: [] for n in names}
    diag = {'L': [], 'R': []}
    def gap_at(side, f):
        g = gaps[side]
        return g[f % NF] if isinstance(g, (list, tuple, np.ndarray)) else g

    for f in range(NF + 1):
        scene.frame_set(f % NF)
        t = (f % NF) / FPS
        for side in ('L', 'R'):
            sol = solve_arm(arm, rig, side, anchors[side], t, gap_at(side, f), tilt=tilts[side])
            Q = chain_Q(arm, rig, side, sol, t, curls[side])
            for n, q in Q.items():
                series[n].append(q)
            diag[side].append((sol['flex'], sol['twist'], sol['twist_used'], sol['wrist_bend'], sol['deficit']))
    act = base.copy()
    act.name = new_name
    act.use_fake_user = True
    fcs = {(fc.data_path, fc.array_index): fc for fc in R3['action_fcurves'](act)}
    changed = 0
    for n in names:
        prev = None
        seq = []
        for q in series[n]:
            if prev is not None and prev.dot(q) < 0.0:
                q = -q
            seq.append(q)
            prev = q
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        for i in range(4):
            fc = fcs.get((dp, i))
            if fc is None:
                continue
            R3['_fill'](fc, [seq[f][i] for f in range(NF + 1)])
            changed += 1
    ad.action = act
    if hasattr(ad, 'action_slot') and act.slots:
        ad.action_slot = act.slots[0]
    scene.frame_set(0)
    summ = {}
    for side in ('L', 'R'):
        d = np.array(diag[side])
        summ[side] = dict(flex=(round(d[:, 0].min(), 1), round(d[:, 0].max(), 1)), flex_step=round(np.abs(np.diff(d[:, 0])).max(), 2),
                          twist_wanted=(round(d[:, 1].min(), 1), round(d[:, 1].max(), 1)), twist_used=(round(d[:, 2].min(), 1), round(d[:, 2].max(), 1)),
                          wrist=(round(d[:, 3].min(), 1), round(d[:, 3].max(), 1)), deficit_mm=round(d[:, 4].max() * 1000, 2),
                          anchor_bone=anchors[side]['bone'], anchor_guess_dist_mm=round(anchors[side]['dist_guess'] * 1000, 1))
    return {'action': act.name, 'curves_changed': changed, 'arms': summ}


def hand_contact(arm, rig, frames):
    """per side the smallest SIGNED distance of the visible hand vertices (incl. thumb) to the gear / thigh surface over the frames
    (m; + = gap, - = inside, measured along the normal of the nearest gear vertex) and the frame of it"""
    H, nm = rig.H, rig.nm
    body = rig.body
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    gear = [i for i, n in enumerate(dom) if vis[i] and (n in (H['hips'], H['leftUpperLeg'], H['rightUpperLeg']) or
                                                       (n.startswith('J_Sec_') and 'Hair' not in n and 'Bust' not in n))]
    hs = {s: {nm(s, 'Hand')} | {nm(s, f + p) for f in FINGERS for p in PARTS} | {nm(s, 'Thumb' + p) for p in PARTS} for s in 'LR'}
    ids = {s: [i for i, n in enumerate(dom) if vis[i] and n in hs[s]] for s in 'LR'}
    out = {'L': (9.0, None), 'R': (9.0, None)}
    per = {'L': [], 'R': []}
    sc = bpy.context.scene
    for f in frames:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        co = [v.co.copy() for v in me.vertices]
        nr = [v.normal.copy() for v in me.vertices]
        ev.to_mesh_clear()
        kd = KDTree(len(gear))
        for k, i in enumerate(gear):
            kd.insert(co[i], k)
        kd.balance()
        for s in 'LR':
            best = 9.0
            for i in ids[s]:
                _, k, d = kd.find(co[i])
                j = gear[k]
                sd = (co[i] - co[j]).dot(nr[j])
                val = d if sd >= 0 else -abs(sd)
                best = min(best, val)
            per[s].append(best)
            if best < out[s][0]:
                out[s] = (best, f)
    sc.frame_set(0)
    return out, per


def calibrate(arm, base_name='Yoru_Idle_v2', new_name='Yoru_Idle_v2_r6', target=0.0015, rounds=4, frames=range(0, 360, 12)):
    """bake, measure the hand contact, move the hand axis along the gear normal so the deepest hand point sits target above the surface"""
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    gaps = {'L': 0.016, 'R': 0.016}
    hist = []
    info = None
    for r in range(rounds):
        info = bake_arms(arm, base_name, new_name + '_cal', gaps)
        c, per = hand_contact(arm, rig, frames)
        hist.append({s: (round(gaps[s] * 1000, 1), round(c[s][0] * 1000, 1), round(max(per[s]) * 1000, 1)) for s in 'LR'})
        done = all(abs(c[s][0] - target) < 0.0007 for s in 'LR')
        if done:
            break
        for s in 'LR':
            gaps[s] += (target - c[s][0])
        old = bpy.data.actions.get(new_name + '_cal')
        if old is not None and r < rounds - 1:
            arm.animation_data.action = bpy.data.actions[base_name]
            bpy.data.actions.remove(old)
    act = bpy.data.actions[new_name + '_cal']
    if bpy.data.actions.get(new_name):
        bpy.data.actions[new_name].name = new_name + '_previous'
    act.name = new_name
    return {'gaps_mm': {s: round(v * 1000, 1) for s, v in gaps.items()}, 'history (gap, min contact, max contact) mm': hist, 'bake': info}


def fit_fingers(arm, base_name, params, target=0.0015, lo=-12.0, hi=45.0, iters=9):
    """at frame 0, with the hand placed by params {side: (gap, tilt, curl)}: per finger the extra curl (deg, mostly at the knuckle) that lays
    the fingertip on the gear surface (target above it).  Fills FINGER_FIT and returns it with the reached tip distances (mm)."""
    from mathutils.bvhtree import BVHTree
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    nm = rig.nm
    scene = bpy.context.scene
    _set_base(arm, base_name)
    scene.frame_set(0)
    anchors = find_anchors(arm, rig)
    polys, hand_all = _gear_polys(rig)
    body = rig.body
    co0 = L['evaluated_coords'](body)
    dom = L['vertex_groups_by_bone'](rig)
    vis = L['visible_vertices'](body)
    ad = arm.animation_data
    keep = ad.action
    ad.action = None
    report = {}
    for side in 'LR':
        bvh = BVHTree.FromPolygons(co0, polys[side], all_triangles=False)
        gap, tilt, curl = params[side]
        for fn in FINGERS:
            FINGER_FIT[side][fn] = 0.0
        sol = solve_arm(arm, rig, side, anchors[side], 0.0, gap, tilt=tilt)
        # the whole finger counts: it stops curling when ANY of its three segments touches (only the tips were measured at first,
        # a middle segment could sink in)
        tip_ids = {fn: [i for i, n in enumerate(dom) if vis[i] and n in (nm(side, fn + 'Proximal'), nm(side, fn + 'Intermediate'), nm(side, fn + 'Distal'))]
                   for fn in FINGERS}

        def tipdist(fn):
            for n, q in chain_Q(arm, rig, side, sol, 0.0, curl).items():
                pb = arm.pose.bones[n]
                pb.rotation_mode = 'QUATERNION'
                pb.rotation_quaternion = q
            bpy.context.view_layer.update()
            co = L['evaluated_coords'](body)
            return min(signed_to_gear(bvh, co[i]) for i in tip_ids[fn])

        rep = {}
        for fn in FINGERS:
            FINGER_FIT[side][fn] = lo
            if tipdist(fn) <= target:                    # touches even when (almost) straight
                rep[fn] = (lo, round(tipdist(fn) * 1000, 1))
                continue
            FINGER_FIT[side][fn] = hi
            if tipdist(fn) > target:                     # cannot reach the surface
                rep[fn] = (hi, round(tipdist(fn) * 1000, 1))
                continue
            a_, b_ = lo, hi
            for _ in range(iters):
                m = 0.5 * (a_ + b_)
                FINGER_FIT[side][fn] = m
                if tipdist(fn) > target:
                    a_ = m
                else:
                    b_ = m
            FINGER_FIT[side][fn] = b_
            rep[fn] = (round(b_, 1), round(tipdist(fn) * 1000, 1))
        report[side] = rep
    ad.action = keep
    scene.frame_set(0)
    return report


def periodic_smooth(x, sigma_frames):
    """Gaussian smoothing of a periodic per-frame signal (keeps the loop seamless)"""
    x = np.asarray(x, dtype=float)
    n = len(x)
    X = np.fft.rfft(x)
    k = np.fft.rfftfreq(n, 1.0)
    return np.fft.irfft(X * np.exp(-0.5 * (2.0 * math.pi * k * sigma_frames) ** 2), n)


def contact_pass(arm, base_name, params, target=0.0010, rounds=2, sigma=6.0, name='Yoru_Idle_v2_r6'):
    """bake with the conform placement, then lift / lower the hand along the gear normal frame by frame so its deepest point stays about
    target above the gear; the correction is smoothed over time (periodic) so the hand never jitters.  params {side: (gap, tilt, curl)}"""
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    gaps = {s: np.full(NF, params[s][0]) for s in 'LR'}
    tilts = {s: params[s][1] for s in 'LR'}
    curls = {s: params[s][2] for s in 'LR'}
    hist = []
    info = None
    tmp = name + '_pass'
    for r in range(rounds + 1):
        if bpy.data.actions.get(tmp):
            _set_base(arm, base_name)
            bpy.data.actions.remove(bpy.data.actions[tmp])
        info = bake_arms(arm, base_name, tmp, {s: list(gaps[s]) for s in 'LR'}, tilts, curls)
        c, per = hand_contact(arm, rig, range(NF))
        hist.append({s: (round(min(per[s]) * 1000, 2), round(max(per[s]) * 1000, 2)) for s in 'LR'})
        if r == rounds:
            break
        for s in 'LR':
            corr = periodic_smooth(target - np.array(per[s]), sigma)
            gaps[s] = gaps[s] + corr
    if bpy.data.actions.get(name):
        bpy.data.actions[name].name = name + '_previous'
    bpy.data.actions[tmp].name = name
    return {'contact_min_max_mm per round': hist, 'gap_range_mm': {s: (round(gaps[s].min() * 1000, 1), round(gaps[s].max() * 1000, 1)) for s in 'LR'},
            'bake': info, 'gaps': {s: [float(g) for g in gaps[s]] for s in 'LR'}}


def _gear_polys(rig):
    """per side the polygons of the visible gear / thigh surface that face OUTWARDS on that side (rest normal x towards the side), and the
    hand vertex sets.  Only outward faces: thin straps have back faces that point inwards, and a point behind such a strap read as
    'inside the gear' by 25 mm (a false alarm that made the contact control swing)."""
    H, nm = rig.H, rig.nm
    body = rig.body
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    gear_v = set(i for i, n in enumerate(dom) if vis[i] and (n in (H['hips'], H['leftUpperLeg'], H['rightUpperLeg']) or
                                                            (n.startswith('J_Sec_') and 'Hair' not in n and 'Bust' not in n)))
    polys = {}
    for s, sx in (('L', -1.0), ('R', 1.0)):
        polys[s] = [list(p.vertices) for p in body.data.polygons
                    if p.normal.x * sx > 0.2 and all(v in gear_v for v in p.vertices)]
    hs = {s: {nm(s, 'Hand')} | {nm(s, f + p) for f in FINGERS for p in PARTS} | {nm(s, 'Thumb' + p) for p in PARTS} for s in 'LR'}
    hand_ids = {s: [i for i, n in enumerate(dom) if vis[i] and n in hs[s]] for s in 'LR'}
    return polys, hand_ids


def signed_to_gear(bvh, p):
    loc, nrm, idx, dist = bvh.find_nearest(p)
    if loc is None:
        return 9.0
    return dist if (p - loc).dot(nrm) >= 0 else -dist


def surface_contact(arm, rig, frames, polys, ids):
    """per frame and side: the smallest signed distance of the given hand vertices to the outward gear SURFACE of that side
    (BVH, smooth; + gap, - inside).  polys: {side: polygons} from _gear_polys"""
    from mathutils.bvhtree import BVHTree
    body = rig.body
    sc = bpy.context.scene
    out = {s: [] for s in ids}
    for f in frames:
        sc.frame_set(f)
        co = L['evaluated_coords'](body)
        for s, lst in ids.items():
            bvh = BVHTree.FromPolygons(co, polys[s], all_triangles=False)
            best = 9.0
            for i in lst:
                loc, nrm, idx, dist = bvh.find_nearest(co[i])
                if loc is None:
                    continue
                sd = (co[i] - loc).dot(nrm)
                val = dist if sd >= 0 else -dist
                best = min(best, val)
            out[s].append(best)
    sc.frame_set(0)
    return out


def contact_pass2(arm, base_name, params, target=0.0012, rounds=5, sigma=4.0, gain=0.6, name='Yoru_Idle_v2_r6'):
    """bake with the conform placement; the deepest point of the WHOLE hand (palm, fingers, thumb) is kept about target above the gear
    SURFACE in every frame by moving the hand along the gear normal; the correction is damped and smoothed over time (periodic, seamless).
    (Measuring only the points that touch at frame 0 let other parts of the hand sink in on the left side.)"""
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    polys, hand_all = _gear_polys(rig)
    gaps = {s: np.full(NF, params[s][0]) for s in 'LR'}
    tilts = {s: params[s][1] for s in 'LR'}
    curls = {s: params[s][2] for s in 'LR'}
    tmp = name + '_pass'
    hist = []
    contact_ids = None
    info = None
    for r in range(rounds + 1):
        if bpy.data.actions.get(tmp):
            _set_base(arm, base_name)
            bpy.data.actions.remove(bpy.data.actions[tmp])
        info = bake_arms(arm, base_name, tmp, {s: list(gaps[s]) for s in 'LR'}, tilts, curls)
        if contact_ids is None:                                    # the points that touch at frame 0
            d0 = surface_contact(arm, rig, [0], polys, {s: hand_all[s] for s in 'LR'})
            from mathutils.bvhtree import BVHTree
            bpy.context.scene.frame_set(0)
            co = L['evaluated_coords'](rig.body)
            contact_ids = {}
            for s in 'LR':
                bvh = BVHTree.FromPolygons(co, polys[s], all_triangles=False)
                vals = []
                for i in hand_all[s]:
                    loc, nrm, idx, dist = bvh.find_nearest(co[i])
                    if loc is not None:
                        vals.append(((co[i] - loc).dot(nrm) if dist > 0 else 0.0, i))
                vals.sort()
                contact_ids[s] = [i for v, i in vals[:40]]
        per = surface_contact(arm, rig, range(NF), polys, {s: hand_all[s] for s in 'LR'})
        full = surface_contact(arm, rig, range(0, NF, 6), polys, contact_ids)
        hist.append({s: dict(contact_pts=(round(min(per[s]) * 1000, 2), round(max(per[s]) * 1000, 2)),
                             whole_hand=(round(min(full[s]) * 1000, 2), round(max(full[s]) * 1000, 2))) for s in 'LR'})
        if r == rounds:
            break
        for s in 'LR':
            corr = periodic_smooth(target - np.array(per[s]), sigma)
            gaps[s] = gaps[s] + gain * corr
    if bpy.data.actions.get(name):
        bpy.data.actions[name].name = name + '_previous'
    bpy.data.actions[tmp].name = name
    return {'rounds': hist, 'gap_range_mm': {s: (round(gaps[s].min() * 1000, 1), round(gaps[s].max() * 1000, 1)) for s in 'LR'},
            'bake': info, 'gaps': {s: [float(g) for g in gaps[s]] for s in 'LR'}}


def gap_step(arm, base_name, params, gaps, target=0.0012, sigma=2.0, name='Yoru_Idle_v2_r6_step'):
    """one direct step: bake with the per-frame gaps, measure the deepest point of the whole hand against the gear surface in EVERY frame,
    and return the gaps that put it at target (moving the hand along the gear normal moves that point by the same amount), lightly smoothed
    over time (periodic).  Also returns the measured contact (m) of this bake."""
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    polys, hand_all = _gear_polys(rig)
    if bpy.data.actions.get(name):
        _set_base(arm, base_name)
        bpy.data.actions.remove(bpy.data.actions[name])
    tilts = {s: params[s][1] for s in 'LR'}
    curls = {s: params[s][2] for s in 'LR'}
    info = bake_arms(arm, base_name, name, {s: list(gaps[s]) for s in 'LR'}, tilts, curls)
    per = surface_contact(arm, rig, range(NF), polys, {s: hand_all[s] for s in 'LR'})
    new = {s: np.asarray(gaps[s], dtype=float) + periodic_smooth(target - np.array(per[s]), sigma) for s in 'LR'}
    return new, {s: np.array(per[s]) for s in 'LR'}, info


def gap_bisect(arm, base_name, params, side, frames, target=0.0012, lo=0.020, hi=0.065, iters=9):
    """per frame: the gap (hand axis above the gear along its normal) at which the deepest point of the whole hand sits target above the
    outward gear surface, by bisection with the arm set directly (no bake).  Robust where the deepest point jumps between thumb ball and
    fingers.  Returns {frame: gap}."""
    from mathutils.bvhtree import BVHTree
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    scene = bpy.context.scene
    base = _set_base(arm, base_name)
    scene.frame_set(0)
    anchors = find_anchors(arm, rig)
    polys, hand_all = _gear_polys(rig)
    body = rig.body
    ad = arm.animation_data
    gap0, tilt, curl = params[side]
    out = {}
    for f in frames:
        ad.action = base
        if hasattr(ad, 'action_slot') and base.slots:
            ad.action_slot = base.slots[0]
        scene.frame_set(f)
        ad.action = None                                   # the body pose of this frame stays, only the arm chain is set below
        co = L['evaluated_coords'](body)
        bvh = BVHTree.FromPolygons(co, polys[side], all_triangles=False)
        t = f / FPS

        def contact(g):
            sol = solve_arm(arm, rig, side, anchors[side], t, g, tilt=tilt)
            for n, q in chain_Q(arm, rig, side, sol, t, curl).items():
                pb = arm.pose.bones[n]
                pb.rotation_mode = 'QUATERNION'
                pb.rotation_quaternion = q
            bpy.context.view_layer.update()
            c2 = L['evaluated_coords'](body)
            return min(signed_to_gear(bvh, c2[i]) for i in hand_all[side])

        a_, b_ = lo, hi
        for _ in range(iters):
            m = 0.5 * (a_ + b_)
            if contact(m) < target:
                a_ = m
            else:
                b_ = m
        out[f] = b_
    ad.action = base
    if hasattr(ad, 'action_slot') and base.slots:
        ad.action_slot = base.slots[0]
    scene.frame_set(0)
    return out


def build_arms(arm, base_name='Yoru_Idle_v2', name='Yoru_Idle_v2_r6'):
    """the whole round 6 arm pass: hand placement on the gear (conform), fingers laid on the gear (fit_fingers), contact kept over the loop
    (contact_pass2).  Only the 36 arm-chain bones change."""
    par = conform(arm, base_name, curls=(0.0,))
    params = {s: par[s][:3] for s in 'LR'}
    fingers = fit_fingers(arm, base_name, params)
    res = contact_pass2(arm, base_name, params, name=name)
    return {'conform': {s: par[s] for s in 'LR'}, 'fingers (extra curl deg, tip mm)': fingers, 'contact rounds': res['rounds'],
            'gap_range_mm': res['gap_range_mm'], 'arms': res['bake']['arms'], 'curves_changed': res['bake']['curves_changed']}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    out = argv[0]
    name = argv[1] if len(argv) > 1 else 'Yoru_A2'
    print('[arms r6]', build_arms(bpy.data.objects[name]), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
