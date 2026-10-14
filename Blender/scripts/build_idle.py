"""
Yoru - normal idle (loop 6 s @ 30 fps), built procedurally on the VRM skeleton.

Run (background Blender):
  blender -b --factory-startup --python build_idle.py -- <Yoru.glb> <output dir>

Method
  - Every humanoid bone gets a WORLD-space rotation delta D relative to the T-pose, either relative to its parent
    (rel) or absolute (arms by direction + palm normal, legs by two-bone IK with fixed feet).
  - The pose-bone basis rotation follows from  Q = R^-1 * D_parent^-1 * D * R   (R = rest orientation of the bone),
    so the bone axes / rolls of the glTF import do not matter.
  - Loop terms use whole cycles per 6 s: breathing 2 cycles (3 s), weight shift 1 cycle, head 1 and 2 cycles.
  - Arm hang angles are fitted automatically so that no arm sample point enters the torso / thigh mesh (no looking needed).
Blender: +Y = forward, left = -X, up = +Z (VRM import).
"""
import bpy, sys, math, json, struct, os, glob, time, re, shutil
from mathutils import Vector, Quaternion, Euler, Matrix
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, 'previews'), exist_ok=True)

FPS = 30
LOOP = 6.0
NF = int(FPS * LOOP)            # 180 -> keys 0..180, key 180 == key 0
TWO_PI = 2.0 * math.pi
T0 = time.time()


def log(*a):
    print('[idle %5.1fs]' % (time.time() - T0), *a, flush=True)


# ------------------------------------------------------------------ import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Body']
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Icosphere'):
        o.hide_render = True
        o.hide_viewport = True
scene = bpy.context.scene
scene.render.fps = FPS
scene.frame_start = 0
scene.frame_end = NF
log('armature matrix_world translation', tuple(round(x,3) for x in arm.matrix_world.translation), 'scale', tuple(arm.scale))

with open(GLB, 'rb') as f:
    f.read(12)
    clen, _ = struct.unpack('<II', f.read(8))
    js = json.loads(f.read(clen).decode('utf-8'))
nodes = js['nodes']
H = {h['bone']: nodes[h['node']]['name'] for h in js['extensions']['VRM']['humanoid']['humanBones']}
bones = arm.data.bones
R = {b.name: b.matrix_local.to_quaternion() for b in bones}          # rest orientation, armature space
HEAD0 = {b.name: b.head_local.copy() for b in bones}
TAIL0 = {b.name: b.tail_local.copy() for b in bones}

order = []                                                           # parents before children
queue = [b for b in bones if b.parent is None]
while queue:
    b = queue.pop(0)
    order.append(b.name)
    queue.extend(b.children)

hum_names = set(H.values())
HAIR_RE = re.compile(r'^J_Sec_Hair(\d+)_(\d+)$')
HAIR = [b.name for b in bones if HAIR_RE.match(b.name)]
TAIL_EARS = ['J_Opt_C_CatTail%d_01' % i for i in range(1, 9)] + ['J_Opt_%s_CatEar%d_01' % (sd, k) for sd in 'LR' for k in (1, 2)]
EXTRA = [n for n in TAIL_EARS if n in bones] + HAIR
log('animated extras: tail+ears', len([n for n in TAIL_EARS if n in bones]), 'hair joints', len(HAIR))


def nm(side, part):                                                  # side 'L'/'R'
    return H[('left' if side == 'L' else 'right') + part]


# ------------------------------------------------------------------ helpers
def deg(x):
    return math.radians(x)


def eul(rx=0.0, ry=0.0, rz=0.0):                                     # degrees, X first, then Y, then Z (world axes)
    return Euler((deg(rx), deg(ry), deg(rz)), 'XYZ').to_quaternion()


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    s = d.cross(n)
    return Matrix((d, n, s)).transposed().to_quaternion()


def aim(rest_dir, rest_nrm, tgt_dir, tgt_nrm):
    return frame_rot(tgt_dir, tgt_nrm) @ frame_rot(rest_dir, rest_nrm).inverted()


def two_bone_ik(Hp, K0, A0, T, pole, L1, L2):
    """returns knee position and the (clamped) ankle position; hip Hp, rest knee K0, rest ankle A0 only for lengths"""
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


