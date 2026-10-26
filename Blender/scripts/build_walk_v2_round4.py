"""
Yoru - WALK v2, round 4: elegant, organic ARMS on top of Neu 0,83 (round 3).  Only the arm chains are replaced (clavicle, upper arm, forearm,
hand, fingers, thumb, both sides); every other curve of Yoru_Walk_v2_N083 (pelvis, legs, spine, head, tail, hair / bust springs) stays as it is.
Three Yorus side by side (seen from the front: R3 left, R4a middle, R4b right), one floor lane at the ground motion of Neu 0,83.
  R3   = round 3 as it was (Neu 0,83)
  R4a  = 'fliessend': bigger soft arcs, wrists and fingers trail clearly, the hands swing back to hip height
  R4b  = 'kompakt'  : smaller arcs, hands near the belly, fine wrist play, a little more posture
The arm layer (per side, phase phi of the 25-frame cycle):
  - one swing signal s(x) (+1 = arm forward) that is NOT a pure sine: the forward swing is faster than the back swing (phase warp) and the
    swing eases into the extremes (blend of cos and its smoothstep); left and right differ by a few per cent in reach and phase
  - overlapping action: clavicle leads, upper arm 0, elbow +lag_e, forearm roll +lag_p, wrist +lag_w, fingers +lag_f (+ per finger / phalanx)
  - arcs: the upper arm turns in (internal rotation) as it swings forward and out as it swings back, so the forearm swings on an ellipse,
    the arm also comes a little in at the front and goes out at the back; the elbow bends more in front, opens downward behind
  - forearm: hinge roll + pronation / supination (limited to TWIST_MAX), wrist: flex / extension and ulnar / radial trail behind the forearm
  - clavicle: lifts / drops and moves forward / back with the swing (on top of the counter-rotation of the shoulders)
  - afterwards the exact gear test (fix_arms of build_walk_v2_round3.py): where hand or forearm would cut the gear, the arm turns out by the
    least angle that clears it (smoothed over the loop)
Background:  blender -b --factory-startup --python build_walk_v2_round4.py -- <out .blend>
"""
import bpy, os, sys, math, json
from mathutils import Vector, Quaternion, Euler, Matrix

SCRIPTS = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
R3_FILE = r'C:\Users\valen\ZeroProtocol\Blender\work\Walk_v2\Yoru_Walk_v2_round3.blend'
NF = 25
FPS = 30
TAU = 2.0 * math.pi
KEYS = ('R3', 'R4a', 'R4b')
X_POS = {'R3': 1.2, 'R4a': 0.0, 'R4b': -1.2}
LABEL = {'R3': 'R3 (Runde 3)', 'R4a': 'R4a fliessend', 'R4b': 'R4b kompakt'}
ROOT = 'Walk_v2_R4'
TWIST_MAX = 18.0
FINGERS = ('Index', 'Middle', 'Ring', 'Little')
PARTS = ('Proximal', 'Intermediate', 'Distal')

STYLE = {
    # upper arm swing (deg, + forward), elbow (deg), arcs, roll, wrist, fingers, clavicle; lags in fractions of the cycle (1 frame = 0.04)
    # (first try: R4a elbow up to 66, R4b a0 6 / fwd 12 / elbow 46..70 -> the forearm came up to almost horizontal in front, like rowing;
    #  second try: forearms leaning out (carry +2 / +4) -> the hands stayed 6 to 9 cm in front of the body, floating;
    #  third try: the hand bend was an extra 'trail' term, the hand reached its extreme only 2 to 3 frames after the upper arm (R3: 4):
    #  now the hand points where the forearm pointed lag_w earlier ('ribbon'), the elbow and the turn of the arm trail as well;
    #  fourth try: forearms turned in (carry -4 / -6, tw0 6) -> the gear pushed them out again at the back swing, the hand went 15 to 22 cm
    #  sideways in every cycle (rowing): now the arm hangs a little wider (ab0 15 / 14) and the in-turn and arc are halved)
    'R4a': dict(a0=3.0, a_fwd=14.0, a_back=15.0, warp=0.15, ease=0.5,
                ab0=15.0, ab_arc=1.5, tw0=4.0, tw_u=6.0, carry=0.0,
                el_min=28.0, el_max=58.0, lag_e=0.12,
                pron0=12.0, pron=13.0, lag_p=0.15,
                wf0=10.0, wf=22.0, wd0=5.0, wd=9.0, lag_w=0.20, ribbon=1.25, k_flex=1.0, k_cross=0.7,
                cu0={'Index': (10, 16, 10), 'Middle': (14, 22, 14), 'Ring': (18, 26, 16), 'Little': (22, 30, 18)}, cu=10.0, lag_f=0.30,
                th=(6.0, 6.0, 4.0), th_dyn=4.0,
                clav_drop0=4.0, clav_back0=1.0, clav_prot=3.5, clav_elev=2.5, lag_c=-0.03,
                asym_amp=0.94, asym_ph=0.025, asym_el=-3.0),
    'R4b': dict(a0=2.0, a_fwd=8.0, a_back=4.0, warp=0.12, ease=0.6,
                ab0=14.0, ab_arc=1.0, tw0=4.0, tw_u=4.0, carry=-2.0,
                el_min=44.0, el_max=60.0, lag_e=0.08,
                pron0=12.0, pron=8.0, lag_p=0.10,
                wf0=12.0, wf=12.0, wd0=5.0, wd=6.0, lag_w=0.14, ribbon=0.85, k_flex=0.8, k_cross=0.5,
                cu0={'Index': (12, 18, 12), 'Middle': (16, 24, 16), 'Ring': (20, 28, 18), 'Little': (24, 32, 20)}, cu=6.0, lag_f=0.22,
                th=(6.0, 8.0, 5.0), th_dyn=3.0,
                clav_drop0=3.0, clav_back0=2.0, clav_prot=2.5, clav_elev=1.5, lag_c=-0.03,
                asym_amp=0.94, asym_ph=0.025, asym_el=-3.0),
}


