"""
Yoru - AIM POSE, ROUND 4 (2026-10-30): hard restart after the user took back A2 ("sie gefaellt mir nicht"; from behind A2 looked squatting, the arms at
chin height like a stiff zombie, shoulders pulled into the hair).  Charakter_Yoru.md point 4: hands at chest to belly height, never at the chin.
BODY  = a 100 % copy of FRAME 0 of the approved idle (Blender/Yoru_Idle_v2.blend, actions Yoru_Idle_v2 + Yoru_Idle_v2_Face): every keyed bone of the
        idle (hips location and rotation, legs, feet, toes, spine, chest, upper chest, neck, head, tail, shoulders, ears, eyes, hair, bust) with its
        local rotation unchanged, the face shape keys of frame 0 (expression B, eyes open).  The ONLY changes: UpperChest +8 deg local yaw (her front
        turns left, the right shoulder comes a little forward) and Head -8 deg local yaw back (the gaze along the aim line, 0 +- 1 deg; corrected if
        the idle's own gaze is off).  No new numbers for legs, pelvis or spine.
ARMS  = low, loose, slim (the layer): elbows point DOWN (the elbow below the shoulder-wrist line, in its vertical plane), the upper arm
        inclined THETA deg forward from hanging, the forearm level, so elbow flexion = 90 - THETA; the barrels level and parallel to the aim line
        (+Y), cant 0, wrist bend <= 8 deg; placeholder pistols in the sprint / round-2 grip.
        V1_LowDual: both upper arms 53 deg (flexion 37), the grip centres 0.26 m apart, centred on the chest.
        V2_LowLead: right upper arm 55 deg (flexion 35) straight forward of the right shoulder; left upper arm 25 deg (flexion 65), the hand low at
        the rib arch / lower chest (25 deg is below the 45..55 of the brief: needed for a level forearm with 65 deg flexion, "close to the body").
RULES = forearm roll <= 18, wrist roll <= 12 deg; arms (the inner upper arm at the armpit excepted), hands and pistols >= 20 mm from vest, pouches and
        holsters (real mesh); barrels <= 3 deg from the aim line; wrist bend <= 8 deg.  When the arm cuts the gear with the elbow straight down, the
        wrist (and with it the whole forearm, staying parallel) is moved OUTWARDS in 1 cm steps and the elbow may swing out a little (4 deg steps)
        until 20 mm hold: the smallest such move is kept and reported (push_cm, swivel_deg, elbow_out_cm).
Layer split: Yoru_Aim_r4_Stand = hips, legs, feet, toes, tail and every other keyed idle bone outside the spine (NLA track 'Stand');
             Yoru_Aim_r4_V1_LowDual / _V2_LowLead = the spine and everything above it (incl. arms, fingers, eyes, ears, hair, bust), no hips keys;
             Yoru_Aim_r4_full_V1 / _full_V2 = both, for measuring and pictures.
Run:  blender -b --factory-startup --python build_aim_r4.py -- <Yoru_V2.glb> <out dir> [idle=<Yoru_Idle_v2.blend>] [design=1]
Writes <out dir>/Yoru_Aim_r4.blend and Yoru_Aim_r4_numbers.json.  Blender: +Y forward (the aim line), her left = -X, up = +Z.
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
IDLE = KV.get('idle', r'C:\Users\valen\ZeroProtocol\Blender\Yoru_Idle_v2.blend')
os.makedirs(OUT, exist_ok=True)
T0 = time.time()


def log(*a):
    print('[aim_r4 %5.1fs]' % (time.time() - T0), *a, flush=True)


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
FING = ('Index', 'Middle', 'Ring', 'Little')
PARTS = ('Proximal', 'Intermediate', 'Distal')


def nm(side, part):
    return H[('left' if side == 'L' else 'right') + part]


def hk(side, part):
    return ('left' if side == 'L' else 'right') + part


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


def signed_angle(a, b, axis):
    ax = axis.normalized()
    a_ = (a - ax * a.dot(ax)).normalized()
    b_ = (b - ax * b.dot(ax)).normalized()
    return math.degrees(math.atan2(a_.cross(b_).dot(ax), a_.dot(b_)))


def qang(a, b):
    x = a.rotation_difference(b).angle
    return math.degrees(min(x, 2.0 * math.pi - x))


# ------------------------------------------------------------------ frame 0 of the idle (local rotations, locations, face shape keys)
def fcurves_of(act):
    out = []
    try:
        out = list(act.fcurves)
    except Exception:
        pass
    if not out:
        for l in act.layers:
            for s in l.strips:
                for cb in s.channelbags:
                    out += list(cb.fcurves)
    return out


with bpy.data.libraries.load(IDLE, link=False) as (src, dst):
    dst.actions = ['Yoru_Idle_v2', 'Yoru_Idle_v2_Face']
IDLE_Q, IDLE_LOC, IDLE_KEYS = {}, {}, {}
for act in dst.actions:
    groups = {}
    for fc in fcurves_of(act):
        groups.setdefault(fc.data_path, {})[fc.array_index] = fc.evaluate(0.0)
    for dp, comp in groups.items():
        if dp.startswith('pose.bones["'):
            bn = dp.split('"')[1]
            if dp.endswith('rotation_quaternion'):
                IDLE_Q[bn] = Quaternion([comp[i] for i in range(4)]).normalized()
            elif dp.endswith('.location'):
                IDLE_LOC[bn] = Vector([comp[i] for i in range(3)])
        elif dp.startswith('key_blocks["'):
            IDLE_KEYS[dp.split('"')[1]] = comp[0]
    bpy.data.actions.remove(act)
missing = [n for n in IDLE_Q if n not in bones]
log('idle frame 0: %d rotations, %d locations, %d shape keys (%s); bones not in this rig: %s' % (
    len(IDLE_Q), len(IDLE_LOC), len(IDLE_KEYS), ', '.join('%s %.3f' % kv for kv in IDLE_KEYS.items()), missing))


def subtree(root):
    out, st = [], [root]
    while st:
        b = st.pop()
        out.append(b.name)
        st.extend(b.children)
    return set(out)


SPINE_TREE = subtree(bones[H['spine']])
ARM_BONES = set()
for _s in ('L', 'R'):
    ARM_BONES |= {nm(_s, p) for p in ('UpperArm', 'LowerArm', 'Hand')}
    ARM_BONES |= {nm(_s, f_ + p_) for f_ in FING + ('Thumb',) for p_ in PARTS if hk(_s, f_ + p_) in H}
COPIED = [n for n in order if n in IDLE_Q and n not in ARM_BONES]
LAYER = [n for n in order if (n in SPINE_TREE and (n in IDLE_Q or n in ARM_BONES))]
STAND = [n for n in order if n in IDLE_Q and n not in SPINE_TREE]
EYES = [H[k] for k in ('leftEye', 'rightEye') if k in H]
log('copied idle bones %d (stand %d, layer %d of which arms are rebuilt: %d)' % (len(COPIED), len(STAND), len(LAYER), len(ARM_BONES)))

# ------------------------------------------------------------------ grip and pistol of the sprint / rounds 1..3 (unchanged)
GRIP = {'Index': (4.0, 10.0, 8.0), 'Middle': (68.0, 74.0, 44.0), 'Ring': (72.0, 78.0, 46.0), 'Little': (75.0, 80.0, 48.0)}
GRIP_SPREAD = {'Index': 22.0, 'Middle': 0.0, 'Ring': -2.0, 'Little': -4.0}
THUMB = (20.0, 30.0, 18.0, 10.0)
GRIP_AT = (0.058, -0.010, 0.020)
PISTOL_BOXES = [((0.0, 0.060, 0.058), (0.026, 0.185, 0.032), 0.0), ((0.0, 0.088, 0.034), (0.022, 0.125, 0.018), 0.0),
                ((0.0, 0.034, 0.016), (0.010, 0.046, 0.010), 0.0), ((0.0, 0.000, 0.000), (0.026, 0.046, 0.096), -12.0)]
BORE = Vector((0.0, 0.0, 0.058))
MUZZLE_Y = 0.060 + 0.185 / 2.0
WR_RULE = 8.0                                                        # round 4: the wrist bend may be at most 8 deg
WR_HARD = 35.0
CLEAR = 0.020
BARREL = Vector((0.0, 1.0, 0.0))                                     # level, parallel to the aim line
UC_YAW, HEAD_YAW = 8.0, -8.0
L_UA = {s: (HEAD0[nm(s, 'LowerArm')] - HEAD0[nm(s, 'UpperArm')]).length for s in ('L', 'R')}
L_FA = {s: (HEAD0[nm(s, 'Hand')] - HEAD0[nm(s, 'LowerArm')]).length for s in ('L', 'R')}
REST_UA = {s: (HEAD0[nm(s, 'LowerArm')] - HEAD0[nm(s, 'UpperArm')]).normalized() for s in ('L', 'R')}
REST_FA = {s: (HEAD0[nm(s, 'Hand')] - HEAD0[nm(s, 'LowerArm')]).normalized() for s in ('L', 'R')}
REST_N = Vector((0.0, 0.0, -1.0))
# theta: upper arm inclined forward from hanging (deg), the forearm level -> flexion 90 - theta; grip_x: the grip centre's x against the chest
# midline (m, None = straight ahead of its own shoulder)
VARIANTS = {
    'V1': dict(name='V1_LowDual', label='V1 LowDual: beide Pistolen auf Brustbeinhoehe, Griffe 0,26 m auseinander', grips_apart=0.26,
               arms={'R': dict(theta=53.0, grip_x=0.13), 'L': dict(theta=53.0, grip_x=-0.13)}),
    'V2': dict(name='V2_LowLead', label='V2 LowLead: rechts vorn auf Brustbeinhoehe, links eng am Rippenbogen',
               arms={'R': dict(theta=55.0, grip_x=None), 'L': dict(theta=25.0, grip_x=None)}),
}


def elbow_ik(S, W, phi, sx, L1, L2):
    """elbow for the wrist target W; phi = swivel about the shoulder-wrist line (0 = elbow straight below the line in its vertical plane,
    + = outwards)"""
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


def compute_pose(V, fit, head_yaw=None):
    """fit[side] = (push m, swivel deg).  Returns Q (local), hips location, D (world deltas), P (joint heads), info"""
    hy = HEAD_YAW if head_yaw is None else head_yaw
    D, P, Q, armc, info = {}, {}, {}, {}, {'head_yaw': hy}
    hips = H['hips']
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        P[name] = HEAD0[name].copy() if parent is None else P[parent] + D[parent] @ (HEAD0[name] - HEAD0[parent])
        if name == hips and hips in IDLE_LOC:
            P[name] = P[name] + R[name] @ IDLE_LOC[name]
        if name in IDLE_Q and name not in ARM_BONES:
            q = IDLE_Q[name].copy()
            if name == H['upperChest']:
                q = q @ Quaternion((0.0, 1.0, 0.0), deg(UC_YAW))      # local yaw about the bone's own axis (local Y = up in this rig)
            elif name == H['head']:
                q = q @ Quaternion((0.0, 1.0, 0.0), deg(hy))
            D[name] = Dp @ (R[name] @ q @ R[name].inverted())
        elif name in ARM_BONES and not name.endswith(('UpperArm', 'LowerArm', 'Hand')):
            side = 'L' if '_L_' in name else 'R'
            sx = -1.0 if side == 'L' else 1.0
            fn = next(f_ for f_ in FING + ('Thumb',) if f_ in name)
            k = int(name[-1]) - 1 if name[-1].isdigit() else 0
            if fn == 'Thumb':
                rel = [eul(rz=-sx * THUMB[0]) @ Quaternion((0, 1, 0), deg(sx * THUMB[1])), Quaternion((0, 1, 0), deg(sx * THUMB[2])),
                       Quaternion((0, 1, 0), deg(sx * THUMB[3]))][k]
            else:
                rel = Quaternion((0, 1, 0), deg(sx * GRIP[fn][k]))
                if k == 0:
                    rel = eul(rz=sx * GRIP_SPREAD[fn]) @ rel
            D[name] = Dp @ rel
        else:
            D[name] = Dp.copy()
        for side, sx in (('L', -1.0), ('R', 1.0)):
            if name == nm(side, 'UpperArm'):
                # round 4 (try 2): the arm by its angles, no IK.  The upper arm is inclined THETA forward from hanging and swung out by ALPHA
                # (the elbow stands out from the body by that much, it still points down and back); the forearm is LEVEL and points straight
                # ahead, turned in by BETA (so the wrist bend = BETA).  The first try (wrist target + elbow swivel) bent the wrist before the
                # elbow came free: the elbow end of the upper arm, in front of the bust, is what touches.
                S = P[name]
                a_ = V['arms'][side]
                th = deg(a_['theta'])
                alpha, beta = fit[side]
                ua = Vector((sx * math.sin(deg(alpha)), math.cos(deg(alpha)) * math.sin(th), -math.cos(deg(alpha)) * math.cos(th))).normalized()
                fo = Vector((-sx * math.sin(deg(beta)), math.cos(deg(beta)), 0.0)).normalized()
                K = S + ua * L_UA[side]
                Weff = K + fo * L_FA[side]
                W, defi, push, phi = Weff.copy(), 0.0, alpha, beta
                ax = ua.cross(fo)
                ax = ax.normalized() if ax.length > 1e-6 else Vector((1.0, 0.0, 0.0))
                n = ax * (-sx)
                Du = aim(REST_UA[side], REST_N, ua, n)
                Df0 = aim(REST_FA[side], REST_N, fo, n)
                ang = math.degrees(fo.angle(BARREL))
                hdir = BARREL.copy() if ang <= WR_HARD else fo.slerp(BARREL, WR_HARD / ang).normalized()
                Dh0 = fo.rotation_difference(hdir) @ Df0
                top = Dh0 @ Vector((0.0, 1.0, 0.0))
                need = -signed_angle(Vector((0.0, 0.0, 1.0)), top, hdir)   # cant 0: roll the pistol top back to upright
                tw_e = max(-18.0, min(18.0, 0.6 * need))
                tw_w = max(-12.0, min(12.0, need - tw_e))
                Df = Quaternion(fo, deg(tw_e)) @ Df0
                Dh = Quaternion(hdir, deg(tw_w)) @ Quaternion(hdir, deg(tw_e)) @ Dh0
                armc[side] = (Du, Df, Dh)
                info[side] = dict(S=S.copy(), K=K.copy(), W=Weff.copy(), W_want=W.copy(), deficit=defi, wrist_bend=ang, tw_e=tw_e, tw_w=tw_w,
                                  push=push, phi=phi, cant0=-need)
                D[name] = Du
            elif name == nm(side, 'LowerArm'):
                D[name] = armc[side][1]
            elif name == nm(side, 'Hand'):
                D[name] = armc[side][2]
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    hips_loc = IDLE_LOC.get(hips, Vector())
    return Q, hips_loc, D, P, info


def chest_mid_x():
    """x of the middle between the shoulder joints in the copied pose (the arms do not change it)"""
    V0 = dict(VARIANTS['V2'], _xc=0.0)
    _, _, _, P0, _ = compute_pose(V0, {'L': (0.0, 0.0), 'R': (0.0, 0.0)})
    return 0.5 * (P0[nm('L', 'UpperArm')].x + P0[nm('R', 'UpperArm')].x)


XC = chest_mid_x()
for _v in VARIANTS.values():
    _v['_xc'] = XC


def gaze_of(D):
    g = (D[H['head']] @ Vector((0.0, 1.0, 0.0))).normalized()
    return math.degrees(math.atan2(g.x, g.y)), math.degrees(math.asin(g.z))


# the head's counter yaw: -8 deg as asked; if the idle's own gaze leaves more than 1 deg, correct it (secant on the local yaw)
_, _, D0, _, _ = compute_pose(VARIANTS['V2'], {'L': (0.0, 0.0), 'R': (0.0, 0.0)})
GAZE_AT_M8 = gaze_of(D0)
if abs(GAZE_AT_M8[0]) > 0.3:                                       # -8 left the gaze 1.0 deg off (at the limit): correct to 0
    y0, y1 = HEAD_YAW, HEAD_YAW + 2.0
    g0 = GAZE_AT_M8[0]
    g1 = gaze_of(compute_pose(VARIANTS['V2'], {'L': (0.0, 0.0), 'R': (0.0, 0.0)}, y1)[2])[0]
    for _ in range(6):
        if abs(g1) < 0.01 or abs(g1 - g0) < 1e-9:                      # converged
            break
        y2 = y1 - g1 * (y1 - y0) / (g1 - g0)
        y0, g0 = y1, g1
        y1 = y2
        g1 = gaze_of(compute_pose(VARIANTS['V2'], {'L': (0.0, 0.0), 'R': (0.0, 0.0)}, y1)[2])[0]
    HEAD_YAW = y1
log('gaze with head -8 deg: yaw %.2f pitch %.2f deg; head local yaw used %.2f deg' % (GAZE_AT_M8[0], GAZE_AT_M8[1], HEAD_YAW))

if DESIGN:
    for key, V in VARIANTS.items():
        Q, hl, D, P, info = compute_pose(V, {'L': (0.0, 0.0), 'R': (0.0, 0.0)})
        for s in ('R', 'L'):
            it = info[s]
            ua, fo = (it['K'] - it['S']).normalized(), (it['W'] - it['K']).normalized()
            log('DESIGN', key, s, 'wrist z %.3f' % it['W'].z, 'upper arm fwd %.1f' % math.degrees(math.acos(-ua.z)),
                'flexion %.1f' % math.degrees(ua.angle(fo)), 'forearm pitch %.1f' % math.degrees(math.asin(fo.z)),
                'wrist bend %.1f' % it['wrist_bend'], 'roll %.1f/%.1f' % (it['tw_e'], it['tw_w']), 'shoulder', [round(x, 3) for x in it['S']])
    sys.exit(0)


# ------------------------------------------------------------------ pistols and the exact clearance (as rounds 1..3b)
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
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
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
    return out


PISTOLS = attach_pistols()


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


def clearance_exact(co=None):
    co = body_coords() if co is None else co
    gear = BVHTree.FromPolygons(co, GEAR_POLYS, all_triangles=False)
    pbs = arm.pose.bones
    res, abvh = {}, {}
    pist = {s: pistol_geometry(s) for s in ('L', 'R')}
    pbvh = {s: BVHTree.FromPolygons(pist[s][0], pist[s][1], all_triangles=False) for s in ('L', 'R')}
    for side in ('L', 'R'):
        sh = arm.matrix_world @ pbs[nm(side, 'UpperArm')].head
        el = arm.matrix_world @ pbs[nm(side, 'LowerArm')].head
        r = {'cut': 0, 'min': 9.0, 'up_min': 9.0, 'up_min_all': 9.0}
        for part in ('UpperArm', 'LowerArm', 'Hand'):
            polys, vids = ARM_PARTS[(side, part)]
            if part == 'UpperArm':
                for v_ in vids:
                    hit = gear.find_nearest(co[v_])
                    if hit[0] is not None:
                        r['up_min_all'] = min(r['up_min_all'], hit[3])
                polys = [pl for pl in polys if intersect_point_line(co[pl[0]], sh, el)[1] > 0.8]
                vids = sorted({v_ for pl in polys for v_ in pl})
            if not polys:
                continue
            tb = BVHTree.FromPolygons(co, polys, all_triangles=False)
            abvh[(side, part)] = tb
            r['cut'] += len(tb.overlap(gear))
            for v_ in vids:
                hit = gear.find_nearest(co[v_])
                if hit[0] is not None:
                    key = 'up_min' if part == 'UpperArm' else 'min'
                    r[key] = min(r[key], hit[3])
        r['pistol_cut'] = len(pbvh[side].overlap(gear))
        r['pistol_min'] = min(gear.find_nearest(s_)[3] for s_ in pist[side][2])
        res[side] = r
    for side, other in (('L', 'R'), ('R', 'L')):
        n_cut = len(pbvh[side].overlap(pbvh[other]))
        for part in ('LowerArm', 'Hand'):
            if (other, part) in abvh:
                n_cut += len(pbvh[side].overlap(abvh[(other, part)]))
        res[side]['pistol_other_cut'] = n_cut
        res[side]['pistol_other_min'] = min((pbvh[other].find_nearest(s_)[3] for s_ in pist[side][2]), default=9.0)
    return res


def side_ok(r):
    return (r['cut'] == 0 and r['min'] >= CLEAR and r['up_min'] >= CLEAR and r['pistol_cut'] == 0 and r['pistol_min'] >= CLEAR
            and r['pistol_other_cut'] == 0)


KEYED = [n for n in order if n in IDLE_Q or n in ARM_BONES]


def set_pose(V, fit):
    ad = arm.animation_data
    if ad and ad.action:
        ad.action = None
    Q, hl, D, P, info = compute_pose(V, fit)
    for n in KEYED:
        pb = arm.pose.bones[n]
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Q[n]
    arm.pose.bones[H['hips']].location = hl
    bpy.context.view_layer.update()
    return Q, hl, D, P, info


# ------------------------------------------------------------------ fit per side: the elbow straight down first; if 20 mm do not hold, move the
# wrist out (the forearm stays parallel) and let the elbow swing out a little, smallest move first
if KV.get('diag') == '1':                                            # which part keeps the arms from the 20 mm (push x swivel table)
    for key, V in VARIANTS.items():
        for side in ('R', 'L'):
            for push_cm in (0, 4, 8, 12):
                for phi in (0.0, 8.0, 16.0, 30.0):
                    f_ = {'L': (0.0, 0.0), 'R': (0.0, 0.0)}
                    f_[side] = (push_cm / 100.0, phi)
                    Q_, hl_, D_, P_, info_ = set_pose(V, f_)
                    r = clearance_exact()[side]
                    log('DIAG %s %s push %2d phi %2.0f: bend %.1f | forearm/hand %.1f mm (%s) elbow-end %.1f pistol %.1f other %d cut %d/%d elbow %s' % (
                        key, side, push_cm, phi, info_[side]['wrist_bend'], 1000 * r['min'], 'ok' if r['min'] >= CLEAR else '--',
                        1000 * r['up_min'], 1000 * r['pistol_min'], r['pistol_other_cut'], r['cut'], r['pistol_cut'],
                        [round(x, 3) for x in info_[side]['K']]))
    sys.exit(0)

fits, fit_log = {}, {}
for key, V in VARIANTS.items():
    fit = {'L': (0.0, 0.0), 'R': (0.0, 0.0)}                         # (alpha = elbow swung out, beta = forearm turned in), deg
    for side in ('R', 'L'):
        done = None
        for alpha in range(0, 46, 2):                                 # the smallest abduction that keeps 20 mm
            f_ = dict(fit)
            f_[side] = (float(alpha), 0.0)
            set_pose(V, f_)
            if side_ok(clearance_exact()[side]):
                done = f_[side]
                break
        if done is None:
            done = (44.0, 0.0)
            fit_log[key + side] = 'no abduction up to 44 deg keeps 20 mm'
        fit[side] = done
        log('fit %s %s: elbow swung out %.0f deg' % (key, side, done[0]))
    if V.get('grips_apart'):                                         # V1: turn the forearms in (wrist bend = beta <= 7) towards 0.26 m
        for beta in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0):
            f_ = {s: (fit[s][0], beta) for s in ('L', 'R')}
            set_pose(V, f_)
            c = clearance_exact()
            if not (side_ok(c['L']) and side_ok(c['R'])):
                break
            fit = f_
            if PISTOLS['R'].matrix_world.translation.x - PISTOLS['L'].matrix_world.translation.x <= V['grips_apart']:
                break
        log('fit %s: forearms turned in %.0f deg' % (key, fit['R'][1]))
    fits[key] = fit


# ------------------------------------------------------------------ keys
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
for key, V in VARIANTS.items():
    Q, hl, D, P, info = compute_pose(V, fits[key])
    if 'Stand' not in acts:
        acts['Stand'] = key_action(Q, hl, STAND, 'Yoru_Aim_r4_Stand', True)
    acts[key] = key_action(Q, hl, LAYER, 'Yoru_Aim_r4_' + V['name'], False)
    acts['full_' + key] = key_action(Q, hl, KEYED, 'Yoru_Aim_r4_full_' + key, True)
ad = arm.animation_data
trk = ad.nla_tracks.new()
trk.name = 'Stand'
strip = trk.strips.new(acts['Stand'].name, 0, acts['Stand'])
if hasattr(strip, 'action_slot') and strip.action_slot is None and len(acts['Stand'].slots):
    strip.action_slot = acts['Stand'].slots[0]
strip.extrapolation = 'HOLD'
if face is not None and face.data.shape_keys:                       # expression B of the idle, frame 0 (set, not keyed)
    for kb in face.data.shape_keys.key_blocks:
        if kb.name != 'Basis':
            kb.value = IDLE_KEYS.get(kb.name, 0.0)


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


# ------------------------------------------------------------------ numbers through the saved full actions
numbers = {'date': '2026-10-30', 'round': 4, 'idle': IDLE, 'upper_chest_local_yaw': UC_YAW, 'head_local_yaw': round(HEAD_YAW, 2),
           'gaze_with_head_minus8': [round(x, 2) for x in GAZE_AT_M8], 'idle_face_keys': IDLE_KEYS, 'clear_needed_mm': 1000 * CLEAR,
           'wrist_rule_deg': WR_RULE, 'stand_bones': STAND, 'layer_bones': LAYER, 'fit_notes': fit_log, 'variants': {}}
for key, V in VARIANTS.items():
    use_action(acts['full_' + key])
    Q, hl, D, P, info = compute_pose(V, fits[key])
    copy_dev = max(qang(arm.pose.bones[n].rotation_quaternion, IDLE_Q[n]) for n in COPIED if n not in (H['upperChest'], H['head']))
    copy_dev_where = max(((qang(arm.pose.bones[n].rotation_quaternion, IDLE_Q[n]), n) for n in COPIED if n not in (H['upperChest'], H['head'])))[1]
    loc_dev = (arm.pose.bones[H['hips']].location - IDLE_LOC.get(H['hips'], Vector())).length
    file_err = max(qang((arm.pose.bones[n].matrix.to_quaternion() @ R[n].inverted()), D[n]) for n in KEYED)
    co = body_coords()
    c = clearance_exact(co)
    gy, gp = gaze_of(D)
    arms_ = {}
    for s, sx in (('R', 1.0), ('L', -1.0)):
        it = info[s]
        S, K, W = it['S'], it['K'], it['W']
        ua, fo = (K - S).normalized(), (W - K).normalized()
        mw = PISTOLS[s].matrix_world
        barrel = (mw.to_3x3() @ Vector((0, 1, 0))).normalized()
        top = (mw.to_3x3() @ Vector((0, 0, 1))).normalized()
        r = c[s]
        arms_[s] = dict(wrist_height_m=round(W.z, 3), grip_world=[round(x, 3) for x in mw.translation], wrist_rel_shoulder=[round(x, 3) for x in (W - S)],
                        upper_arm_from_hanging_deg=round(math.degrees(math.acos(max(-1.0, min(1.0, -ua.z)))), 1),
                        upper_arm_forward_sagittal_deg=round(math.degrees(math.atan2(ua.y, -ua.z)), 1),
                        upper_arm_out_deg=round(math.degrees(math.asin(max(-1.0, min(1.0, sx * ua.x)))), 1),
                        elbow_flexion_deg=round(math.degrees(ua.angle(fo)), 1), elbow_out_cm=round(100.0 * sx * (K.x - S.x), 1),
                        forearm_pitch_deg=round(math.degrees(math.asin(max(-1.0, min(1.0, fo.z)))), 1),
                        forearm_in_deg=round(math.degrees(math.atan2(-sx * fo.x, fo.y)), 1),
                        wrist_bend_deg=round(math.degrees(fo.angle(barrel)), 1),
                        barrel_yaw_deg=round(math.degrees(math.atan2(barrel.x, barrel.y)), 2), barrel_pitch_deg=round(math.degrees(math.asin(barrel.z)), 2),
                        cant_deg=round(sx * signed_angle(Vector((0, 0, 1)), top, barrel), 1), forearm_roll_deg=round(it['tw_e'], 1),
                        wrist_roll_deg=round(it['tw_w'], 1), elbow_swung_out_alpha_deg=it['push'], forearm_in_beta_deg=it['phi'],
                        clearance_mm=dict(forearm_hand=round(1000 * r['min'], 1), upper_arm_elbow_end=round(1000 * r['up_min'], 1),
                                          upper_arm_whole=round(1000 * r['up_min_all'], 1), pistol=round(1000 * r['pistol_min'], 1),
                                          pistol_to_other=round(1000 * r['pistol_other_min'], 1),
                                          cuts=dict(arm=r['cut'], pistol=r['pistol_cut'], pistol_other=r['pistol_other_cut'])))
    gR, gL = PISTOLS['R'].matrix_world.translation, PISTOLS['L'].matrix_world.translation
    use_action(acts[key])
    layer_err = max((arm.matrix_world @ arm.pose.bones[n].head - P[n]).length for n in KEYED)
    numbers['variants'][key] = dict(name=V['name'], label=V['label'], fit=fits[key], arms=arms_,
                                    grips_apart_x_m=round(gR.x - gL.x, 3), grips_apart_m=round((gR - gL).length, 3),
                                    gaze=dict(yaw_right=round(gy, 2), pitch_up=round(gp, 2)),
                                    check=dict(copied_bones_vs_idle_frame0_max_deg=round(copy_dev, 4), worst_bone=copy_dev_where,
                                               hips_location_vs_idle_mm=round(1000 * loc_dev, 3), file_vs_solver_deg=round(file_err, 4),
                                               layer_plus_nla_vs_full_mm=round(1000 * layer_err, 3)))
    log('NUMBERS', key, json.dumps(numbers['variants'][key]))
json.dump(numbers, open(os.path.join(OUT, 'Yoru_Aim_r4_numbers.json'), 'w'), indent=1, default=str)
use_action(acts['V1'])
bpy.context.preferences.filepaths.save_version = 0
path = os.path.join(OUT, 'Yoru_Aim_r4.blend')
bpy.ops.wm.save_as_mainfile(filepath=path)
log('saved', path, '| actions', ', '.join(a.name for a in acts.values()))
log('DONE')