# ------------------------------------------------------------------ pose parameters
class P:
    # arm hang per side (fitted below): outward angle of the upper arm from the vertical, forearm outward angle,
    # elbow flexion (forearm forward), wrist
    # starting values = the ones the user approved in the first version of the idle (left 24 / 24, right 28 / 14)
    arm = {'L': dict(up_out=24.0, fore_out=12.0, fore_fwd=24.0, hand_fwd=19.2),
           'R': dict(up_out=28.0, fore_out=14.0, fore_fwd=14.0, hand_fwd=11.2)}
    hips_drop = 0.004    # hips lower than T-pose (m), more bends the knees
    tail = [6.0, -4.0, -12.0, -16.0, -18.0, 30.0, 0.0, 62.0]   # pitch per tail joint in degrees (+ up, - down), replaced by the fit below
    sway_x = 0.014       # hips shift to the right (weight leg) in m, base
    foot_fwd_L = 0.055   # unloaded (left) foot placed forward
    foot_out_L = 0.020   # and outward
    toe_out_R = 7.0
    toe_out_L = 12.0


FINGERS = {'Index': (22, 26, 16), 'Middle': (28, 32, 18), 'Ring': (34, 36, 20), 'Little': (40, 38, 22)}
PARTS = ('Proximal', 'Intermediate', 'Distal')