def log(*a):
    print('[walk_v2 round4]', *a, flush=True)


def _load(name):
    ns = {'__file__': os.path.join(SCRIPTS, name)}
    exec(compile(open(ns['__file__'], encoding='utf-8').read(), ns['__file__'], 'exec'), ns)
    return ns


R3 = _load('build_walk_v2_round3.py')
R3['ROOT'] = ROOT
R3['X_POS'] = X_POS
R3['LABEL'] = LABEL
R3['GAIT'] = {k: dict(V=1.35, NF=NF, amp=0.05) for k in KEYS}


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


def swing(x, st):
    """+1 forward extreme at x = 0, -1 back extreme; the forward swing (back -> front) is faster than the back swing; eases at the extremes"""
    th = TAU * (x % 1.0)
    c = math.cos(th - st['warp'] * (1.0 - math.cos(th)))
    return (1.0 - st['ease']) * c + st['ease'] * 0.5 * (3.0 * c - c ** 3)


# ------------------------------------------------------------------ append the round 3 clip Neu 0,83
def append_n083(key):
    wanted = ['Yoru_R3_N083', 'Body_R3_N083', 'Face_R3_N083', 'Hair_R3_N083']
    with bpy.data.libraries.load(R3_FILE, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in wanted]
    objs = [o for o in dst.objects if o is not None]
    arm = next(o for o in objs if o.type == 'ARMATURE')
    col = R3['coll'](ROOT + '_' + key, R3['coll'](ROOT))
    col.objects.link(arm)
    for o in objs:
        if o is not arm:
            col.objects.link(o)
            o.name = o.name.split('_R3_')[0] + '_R4_' + key
    arm.name = 'Yoru_R4_' + key
    arm.location = Vector((X_POS[key], 0.0, 0.0))
    act = arm.animation_data.action
    if key != 'R3':
        act = act.copy()
        act.name = 'Yoru_Walk_v2_N083_' + key
        act.use_fake_user = True
        arm.animation_data.action = act
    return arm


