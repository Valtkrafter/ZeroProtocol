"""
Yoru - AIM SUITE STAGE 1, round 1 (2026-10-31): the aim-idle loop Yoru_Aim_Idle = the approved Idle_v2 loop (12 s, 361 frames at 30 fps, frame
360 = frame 0) with the approved aim pose V2 (Blender/Yoru_Aim.blend) on top.  Spec: Blender/work/Aim/suite_spec_from_gemini.md, Stage 1.
  blender -b --factory-startup <Blender/Yoru_Aim.blend> --python build_aim_s1.py -- <out .blend> [idle=<Blender/Yoru_Idle_v2.blend>] [solver=<out .json>]
          [follow=line|none] [head=lock|idle]
  round 1 = follow=line head=idle (Blender/work/Aim/Yoru_Aim_s1_r1.blend); round 2 (default) = follow=line head=lock
HEAD  head=lock (round 2, the user: "the head stays locked on the crosshair"): J_Bip_C_Head gets, in every frame, the local rotation that keeps
      its WORLD rotation at the one of frame 0 (= pose V2) in all three axes: q_head(f) = R^-1 @ D_neck(f)^-1 @ D_head(V2) @ R, with D_neck(f)
      from the copied idle keys; periodic (frame 360 = frame 0).  The neck and every other body bone stay as above; eyes, ears and hair keep their
      idle keys (they ride on the locked head).  head=idle (round 1): Head = q_idle(f) @ off_head (the constant -9 deg).
  e.g. ... Blender/Yoru_Aim.blend --python Blender/scripts/build_aim_s1.py -- Blender/work/Aim/Yoru_Aim_s1.blend solver=Blender/work/Aim/Yoru_Aim_s1_solver.json
BODY  every keyed bone of the idle action Yoru_Idle_v2 except the arms (hips rotation and location, legs, feet, toes, tail, spine, chest, upper chest,
      shoulders, neck, head, ears, eyes, hair, bust) is copied key for key (361 linear keys with the cycles modifier, as in the idle).  The only
      change: the two constant local offsets of pose V2, UpperChest q_idle(f) @ off_uc (+8 deg local yaw) and Head q_idle(f) @ off_head (-9 deg);
      both are read from the pose (off = q_idle(0)^-1 @ q_pose), so frame 0 is the pose.  Face: Yoru_Aim_Idle_Face = a copy of Yoru_Idle_v2_Face
      (expression B, two blinks).
ARMS  target-locked: each hand keeps, in every frame, the world ROTATION it has in pose V2 (so cant and barrel direction cannot change; the pistols
      are parented to the hands) and its wrist joint stays on the V2 wrist, except (follow=line, the default) a slide along its own arm line
      (shoulder -> wrist of V2) by the shoulder joint's motion along that line.  Why: the idle's shoulder joints move up to 13 mm up, 12 mm back and
      7 mm sideways; with the wrist fixed in all three axes (follow=none, try 1 = Yoru_Aim_s1_try1_handsfixed.blend) the shoulder-wrist distance
      grows by up to 11.5 mm while the V2 arm (elbow 13.5 deg) has only 2.9 mm left: the elbows lock straight (3.6 deg) and the wrists are pulled
      back up to 9 mm anyway.  The slide along the arm line moves the muzzle only 0.05 mm up per mm (the arm drops 2 cm over 42 cm) and keeps the
      elbow at 12.9..13.5 deg.  Two-bone IK from the shoulder joint that breathes with the idle, pole as in V2 (elbow straight below the
      shoulder-wrist line, swivel 0); the upper arm and forearm without roll against the elbow hinge, the forearm then takes 0.6 of the roll the
      hand needs (<= 18 deg) and the wrist the rest (<= 12 deg), as in round 5.  Baked as FK keys (local rotations only, no IK constraint).
      Fingers: the V2 grip, constant.
LAYERS Yoru_Aim_Idle = everything (for pictures, checks and a later export); Yoru_Aim_Idle_Layer = the bones of Yoru_Aim_Pose_V2 (spine and up incl.
      arms, fingers, eyes, ears, hair, bust; no hips keys); Yoru_Aim_Idle_Stand = the bones of Yoru_Aim_Pose_V2_Stand (hips rotation and location,
      legs, feet, toes, tail).  The pose actions and the NLA track 'Stand' of the clean file stay untouched.
Blender: +Y forward (the aim line), her left = -X, up = +Z.  Prints and writes (solver=) the per-frame solver numbers.
"""
import bpy, sys, os, math, json, time
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = os.path.abspath(argv[0])
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
IDLE = KV.get('idle', r'C:\Users\valen\ZeroProtocol\Blender\Yoru_Idle_v2.blend')
SOLVER = KV.get('solver')
FOLLOW = KV.get('follow', 'line')
HEAD_MODE = KV.get('head', 'lock')
NF, FPS = 360, 30
T0 = time.time()


