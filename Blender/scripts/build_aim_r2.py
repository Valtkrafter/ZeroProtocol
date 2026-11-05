"""
Yoru - AIM STANCE with two pistols, ROUND 2 (2026-10-29): a copy of build_aim_r1.py (stays untouched) with a NEW STANCE after the references
(Blender/previews/ref_aim/: Tomb Raider AimLevel, ROTTR gameplay, PoseMy.Art).  Round 1 was a squat (ankles 0.175 m apart, knees 30 deg, pelvis 3 cm
down, torso upright); the user: "every pose looks like she is shitting".  Now: legs nearly straight, feet 0.38 m apart (ankle joints) and staggered
0.16 m, toes out 5 deg (front foot) / 13 deg (back foot), pelvis over the middle of the feet and at most 1.5 cm lower, the trunk leans forward in the
spine chain (hips -> neck 6..10 deg ahead of the plumb line), head up and level.  The pelvis drop is not chosen: it follows from the knee of the
BACK leg (knee_back), the front knee follows from the stagger and from how far the pelvis sits ahead of the feet (see stance_solve).
Arm variants as round 1 (B now with the hands at chin height, arms 27.5 deg apart, elbows 164 deg).  Foot in front: A = RIGHT foot (the trunk turns
the right shoulder forward, the right arm leads, and the left hand at the left hip has room); B and C = LEFT foot (as Lara).
Split for an UPPER-BODY LAYER and for the pictures:
  action Yoru_Aim_r2_<V>          the whole aim: Spine, Chest, UpperChest, Neck, Head, both Shoulders, UpperArm, LowerArm, Hand, all finger and thumb
                                  joints (local rotations, keys on frames 0 and 1).  No hips, legs or tail keys.
  action Yoru_Aim_r2_Stand        the stance for the pictures (left foot in front, used by B and C): Hips (rotation 0, lowered), UpperLeg, LowerLeg,
                                  Foot, Toes and the tail.  On the NLA track 'Stand' under the active action.
  action Yoru_Aim_r2_Stand_A      the same with the RIGHT foot in front (A).  Stand_S1 / Stand_S3: narrow / Tomb-Raider-wide stance (B extras).
  action Yoru_Aim_r2_<V>_full     upper body + its own stance in one action (for measuring and pictures, independent of the NLA):
                                  A_full, B_full, C_full, B_S1_full, B_S3_full (B_S2 = B_full).
Method (world-space rotation deltas D per bone, parents first, as build_idle.py / build_sprint_r1.py):
  - trunk: lean and turn live in the spine chain only, the pelvis keeps rotation 0; neck and head bring the gaze back onto the aim line (+Y);
  - arms: two-bone IK to a WRIST target given as an offset from the posed shoulder joint (world axes: x her right, y forward, z up).  The elbow
    swivel phi (0 = elbow straight down from the shoulder-wrist line, + = outwards) is fitted per side: the smallest phi from the variant's
    start value at which forearm, hand and pistol keep CLEAR from body and gear (exact BVH test of build_sprint_r1.py; the upper arm counts only
    at its elbow end, the inner upper arm rests on the ribs in every arms-down pose of this rig).  Upper arm and forearm share the elbow axis
    (pure hinge, no twist at the elbow); the hand turns from the forearm onto the barrel line by the shortest rotation (at most WR_MAX) and the
    barrel points at AIM_POINT (15 m ahead on the crosshair line of the game camera); a remaining cant of the pistol is taken out by a small
    forearm roll (at most 18 deg) plus a wrist roll (at most 12 deg).
Run (background Blender, absolute paths):
  blender -b --factory-startup --python build_aim_r2.py -- <Yoru_V2.glb> <out dir> [design=1] [variants=A,B,C] [A.wrist_R=x,y,z ...]
Writes <out dir>/Yoru_Aim_r2.blend and <out dir>/Yoru_Aim_r2_numbers.json (design=1: only prints the geometry, saves nothing).
Blender: +Y forward, her left = -X, up = +Z.
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
    print('[aim_r2 %5.1fs]' % (time.time() - T0), *a, flush=True)


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

# ------------------------------------------------------------------ stance (pictures only) after the references
# spacing: sideways distance of the ankle joints (m); stagger: front to back distance of the ankle joints (m); front: the foot ahead;
# hips_ahead: the hips joint ahead of the middle between the ankles (m); knee_back: knee flexion of the back leg (deg) - the pelvis drop follows
# from it; toe_front / toe_back: toes turned out (deg).  The pelvis stays where it is in x / y (rotation 0), the feet are placed around it.
# Why these numbers (this rig: thigh 0.3425, shank 0.4005, hip joints 0.0751 off the midline): with the ankles 0.38 apart the back leg reaches the
# floor only if the pelvis comes down about 1.4 cm even with a straight knee; the front knee = back knee + what the stagger x hips_ahead takes:
# both knees <= 6 / 12 deg needs stagger * hips_ahead <= ~0.0022 m^2 (0.16 m stagger -> pelvis at most 1.4 cm ahead of the feet).
STANCES = {
    'L':  dict(label='S2 mittel, linker Fuss vorn', spacing=0.38, stagger=0.16, front='L', hips_ahead=0.010, knee_back=5.0, toe_front=5.0, toe_back=13.0),
    'R':  dict(label='S2 mittel, rechter Fuss vorn', spacing=0.38, stagger=0.16, front='R', hips_ahead=0.010, knee_back=5.0, toe_front=5.0, toe_back=13.0),
    'S1': dict(label='S1 schmal', spacing=0.28, stagger=0.12, front='L', hips_ahead=0.010, knee_back=5.0, toe_front=5.0, toe_back=13.0),
    'S3': dict(label='S3 breit wie Tomb Raider', spacing=0.50, stagger=0.18, front='L', hips_ahead=0.010, knee_back=5.0, toe_front=5.0, toe_back=13.0),
}
LEG_L1 = (HEAD0[H['leftLowerLeg']] - HEAD0[H['leftUpperLeg']]).length
LEG_L2 = (HEAD0[H['leftFoot']] - HEAD0[H['leftLowerLeg']]).length


def stance_solve(st):
    """ankle targets (world), foot yaw (deg, rz) per side and the pelvis drop (m) for a stance: the feet are set around the resting pelvis so that
    the hips joint sits hips_ahead ahead of their middle; the drop is what the BACK leg needs for its knee flexion knee_back"""
    hip0 = HEAD0[H['hips']]
    mid_y = hip0.y - st['hips_ahead']
    ank, yaw = {}, {}
    for side in ('L', 'R'):
        sx = -1.0 if side == 'L' else 1.0
        fy = mid_y + (0.5 * st['stagger'] if side == st['front'] else -0.5 * st['stagger'])
        ank[side] = Vector((sx * 0.5 * st['spacing'], fy, HEAD0[nm(side, 'Foot')].z))
        toe = st['toe_front'] if side == st['front'] else st['toe_back']
        yaw[side] = toe if side == 'L' else -toe                      # + rz turns the left toes out, - rz the right toes
    back = 'R' if st['front'] == 'L' else 'L'
    hj = HEAD0[nm(back, 'UpperLeg')]
    d2 = LEG_L1 ** 2 + LEG_L2 ** 2 + 2.0 * LEG_L1 * LEG_L2 * math.cos(deg(st['knee_back']))
    a = ank[back]
    h2 = (a.x - hj.x) ** 2 + (a.y - hj.y) ** 2
    drop = (hj.z - a.z) - math.sqrt(max(d2 - h2, 0.0))
    return ank, yaw, drop
# tail (pictures only): direction of every segment (pitch above the horizontal, yaw from straight back towards her LEFT, deg).  A slim hook:
# down close behind the left buttock and thigh, the last third rolls up tightly to her left side (seen from behind it is a thin line, not a blob)
TAIL_DIRS = [(-35.0, 22.0), (-62.0, 26.0), (-84.0, 26.0), (-96.0, 28.0), (-62.0, 75.0), (-5.0, 125.0), (-5.0, 125.0), (55.0, 180.0)]
# round 2: with the feet apart the round-1 hook hung in the gap between the legs and showed from the front.  Now the tail drapes down behind the
# FRONT leg (left foot in front: behind the left leg; right foot in front, A: mirrored behind the right leg), the tip turns a little back
# (the first two joints keep the round-1 start: turned further to the side right at the root, the tail cuts the buttock: 8 triangle pairs)
TAIL_DIRS = [(-35.0, 22.0), (-62.0, 26.0), (-75.0, 50.0), (-78.0, 62.0), (-80.0, 68.0), (-82.0, 70.0), (-82.0, 70.0), (-55.0, 35.0)]
# (further to her left, yaw 32..50 at the root, the tail comes within 2.5..3.2 mm of the left buttock / thigh or cuts it; this one keeps 8.8 mm)

# ------------------------------------------------------------------ variants: they differ in how far the arms go (same stance)
# wrist: offset of the wrist (hand bone head) from the posed shoulder joint (upper arm head), world axes, m.  phi0: start of the elbow swivel fit.
# clav: (protraction, depression) of the shoulder bone in deg.  lean / yaw: spine, chest, upper chest (deg; lean + = forward, yaw + = right
# shoulder forward).  neck_* / head_pitch: WORLD orientation of neck and head (pitch + = forward / chin down, yaw + = to her left).
# lean 8.5 / 8.5 / 7 (24 deg in the spine chain) puts hips -> neck about 9 deg ahead of the plumb line and the shoulders 7..8 cm ahead of the feet;
# 7 / 7 / 5 gave 6.7 deg and shoulders +5.7..6.3 cm (too far back), 9 / 9 / 8 gave 10.6 deg (over 10)
TRUNK = dict(lean=(8.5, 8.5, 7.0), yaw=(0.0, 0.0, 0.0), neck_pitch=6.0, neck_yaw=0.0, head_pitch=2.0)
VARIANTS = {
    # A: the right arm points 12 deg outwards so that the pistol shows to the right of her hair in the game camera (straight ahead it hides
    # behind the hair: 1 % visible); the left hand beside the left hip, the barrel level.  Right foot in front (with the right shoulder).
    'A': dict(label='A  eine Hand fuehrt (rechts vorn auf Schulterhoehe, links tief neben der Huefte)', yaw=(4.0, 3.0, 3.0), neck_yaw=4.0,
              wrist={'R': (0.085, 0.402, -0.055), 'L': (-0.090, 0.130, -0.250)}, phi0={'R': 15.0, 'L': 8.0},
              clav={'R': (10.0, 0.0), 'L': (0.0, 2.0)}, stance='R'),
    # B (round 2): hands at chin height (wrist 5 cm over the shoulder joint), arms 27.5 deg apart, elbows 164 deg inside (reference TR AimLevel)
    'B': dict(label='B  beide gestreckt, 27,5 Grad auseinander, Haende auf Kinnhoehe',
              wrist={'R': (0.099, 0.403, 0.050), 'L': (-0.099, 0.403, 0.050)}, phi0={'R': 20.0, 'L': 20.0},
              clav={'R': (8.0, 0.0), 'L': (8.0, 0.0)}, stance='L'),
    # C: the fists (grip centres) 19 cm apart, the wrists 23 cm (the grip lies 2 cm inside the wrist line); with the wrists 20 cm apart the
    # forearms had to turn in 26 deg and the wrists bent 28..30 deg
    'C': dict(label='C  kompakt vor der Brust, Ellbogen an den Rippen',
              wrist={'R': (0.019, 0.220, -0.150), 'L': (-0.019, 0.220, -0.150)}, phi0={'R': 8.0, 'L': 8.0},
              clav={'R': (4.0, 2.0), 'L': (4.0, 2.0)}, stance='L'),
}
EXTRA = {'B_S1': ('B', 'S1'), 'B_S3': ('B', 'S3')}                  # stance alternatives for B (full actions only, same arms as B)
for _k, _v in KV.items():                                            # e.g. A.wrist_R=0.02,0.41,-0.05  C.phi0_L=12  C.clav_R=4,2  variants=A,C
    if _k.startswith('stance.'):                                     # stance.L.hips_ahead=0.012
        _, sk_, pk_ = _k.split('.')
        STANCES[sk_][pk_] = _v if pk_ == 'front' else float(_v)
    elif _k == 'lean':                                               # lean=7,7,5
        TRUNK['lean'] = tuple(float(t) for t in _v.split(','))
    elif _k in ('neck_pitch', 'head_pitch'):
        TRUNK[_k] = float(_v)
    elif _k.startswith('GRIP_') and _k[5:] in GRIP:                  # grip experiments (probe only): GRIP_Middle=60,62,36
        GRIP[_k[5:]] = tuple(float(t) for t in _v.split(','))
    elif _k in ('GRIP_AT', 'THUMB'):
        globals()[_k] = tuple(float(t) for t in _v.split(','))
    elif _k == 'TAIL':                                               # TAIL=-35,30;-60,34;...  (8 pairs: pitch, yaw)
        TAIL_DIRS = [tuple(float(t) for t in pr.split(',')) for pr in _v.split(';')]
    elif _k == 'variants':
        VARIANTS = {k_: v_ for k_, v_ in VARIANTS.items() if k_ in _v.split(',')}
    elif '.' in _k and _k.split('.')[0] in VARIANTS:
        vk_, pk_ = _k.split('.', 1)
        vals = [float(t) for t in _v.split(',')]
        if pk_.startswith(('wrist_', 'phi0_', 'clav_')):
            grp, sd = pk_.split('_')
            VARIANTS[vk_].setdefault(grp, {})[sd] = tuple(vals) if len(vals) > 1 else vals[0]
        else:
            VARIANTS[vk_][pk_] = tuple(vals) if len(vals) > 1 else vals[0]


def trunk_of(V):
    t = dict(TRUNK)
    t.update({k: V[k] for k in TRUNK if k in V})
    return t


def tail_dir(pitch, yaw):
    cp = math.cos(deg(pitch))
    return Vector((-math.sin(deg(yaw)) * cp, -math.cos(deg(yaw)) * cp, math.sin(deg(pitch))))


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
    tr = trunk_of(V)
    st = STANCES[stance_key or V['stance']]
    rel, absd = {}, {}
    for k, key in enumerate(('spine', 'chest', 'upperChest')):
        rel[H[key]] = eul(rx=-tr['lean'][k], rz=tr['yaw'][k])
    absd[H['neck']] = eul(rx=-tr['neck_pitch'], rz=tr['neck_yaw'])
    absd[H['head']] = eul(rx=-tr['head_pitch'])
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
    # stance (stance_solve: feet around the resting pelvis, the drop from the back knee)
    ank, fyaw, drop = stance_solve(st)
    hips_d = Vector((0.0, 0.0, -drop))
    legs = {side: (ank[side], fyaw[side]) for side in ('L', 'R')}
    D, P, Q, ik, armc = {}, {}, {}, {}, {}
    info = {'phi': dict(phi), 'drop': drop, 'stance': st}
    hips_name = H['hips']
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        P[name] = HEAD0[name].copy() if parent is None else P[parent] + D[parent] @ (HEAD0[name] - HEAD0[parent])
        if name == hips_name:
            P[name] = P[name] + hips_d
            D[name] = Quaternion()                                    # the pelvis keeps rotation 0
        elif name in absd:
            D[name] = absd[name]
        elif name in rel:
            D[name] = Dp @ rel[name]
        else:
            D[name] = Dp.copy()
        if name in TAIL:                                              # tail: parallel transport of the parent's frame onto the wanted direction
            i = TAIL.index(name)
            rest_dir = Vector((0.0, -1.0, 0.0))
            tp_, ty_ = TAIL_DIRS[i]
            if st['front'] == 'R':                                    # behind the front leg: mirror for the right foot in front
                ty_ = -ty_
            D[name] = (Dp @ rest_dir).rotation_difference(tail_dir(tp_, ty_)) @ Dp
        for side, sx in (('L', -1.0), ('R', 1.0)):
            if name == nm(side, 'UpperLeg'):
                Hp = P[name]
                K0, A0 = HEAD0[nm(side, 'LowerLeg')], HEAD0[nm(side, 'Foot')]
                L1, L2 = (K0 - HEAD0[name]).length, (A0 - K0).length
                T, yaw_ = legs[side]
                pole = Vector((-math.sin(deg(yaw_)), math.cos(deg(yaw_)), 0.0))
                K, Teff, defi = two_bone_ik(Hp, T, pole, L1, L2)
                ik[side] = (K, Teff, defi)
                D[name] = (K0 - HEAD0[name]).rotation_difference(K - Hp)
            elif name == nm(side, 'LowerLeg'):
                K0, A0 = HEAD0[name], HEAD0[nm(side, 'Foot')]
                K, Teff, _ = ik[side]
                D[name] = (A0 - K0).rotation_difference(Teff - K)
            elif name == nm(side, 'Foot'):
                D[name] = eul(rz=legs[side][1])
            elif name == nm(side, 'UpperArm'):
                S = P[name]
                W = S + Vector(V['wrist'][side])
                K, Weff, defi = elbow_ik(S, W, phi[side], sx, L_UA[side], L_FA[side])
                ua, fo = (K - S).normalized(), (Weff - K).normalized()
                ax = ua.cross(fo)
                if ax.length < 1e-6:
                    ax = Vector((1.0, 0.0, 0.0))
                ax.normalize()
                n = ax * (-sx)                                        # palm normal on the elbow axis: pure hinge, no twist
                Du = aim(REST_UA[side], REST_N, ua, n)
                Df0 = aim(REST_FA[side], REST_N, fo, n)
                muzzle_guess = Weff + fo * 0.21 + Vector((0.0, 0.0, 0.05))
                bdir = (AIM_POINT - muzzle_guess).normalized()
                ang = math.degrees(fo.angle(bdir))
                hdir = bdir.copy() if ang <= WR_MAX else fo.slerp(bdir, WR_MAX / ang).normalized()
                Dh0 = fo.rotation_difference(hdir) @ Df0
                top = Dh0 @ Vector((0.0, 1.0, 0.0))
                up_ref = Vector((0.0, 0.0, 1.0))
                cant = signed_angle(up_ref, top, hdir)                # roll of the pistol top from upright about the barrel (deg)
                tw_e = max(-18.0, min(18.0, -cant * 0.6))
                tw_w = max(-12.0, min(12.0, -cant - tw_e))
                Df = Quaternion(fo, deg(tw_e)) @ Df0
                Dh = Quaternion(hdir, deg(tw_w)) @ Quaternion(hdir, deg(tw_e)) @ Dh0
                armc[side] = (Du, Df, Dh)
                info[side] = dict(S=S.copy(), K=K.copy(), W=Weff.copy(), W_want=W.copy(), deficit=defi, ua=ua, fo=fo, hdir=hdir, bdir=bdir,
                                  wrist_want=ang, cant0=cant, tw_e=tw_e, tw_w=tw_w)
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
            log('  ', s, json.dumps(g[s]))
        log('   both', json.dumps(both))
        log('   trunk', json.dumps(trunk))
        log('   legs', json.dumps(legs))
    for sk in ('S1', 'S3'):
        if 'B' in VARIANTS:
            Q, hl, D, P, info = compute_pose(VARIANTS['B'], dict(VARIANTS['B']['phi0']), sk)
            g, both, trunk, legs = geometry(D, P, info)
            log('DESIGN B stance', sk, json.dumps(trunk['stance']))
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


# ------------------------------------------------------------------ probe mode: try wrist targets, print clearance and camera numbers, save nothing
if KV.get('probe'):                                                  # probe=A:R:0.055,0.41,-0.05;0.075,0.405,-0.05   (side 'both' = mirrored)
    for job in KV['probe'].split('|'):
        vk, sd, cands = job.split(':')
        for cand in cands.split(';'):
            V = dict(VARIANTS[vk])
            V['wrist'] = dict(V['wrist'])
            xyz = tuple(float(t) for t in cand.split(','))
            if sd == 'both':
                V['wrist']['R'] = xyz
                V['wrist']['L'] = (-xyz[0], xyz[1], xyz[2])
            else:
                V['wrist'][sd] = xyz
            phi = {s: float(V['phi0'][s]) for s in ('L', 'R')}
            for it in range(40):
                set_pose(V, phi)
                c = clearance_exact()
                bad = [s for s in ('L', 'R') if not side_ok(c[s])]
                if not bad:
                    break
                for s in bad:
                    phi[s] = min(70.0, phi[s] + 2.0)
            Q, hl, D, P, info = compute_pose(V, phi)
            g, both, trunk, legs = geometry(D, P, info)
            fg = face_gap()
            log('PROBE %s %s %s phi L %.0f R %.0f | %s | R wrist %.1f grip %s | L wrist %.1f grip %s | clear R %.1f/%.1f L %.1f/%.1f mm' % (
                vk, sd, cand, phi['L'], phi['R'], json.dumps(fg), g['R']['wrist_bend'], g['R']['grip_world'], g['L']['wrist_bend'],
                g['L']['grip_world'], 1000 * c['R']['min'], 1000 * c['R']['up_min'], 1000 * c['L']['min'], 1000 * c['L']['up_min']))
            log('PROBEGRIP', json.dumps(grip_numbers(body_coords())['R']), 'GRIP', json.dumps(GRIP), 'THUMB', THUMB, 'GRIP_AT', GRIP_AT,
                'upper arm out R %.1f L %.1f' % (g['R']['upper_arm_out'], g['L']['upper_arm_out']))
    sys.exit(0)

# ------------------------------------------------------------------ fit the elbow swivel per variant and side (each variant on its own stance)
PHI_MAX = 70.0
poses = {}
for key, V in VARIANTS.items():
    phi = {s: float(V['phi0'][s]) for s in ('L', 'R')}
    for it in range(40):
        set_pose(V, phi)
        c = clearance_exact()
        bad = [s for s in ('L', 'R') if not side_ok(c[s])]
        if not bad:
            break
        moved = False
        for s in bad:
            if phi[s] < PHI_MAX:
                phi[s] += 2.0
                moved = True
        if not moved:
            break
    log('variant %s (stance %s): elbow swivel L %.1f R %.1f deg after %d steps; clearance L %s / R %s' % (
        key, V['stance'], phi['L'], phi['R'], it, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in c['L'].items()},
        {k: (round(v, 4) if isinstance(v, float) else v) for k, v in c['R'].items()}))
    poses[key] = phi
SETUPS = {k: (k, VARIANTS[k]['stance']) for k in VARIANTS}            # picture / measuring setups: name -> (arm variant, stance)
SETUPS.update({k: v for k, v in EXTRA.items() if v[0] in VARIANTS})


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
STAND_NAME = {'L': 'Yoru_Aim_r2_Stand', 'R': 'Yoru_Aim_r2_Stand_A', 'S1': 'Yoru_Aim_r2_Stand_S1', 'S3': 'Yoru_Aim_r2_Stand_S3'}
for key, V in VARIANTS.items():                                      # the layer: upper body only
    Q, hl, D, P, info = compute_pose(V, poses[key])
    acts[key] = key_action(Q, hl, UPPER, 'Yoru_Aim_r2_' + key, False)
for name, (vk, sk) in SETUPS.items():                                # the stances (pictures only) and the full poses (upper body + its stance)
    Q, hl, D, P, info = compute_pose(VARIANTS[vk], poses[vk], sk)
    if 'stand_' + sk not in acts:
        acts['stand_' + sk] = key_action(Q, hl, STAND, STAND_NAME[sk], True)
    acts[name + '_full'] = key_action(Q, hl, UPPER + STAND, 'Yoru_Aim_r2_%s_full' % name, True)
ad = arm.animation_data
trk = ad.nla_tracks.new()
trk.name = 'Stand'
stand_act = acts.get('stand_L') or next(a for k, a in acts.items() if k.startswith('stand_'))
strip = trk.strips.new(stand_act.name, 0, stand_act)
if hasattr(strip, 'action_slot') and strip.action_slot is None and len(stand_act.slots):
    strip.action_slot = stand_act.slots[0]
strip.extrapolation = 'HOLD'
log('actions:', ', '.join(a.name for a in acts.values()), '| NLA track Stand = %s, strip frames %.0f..%.0f' % (stand_act.name, strip.frame_start, strip.frame_end))


def use_action(act):
    ad_ = arm.animation_data
    ad_.action = act
    if hasattr(ad_, 'action_slot') and ad_.action_slot is None and len(act.slots):
        ad_.action_slot = act.slots[0]
    for pb in arm.pose.bones:                                         # nothing left over from the fits
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
    scene.frame_set(1)
    scene.frame_set(0)
    bpy.context.view_layer.update()


# ------------------------------------------------------------------ face: expression B (cool, alert) of the idle, set (not keyed)
FACE_B = {'Fcl_EYE_Angry': 0.40, 'Fcl_EYE_Fun': 0.16, 'Fcl_MTH_Neutral': 0.55, 'Fcl_MTH_Close': 0.20, 'Fcl_BRW_Angry': 0.50}
if face is not None and face.data.shape_keys:
    for kb in face.data.shape_keys.key_blocks:
        if kb.name != 'Basis':
            kb.value = FACE_B.get(kb.name, 0.0)

# ------------------------------------------------------------------ numbers: through the saved full actions (what the file really shows)
numbers = {'date': '2026-10-29', 'round': 2, 'model': os.path.basename(GLB), 'aim_point': list(AIM_POINT), 'clear_needed_mm': 1000 * CLEAR,
           'wrist_max_deg': WR_MAX, 'stances': STANCES, 'trunk': TRUNK, 'tail_dirs': TAIL_DIRS,
           'grip': {'GRIP': GRIP, 'GRIP_SPREAD': GRIP_SPREAD, 'THUMB': THUMB, 'GRIP_AT': GRIP_AT},
           'layer': {'upper_body_action_bones': UPPER, 'stand_action_bones': STAND,
                     'actions': {k: a.name for k, a in acts.items()}, 'nla_track_Stand': stand_act.name}, 'variants': {}}
for name, (vk, sk) in SETUPS.items():
    V = VARIANTS[vk]
    use_action(acts[name + '_full'])
    Q, hl, D, P, info = compute_pose(V, poses[vk], sk)
    pb_err = max(min(a_, 2.0 * math.pi - a_) for a_ in ((arm.pose.bones[n].matrix.to_quaternion() @ R[n].inverted()).rotation_difference(D[n]).angle
                                                         for n in UPPER + STAND))
    pos_err = max((arm.matrix_world @ arm.pose.bones[n].head - P[n]).length for n in UPPER + STAND)
    g, both, trunk, legs = geometry(D, P, info)
    co = body_coords()
    c = clearance_exact(co)
    for s in ('L', 'R'):
        r = c[s]
        g[s]['clearance_mm'] = dict(forearm_hand=round(1000 * r['min'], 1), forearm_hand_where=r['min_part'][:2] if r['min_part'] else None,
                                    upper_arm_elbow_end=round(1000 * r['up_min'], 1), upper_arm_whole=round(1000 * r['up_min_all'], 1),
                                    pistol=round(1000 * r['pistol_min'], 1), pistol_to_other_side=round(1000 * r['pistol_other_min'], 1),
                                    cuts=dict(arm=r['cut'], pistol=r['pistol_cut'], pistol_other=r['pistol_other_cut']))
    fg = face_gap()
    tl = tail_numbers(co)
    layer_err = None
    if name in VARIANTS and sk == 'L':                               # the layer action over the NLA stance must give the same pose as the full action
        use_action(acts[name])
        layer_err = max((arm.matrix_world @ arm.pose.bones[n].head - P[n]).length for n in UPPER + STAND)
    numbers['variants'][name] = dict(label=V['label'], arms_variant=vk, stance_key=sk,
                                     input=dict(wrist=V['wrist'], clav=V['clav'], trunk=trunk_of(V), phi_start=V['phi0']),
                                     arms=g, both=both, trunk=trunk, legs=legs, pistol_face_gap_px_1920x1080=fg, tail=tl,
                                     check=dict(file_vs_solver_rot_deg=round(math.degrees(pb_err), 3), file_vs_solver_pos_mm=round(1000 * pos_err, 2),
                                                layer_plus_nla_vs_full_mm=None if layer_err is None else round(1000 * layer_err, 2)))
    log('NUMBERS', name, json.dumps(numbers['variants'][name]))

json.dump(numbers, open(os.path.join(OUT, 'Yoru_Aim_r2_numbers.json'), 'w'), indent=1)
use_action(acts['B'] if 'B' in acts else next(iter(acts.values())))
bpy.context.preferences.filepaths.save_version = 0
path = os.path.join(OUT, 'Yoru_Aim_r2.blend')
bpy.ops.wm.save_as_mainfile(filepath=path)
log('saved', path, '(active action %s, NLA track Stand = %s)' % (arm.animation_data.action.name, stand_act.name))
log('DONE')
