"""
Yoru - LAUF v2 (the main run on W, NTE reference): library, no side effects on import (live and background).

Gait: build_run.py (the run gait solver of the old sprint, unchanged) is run with the NTE timing into Blender/work/Lauf_v2/gen_rN/
(40 frames at 60 fps = 0.667 s per cycle, 4.0 m/s, stance 25 % of the cycle, see GEN_ARGS).  This library then
  - appends that clip and replaces the ARM CHAINS (clavicle, upper arm, forearm, hand, fingers, thumb) with the organic arm layer of the walk
    round 4 (build_walk_v2_round4.py, ArmLayer), re-tuned to the NTE angles: upper arm about +33 deg forward / -37 deg back from the plumb
    line, elbow 64 deg (behind) .. 100 deg (in front), loose fist that opens a little behind, overlapping action clavicle -> upper arm ->
    elbow -> forearm roll -> wrist -> fingers, forward swing quicker than the back swing, left and right not mirrored;
  - fits the arms against the gear with the exact intersection test (GearTester of build_walk_v2_lib.py, here WITH the bust: the fists pass
    in front of the chest), the least outward turn of the upper arm per frame, smoothed over the loop;
  - face B, Cycles modifiers (endless loop), a floor lane that scrolls with the ground motion G(phi) of the gait (planted shoe stays on its tile).
Blender axes for Yoru: +Y forward, her right = +X, up = +Z.
"""
import bpy, os, sys, math, json
from mathutils import Vector, Quaternion, Euler, Matrix

SCRIPTS = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
BL = r'C:\Users\valen\ZeroProtocol\Blender'
WORK = os.path.join(BL, 'work', 'Lauf_v2')
OLD_RUN = os.path.join(BL, 'Yoru_Run.blend')
FPS = 60
NF = 40
TAU = 2.0 * math.pi
TWIST_MAX = 18.0
FINGERS = ('Index', 'Middle', 'Ring', 'Little')
PARTS = ('Proximal', 'Intermediate', 'Distal')
FACE_B = {'Fcl_EYE_Angry': 0.40, 'Fcl_EYE_Fun': 0.16, 'Fcl_MTH_Neutral': 0.55, 'Fcl_MTH_Close': 0.20, 'Fcl_BRW_Angry': 0.50}
# gait of the new run (build_run.py arguments) and of the old sprint (for its floor lane)
GAIT_NEU = dict(SPEED=4.0, NF=40, PH_TO=0.25, speed_var=0.08)
GAIT_ALT = dict(SPEED=5.0, NF=36, PH_TO=0.2222, speed_var=0.08)
GEN_ARGS = ('NF=40 SPEED=4.0 PH_TO=0.23 KD=0.12 KA=0.65 KN_TD=16 KN_TO=26 lean=34 hips_lean=15 T_REAR=2.5 P_FWD=1.3 SW_FLEX_U=0.38 '
            'KN_SW=108 KN_EXT=20 T_FWD=3.3 HEEL_DELAY=1.0 HEEL_RAMP=1.8 SW_STOP_T=5.2 BASE=0.045 neck_pitch=26 head_pitch=17 ARM_FIT=0 '
            'tail_abs=12,0,-10,-14,-6,14,32,32 wind_hair=0.11 wind_lift=0.0 wind_ear=0.2')
GAIT_NEU['PH_TO'] = 0.23