# ------------------------------------------------------------------ the arm layer
class ArmLayer:
    def __init__(self, arm, key):
        L = _load('build_idle_v2_lib.py')
        self.arm = arm
        self.st = STYLE[key]
        self.H = L['humanoid_map']()
        self.bones = arm.data.bones
        self.R = {b.name: b.matrix_local.to_quaternion() for b in self.bones}
        self.HEAD0 = {b.name: b.head_local.copy() for b in self.bones}

    def nm(self, side, part):
        return self.H[('left' if side == 'L' else 'right') + part]

    def side_params(self, side):
        st = dict(self.st)
        if side == 'L':                                 # not mirrored: a little less reach, a little later, a little less bend
            for k in ('a_fwd', 'a_back', 'tw_u', 'pron', 'wf', 'wd', 'cu', 'clav_prot', 'clav_elev'):
                st[k] = st[k] * st['asym_amp']
            st['el_max'] = st['el_max'] + st['asym_el']
        return st

    def chain(self, side, phi, pbs):
        """basis rotations (Q) of clavicle, upper arm, forearm, hand, fingers, thumb for this side at cycle phase phi"""
        st = self.side_params(side)
        sx = 1.0 if side == 'R' else -1.0
        R, HEAD0, nm = self.R, self.HEAD0, self.nm
        x0 = phi - (0.5 if side == 'R' else 0.0) - (st['asym_ph'] if side == 'L' else 0.0)   # forward extreme of this arm at x0 = 0
        s_c = swing(x0 - st['lag_c'], st)
        s_u = swing(x0, st)
        s_e = swing(x0 - st['lag_e'], st)
        s_p = swing(x0 - st['lag_p'], st)
        trail = s_u - swing(x0 - st['lag_w'], st)                       # > 0 while the arm swings forward: the hand trails behind
        trail2 = s_u - swing(x0 - st['lag_w'] - 0.05, st)
        # clavicle (relative to the upper chest): forward and up with the forward swing
        n_uc, n_cl = self.H['upperChest'], nm(side, 'Shoulder')
        uc = pbs[n_uc]
        D_uc = uc.matrix.to_quaternion() @ R[n_uc].inverted()
        drop = st['clav_drop0'] - st['clav_elev'] * s_c
        back = st['clav_back0'] - st['clav_prot'] * s_c
        rel_c = eul(ry=sx * drop, rz=-sx * back)
        D_cl = D_uc @ rel_c
        P_cl = pbs[n_cl].head.copy()
        n_u, n_f, n_h = nm(side, 'UpperArm'), nm(side, 'LowerArm'), nm(side, 'Hand')
        S = P_cl + D_cl @ (HEAD0[n_u] - HEAD0[n_cl])
        # arm in the frame of the chest heading
        fwd = D_uc @ Vector((0.0, 1.0, 0.0))
        Fy = Quaternion((0.0, 0.0, 1.0), math.atan2(-fwd.x, fwd.y))

        def dirs(x):
            """upper arm, flex direction, forearm in the heading frame for arm phase x (the elbow and the turn of the arm trail the swing)"""
            su = swing(x, st)
            se = swing(x - st['lag_e'], st)
            sr = swing(x - 0.5 * st['lag_e'], st)
            alpha = math.radians(st['a0'] + 0.5 * (st['a_fwd'] + st['a_back']) * su + 0.5 * (st['a_fwd'] - st['a_back']))
            ab = math.radians(st['ab0'] - st['ab_arc'] * sr)
            du_ = Quaternion((1.0, 0.0, 0.0), alpha) @ Quaternion((0.0, 1.0, 0.0), -sx * ab) @ Vector((0.0, 0.0, -1.0))
            fl0 = perp(Vector((0.0, 1.0, 0.0)), du_)
            fl_ = Quaternion(du_, -sx * math.radians(st['tw0'] + st['tw_u'] * sr)) @ fl0     # internal rotation in front, external behind
            beta = math.radians(st['el_min'] + (st['el_max'] - st['el_min']) * 0.5 * (se + 1.0))
            df_ = du_ * math.cos(beta) + fl_ * math.sin(beta)
            df_ = Quaternion(fl_, -sx * math.radians(st['carry'])) @ df_
            return du_, fl_, df_.normalized(), alpha

        du_l, fl_l, df_l, alpha = dirs(x0)
        # the hand follows like a ribbon: it points where the forearm pointed lag_w earlier (scaled by ribbon: > 1 a little more, < 1 less)
        df_lag = dirs(x0 - st['lag_w'])[2]
        q_r = df_l.rotation_difference(df_lag)
        dh_l = (Quaternion(q_r.axis, q_r.angle * st['ribbon']) @ df_l).normalized() if q_r.angle > 1e-6 else df_l.copy()
        du, df, fl = Fy @ du_l, (Fy @ df_l).normalized(), Fy @ fl_l
        beta = du.angle(df)
        rest = Vector((sx, 0.0, 0.0))
        Du = aim(rest, Vector((0, 1, 0)), du, fl)
        flex = du.angle(df)
        hinge = Du @ Vector((0.0, 0.0, sx))
        sgn = 1.0 if hinge.dot(du.cross(df)) >= 0 else -1.0
        Df0 = Quaternion(hinge, sgn * flex) @ Du
        n0 = perp(Df0 @ Vector((0.0, 0.0, -1.0)), df)
        tw = max(-TWIST_MAX, min(TWIST_MAX, st['pron0'] + st['pron'] * s_p))      # pronation (+) turns the palm towards the back
        nf = Quaternion(df, -sx * math.radians(tw)) @ n0
        Df = aim(rest, Vector((0, 0, -1)), df, nf)
        # hand: the ribbon trail split into wrist flex (towards the palm) and deviation (towards the little finger), each within natural
        # limits (with the palm facing in, a swing trail falls mostly into the deviation: unlimited it bent the wrist sideways by 38 deg)
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
        # fingers: loosely curled, a little more closed in front, more open behind, each finger / phalanx a little later
        for fi, fn in enumerate(FINGERS):
            for pj, part in enumerate(PARTS):
                s_f = swing(x0 - st['lag_f'] - 0.02 * fi - 0.015 * pj, st)
                c = st['cu0'][fn][pj] + st['cu'] * s_f * (1.0 if pj == 0 else 0.7)
                n = nm(side, fn + part)
                rel = Quaternion((0, 1, 0), math.radians(sx * c))
                Q[n] = R[n].inverted() @ rel @ R[n]
        s_t = swing(x0 - st['lag_f'] - 0.04, st)
        t1, t2, t3 = st['th']
        for part, rel in (('ThumbProximal', eul(rx=-(t1 + st['th_dyn'] * s_t))), ('ThumbIntermediate', eul(rz=-sx * (t2 + 0.5 * st['th_dyn'] * s_t))),
                          ('ThumbDistal', eul(rz=-sx * t3))):
            n = nm(side, part)
            Q[n] = R[n].inverted() @ rel @ R[n]
        diag = dict(elbow=math.degrees(flex), twist=tw, wrist=math.degrees(df.angle(dh)), wf=math.degrees(wf), wd=math.degrees(wd),
                    swing_u=math.degrees(alpha), wrist_pos=None)
        return Q, diag


