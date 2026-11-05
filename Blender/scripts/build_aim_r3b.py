"""
Yoru - AIM POSE, ROUND 3b (2026-10-30): stage 1 corrected and stages 2 + 3 in one step, after the user's numbers (round-3 spec
Blender/work/Aim/round3_spec_from_gemini.md plus the user's corrections).  A copy of build_aim_r2.py (stays untouched) with:
  STANCE  ankles 0.34 m apart, the LEFT foot only 0.08 m ahead, toes out 5 deg (front) / 13 deg (back), the pelvis 2 cm towards the standing
          (right) foot, pelvis roll 4.5 deg with the RIGHT hip up (as Idle_v2 A2: weight right), pelvis yaw 0 and tilt 0; the drop follows from
          the right (standing) knee 8 deg, the left (free) knee follows (with the right hip up it cannot be 5 deg: see stance_solve)
  TRUNK   (layer) spine / chest / upper chest lean 7.5 / 7.5 / 6 deg (hips -> neck about 7 deg ahead of the plumb line), the idle's counter roll
          3.0 / 2.5 / 1.2 deg (the shoulders do not lean with the pelvis), chest + upper chest 6 + 6 = 12 deg LEFT (the right shoulder leads);
          the neck takes 45 % of the turn back, the head looks at the aim point with the chin 4.5 deg down and 3 deg roll to the right shoulder,
          the eyes look at the aim point, ears 9 deg back, face expression B
  TAIL    the hanging pose of round 2, copied as local rotations from the action Yoru_Aim_r2_Stand (Blender/work/Aim/Yoru_Aim_r2.blend)
  ARMS    (layer) placeholder pistols in the round-2 grip.  A1: the right arm aims (elbow 16 deg, wrist 5 cm over the shoulder joint), the right
          pistol 14 deg canted inward; the left hand is a high guard at the upper chest, its pistol 0.18..0.22 m behind and 0.14 m left of the
          right pistol (searched: the nearest offset that the rules allow), barrel on the aim line, 22 deg canted inward, elbow near the ribs.
          A2: both arms forward as round-2 B (wrists 5 cm over the shoulders, 27 deg apart, elbows 15 deg), both pistols 12 deg canted inward.
  RULES   forearm roll <= 18 deg, wrist roll <= 12 deg, arms (except the inner upper arm at the armpit), hands and pistols >= 20 mm from vest,
          pouches and holsters (real mesh), barrels <= 3 deg from the aim line, wrist bend <= 35 deg.  What does not hold is reported, not hidden.
Actions: Yoru_Aim_r3b_Stand (hips, legs, feet, toes, tail; NLA track 'Stand'), Yoru_Aim_r3b_A1 / _A2 (layer from the spine up incl. arms, hands,
fingers, eyes, ears), Yoru_Aim_r3b_full_A1 / _full_A2 (layer + stand, for measuring and pictures).
Run:  blender -b --factory-startup --python build_aim_r3b.py -- <Yoru_V2.glb> <out dir> [design=1]
Writes <out dir>/Yoru_Aim_r3b.blend and <out dir>/Yoru_Aim_r3b_numbers.json.
Blender: +Y forward (the aim line), her left = -X, up = +Z.
"""
import bpy, bmesh, sys, os, math, json, struct, time
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
    print('[aim_r3b %5.1fs]' % (time.time() - T0), *a, flush=True)


# ------------------------------------------------------------------ import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Body']
face = bpy.data.objects.get('Face')
hair = bpy.data.objects.get('Hair')
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
nodes = js['nodes']
H = {h['bone']: nodes[h['node']]['name'] for h in js['extensions']['VRM']['humanoid']['humanBones']}
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
FING = ('Index', 'Middle', 'Ring', 'Little')
PARTS = ('Proximal', 'Intermediate', 'Distal')


def nm(side, part):
    return H[('left' if side == 'L' else 'right') + part]


def hkey(side, part):
    return ('left' if side == 'L' else 'right') + part


UPPER = [H[k] for k in ('spine', 'chest', 'upperChest', 'neck', 'head')]
for _s in ('L', 'R'):
    UPPER += [nm(_s, p) for p in ('Shoulder', 'UpperArm', 'LowerArm', 'Hand')]
    UPPER += [nm(_s, f_ + p_) for f_ in FING + ('Thumb',) for p_ in PARTS if hkey(_s, f_ + p_) in H]