# arm style (angles in deg, lags in fractions of the cycle; 1 frame = 0.025).  Round 1 values after the comparison with NTE
# (first try: phase +0.06 = extremes just after the touchdowns as in build_run.py -> both fists hung in front during the flight;
#  NTE has the arms spread in the flight, the forward extreme just after the toe-off of the same side)
STYLE = dict(
    phase=-0.13,                      # extremes in the middle of the flight (right arm forward at phi 0.37, left at 0.87)
    a0=0.0, a_fwd=28.0, a_back=38.0,  # upper arm swing about the shoulder from the plumb line (heading frame): +28 forward, -38 back
    warp=0.12, ease=0.45,             # forward drive quicker than the way back; eases into the extremes
    ab0=14.0, ab_arc=2.0,             # upper arm out from the side (gear); a little further out at the back, in at the front
    tw0=0.0, tw_u=5.0,                # internal rotation in front (the fist moves towards the midline), external behind
    carry=3.0, yaw_follow=0.4,        # forearm leans out a little; the swing plane follows 40 % of the chest's turn
    el_min=55.0, el_max=92.0, lag_e=0.04,       # elbow flexion behind / in front; the elbow trails the upper arm
    pron0=6.0, pron=8.0, lag_p=0.10,            # forearm roll (pronation turns the palm back), trails
    wf0=8.0, wf=14.0, wd0=6.0, wd=8.0, lag_w=0.14, ribbon=1.0, k_flex=0.9, k_cross=0.6,   # wrist: flex / deviation from the ribbon trail
    cu0={'Index': (34, 46, 26), 'Middle': (42, 56, 32), 'Ring': (50, 62, 36), 'Little': (56, 68, 40)},  # loose fist
    cu=12.0, lag_f=0.22,              # the fist closes a little in front and opens behind, each finger / phalanx a little later
    th=(18.0, 14.0, 10.0), th_dyn=6.0, thumb_run=(30.0, 10.0, 18.0, 12.0), spread=(4.0, 1.5, -1.5, -5.0),
    clav_drop0=4.0, clav_back0=1.0, clav_prot=5.0, clav_elev=2.5, lag_c=-0.03,   # shoulder blade glides with the arm, leads a little
    asym_amp=0.94, asym_ph=0.025, asym_el=-3.0,  # left arm: a little less reach, a little later, a little less bend (not mirrored)
)


def log(*a):
    print('[lauf_v2]', *a, flush=True)


def load(name):
    ns = {'__file__': os.path.join(SCRIPTS, name)}
    exec(compile(open(ns['__file__'], encoding='utf-8').read(), ns['__file__'], 'exec'), ns)
    return ns


def eul(rx=0.0, ry=0.0, rz=0.0):
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_quaternion()


def perp(v, axis):
    w = v - axis * v.dot(axis)
    return w.normalized() if w.length > 1e-9 else None


def frame_rot(d, n):
    d = Vector(d).normalized()
    n = Vector(n)
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed().to_quaternion()


def aim(rest_dir, rest_nrm, tgt_dir, tgt_nrm):
    return frame_rot(tgt_dir, tgt_nrm) @ frame_rot(rest_dir, rest_nrm).inverted()


def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    par = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in par.children]:
        par.children.link(c)
    return c


def fcurves(action):
    if hasattr(action, 'fcurves'):
        try:
            return list(action.fcurves)
        except Exception:
            pass
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


# ------------------------------------------------------------------ ground motion (same formula as build_run.py)
def ground(g, phi):
    """how far the ground has moved back (m) at cycle phase phi (may exceed 1): G(1) = stride"""
    VT = g['SPEED'] * g['NF'] / float(FPS)
    b, var = g['PH_TO'], g['speed_var']
    k_ = math.floor(phi)
    q_ = phi - k_

    def dip_int(p):
        k = int(math.floor(p / 0.5 + 1e-12))
        q = p - 0.5 * k
        if q < b:
            return k * (2.0 * b / math.pi) + (b / math.pi) * (1.0 - math.cos(math.pi * q / b))
        return (k + 1) * (2.0 * b / math.pi)

    one = VT * (q_ * (1.0 + var * 4.0 * b / math.pi) - var * dip_int(q_))
    return k_ * VT + one


# ------------------------------------------------------------------ the arm layer (from build_walk_v2_round4.py, NTE angles)
def swing(x, st):
    """+1 forward extreme at x = 0, -1 back extreme; the forward swing is quicker than the back swing; eases at the extremes"""
    th = TAU * (x % 1.0)
    c = math.cos(th - st['warp'] * (1.0 - math.cos(th)))
    return (1.0 - st['ease']) * c + st['ease'] * 0.5 * (3.0 * c - c ** 3)


