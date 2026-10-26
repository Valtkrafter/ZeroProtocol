"""
Yoru - IDLE v2, round 1: three STAND candidates as stills (one pose each, no animation, no keys).

Library without side effects on import.  The live session (MCP, the user's Blender) runs it with exec() and calls the functions step by step;
the background build calls main() (only when Blender runs with -b).

Method (same as build_idle.py / build_aim_pose.py): a WORLD-space rotation delta D per bone relative to the T-pose, pose basis
Q = R^-1 * D_parent^-1 * D * R; legs and arms by two-bone IK.  Arms, hands, fingers and head targets are given in the rest frame of an upright
torso and carried by the upper chest; the tail is given in the frame of the hips.  So everything except the STANCE (pelvis, legs, feet)
is the same in every variant, and the variants can be compared by the stance alone.

Background (builds the stage from the model and saves it):
  blender -b --factory-startup --python build_idle_v2_lib.py -- <Yoru_V2.glb> <out .blend> [variants, default A,B,C]
Live:  ns = {}; exec(open(<this file>).read(), ns); ns['import_model'](...), ns['pose_variant'](...), ...
Blender axes for Yoru: +Y forward, her left = -X, up = +Z.  Her right side is +X.

Round 2 (the user chose A): VARIANTS['A2'] + COMMON2 = the corrected stance (calm from behind, no X-leg), relaxed arms that are not mirrored,
a tail that hangs and rolls in at the tip.  Use pose_variant(rig, 'A2', COMMON2).  The loop is built by build_idle_v2_loop.py.
FIX in round 2: the arm checks of round 1 sampled pose_bone.head -> pose_bone.tail, but after the glTF import every bone points UP, so the
samples were not on the arm (arm_segments() now runs from joint to joint, arm_penetration() is a mesh test).  The round 1 poses had the
forearms 7 to 22 mm in the belt gear; Blender/work/Idle_v2/Yoru_Idle_v2_round1.blend is the state of round 1 as it was shown.
"""
import bpy, sys, math, json, struct, os, time
from mathutils import Vector, Quaternion, Euler, Matrix
from mathutils.kdtree import KDTree

GLB_DEFAULT = r'C:\Users\valen\ZeroProtocol\Blender\work\Yoru_V2.glb'
SPACING = 1.2
X_POS = {'A': SPACING, 'B': 0.0, 'C': -SPACING}        # A is on the left in the front three-quarter view (her right side is +X)
COLL = {'A': 'A_Kontrapost', 'B': 'B_Catwalk', 'C': 'C_Kompakt'}


def log(*a):
    print('[idle_v2]', *a, flush=True)


# ------------------------------------------------------------------ math helpers
def deg(x):
    return math.radians(x)


def eul(rx=0.0, ry=0.0, rz=0.0):                                     # degrees about the world axes, X first, then Y, then Z
    return Euler((deg(rx), deg(ry), deg(rz)), 'XYZ').to_quaternion()


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    s = d.cross(n)
    return Matrix((d, n, s)).transposed().to_quaternion()


def aim(rest_dir, rest_nrm, tgt_dir, tgt_nrm):
    """rotation that turns rest_dir into tgt_dir and rest_nrm (as far as it is free) into tgt_nrm"""
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
    K = Hp + u * a + p * h
    return K, Hp + u * d_c, d - d_c


def perp(v, axis):
    """part of v that is perpendicular to the unit vector axis, normalised (None if v is (almost) parallel)"""
    w = v - axis * v.dot(axis)
    return w.normalized() if w.length > 1e-6 else None


def humanoid_map(glb=GLB_DEFAULT):
    with open(glb, 'rb') as f:
        f.read(12)
        clen, _ = struct.unpack('<II', f.read(8))
        js = json.loads(f.read(clen).decode('utf-8'))
    nodes = js['nodes']
    return {h['bone']: nodes[h['node']]['name'] for h in js['extensions']['VRM']['humanoid']['humanBones']}


class Rig:
    def __init__(self, arm, H):
        self.arm, self.H = arm, H
        bones = arm.data.bones
        self.bones = bones
        self.R = {b.name: b.matrix_local.to_quaternion() for b in bones}
        self.HEAD0 = {b.name: b.head_local.copy() for b in bones}
        self.order = []
        q = [b for b in bones if b.parent is None]
        while q:
            b = q.pop(0)
            self.order.append(b.name)
            q.extend(b.children)
        self.tail_bones = [n for n in ('J_Opt_C_CatTail%d_01' % i for i in range(1, 9)) if n in bones]
        self.body = next((c for c in arm.children if c.type == 'MESH' and c.name.startswith('Body')), None)

    def nm(self, side, part):
        return self.H[('left' if side == 'L' else 'right') + part]


FINGERS = ('Index', 'Middle', 'Ring', 'Little')
PARTS = ('Proximal', 'Intermediate', 'Distal')