def log(*a):
    print('[aim_s1 %5.1fs]' % (time.time() - T0), *a, flush=True)


scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
face = bpy.data.objects.get('Face')
bones = arm.data.bones
R = {b.name: b.matrix_local.to_quaternion() for b in bones}
HEAD0 = {b.name: b.head_local.copy() for b in bones}
PARENT = {b.name: (b.parent.name if b.parent else None) for b in bones}
ORDER = []
_q = [b for b in bones if b.parent is None]
while _q:
    _b = _q.pop(0)
    ORDER.append(_b.name)
    _q.extend(_b.children)
FING = ('Thumb', 'Index', 'Middle', 'Ring', 'Little')
ARM3 = {s: ['J_Bip_%s_%s' % (s, p) for p in ('UpperArm', 'LowerArm', 'Hand')] for s in 'LR'}
FINGERS = {s: ['J_Bip_%s_%s%d' % (s, f, k) for f in FING for k in (1, 2, 3) if 'J_Bip_%s_%s%d' % (s, f, k) in bones] for s in 'LR'}
ARM_BONES = set(ARM3['L'] + ARM3['R'] + FINGERS['L'] + FINGERS['R'])
UC, HEAD = 'J_Bip_C_UpperChest', 'J_Bip_C_Head'
HIPS = 'J_Bip_C_Hips'


def fcurves_of(act):
    out = []
    for l in act.layers:
        for s in l.strips:
            for cb in s.channelbags:
                out += list(cb.fcurves)
    return out


def channelbags_of(act):
    return [cb for l in act.layers for s in l.strips for cb in s.channelbags]


def bone_of(dp):
    return dp.split('"')[1] if dp.startswith('pose.bones["') else None


def deg(x):
    return math.radians(x)


def qang(a, b):
    x = a.rotation_difference(b).angle
    return math.degrees(min(x, 2.0 * math.pi - x))


# ------------------------------------------------------------------ the idle (actions + its rest pose for a check)
with bpy.data.libraries.load(IDLE, link=False) as (src, dst):
    dst.actions = ['Yoru_Idle_v2', 'Yoru_Idle_v2_Face']
    dst.armatures = list(src.armatures)
IDLE_ACT, IDLE_FACE = dst.actions
rest_dev = 0.0
for ad_ in dst.armatures:
    for b in ad_.bones:
        if b.name in bones:
            rest_dev = max(rest_dev, (b.matrix_local.translation - bones[b.name].matrix_local.translation).length * 1000.0,
                           qang(b.matrix_local.to_quaternion(), R[b.name]) * 1000.0)        # mm, or millidegrees
    bpy.data.armatures.remove(ad_)
log('idle rest pose vs this rig: max %.6f (mm or millideg)' % rest_dev)