STAND = [H['hips']] + [nm(s, p) for s in ('L', 'R') for p in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes') if hkey(s, p) in H] + TAIL


# ------------------------------------------------------------------ helpers
def deg(x):
    return math.radians(x)


def eul(rx=0.0, ry=0.0, rz=0.0):
    return Euler((deg(rx), deg(ry), deg(rz)), 'XYZ').to_quaternion()


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    s = d.cross(n)
    return Matrix((d, n, s)).transposed().to_quaternion()


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


def signed_angle(a, b, axis):
    """angle (deg) that turns a onto b about axis (both projected onto the plane normal to axis)"""
    ax = axis.normalized()
    a_ = (a - ax * a.dot(ax)).normalized()
    b_ = (b - ax * b.dot(ax)).normalized()
    return math.degrees(math.atan2(a_.cross(b_).dot(ax), a_.dot(b_)))


# ------------------------------------------------------------------ grip and pistol of the sprint (build_sprint_r1.py, unchanged numbers)
GRIP = {'Index': (4.0, 10.0, 8.0), 'Middle': (68.0, 74.0, 44.0), 'Ring': (72.0, 78.0, 46.0), 'Little': (75.0, 80.0, 48.0)}
GRIP_SPREAD = {'Index': 22.0, 'Middle': 0.0, 'Ring': -2.0, 'Little': -4.0}
THUMB = (20.0, 30.0, 18.0, 10.0)
GRIP_AT = (0.058, -0.010, 0.020)    # grip centre from the wrist: along the hand, towards the thumb, towards the palm (m)
PISTOL_BOXES = [((0.0, 0.060, 0.058), (0.026, 0.185, 0.032), 0.0),      # slide          (centre, size, rake about x in deg), pistol local frame:
                ((0.0, 0.088, 0.034), (0.022, 0.125, 0.018), 0.0),      # frame          +Y = barrel, +Z = top (thumb side), origin = grip centre
                ((0.0, 0.034, 0.016), (0.010, 0.046, 0.010), 0.0),      # trigger guard
                ((0.0, 0.000, 0.000), (0.026, 0.046, 0.096), -12.0)]    # grip
BORE = Vector((0.0, 0.0, 0.058))                                       # the bore line (slide centre line) in the pistol frame
MUZZLE_Y = 0.060 + 0.185 / 2.0
WR_MAX = 35.0
CLEAR = 0.003
AIM_POINT = Vector((0.35, 15.0, 1.30))   # the barrels converge 15 m ahead on the crosshair line of the game camera (0.35 m right of her centre line)

# ------------------------------------------------------------------ stance r3b (pictures only; the user's numbers)
# spacing / stagger of the ankle joints (m), front = the foot ahead, shift = pelvis moved from the middle of the feet towards the standing (back,
# right) foot (m), roll = pelvis roll (deg, the RIGHT hip up), knee_back = knee flexion of the standing leg (deg) - the drop follows from it
STANCES = {'L': dict(label='r3b: 0,34 m, linker Fuss 0,08 m vorn, Becken-Roll 4,5 Grad (rechte Huefte oben wie Idle_v2)',
                     spacing=0.34, stagger=0.08, front='L', shift=0.020, roll=4.5, knee_back=8.0, toe_front=5.0, toe_back=13.0)}
LEG_L1 = (HEAD0[H['leftLowerLeg']] - HEAD0[H['leftUpperLeg']]).length
LEG_L2 = (HEAD0[H['leftFoot']] - HEAD0[H['leftLowerLeg']]).length
CLEAR = 0.020                                                        # round 3b rule: 20 mm against vest, pouches and holsters


def pelvis_q(st):
    return eul(ry=-st['roll'])                                       # rotation about +Y by -roll lifts her right side


def stance_solve(st):
    """ankle targets, foot yaws and the pelvis drop: the feet are set around the resting pelvis so that it sits `shift` from their middle
    towards the standing foot; the drop is what the standing (back) leg needs for its knee flexion knee_back"""
    hip0 = HEAD0[H['hips']]
    back = 'R' if st['front'] == 'L' else 'L'
    sxb = 1.0 if back == 'R' else -1.0
    to_back = Vector((sxb * 0.5 * st['spacing'], -0.5 * st['stagger'], 0.0)).normalized()
    mid = Vector((hip0.x, hip0.y, 0.0)) - to_back * st['shift']
    ank, yaw = {}, {}
    for side in ('L', 'R'):
        sx = -1.0 if side == 'L' else 1.0
        fy = mid.y + (0.5 * st['stagger'] if side == st['front'] else -0.5 * st['stagger'])
        ank[side] = Vector((mid.x + sx * 0.5 * st['spacing'], fy, HEAD0[nm(side, 'Foot')].z))
        toe = st['toe_front'] if side == st['front'] else st['toe_back']
        yaw[side] = toe if side == 'L' else -toe
    q = pelvis_q(st)
    hj = hip0 + q @ (HEAD0[nm(back, 'UpperLeg')] - hip0)
    d2 = LEG_L1 ** 2 + LEG_L2 ** 2 + 2.0 * LEG_L1 * LEG_L2 * math.cos(deg(st['knee_back']))
    a = ank[back]
    h2 = (a.x - hj.x) ** 2 + (a.y - hj.y) ** 2
    drop = (hj.z - a.z) - math.sqrt(max(d2 - h2, 0.0))
    return ank, yaw, drop


# ------------------------------------------------------------------ tail: the hanging pose of round 2, copied as local rotations
R2_BLEND = KV.get('r2_blend', r'C:\Users\valen\ZeroProtocol\Blender\work\Aim\Yoru_Aim_r2.blend')


def load_r2_tail():
    """local rotation quaternions (frame 0) of the tail joints in the action Yoru_Aim_r2_Stand of the round-2 file"""
    with bpy.data.libraries.load(R2_BLEND, link=False) as (src, dst):
        dst.actions = ['Yoru_Aim_r2_Stand']
    act = dst.actions[0]
    fcs = []
    try:
        fcs = list(act.fcurves)
    except Exception:
        pass
    if not fcs:
        for l in act.layers:
            for s in l.strips:
                for cb in s.channelbags:
                    fcs += list(cb.fcurves)
    q = {}
    for n in TAIL:
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        comp = sorted([fc for fc in fcs if fc.data_path == dp], key=lambda fc: fc.array_index)
        q[n] = Quaternion([fc.evaluate(0.0) for fc in comp]).normalized()
    bpy.data.actions.remove(act)
    return q


TAIL_Q_R2 = load_r2_tail()
TAIL_REL = {n: R[n] @ TAIL_Q_R2[n] @ R[n].inverted() for n in TAIL}  # the same local rotation, as a rest-frame delta (D = D_parent @ rel)
log('tail: copied the local rotations of %d joints from %s (Yoru_Aim_r2_Stand)' % (len(TAIL_REL), R2_BLEND))
TAIL_DIRS = 'copied from Yoru_Aim_r2_Stand'

# ------------------------------------------------------------------ trunk (layer) and the two arm variants
TRUNK = dict(lean=(7.0, 6.5, 5.5), roll=(3.0, 2.5, 1.2), yaw=(0.0, 6.0, 6.0), neck_share=0.45, head_pitch_down=4.5, head_roll_right=3.0)
EYES = [H[k] for k in ('leftEye', 'rightEye') if k in H]
EARS = [n for n in ('J_Opt_L_CatEar1_01', 'J_Opt_R_CatEar1_01') if n in bones]
EARS_BACK = 9.0
UPPER = UPPER + EYES + EARS
# wrist: offset of the wrist from the posed shoulder joint (world axes, m); cant_in: wanted inward cant of the pistol (deg, top towards the
# thumb side = towards her midline); guard: A1's left pistol relative to the right one (m behind, m to the left, grip height in m)
VARIANTS = {
    'A1': dict(label='A1  eine Hand fuehrt, linke Pistole als hohe Garde auf Brusthoehe', stance='L',
               wrist={'R': (0.070, 0.409, 0.050), 'L': (-0.060, 0.250, -0.040)}, phi0={'R': 15.0, 'L': 10.0},
               cant_in={'R': 14.0, 'L': 22.0}, clav={'R': (10.0, 0.0), 'L': (4.0, 1.0)},
               guard=dict(behind=(0.20, 0.18, 0.16, 0.14, 0.12, 0.10, 0.08), left=0.14, grip_z=1.20)),
    'A2': dict(label='A2  beide Arme vor (wie Runde 2 B), Ellbogen 15 Grad, Pistolen 12 Grad nach innen', stance='L',
               wrist={'R': (0.097, 0.404, 0.050), 'L': (-0.097, 0.404, 0.050)}, phi0={'R': 20.0, 'L': 20.0},
               cant_in={'R': 12.0, 'L': 12.0}, clav={'R': (8.0, 0.0), 'L': (8.0, 0.0)}),
}


def trunk_of(V):
    return dict(TRUNK)


# ------------------------------------------------------------------ the pose
REST_UA = {s: (HEAD0[nm(s, 'LowerArm')] - HEAD0[nm(s, 'UpperArm')]).normalized() for s in ('L', 'R')}
REST_FA = {s: (HEAD0[nm(s, 'Hand')] - HEAD0[nm(s, 'LowerArm')]).normalized() for s in ('L', 'R')}
REST_HD = {s: Vector((1.0 if s == 'R' else -1.0, 0.0, 0.0)) for s in ('L', 'R')}
REST_N = Vector((0.0, 0.0, -1.0))
L_UA = {s: (HEAD0[nm(s, 'LowerArm')] - HEAD0[nm(s, 'UpperArm')]).length for s in ('L', 'R')}
L_FA = {s: (HEAD0[nm(s, 'Hand')] - HEAD0[nm(s, 'LowerArm')]).length for s in ('L', 'R')}


def elbow_ik(S, W, phi, sx, L1, L2):
    """elbow K for the wrist target W; phi = swivel of the elbow about the shoulder-wrist line (0 = straight down, + = outwards, deg)"""
    v = W - S
    d = v.length
    d_c = min(max(d, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.9995)
    u = v.normalized()
    a = (L1 * L1 - L2 * L2 + d_c * d_c) / (2.0 * d_c)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    down = Vector((0.0, 0.0, -1.0))
    p0 = (down - u * down.dot(u)).normalized()
    out = Vector((sx, 0.0, 0.0))
    o0 = (out - u * out.dot(u) - p0 * out.dot(p0)).normalized()
    p = (p0 * math.cos(deg(phi)) + o0 * math.sin(deg(phi))).normalized()
    return S + u * a + p * h, S + u * d_c, d - d_c


def compute_pose(V, phi, stance_key=None):
    tr = TRUNK
    st = STANCES[stance_key or V['stance']]
    rel = {}
    for k, key in enumerate(('spine', 'chest', 'upperChest')):
        rel[H[key]] = eul(rx=-tr['lean'][k], ry=tr['roll'][k], rz=tr['yaw'][k])
    for n in EARS:
        rel[n] = eul(rx=-EARS_BACK)                                   # + about X tips the ears forward (build_idle_v2_face.py): 9 deg back = -9
    for n in TAIL:
        rel[n] = TAIL_REL[n]
    for side, sx in (('L', -1.0), ('R', 1.0)):
        pro, dep = V['clav'][side]
        rel[nm(side, 'Shoulder')] = eul(ry=sx * dep, rz=sx * pro)
        for fn, curls in GRIP.items():
            for pj, (part, c) in enumerate(zip(PARTS, curls)):
                q_ = Quaternion((0, 1, 0), deg(sx * c))
                if pj == 0:
                    q_ = eul(rz=sx * GRIP_SPREAD[fn]) @ q_
                rel[nm(side, fn + part)] = q_
        rel[nm(side, 'ThumbProximal')] = eul(rz=-sx * THUMB[0]) @ Quaternion((0, 1, 0), deg(sx * THUMB[1]))
        rel[nm(side, 'ThumbIntermediate')] = Quaternion((0, 1, 0), deg(sx * THUMB[2]))
        rel[nm(side, 'ThumbDistal')] = Quaternion((0, 1, 0), deg(sx * THUMB[3]))
    head0 = HEAD0[H['head']]
    yaw_aim = math.degrees(math.atan2(AIM_POINT.x - head0.x, AIM_POINT.y - head0.y))     # + = the aim point lies to her right
    d_head = eul(rz=-yaw_aim) @ eul(rx=-tr['head_pitch_down']) @ eul(ry=tr['head_roll_right'])
    ank, fyaw, drop = stance_solve(st)
    hips_d = Vector((0.0, 0.0, -drop))
    legs = {side: (ank[side], fyaw[side]) for side in ('L', 'R')}
    D, P, Q, ik, armc = {}, {}, {}, {}, {}
    info = {'phi': dict(phi), 'drop': drop, 'stance': st, 'yaw_aim': yaw_aim}
    hips_name = H['hips']
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        P[name] = HEAD0[name].copy() if parent is None else P[parent] + D[parent] @ (HEAD0[name] - HEAD0[parent])
        if name == hips_name:
            P[name] = P[name] + hips_d
            D[name] = pelvis_q(st)
        elif name == H['neck']:
            D[name] = D[H['upperChest']].slerp(d_head, tr['neck_share'])
        elif name == H['head']:
            D[name] = d_head
        elif name in EYES:
            fwd = (d_head @ Vector((0.0, 1.0, 0.0))).normalized()
            D[name] = fwd.rotation_difference((AIM_POINT - P[name]).normalized()) @ d_head
        elif name in rel:
            D[name] = Dp @ rel[name]
        else:
            D[name] = Dp.copy()
        for side, sx in (('L', -1.0), ('R', 1.0)):
            if name == nm(side, 'UpperLeg'):
                Hp = P[name]
                K0, A0 = HEAD0[nm(side, 'LowerLeg')], HEAD0[nm(side, 'Foot')]
                T, yaw_ = legs[side]
                pole = Vector((-math.sin(deg(yaw_)), math.cos(deg(yaw_)), 0.0))
                K, Teff, defi = two_bone_ik(Hp, T, pole, LEG_L1, LEG_L2)
                ik[side] = (K, Teff, defi)
                D[name] = (K0 - HEAD0[name]).rotation_difference(K - Hp)
            elif name == nm(side, 'LowerLeg'):
                K, Teff, _ = ik[side]
                D[name] = (HEAD0[nm(side, 'Foot')] - HEAD0[name]).rotation_difference(Teff - K)
            elif name == nm(side, 'Foot'):
                D[name] = eul(rz=legs[side][1])
            elif name == nm(side, 'UpperArm'):
                S = P[name]
                W = Vector(V['wrist_world'][side]) if side in V.get('wrist_world', {}) else S + Vector(V['wrist'][side])
                K, Weff, defi = elbow_ik(S, W, phi[side], sx, L_UA[side], L_FA[side])
                ua, fo = (K - S).normalized(), (Weff - K).normalized()
                ax = ua.cross(fo)
                ax = ax.normalized() if ax.length > 1e-6 else Vector((1.0, 0.0, 0.0))
                n = ax * (-sx)                                        # palm normal on the elbow axis: pure hinge, no twist at the elbow
                Du = aim(REST_UA[side], REST_N, ua, n)
                Df0 = aim(REST_FA[side], REST_N, fo, n)
                muzzle_guess = Weff + fo * 0.21 + Vector((0.0, 0.0, 0.05))
                bdir = (AIM_POINT - muzzle_guess).normalized()
                ang = math.degrees(fo.angle(bdir))
                hdir = bdir.copy() if ang <= WR_MAX else fo.slerp(bdir, WR_MAX / ang).normalized()
                Dh0 = fo.rotation_difference(hdir) @ Df0
                top = Dh0 @ Vector((0.0, 1.0, 0.0))
                cant = signed_angle(Vector((0.0, 0.0, 1.0)), top, hdir)   # right-hand roll about the barrel from upright to the pistol top
                want = -sx * V['cant_in'][side]                       # inward = towards her midline: - for the right hand, + for the left
                need = want - cant
                tw_e = max(-18.0, min(18.0, 0.6 * need))
                tw_w = max(-12.0, min(12.0, need - tw_e))
                Df = Quaternion(fo, deg(tw_e)) @ Df0
                Dh = Quaternion(hdir, deg(tw_w)) @ Quaternion(hdir, deg(tw_e)) @ Dh0
                armc[side] = (Du, Df, Dh)
                info[side] = dict(S=S.copy(), K=K.copy(), W=Weff.copy(), W_want=W.copy(), deficit=defi, ua=ua, fo=fo, hdir=hdir, bdir=bdir,
                                  wrist_want=ang, cant0=cant, tw_e=tw_e, tw_w=tw_w, cant_want=want)
                D[name] = Du
            elif name == nm(side, 'LowerArm'):
                D[name] = armc[side][1]
            elif name == nm(side, 'Hand'):
                D[name] = armc[side][2]
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    info['legs'] = {s: ik[s] for s in ('L', 'R')}
    hips_loc = R[hips_name].inverted() @ hips_d
    return Q, hips_loc, D, P, info


def set_pose(V, phi, stance_key=None):
    ad = arm.animation_data
    if ad and ad.action:
        ad.action = None
    Q, hips_loc, D, P, info = compute_pose(V, phi, stance_key)
    for n in UPPER + STAND:
        pb = arm.pose.bones[n]
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Q[n]
    arm.pose.bones[H['hips']].location = hips_loc
    bpy.context.view_layer.update()
    return Q, hips_loc, D, P, info


# ------------------------------------------------------------------ geometry numbers (no mesh)
def pistol_frame(D, P, side):
    """world matrix of the pistol for the pose (same placement as attach_pistols: rest frame of the hand + GRIP_AT, carried by the hand delta)"""
    sx = 1.0 if side == 'R' else -1.0
    F, U, N = Vector((sx, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, -1.0))
    M = Matrix((F.cross(U), F, U)).transposed().to_4x4()
    M.translation = HEAD0[nm(side, 'Hand')] + F * GRIP_AT[0] + U * GRIP_AT[1] + N * GRIP_AT[2]
    Dh = D[nm(side, 'Hand')]
    W0, W = HEAD0[nm(side, 'Hand')], P[nm(side, 'Hand')]
    return Matrix.Translation(W) @ Dh.to_matrix().to_4x4() @ Matrix.Translation(-W0) @ M


def geometry(D, P, info):
    g = {}
    for side, sx in (('L', -1.0), ('R', 1.0)):
        it = info[side]
        S, K, W = P[nm(side, 'UpperArm')], P[nm(side, 'LowerArm')], P[nm(side, 'Hand')]
        ua, fo = (K - S).normalized(), (W - K).normalized()
        Mp = pistol_frame(D, P, side)
        barrel = (Mp.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
        top = (Mp.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
        grip = Mp.translation.copy()
        muzzle = Mp @ (BORE + Vector((0.0, MUZZLE_Y, 0.0)))
        bore0 = Mp @ BORE
        to_aim = (AIM_POINT - muzzle).normalized()
        g[side] = dict(
            wrist_rel_shoulder=[round(x, 3) for x in (W - S)], grip_rel_shoulder=[round(x, 3) for x in (grip - S)],
            wrist_world=[round(x, 3) for x in W], grip_world=[round(x, 3) for x in grip], elbow_world=[round(x, 3) for x in K],
            shoulder_world=[round(x, 3) for x in S], muzzle_world=[round(x, 3) for x in muzzle],
            elbow_inner=round(180.0 - math.degrees(ua.angle(fo)), 1),
            upper_arm_raise=round(math.degrees(ua.angle(Vector((0.0, 0.0, -1.0)))), 1),          # 0 = hanging, 90 = level
            upper_arm_out=round(math.degrees(math.asin(max(-1.0, min(1.0, sx * ua.x)))), 1),    # out of the sagittal plane: + = away from the body
            upper_arm_fwd=round(math.degrees(math.atan2(ua.y, -ua.z)), 1),                       # sagittal plane: + = forward
            forearm_pitch=round(math.degrees(math.asin(max(-1.0, min(1.0, fo.z)))), 1),         # + = forearm rising towards the hand
            forearm_in=round(math.degrees(math.atan2(-sx * fo.x, fo.y)), 1),                    # + = towards the midline
            wrist_bend=round(math.degrees(fo.angle(barrel)), 1), wrist_wanted=round(it['wrist_want'], 1),
            barrel_vs_forward=round(math.degrees(barrel.angle(Vector((0.0, 1.0, 0.0)))), 2),
            barrel_yaw=round(math.degrees(math.atan2(barrel.x, barrel.y)), 2), barrel_pitch=round(math.degrees(math.asin(barrel.z)), 2),
            barrel_vs_aimpoint=round(math.degrees(barrel.angle(to_aim)), 2),
            cant=round(sx * signed_angle(Vector((0.0, 0.0, 1.0)), top, barrel), 1),             # + = pistol top rolled outwards
            cant_before_roll=round(sx * it['cant0'], 1), forearm_roll=round(it['tw_e'], 1), wrist_roll=round(it['tw_w'], 1),
            elbow_swivel=round(info['phi'][side], 1), reach_deficit_mm=round(1000.0 * it['deficit'], 1),
            bore_line=(bore0, barrel))
    (pa, da), (pb_, db) = g['L'].pop('bore_line'), g['R'].pop('bore_line')
    w = da.cross(db)                                                  # closest approach of the two bore lines
    if w.length > 1e-9:
        t1 = (pb_ - pa).cross(db).dot(w) / w.length_squared
        t2 = (pb_ - pa).cross(da).dot(w) / w.length_squared
        c1, c2 = pa + da * t1, pb_ + db * t2
        conv = dict(distance_ahead_m=round(0.5 * (c1.y + c2.y), 2), gap_m=round((c1 - c2).length, 3))
    else:
        conv = dict(distance_ahead_m=None, gap_m=None)
    vL = Vector(g['L']['wrist_rel_shoulder'])
    vR = Vector(g['R']['wrist_rel_shoulder'])
    both = dict(barrels_angle=round(math.degrees(da.angle(db)), 2), barrels_converge=conv,
                arms_angle_3d=round(math.degrees(vL.angle(vR)), 1),
                arms_angle_top=round(math.degrees(Vector((vL.x, vL.y, 0.0)).angle(Vector((vR.x, vR.y, 0.0)))), 1),
                wrists_apart_m=round((P[nm('L', 'Hand')] - P[nm('R', 'Hand')]).length, 3),
                wrists_apart_x_m=round(P[nm('R', 'Hand')].x - P[nm('L', 'Hand')].x, 3),
                grips_apart_m=round((Vector(g['L']['grip_world']) - Vector(g['R']['grip_world'])).length, 3))
    # trunk and head
    hip, neck = P[H['hips']], P[H['neck']]
    hn = neck - hip
    hip0, neck0 = HEAD0[H['hips']], HEAD0[H['neck']]
    hn0 = neck0 - hip0
    duc = D[H['upperChest']]
    chest_fwd = duc @ Vector((0.0, 1.0, 0.0))
    chest_up = duc @ Vector((0.0, 0.0, 1.0))
    sh_line = P[nm('R', 'UpperArm')] - P[nm('L', 'UpperArm')]
    gaze = D[H['head']] @ Vector((0.0, 1.0, 0.0))
    trunk = dict(hips_rotation_deg=round(math.degrees(D[H['hips']].angle), 3), hips_drop_m=round(info['drop'], 4),
                 spine_chain_pitch_fwd=round(math.degrees(math.atan2(chest_up.y, chest_up.z)), 1),
                 spine_chain_yaw=round(math.degrees(math.atan2(-chest_fwd.x, chest_fwd.y)), 1),        # + = right shoulder forward
                 hip_neck_lean_fwd=round(math.degrees(math.atan2(hn.y, hn.z)), 1), hip_neck_lean_rest=round(math.degrees(math.atan2(hn0.y, hn0.z)), 1),
                 shoulder_line_yaw=round(math.degrees(math.atan2(sh_line.y, sh_line.x)), 1),
                 gaze_yaw_right=round(math.degrees(math.atan2(gaze.x, gaze.y)), 1), gaze_pitch_up=round(math.degrees(math.asin(gaze.z)), 1),
                 head_pos=[round(x, 3) for x in P[H['head']]])
    for side in ('L', 'R'):                                           # shoulder joint rise in the upper chest frame against the rest pose (shrug check)
        s_now = duc.inverted() @ (P[nm(side, 'UpperArm')] - P[H['upperChest']])
        s_rest = HEAD0[nm(side, 'UpperArm')] - HEAD0[H['upperChest']]
        trunk['shoulder_rise_mm_' + side] = round(1000.0 * (s_now.z - s_rest.z), 1)
        trunk['shoulder_fwd_mm_' + side] = round(1000.0 * (s_now.y - s_rest.y), 1)
    legs = {}
    st = info['stance']
    for side in ('L', 'R'):
        K, Teff, defi = info['legs'][side]
        hp = P[nm(side, 'UpperLeg')]
        legs[side] = dict(knee_flex=round(180.0 - math.degrees((hp - K).angle(Teff - K)), 1), ankle=[round(x, 3) for x in Teff],
                          reach_deficit_mm=round(1000.0 * defi, 1),
                          toe_out=st['toe_front'] if side == st['front'] else st['toe_back'], front=(side == st['front']))
    # the stance block in the definitions of aim_measure.py (ankle joints, hips joint, upper-arm joints, head joint; cm ahead of the ankles' middle)
    fl, fr_ = P[nm('L', 'Foot')], P[nm('R', 'Foot')]
    mid = (fl + fr_) * 0.5
    sh_mid = (P[nm('L', 'UpperArm')] + P[nm('R', 'UpperArm')]) * 0.5
    stance = dict(label=st['label'], front_foot=st['front'], knee_L=legs['L']['knee_flex'], knee_R=legs['R']['knee_flex'],
                  feet_spacing_x=round(abs(fl.x - fr_.x), 3), feet_stagger_y=round(abs(fl.y - fr_.y), 3),
                  pelvis_drop_cm=round(100.0 * info['drop'], 2), hips_vs_feet_y_cm=round(100.0 * (hip.y - mid.y), 1),
                  shoulders_vs_feet_y_cm=round(100.0 * (sh_mid.y - mid.y), 1), head_vs_feet_y_cm=round(100.0 * (P[H['head']].y - mid.y), 1),
                  hips_height_m=round(hip.z, 3), lean=round(math.degrees(math.atan2(hn.y, hn.z)), 1),
                  toe_out_front=st['toe_front'], toe_out_back=st['toe_back'], feet_mid_xy=[round(mid.x, 4), round(mid.y, 4)])
    trunk['stance'] = stance
    return g, both, trunk, legs


if DESIGN:
    for key, V in VARIANTS.items():
        phi = dict(V['phi0'])
        Q, hl, D, P, info = compute_pose(V, phi)
        g, both, trunk, legs = geometry(D, P, info)
        log('DESIGN', key, V['label'])
        for s in ('R', 'L'):
            log('  ', s, json.dumps({k: g[s][k] for k in ('wrist_rel_shoulder', 'grip_world', 'elbow_inner', 'wrist_bend', 'wrist_wanted', 'cant',
                                                          'cant_before_roll', 'forearm_roll', 'wrist_roll', 'barrel_vs_aimpoint')}))
        log('   stance', json.dumps(trunk['stance']))
        log('   trunk', json.dumps({k: v for k, v in trunk.items() if k != 'stance'}))
    sys.exit(0)


# ------------------------------------------------------------------ pistols (placeholders) attached to the hand bones (as build_sprint_r1.py)
def make_pistol(name):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    for c, s, rx in PISTOL_BOXES:
        m = Matrix.Translation(c) @ Euler((deg(rx), 0, 0)).to_matrix().to_4x4() @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + '_mat')
    mat.use_nodes = True
    bsdf = next(n_ for n_ in mat.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.16, 0.17, 0.19, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.55
    bsdf.inputs['Roughness'].default_value = 0.38
    ob.data.materials.append(mat)
    return ob


def attach_pistols():
    ad_ = arm.animation_data
    keep = ad_.action if ad_ else None
    if ad_:
        ad_.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
        pb.scale = Vector((1.0, 1.0, 1.0))
    bpy.context.view_layer.update()
    out = {}
    for side in ('L', 'R'):
        sx = 1.0 if side == 'R' else -1.0
        F, U, N = Vector((sx, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, -1.0))
        M = Matrix((F.cross(U), F, U)).transposed().to_4x4()
        M.translation = HEAD0[nm(side, 'Hand')] + F * GRIP_AT[0] + U * GRIP_AT[1] + N * GRIP_AT[2]
        ob = make_pistol('PLATZHALTER_Pistole_' + side)
        ob.parent = arm
        ob.parent_type = 'BONE'
        ob.parent_bone = nm(side, 'Hand')
        bpy.context.view_layer.update()
        ob.matrix_world = arm.matrix_world @ M
        bpy.context.view_layer.update()
        out[side] = ob
    if ad_ and keep:
        ad_.action = keep
    return out


PISTOLS = attach_pistols()
log('pistols attached:', ', '.join(o.name for o in PISTOLS.values()))


# ------------------------------------------------------------------ exact clearance (build_sprint_r1.py: clearance_exact)
def invisible_polygons():
    me = body.data
    imgs = {}
    for mi, m in enumerate(me.materials):
        if m is None or not m.use_nodes:
            continue
        for n_ in m.node_tree.nodes:
            if n_.type == 'TEX_IMAGE' and n_.image:
                w_, h_ = n_.image.size
                px = np.array(n_.image.pixels[:], dtype=np.float32).reshape(h_, w_, 4)[:, :, 3]
                imgs[mi] = (px, w_, h_)
                break
    uv = me.uv_layers.active.data
    out = set()
    for poly in me.polygons:
        im = imgs.get(poly.material_index)
        if im is None:
            continue
        px, w_, h_ = im
        a_ = 0.0
        for li in poly.loop_indices:
            u_, v_ = uv[li].uv
            a_ += px[int(min(max(v_, 0.0), 0.9999) * h_), int(min(max(u_, 0.0), 0.9999) * w_)]
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
HAND_SET = {}
for side in ('L', 'R'):
    hand_set = {nm(side, 'Hand')} | {nm(side, f_ + p_) for f_ in FING + ('Thumb',) for p_ in PARTS if hkey(side, f_ + p_) in H}
    HAND_SET[side] = hand_set
    for part, bset in (('UpperArm', {nm(side, 'UpperArm')}), ('LowerArm', {nm(side, 'LowerArm')}), ('Hand', hand_set)):
        polys = [list(p.vertices) for p in body.data.polygons if p.index not in INV and all(dom_of[v_] in bset and VIS[v_] for v_ in p.vertices)]
        ARM_PARTS[(side, part)] = (polys, sorted({v_ for pl in polys for v_ in pl}))
tail_v = set(i for i, n_ in enumerate(dom_of) if VIS[i] and n_ in TAIL[2:])
TAIL_POLYS = [list(p.vertices) for p in body.data.polygons if p.index not in INV and all(v_ in tail_v for v_ in p.vertices)]
NOT_TAIL_POLYS = [list(p.vertices) for p in body.data.polygons if p.index not in INV
                  and all(VIS[v_] and dom_of[v_] not in TAIL and (dom_of[v_] in _solid or dom_of[v_] in {H['leftFoot'], H['rightFoot']}
                                                                   or (dom_of[v_].startswith('J_Sec_') and 'Hair' not in dom_of[v_])) for v_ in p.vertices)]
FINGER_VERTS = {s: {f_: [i for i, n_ in enumerate(dom_of) if n_ in (nm(s, f_ + 'Intermediate'), nm(s, f_ + 'Distal'))] for f_ in FING + ('Thumb',)}
                for s in ('L', 'R')}
HANDALL_VERTS = {s: [i for i, n_ in enumerate(dom_of) if n_ in HAND_SET[s]] for s in ('L', 'R')}
log('clearance sets: gear %d polys, tail %d polys, body-without-tail %d polys, invisible %d' % (len(GEAR_POLYS), len(TAIL_POLYS), len(NOT_TAIL_POLYS), len(INV)))
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


def pistol_geometry(side):
    ob = PISTOLS[side]
    mw = ob.matrix_world
    co = [mw @ v.co for v in ob.data.vertices]
    polys = [list(p.vertices) for p in ob.data.polygons]
    samples = list(co)
    for p in ob.data.polygons:
        vs = [co[i] for i in p.vertices]
        for a_ in (0.125, 0.375, 0.625, 0.875):
            for b_ in (0.125, 0.375, 0.625, 0.875):
                samples.append(vs[0].lerp(vs[1], a_).lerp(vs[3].lerp(vs[2], a_), b_))
    return co, polys, samples


def clearance_exact(co=None, t_min=0.8):
    co = body_coords() if co is None else co
    gear = BVHTree.FromPolygons(co, GEAR_POLYS, all_triangles=False)
    pbs = arm.pose.bones
    res = {}
    pist = {s: pistol_geometry(s) for s in ('L', 'R')}
    pbvh = {s: BVHTree.FromPolygons(pist[s][0], pist[s][1], all_triangles=False) for s in ('L', 'R')}
    abvh = {}
    for side in ('L', 'R'):
        sh = arm.matrix_world @ pbs[nm(side, 'UpperArm')].head
        el = arm.matrix_world @ pbs[nm(side, 'LowerArm')].head
        r = {'cut': 0, 'cut_part': None, 'min': 9.0, 'min_part': None, 'up_min': 9.0, 'up_min_all': 9.0}
        for part in ('UpperArm', 'LowerArm', 'Hand'):
            polys, vids = ARM_PARTS[(side, part)]
            if part == 'UpperArm':
                for v_ in vids:
                    hit = gear.find_nearest(co[v_])
                    if hit[0] is not None:
                        r['up_min_all'] = min(r['up_min_all'], hit[3])
                polys = [pl for pl in polys if intersect_point_line(co[pl[0]], sh, el)[1] > t_min]
                vids = sorted({v_ for pl in polys for v_ in pl})
            if not polys:
                continue
            tb = BVHTree.FromPolygons(co, polys, all_triangles=False)
            abvh[(side, part)] = tb
            pairs_ = tb.overlap(gear)
            if len(pairs_) > r['cut']:
                gb_ = {}
                for ia_, ib_ in pairs_:
                    k_ = dom_of[GEAR_POLYS[ib_][0]]
                    gb_[k_] = gb_.get(k_, 0) + 1
                r['cut'], r['cut_part'] = len(pairs_), (part, gb_)
            for v_ in vids:
                hit = gear.find_nearest(co[v_])
                if hit[0] is None:
                    continue
                if part == 'UpperArm':
                    r['up_min'] = min(r['up_min'], hit[3])
                elif hit[3] < r['min']:
                    r['min'], r['min_part'] = hit[3], (part, dom_of[v_], tuple(round(x, 3) for x in co[v_]))
        r['pistol_cut'] = len(pbvh[side].overlap(gear))
        r['pistol_min'], r['pistol_where'] = 9.0, None
        for s_ in pist[side][2]:
            hit = gear.find_nearest(s_)
            if hit[0] is not None and hit[3] < r['pistol_min']:
                r['pistol_min'], r['pistol_where'] = hit[3], tuple(round(x, 3) for x in s_)
        res[side] = r
    for side, other in (('L', 'R'), ('R', 'L')):
        n_cut = len(pbvh[side].overlap(pbvh[other]))
        for part in ('LowerArm', 'Hand'):
            if (other, part) in abvh:
                n_cut += len(pbvh[side].overlap(abvh[(other, part)]))
        dmin = min((pbvh[other].find_nearest(s_)[3] for s_ in pist[side][2]), default=9.0)
        res[side]['pistol_other_cut'], res[side]['pistol_other_min'] = n_cut, dmin
    return res


def side_ok(r):
    return (r['cut'] == 0 and r['min'] >= CLEAR and r['up_min'] >= CLEAR and r['pistol_cut'] == 0 and r['pistol_min'] >= CLEAR
            and r['pistol_other_cut'] == 0 and r['pistol_other_min'] >= CLEAR)


def box_depth(p_local):
    """how deep a point (pistol frame) lies inside the union of the pistol boxes (m, > 0 inside), and its distance to the surface outside (< 0)"""
    best = -9.0
    for c, s, rx in PISTOL_BOXES:
        q = Euler((-deg(rx), 0, 0)).to_matrix() @ (p_local - Vector(c))
        dx, dy, dz = s[0] / 2 - abs(q.x), s[1] / 2 - abs(q.y), s[2] / 2 - abs(q.z)
        if dx > 0 and dy > 0 and dz > 0:
            d = min(dx, dy, dz)
        else:
            d = -math.sqrt(max(0.0, -dx) ** 2 + max(0.0, -dy) ** 2 + max(0.0, -dz) ** 2)
        best = max(best, d)
    return best


def grip_numbers(co):
    """per hand: deepest finger / hand vertex inside its own pistol (mm) and per finger the closest approach to the pistol (mm, < 0 = inside)"""
    out = {}
    for side in ('L', 'R'):
        Mi = PISTOLS[side].matrix_world.inverted()
        depth_all = max(box_depth(Mi @ co[i]) for i in HANDALL_VERTS[side])
        n3 = sum(1 for i in HANDALL_VERTS[side] if box_depth(Mi @ co[i]) > 0.003)
        fingers, where = {}, {}
        for f_, ids in FINGER_VERTS[side].items():
            if ids:
                i_best = max(ids, key=lambda i: box_depth(Mi @ co[i]))
                fingers[f_] = round(-1000.0 * box_depth(Mi @ co[i_best]), 1)
                where[f_] = [round(1000.0 * x, 1) for x in (Mi @ co[i_best])]    # pistol frame, mm: x side, y towards the muzzle, z up
        out[side] = dict(deepest_inside_mm=round(1000.0 * depth_all, 1), verts_deeper_3mm=n3, finger_gap_mm=fingers, deepest_at_mm=where)
    return out


def tail_numbers(co):
    if not TAIL_POLYS or not NOT_TAIL_POLYS:
        return {}
    bt = BVHTree.FromPolygons(co, NOT_TAIL_POLYS, all_triangles=False)
    tt = BVHTree.FromPolygons(co, TAIL_POLYS, all_triangles=False)
    ids = sorted({v_ for pl in TAIL_POLYS for v_ in pl})
    dmin = min(bt.find_nearest(co[i])[3] for i in ids)
    return dict(tail_cut=len(tt.overlap(bt)), tail_min_mm=round(1000.0 * dmin, 1), tail_lowest_z=round(min(co[i].z for i in ids), 3),
                tail_back_most_y=round(min(co[i].y for i in ids), 3), tail_x_range=[round(min(co[i].x for i in ids), 3), round(max(co[i].x for i in ids), 3)])


# ------------------------------------------------------------------ the pistols against the face in the game and ADS camera (image space)
from bpy_extras.object_utils import world_to_camera_view

CAMS = {'game': dict(pivot=1.35, dist=4.4, right=0.35, pitch=15.0, fov=60.0),
        'ots': dict(pivot=1.35, dist=4.4, right=0.60, pitch=15.0, fov=60.0),
        'ads': dict(pivot=1.30, dist=2.4, right=0.58, pitch=15.0, fov=42.0)}


def make_cam(c):
    cd = bpy.data.cameras.new('tmp_cam')
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = deg(c['fov'])
    ob = bpy.data.objects.new('tmp_cam', cd)
    scene.collection.objects.link(ob)
    p = deg(c['pitch'])
    ob.location = (c['right'], -c['dist'] * math.cos(p), c['pivot'] + c['dist'] * math.sin(p))
    ob.rotation_euler = (math.radians(90.0) - p, 0.0, 0.0)
    return ob


def hull2d(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def poly_gap(A, B):
    """distance (px) between two convex polygons, negative if they overlap (SAT, the smallest overlap along an edge normal)"""
    best_sep, best_ovl = -1e9, 1e9
    for P_ in (A, B):
        for i in range(len(P_)):
            x1, y1 = P_[i]
            x2, y2 = P_[(i + 1) % len(P_)]
            nx, ny = y2 - y1, x1 - x2
            ln = math.hypot(nx, ny)
            if ln < 1e-9:
                continue
            nx, ny = nx / ln, ny / ln
            pa = [x * nx + y * ny for x, y in A]
            pb = [x * nx + y * ny for x, y in B]
            sep = max(min(pb) - max(pa), min(pa) - max(pb))
            if sep > 0:
                best_sep = max(best_sep, sep)
            else:
                best_ovl = min(best_ovl, -sep)
    if best_sep > 0:                                                  # separated: the SAT value is a lower bound, refine by point-segment distances
        def pd(p, a, b):
            ax, ay = b[0] - a[0], b[1] - a[1]
            t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / max(ax * ax + ay * ay, 1e-12)))
            return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)
        d = min(min(pd(p, B[i], B[(i + 1) % len(B)]) for p in A for i in range(len(B))),
                min(pd(p, A[i], A[(i + 1) % len(A)]) for p in B for i in range(len(A))))
        return d
    return -best_ovl


def face_gap(res=(1920, 1080)):
    """per camera and pistol: gap (px at res) between the pistol's silhouette and the head (face mesh + the hair above the chin), < 0 = they
    overlap in the picture (the pistol covers the head or hides behind it); and the visible share of every pistol (rays from the camera to points
    on the camera-facing pistol faces, blocked by body, face or hair)"""
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = res[0], res[1], 100
    dg = bpy.context.evaluated_depsgraph_get()
    head_pts = []
    zc = (arm.matrix_world @ arm.pose.bones[H['head']].head).z - 0.03
    occ_v, occ_p = [], []
    for ob in (body, face, hair):
        if ob is None:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ob.matrix_world
        base = len(occ_v)
        for v in me.vertices:
            w = mw @ v.co
            occ_v.append(w)
            if ob is face or (ob is hair and w.z > zc):
                head_pts.append(w)
        for p in me.polygons:
            if ob is body and p.index in INV:
                continue
            occ_p.append([base + i for i in p.vertices])
        ev.to_mesh_clear()
    occ = BVHTree.FromPolygons(occ_v, occ_p, all_triangles=False)
    out = {}
    for cn, c in CAMS.items():
        cam = make_cam(c)
        bpy.context.view_layer.update()
        cpos = cam.matrix_world.translation.copy()

        def px(w):
            q = world_to_camera_view(scene, cam, w)
            return (q.x * res[0], q.y * res[1])
        hh = hull2d([px(w) for w in head_pts[::3]])
        for side in ('L', 'R'):
            pco, ppolys, _ = pistol_geometry(side)
            ph = hull2d([px(w) for w in pco])
            out['gap_%s_%s' % (cn, side)] = round(poly_gap(ph, hh), 1)
            n_all = n_vis = 0
            for fi, pl in enumerate(ppolys):
                vs = [pco[i] for i in pl]
                ctr = (vs[0] + vs[1] + vs[2] + vs[3]) / 4.0
                bi = fi // 6                                          # create_cube: 8 vertices and 6 faces per box
                bctr = sum(pco[8 * bi:8 * bi + 8], Vector()) / 8.0
                nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0]).normalized()
                if nrm.dot(ctr - bctr) < 0:
                    nrm = -nrm
                if nrm.dot(cpos - ctr) <= 0:
                    continue
                for a_ in (0.2, 0.5, 0.8):
                    for b_ in (0.2, 0.5, 0.8):
                        s_ = vs[0].lerp(vs[1], a_).lerp(vs[3].lerp(vs[2], a_), b_)
                        d_ = s_ - cpos
                        hit = occ.ray_cast(cpos, d_.normalized(), d_.length - 0.002)
                        n_all += 1
                        if hit[0] is None:
                            n_vis += 1
            out['visible_%s_%s' % (cn, side)] = round(n_vis / max(n_all, 1), 2)
        bpy.data.objects.remove(cam, do_unlink=True)
    return out