# ------------------------------------------------------------------ the parts that are THE SAME in every variant
COMMON = dict(
    # spine, organic S: pelvis tipped forward a little, lower back and chest lifted (deg about X, + = top of the bone tips back)
    lean=(-4.0, 3.0, 2.5, 0.5),
    shoulder_drop=4.0,             # clavicle, outer end down (deg): relaxed shoulders, a long neck
    shoulder_back=3.0,             # clavicle, outer end back (deg): open chest, confident
    head_pitch=-2.0,               # head in the world (deg, - = chin a touch down), looks straight ahead in every variant
    neck_share=0.45,               # share of the head correction that the neck takes
    # arms: hang relaxed and close to the gear, a soft bend in the elbow, the hands a little in front of the hips, palms to the thighs.
    # arm_frame 'world': the wrist is an offset from the posed shoulder joint in WORLD axes (relaxed arms hang with gravity),
    #            'chest': offset positions in the rest frame of an upright torso, carried by the upper chest (hands that hold something).
    arm_frame='world',
    wrist={'R': Vector((0.050, 0.100, -0.384)), 'L': Vector((-0.050, 0.100, -0.384))},
    hand_dir={'R': Vector((-0.06, 0.26, -0.96)), 'L': Vector((0.06, 0.26, -0.96))},
    palm={'R': Vector((-1.0, -0.20, 0.0)), 'L': Vector((1.0, -0.20, 0.0))},
    elbow_pole={'R': Vector((0.45, -0.90, 0.0)), 'L': Vector((-0.45, -0.90, 0.0))},
    elbow_out={'R': None, 'L': None},   # if set (deg): the elbow pole turns from straight back (0) to straight out (90)
    wrist_max=40.0,                # the wrist bends at most this much (deg)
    finger_curl={'R': {'Index': (12, 18, 10), 'Middle': (18, 24, 12), 'Ring': (22, 28, 14), 'Little': (26, 30, 16)},
                 'L': {'Index': (12, 18, 10), 'Middle': (18, 24, 12), 'Ring': (22, 28, 14), 'Little': (26, 30, 16)}},
    thumb={'R': (-16.0, -6.0, -6.0), 'L': (-16.0, -6.0, -6.0)},       # proximal opposition (deg about X), intermediate / distal curl
    # tail: slim and calm; leaves the rump backwards, hangs down behind the legs and rolls in to her right at the end (seen from behind a
    # soft J, not a straight line).  Per joint the direction in the hips frame (x her right, y forward, z up); joint 7 has no length.
    tail=[(0.0, -0.97, -0.25), (0.0, -0.80, -0.60), (0.03, -0.45, -0.89), (0.10, -0.18, -0.98),
          (0.60, -0.08, -0.80), (0.95, 0.0, 0.30), (0.95, 0.0, 0.30), (0.10, 0.0, 1.0)],
    tail_scale=0.72,               # same as Unity (YoruSecondaryMotion.tailScale)
)

# hands loosely folded in front of the belly (tried first; the gear in front of the belly pushes the elbows forward and out, it looked meek)
COMMON_FOLDED = dict(COMMON, arm_frame='chest',
                     wrist={'R': Vector((0.035, 0.180, 0.955)), 'L': Vector((0.008, 0.207, 0.985))},
                     hand_dir={'R': Vector((-0.42, 0.20, -0.88)), 'L': Vector((0.66, 0.22, -0.72))},
                     palm={'R': Vector((-0.20, -0.90, 0.15)), 'L': Vector((0.05, -1.0, 0.10))},
                     elbow_pole={'R': Vector((0.55, -0.80, -0.25)), 'L': Vector((-0.55, -0.80, -0.25))},
                     elbow_out={'R': 80, 'L': 90}, wrist_max=55.0,
                     finger_curl={'R': {'Index': (16, 22, 14), 'Middle': (22, 28, 16), 'Ring': (26, 32, 18), 'Little': (30, 34, 20)},
                                  'L': {'Index': (34, 44, 24), 'Middle': (44, 54, 30), 'Ring': (50, 58, 32), 'Little': (54, 60, 34)}},
                     thumb={'R': (-22.0, -8.0, -8.0), 'L': (-40.0, -14.0, -12.0)})


# ------------------------------------------------------------------ round 2: the user chose A ("von hinten komisch", "Arme steif") -> A2
def tail_dirs_r2(curl_side=1.0, curl=1.0):
    """slim tail, hangs down the middle behind the legs and rolls in only below the belt pouches (a small, low hook, no second line up).
    curl_side +1 = the tip rolls towards her right, -1 = left; curl 0..1 = how far the tip rolls in."""
    s = curl_side
    return [(0.0, -1.0, -0.10), (0.0, -0.90, -0.44), (0.0, -0.55, -0.83), (0.02 * s, -0.20, -0.98),
            (0.04 * s, 0.0, -1.0), (0.40 * s * curl, 0.12, -0.91), (0.40 * s * curl, 0.12, -0.91), (0.85 * s * curl, 0.35, 0.20 * curl - 0.6 * (1.0 - curl))]