class ArmLayer:
    def __init__(self, arm, st=None, H=None):
        self.arm = arm
        self.st = dict(st or STYLE)
        self.H = H or load('build_idle_v2_lib.py')['humanoid_map']()
        self.bones = arm.data.bones
        self.R = {b.name: b.matrix_local.to_quaternion() for b in self.bones}
        self.HEAD0 = {b.name: b.head_local.copy() for b in self.bones}

    def nm(self, side, part):
        return self.H[('left' if side == 'L' else 'right') + part]

    def side_params(self, side):
        st = dict(self.st)
        if side == 'L':
            for k in ('a_fwd', 'a_back', 'tw_u', 'pron', 'wf', 'wd', 'cu', 'clav_prot', 'clav_elev'):
                st[k] = st[k] * st['asym_amp']
            st['el_max'] = st['el_max'] + st['asym_el']
        return st

    def chain(self, side, phi, pbs):
        st = self.side_params(side)
        sx = 1.0 if side == 'R' else -1.0
        R, HEAD0, nm = self.R, self.HEAD0, self.nm
        # left arm forward at the right touchdown (phi 0) + phase; right arm half a cycle later
        x0 = phi - st['phase'] - (0.5 if side == 'R' else 0.0) - (st['asym_ph'] if side == 'L' else 0.0)
        s_c = swing(x0 - st['lag_c'], st)
        s_p = swing(x0 - st['lag_p'], st)
        n_uc, n_cl = self.H['upperChest'], nm(side, 'Shoulder')
        D_uc = pbs[n_uc].matrix.to_quaternion() @ R[n_uc].inverted()
        drop = st['clav_drop0'] - st['clav_elev'] * s_c
        back = st['clav_back0'] - st['clav_prot'] * s_c
        rel_c = eul(ry=sx * drop, rz=-sx * back)
        D_cl = D_uc @ rel_c
        n_u, n_f, n_h = nm(side, 'UpperArm'), nm(side, 'LowerArm'), nm(side, 'Hand')
        fwd = D_uc @ Vector((0.0, 1.0, 0.0))
        # the swing plane follows only part of the chest's turn (full follow made the forward fist cross in front of the other breast)
        Fy = Quaternion((0.0, 0.0, 1.0), st.get('yaw_follow', 1.0) * math.atan2(-fwd.x, fwd.y))

        def dirs(x):
            su = swing(x, st)
            se = swing(x - st['lag_e'], st)
            sr = swing(x - 0.5 * st['lag_e'], st)
            alpha = math.radians(st['a0'] + 0.5 * (st['a_fwd'] + st['a_back']) * su + 0.5 * (st['a_fwd'] - st['a_back']))
            ab = math.radians(st['ab0'] - st['ab_arc'] * sr)
            du_ = Quaternion((1.0, 0.0, 0.0), alpha) @ Quaternion((0.0, 1.0, 0.0), -sx * ab) @ Vector((0.0, 0.0, -1.0))
            fl0 = perp(Vector((0.0, 1.0, 0.0)), du_)
            fl_ = Quaternion(du_, -sx * math.radians(st['tw0'] + st['tw_u'] * sr)) @ fl0
            beta = math.radians(st['el_min'] + (st['el_max'] - st['el_min']) * 0.5 * (se + 1.0))
            df_ = du_ * math.cos(beta) + fl_ * math.sin(beta)
            df_ = Quaternion(fl_, -sx * math.radians(st['carry'])) @ df_
            return du_, fl_, df_.normalized(), alpha

        du_l, fl_l, df_l, alpha = dirs(x0)
        df_lag = dirs(x0 - st['lag_w'])[2]
        q_r = df_l.rotation_difference(df_lag)
        dh_l = (Quaternion(q_r.axis, q_r.angle * st['ribbon']) @ df_l).normalized() if q_r.angle > 1e-6 else df_l.copy()
        du, df, fl = Fy @ du_l, (Fy @ df_l).normalized(), Fy @ fl_l
        rest = Vector((sx, 0.0, 0.0))
        Du = aim(rest, Vector((0, 1, 0)), du, fl)
        flex = du.angle(df)
        hinge = Du @ Vector((0.0, 0.0, sx))
        sgn = 1.0 if hinge.dot(du.cross(df)) >= 0 else -1.0
        Df0 = Quaternion(hinge, sgn * flex) @ Du
        n0 = perp(Df0 @ Vector((0.0, 0.0, -1.0)), df)
        tw = max(-TWIST_MAX, min(TWIST_MAX, st['pron0'] + st['pron'] * s_p))
        nf = Quaternion(df, -sx * math.radians(tw)) @ n0
        Df = aim(rest, Vector((0, 0, -1)), df, nf)
        dr = (Fy @ dh_l).normalized()
        q_t = df.rotation_difference(dr)
        rv = q_t.axis * q_t.angle if q_t.angle > 1e-6 else Vector((0.0, 0.0, 0.0))
        a_flex = df.cross(nf).normalized()
        flex_t = math.degrees(rv.dot(a_flex))
        dev_t = math.degrees(sx * rv.dot(nf))
        wf_d = st['wf0'] + max(-st['wf'], min(st['wf'], st['k_flex'] * flex_t + st['k_cross'] * abs(dev_t) * (1.0 if dev_t >= 0 else -1.0)))
        wd_d = st['wd0'] + max(-st['wd'], min(st['wd'], dev_t))
        wf, wd = math.radians(wf_d), math.radians(wd_d)
        ulnar = sx * nf.cross(df)
        dh = (df * (math.cos(wf) * math.cos(wd)) + nf * math.sin(wf) + ulnar * math.sin(wd)).normalized()
        nh = perp(nf, dh) or nf
        Dh = aim(rest, Vector((0, 0, -1)), dh, nh)
        Q = {n_cl: R[n_cl].inverted() @ rel_c @ R[n_cl],
             n_u: R[n_u].inverted() @ D_cl.inverted() @ Du @ R[n_u],
             n_f: R[n_f].inverted() @ Du.inverted() @ Df @ R[n_f],
             n_h: R[n_h].inverted() @ Df.inverted() @ Dh @ R[n_h]}
        spread = st.get('spread', (4.0, 1.5, -1.5, -5.0))
        for fi, fn in enumerate(FINGERS):
            for pj, part in enumerate(PARTS):
                s_f = swing(x0 - st['lag_f'] - 0.02 * fi - 0.015 * pj, st)
                c = st['cu0'][fn][pj] + st['cu'] * s_f * (1.0 if pj == 0 else 0.7)
                n = nm(side, fn + part)
                rel = Quaternion((0, 1, 0), math.radians(sx * c))
                if pj == 0:
                    rel = eul(rz=sx * spread[fi]) @ rel
                Q[n] = R[n].inverted() @ rel @ R[n]
        # thumb as in build_run.py (laid along the fist and curled; the first try bent it about other axes and it stuck out forward)
        s_t = [swing(x0 - st['lag_f'] - d, st) for d in (0.04, 0.07, 0.10)]
        t_add, t1, t2, t3 = st.get('thumb_run', (30.0, 10.0, 18.0, 12.0))
        td = st['th_dyn']
        for part, rel in (('ThumbProximal', eul(rz=-sx * t_add) @ Quaternion((0, 1, 0), math.radians(sx * (t1 + td * s_t[0])))),
                          ('ThumbIntermediate', Quaternion((0, 1, 0), math.radians(sx * (t2 + 0.6 * td * s_t[1])))),
                          ('ThumbDistal', Quaternion((0, 1, 0), math.radians(sx * (t3 + 0.5 * td * s_t[2]))))):
            n = nm(side, part)
            Q[n] = R[n].inverted() @ rel @ R[n]
        diag = dict(elbow=math.degrees(flex), twist=tw, wrist=math.degrees(df.angle(dh)), swing_u=math.degrees(alpha))
        return Q, diag


