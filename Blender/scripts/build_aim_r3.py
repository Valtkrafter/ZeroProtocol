"""
Yoru - AIM POSE, ROUND 3, STAGE 1 ONLY (2026-10-30): lower body contrapposto, spine torsion, head and tail after the spec the user pasted
(Blender/work/Aim/round3_spec_from_gemini.md: verbatim text + the main agent's decisions).  Arms hang loosely (placeholder), no pistols.
  stance (both): ankles 0.31 m apart sideways, LEFT foot 0.22 m ahead of the right, right toes out 20 deg (left foot straight ahead, 0 deg: the spec
          gives no number), 62 % of the weight over the back (right) leg = the pelvis 0.12 x (spacing, stagger) from the middle between the ankles
          towards the right foot (3.7 cm right, 2.6 cm back); pelvis yaw 20 deg LEFT (counter-clockwise seen from above), anterior tilt 6 deg,
          roll 5.5 deg (right hip up)
  S-a: knees left 14 / right 18 deg, the pelvis drop follows (the ankle spacing may move inside 0.30..0.32 m so that both knees hold)
  S-b: pelvis 45 mm lower, the knees follow
  trunk: spine 3.0 + chest 2.5 + upper chest 2.0 = 7.5 deg forward (local, against the rest pose); chest and upper chest 12.5 + 12.5 deg further
         LEFT (net chest about 45 deg left of the aim line, the right shoulder leads); the neck takes 45 % of the turn back, the head the rest: the
         face looks at the aim point (15 m ahead on the crosshair line), head pitch 4.5 deg down (chin tucked), roll 3 deg towards the right
         shoulder (world); the eyes look at the aim point; ears 9 deg back; face expression B (shape keys of the idle)
  tail: swan-neck S (base 18 deg up, the middle sweeps back and down, the tip curls 35 deg inward = up), swept a little to her left so that the
        game camera (behind her, on the right) sees a curve and not the end of the tail
Layer split: action Yoru_Aim_r3_Torso    = Spine, Chest, UpperChest, Neck, Head, eyes, ears (local rotations; no hips keys)
             actions Yoru_Aim_r3_Stand_Sa / _Sb = Hips (rotation + location), legs, feet, toes, tail; NLA track 'Stand' = Stand_Sa
             actions Yoru_Aim_r3_full_Sa / _Sb  = Torso + Stand + the hanging placeholder arms and relaxed fingers (measure and render these)
Run:  blender -b --factory-startup --python build_aim_r3.py -- <Yoru_V2.glb> <out dir> [design=1]
Writes <out dir>/Yoru_Aim_r3.blend, Yoru_Aim_r3_stage1_numbers.json, Yoru_Aim_r3_stage1_table.json and Yoru_Aim_r3_stage1_table.md.
Blender: +Y forward (the aim line), her left = -X, up = +Z.
"""
import bpy, sys, os, math, json, struct, time
from mathutils import Vector, Quaternion, Euler, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_point_line
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = argv[0], argv[1]
KV = dict(a.split('=', 1) for a in argv[2:] if '=' in a)
DESIGN = KV.get('design') == '1'
os.makedirs(OUT, exist_ok=True)
T0 = time.time()