def solve(t, par=P):
    """returns (Q per bone name, hips local location vector, diagnostics)"""
    s = math.sin(TWO_PI * t / LOOP)                                   # weight shift (1 cycle / 6 s)
    br = 0.5 - 0.5 * math.cos(TWO_PI * 2.0 * t / LOOP)                # breath 0..1 (2 cycles / 6 s)
    brs = math.sin(TWO_PI * 2.0 * t / LOOP)

    rel = {}
    absd = {}
    diag = {'reach_deficit': 0.0}

    # --- pelvis and spine: weight on the right leg, counter rotation so the head stays level
    rel[H['hips']] = eul(rx=-1.0 + 0.5 * br, ry=-1.5 - 1.2 * s, rz=1.0 * math.sin(TWO_PI * t / LOOP + 0.9))
    rel[H['spine']] = eul(rx=0.4 * br, ry=1.0 + 0.8 * s, rz=-0.6 * math.sin(TWO_PI * t / LOOP + 0.9))
    rel[H['chest']] = eul(rx=0.9 * br + 0.5, ry=0.4 + 0.3 * s, rz=-0.4 * math.sin(TWO_PI * t / LOOP + 0.9))
    rel[H['upperChest']] = eul(rx=1.3 * br, ry=0.2 + 0.1 * s)
    hips_d = Vector((par.sway_x + 0.010 * s,
                     0.003 * math.sin(TWO_PI * t / LOOP + 1.3),
                     -par.hips_drop - 0.0026 * br))

    # --- neck and head: small slow looks and tilts
    yaw = 4.0 * math.sin(TWO_PI * t / LOOP + 0.4) + 1.2 * math.sin(TWO_PI * 2 * t / LOOP + 1.7)
    pit = 1.4 * math.sin(TWO_PI * t / LOOP + 2.0) + 0.7 * math.sin(TWO_PI * 2 * t / LOOP + 0.2)
    rol = 1.0 * math.sin(TWO_PI * t / LOOP + 1.0)
    rel[H['neck']] = eul(rx=0.4 * pit, ry=0.4 * rol, rz=0.4 * yaw)
    rel[H['head']] = eul(rx=0.6 * pit - 0.4 * br, ry=0.6 * rol, rz=0.6 * yaw)

    # --- shoulders (clavicles): outer end drops a little, rises a little with the breath (left ry<0 / right ry>0 = down)
    for side, sx in (('L', -1.0), ('R', 1.0)):
        rel[nm(side, 'Shoulder')] = eul(ry=sx * (4.0 - 1.05 * br))


    # --- cat tail: anime cat tail, leaves the back almost level, arcs down, tip curls up; lazy S-wave sway travelling to the tip
    # (Unity: the same base lift / curve + physics; here the wave is animated so it can be judged)
    rest_pitch = par.tail                                               # degrees per joint (+ up, - down); fitted so that the tail stays clear of the body (same values go into YoruSecondaryMotion)
    for i in range(1, 9):
        up = rest_pitch[i - 1]
        lag = 0.45 * i
        yaw_t = 2.2 * math.sin(TWO_PI * t / LOOP - lag) + 0.6 * math.sin(TWO_PI * 2.0 * t / LOOP - 1.6 * lag + 0.8)
        pit_t = 0.7 * math.sin(TWO_PI * 2.0 * t / LOOP - 0.3 * i)
        rel['J_Opt_C_CatTail%d_01' % i] = eul(rx=-(up + pit_t), rz=yaw_t)

    # --- cat ears: slow breathing sway, one ear flicks at a time (periodic bump so the loop closes)
    def bump(t_, c, w):
        d = (t_ - c + LOOP / 2.0) % LOOP - LOOP / 2.0
        return math.exp(-(d / w) ** 2)
    flick_L = bump(t, 1.8, 0.12)
    flick_R = 0.7 * bump(t, 4.3, 0.12)
    for side, sx, fl in (('L', -1.0, flick_L), ('R', 1.0, flick_R)):
        sway_e = 1.5 * math.sin(TWO_PI * 2.0 * t / LOOP + (0.6 if side == 'L' else 2.1))
        rel['J_Opt_%s_CatEar1_01' % side] = eul(rx=sway_e + 9.0 * fl, ry=sx * 3.5 * fl)
        rel['J_Opt_%s_CatEar2_01' % side] = eul(rx=0.6 * sway_e + 5.0 * fl, ry=sx * 1.5 * fl)

    # --- hair: very small wave down every strand so it is not frozen (in Unity the spring-bone physics moves it)
    for name in HAIR:
        m = HAIR_RE.match(name)
        depth, chain = int(m.group(1)), int(m.group(2))
        a = 0.9
        rel[name] = eul(rx=a * math.sin(TWO_PI * 2.0 * t / LOOP + 0.6 * chain - 0.35 * depth),
                        ry=0.6 * a * math.sin(TWO_PI * t / LOOP + 0.4 * chain - 0.3 * depth))

    # --- arms: absolute directions + palm normals
    for side, sx in (('L', -1.0), ('R', 1.0)):
        ap = par.arm[side]
        sway = 1.2 * s * (1.0 if side == 'L' else -1.0)
        a_u = deg(ap['up_out'] + sway + 0.5 * brs)
        a_f = deg(ap['fore_out'])
        b_f = deg(ap['fore_fwd'] + 1.0 * br)
        b_h = deg(ap['hand_fwd'])
        rest_dir = Vector((sx, 0, 0))
        rest_nrm = Vector((0, 0, -1))
        d_u = Vector((sx * math.sin(a_u), 0.05, -math.cos(a_u)))
        d_f = Vector((sx * math.sin(a_f), math.sin(b_f), -math.cos(b_f) * math.cos(a_f)))
        d_h = Vector((sx * 0.10, math.sin(b_h), -0.97))
        n_in = Vector((-sx, -0.15, 0.0))
        absd[nm(side, 'UpperArm')] = aim(rest_dir, rest_nrm, d_u, n_in)
        absd[nm(side, 'LowerArm')] = aim(rest_dir, rest_nrm, d_f, Vector((-sx, -0.12, 0.0)))
        absd[nm(side, 'Hand')] = aim(rest_dir, rest_nrm, d_h, Vector((-sx, -0.25, 0.0)))
        # fingers: relaxed curl, tiny breathing movement
        for fn, curls in FINGERS.items():
            for part, c in zip(PARTS, curls):
                cc = c + 1.5 * br
                rel[nm(side, fn + part)] = Quaternion((0, 1, 0), deg(sx * cc))     # tips towards the palm side (down in the T-pose)
        # thumb stays at rest (gentle)
    # --- legs: planted feet, two-bone IK
    # feet targets
    legs = {}
    for side, sx in (('L', -1.0), ('R', 1.0)):
        A0 = HEAD0[nm(side, 'Foot')]
        off = Vector((0, 0, 0))
        yaw_foot = -par.toe_out_R if side == 'R' else par.toe_out_L
        if side == 'L':
            off = Vector((-par.foot_out_L, par.foot_fwd_L, 0))
        legs[side] = (A0 + off, eul(rz=yaw_foot))
    return rel, absd, hips_d, legs, diag