def sample_poses(arm, nf):
    scene = bpy.context.scene
    pbs = arm.pose.bones
    names = [pb.name for pb in pbs]
    out = []
    for f in range(nf):
        scene.frame_set(f)
        out.append({n: (pbs[n].location.copy(), pbs[n].rotation_quaternion.copy(), pbs[n].scale.copy()) for n in names})
    return out


def write_quat_keys(act, arm, newQ, nf):
    """newQ: per frame {bone: quaternion}; keys 0 .. nf (key nf == key 0), linear, Cycles modifier"""
    by = {}
    for fc in fcurves(act):
        by.setdefault(fc.data_path, {})[fc.array_index] = fc
    pbs = arm.pose.bones
    n_done = 0
    for n in newQ[0].keys():
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        if dp not in by:
            pb = pbs[n]
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = newQ[0][n]
            pb.keyframe_insert('rotation_quaternion', frame=0)
            by = {}
            for fc in fcurves(act):
                by.setdefault(fc.data_path, {})[fc.array_index] = fc
        seq, prev = [], None
        for f in range(nf):
            q = newQ[f][n].copy()
            if prev is None and q.w < 0:
                q = -q
            if prev is not None and prev.dot(q) < 0:
                q = -q
            seq.append(q)
            prev = q
        seq.append(seq[0] if seq[0].dot(seq[-1]) >= 0 else -seq[0])
        for i in range(4):
            fc = by[dp][i]
            kp = fc.keyframe_points
            while len(kp) > nf + 1:
                kp.remove(kp[-1])
            if len(kp) < nf + 1:
                kp.add(nf + 1 - len(kp))
            co = []
            for f in range(nf + 1):
                co.extend((float(f), float(seq[f][i])))
            kp.foreach_set('co', co)
            for k in kp:
                k.interpolation = 'LINEAR'
            fc.update()
            if not any(m.type == 'CYCLES' for m in fc.modifiers):
                fc.modifiers.new('CYCLES')
        n_done += 1
    return n_done