FC_IDLE = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(IDLE_ACT)}
IDLE_BONES = sorted({bone_of(dp) for dp, _ in FC_IDLE if bone_of(dp)})
for (dp, i), fc in FC_IDLE.items():
    assert len(fc.keyframe_points) == NF + 1 and all(abs(fc.keyframe_points[f].co[0] - f) < 1e-6 for f in (0, 1, NF)), (dp, i)


def idle_q(n, f):
    dp = 'pose.bones["%s"].rotation_quaternion' % n
    return Quaternion([FC_IDLE[(dp, i)].keyframe_points[f].co[1] for i in range(4)])


def idle_loc(n, f):
    dp = 'pose.bones["%s"].location' % n
    if (dp, 0) not in FC_IDLE:
        return None
    return Vector([FC_IDLE[(dp, i)].keyframe_points[f].co[1] for i in range(3)])


# ------------------------------------------------------------------ pose V2 (frame 0 of the full pose action)
POSE_FULL = bpy.data.actions['Yoru_Aim_Pose_V2_full']
FC_POSE = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(POSE_FULL)}
Q_V2 = {}
for n in {bone_of(dp) for dp, _ in FC_POSE if bone_of(dp)}:
    dp = 'pose.bones["%s"].rotation_quaternion' % n
    if (dp, 0) in FC_POSE:
        Q_V2[n] = Quaternion([FC_POSE[(dp, i)].evaluate(0.0) for i in range(4)])
LOC_V2 = Vector([FC_POSE[('pose.bones["%s"].location' % HIPS, i)].evaluate(0.0) for i in range(3)])
LAYER_BONES = sorted({bone_of(fc.data_path) for fc in fcurves_of(bpy.data.actions['Yoru_Aim_Pose_V2']) if bone_of(fc.data_path)})
STAND_BONES = sorted({bone_of(fc.data_path) for fc in fcurves_of(bpy.data.actions['Yoru_Aim_Pose_V2_Stand']) if bone_of(fc.data_path)})
assert set(LAYER_BONES) | set(STAND_BONES) == set(IDLE_BONES) == set(Q_V2), 'bone sets differ'
assert not (set(LAYER_BONES) & set(STAND_BONES))
assert ARM_BONES <= set(IDLE_BONES)

OFF = {}
for n in (UC, HEAD):
    o = idle_q(n, 0).normalized().inverted() @ Q_V2[n].normalized()
    if o.w < 0:
        o = -o
    ax, an = o.to_axis_angle()
    OFF[n] = o
    log('offset %s: %.4f deg about local axis (%.5f %.5f %.5f), local yaw %.4f deg' % (n, math.degrees(an), ax.x, ax.y, ax.z,
                                                                                    math.degrees(2.0 * math.atan2(o.y, o.w))))
body_dev0 = max((qang(idle_q(n, 0), Q_V2[n]), n) for n in IDLE_BONES if n not in ARM_BONES and n not in OFF)
hips_dev0 = (idle_loc(HIPS, 0) - LOC_V2).length * 1000.0
log('pose V2 vs idle frame 0 (non-arm bones without UC/Head): max %.6f deg (%s), hips location %.6f mm' % (body_dev0[0], body_dev0[1], hips_dev0))


# ------------------------------------------------------------------ FK (as compute_pose of build_aim_r5.py, with a parent-aware hips location)
def fk(qget, locget, names=ORDER):
    D, P = {}, {}
    for n in names:
        p = PARENT[n]
        Dp = D[p] if p else Quaternion()
        P[n] = HEAD0[n].copy() if p is None else P[p] + D[p] @ (HEAD0[n] - HEAD0[p])
        loc = locget(n)
        if loc is not None:
            P[n] = P[n] + Dp @ (R[n] @ loc)
        D[n] = Dp @ (R[n] @ qget(n) @ R[n].inverted())
    return D, P


def frame_q(f):
    def g(n):
        if n in OFF:
            return idle_q(n, f) @ OFF[n]
        if ('pose.bones["%s"].rotation_quaternion' % n, 0) in FC_IDLE:
            return idle_q(n, f)
        return Quaternion()
    return g