# ------------------------------------------------------------------ fit: elbow swivel per side (20 mm), A1's left high guard by search
PHI_MAX = 80.0


def fit_side(V, phi, side):
    for it in range(45):
        set_pose(V, phi)
        c = clearance_exact()
        if side_ok(c[side]) or phi[side] >= PHI_MAX:
            return phi, c
        phi[side] = min(PHI_MAX, phi[side] + 2.0)
    return phi, c


def grip_of(V, phi):
    Q_, hl_, D_, P_, info_ = compute_pose(V, phi)
    return {s: pistol_frame(D_, P_, s).translation.copy() for s in ('L', 'R')}, info_


poses = {}
search = {}
for key, V in VARIANTS.items():
    phi = {s: float(V['phi0'][s]) for s in ('L', 'R')}
    if 'guard' not in V:
        for s in ('R', 'L'):
            phi, c = fit_side(V, phi, s)
    else:
        phi, c = fit_side(V, phi, 'R')                                # the leading arm first; the left guard is placed against its pistol
        g = V['guard']
        G, _ = grip_of(V, phi)
        best, tried = None, []
        for behind in g['behind']:
            target = Vector((G['R'].x - g['left'], G['R'].y - behind, g['grip_z']))
            for phl in range(0, 81, 4):
                ph = dict(phi, L=float(phl))
                W = target - Vector((0.0, 0.058, -0.010))
                for _ in range(3):                                    # wrist target from the wanted grip centre
                    V['wrist_world'] = {'L': W}
                    Gq, inf = grip_of(V, ph)
                    W = W + (target - Gq['L'])
                V['wrist_world'] = {'L': W}
                Gq, inf = grip_of(V, ph)
                ww = inf['L']['wrist_want']
                tried.append((behind, phl, round(ww, 1)))
                if ww > WR_MAX:
                    continue
                set_pose(V, ph)
                cL = clearance_exact()['L']
                if side_ok(cL):
                    best = (behind, phl, W.copy(), ww, cL)
                    break
            if best:
                break
        if best is None:                                              # nothing holds every rule: keep the spec offset and the least wrist bend
            b0 = g['behind'][0]
            cand = [t for t in tried if t[0] == b0]
            b_, phl_, ww_ = min(cand, key=lambda t: t[2])
            target = Vector((G['R'].x - g['left'], G['R'].y - b0, g['grip_z']))
            ph = dict(phi, L=float(phl_))
            W = target - Vector((0.0, 0.058, -0.010))
            for _ in range(3):
                V['wrist_world'] = {'L': W}
                Gq, inf = grip_of(V, ph)
                W = W + (target - Gq['L'])
            V['wrist_world'] = {'L': W}
            phi = ph
            search[key] = dict(found=False, behind=b0, phi_L=phl_, wrist_want=ww_, note='no swivel keeps the wrist <= 35 deg at any offset')
        else:
            phi = dict(phi, L=float(best[1]))
            V['wrist_world'] = {'L': best[2]}
            search[key] = dict(found=True, behind=best[0], phi_L=best[1], wrist_want=round(best[3], 1),
                               first_ok_at_spec=(best[0] == g['behind'][0]))
        search[key]['wrist_want_min_per_behind'] = {str(b): min(t[2] for t in tried if t[0] == b) for b in sorted({t[0] for t in tried})}
        log('A1 left guard search:', json.dumps(search[key]))
    set_pose(V, phi)
    c = clearance_exact()
    poses[key] = phi
    log('variant %s: elbow swivel L %.1f R %.1f deg; clearance L %s / R %s' % (
        key, phi['L'], phi['R'], {k: (round(v, 4) if isinstance(v, float) else v) for k, v in c['L'].items()},
        {k: (round(v, 4) if isinstance(v, float) else v) for k, v in c['R'].items()}))