def apply_arm_layer(arm, st=None, nf=NF):
    layer = ArmLayer(arm, st)
    ad = arm.animation_data
    act = ad.action
    slot = getattr(ad, 'action_slot', None)
    pbs = arm.pose.bones
    poses = sample_poses(arm, nf)
    ad.action = None
    newQ, diags = [], []
    for f in range(nf):
        for n, (lo, ro, sc) in poses[f].items():
            pbs[n].location, pbs[n].rotation_quaternion, pbs[n].scale = lo, ro, sc
        bpy.context.view_layer.update()
        qf, df_ = {}, {}
        for side in ('L', 'R'):
            q, dg = layer.chain(side, f / float(nf), pbs)
            qf.update(q)
            df_[side] = dg
        newQ.append(qf)
        diags.append(df_)
    ad.action = act
    if slot is not None and hasattr(ad, 'action_slot'):
        ad.action_slot = slot
    n = write_quat_keys(act, arm, newQ, nf)
    return n, diags


# ------------------------------------------------------------------ exact gear test WITH the bust (the fists pass in front of the chest)
def make_tester(arm, with_bust=True):
    W = load('build_walk_v2_lib.py')
    L = W['L']
    rig = L['Rig'](arm, L['humanoid_map']())
    t = W['GearTester'](rig)
    if with_bust:
        H = rig.H
        body = rig.body
        vis = L['visible_vertices'](body)
        dom = L['vertex_groups_by_bone'](rig)
        solid = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg']}
        gear_v = set(i for i, n in enumerate(dom) if vis[i] and (n in solid or (n.startswith('J_Sec_') and 'Hair' not in n)))
        t.gear_polys = [list(p.vertices) for p in body.data.polygons if all(v in gear_v for v in p.vertices)]
    return W, L, rig, t