COMMON2 = dict(COMMON,
               # arms NOT mirrored: the elbows bow out a little (the gear holds them), the forearms come back in and a little forward, so from
               # behind each arm shows a soft bend.  The standing-leg side (right) rests against the jutting hip, the free side hangs further forward.
               # (searched against the gear with the mesh test: the forearms pass just in front of the belt pouches; wider would look spread,
               #  lower would push the forearm into the pouches)
               wrist={'R': Vector((0.100, 0.110, -0.370)), 'L': Vector((-0.085, 0.150, -0.370))},
               elbow_pole={'R': Vector((0.819, -0.574, 0.0)), 'L': Vector((-0.819, -0.574, 0.0))},     # 55 deg from straight back towards out
               palm={'R': Vector((-1.0, -0.40, 0.0)), 'L': Vector((1.0, -0.40, 0.0))},
               hand_rel={'R': (6.0, 4.0), 'L': (8.0, 5.0)},            # wrist relative to the forearm: towards the palm, towards the little finger (deg)
               wrist_max=40.0,
               finger_curl={'R': {'Index': (10, 18, 12), 'Middle': (16, 26, 16), 'Ring': (20, 30, 18), 'Little': (26, 34, 20)},
                            'L': {'Index': (14, 22, 14), 'Middle': (20, 30, 18), 'Ring': (24, 34, 20), 'Little': (30, 38, 22)}},
               thumb={'R': (-18.0, -10.0, -8.0), 'L': (-22.0, -12.0, -10.0)},
               shoulder_drop_side={'L': 3.5, 'R': 4.5},                # the shoulder over the standing leg sits a little lower
               # tail: hangs calm down the middle and rolls in only at the tip, low enough that the roll lies on the dark stocking and not on
               # the light skin band between shorts and stockings (white on skin read as a muddle from behind; a roll right under the rump and
               # C-shapes to either side were tried).  A hanging tail also shows the slow S-sway of the idle.
               tail=[(0.0, -1.0, -0.10), (0.0, -0.90, -0.44), (0.0, -0.50, -0.87), (0.02, -0.12, -0.99), (0.06, 0.02, -1.0),
                     (0.55, 0.10, -0.83), (0.55, 0.10, -0.83), (0.75, 0.20, 0.62)])


def _arm_candidates_r2():
    """round 2: the hand may go forward (in front of the hip gear) before it goes out to the side"""
    out = []
    for o in (0.0, 0.01, 0.02, 0.03, 0.04, 0.05):
        for f in (0.0, 0.01, 0.02, 0.03, 0.04, 0.05):
            for u in (0.0, 0.015, 0.03):
                out.append((o + 0.4 * f + 0.7 * u, dict(out=o, fwd=f, up=u)))
    out.sort(key=lambda t: t[0])
    return [c for _, c in out]


ARM_CANDIDATES_R2 = _arm_candidates_r2()

# ------------------------------------------------------------------ the STANCE variants (the only thing that differs)
# hips: shift (x = her right, y = forward, m), drop (m), per torso bone hips/spine/chest/upperChest an extra lean (about X), roll (about Y,
#       + = her right side down) and yaw (about Z, + = her right side forward).
# foot[side]: (x, y) of the toe joint (ball of the foot) on the ground in m (rest: x +-0.075, y 0.075), toe-out in deg, heel lift in deg.
# knee[side]: pole direction of the knee.
VARIANTS = {
    'A': dict(label='A  Kontrapost (Gewicht rechts)',
              shift=(0.054, 0.0), drop=0.015,
              lean=(0.0, 0.0, 0.0, 0.0), roll=(-7.0, 4.5, 3.5, 2.0), yaw=(-5.0, 2.0, 2.0, 1.0),
              foot={'R': (0.062, 0.070, 10.0, 0.0), 'L': (-0.058, 0.170, 4.0, 18.0)},
              knee={'R': Vector((0.10, 1.0, 0.0)), 'L': Vector((0.55, 1.0, 0.0))}),
    'B': dict(label='B  Catwalk (Fuesse hintereinander)',
              shift=(0.022, -0.015), drop=0.017,
              lean=(0.0, 0.0, 0.0, 0.0), roll=(-2.5, 1.5, 1.0, 0.5), yaw=(-12.0, 3.0, 3.0, 2.0),
              foot={'R': (0.040, 0.000, 30.0, 0.0), 'L': (0.000, 0.200, 0.0, 8.0)},
              knee={'R': Vector((0.45, 1.0, 0.0)), 'L': Vector((0.30, 1.0, 0.0))}),
    'C': dict(label='C  Kompakt (Fuesse eng, mittig)',
              shift=(0.0, 0.0), drop=0.008,
              lean=(0.0, 0.0, 0.0, 0.0), roll=(0.0, 0.0, 0.0, 0.0), yaw=(0.0, 0.0, 0.0, 0.0),
              foot={'R': (0.058, 0.085, 7.0, 0.0), 'L': (-0.058, 0.070, 7.0, 0.0)},
              knee={'R': Vector((0.05, 1.0, 0.0)), 'L': Vector((-0.05, 1.0, 0.0))}),
}

# round 2: the corrected A (calmer from behind).  Used with COMMON2.
VARIANTS['A2'] = dict(label='A2  Kontrapost ruhig (Gewicht rechts)',
                      shift=(0.040, 0.0), drop=0.013,
                      lean=(0.0, 0.0, 0.0, 0.0), roll=(-4.5, 3.0, 2.5, 1.2), yaw=(-4.0, 1.5, 1.5, 1.0),
                      # the free (left) foot stands under its own hip, the knee bends forward (no X-leg), the heel is only a little lifted
                      foot={'R': (0.080, 0.066, 11.0, 0.0), 'L': (-0.050, 0.140, 8.0, 5.0)},
                      knee={'R': Vector((0.08, 1.0, 0.0)), 'L': Vector((0.15, 1.0, 0.0))})
COLL['A2'] = 'A2_Kontrapost'
X_POS['A2'] = 2.4