def frame_loc(f):
    return lambda n: idle_loc(n, f) if n == HIPS else None


def chain(n):
    c = []
    while n is not None:
        c.append(n)
        n = PARENT[n]
    return c[::-1]


CHAIN = [n for n in ORDER if n in set(chain(ARM3['L'][0]) + chain(ARM3['R'][0]) + chain(HEAD))]     # root .. shoulders .. upper arms, .. neck .. head

# FK check against Blender's own evaluation of the pose
ad = arm.animation_data
ad.action = POSE_FULL
if hasattr(ad, 'action_slot') and len(POSE_FULL.slots):
    ad.action_slot = POSE_FULL.slots[0]
scene.frame_set(1)
scene.frame_set(0)
D_V2, P_V2 = fk(lambda n: Q_V2.get(n, Quaternion()), lambda n: LOC_V2 if n == HIPS else None)
fk_err = max((arm.matrix_world @ arm.pose.bones[n].head - P_V2[n]).length for n in ORDER) * 1000.0
fk_rot = max(qang((arm.pose.bones[n].matrix.to_quaternion() @ R[n].inverted()), D_V2[n]) for n in ORDER)
log('python FK vs Blender, pose V2 frame 0: %.6f mm, %.6f deg' % (fk_err, fk_rot))

# ------------------------------------------------------------------ the arm solver (round 5 geometry)
L1 = {s: (HEAD0[ARM3[s][1]] - HEAD0[ARM3[s][0]]).length for s in 'LR'}
L2 = {s: (HEAD0[ARM3[s][2]] - HEAD0[ARM3[s][1]]).length for s in 'LR'}
REST_UA = {s: (HEAD0[ARM3[s][1]] - HEAD0[ARM3[s][0]]).normalized() for s in 'LR'}
REST_FA = {s: (HEAD0[ARM3[s][2]] - HEAD0[ARM3[s][1]]).normalized() for s in 'LR'}
REST_N = Vector((0.0, 0.0, -1.0))
PHI = {'L': 0.0, 'R': 0.0}                                            # the V2 fit: elbow straight below the shoulder-wrist line
SX = {'L': -1.0, 'R': 1.0}
W0 = {s: P_V2[ARM3[s][2]].copy() for s in 'LR'}                       # wrist joint of V2 (world, fixed)
DH = {s: D_V2[ARM3[s][2]].copy() for s in 'LR'}                       # hand rotation of V2 (world delta, fixed)


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed().to_quaternion()


def aim(rest_dir, rest_nrm, tgt_dir, tgt_nrm):
    return frame_rot(tgt_dir, tgt_nrm) @ frame_rot(rest_dir, rest_nrm).inverted()


def elbow_ik(S, W, phi, sx, L1_, L2_):
    v = W - S
    d = v.length
    d_c = min(max(d, abs(L1_ - L2_) + 1e-4), (L1_ + L2_) * 0.9995)
    u = v.normalized()
    a = (L1_ * L1_ - L2_ * L2_ + d_c * d_c) / (2.0 * d_c)
    h = math.sqrt(max(L1_ * L1_ - a * a, 0.0))
    down = Vector((0.0, 0.0, -1.0))
    p0 = (down - u * down.dot(u)).normalized()
    out = Vector((sx, 0.0, 0.0))
    o0 = (out - u * out.dot(u) - p0 * out.dot(p0)).normalized()
    p = (p0 * math.cos(deg(phi)) + o0 * math.sin(deg(phi))).normalized()
    return S + u * a + p * h, S + u * d_c, d - d_c


def signed_about(q, axis):
    """angle (deg) of the rotation q about axis (q is a rotation about +-axis)"""
    ax, an = q.to_axis_angle()
    a = math.degrees(an) * (1.0 if ax.dot(axis) >= 0 else -1.0)
    return (a + 180.0) % 360.0 - 180.0