def fix_arms(arm, nf=NF, hi=24.0, iters=6, margin=0.6):
    """per frame and side the least extra outward turn (deg) of the upper arm about the chest's forward axis through the shoulder joint
    that leaves hand and forearm (beyond the elbow end) with no exact intersection with torso, bust, thighs and gear; dilated, smoothed
    over the loop, checked again and baked into the upper-arm keys (copy of fix_arms in build_walk_v2_round3.py, with the bust)"""
    W, L, rig, tester = make_tester(arm, True)
    scene = bpy.context.scene
    ad = arm.animation_data
    act = ad.action
    slot = getattr(ad, 'action_slot', None)
    pbs = arm.pose.bones
    names = [pb.name for pb in pbs]
    R_uc = arm.data.bones[rig.H['upperChest']].matrix_local.to_quaternion()
    poses = sample_poses(arm, nf)
    ad.action = None

    def set_pose(f, side=None, delta=0.0):
        for n, (lo, ro, sc) in poses[f].items():
            pbs[n].location, pbs[n].rotation_quaternion, pbs[n].scale = lo, ro, sc
        bpy.context.view_layer.update()
        if side is None:
            return None
        pb = pbs[rig.nm(side, 'UpperArm')]
        if delta == 0.0:
            return pb.rotation_quaternion.copy()
        D_c = pbs[rig.H['upperChest']].matrix.to_quaternion() @ R_uc.inverted()
        fwd = (D_c @ Vector((0.0, 1.0, 0.0))).normalized()
        sx = 1.0 if side == 'R' else -1.0
        M = pb.matrix.copy()
        h = M.translation.copy()
        Mn = Matrix.Translation(h) @ Quaternion(fwd, -sx * math.radians(delta)).to_matrix().to_4x4() @ Matrix.Translation(-h) @ M
        q = arm.convert_space(pose_bone=pb, matrix=Mn, from_space='POSE', to_space='LOCAL').decompose()[1]
        pb.rotation_quaternion = q
        bpy.context.view_layer.update()
        return q.copy()

    def bad(f, side, delta):
        set_pose(f, side, delta)
        res, gap = tester.test()
        return res[side + ' Hand'] + res[side + ' LowerArm']

    extra = {}
    for side in ('L', 'R'):
        raw = []
        for f in range(nf):
            if bad(f, side, 0.0) == 0:
                raw.append(0.0)
                continue
            lo, h_ = 0.0, hi
            for _ in range(iters):
                mid = 0.5 * (lo + h_)
                if bad(f, side, mid) == 0:
                    h_ = mid
                else:
                    lo = mid
            raw.append(h_ + margin)
        dil = [max(raw[(i + d) % nf] for d in range(-3, 4)) for i in range(nf)]
        sm = W['_periodic_smooth'](dil, 2.5)
        for _ in range(4):
            fails = [f for f in range(nf) if bad(f, side, sm[f])]
            if not fails:
                break
            for f in fails:
                for d in range(-3, 4):
                    sm[(f + d) % nf] += 1.0 if d == 0 else 0.6
        extra[side] = sm
    newq = {s: [set_pose(f, s, extra[s][f]) for f in range(nf)] for s in ('L', 'R')}
    ad.action = act
    if slot is not None and hasattr(ad, 'action_slot'):
        ad.action_slot = slot
    write_quat_keys(act, arm, [{rig.nm(s, 'UpperArm'): newq[s][f] for s in ('L', 'R')} for f in range(nf)], nf)
    return {s: (round(min(v), 1), round(max(v), 1)) for s, v in extra.items()}


# ------------------------------------------------------------------ face, loop, floor, labels
def face_b(arm):
    for ch in arm.children:
        sk = ch.data.shape_keys if ch.type == 'MESH' else None
        if sk and 'Fcl_EYE_Close' in sk.key_blocks:
            for kb in sk.key_blocks:
                if kb.name != 'Basis':
                    kb.value = FACE_B.get(kb.name, 0.0)
            return ch.name
    return None


TAIL_ROOT = 'J_Opt_C_CatTail1_01'


def turn_tail(arm, deg_, nf=NF):
    """turns the tail root about the up axis of the pelvis by deg_ (+ = towards her right) in every key (as build_walk_v2_round3.turn_tail):
    straight back the tail points at the game camera and reads as a light blob on the rump"""
    scene = bpy.context.scene
    act = arm.animation_data.action
    dp = 'pose.bones["%s"].rotation_quaternion' % TAIL_ROOT
    fcs = sorted([fc for fc in fcurves(act) if fc.data_path == dp], key=lambda fc: fc.array_index)
    pb = arm.pose.bones[TAIL_ROOT]
    hips = arm.pose.bones['J_Bip_C_Hips']
    R_h = arm.data.bones['J_Bip_C_Hips'].matrix_local.to_quaternion()
    new = {}
    for f in range(nf + 1):
        scene.frame_set(f)
        D_h = hips.matrix.to_quaternion() @ R_h.inverted()
        up = (D_h @ Vector((0.0, 0.0, 1.0))).normalized()
        M = pb.matrix.copy()
        h = M.translation.copy()
        Mn = Matrix.Translation(h) @ Quaternion(up, math.radians(deg_)).to_matrix().to_4x4() @ Matrix.Translation(-h) @ M
        new[f] = arm.convert_space(pose_bone=pb, matrix=Mn, from_space='POSE', to_space='LOCAL').decompose()[1]
    prev = None
    for f in range(nf + 1):
        q = new[f]
        if prev is not None and prev.dot(q) < 0:
            q = -q
        new[f] = q
        prev = q
    for fc in fcs:
        for k in fc.keyframe_points:
            f = int(round(k.co.x))
            if f in new:
                v = new[f][fc.array_index]
                d = v - k.co.y
                k.co.y = v
                k.handle_left.y += d
                k.handle_right.y += d
        fc.update()
    return len(new)