# ------------------------------------------------------------------ pose solver
def compute_pose(rig, V, C=COMMON):
    """returns Q (basis rotation per bone), hips location (bone frame), D (world deltas), P (posed joint heads, armature space), diag"""
    H, R, HEAD0, nm = rig.H, rig.R, rig.HEAD0, rig.nm
    rel, absd = {}, {}
    torso = (H['hips'], H['spine'], H['chest'], H['upperChest'])
    for i, b in enumerate(torso):
        rel[b] = eul(rx=C['lean'][i] + V['lean'][i], ry=V['roll'][i], rz=V['yaw'][i])
    for side, sx in (('L', -1.0), ('R', 1.0)):
        s_drop = C.get('shoulder_drop_side', {}).get(side, C['shoulder_drop'])
        rel[nm(side, 'Shoulder')] = eul(ry=sx * s_drop, rz=-sx * C['shoulder_back'])
        for fn in FINGERS:
            for part, c in zip(PARTS, C['finger_curl'][side][fn]):
                rel[nm(side, fn + part)] = Quaternion((0, 1, 0), deg(sx * c))
        t1, t2, t3 = C['thumb'][side]
        rel[nm(side, 'ThumbProximal')] = eul(rx=t1)
        rel[nm(side, 'ThumbIntermediate')] = eul(rz=sx * t2)          # t < 0: the tip turns towards the fingers
        rel[nm(side, 'ThumbDistal')] = eul(rz=sx * t3)
    rel.update(C.get('extra_rel', {}))                               # round 2: hair, ears, bust (small rotations relative to the parent)
    hips_d = Vector((V['shift'][0], V['shift'][1], -V['drop']))
    head_abs = eul(rx=C['head_pitch'], ry=C.get('head_roll', 0.0), rz=C.get('head_yaw', 0.0))

    D, Q, P, legs, aik = {}, {}, {}, {}, {}
    diag = {'leg_deficit': {}, 'arm_deficit': {}, 'wrist_bend': {}}
    hips_name = H['hips']
    for name in rig.order:
        b = rig.bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        P[name] = HEAD0[name].copy() if parent is None else P[parent] + D[parent] @ (HEAD0[name] - HEAD0[parent])
        if name == hips_name:
            P[name] = P[name] + hips_d
        D[name] = Dp @ rel[name] if name in rel else Dp.copy()
        if name == H['neck']:
            D[name] = Dp.slerp(head_abs, C['neck_share'])
        elif name == H['head']:
            D[name] = head_abs.copy()
        elif name in rig.tail_bones:
            i = rig.tail_bones.index(name)
            dvec = Vector(C['tail'][i]).normalized()
            D[name] = D[hips_name] @ Vector((0.0, -1.0, 0.0)).rotation_difference(dvec)
        for side, sx in (('L', -1.0), ('R', 1.0)):
            if name == nm(side, 'UpperLeg'):
                fx, fy, toe_out, heel = V['foot'][side]
                # toe-out: the right foot turns towards +X (rz < 0), the left towards -X (rz > 0); heel lift = toes down (rx < 0)
                d_foot = eul(rz=(-toe_out if side == 'R' else toe_out)) @ eul(rx=-heel)
                T0 = HEAD0[nm(side, 'Toes')]
                A0 = HEAD0[nm(side, 'Foot')]
                ball = Vector((fx, fy, T0.z))
                ankle = ball + d_foot @ (A0 - T0)
                Hp = P[name]
                K0 = HEAD0[nm(side, 'LowerLeg')]
                L1, L2 = (K0 - HEAD0[name]).length, (A0 - K0).length
                K, Teff, deficit = two_bone_ik(Hp, ankle, V['knee'][side], L1, L2)
                diag['leg_deficit'][side] = deficit
                foot_fwd = d_foot @ Vector((0.0, 1.0, 0.0))
                foot_fwd.z = 0.0
                foot_fwd.normalize()
                dth = (K - Hp).normalized()
                dsh = (Teff - K).normalized()
                knee_face = perp(V['knee'][side].normalized(), dth) or perp(foot_fwd, dth)
                shin_face = perp(knee_face.lerp(foot_fwd, 0.5), dsh) or knee_face
                legs[side] = (K, Teff, d_foot, dsh, shin_face)
                D[name] = aim((K0 - HEAD0[name]).normalized(), Vector((0, 1, 0)), dth, knee_face)
            elif name == nm(side, 'LowerLeg'):
                K, Teff, d_foot, dsh, shin_face = legs[side]
                A0 = HEAD0[nm(side, 'Foot')]
                D[name] = aim((A0 - HEAD0[name]).normalized(), Vector((0, 1, 0)), dsh, shin_face)
            elif name == nm(side, 'Foot'):
                D[name] = legs[side][2].copy()
            elif name == nm(side, 'Toes'):
                fx, fy, toe_out, heel = V['foot'][side]
                D[name] = eul(rz=(-toe_out if side == 'R' else toe_out))       # toes stay flat on the ground
            elif name == nm(side, 'UpperArm'):
                S = P[name]
                adj = V.get('arm_adj', {}).get(side, {})
                move = Vector((sx * adj.get('out', 0.0), adj.get('fwd', 0.0), adj.get('up', 0.0)))
                if C.get('arm_frame', 'chest') == 'world':
                    Dc = Quaternion()
                    T = S + C['wrist'][side] + move + C.get('wrist_extra', {}).get(side, Vector((0.0, 0.0, 0.0)))
                else:
                    Dc = D[H['upperChest']]
                    Pc = P[H['upperChest']]
                    Hc0 = HEAD0[H['upperChest']]
                    T = Pc + Dc @ (C['wrist'][side] + move - Hc0)
                L1 = (HEAD0[nm(side, 'LowerArm')] - HEAD0[name]).length
                L2 = (HEAD0[nm(side, 'Hand')] - HEAD0[nm(side, 'LowerArm')]).length
                pole = C['elbow_pole'][side]
                e_out = adj.get('elbow_out', C.get('elbow_out', {}).get(side))
                if e_out is not None:
                    phi = deg(e_out)
                    pole = Vector((sx * math.sin(phi), -math.cos(phi), -0.25))
                K, Teff, deficit = two_bone_ik(S, T, Dc @ pole, L1, L2)
                diag['arm_deficit'][side] = deficit
                du, df = (K - S).normalized(), (Teff - K).normalized()
                palm = (Dc @ C['palm'][side]).normalized()
                if C.get('hand_rel'):
                    # round 2: the hand follows the forearm and bends relative to it (relaxed: a little towards the palm and the little finger)
                    flex, dev = C['hand_rel'][side]
                    n_f = perp(palm, df) or perp(Vector((0, 0, -1)), df)
                    ulnar = sx * n_f.cross(df)
                    dh = (df * (math.cos(deg(flex)) * math.cos(deg(dev))) + n_f * math.sin(deg(flex)) + ulnar * math.sin(deg(dev))).normalized()
                else:
                    dh = (Dc @ C['hand_dir'][side]).normalized()
                ang = df.angle(dh)
                if ang > deg(C['wrist_max']):
                    dh = df.slerp(dh, deg(C['wrist_max']) / ang)
                diag['wrist_bend'][side] = math.degrees(df.angle(dh))
                biceps = perp(df, du) or perp(Vector((0, 1, 0)), du)
                aik[side] = (df, dh, palm)
                D[name] = aim(Vector((sx, 0, 0)), Vector((0, 1, 0)), du, biceps)
            elif name == nm(side, 'LowerArm'):
                df, dh, palm = aik[side]
                n_f = perp(palm, df) or perp(Vector((0, 0, -1)), df)
                D[name] = aim(Vector((sx, 0, 0)), Vector((0, 0, -1)), df, n_f)
            elif name == nm(side, 'Hand'):
                df, dh, palm = aik[side]
                n_h = perp(palm, dh) or perp(Vector((0, 0, -1)), dh)
                D[name] = aim(Vector((sx, 0, 0)), Vector((0, 0, -1)), dh, n_h)
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    hips_loc = R[hips_name].inverted() @ hips_d
    return Q, hips_loc, D, P, diag