def solve_arm(s, S, Dp, W):
    sx = SX[s]
    K, Weff, defi = elbow_ik(S, W, PHI[s], sx, L1[s], L2[s])
    ua, fo = (K - S).normalized(), (Weff - K).normalized()
    ax = ua.cross(fo)
    ax = ax.normalized() if ax.length > 1e-9 else Vector((1.0, 0.0, 0.0))
    n = ax * (-sx)
    Du = aim(REST_UA[s], REST_N, ua, n)
    Df0 = aim(REST_FA[s], REST_N, fo, n)
    hdir = (DH[s] @ REST_FA[s]).normalized()
    Dh0 = fo.rotation_difference(hdir) @ Df0
    rel = DH[s] @ Dh0.inverted()
    tw = signed_about(rel, hdir)
    tw_e = max(-18.0, min(18.0, 0.6 * tw))
    tw_w = tw - tw_e
    Df = Quaternion(fo, deg(tw_e)) @ Df0
    up, lo, ha = ARM3[s]
    q_ua = R[up].inverted() @ Dp.inverted() @ Du @ R[up]
    q_fa = R[lo].inverted() @ Du.inverted() @ Df @ R[lo]
    q_h = R[ha].inverted() @ Df.inverted() @ DH[s] @ R[ha]
    info = dict(S=list(S), K=list(K), W=list(Weff), deficit_mm=defi * 1000.0, dist_mm=(W - S).length * 1000.0,
                wrist_slide_mm=(W - W0[s]).dot(U0[s]) * 1000.0, wrist_move_mm=(Weff - W0[s]).length * 1000.0,
                flex=math.degrees(ua.angle(fo)), tw_total=tw, tw_e=tw_e, tw_w=tw_w, wrist_bend=math.degrees(fo.angle(hdir)),
                rel_axis_err_deg=(math.degrees(min(rel.to_axis_angle()[0].angle(hdir), rel.to_axis_angle()[0].angle(-hdir)))
                                  if abs(tw) > 1e-3 else 0.0))
    return (q_ua, q_fa, q_h), info


# ------------------------------------------------------------------ solve every frame
SOL = {n: [] for n in ARM_BONES}
INFO = {'L': [], 'R': []}
S0 = {s: P_V2[ARM3[s][0]].copy() for s in 'LR'}                       # shoulder joints of V2 = frame 0
U0 = {s: (W0[s] - S0[s]).normalized() for s in 'LR'}                  # the arm line of V2 (shoulder -> wrist)
NECK = PARENT[HEAD]
HEAD_SEQ = []                                                          # head=lock: local rotation that keeps the V2 world rotation
for f in range(NF + 1):
    D, P = fk(frame_q(f), frame_loc(f), CHAIN)
    HEAD_SEQ.append(R[HEAD].inverted() @ D[NECK].inverted() @ D_V2[HEAD] @ R[HEAD])
    for s in 'LR':
        up = ARM3[s][0]
        W = W0[s].copy()
        if FOLLOW == 'line':
            W = W + U0[s] * (P[up] - S0[s]).dot(U0[s])
        qs, info = solve_arm(s, P[up], D[PARENT[up]], W)
        for n, q in zip(ARM3[s], qs):
            SOL[n].append(q)
        for n in FINGERS[s]:
            SOL[n].append(Q_V2[n].copy())
        INFO[s].append(info)
for n, seq in SOL.items():                                             # sign continuity (linear keys), frame 0 on the pose's sign
    if seq[0].dot(Q_V2[n]) < 0:
        seq[0] = -seq[0]
    for f in range(1, NF + 1):
        if seq[f].dot(seq[f - 1]) < 0:
            seq[f] = -seq[f]
if HEAD_SEQ[0].dot(Q_V2[HEAD]) < 0:
    HEAD_SEQ[0] = -HEAD_SEQ[0]