def make_cyclic(action):
    n = 0
    for fc in fcurves(action):
        if not any(m.type == 'CYCLES' for m in fc.modifiers):
            fc.modifiers.new('CYCLES')
            n += 1
    return n


def make_lane(name, g, x0, x1, root, cells_per_stride=8):
    """checker floor lane x0 .. x1 that scrolls backwards with G(phi) of the gait g; the checker period divides the stride, so one cycle
    moves the floor by whole periods (seamless loop)"""
    nf = g['NF']
    VT = g['SPEED'] * nf / float(FPS)
    tile = VT / cells_per_stride
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x0, -12, 0), (x1, -12, 0), (x1, 12, 0), (x0, 12, 0)], [], [(0, 1, 2, 3)])
    me.uv_layers.new()
    ob = bpy.data.objects.new(name, me)
    root.objects.link(ob)
    mat = bpy.data.materials.new(name + '_Material')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n_ for n_ in nt.nodes if n_.type == 'BSDF_PRINCIPLED')
    chk = nt.nodes.new('ShaderNodeTexChecker')
    chk.inputs['Color1'].default_value = (0.215, 0.225, 0.255, 1.0)
    chk.inputs['Color2'].default_value = (0.105, 0.112, 0.130, 1.0)
    chk.inputs['Scale'].default_value = 1.0 / tile
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.name = 'Scroll'
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], chk.inputs['Vector'])
    nt.links.new(chk.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.85
    me.materials.append(mat)
    loc = mp.inputs['Location']
    for f in range(nf + 1):
        loc.default_value = (0.0, ground(g, f / float(nf)), 0.0)
        loc.keyframe_insert('default_value', index=1, frame=f)
    for fc in fcurves(nt.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'
        m = fc.modifiers.new('CYCLES')
        m.mode_before = 'REPEAT_OFFSET'
        m.mode_after = 'REPEAT_OFFSET'
        fc.update()
    return ob


def make_label(name, text, x, root, y=0.75):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = text
    cu.size = 0.13
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new(name, cu)
    root.objects.link(ob)
    ob.location = (x, y, 0.003)
    ob.rotation_euler = (0.0, 0.0, math.pi)
    ob.hide_render = True
    mat = bpy.data.materials.new(name + '_Material')
    mat.use_nodes = True
    next(n_ for n_ in mat.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.90, 0.80, 0.40, 1.0)
    cu.materials.append(mat)
    return ob


def append_character(path, coll_obj, suffix, x):
    """appends the armature and its meshes (not the floor, not the import icosphere) from a .blend; the file itself is only read"""
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None]
    arm = next(o for o in objs if o.type == 'ARMATURE')
    kids = [o for o in objs if o.parent == arm and o.type == 'MESH' and not o.name.startswith('Icosphere')]
    coll_obj.objects.link(arm)
    for k in kids:
        coll_obj.objects.link(k)
        k.name = k.name.split('.')[0] + '_' + suffix
    for o in objs:                                   # the rest (floor, icosphere, ...) is dropped again
        if o is not arm and o not in kids and o.users == 0:
            bpy.data.objects.remove(o)
    arm.name = 'Yoru_' + suffix
    arm.location = Vector((x, 0.0, 0.0))
    return arm, kids