def apply_pose(rig, Q, hips_loc, tail_scale=1.0):
    arm = rig.arm
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Q.get(pb.name, Quaternion())
        pb.location = Vector()
        pb.scale = Vector((1.0, 1.0, 1.0))
    arm.pose.bones[rig.H['hips']].location = hips_loc
    if rig.tail_bones:
        arm.pose.bones[rig.tail_bones[0]].scale = Vector((tail_scale,) * 3)
    bpy.context.view_layer.update()


def pose_variant(rig, key, C=COMMON, V=None):
    V = V or VARIANTS[key]
    Q, hips_loc, D, P, diag = compute_pose(rig, V, C)
    apply_pose(rig, Q, hips_loc, C['tail_scale'])
    return D, P, diag


# ------------------------------------------------------------------ checks (numbers only, armature space)
_VIS = bpy.app.driver_namespace.setdefault('yoru_idle_v2_vis', {})       # survives between the live calls


def visible_vertices(body):
    """vertices that belong to at least one visible polygon (the alpha of the texture cuts away a long coat hem of the outfit)"""
    key = body.data.name
    if key in _VIS:
        return _VIS[key]
    import numpy as np
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
    vis = [False] * len(me.vertices)
    for poly in me.polygons:
        im = imgs.get(poly.material_index)
        if im is not None:
            px, w_, h_ = im
            a_ = 0.0
            for li in poly.loop_indices:
                u_, v_ = uv[li].uv
                a_ += px[int(min(max(v_, 0.0), 0.9999) * h_), int(min(max(u_, 0.0), 0.9999) * w_)]
            if a_ / len(poly.loop_indices) < 0.3:
                continue
        for vi in poly.vertices:
            vis[vi] = True
    _VIS[key] = vis
    return vis


def vertex_groups_by_bone(rig):
    """dominant bone per vertex of the body"""
    body = rig.body
    names = {vg.index: vg.name for vg in body.vertex_groups}
    dom = []
    for v in body.data.vertices:
        if not v.groups:
            dom.append('')
            continue
        g = max(v.groups, key=lambda g: g.weight)
        dom.append(names.get(g.group, ''))
    return dom


def evaluated_coords(body):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    co = [v.co.copy() for v in me.vertices]
    ev.to_mesh_clear()
    return co


def side_chain(rig, side):
    s = 'L' if side == 'L' else 'R'
    out = set()
    for part in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes'):
        out.add(rig.nm(s, part))
    return out