for f in range(1, NF + 1):
    if HEAD_SEQ[f].dot(HEAD_SEQ[f - 1]) < 0:
        HEAD_SEQ[f] = -HEAD_SEQ[f]
HEAD_IDLE = [idle_q(HEAD, f) @ OFF[HEAD] for f in range(NF + 1)]      # round 1
head0 = qang(HEAD_SEQ[0], Q_V2[HEAD])
head_seam = qang(HEAD_SEQ[0], HEAD_SEQ[NF])
head_step = max(qang(HEAD_SEQ[f], HEAD_SEQ[f + 1]) for f in range(NF))
head_vs_r1 = max(qang(HEAD_SEQ[f], HEAD_IDLE[f]) for f in range(NF + 1))
_g = []
for f in range(NF + 1):                                              # world rotation of the locked head against V2 (python FK)
    D, P = fk(lambda n, f=f: HEAD_SEQ[f] if n == HEAD else frame_q(f)(n), frame_loc(f), CHAIN)
    _g.append(qang(D[HEAD], D_V2[HEAD]))
log('head=%s: locked head vs V2 at frame 0 %.6f deg, seam %.6f deg, largest step %.4f deg/frame, local difference to round 1 up to %.3f deg, '
    'world rotation vs V2 (FK) up to %.6f deg' % (HEAD_MODE, head0, head_seam, head_step, head_vs_r1, max(_g)))
arm0 = max((qang(SOL[n][0], Q_V2[n]), n) for n in ARM_BONES)
seam_arm = max(qang(SOL[n][0], SOL[n][NF]) for n in ARM_BONES)
sign_seam = min(SOL[n][0].dot(SOL[n][NF]) for n in ARM_BONES)
log('arms at frame 0 vs pose V2: max %.6f deg (%s); arm seam 360 vs 0: %.6f deg (sign dot min %.6f)' % (arm0[0], arm0[1], seam_arm, sign_seam))
for s in 'LR':
    I = INFO[s]
    fl = [i['flex'] for i in I]
    log('%s: flexion %.2f..%.2f deg (frame 0 %.2f), reach deficit max %.3f mm, shoulder-wrist %.2f..%.2f mm, roll total %.2f..%.2f, forearm %.2f..%.2f, '
        'wrist %.2f..%.2f, wrist bend %.2f..%.2f, roll-axis err %.4f deg' % (
            s, min(fl), max(fl), fl[0], max(i['deficit_mm'] for i in I), min(i['dist_mm'] for i in I), max(i['dist_mm'] for i in I),
            min(i['tw_total'] for i in I), max(i['tw_total'] for i in I), min(i['tw_e'] for i in I), max(i['tw_e'] for i in I),
            min(i['tw_w'] for i in I), max(i['tw_w'] for i in I), min(i['wrist_bend'] for i in I), max(i['wrist_bend'] for i in I),
            max(i['rel_axis_err_deg'] for i in I)))
    log('%s (follow=%s): wrist slide along the arm line %.2f..%.2f mm, wrist moved max %.2f mm, wrist height change %.3f..%.3f mm' % (
        s, FOLLOW, min(i['wrist_slide_mm'] for i in I), max(i['wrist_slide_mm'] for i in I), max(i['wrist_move_mm'] for i in I),
        1000 * min(i['W'][2] - W0[s].z for i in I), 1000 * max(i['W'][2] - W0[s].z for i in I)))
    sz = [i['S'][2] for i in I]
    sy = [i['S'][1] for i in I]
    sxs = [i['S'][0] for i in I]
    log('%s shoulder joint: z %.2f mm p2p, y %.2f mm p2p, x %.2f mm p2p' % (s, 1000 * (max(sz) - min(sz)), 1000 * (max(sy) - min(sy)),
                                                                          1000 * (max(sxs) - min(sxs))))

# ------------------------------------------------------------------ the actions
act = IDLE_ACT.copy()
act.name = 'Yoru_Aim_Idle'
act.use_fake_user = True
FC = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(act)}