def log(*a):
    print('[aim_r3 %5.1fs]' % (time.time() - T0), *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Body']
face = bpy.data.objects.get('Face')
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Icosphere'):
        o.hide_render = True
        o.hide_viewport = True
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 0, 1
with open(GLB, 'rb') as f:
    f.read(12)
    clen, _ = struct.unpack('<II', f.read(8))
    js = json.loads(f.read(clen).decode('utf-8'))
H = {h['bone']: js['nodes'][h['node']]['name'] for h in js['extensions']['VRM']['humanoid']['humanBones']}
bones = arm.data.bones
R = {b.name: b.matrix_local.to_quaternion() for b in bones}
HEAD0 = {b.name: b.head_local.copy() for b in bones}
order = []
queue = [b for b in bones if b.parent is None]
while queue:
    b = queue.pop(0)
    order.append(b.name)
    queue.extend(b.children)
TAIL = ['J_Opt_C_CatTail%d_01' % i for i in range(1, 9)]
EARS = [n for n in ('J_Opt_L_CatEar1_01', 'J_Opt_R_CatEar1_01') if n in bones]
FING = ('Index', 'Middle', 'Ring', 'Little')
PARTS = ('Proximal', 'Intermediate', 'Distal')


def nm(side, part):
    return H[('left' if side == 'L' else 'right') + part]


def hk(side, part):
    return ('left' if side == 'L' else 'right') + part


EYES = [H[k] for k in ('leftEye', 'rightEye') if k in H]
TORSO = [H[k] for k in ('spine', 'chest', 'upperChest', 'neck', 'head')] + EYES + EARS
STAND = [H['hips']] + [nm(s, p) for s in ('L', 'R') for p in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes') if hk(s, p) in H] + TAIL
ARMS_SET = []
for _s in ('L', 'R'):
    ARMS_SET += [nm(_s, p) for p in ('Shoulder', 'UpperArm', 'LowerArm', 'Hand')]
    ARMS_SET += [nm(_s, f_ + p_) for f_ in FING + ('Thumb',) for p_ in PARTS if hk(_s, f_ + p_) in H]


def deg(x):
    return math.radians(x)


def eul(rx=0.0, ry=0.0, rz=0.0):
    return Euler((deg(rx), deg(ry), deg(rz)), 'XYZ').to_quaternion()


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed().to_quaternion()


def aim(rest_dir, rest_nrm, tgt_dir, tgt_nrm):
    return frame_rot(tgt_dir, tgt_nrm) @ frame_rot(rest_dir, rest_nrm).inverted()


def two_bone_ik(Hp, T, pole, L1, L2):
    v = T - Hp
    d = v.length
    d_c = min(max(d, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.9995)
    u = v.normalized()
    a = (L1 * L1 - L2 * L2 + d_c * d_c) / (2.0 * d_c)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    p = pole - u * pole.dot(u)
    p.normalize()
    return Hp + u * a + p * h, Hp + u * d_c, d - d_c


def ypr(q):
    """world yaw (+ = turned left), forward tilt (+ = front down) and roll (+ = right side up) of a rotation, decomposed as Rz(yaw) Rx(pitch) Ry(roll)"""
    e = q.to_euler('YXZ')
    return math.degrees(e.z), -math.degrees(e.x), -math.degrees(e.y)


# ------------------------------------------------------------------ the spec (stage 1)
AIM_POINT = Vector((0.35, 15.0, 1.30))                               # 15 m ahead on the crosshair line of the game camera (as rounds 1 and 2)
PELVIS = dict(yaw_left=20.0, tilt_fwd=6.0, roll_right_up=5.5, weight_back=0.62)
STANCE = dict(spacing=0.31, stagger=0.22, front='L', toe_L=0.0, toe_R=20.0)
SETUPS = {'Sa': dict(mode='knees', knee_L=14.0, knee_R=18.0), 'Sb': dict(mode='drop', drop=0.045)}
TRUNK = dict(lean=(3.0, 2.5, 2.0), yaw=(0.0, 12.5, 12.5), neck_share=0.45, head_pitch_down=4.5, head_roll_right=3.0)
EARS_BACK = 9.0
# swan-neck tail: WORLD direction of every segment (pitch above the horizontal, yaw from straight back towards her LEFT, deg)
TAIL_DIRS = [(18.0, 10.0), (8.0, 12.0), (-8.0, 14.0), (-22.0, 16.0), (-30.0, 18.0), (-20.0, 20.0), (-20.0, 20.0), (15.0, 24.0)]
# placeholder arms: the wrist hangs beside the hip, given against the hip joint in the frame of the turned PELVIS (out, forward, up); hanging
# straight down from the shoulders (chest turned 45 deg, pelvis 20 deg) the hands went through hips and pouches (63..262 cutting triangle pairs)
ARM_AT_HIP = {'R': (0.12, 0.03, -0.02), 'L': (0.12, 0.03, -0.02)}    # (round-3 try 2, still cutting: replaced by the hinge chain below)
ARM_SWING, ARM_ELBOW = 6.0, 18.0                                     # placeholder arm: upper arm 6 deg forward of hanging, elbow 18 deg bent
RELAX = {'Index': (25.0, 35.0, 20.0), 'Middle': (32.0, 45.0, 26.0), 'Ring': (38.0, 52.0, 30.0), 'Little': (44.0, 58.0, 34.0)}
THUMB_RELAX = (12.0, 14.0, 10.0, 8.0)
CLEAR = 0.003
LEG_L1 = (HEAD0[nm('L', 'LowerLeg')] - HEAD0[nm('L', 'UpperLeg')]).length
LEG_L2 = (HEAD0[nm('L', 'Foot')] - HEAD0[nm('L', 'LowerLeg')]).length
L_UA = {s: (HEAD0[nm(s, 'LowerArm')] - HEAD0[nm(s, 'UpperArm')]).length for s in ('L', 'R')}
L_FA = {s: (HEAD0[nm(s, 'Hand')] - HEAD0[nm(s, 'LowerArm')]).length for s in ('L', 'R')}
REST_UA = {s: (HEAD0[nm(s, 'LowerArm')] - HEAD0[nm(s, 'UpperArm')]).normalized() for s in ('L', 'R')}
REST_FA = {s: (HEAD0[nm(s, 'Hand')] - HEAD0[nm(s, 'LowerArm')]).normalized() for s in ('L', 'R')}
REST_N = Vector((0.0, 0.0, -1.0))


def pelvis_q():
    return eul(rz=PELVIS['yaw_left']) @ eul(rx=-PELVIS['tilt_fwd']) @ eul(ry=-PELVIS['roll_right_up'])


def tail_dir(pitch, yaw):
    cp = math.cos(deg(pitch))
    return Vector((-math.sin(deg(yaw)) * cp, -math.cos(deg(yaw)) * cp, math.sin(deg(pitch))))


def feet_for(spacing):
    """ankle targets (flat feet) around the resting pelvis: the pelvis sits (w - 0.5) x (right - left) away from the middle between the ankles"""
    hip0 = HEAD0[H['hips']]
    w = PELVIS['weight_back'] - 0.5
    mid = Vector((hip0.x - w * spacing, hip0.y + w * STANCE['stagger'], 0.0))
    z = HEAD0[nm('L', 'Foot')].z
    return {'L': Vector((mid.x - 0.5 * spacing, mid.y + 0.5 * STANCE['stagger'], z)),
            'R': Vector((mid.x + 0.5 * spacing, mid.y - 0.5 * STANCE['stagger'], z))}, mid


def hip_joints(drop):
    q = pelvis_q()
    hh = HEAD0[H['hips']] + Vector((0.0, 0.0, -drop))
    return {s: hh + q @ (HEAD0[nm(s, 'UpperLeg')] - HEAD0[H['hips']]) for s in ('L', 'R')}


def knee_of(dist):
    c = (dist * dist - LEG_L1 ** 2 - LEG_L2 ** 2) / (2.0 * LEG_L1 * LEG_L2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def knees(drop, spacing):
    ank, _ = feet_for(spacing)
    hj = hip_joints(drop)
    return {s: knee_of((ank[s] - hj[s]).length) for s in ('L', 'R')}


def solve_setup(su):
    """S-b: the given drop; S-a: for every spacing in 0.30..0.32 the drop that gives the right knee its angle, keep the spacing whose left knee
    comes closest to its angle"""
    if su['mode'] == 'drop':
        return su['drop'], STANCE['spacing'], knees(su['drop'], STANCE['spacing'])
    if su['mode'] == 'kneeL':                                        # only for the question: the left knee exact, spacing 0.31, the right follows
        lo, hi = -0.02, 0.12
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if knees(mid, STANCE['spacing'])['L'] < su['knee_L']:
                lo = mid
            else:
                hi = mid
        dr = 0.5 * (lo + hi)
        return dr, STANCE['spacing'], knees(dr, STANCE['spacing'])
    best = None
    for sp in [0.30 + 0.001 * i for i in range(21)]:
        lo, hi = -0.02, 0.12
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if knees(mid, sp)['R'] < su['knee_R']:
                lo = mid
            else:
                hi = mid
        dr = 0.5 * (lo + hi)
        k = knees(dr, sp)
        err = abs(k['L'] - su['knee_L'])
        if best is None or err < best[0]:
            best = (err, dr, sp, k)
    return best[1], best[2], best[3]


def elbow_ik(S, W, phi, sx, L1, L2):
    v = W - S
    d = v.length
    d_c = min(max(d, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.9995)
    u = v.normalized()
    a = (L1 * L1 - L2 * L2 + d_c * d_c) / (2.0 * d_c)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    back = Vector((0.0, -1.0, 0.0))
    p0 = (back - u * back.dot(u)).normalized()                      # hanging arm: 0 = elbow straight back
    out = Vector((sx, 0.0, 0.0))
    o0 = (out - u * out.dot(u) - p0 * out.dot(p0)).normalized()
    p = (p0 * math.cos(deg(phi)) + o0 * math.sin(deg(phi))).normalized()
    return S + u * a + p * h, S + u * d_c, d - d_c


def compute_pose(sk, phi):
    drop, spacing, _k = solve_setup(SETUPS[sk])
    ank, mid = feet_for(spacing)
    fyaw = {'L': STANCE['toe_L'], 'R': -STANCE['toe_R']}              # + rz turns the left toes out, - rz the right toes out
    rel, absd = {}, {}
    for k, key in enumerate(('spine', 'chest', 'upperChest')):
        rel[H[key]] = eul(rx=-TRUNK['lean'][k], rz=TRUNK['yaw'][k])
    for n in EARS:
        rel[n] = eul(rx=-EARS_BACK)                                   # ears: + about X tips them forward (build_idle_v2_face.py), so 9 deg back = -9
    for side, sx in (('L', -1.0), ('R', 1.0)):
        for fn, curls in RELAX.items():
            for part, c in zip(PARTS, curls):
                rel[nm(side, fn + part)] = Quaternion((0, 1, 0), deg(sx * c))
        rel[nm(side, 'ThumbProximal')] = eul(rz=-sx * THUMB_RELAX[0]) @ Quaternion((0, 1, 0), deg(sx * THUMB_RELAX[1]))
        rel[nm(side, 'ThumbIntermediate')] = Quaternion((0, 1, 0), deg(sx * THUMB_RELAX[2]))
        rel[nm(side, 'ThumbDistal')] = Quaternion((0, 1, 0), deg(sx * THUMB_RELAX[3]))
    head0 = HEAD0[H['head']]
    yaw_aim = math.degrees(math.atan2(AIM_POINT.x - head0.x, AIM_POINT.y - head0.y))   # + = the target lies to her right
    d_head = eul(rz=-yaw_aim) @ eul(rx=-TRUNK['head_pitch_down']) @ eul(ry=TRUNK['head_roll_right'])
    hips_d = Vector((0.0, 0.0, -drop))
    D, P, Q, ik, armc = {}, {}, {}, {}, {}
    info = {'drop': drop, 'spacing': spacing, 'ankles': ank, 'feet_mid': mid, 'foot_yaw': fyaw, 'phi': dict(phi), 'yaw_aim': yaw_aim}
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        P[name] = HEAD0[name].copy() if parent is None else P[parent] + D[parent] @ (HEAD0[name] - HEAD0[parent])
        if name == H['hips']:
            P[name] = P[name] + hips_d
            D[name] = pelvis_q()
        elif name == H['neck']:
            D[name] = D[H['upperChest']].slerp(d_head, TRUNK['neck_share'])
        elif name == H['head']:
            D[name] = d_head
        elif name in EYES:                                            # the eyes look at the aim point
            fwd = (d_head @ Vector((0.0, 1.0, 0.0))).normalized()
            D[name] = fwd.rotation_difference((AIM_POINT - P[name]).normalized()) @ d_head
        elif name in rel:
            D[name] = Dp @ rel[name]
        else:
            D[name] = Dp.copy()
        if name in TAIL:
            i = TAIL.index(name)
            D[name] = (Dp @ Vector((0.0, -1.0, 0.0))).rotation_difference(tail_dir(*TAIL_DIRS[i])) @ Dp
        for side, sx in (('L', -1.0), ('R', 1.0)):
            if name == nm(side, 'UpperLeg'):
                Hp = P[name]
                K0, A0 = HEAD0[nm(side, 'LowerLeg')], HEAD0[nm(side, 'Foot')]
                pole = Vector((-math.sin(deg(fyaw[side])), math.cos(deg(fyaw[side])), 0.0))
                K, Teff, defi = two_bone_ik(Hp, ank[side], pole, LEG_L1, LEG_L2)
                ik[side] = (K, Teff, defi)
                D[name] = (K0 - HEAD0[name]).rotation_difference(K - Hp)
            elif name == nm(side, 'LowerLeg'):
                K, Teff, _ = ik[side]
                D[name] = (HEAD0[nm(side, 'Foot')] - HEAD0[name]).rotation_difference(Teff - K)
            elif name == nm(side, 'Foot'):
                D[name] = eul(rz=fyaw[side])
            elif name == nm(side, 'UpperArm'):
                # placeholder arm as the sprint's hinge chain (build_sprint_r1.arm_chain): the upper arm hangs in the frame of the turned chest,
                # abducted by phi (fitted against the gear), swung ARM_SWING forward; the elbow bends ARM_ELBOW about the chest's lateral axis
                S = P[name]
                cz = eul(rz=ypr(D[H['upperChest']])[0])
                v = Quaternion((1.0, 0.0, 0.0), deg(ARM_SWING)) @ (Quaternion((0.0, 1.0, 0.0), deg(-sx * phi[side])) @ Vector((0.0, 0.0, -1.0)))
                ua = (cz @ v).normalized()
                a0 = cz @ Vector((1.0, 0.0, 0.0))
                a0 = (a0 - ua * a0.dot(ua)).normalized()
                fo = (Quaternion(a0, deg(ARM_ELBOW)) @ ua).normalized()
                K = S + ua * L_UA[side]
                Weff = K + fo * L_FA[side]
                defi = 0.0
                n = a0 * (-sx)
                Du = aim(REST_UA[side], REST_N, ua, n)
                Df = aim(REST_FA[side], REST_N, fo, n)
                armc[side] = (Du, Df, Df)                             # the hand continues the forearm (relaxed, no wrist bend)
                info['arm_' + side] = dict(S=S, K=K, W=Weff, deficit=defi)
                D[name] = Du
            elif name == nm(side, 'LowerArm'):
                D[name] = armc[side][1]
            elif name == nm(side, 'Hand'):
                D[name] = armc[side][2]
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    info['legs'] = ik
    return Q, R[H['hips']].inverted() @ hips_d, D, P, info


KEYED = TORSO + STAND + ARMS_SET


def set_pose(sk, phi):
    ad = arm.animation_data
    if ad and ad.action:
        ad.action = None
    Q, hl, D, P, info = compute_pose(sk, phi)
    for n in KEYED:
        pb = arm.pose.bones[n]
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Q[n]
    arm.pose.bones[H['hips']].location = hl
    bpy.context.view_layer.update()
    return Q, hl, D, P, info


def numbers_of(D, P, info):
    """the stance block in the definitions of aim_measure.py plus the stage-1 checks"""
    hip, neck, head = P[H['hips']], P[H['neck']], P[H['head']]
    fl, fr_ = P[nm('L', 'Foot')], P[nm('R', 'Foot')]
    mid = (fl + fr_) * 0.5
    sh = (P[nm('L', 'UpperArm')] + P[nm('R', 'UpperArm')]) * 0.5
    hn = neck - hip
    out = dict(knee_L=None, knee_R=None, feet_spacing_x=round(abs(fl.x - fr_.x), 3), feet_stagger_y=round(abs(fl.y - fr_.y), 3),
               pelvis_drop_cm=round(100.0 * info['drop'], 2), hips_vs_feet_y_cm=round(100.0 * (hip.y - mid.y), 1),
               hips_vs_feet_x_cm=round(100.0 * (hip.x - mid.x), 1), shoulders_vs_feet_y_cm=round(100.0 * (sh.y - mid.y), 1),
               head_vs_feet_y_cm=round(100.0 * (head.y - mid.y), 1), hips_height_m=round(hip.z, 3),
               lean_hips_neck=round(math.degrees(math.atan2(hn.y, hn.z)), 1),
               lean_hips_neck_3d=round(math.degrees(math.atan2(math.hypot(hn.x, hn.y), hn.z)), 1))
    for side in ('L', 'R'):
        K, T, defi = info['legs'][side]
        hp = P[nm(side, 'UpperLeg')]
        out['knee_' + side] = round(180.0 - math.degrees((hp - K).angle(T - K)), 1)
        out['leg_reach_deficit_mm_' + side] = round(1000.0 * defi, 2)
        axis = (T - hp).normalized()                                  # knee direction: the bend offset from the hip-ankle line, seen from above
        off = (K - hp) - axis * (K - hp).dot(axis)
        fdir = D[nm(side, 'Foot')] @ Vector((0.0, 1.0, 0.0))
        out['knee_vs_foot_deg_' + side] = round(math.degrees(math.atan2(off.x * fdir.y - off.y * fdir.x, off.x * fdir.x + off.y * fdir.y)) if off.length > 1e-6 else 0.0, 1)
        fy, fp, fr = ypr(D[nm(side, 'Foot')])
        out['foot_' + side] = dict(yaw_left=round(fy, 1), tilt=round(fp, 2), roll=round(fr, 2), ankle=[round(x, 3) for x in T])
    for nm_, b in (('hips', H['hips']), ('chest', H['upperChest']), ('head', H['head'])):
        y_, p_, r_ = ypr(D[b])
        out['world_' + nm_] = dict(yaw_left=round(y_, 1), tilt_fwd=round(p_, 1), roll_right_up=round(r_, 1))
    gz = (D[H['head']] @ Vector((0.0, 1.0, 0.0))).normalized()
    out['head_gaze'] = dict(yaw_right=round(math.degrees(math.atan2(gz.x, gz.y)), 1), pitch_up=round(math.degrees(math.asin(gz.z)), 1),
                            aim_point_yaw_right=round(info['yaw_aim'], 2))
    if EYES:
        ez = (D[EYES[0]] @ Vector((0.0, 1.0, 0.0))).normalized()
        to_aim = (AIM_POINT - P[EYES[0]]).normalized()
        out['eye_vs_aim_point_deg'] = round(math.degrees(ez.angle(to_aim)), 2)
    out['chest_net_yaw_left'] = out['world_chest']['yaw_left']
    out['shoulder_line_yaw'] = round(math.degrees(math.atan2((P[nm('R', 'UpperArm')] - P[nm('L', 'UpperArm')]).y,
                                                             (P[nm('R', 'UpperArm')] - P[nm('L', 'UpperArm')]).x)), 1)
    return out


if DESIGN:
    for sk in SETUPS:
        Q, hl, D, P, info = compute_pose(sk, {'L': 20.0, 'R': 20.0})
        log('DESIGN', sk, 'drop %.4f spacing %.3f' % (info['drop'], info['spacing']), json.dumps(numbers_of(D, P, info)))
    sys.exit(0)

# ------------------------------------------------------------------ mesh sets and the exact clearance (as build_aim_r2.py, no pistols)
def invisible_polygons():
    me = body.data
    imgs = {}
    for mi, m in enumerate(me.materials):
        if m is None or not m.use_nodes:
            continue
        for n_ in m.node_tree.nodes:
            if n_.type == 'TEX_IMAGE' and n_.image:
                w_, h_ = n_.image.size
                imgs[mi] = (np.array(n_.image.pixels[:], dtype=np.float32).reshape(h_, w_, 4)[:, :, 3], w_, h_)
                break
    uv = me.uv_layers.active.data
    out = set()
    for poly in me.polygons:
        im = imgs.get(poly.material_index)
        if im is None:
            continue
        px, w_, h_ = im
        a_ = sum(px[int(min(max(uv[li].uv[1], 0.0), 0.9999) * h_), int(min(max(uv[li].uv[0], 0.0), 0.9999) * w_)] for li in poly.loop_indices)
        if a_ / len(poly.loop_indices) < 0.3:
            out.add(poly.index)
    return out


vg_names = {vg.index: vg.name for vg in body.vertex_groups}
INV = invisible_polygons()
VIS = [False] * len(body.data.vertices)
for poly in body.data.polygons:
    if poly.index not in INV:
        for vi in poly.vertices:
            VIS[vi] = True
dom_of = [vg_names.get(max(v.groups, key=lambda g: g.weight).group, '') if v.groups else '' for v in body.data.vertices]
_solid = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg'], H['leftLowerLeg'], H['rightLowerLeg']}
gear_v = set(i for i, n_ in enumerate(dom_of) if VIS[i] and (n_ in _solid or (n_.startswith('J_Sec_') and 'Hair' not in n_)))
GEAR_POLYS = [list(p.vertices) for p in body.data.polygons if p.index not in INV and all(v_ in gear_v for v_ in p.vertices)]
ARM_PARTS = {}
for side in ('L', 'R'):
    hand_set = {nm(side, 'Hand')} | {nm(side, f_ + p_) for f_ in FING + ('Thumb',) for p_ in PARTS if hk(side, f_ + p_) in H}
    for part, bset in (('UpperArm', {nm(side, 'UpperArm')}), ('LowerArm', {nm(side, 'LowerArm')}), ('Hand', hand_set)):
        polys = [list(p.vertices) for p in body.data.polygons if p.index not in INV and all(dom_of[v_] in bset and VIS[v_] for v_ in p.vertices)]
        ARM_PARTS[(side, part)] = (polys, sorted({v_ for pl in polys for v_ in pl}))
tail_v = set(i for i, n_ in enumerate(dom_of) if VIS[i] and n_ in TAIL[2:])
TAIL_POLYS = [list(p.vertices) for p in body.data.polygons if p.index not in INV and all(v_ in tail_v for v_ in p.vertices)]
NOT_TAIL = [list(p.vertices) for p in body.data.polygons if p.index not in INV
            and all(VIS[v_] and dom_of[v_] not in TAIL and (dom_of[v_] in _solid or dom_of[v_] in {H['leftFoot'], H['rightFoot']}
                                                             or (dom_of[v_].startswith('J_Sec_') and 'Hair' not in dom_of[v_])) for v_ in p.vertices)]
FOOT_VERTS = {s: [i for i, n_ in enumerate(dom_of) if n_ in (nm(s, 'Foot'), nm(s, 'Toes'))] for s in ('L', 'R')}
NV = len(body.data.vertices)


def body_coords():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    arr = np.empty(NV * 3, dtype=np.float64)
    me.vertices.foreach_get('co', arr)
    ev.to_mesh_clear()
    arr = arr.reshape(NV, 3)
    mw = body.matrix_world
    if mw != Matrix.Identity(4):
        arr = arr @ np.array(mw.to_3x3()).T + np.array(mw.translation)
    return [Vector(c) for c in arr]


def arm_clearance(co):
    gear = BVHTree.FromPolygons(co, GEAR_POLYS, all_triangles=False)
    pbs = arm.pose.bones
    res = {}
    for side in ('L', 'R'):
        sh = arm.matrix_world @ pbs[nm(side, 'UpperArm')].head
        el = arm.matrix_world @ pbs[nm(side, 'LowerArm')].head
        r = {'cut': 0, 'min': 9.0, 'up_min': 9.0}
        for part in ('UpperArm', 'LowerArm', 'Hand'):
            polys, vids = ARM_PARTS[(side, part)]
            if part == 'UpperArm':
                polys = [pl for pl in polys if intersect_point_line(co[pl[0]], sh, el)[1] > 0.8]
                vids = sorted({v_ for pl in polys for v_ in pl})
            if not polys:
                continue
            r['cut'] += len(BVHTree.FromPolygons(co, polys, all_triangles=False).overlap(gear))
            for v_ in vids:
                hit = gear.find_nearest(co[v_])
                if hit[0] is not None:
                    key = 'up_min' if part == 'UpperArm' else 'min'
                    r[key] = min(r[key], hit[3])
        res[side] = r
    return res


def tail_numbers(co):
    bt = BVHTree.FromPolygons(co, NOT_TAIL, all_triangles=False)
    tt = BVHTree.FromPolygons(co, TAIL_POLYS, all_triangles=False)
    ids = sorted({v_ for pl in TAIL_POLYS for v_ in pl})
    dist = [bt.find_nearest(co[i])[3] for i in ids]
    j = min(range(len(ids)), key=lambda k: dist[k])
    return dict(tail_cut=len(tt.overlap(bt)), tail_min_mm=round(1000.0 * dist[j], 1), tail_min_at=[round(x, 3) for x in co[ids[j]]],
                tail_back_most_y=round(min(co[i].y for i in ids), 3), tail_lowest_z=round(min(co[i].z for i in ids), 3),
                tail_highest_z=round(max(co[i].z for i in ids), 3), tail_x_range=[round(min(co[i].x for i in ids), 3), round(max(co[i].x for i in ids), 3)])


def foot_flat(co, info):
    out = {}
    for s in ('L', 'R'):
        ids = FOOT_VERTS[s]
        ank = arm.matrix_world @ arm.pose.bones[nm(s, 'Foot')].head
        fy = deg(info['foot_yaw'][s])
        fdir = Vector((-math.sin(fy), math.cos(fy), 0.0))
        heel = [co[i].z for i in ids if (co[i] - ank).dot(fdir) < -0.02]
        toe = [co[i].z for i in ids if (co[i] - ank).dot(fdir) > 0.10]
        out[s] = dict(sole_min_z_heel_mm=round(1000.0 * min(heel), 1) if heel else None, sole_min_z_toe_mm=round(1000.0 * min(toe), 1) if toe else None)
    return out


# ------------------------------------------------------------------ fit the elbow of the hanging arms (clear of the gear by CLEAR)
poses = {}
for sk in SETUPS:
    phi = {'L': 10.0, 'R': 10.0}                                     # here phi = abduction of the placeholder upper arm (deg)
    for it in range(30):
        set_pose(sk, phi)
        c = arm_clearance(body_coords())
        bad = [s for s in ('L', 'R') if (c[s]['cut'] > 0 or c[s]['min'] < CLEAR or c[s]['up_min'] < CLEAR) and phi[s] < 40.0]
        if not bad:
            break
        for s in bad:
            phi[s] = min(40.0, phi[s] + 2.0)
    poses[sk] = phi
    log('setup %s: arm swivel L %.0f R %.0f; clearance %s' % (sk, phi['L'], phi['R'], {s: {k: round(v, 4) for k, v in c[s].items()} for s in c}))


# ------------------------------------------------------------------ keys: Torso (layer), Stand_Sa / _Sb, full_Sa / _Sb, NLA track 'Stand'
def key_action(Qd, hips_loc, names, act_name, with_hips_loc):
    ad = arm.animation_data_create()
    ad.action = None
    for f in (0, 1):
        for n in names:
            pb = arm.pose.bones[n]
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = Qd[n]
            pb.keyframe_insert('rotation_quaternion', frame=f)
        if with_hips_loc:
            pbh = arm.pose.bones[H['hips']]
            pbh.location = hips_loc
            pbh.keyframe_insert('location', frame=f)
    act = ad.action
    act.name = act_name
    act.use_fake_user = True
    ad.action = None
    return act


for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = Quaternion()
    pb.location = Vector()
acts = {}
for sk in SETUPS:
    Q, hl, D, P, info = compute_pose(sk, poses[sk])
    if 'Torso' not in acts:
        acts['Torso'] = key_action(Q, hl, TORSO, 'Yoru_Aim_r3_Torso', False)
    acts['Stand_' + sk] = key_action(Q, hl, STAND, 'Yoru_Aim_r3_Stand_' + sk, True)
    acts['full_' + sk] = key_action(Q, hl, KEYED, 'Yoru_Aim_r3_full_' + sk, True)
ad = arm.animation_data
trk = ad.nla_tracks.new()
trk.name = 'Stand'
strip = trk.strips.new(acts['Stand_Sa'].name, 0, acts['Stand_Sa'])
if hasattr(strip, 'action_slot') and strip.action_slot is None and len(acts['Stand_Sa'].slots):
    strip.action_slot = acts['Stand_Sa'].slots[0]
strip.extrapolation = 'HOLD'


def use_action(act):
    ad_ = arm.animation_data
    ad_.action = act
    if hasattr(ad_, 'action_slot') and ad_.action_slot is None and len(act.slots):
        ad_.action_slot = act.slots[0]
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
    scene.frame_set(1)
    scene.frame_set(0)
    bpy.context.view_layer.update()


FACE_B = {'Fcl_EYE_Angry': 0.40, 'Fcl_EYE_Fun': 0.16, 'Fcl_MTH_Neutral': 0.55, 'Fcl_MTH_Close': 0.20, 'Fcl_BRW_Angry': 0.50}
if face is not None and face.data.shape_keys:
    for kb in face.data.shape_keys.key_blocks:
        if kb.name != 'Basis':
            kb.value = FACE_B.get(kb.name, 0.0)

# ------------------------------------------------------------------ numbers and the bone table, through the saved full actions
TABLE_BONES = ([H['hips'], H['spine'], H['chest'], H['upperChest'], H['neck'], H['head']]
               + [nm(s, p) for s in ('L', 'R') for p in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')] + TAIL)
numbers = {'date': '2026-10-30', 'round': 3, 'stage': 1, 'spec': 'Blender/work/Aim/round3_spec_from_gemini.md', 'aim_point': list(AIM_POINT),
           'pelvis': PELVIS, 'stance': STANCE, 'setups': SETUPS, 'trunk': TRUNK, 'ears_back_deg': EARS_BACK, 'tail_dirs_world': TAIL_DIRS,
           'actions': {k: a.name for k, a in acts.items()}, 'layer_bones': TORSO, 'stand_bones': STAND, 'results': {}}
table = {'conventions': {
    'pose_local_euler_xyz_deg': 'the pose bone rotation against its rest pose in the BONE\'S OWN axes, Euler XYZ (what Blender shows for rotation mode '
                                'XYZ). In this rig (glTF import) every bone rests with local X = world X (her right), local Y = world Z (up), '
                                'local Z = world -Y (back)',
    'rel_world_axes_euler_xyz_deg': 'the same rotation against the parent, written in the rest WORLD axes X right, Y forward, Z up (Euler XYZ, '
                                    'right-hand rule: +X turns forward towards up, so a minus X value leans an upright bone FORWARD; +Z turns the '
                                    'front to her LEFT; +Y turns the top to her RIGHT)',
    'world_yaw_tilt_roll_deg': 'world attitude decomposed as Rz(yaw) Rx(-tilt) Ry(-roll): yaw + = facing left of the aim line, tilt + = front down / '
                               'leaning forward, roll + = right side up'}, 'setups': {}}
for sk in SETUPS:
    use_action(acts['full_' + sk])
    Q, hl, D, P, info = compute_pose(sk, poses[sk])
    err = max(min(a_, 2.0 * math.pi - a_) for a_ in ((arm.pose.bones[n].matrix.to_quaternion() @ R[n].inverted()).rotation_difference(D[n]).angle
                                                    for n in KEYED))
    perr = max((arm.matrix_world @ arm.pose.bones[n].head - P[n]).length for n in KEYED)
    co = body_coords()
    num = numbers_of(D, P, info)
    c = arm_clearance(co)
    num['arms_placeholder_clearance_mm'] = {s: dict(forearm_hand=round(1000 * c[s]['min'], 1), upper_arm_elbow_end=round(1000 * c[s]['up_min'], 1),
                                                    cuts=c[s]['cut'], swivel=poses[sk][s]) for s in c}
    num['tail'] = tail_numbers(co)
    num['feet_flat'] = foot_flat(co, info)
    num['spacing_used'] = round(info['spacing'], 3)
    num['check'] = dict(file_vs_solver_rot_deg=round(math.degrees(err), 3), file_vs_solver_pos_mm=round(1000 * perr, 2))
    numbers['results'][sk] = num
    rows = {}
    for n in TABLE_BONES:
        b = bones[n]
        pq = arm.pose.bones[n].rotation_quaternion.copy()
        relw = (D[b.parent.name].inverted() @ D[n]) if b.parent else D[n]
        e1 = pq.to_euler('XYZ')
        e2 = relw.to_euler('XYZ')
        rows[n] = dict(pose_local_euler_xyz_deg=[round(math.degrees(x), 2) for x in e1], rel_world_axes_euler_xyz_deg=[round(math.degrees(x), 2) for x in e2])
        if n == H['hips']:
            rows[n]['location_m'] = [round(x, 4) for x in (P[n] - HEAD0[n])]
    wa = {}
    for key, bn in (('Hips', H['hips']), ('Chest (UpperChest)', H['upperChest']), ('Head', H['head']), ('Foot L', nm('L', 'Foot')), ('Foot R', nm('R', 'Foot'))):
        y_, p_, r_ = ypr(D[bn])
        wa[key] = dict(yaw_left=round(y_, 2), tilt_fwd=round(p_, 2), roll_right_up=round(r_, 2))
    table['setups'][sk] = dict(drop_m=round(info['drop'], 4), spacing_m=round(info['spacing'], 3), bones=rows, world=wa)
    log('NUMBERS', sk, json.dumps(num))

json.dump(numbers, open(os.path.join(OUT, 'Yoru_Aim_r3_stage1_numbers.json'), 'w'), indent=1)
json.dump(table, open(os.path.join(OUT, 'Yoru_Aim_r3_stage1_table.json'), 'w'), indent=1)
md = ['# Yoru aim pose, round 3, stage 1: bone table (2026-10-30)', '',
      'Written by `Blender/scripts/build_aim_r3.py` from the saved full actions `Yoru_Aim_r3_full_Sa` / `_Sb` (frame 0).', '',
      '- **pose local Euler XYZ (deg)**: ' + table['conventions']['pose_local_euler_xyz_deg'] + '.',
      '- **rel. world axes Euler XYZ (deg)**: rotation against the parent in the rest world axes (X right, Y forward, Z up), Euler order XYZ, '
      'right-hand rule: +X turns forward (+Y) towards up (+Z), so a minus X value leans an upright bone FORWARD; +Z turns the front to her LEFT; '
      '+Y turns the top to her RIGHT.',
      '- **world yaw / tilt / roll**: ' + table['conventions']['world_yaw_tilt_roll_deg'] + '.', '']
for sk, t in table['setups'].items():
    md += ['## %s  (pelvis drop %.1f mm, ankle spacing %.3f m)' % (sk, 1000.0 * t['drop_m'], t['spacing_m']), '',
           '| bone | pose local Euler XYZ | rel. world axes Euler XYZ |', '|---|---|---|']
    for n, row in t['bones'].items():
        extra = ('  (location %s m)' % row['location_m']) if 'location_m' in row else ''
        md.append('| %s%s | %s | %s |' % (n, extra, ', '.join('%.2f' % v for v in row['pose_local_euler_xyz_deg']),
                                           ', '.join('%.2f' % v for v in row['rel_world_axes_euler_xyz_deg'])))
    md += ['', '| world attitude | yaw left | tilt forward | roll right up |', '|---|---|---|---|']
    for k_, w_ in t['world'].items():
        md.append('| %s | %.2f | %.2f | %.2f |' % (k_, w_['yaw_left'], w_['tilt_fwd'], w_['roll_right_up']))
    md.append('')
open(os.path.join(OUT, 'Yoru_Aim_r3_stage1_table.md'), 'w', encoding='utf-8').write('\n'.join(md))
use_action(acts['Torso'])
bpy.context.preferences.filepaths.save_version = 0
path = os.path.join(OUT, 'Yoru_Aim_r3.blend')
bpy.ops.wm.save_as_mainfile(filepath=path)
log('saved', path, '| actions', ', '.join(a.name for a in acts.values()), '| active Torso over NLA Stand_Sa')
log('DONE')