def run_checks(rig):
    """arms vs torso / thighs, hand-to-hand gap, leg vs leg, soles on the ground, tail vs body.  Distances in m (negative = inside)."""
    H, nm = rig.H, rig.nm
    body = rig.body
    vis = visible_vertices(body)
    dom = _DOM.get(body.data.name) or _DOM.setdefault(body.data.name, vertex_groups_by_bone(rig))
    co = evaluated_coords(body)
    torso_like = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg']}
    solid = [i for i, n in enumerate(dom) if vis[i] and (n in torso_like or (n.startswith('J_Sec_') and 'Hair' not in n))]
    kd = KDTree(len(solid))
    for k, i in enumerate(solid):
        kd.insert(co[i], k)
    kd.balance()
    res = {}
    pbs = rig.arm.pose.bones
    for side in ('L', 'R'):
        worst = 9.0
        for part, h, tl, r, i0 in arm_segments(rig, side):
            for i in range(i0, 9):
                _, _, dist = kd.find(h.lerp(tl, i / 8.0))
                worst = min(worst, dist - r)
        res['arm_clear_' + side] = worst
    # hands: gap between the left and the right hand mesh (should be about 0: touching, not deep inside)
    hand_bones = {}
    for side in ('L', 'R'):
        s = {nm(side, 'Hand')}
        for fn in FINGERS:
            for part in PARTS:
                s.add(nm(side, fn + part))
        for part in ('ThumbProximal', 'ThumbIntermediate', 'ThumbDistal'):
            s.add(nm(side, part))
        hand_bones[side] = s
    hl = [i for i, n in enumerate(dom) if n in hand_bones['L']]
    hr = [i for i, n in enumerate(dom) if n in hand_bones['R']]
    kdr = KDTree(len(hr))
    for k, i in enumerate(hr):
        kdr.insert(co[i], k)
    kdr.balance()
    res['hand_gap'] = min(kdr.find(co[i])[2] for i in hl)
    # legs: the closest vertices of the left and the right leg chain (knees, shins, shoes must not touch)
    ll = [i for i, n in enumerate(dom) if vis[i] and n in side_chain(rig, 'L')]
    lr = [i for i, n in enumerate(dom) if vis[i] and n in side_chain(rig, 'R')]
    kdl = KDTree(len(lr))
    for k, i in enumerate(lr):
        kdl.insert(co[i], k)
    kdl.balance()
    best = (9.0, None)
    for i in ll:
        if co[i].z > 0.62:                   # below the thigh gear (the thighs may touch at the top, that is normal)
            continue
        _, j, dist = kdl.find(co[i])
        if dist < best[0]:
            best = (dist, tuple(round(x, 3) for x in co[i]))
    res['leg_gap'] = best[0]
    res['leg_gap_at'] = best[1]
    # soles: lowest point of each shoe and of its heel / toe part
    for side in ('L', 'R'):
        ids = [i for i, n in enumerate(dom) if vis[i] and n in (nm(side, 'Foot'), nm(side, 'Toes'))]
        zs = [co[i].z for i in ids]
        res['sole_min_' + side] = min(zs)
        toe_ids = [i for i in ids if dom[i] == nm(side, 'Toes')]
        res['toe_min_' + side] = min(co[i].z for i in toe_ids) if toe_ids else None
    # tail against hips, legs and coat
    tail_set = set(rig.tail_bones)
    tail_ids = [i for i, n in enumerate(dom) if n in tail_set and n not in rig.tail_bones[:2]]
    obst_bones = {H['hips'], H['spine'], H['leftUpperLeg'], H['rightUpperLeg'], H['leftLowerLeg'], H['rightLowerLeg'], H['leftFoot'], H['rightFoot']}
    obst = [i for i, n in enumerate(dom) if vis[i] and (n in obst_bones or n.startswith('J_Sec_L_Coat') or n.startswith('J_Sec_R_Coat'))]
    kdo = KDTree(len(obst))
    for k, i in enumerate(obst):
        kdo.insert(co[i], k)
    kdo.balance()
    best = (9.0, None)
    for i in tail_ids:
        _, _, dist = kdo.find(co[i])
        if dist < best[0]:
            best = (dist, tuple(round(x, 3) for x in co[i]))
    res['tail_gap'] = best[0]
    res['tail_gap_at'] = best[1]
    # centre of the feet vs pelvis / head (balance, x = her right)
    res['hips_x'] = pbs[H['hips']].head.x
    res['head_x'] = pbs[H['head']].head.x
    res['ankle_R'] = tuple(round(x, 3) for x in pbs[nm('R', 'Foot')].head)
    res['ankle_L'] = tuple(round(x, 3) for x in pbs[nm('L', 'Foot')].head)
    return res


def arm_segments(rig, side):
    """the arm as capsules from joint to joint (posed heads).  NOTE: after the glTF import every bone points UP (+Z of the rest pose), so
    pose_bone.tail is NOT on the limb; the segments must run from a joint to the next joint.  (part, start, end, radius, first sample of 8)"""
    pbs, nm = rig.arm.pose.bones, rig.nm
    sh, el, wr = pbs[nm(side, 'UpperArm')].head, pbs[nm(side, 'LowerArm')].head, pbs[nm(side, 'Hand')].head
    kn = pbs[nm(side, 'MiddleProximal')].head
    tip = kn + (kn - wr).normalized() * 0.05
    return [('UpperArm', sh.copy(), el.copy(), 0.040, 3), ('LowerArm', el.copy(), wr.copy(), 0.033, 0),
            ('Hand', wr.copy(), kn.copy(), 0.022, 0), ('Fingers', kn.copy(), tip, 0.014, 1)]