def write(n, seq):
    dp = 'pose.bones["%s"].rotation_quaternion' % n
    for i in range(4):
        cos = []
        for f in range(NF + 1):
            cos.extend((float(f), float(seq[f][i])))
        FC[(dp, i)].keyframe_points.foreach_set('co', cos)
        FC[(dp, i)].update()


for n, o in OFF.items():
    seq = [idle_q(n, f) @ o for f in range(NF + 1)]
    if n == HEAD and HEAD_MODE == 'lock':
        seq = HEAD_SEQ
    write(n, seq)
for n, seq in SOL.items():
    write(n, seq)
try:
    act.slots[0].name_display = arm.name
except Exception as e:
    log('slot rename:', e)


def subset(name, keep):
    a = act.copy()
    a.name = name
    a.use_fake_user = True
    for cb in channelbags_of(a):
        for fc in list(cb.fcurves):
            if bone_of(fc.data_path) not in keep:
                cb.fcurves.remove(fc)
        for g in list(cb.groups):
            if not len(g.channels):
                cb.groups.remove(g)
    return a


ACT_LAYER = subset('Yoru_Aim_Idle_Layer', set(LAYER_BONES))
ACT_STAND = subset('Yoru_Aim_Idle_Stand', set(STAND_BONES))
fact = IDLE_FACE.copy()
fact.name = 'Yoru_Aim_Idle_Face'
fact.use_fake_user = True
sk = face.data.shape_keys
if sk.animation_data is None:
    sk.animation_data_create()
sk.animation_data.action = fact
if hasattr(sk.animation_data, 'action_slot') and len(fact.slots):
    sk.animation_data.action_slot = fact.slots[0]
try:
    fact.slots[0].name_display = sk.name
except Exception as e:
    log('face slot rename:', e)
bpy.data.actions.remove(IDLE_ACT)
bpy.data.actions.remove(IDLE_FACE)
ad.action = act
if hasattr(ad, 'action_slot') and len(act.slots):
    ad.action_slot = act.slots[0]
scene.render.fps, scene.render.fps_base = FPS, 1.0
scene.frame_start, scene.frame_end = 0, NF - 1                      # the loop plays 0..359 (360 = 0), as in Yoru_Idle_v2.blend
scene.frame_set(1)
scene.frame_set(0)
log('actions', sorted(a.name for a in bpy.data.actions), '| layer bones %d, stand bones %d, fcurves %d / %d / %d' % (
    len(LAYER_BONES), len(STAND_BONES), len(fcurves_of(act)), len(fcurves_of(ACT_LAYER)), len(fcurves_of(ACT_STAND))))

if SOLVER:
    json.dump(dict(date='2026-10-31', stage=1, round=2 if HEAD_MODE == 'lock' else 1, follow=FOLLOW, head=HEAD_MODE, head_step_max_deg=head_step,
                   head_seam_deg=head_seam, head_local_vs_round1_max_deg=head_vs_r1, head_world_vs_V2_max_deg=max(_g) if HEAD_MODE == 'lock' else None,
                   idle=IDLE, out=OUT, rest_dev=rest_dev, offsets_deg={n: math.degrees(2.0 * math.atan2(o.y, o.w)) for n, o in OFF.items()},
                   pose_vs_idle0_max_deg=body_dev0[0], pose_hips_vs_idle0_mm=hips_dev0, fk_vs_blender_mm=fk_err, fk_vs_blender_deg=fk_rot,
                   arms_frame0_vs_pose_deg=arm0[0], arm_seam_deg=seam_arm, L1=L1, L2=L2, W0={s: list(W0[s]) for s in 'LR'},
                   layer_bones=LAYER_BONES, stand_bones=STAND_BONES, per_frame=INFO), open(SOLVER, 'w'), indent=0)
    log('wrote', SOLVER)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=OUT)
log('saved', OUT)
log('DONE')
