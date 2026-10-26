"""
Yoru - WALK v2, round 3 (from build_walk_v2_round2.py): Alt | Neu 0,70 | Neu 0,83 | Neu 0,97 side by side in one file (seen from the front:
Alt left).  The three Neu clips come from build_walk.py with bent elbows (e_min 28, E_MAX 66), closer arms (ARM_UP 16, ARM_FORE -4), a tail
that falls and rises again (tail_abs), and per tempo a heel-strike distance / late-swing lift that keeps the knee after the heel strike
below 20 deg (work/Walk_v2/r3_n070, r3_n083, r3_n097; parameters in their build.log).  Round 2 notes below still apply.
  Alt   = the old walk, appended from Blender/Yoru_Walk.blend (the file is only read): 0.70 s, 1.5 m/s
  Neu   = build_walk.py (the old gait generator, unchanged) re-timed to 29 frames / 1.2 m/s with the round 2 settings  (work/Walk_v2/r2_neu)
  Neu+  = the same with about 1.6 x the hip and shoulder motion and more arm swing                                   (work/Walk_v2/r2_neuplus)
  The build commands are in the head of round2 in the report; both are run with
    blender -b --factory-startup --python build_walk.py -- Yoru_V2.glb <out dir> build NF=29 SPEED=1.2 HARM=3 A_HS=0.27 lean=4 BASE=0.034 CIRC=0.050 tail_lat=3.0 ...
On top of the old generator (only for Neu / Neu+): the tail is turned TAIL_YAW deg to her right about the up axis of the pelvis, so the S-curve
reads from the game camera behind her (straight back it was a light blob on the rump); face B 'kuehl-wachsam'; Cycles modifiers (endless loop);
the actions are named Yoru_Walk_v2_Neu / Yoru_Walk_v2_NeuPlus.  Floors: one lane per tempo; each lane scrolls with the ground motion of its gait
(mean speed with the +-5 % wobble of build_walk.py: G(phi) = V T (phi + a / 4 pi sin(4 pi phi))), so planted feet stay on their tiles.
The scene plays 0 .. 608 (609 = 21 x 29 frames: Alt and Neu loop seamlessly together).

Background:  blender -b --factory-startup --python build_walk_v2_round2.py -- <out .blend>
Live (MCP):  append the collection 'Walk_v2_R2' from the saved file (see append_live in this file).
"""
import bpy, os, sys, math, json
from mathutils import Vector, Quaternion, Matrix

BL = r'C:\Users\valen\ZeroProtocol\Blender'
KEYS = ('Alt', 'N070', 'N083', 'N097')
SRC = {'Alt': os.path.join(BL, 'Yoru_Walk.blend'),
       'N070': os.path.join(BL, 'work', 'Walk_v2', 'r3_n070', 'Yoru_Walk.blend'),
       'N083': os.path.join(BL, 'work', 'Walk_v2', 'r3_n083', 'Yoru_Walk.blend'),
       'N097': os.path.join(BL, 'work', 'Walk_v2', 'r3_n097', 'Yoru_Walk.blend')}
X_POS = {'Alt': 1.8, 'N070': 0.6, 'N083': -0.6, 'N097': -1.8}
LABEL = {'Alt': 'Alt', 'N070': 'Neu 0,70', 'N083': 'Neu 0,83', 'N097': 'Neu 0,97'}
GAIT = {'Alt': dict(V=1.5, NF=21, amp=0.05), 'N070': dict(V=1.5, NF=21, amp=0.05), 'N083': dict(V=1.35, NF=25, amp=0.05),
        'N097': dict(V=1.2, NF=29, amp=0.05)}
LANES = {'Alt': (1.2, 9.0), 'N070': (0.0, 1.2), 'N083': (-1.2, 0.0), 'N097': (-9.0, -1.2)}
ROOT = 'Walk_v2_R3'
FPS = 30
PLAY_END = 15224                 # 15225 = 21 x 25 x 29 frames: every clip and its floor loop seamlessly
TAIL_YAW = 20.0
TAIL_ROOT = 'J_Opt_C_CatTail1_01'
FACE_B = {'Fcl_EYE_Angry': 0.40, 'Fcl_EYE_Fun': 0.16, 'Fcl_MTH_Neutral': 0.55, 'Fcl_MTH_Close': 0.20, 'Fcl_BRW_Angry': 0.50}