def apply_arm_layer(arm, key):
    scene = bpy.context.scene
    layer = ArmLayer(arm, key)
    ad = arm.animation_data
    act = ad.action
    slot = getattr(ad, 'action_slot', None)
    pbs = arm.pose.bones
    names = [pb.name for pb in pbs]
    poses = []
    for f in range(NF):
        scene.frame_set(f)
        poses.append({n: (pbs[n].location.copy(), pbs[n].rotation_quaternion.copy(), pbs[n].scale.copy()) for n in names})
    ad.action = None
    newQ = []
    diags = []
    for f in range(NF):
        for n, (lo, ro, sc) in poses[f].items():
            pbs[n].location, pbs[n].rotation_quaternion, pbs[n].scale = lo, ro, sc
        bpy.context.view_layer.update()
        qf, df_ = {}, {}
        for side in ('L', 'R'):
            q, dg = layer.chain(side, f / float(NF), pbs)
            qf.update(q)
            df_[side] = dg
        newQ.append(qf)
        diags.append(df_)
    ad.action = act
    if slot is not None and hasattr(ad, 'action_slot'):
        ad.action_slot = slot
    fcs = R3['fcurves'](act)
    by = {}
    for fc in fcs:
        by.setdefault(fc.data_path, {})[fc.array_index] = fc
    changed = 0
    for n in newQ[0].keys():
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        if dp not in by:
            pb = pbs[n]
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = newQ[0][n]
            pb.keyframe_insert('rotation_quaternion', frame=0)
            by = {}
            for fc in R3['fcurves'](act):
                by.setdefault(fc.data_path, {})[fc.array_index] = fc
        seq, prev = [], None
        for f in range(NF):
            q = newQ[f][n]
            if prev is not None and prev.dot(q) < 0:
                q = -q
            seq.append(q)
            prev = q
        seq.append(seq[0] if seq[0].dot(seq[-1]) >= 0 else -seq[0])
        for i in range(4):
            fc = by[dp][i]
            kp = fc.keyframe_points
            if len(kp) < NF + 1:
                kp.add(NF + 1 - len(kp))
            co = []
            for f in range(NF + 1):
                co.extend((float(f), float(seq[f][i])))
            kp.foreach_set('co', co)
            for k in kp:
                k.interpolation = 'LINEAR'
            fc.update()
            if not any(m.type == 'CYCLES' for m in fc.modifiers):
                fc.modifiers.new('CYCLES')
        changed += 1
    return changed, diags


def build():
    info = {}
    arms = {}
    for key in KEYS:
        arms[key] = append_n083(key)
    for key in ('R4a', 'R4b'):
        n, diags = apply_arm_layer(arms[key], key)
        el = [d[s]['elbow'] for d in diags for s in 'LR']
        wr = [d[s]['wrist'] for d in diags for s in 'LR']
        tw = [d[s]['twist'] for d in diags for s in 'LR']
        info[key] = dict(bones=n, elbow=(round(min(el), 1), round(max(el), 1)), wrist_bend=(round(min(wr), 1), round(max(wr), 1)),
                         forearm_roll=(round(min(tw), 1), round(max(tw), 1)))
        info[key]['arm_extra_deg'] = R3['fix_arms'](arms[key], nf=NF)
    R3['make_lane']('R4a', -9.0, 9.0, 1.35 * NF / float(FPS) / 4.0).name = 'Boden_R4'
    for key in KEYS:
        R3['make_label'](key)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 0, NF - 1
    scene.frame_set(0)
    return info


def main():
    out = sys.argv[sys.argv.index('--') + 1:][0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info = build()
    log(json.dumps(info))
    bpy.ops.wm.save_as_mainfile(filepath=out)
    log('saved', out)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
