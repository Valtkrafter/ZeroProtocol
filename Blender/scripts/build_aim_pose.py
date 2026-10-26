"""
Yoru - AIM STANCE STILLS with dual pistols (round 1: look candidates, a single pose each, no animation yet).
Built on the VRM skeleton with the method of build_idle.py: a WORLD-space rotation delta D per humanoid bone, the legs by two-bone IK to planted feet,
and here also the ARMS by two-bone IK to hand targets (offset from the posed shoulder).  The pistols are PLACEHOLDER boxes (no weapon model exists).

Run (background Blender):
  blender -b --factory-startup --python build_aim_pose.py -- <Yoru.glb> <output dir> [variants, comma separated, default all]
Writes <output dir>/Yoru_Aim_<variant>.blend (pose on frames 0 and 1) and prints diagnostics (lines starting with AIMDIAG).
Blender: +Y = forward, left = -X, up = +Z (VRM import).
"""
import bpy, bmesh, sys, math, json, struct, os, time
from mathutils import Vector, Quaternion, Euler, Matrix
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = argv[0], argv[1]
WANT = argv[2].split(',') if len(argv) > 2 else None
os.makedirs(OUT, exist_ok=True)
T0 = time.time()


def log(*a):
    print('[aim %5.1fs]' % (time.time() - T0), *a, flush=True)


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
hum_names = set(H.values())
TAIL_BONES = ['J_Opt_C_CatTail%d_01' % i for i in range(1, 9) if 'J_Opt_C_CatTail%d_01' % i in bones]
TAIL_PITCH = [8, -13, -23, -30, -32, -35, 0, -40]                    # the compact roll approved for the idle
try:
    tp = os.path.join(os.path.dirname(os.path.abspath(GLB)), '..', 'Yoru_Idle_tail.json')
    TAIL_PITCH = json.load(open(tp))['restPitch']
except Exception:
    pass


def nm(side, part):
    return H[('left' if side == 'L' else 'right') + part]


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
    K = Hp + u * a + p * h
    return K, Hp + u * d_c, d - d_c


FINGERS = {'Index': (30, 38, 24), 'Middle': (62, 70, 42), 'Ring': (68, 74, 46), 'Little': (72, 78, 48)}   # a grip around a pistol handle
PARTS = ('Proximal', 'Intermediate', 'Distal')

# ------------------------------------------------------------------ the variants
# hand[side]: wrist target as an OFFSET from the posed shoulder joint (m; x her right, y forward, z up). Arm reach is about 0.42 m.
# yaw / lean per bone hips, spine, chest, upperChest (deg). yaw: + = right shoulder forward (counter-clockwise from above). lean: - = forward.
# aim[side]: world direction the pistol points along, aimw[side]: weight (0 = along the forearm, 1 = exactly the aim direction; the wrist bends at most 35 deg).
VARIANTS = {
    'A': dict(label='A  eine Hand führt, die andere tief',
              yaw=(-4, -3, -3, -2), lean=(-2, -3, -3, -2), drop=0.09, shift=(0.010, 0.040),
              foot={'L': (-0.03, 0.20, 6.0), 'R': (0.03, -0.10, -16.0)},
              hand={'R': Vector((0.07, 0.395, 0.10)), 'L': Vector((-0.07, 0.20, -0.30))},
              pole={'R': Vector((0.6, -0.1, -0.7)), 'L': Vector((-0.5, -0.9, -0.2))},
              aim={'R': Vector((0.0, 1.0, 0.18)), 'L': Vector((0.0, 1.0, -0.35))}, aimw={'R': 0.85, 'L': 0.85},
              shoulder={'R': 0.0, 'L': 4.0}),
    'B': dict(label='B  beide Arme gestreckt, leicht auseinander',
              yaw=(0, 0, 0, 0), lean=(-2, -3, -3, -2), drop=0.09, shift=(0.0, 0.03),
              foot={'L': (-0.06, 0.14, 8.0), 'R': (0.06, -0.08, -8.0)},
              hand={'R': Vector((0.19, 0.365, 0.06)), 'L': Vector((-0.19, 0.365, 0.06))},
              pole={'R': Vector((0.4, -0.1, -1.0)), 'L': Vector((-0.4, -0.1, -1.0))},
              aim={'R': Vector((0.12, 1.0, 0.05)), 'L': Vector((-0.12, 1.0, 0.05))}, aimw={'R': 0.75, 'L': 0.75},
              shoulder={'R': 1.0, 'L': 1.0}),
    'C': dict(label='C  kompakt vor der Brust',
              yaw=(0, 0, 0, 0), lean=(-2, -3, -3, -2), drop=0.09, shift=(0.0, 0.03),
              foot={'L': (-0.05, 0.16, 8.0), 'R': (0.05, -0.09, -10.0)},
              hand={'R': Vector((0.0, 0.300, -0.11)), 'L': Vector((0.0, 0.300, -0.11))},
              pole={'R': Vector((0.5, -0.5, -1.0)), 'L': Vector((-0.5, -0.5, -1.0))},
              aim={'R': Vector((-0.04, 1.0, 0.04)), 'L': Vector((0.04, 1.0, 0.04))}, aimw={'R': 1.0, 'L': 1.0},
              shoulder={'R': 3.0, 'L': 3.0}),
}