def log(*a):
    print('[walk_v2 round2]', *a, flush=True)


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


def append_walk(key):
    path = SRC[key]
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None]
    arm = next(o for o in objs if o.type == 'ARMATURE')
    kids = [o for o in objs if o.parent == arm and o.type == 'MESH' and not o.name.startswith('Icosphere')]
    c = coll(ROOT + '_' + key, coll(ROOT))
    c.objects.link(arm)
    for k in kids:
        c.objects.link(k)
        k.name = k.name.split('.')[0] + '_R3_' + key
    arm.name = 'Yoru_R3_' + key
    arm.location = Vector((X_POS[key], 0.0, 0.0))
    return arm, kids


def make_cyclic(action):
    n = 0
    for fc in fcurves(action):
        if not any(m.type == 'CYCLES' for m in fc.modifiers):
            fc.modifiers.new('CYCLES')
            n += 1
    return n


def turn_tail(arm, deg_):
    """turns the tail root about the up axis of the pelvis (pose space) by deg_ (+ = towards her right) in every key"""
    scene = bpy.context.scene
    act = arm.animation_data.action
    dp = 'pose.bones["%s"].rotation_quaternion' % TAIL_ROOT
    fcs = sorted([fc for fc in fcurves(act) if fc.data_path == dp], key=lambda fc: fc.array_index)
    frames = sorted({int(round(k.co.x)) for k in fcs[0].keyframe_points})
    pb = arm.pose.bones[TAIL_ROOT]
    hips = arm.pose.bones['J_Bip_C_Hips']
    R_h = arm.data.bones['J_Bip_C_Hips'].matrix_local.to_quaternion()
    new = {}
    for f in frames:
        scene.frame_set(f)
        D_h = hips.matrix.to_quaternion() @ R_h.inverted()
        up = (D_h @ Vector((0.0, 0.0, 1.0))).normalized()
        M = pb.matrix.copy()
        h = M.translation.copy()
        Mn = Matrix.Translation(h) @ Quaternion(up, math.radians(deg_)).to_matrix().to_4x4() @ Matrix.Translation(-h) @ M
        basis = arm.convert_space(pose_bone=pb, matrix=Mn, from_space='POSE', to_space='LOCAL')
        new[f] = basis.decompose()[1]
    prev = None
    for f in frames:
        q = new[f]
        if prev is not None and prev.dot(q) < 0:
            q = -q
        new[f] = q
        prev = q
    for fc in fcs:
        for k in fc.keyframe_points:
            f = int(round(k.co.x))
            v = new[f][fc.array_index]
            d = v - k.co.y
            k.co.y = v
            k.handle_left.y += d
            k.handle_right.y += d
        fc.update()
    return len(frames)


def face_b(arm):
    for ch in arm.children:
        sk = ch.data.shape_keys if ch.type == 'MESH' else None
        if sk and 'Fcl_EYE_Close' in sk.key_blocks:
            for kb in sk.key_blocks:
                if kb.name != 'Basis' and kb.name != 'Fcl_EYE_Close':
                    kb.value = FACE_B.get(kb.name, 0.0)
            return ch.name
    return None


def ground(key, f):
    g = GAIT[key]
    T = g['NF'] / float(FPS)
    phi = f / float(g['NF'])
    return g['V'] * T * (phi + g['amp'] / (4.0 * math.pi) * math.sin(4.0 * math.pi * phi))