def compute_pose(t, par=P):
    rel, absd, hips_d, legs, diag = solve(t, par)
    D = {}
    Q = {}
    ik = {}
    hips_name = H['hips']
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        if name in rel:
            D[name] = Dp @ rel[name]
        elif name in absd:
            D[name] = absd[name]
        else:
            D[name] = Dp.copy()
        # legs: IK once the hips are known
        for side in ('L', 'R'):
            if name == nm(side, 'UpperLeg'):
                Hp0 = HEAD0[name]
                hip_head = HEAD0[hips_name]
                Hp = hip_head + hips_d + D[hips_name] @ (Hp0 - hip_head)
                K0 = HEAD0[nm(side, 'LowerLeg')]
                A0 = HEAD0[nm(side, 'Foot')]
                L1 = (K0 - Hp0).length
                L2 = (A0 - K0).length
                T, foot_rot = legs[side]
                pole = Vector((-0.15 if side == 'L' else 0.15, 1.0, 0.0))
                K, Teff, deficit = two_bone_ik(Hp, K0, A0, T, pole, L1, L2)
                diag['reach_deficit'] = max(diag['reach_deficit'], deficit)
                ik[side] = (K, Teff)
                D[name] = (K0 - Hp0).rotation_difference(K - Hp)
            elif name == nm(side, 'LowerLeg'):
                K0 = HEAD0[name]
                A0 = HEAD0[nm(side, 'Foot')]
                K, Teff = ik[side]
                D[name] = (A0 - K0).rotation_difference(Teff - K)
            elif name == nm(side, 'Foot'):
                D[name] = legs[side][1]
        # basis rotation
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    hips_loc = R[hips_name].inverted() @ hips_d
    return Q, hips_loc, D, diag, hips_d


# ------------------------------------------------------------------ clearance check (numbers only)
vg_names = {vg.index: vg.name for vg in body.vertex_groups}
torso_like = {H['hips'], H['spine'], H['chest'], H['upperChest']}
thigh_like = {H['leftUpperLeg'], H['rightUpperLeg']}
torso_idx, thigh_idx = [], []
for v in body.data.vertices:
    if not v.groups:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    n = vg_names.get(g.group, '')
    if n in torso_like or n.startswith('J_Sec_'):
        torso_idx.append(v.index)
    elif n in thigh_like:
        thigh_idx.append(v.index)
log('body verts', len(body.data.vertices), 'torso-like', len(torso_idx), 'thigh-like', len(thigh_idx))


def arm_points(dg):
    """sample points (with radius) along both arms from the evaluated pose"""
    arm_ev = arm.evaluated_get(dg)
    pts = []
    for side in ('L', 'R'):
        for part, r in (('UpperArm', 0.050), ('LowerArm', 0.042), ('Hand', 0.036)):
            pb = arm_ev.pose.bones[nm(side, part)]
            h, tl = pb.head.copy(), pb.tail.copy()
            n = 8
            for i in range(3 if part == 'UpperArm' else 0, n + 1):
                pts.append((h.lerp(tl, i / n), r, side))
            if part == 'Hand':
                d = (tl - h).normalized()
                for i in range(1, 5):
                    pts.append((tl + d * (0.02 * i), 0.03, side))
    return pts


def min_clearance(frames):
    """minimum clearance (m) of the arm sample points to torso / thigh mesh, per side"""
    worst = {'L': (9.0, None), 'R': (9.0, None)}
    for f in frames:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        co = [v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()
        kd = KDTree(len(torso_idx) + len(thigh_idx))
        for i, vi in enumerate(torso_idx + thigh_idx):
            kd.insert(co[vi], i)
        kd.balance()
        for p, r, side in arm_points(dg):
            _, _, dist = kd.find(p)
            c = dist - r
            if c < worst[side][0]:
                worst[side] = (c, (f, tuple(round(x, 3) for x in p)))
    return worst


# ------------------------------------------------------------------ keyframes
def build_action(par=P):
    if arm.animation_data and arm.animation_data.action:
        old_action = arm.animation_data.action
        arm.animation_data.action = None
        bpy.data.actions.remove(old_action)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
    keyed = None
    prev = {}
    max_deficit = 0.0
    frames_data = []
    for f in range(NF + 1):
        t = f / FPS
        Q, hips_loc, D, diag, hips_d = compute_pose(t, par)
        max_deficit = max(max_deficit, diag['reach_deficit'])
        if keyed is None:
            keyed = [n for n in order if n in hum_names or n in EXTRA]
        for n in keyed:
            q = Q[n]
            if n in prev and prev[n].dot(q) < 0:
                q = -q
            prev[n] = q
            pb = arm.pose.bones[n]
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=f)
        pbh = arm.pose.bones[H['hips']]
        pbh.location = hips_loc
        pbh.keyframe_insert('location', frame=f)
        frames_data.append({'frame': f, 'hips_world_offset': list(hips_d),
                            'D': {n: [D[n].w, D[n].x, D[n].y, D[n].z] for n in H.values()}})
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action.name = 'Yoru_Idle'
        arm.animation_data.action.use_fake_user = True
    return max_deficit, frames_data