def arm_clearance(rig):
    """least clearance (m) of the arm capsules to the visible torso / thigh / gear vertices, per side (negative = inside)"""
    H, nm = rig.H, rig.nm
    vis = visible_vertices(rig.body)
    dom = _DOM.get(rig.body.data.name) or _DOM.setdefault(rig.body.data.name, vertex_groups_by_bone(rig))
    co = evaluated_coords(rig.body)
    torso_like = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg']}
    solid = [i for i, n in enumerate(dom) if vis[i] and (n in torso_like or (n.startswith('J_Sec_') and 'Hair' not in n))]
    kd = KDTree(len(solid))
    for k, i in enumerate(solid):
        kd.insert(co[i], k)
    kd.balance()
    out = {}
    for side in ('L', 'R'):
        worst = (9.0, '')
        for part, h, tl, r, i0 in arm_segments(rig, side):
            for i in range(i0, 9):
                _, _, dist = kd.find(h.lerp(tl, i / 8.0))
                if dist - r < worst[0]:
                    worst = (dist - r, '%s %d/8' % (part, i))
        out[side] = worst
    return out


_DOM = bpy.app.driver_namespace.setdefault('yoru_idle_v2_dom', {})


def arm_penetration(rig, t_min=0.6):
    """mesh test: how deep the visible arm / hand vertices sit behind the surface of the torso, thighs and gear (m, 0 = nothing inside).
    A vertex counts as inside when it lies on the back side of its nearest body vertex (normal), closer than 3 cm.
    The upper arm counts only beyond t_min of its length (the armpit end touches the side of the vest by nature, covered by the arm)."""
    H, nm = rig.H, rig.nm
    body = rig.body
    vis = visible_vertices(body)
    dom = _DOM.get(body.data.name) or _DOM.setdefault(body.data.name, vertex_groups_by_bone(rig))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    co = [v.co.copy() for v in me.vertices]
    nrm = [v.normal.copy() for v in me.vertices]
    ev.to_mesh_clear()
    torso_like = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg']}
    solid = [i for i, n in enumerate(dom) if vis[i] and (n in torso_like or (n.startswith('J_Sec_') and 'Hair' not in n))]
    kd = KDTree(len(solid))
    for k, i in enumerate(solid):
        kd.insert(co[i], k)
    kd.balance()
    out = {}
    from mathutils.geometry import intersect_point_line
    pbs = rig.arm.pose.bones
    for side in ('L', 'R'):
        bones_side = {nm(side, p) for p in ('LowerArm', 'Hand')} | {nm(side, f + p) for f in FINGERS for p in PARTS} | \
                     {nm(side, p) for p in ('ThumbProximal', 'ThumbIntermediate', 'ThumbDistal')}
        ids = [i for i, n in enumerate(dom) if vis[i] and n in bones_side]
        # the elbow end of the upper arm too (the armpit end touches the vest by nature and is hidden)
        sh, el = pbs[nm(side, 'UpperArm')].head, pbs[nm(side, 'LowerArm')].head
        for i, n in enumerate(dom):
            if vis[i] and n == nm(side, 'UpperArm'):
                _, t = intersect_point_line(co[i], sh, el)
                if t > t_min:
                    ids.append(i)
        deepest, where = 0.0, None
        deep_upper, deep_lower, where_lower = 0.0, 0.0, None
        for i in ids:
            _, k, dist = kd.find(co[i])
            if dist > 0.03:
                continue
            s = solid[k]
            depth = -(co[i] - co[s]).dot(nrm[s])
            if dom[i] == nm(side, 'UpperArm'):
                deep_upper = max(deep_upper, depth)
            elif depth > deep_lower:
                deep_lower = depth
                where_lower = (tuple(round(x, 3) for x in co[i]), dom[i], dom[s])
            if depth > deepest:
                deepest, where = depth, (tuple(round(x, 3) for x in co[i]), dom[i], dom[s])
        # (deepest of all, where, elbow half of the upper arm, forearm / hand / fingers, where the forearm / hand is deepest)
        out[side] = (deepest, where, deep_upper, deep_lower, where_lower)
    return out


def _arm_candidates():
    """hand moves: out to the side, forward, up (= a little more bend in the elbow, so the elbow can leave the waist); cheapest first"""
    out = []
    for o in (0.0, 0.01, 0.02, 0.03, 0.04, 0.05):
        for f in (0.0, 0.01, 0.02):
            for u in (0.0, 0.015, 0.03):
                out.append((o + 0.5 * f + 0.7 * u, dict(out=o, fwd=f, up=u)))
    out.sort(key=lambda t: t[0])
    return [c for _, c in out]


ARM_CANDIDATES = _arm_candidates()


def fit_arms_variant(rig, key, C=COMMON, V=None, need=0.003, cands=None):
    """per side the smallest change of the hand that keeps the arm clear of the gear in this stance
    (relaxed arms rest against what is there: a hip that juts out pushes the arm out).  Stores the result in V['arm_adj']."""
    V = V if V is not None else VARIANTS[key]
    V['arm_adj'] = {'L': {}, 'R': {}}
    for side in ('L', 'R'):
        chosen, best = None, None
        for cand in (cands or ARM_CANDIDATES):
            V['arm_adj'][side] = dict(cand)
            pose_variant(rig, key, C, V)
            w = arm_clearance(rig)[side]
            if best is None or w[0] > best[0][0]:
                best = (w, cand)
            if w[0] >= need:
                chosen = cand
                break
        V['arm_adj'][side] = dict(chosen if chosen is not None else best[1])
        log('fit arms', key, side, 'adj', V['arm_adj'][side], 'clearance %.4f at %s' % (best[0][0], best[0][1]) if chosen is None else 'ok')
    pose_variant(rig, key, C, V)
    return V['arm_adj']