def solve(V):
    rel = {}
    yaw, lean = V['yaw'], V['lean']
    rel[H['hips']] = eul(rx=lean[0], rz=yaw[0])
    rel[H['spine']] = eul(rx=lean[1], rz=yaw[1])
    rel[H['chest']] = eul(rx=lean[2], rz=yaw[2])
    rel[H['upperChest']] = eul(rx=lean[3], rz=yaw[3])
    sy, sl = sum(yaw), sum(lean)
    rel[H['neck']] = eul(rx=-0.4 * sl, rz=-0.4 * sy)                 # the head looks straight ahead along the aim line
    rel[H['head']] = eul(rx=-0.6 * sl, rz=-0.6 * sy)
    for side, sx in (('L', -1.0), ('R', 1.0)):
        rel[nm(side, 'Shoulder')] = eul(ry=sx * V['shoulder'][side])
        for fn, curls in FINGERS.items():
            for part, c in zip(PARTS, curls):
                rel[nm(side, fn + part)] = Quaternion((0, 1, 0), deg(sx * c))
    for i, nmb in enumerate(TAIL_BONES):
        rel[nmb] = eul(rx=-TAIL_PITCH[i])
    hips_d = Vector((V['shift'][0], V['shift'][1], -V['drop']))
    legs = {}
    for side in ('L', 'R'):
        ox, oy, fyaw = V['foot'][side]
        legs[side] = (HEAD0[nm(side, 'Foot')] + Vector((ox, oy, 0.0)), eul(rz=fyaw))
    return rel, hips_d, legs


def compute_pose(V):
    rel, hips_d, legs = solve(V)
    D, Q, P, ik, aik = {}, {}, {}, {}, {}
    diag = {'leg_deficit': 0.0, 'arm_deficit': {}}
    hips_name = H['hips']
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        P[name] = HEAD0[name].copy() if parent is None else P[parent] + D[parent] @ (HEAD0[name] - HEAD0[parent])
        if name == hips_name:
            P[name] = P[name] + hips_d
        D[name] = Dp @ rel[name] if name in rel else Dp.copy()
        for side, sx in (('L', -1.0), ('R', 1.0)):
            inward = Vector((-sx, 0.0, 0.0))
            rest_dir, rest_nrm = Vector((sx, 0.0, 0.0)), Vector((0.0, 0.0, -1.0))
            if name == nm(side, 'UpperLeg'):
                Hp = P[name]
                K0, A0 = HEAD0[nm(side, 'LowerLeg')], HEAD0[nm(side, 'Foot')]
                L1, L2 = (K0 - HEAD0[name]).length, (A0 - K0).length
                T, foot_rot = legs[side]
                pole = Vector((-0.15 if side == 'L' else 0.15, 1.0, 0.0))
                K, Teff, deficit = two_bone_ik(Hp, T, pole, L1, L2)
                diag['leg_deficit'] = max(diag['leg_deficit'], deficit)
                ik[side] = (K, Teff)
                D[name] = (K0 - HEAD0[name]).rotation_difference(K - Hp)
            elif name == nm(side, 'LowerLeg'):
                K0, A0 = HEAD0[name], HEAD0[nm(side, 'Foot')]
                K, Teff = ik[side]
                D[name] = (A0 - K0).rotation_difference(Teff - K)
            elif name == nm(side, 'Foot'):
                D[name] = legs[side][1]
            elif name == nm(side, 'UpperArm'):
                S = P[name]
                T = S + V['hand'][side]
                L1 = (HEAD0[nm(side, 'LowerArm')] - HEAD0[name]).length
                L2 = (HEAD0[nm(side, 'Hand')] - HEAD0[nm(side, 'LowerArm')]).length
                K, Teff, deficit = two_bone_ik(S, T, V['pole'][side], L1, L2)
                diag['arm_deficit'][side] = deficit
                du, df = (K - S).normalized(), (Teff - K).normalized()
                aik[side] = (K, Teff, df)
                D[name] = aim(rest_dir, rest_nrm, du, inward)
            elif name == nm(side, 'LowerArm'):
                D[name] = aim(rest_dir, rest_nrm, aik[side][2], inward)
            elif name == nm(side, 'Hand'):
                df = aik[side][2]
                w = V['aimw'][side]
                dh = (df * (1.0 - w) + V['aim'][side].normalized() * w).normalized()
                ang = df.angle(dh)
                if ang > deg(35.0):                                    # the wrist bends at most 35 deg
                    dh = df.slerp(dh, deg(35.0) / ang)
                D[name] = aim(rest_dir, rest_nrm, dh, inward)
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    hips_loc = R[hips_name].inverted() @ hips_d
    return Q, hips_loc, D, P, diag