# fit the arm hang so that nothing enters the body (numbers only): try elbow flexion x outward angle,
# take the most relaxed combination (smallest outward angle, least elbow bend) that stays clear, per side.
fit_frames = [0, 20, 40, 60, 80, 100, 120, 140, 160]
for attempt in range(8):
    max_def, frames_data = build_action(P)
    if max_def > 0.0005:
        P.hips_drop += 0.002
        log('feet cannot reach (deficit %.4f m), hips_drop -> %.3f' % (max_def, P.hips_drop))
        continue
    break
log('hips_drop %.3f' % P.hips_drop)
# keep the approved arm hang; only open an arm further if the (slightly stronger) breathing made it touch the gear
for attempt in range(6):
    build_action(P)
    w = min_clearance(fit_frames)
    log('clearance L %.4f R %.4f' % (w['L'][0], w['R'][0]))
    changed = False
    for sd in ('L', 'R'):
        if w[sd][0] < 0.002:
            P.arm[sd]['up_out'] += 1.5
            P.arm[sd]['fore_out'] = 0.5 * P.arm[sd]['up_out']
            changed = True
            log('  side', sd, 'opened to', P.arm[sd]['up_out'])
    if not changed:
        break
max_def, frames_data = build_action(P)
w = min_clearance(fit_frames)
log('final clearance L %.4f R %.4f, feet deficit %.5f' % (w['L'][0], w['R'][0], max_def))


# ------------------------------------------------------------------ tail: compact roll, fitted against the body (numbers only)
def heads_to_pitch(heads):
    """segment headings (seg1..seg6, seg8; degrees from the backward horizontal, + up, - down) -> pitch per joint (8 joints)"""
    h = list(heads[:6]) + [heads[5]] + [heads[6]]                # seg7 has no length: same heading as seg6
    return [h[0]] + [h[i] - h[i - 1] for i in range(1, 8)]


TAIL_CANDIDATES = [   # from the tightest roll that curls towards the body to a looser hook
    ('roll 200', [8, -5, -30, -65, -105, -150, -200]),
    ('roll 165', [8, -5, -28, -58, -90, -125, -165]),
    ('roll 135', [8, -5, -25, -50, -78, -105, -135]),
    ('hook 95', [8, -5, -22, -42, -62, -78, -95]),
    ('hook up', [6, 2, -10, -26, -44, -14, 48]),
]
TAIL_BONES = ['J_Opt_C_CatTail%d_01' % i for i in range(1, 9)]
obst_bones = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg'], H['leftLowerLeg'], H['rightLowerLeg']}
obst_idx = []
for v in body.data.vertices:
    if not v.groups:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    n = vg_names.get(g.group, '')
    if n in obst_bones or n.startswith('J_Sec_L_Coat') or n.startswith('J_Sec_R_Coat') or n.startswith('J_Sec_L_Bust') or n.startswith('J_Sec_R_Bust'):
        obst_idx.append(v.index)
log('tail obstacles (torso, hips, legs, coat):', len(obst_idx))


def min_tail_clearance(frames):
    worst, where = 9.0, None
    for f in frames:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        co = [v.co.copy() for v in me.vertices]
        ev.to_mesh_clear()
        kd = KDTree(len(obst_idx))
        for i, vi in enumerate(obst_idx):
            kd.insert(co[vi], i)
        kd.balance()
        arm_ev = arm.evaluated_get(dg)
        for bn in TAIL_BONES[2:]:                                  # the first two joints sit inside the hips on purpose
            pb = arm_ev.pose.bones[bn]
            h0, t0 = pb.head.copy(), pb.tail.copy()
            for k in range(5):
                pt = h0.lerp(t0, k / 4.0)
                _, _, dist = kd.find(pt)
                c = dist - 0.016
                if c < worst:
                    worst, where = c, (f, bn, tuple(round(x, 3) for x in pt))
    return worst, where


tail_frames = [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165]
tail_choice = None
for label, heads in TAIL_CANDIDATES:
    P.tail = heads_to_pitch(heads)
    build_action(P)
    worst, where = min_tail_clearance(tail_frames)
    log('tail %-9s pitches %s -> min clearance %.4f m at %s' % (label, [round(x) for x in P.tail], worst, where))
    if worst >= 0.008 and tail_choice is None:
        tail_choice = (label, list(P.tail), worst)
        break
if tail_choice is None:
    # none was clear enough: take the loosest candidate and say so
    label, heads = TAIL_CANDIDATES[-1]
    P.tail = heads_to_pitch(heads)
    log('WARNING: no tail candidate reached 8 mm clearance, using', label)