# ------------------------------------------------------------------ keys
def key_action(Qd, hips_loc, names, act_name, with_hips_loc):
    ad = arm.animation_data_create()
    ad.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    for f in (0, 1):
        for n in names:
            pb = arm.pose.bones[n]
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
for key, V in VARIANTS.items():
    Q, hl, D, P, info = compute_pose(V, poses[key])
    acts[key] = key_action(Q, hl, UPPER, 'Yoru_Aim_r3b_' + key, False)
    if 'Stand' not in acts:
        acts['Stand'] = key_action(Q, hl, STAND, 'Yoru_Aim_r3b_Stand', True)
    acts['full_' + key] = key_action(Q, hl, UPPER + STAND, 'Yoru_Aim_r3b_full_' + key, True)
ad = arm.animation_data
trk = ad.nla_tracks.new()
trk.name = 'Stand'
strip = trk.strips.new(acts['Stand'].name, 0, acts['Stand'])
if hasattr(strip, 'action_slot') and strip.action_slot is None and len(acts['Stand'].slots):
    strip.action_slot = acts['Stand'].slots[0]
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

# ------------------------------------------------------------------ numbers through the saved full actions
numbers = {'date': '2026-10-30', 'round': '3b', 'model': os.path.basename(GLB), 'aim_point': list(AIM_POINT), 'clear_needed_mm': 1000 * CLEAR,
           'wrist_max_deg': WR_MAX, 'stance': STANCES['L'], 'trunk': TRUNK, 'ears_back_deg': EARS_BACK, 'tail': TAIL_DIRS,
           'grip': {'GRIP': GRIP, 'GRIP_SPREAD': GRIP_SPREAD, 'THUMB': THUMB, 'GRIP_AT': GRIP_AT}, 'a1_guard_search': search,
           'actions': {k: a.name for k, a in acts.items()}, 'layer_bones': UPPER, 'stand_bones': STAND, 'variants': {}}