# ------------------------------------------------------------------ clearance of the arms to the torso / thighs (numbers only)
vg_names = {vg.index: vg.name for vg in body.vertex_groups}
torso_like = {H['hips'], H['spine'], H['chest'], H['upperChest']}
thigh_like = {H['leftUpperLeg'], H['rightUpperLeg']}
solid_idx = []
for v in body.data.vertices:
    if not v.groups:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    n = vg_names.get(g.group, '')
    if n in torso_like or n in thigh_like or n.startswith('J_Sec_'):
        solid_idx.append(v.index)


def arm_clearance():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    co = [v.co.copy() for v in me.vertices]
    ev.to_mesh_clear()
    kd = KDTree(len(solid_idx))
    for i, vi in enumerate(solid_idx):
        kd.insert(co[vi], i)
    kd.balance()
    arm_ev = arm.evaluated_get(dg)
    worst = {'L': 9.0, 'R': 9.0}
    for side in ('L', 'R'):
        for part, r in (('UpperArm', 0.050), ('LowerArm', 0.042), ('Hand', 0.036)):
            pb = arm_ev.pose.bones[nm(side, part)]
            h, tl = pb.head.copy(), pb.tail.copy()
            for i in range(3 if part == 'UpperArm' else 0, 9):
                _, _, dist = kd.find(h.lerp(tl, i / 8))
                worst[side] = min(worst[side], dist - r)
    return worst


# ------------------------------------------------------------------ placeholder pistol
def make_pistol(name):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()

    def box(c, s, rx=0.0):
        m = Matrix.Translation(c) @ Euler((deg(rx), 0, 0)).to_matrix().to_4x4() @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    box((0.0, 0.055, 0.021), (0.026, 0.185, 0.032))                    # slide
    box((0.0, 0.070, -0.003), (0.022, 0.140, 0.012))                   # frame under the slide
    box((0.0, -0.022, -0.050), (0.025, 0.046, 0.092), rx=-12.0)         # grip
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + '_mat')
    mat.use_nodes = True
    bsdf = next(n_ for n_ in mat.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.05, 0.05, 0.06, 1.0)
    bsdf.inputs['Metallic'].default_value = 0.6
    bsdf.inputs['Roughness'].default_value = 0.4
    ob.data.materials.append(mat)
    return ob


def place_pistol(ob, side, D, P):
    sx = -1.0 if side == 'L' else 1.0
    wrist = P[nm(side, 'Hand')]
    F = (D[nm(side, 'Hand')] @ Vector((sx, 0.0, 0.0))).normalized()   # direction of the hand = barrel direction
    U = D[nm(side, 'Hand')] @ Vector((0.0, 1.0, 0.0))                   # thumb side = top of the pistol
    U = (U - F * U.dot(F)).normalized()
    X = F.cross(U)
    palm = wrist + F * 0.050
    origin = palm + F * 0.022 + U * 0.052                              # grip centre (local 0,-0.022,-0.052) lies in the palm
    ob.matrix_world = Matrix((X, F, U)).transposed().to_4x4()
    ob.location = origin


# ------------------------------------------------------------------ apply to the armature, key frames 0 and 1
def apply(V):
    Q, hips_loc, D, P, diag = compute_pose(V)
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action = None
    for f in (0, 1):
        for n in order:
            if n in hum_names or n in TAIL_BONES:
                pb = arm.pose.bones[n]
                pb.rotation_quaternion = Q[n]
                pb.keyframe_insert('rotation_quaternion', frame=f)
        pbh = arm.pose.bones[H['hips']]
        pbh.location = hips_loc
        pbh.keyframe_insert('location', frame=f)
    scene.frame_set(0)
    bpy.context.view_layer.update()
    return D, P, diag


results = {}
for key, V in VARIANTS.items():
    if WANT and key not in WANT:
        continue
    V = dict(V)
    V['hand'] = {s: v.copy() for s, v in V['hand'].items()}
    D, P, diag = apply(V)
    clr = arm_clearance()
    for attempt in range(6):                                           # push the hands forward until the arms are clear of the body
        if min(clr.values()) >= 0.003:
            break
        for s in ('L', 'R'):
            if clr[s] < 0.003:
                V['hand'][s] = V['hand'][s] + Vector((0.0, 0.02, 0.0))
        D, P, diag = apply(V)
        clr = arm_clearance()
    log('variant', key, V['label'])
    print('AIMDIAG', key, 'leg_deficit %.4f' % diag['leg_deficit'], 'arm_deficit', {s: round(v, 4) for s, v in diag['arm_deficit'].items()},
          'arm_clearance', {s: round(v, 4) for s, v in clr.items()}, 'hand_offset', {s: [round(x, 3) for x in V['hand'][s]] for s in V['hand']}, flush=True)
    pistols = []
    for side in ('L', 'R'):
        ob = make_pistol('PLATZHALTER_Pistole_' + side)
        place_pistol(ob, side, D, P)
        pistols.append(ob)
    path = os.path.join(OUT, 'Yoru_Aim_%s.blend' % key)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    log('saved', path)
    for ob in pistols:
        bpy.data.objects.remove(ob, do_unlink=True)
log('DONE')