def fmt_checks(res):
    out = []
    for k, v in res.items():
        if isinstance(v, float):
            out.append('%s %.4f' % (k, v))
        else:
            out.append('%s %s' % (k, v))
    return ', '.join(out)


# ------------------------------------------------------------------ stage helpers (used live and in the background build)
def find_layer_collection(lc, name):
    if lc.name == name:
        return lc
    for c in lc.children:
        r = find_layer_collection(c, name)
        if r:
            return r
    return None


def import_model(coll_name, glb=GLB_DEFAULT):
    scene = bpy.context.scene
    col = bpy.data.collections.get(coll_name) or bpy.data.collections.new(coll_name)
    if col.name not in [c.name for c in scene.collection.children]:
        scene.collection.children.link(col)
    vl = bpy.context.view_layer
    vl.active_layer_collection = find_layer_collection(vl.layer_collection, col.name)
    before = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    new = [o for o in bpy.data.objects if o.name not in before]
    for o in new:
        if o.type == 'MESH' and o.name.startswith('Icosphere'):
            o.hide_viewport = True
            o.hide_render = True
    lc = find_layer_collection(vl.layer_collection, 'glTF_not_exported')
    if lc:
        lc.exclude = True
    arm = next(o for o in new if o.type == 'ARMATURE')
    return arm


def copy_character(src_arm, coll_name, x):
    """a second Yoru: the armature is copied (own pose), the meshes share their data with the original (linked duplicates)"""
    scene = bpy.context.scene
    col = bpy.data.collections.get(coll_name) or bpy.data.collections.new(coll_name)
    if col.name not in [c.name for c in scene.collection.children]:
        scene.collection.children.link(col)
    arm2 = src_arm.copy()
    if src_arm.animation_data:
        arm2.animation_data_clear()
    col.objects.link(arm2)
    for ch in src_arm.children:
        c2 = ch.copy()
        col.objects.link(c2)
        c2.parent = arm2
        c2.matrix_parent_inverse = ch.matrix_parent_inverse.copy()
        for m in c2.modifiers:
            if m.type == 'ARMATURE' and m.object == src_arm:
                m.object = arm2
    arm2.location = Vector((x, 0.0, 0.0))
    return arm2


def make_floor(size=(5.6, 3.2), name='Boden'):
    ob = bpy.data.objects.get(name)
    if ob:
        return ob
    me = bpy.data.meshes.new(name)
    sx, sy = size[0] / 2.0, size[1] / 2.0
    me.from_pydata([(-sx, -sy, 0), (sx, -sy, 0), (sx, sy, 0), (-sx, sy, 0)], [], [(0, 1, 2, 3)])
    me.uv_layers.new()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + '_Material')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n_ for n_ in nt.nodes if n_.type == 'BSDF_PRINCIPLED')
    chk = nt.nodes.new('ShaderNodeTexChecker')
    chk.inputs['Color1'].default_value = (0.16, 0.17, 0.19, 1.0)
    chk.inputs['Color2'].default_value = (0.12, 0.13, 0.15, 1.0)
    chk.inputs['Scale'].default_value = 1.0
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (2.0, 2.0, 2.0)               # 0.5 m tiles
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], chk.inputs['Vector'])
    nt.links.new(chk.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.85
    me.materials.append(mat)
    return ob


def make_label(text, x, name):
    ob = bpy.data.objects.get(name)
    if ob:
        return ob
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = text
    cu.size = 0.12
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, 0.45, 0.002)
    ob.rotation_euler = (0.0, 0.0, math.pi)                          # reads from the front
    ob.hide_render = True
    mat = bpy.data.materials.new(name + '_Material')
    mat.use_nodes = True
    bsdf = next(n_ for n_ in mat.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.85, 0.80, 0.45, 1.0)
    cu.materials.append(mat)
    return ob


def build_all(glb=GLB_DEFAULT, keys=('A', 'B', 'C')):
    H = humanoid_map(glb)
    armA = import_model(COLL['A'], glb)
    armA.name = 'Yoru_A'
    arms = {'A': armA}
    armA.location = Vector((X_POS['A'], 0.0, 0.0))
    for k in keys:
        if k != 'A':
            arms[k] = copy_character(armA, COLL[k], X_POS[k])
            arms[k].name = 'Yoru_' + k
    rigs = {k: Rig(a, H) for k, a in arms.items()}
    results = {}
    for k in keys:
        fit_arms_variant(rigs[k], k)
        D, P, diag = pose_variant(rigs[k], k)
        results[k] = (diag, run_checks(rigs[k]))
        log(k, 'diag', diag, '|', fmt_checks(results[k][1]))
    make_floor()
    for k in keys:
        make_label(k + '  ' + VARIANTS[k]['label'].split('(')[0].split('  ')[1].strip(), X_POS[k], 'Label_' + k)
    return rigs, results


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    glb, out = argv[0], argv[1]
    keys = tuple(argv[2].split(',')) if len(argv) > 2 else ('A', 'B', 'C')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_all(glb, keys)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    log('saved', out)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