for key, V in VARIANTS.items():
    use_action(acts['full_' + key])
    Q, hl, D, P, info = compute_pose(V, poses[key])
    err = max(min(a_, 2.0 * math.pi - a_) for a_ in ((arm.pose.bones[n].matrix.to_quaternion() @ R[n].inverted()).rotation_difference(D[n]).angle
                                                    for n in UPPER + STAND))
    perr = max((arm.matrix_world @ arm.pose.bones[n].head - P[n]).length for n in UPPER + STAND)
    g, both, trunk, legs = geometry(D, P, info)
    co = body_coords()
    c = clearance_exact(co)
    for s in ('L', 'R'):
        r = c[s]
        g[s]['clearance_mm'] = dict(forearm_hand=round(1000 * r['min'], 1), forearm_hand_where=r['min_part'][:2] if r['min_part'] else None,
                                    upper_arm_elbow_end=round(1000 * r['up_min'], 1), upper_arm_whole=round(1000 * r['up_min_all'], 1),
                                    pistol=round(1000 * r['pistol_min'], 1), pistol_to_other_side=round(1000 * r['pistol_other_min'], 1),
                                    cuts=dict(arm=r['cut'], pistol=r['pistol_cut'], pistol_other=r['pistol_other_cut']))
        g[s]['cant_wanted'] = round(-V['cant_in'][s], 1)
    if 'guard' in V:
        gR, gL = Vector(g['R']['grip_world']), Vector(g['L']['grip_world'])
        both['left_pistol_vs_right'] = dict(behind_m=round(gR.y - gL.y, 3), left_m=round(gR.x - gL.x, 3), below_m=round(gR.z - gL.z, 3))
    fg = face_gap()
    tl = tail_numbers(co)
    layer_err = None
    use_action(acts[key])
    layer_err = max((arm.matrix_world @ arm.pose.bones[n].head - P[n]).length for n in UPPER + STAND)
    numbers['variants'][key] = dict(label=V['label'], input=dict(wrist=V['wrist'], wrist_world_L=[round(x, 4) for x in V['wrist_world']['L']]
                                                                if 'wrist_world' in V else None, clav=V['clav'], cant_in=V['cant_in'], phi=poses[key]),
                                    arms=g, both=both, trunk=trunk, legs=legs, cameras=fg, tail=tl,
                                    check=dict(file_vs_solver_rot_deg=round(math.degrees(err), 3), file_vs_solver_pos_mm=round(1000 * perr, 2),
                                               layer_plus_nla_vs_full_mm=round(1000 * layer_err, 2)))
    log('NUMBERS', key, json.dumps(numbers['variants'][key]))
json.dump(numbers, open(os.path.join(OUT, 'Yoru_Aim_r3b_numbers.json'), 'w'), indent=1, default=str)
use_action(acts['A1'])
bpy.context.preferences.filepaths.save_version = 0
path = os.path.join(OUT, 'Yoru_Aim_r3b.blend')
bpy.ops.wm.save_as_mainfile(filepath=path)
log('saved', path, '| actions', ', '.join(a.name for a in acts.values()))
log('DONE')