else:
    log('tail chosen:', tail_choice[0], [round(x, 1) for x in tail_choice[1]], 'clearance %.4f' % tail_choice[2])
max_def, frames_data = build_action(P)
log('final tail pitches', [round(x, 1) for x in P.tail])
with open(os.path.join(OUT, 'Yoru_Idle_tail.json'), 'w') as f:
    json.dump({'restPitch': [round(x, 2) for x in P.tail]}, f)

with open(os.path.join(OUT, 'Yoru_Idle_pose.json'), 'w') as f:
    json.dump({'fps': FPS, 'frames': NF + 1, 'loop_seconds': LOOP, 'note': 'D = world-space rotation delta from the T-pose per humanoid bone (Blender axes: +Y forward, -X = her left)',
               'humanoid_map': H, 'hips_rest': list(HEAD0[H['hips']]), 'data': frames_data}, f)
scene.frame_set(0)

# ------------------------------------------------------------------ preview render
def make_floor():
    import numpy as np
    n = 2048
    img = bpy.data.images.new('floor_grid', n, n)
    a = np.zeros((n, n, 4), dtype=np.float32)
    a[..., :3] = (0.55, 0.58, 0.62)
    a[..., 3] = 1.0
    step = n // 16                                                     # 16 tiles over 8 m -> 0.5 m
    for k in range(0, n, step):
        a[k:k + 3, :, :3] = (0.25, 0.27, 0.30)
        a[:, k:k + 3, :3] = (0.25, 0.27, 0.30)
    img.pixels.foreach_set(a.ravel())
    img.pack()
    mat = bpy.data.materials.new('floor')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n_ for n_ in nt.nodes if n_.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0, 0, 0))
    fl = bpy.context.active_object
    fl.name = 'Floor'
    fl.data.materials.append(mat)


def setup_render():
    engine_ok = None
    for cand in ('BLENDER_WORKBENCH', 'BLENDER_EEVEE'):
        try:
            scene.render.engine = cand
            engine_ok = cand
            break
        except TypeError as e:
            log('engine', cand, 'not available:', str(e)[:120])
    log('render engine:', scene.render.engine)
    scene.render.resolution_x = 540
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    if scene.render.engine == 'BLENDER_WORKBENCH':
        sh = scene.display.shading
        sh.light = 'STUDIO'
        sh.color_type = 'TEXTURE'
        sh.show_object_outline = True
        sh.show_shadows = False
        sh.show_cavity = False
        scene.display.render_aa = '8'
    else:
        try:
            scene.eevee.taa_render_samples = 12
        except Exception:
            pass
        sun = bpy.data.lights.new('sun', 'SUN')
        sun.energy = 3.0
        so = bpy.data.objects.new('sun', sun)
        scene.collection.objects.link(so)
        so.rotation_euler = (math.radians(50), 0, math.radians(30))
    world = bpy.data.worlds.new('w')
    world.color = (0.80, 0.84, 0.90)
    scene.world = world
    return False


def add_camera(name, loc, target):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 1.95
    cam_data.clip_end = 60
    cam = bpy.data.objects.new(name, cam_data)
    scene.collection.objects.link(cam)
    cam.location = loc
    c = cam.constraints.new('TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return cam


if len(argv) < 3 or argv[2] != 'render':
    scene.frame_start, scene.frame_end = 0, NF - 1
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Yoru_Idle.blend'))
    log('saved blend (no render)')
    log('DONE')
    sys.exit(0)
make_floor()
ffmpeg_ok = setup_render()
target = bpy.data.objects.new('target', None)
target.location = (0, 0, 0.80)
scene.collection.objects.link(target)
cams = {
    'front34': add_camera('cam_front34', (6.0 * math.sin(math.radians(35)), 6.0 * math.cos(math.radians(35)), 1.0), target),
    'side': add_camera('cam_side', (6.0, 0.0, 1.0), target),
}
for key, cam in cams.items():
    scene.camera = cam
    prefix = os.path.join(OUT, 'previews', 'Yoru_Idle_' + key)
    scene.render.filepath = prefix if ffmpeg_ok else prefix + '_'
    scene.frame_start, scene.frame_end = 0, NF - 1                    # frame NF == frame 0, do not show it twice
    bpy.ops.render.render(animation=True)
    log('rendered', key)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Yoru_Idle.blend'))
log('saved blend; previews:', sorted(os.listdir(os.path.join(OUT, 'previews')))[:6])
log('DONE')