def make_lane(key, x0, x1, tile):
    name = 'Boden_R3_' + key
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x0, -8, 0), (x1, -8, 0), (x1, 8, 0), (x0, 8, 0)], [], [(0, 1, 2, 3)])
    me.uv_layers.new()
    ob = bpy.data.objects.new(name, me)
    coll(ROOT).objects.link(ob)
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
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], chk.inputs['Vector'])
    nt.links.new(chk.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.85
    me.materials.append(mat)
    loc = mp.inputs['Location']
    nf = GAIT[key]['NF']
    for f in range(nf + 1):
        loc.default_value = (0.0, ground(key, f), 0.0)
        loc.keyframe_insert('default_value', index=1, frame=f)
    for fc in fcurves(nt.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'
        m = fc.modifiers.new('CYCLES')
        m.mode_before = 'REPEAT_OFFSET'
        m.mode_after = 'REPEAT_OFFSET'
        fc.update()
    return ob


def make_label(key):
    cu = bpy.data.curves.new('Label_R3_' + key, 'FONT')
    cu.body = LABEL[key]
    cu.size = 0.12
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new('Label_R3_' + key, cu)
    coll(ROOT + '_Beschriftung', coll(ROOT)).objects.link(ob)
    ob.location = (X_POS[key], 0.62, 0.003)
    ob.rotation_euler = (0.0, 0.0, math.pi)
    ob.hide_render = True
    mat = bpy.data.materials.new('Label_R3_' + key + '_Material')
    mat.use_nodes = True
    next(n_ for n_ in mat.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = (0.90, 0.80, 0.40, 1.0)
    cu.materials.append(mat)
    return ob


# ------------------------------------------------------------------ arms: the old generator lets hand and forearm sink into the gear
LIB = r'C:\Users\valen\ZeroProtocol\Blender\scripts\build_walk_v2_lib.py'


def fix_arms(arm, nf=29, hi=16.0, iters=6, margin=0.6):
    """per frame and side the least extra outward turn (deg) of the upper arm about the chest's forward axis through the shoulder joint
    that leaves hand and forearm (beyond the elbow end) with no exact intersection with torso, thighs and gear; dilated, smoothed over
    the loop, checked again and baked into the upper-arm keys.  The swing of the old generator stays as it is."""
    W = {'__file__': LIB}
    exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'), W)
    L = W['L']
    scene = bpy.context.scene
    rig = L['Rig'](arm, L['humanoid_map']())
    tester = W['GearTester'](rig)
    ad = arm.animation_data
    act = ad.action
    slot = getattr(ad, 'action_slot', None)
    pbs = arm.pose.bones
    names = [pb.name for pb in pbs]
    R_uc = arm.data.bones[rig.H['upperChest']].matrix_local.to_quaternion()
    poses = []
    for f in range(nf):
        scene.frame_set(f)
        poses.append({n: (pbs[n].location.copy(), pbs[n].rotation_quaternion.copy(), pbs[n].scale.copy()) for n in names})
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
        dil = [max(raw[(i + d) % nf] for d in range(-2, 3)) for i in range(nf)]
        sm = W['_periodic_smooth'](dil, 1.5)
        for _ in range(3):
            fails = [f for f in range(nf) if bad(f, side, sm[f])]
            if not fails:
                break
            for f in fails:
                for d in range(-2, 3):
                    sm[(f + d) % nf] += 1.0 if d == 0 else 0.5
        extra[side] = sm
    newq = {s: [set_pose(f, s, extra[s][f]) for f in range(nf)] for s in ('L', 'R')}
    ad.action = act
    if slot is not None and hasattr(ad, 'action_slot'):
        ad.action_slot = slot
    for side in ('L', 'R'):
        dp = 'pose.bones["%s"].rotation_quaternion' % rig.nm(side, 'UpperArm')
        fcs = sorted([fc for fc in fcurves(act) if fc.data_path == dp], key=lambda fc: fc.array_index)
        seq, prev = [], None
        for f in range(nf):
            q = newq[side][f]
            if prev is not None and prev.dot(q) < 0:
                q = -q
            seq.append(q)
            prev = q
        for fc in fcs:
            for k in fc.keyframe_points:
                f = int(round(k.co.x)) % nf
                v = seq[f][fc.array_index]
                d = v - k.co.y
                k.co.y = v
                k.handle_left.y += d
                k.handle_right.y += d
            fc.update()
    return {s: (round(min(v), 1), round(max(v), 1)) for s, v in extra.items()}


def build():
    info = {}
    for key in KEYS:
        arm, kids = append_walk(key)
        act = arm.animation_data.action
        if key != 'Alt':
            act.name = 'Yoru_Walk_v2_' + key
            act.use_fake_user = True
            info[key] = dict(cycles_added=make_cyclic(act), tail_keys=turn_tail(arm, TAIL_YAW), face=face_b(arm))
            info[key]['arm_extra_deg'] = fix_arms(arm, nf=GAIT[key]['NF'])
        else:
            info[key] = dict(action=act.name, frame_range=tuple(act.frame_range))
        info[key]['meshes'] = [k.name for k in kids]
    for key in KEYS:                              # tile = stride / 4: one cycle moves the floor by exactly two checker periods
        g = GAIT[key]
        make_lane(key, LANES[key][0], LANES[key][1], g['V'] * g['NF'] / float(FPS) / 4.0)
        make_label(key)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 0, PLAY_END
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
