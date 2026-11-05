"""
Yoru - AIM SUITE STAGE 1: checks of the aim-idle loop, measured on the SAVED file (saves nothing but the JSON; the Markdown report is written by
build_aim_s1_media.py from it).
  blender -b --factory-startup <Blender/work/Aim/Yoru_Aim_s1.blend> --python build_aim_s1_check.py -- <out .json> [idle=<Blender/Yoru_Idle_v2.blend>]
          [pose_check=<Yoru_Aim_s1_pose_check.json>] [solver=<Yoru_Aim_s1_solver.json>] [try1=<..._try1_handsfixed_solver.json>] [step=3]
          [compare=<blend of an earlier round, e.g. Blender/work/Aim/Yoru_Aim_s1_r1.blend>]
  (without --factory-startup the user's add-ons print handler errors on every frame change; the numbers are the same)
  round 1: ... Yoru_Aim_s1_report.json;  round 2: ... Yoru_Aim_s1_r2_report.json solver=..._r2_solver.json compare=..._r1.blend
Round 2 adds: the head's world rotation against frame 0 (gaze yaw / pitch as aim_measure.py, roll = twist about the frame-0 gaze, total angle);
with compare=: the four Yoru_Aim_Idle* actions of the earlier round key for key (which bones differ), its gaze per frame, and on the sample frames
the contact test of the idle round 7 (build_idle_v2_check_r7.py: triangle pairs by BVH overlap) for both rounds: hair x torso / neck / shoulders /
vest gear, hair x bust, hair x arms, hair x pistols, hair x face, ears x hair, face x chest / shoulders / bust (no neck: the face mesh joins there).
Every frame 0..360 of Yoru_Aim_Idle (+ Yoru_Aim_Idle_Face): muzzle points (mean of the front vertices of PLATZHALTER_Pistole_L/R, as aim_measure.py),
barrel yaw / pitch, cant, wrist bend, elbow flexion, forearm roll and wrist roll (the round-5 definitions: roll of the forearm about its axis against
the elbow-hinge frame, the hand's extra roll about its axis), arm direction (deg outwards), gaze yaw / pitch (aim_measure.py), shoulder joints,
toe joints (standing-foot drift), joint step per frame (local rotations), the seam 360 vs 0, and the body against Yoru_Idle_v2 key for key.
Every <step>-th frame plus the breathing extremes: the clearance test of aim_measure.py / build_aim_r5.py (forearm + hand, and the elbow end of the
upper arm = its polygons beyond 0.8 of the shoulder-elbow line, against vest, torso, bust, pouches, holsters, thighs of the deformed real mesh; the
inner upper arm at the armpit is left out as before) and the visible share of each pistol in the real game camera (pivot 1.35 m over the middle of
the feet, 4.4 m behind, 0.35 m right, 15 deg down; rays to 3 x 3 samples per camera-facing box face against Body, Face, Hair; build_aim_r5.py).
"""
import bpy, sys, os, math, json, time
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_point_line

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
IDLE = KV.get('idle', r'C:\Users\valen\ZeroProtocol\Blender\Yoru_Idle_v2.blend')
STEP = int(KV.get('step', 3))
COMPARE = os.path.abspath(KV['compare']) if KV.get('compare') else None    # absolute: Blender resolves relative paths against the drive root
NF = 360
T0 = time.time()


def log(*a):
    print('[aim_s1_check %5.1fs]' % (time.time() - T0), *a, flush=True)


scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body, face, hair = bpy.data.objects['Body'], bpy.data.objects.get('Face'), bpy.data.objects.get('Hair')
MW = arm.matrix_world
PB = arm.pose.bones
R = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
HEAD0 = {b.name: b.head_local.copy() for b in arm.data.bones}
PIST = {('L' if o.name.endswith('_L') else 'R'): o for o in bpy.data.objects if o.name.startswith('PLATZHALTER_Pistole')}
ARM3 = {s: ['J_Bip_%s_%s' % (s, p) for p in ('UpperArm', 'LowerArm', 'Hand')] for s in 'LR'}
FINGERS = {s: ['J_Bip_%s_%s%d' % (s, f, k) for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Little') for k in (1, 2, 3)] for s in 'LR'}
ARM_BONES = set(ARM3['L'] + ARM3['R'] + FINGERS['L'] + FINGERS['R'])
SX = {'L': -1.0, 'R': 1.0}
REST_FA = {s: (HEAD0[ARM3[s][2]] - HEAD0[ARM3[s][1]]).normalized() for s in 'LR'}
REST_N = Vector((0.0, 0.0, -1.0))
UC, HEAD = 'J_Bip_C_UpperChest', 'J_Bip_C_Head'


def fcurves_of(act):
    return [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def bone_of(dp):
    return dp.split('"')[1] if dp.startswith('pose.bones["') else None


def qang(a, b):
    x = a.rotation_difference(b).angle
    return math.degrees(min(x, 2.0 * math.pi - x))


def ang(a, b):
    a, b = a.normalized(), b.normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed().to_quaternion()


def aim(rest_dir, rest_nrm, tgt_dir, tgt_nrm):
    return frame_rot(tgt_dir, tgt_nrm) @ frame_rot(rest_dir, rest_nrm).inverted()


def signed_about(q, axis):
    ax, an = q.to_axis_angle()
    a = math.degrees(an) * (1.0 if ax.dot(axis) >= 0 else -1.0)
    return (a + 180.0) % 360.0 - 180.0


# ------------------------------------------------------------------ action set-up
AD = arm.animation_data
ACT = bpy.data.actions['Yoru_Aim_Idle']
AD.action = ACT
if hasattr(AD, 'action_slot') and len(ACT.slots):
    AD.action_slot = ACT.slots[0]
FACT = bpy.data.actions['Yoru_Aim_Idle_Face']
SK = face.data.shape_keys
assert SK.animation_data and SK.animation_data.action == FACT, 'face action not assigned'
KEYED = sorted({bone_of(fc.data_path) for fc in fcurves_of(ACT) if bone_of(fc.data_path)})
FACE_KEYS = sorted({fc.data_path.split('"')[1] for fc in fcurves_of(FACT)})
log('keyed bones', len(KEYED), '| face keys', FACE_KEYS, '| scene fps', scene.render.fps, 'range', scene.frame_start, scene.frame_end)

# ------------------------------------------------------------------ the idle, key for key
with bpy.data.libraries.load(IDLE, link=False) as (src, dst):
    dst.actions = ['Yoru_Idle_v2', 'Yoru_Idle_v2_Face']
I_ACT, I_FACE = dst.actions
FCI = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(I_ACT)}
FCF = {fc.data_path.split('"')[1]: fc for fc in fcurves_of(I_FACE)}


def idle_q(n, f):
    dp = 'pose.bones["%s"].rotation_quaternion' % n
    return Quaternion([FCI[(dp, i)].keyframe_points[f].co[1] for i in range(4)])


def idle_loc(n, f):
    dp = 'pose.bones["%s"].location' % n
    return Vector([FCI[(dp, i)].keyframe_points[f].co[1] for i in range(3)])


# ------------------------------------------------------------------ the earlier round (compare=), loaded next to the current actions (suffix .001)
CMP = {}
if COMPARE and os.path.exists(COMPARE):
    _want = ['Yoru_Aim_Idle', 'Yoru_Aim_Idle_Layer', 'Yoru_Aim_Idle_Stand', 'Yoru_Aim_Idle_Face']
    with bpy.data.libraries.load(COMPARE, link=False) as (src, dst):
        _have = [n for n in _want if n in src.actions]
        dst.actions = list(_have)
    CMP = dict(zip(_have, dst.actions))
    log('compare round loaded from', COMPARE, {k: v.name for k, v in CMP.items()})


def key_diff(a, b):
    """bones (or data paths) whose keys differ between two actions: {name: largest component difference}"""
    fa = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(a)}
    fb = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(b)}
    out = {}
    for k in set(fa) | set(fb):
        name = bone_of(k[0]) or k[0]
        if k not in fa or k not in fb or len(fa[k].keyframe_points) != len(fb[k].keyframe_points):
            out[name] = 'missing or different key count'
            continue
        ka = np.empty(2 * len(fa[k].keyframe_points))
        kb = np.empty(2 * len(fb[k].keyframe_points))
        fa[k].keyframe_points.foreach_get('co', ka)
        fb[k].keyframe_points.foreach_get('co', kb)
        d = float(np.abs(ka - kb).max()) if len(ka) else 0.0
        if d > 1e-7:
            out[name] = max(out.get(name, 0.0), round(d, 6)) if not isinstance(out.get(name), str) else out[name]
    return out


# ------------------------------------------------------------------ mesh sets (aim_measure.py / build_aim_r5.py)
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
DOM = [vg_names.get(max(v.groups, key=lambda g: g.weight).group, '') if v.groups else '' for v in body.data.vertices]
SOLID = {'J_Bip_C_Hips', 'J_Bip_C_Spine', 'J_Bip_C_Chest', 'J_Bip_C_UpperChest', 'J_Bip_L_UpperLeg', 'J_Bip_R_UpperLeg', 'J_Bip_L_LowerLeg', 'J_Bip_R_LowerLeg'}
GEAR = [list(p.vertices) for p in body.data.polygons
        if p.index not in INV and all(VIS[v_] and (DOM[v_] in SOLID or (DOM[v_].startswith('J_Sec_') and 'Hair' not in DOM[v_])) for v_ in p.vertices)]
ARM_PARTS = {}
for s in 'LR':
    hand_set = {'J_Bip_%s_Hand' % s} | set(FINGERS[s])
    for part, bset in (('UpperArm', {'J_Bip_%s_UpperArm' % s}), ('LowerArm', {'J_Bip_%s_LowerArm' % s}), ('Hand', hand_set)):
        polys = [list(p.vertices) for p in body.data.polygons if p.index not in INV and all(DOM[v_] in bset and VIS[v_] for v_ in p.vertices)]
        ARM_PARTS[(s, part)] = polys
NV = len(body.data.vertices)
log('mesh sets: body verts %d, gear polys %d, invisible polys %d' % (NV, len(GEAR), len(INV)))


def mesh_world(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    arr = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get('co', arr)
    polys = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    arr = arr.reshape(-1, 3) @ np.array(ob.matrix_world.to_3x3()).T + np.array(ob.matrix_world.translation)
    return [Vector(c) for c in arr], polys


def pistol_geometry(ob):
    mw = ob.matrix_world
    co = [mw @ v.co for v in ob.data.vertices]
    polys = [list(p.vertices) for p in ob.data.polygons]
    samples = list(co)
    for p in ob.data.polygons:
        vs = [co[i] for i in p.vertices]
        if len(vs) != 4:
            continue
        for a_ in (0.125, 0.375, 0.625, 0.875):
            for b_ in (0.125, 0.375, 0.625, 0.875):
                samples.append(vs[0].lerp(vs[1], a_).lerp(vs[3].lerp(vs[2], a_), b_))
    return co, polys, samples


def clearance(co):
    """forearm + hand and the elbow end of the upper arm against the gear (min distance, cut pairs); pistols against the gear and each other"""
    gear = BVHTree.FromPolygons(co, GEAR, all_triangles=False)
    pg = {s: pistol_geometry(PIST[s]) for s in 'LR'}
    pb_ = {s: BVHTree.FromPolygons(pg[s][0], pg[s][1], all_triangles=False) for s in 'LR'}
    out, abvh = {}, {}
    for s in 'LR':
        sh, el = MW @ PB['J_Bip_%s_UpperArm' % s].head, MW @ PB['J_Bip_%s_LowerArm' % s].head
        r = dict(cut=0, forearm_hand=9.0, elbow_end=9.0, upper_arm_whole=9.0)
        for part in ('UpperArm', 'LowerArm', 'Hand'):
            polys = ARM_PARTS[(s, part)]
            if part == 'UpperArm':
                for v_ in {v_ for pl in polys for v_ in pl}:
                    r['upper_arm_whole'] = min(r['upper_arm_whole'], gear.find_nearest(co[v_])[3])
                polys = [pl for pl in polys if intersect_point_line(co[pl[0]], sh, el)[1] > 0.8]
            if not polys:
                continue
            tb = BVHTree.FromPolygons(co, polys, all_triangles=False)
            abvh[(s, part)] = tb
            r['cut'] += len(tb.overlap(gear))
            key = 'elbow_end' if part == 'UpperArm' else 'forearm_hand'
            for v_ in {v_ for pl in polys for v_ in pl}:
                hit = gear.find_nearest(co[v_])
                if hit[0] is not None:
                    r[key] = min(r[key], hit[3])
        r['pistol_cut'] = len(pb_[s].overlap(gear))
        r['pistol'] = min(gear.find_nearest(q)[3] for q in pg[s][2])
        out[s] = r
    for s, o in (('L', 'R'), ('R', 'L')):
        n = len(pb_[s].overlap(pb_[o]))
        for part in ('LowerArm', 'Hand'):
            if (o, part) in abvh:
                n += len(pb_[s].overlap(abvh[(o, part)]))
        out[s]['pistol_other_cut'] = n
    return out


INV_SET = INV


def visibility(cpos):
    occ_v, occ_p = [], []
    for ob in (body, face, hair):
        if ob is None:
            continue
        co, polys = mesh_world(ob)
        base = len(occ_v)
        occ_v += co
        occ_p += [[base + i for i in p] for pi, p in enumerate(polys) if not (ob is body and pi in INV_SET)]
    occ = BVHTree.FromPolygons(occ_v, occ_p, all_triangles=False)
    out = {}
    for s in 'LR':
        pco, ppolys, _ = pistol_geometry(PIST[s])
        n_all = n_vis = 0
        for fi, pl in enumerate(ppolys):
            vs = [pco[i] for i in pl]
            ctr = sum(vs, Vector()) / 4.0
            bctr = sum(pco[8 * (fi // 6):8 * (fi // 6) + 8], Vector()) / 8.0
            nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0]).normalized()
            if nrm.dot(ctr - bctr) < 0:
                nrm = -nrm
            if nrm.dot(cpos - ctr) <= 0:
                continue
            for a_ in (0.2, 0.5, 0.8):
                for b_ in (0.2, 0.5, 0.8):
                    s_ = vs[0].lerp(vs[1], a_).lerp(vs[3].lerp(vs[2], a_), b_)
                    d_ = s_ - cpos
                    n_all += 1
                    if occ.ray_cast(cpos, d_.normalized(), d_.length - 0.002)[0] is None:
                        n_vis += 1
        out[s] = n_vis / max(n_all, 1)
    return out


# ------------------------------------------------------------------ contacts (idle round 7: triangle pairs by BVH overlap; compared with the earlier round)
def _polys(test):
    return [list(p.vertices) for p in body.data.polygons if p.index not in INV and all(VIS[v_] and test(DOM[v_]) for v_ in p.vertices)]


_TORSO = {'J_Bip_C_Hips', 'J_Bip_C_Spine', 'J_Bip_C_Chest', 'J_Bip_C_UpperChest', 'J_Bip_C_Neck', 'J_Bip_L_Shoulder', 'J_Bip_R_Shoulder'}
C_SETS = dict(
    torso=_polys(lambda n: n in _TORSO or (n.startswith('J_Sec_') and 'Hair' not in n and 'Bust' not in n)),
    bust=_polys(lambda n: 'Bust' in n),
    chest_for_face=_polys(lambda n: n in {'J_Bip_C_Chest', 'J_Bip_C_UpperChest', 'J_Bip_L_Shoulder', 'J_Bip_R_Shoulder'} or 'Bust' in n),
    ears=[list(p.vertices) for p in body.data.polygons if all('CatEar' in DOM[v_] for v_ in p.vertices)],
    arms=[pl for s in 'LR' for part in ('UpperArm', 'LowerArm', 'Hand') for pl in ARM_PARTS[(s, part)]],
    forearm_hand=[pl for s in 'LR' for part in ('LowerArm', 'Hand') for pl in ARM_PARTS[(s, part)]])


def contacts():
    bco, _ = mesh_world(body)
    fco, fpolys = mesh_world(face)
    hco, hpolys = mesh_world(hair)
    bh = BVHTree.FromPolygons(hco, hpolys, all_triangles=False)
    bf = BVHTree.FromPolygons(fco, fpolys, all_triangles=False)
    t = {k: BVHTree.FromPolygons(bco, v, all_triangles=False) for k, v in C_SETS.items()}
    pist = [BVHTree.FromPolygons(*pistol_geometry(PIST[s])[:2], all_triangles=False) for s in 'LR']
    return dict(hair_torso=len(bh.overlap(t['torso'])), hair_bust=len(bh.overlap(t['bust'])), hair_arms=len(bh.overlap(t['arms'])),
                hair_forearm_hand=len(bh.overlap(t['forearm_hand'])),
                hair_pistols=sum(len(bh.overlap(p_)) for p_ in pist), hair_face=len(bh.overlap(bf)), ears_hair=len(t['ears'].overlap(bh)),
                face_chest=len(bf.overlap(t['chest_for_face'])))


def use(act):
    AD.action = act
    if hasattr(AD, 'action_slot') and len(act.slots):
        AD.action_slot = act.slots[0]


def head_world():
    hp = PB[HEAD]
    return MW.to_quaternion() @ hp.matrix.to_quaternion() @ hp.bone.matrix_local.to_quaternion().inverted()


def head_angles(Dh, Dh0):
    """gaze yaw / pitch (aim_measure.py), roll = twist of Dh against Dh0 about the frame-0 gaze, total angle (deg)"""
    fw = (Dh @ Vector((0.0, 1.0, 0.0))).normalized()
    fw0 = (Dh0 @ Vector((0.0, 1.0, 0.0))).normalized()
    d = Dh @ Dh0.inverted()
    if d.w < 0:
        d = -d
    roll = math.degrees(2.0 * math.atan2(Vector((d.x, d.y, d.z)).dot(fw0), d.w))
    return (math.degrees(math.atan2(fw.x, fw.y)), math.degrees(math.asin(max(-1.0, min(1.0, fw.z)))), roll, qang(Dh, Dh0))


# ------------------------------------------------------------------ pass 1: every frame
MUZ_LOCAL = {}
for s in 'LR':
    vs = PIST[s].data.vertices
    ymax = max(v.co.y for v in vs)
    front = [v.co.copy() for v in vs if v.co.y > ymax - 1e-4]
    MUZ_LOCAL[s] = sum(front, Vector()) / len(front)
FR = []
for f in range(NF + 1):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    rec = dict(q={n: PB[n].rotation_quaternion.copy() for n in KEYED}, hips_loc=PB['J_Bip_C_Hips'].location.copy(),
               heads={n: (MW @ PB[n].head).copy() for n in KEYED}, keys={k: SK.key_blocks[k].value for k in FACE_KEYS})
    for s in 'LR':
        sx = SX[s]
        up, lo, ha = ARM3[s]
        S, K, W = MW @ PB[up].head, MW @ PB[lo].head, MW @ PB[ha].head
        ua, fo = (K - S).normalized(), (W - K).normalized()
        n_ = ua.cross(fo).normalized() * (-sx)
        Df = (MW.to_quaternion() @ PB[lo].matrix.to_quaternion()) @ R[lo].inverted()
        Dh = (MW.to_quaternion() @ PB[ha].matrix.to_quaternion()) @ R[ha].inverted()
        Df0 = aim(REST_FA[s], REST_N, fo, n_)
        tw_e = signed_about(Df @ Df0.inverted(), fo)
        hdir = (Dh @ REST_FA[s]).normalized()
        tw = signed_about(Dh @ (fo.rotation_difference(hdir) @ Df0).inverted(), hdir)
        mw = PIST[s].matrix_world
        barrel = (mw.to_3x3() @ Vector((0, 1, 0))).normalized()
        top = (mw.to_3x3() @ Vector((0, 0, 1))).normalized()
        up_ref = (Vector((0, 0, 1)) - barrel * barrel.z).normalized()
        rec[s] = dict(S=S.copy(), K=K.copy(), W=W.copy(), muzzle=(mw @ MUZ_LOCAL[s]).copy(), flex=ang(ua, fo), tw_e=tw_e, tw_w=tw - tw_e,
                      wrist_bend=ang(fo, barrel), barrel_yaw=math.degrees(math.atan2(barrel.x * sx, barrel.y)),
                      barrel_pitch=math.degrees(math.asin(max(-1.0, min(1.0, barrel.z)))),
                      cant=math.degrees(math.atan2(barrel.dot(up_ref.cross(top)), up_ref.dot(top))) * sx,
                      arm_out=math.degrees(math.atan2(sx * (W - S).x, (W - S).y)))
    rec['Dhead'] = head_world()
    rec['gaze'] = head_angles(rec['Dhead'], FR[0]['Dhead'] if FR else rec['Dhead'])[:2]
    FR.append(rec)
for rec in FR:
    rec['head'] = head_angles(rec['Dhead'], FR[0]['Dhead'])           # yaw, pitch, roll vs frame 0, total
log('pass 1 done (%d frames)' % len(FR))
GAZE_CMP = None
if 'Yoru_Aim_Idle' in CMP:                                           # the earlier round's head, same measure (frame 0 is the same pose)
    use(CMP['Yoru_Aim_Idle'])
    _d = []
    for f in range(NF + 1):
        scene.frame_set(f)
        _d.append(head_world())
    GAZE_CMP = [head_angles(d, _d[0]) for d in _d]
    use(ACT)
    scene.frame_set(0)


def rng(vals):
    return [round(min(vals), 3), round(max(vals), 3)]


summ = {}
sh_z = [0.5 * (r['L']['S'].z + r['R']['S'].z) for r in FR]
sh_y = [0.5 * (r['L']['S'].y + r['R']['S'].y) for r in FR]
for s in 'LR':
    mz = [r[s]['muzzle'].z for r in FR]
    m0 = FR[0][s]['muzzle']
    summ[s] = dict(
        muzzle_vertical_p2p_mm=round(1000 * (max(mz) - min(mz)), 3),
        muzzle_vertical_max_vs_f0_mm=round(1000 * max(abs(z - m0.z) for z in mz), 3),
        muzzle_3d_max_vs_f0_mm=round(1000 * max((r[s]['muzzle'] - m0).length for r in FR), 3),
        muzzle_side_max_vs_f0_mm=round(1000 * max(abs(r[s]['muzzle'].x - m0.x) for r in FR), 3),
        muzzle_along_aim_max_vs_f0_mm=round(1000 * max(abs(r[s]['muzzle'].y - m0.y) for r in FR), 3),
        elbow_flex_deg=rng([r[s]['flex'] for r in FR]), forearm_roll_deg=rng([r[s]['tw_e'] for r in FR]),
        wrist_roll_deg=rng([r[s]['tw_w'] for r in FR]), wrist_bend_deg=rng([r[s]['wrist_bend'] for r in FR]),
        cant_deg=rng([r[s]['cant'] for r in FR]), barrel_yaw_deg=rng([r[s]['barrel_yaw'] for r in FR]),
        barrel_pitch_deg=rng([r[s]['barrel_pitch'] for r in FR]), arm_out_deg=rng([r[s]['arm_out'] for r in FR]),
        shoulder_joint_p2p_mm=[round(1000 * (max(r[s]['S'][i] for r in FR) - min(r[s]['S'][i] for r in FR)), 2) for i in range(3)])
summ['arms_apart_deg'] = rng([r['L']['arm_out'] + r['R']['arm_out'] for r in FR])
summ['gaze_yaw_deg'] = rng([r['gaze'][0] for r in FR])
summ['gaze_pitch_deg'] = rng([r['gaze'][1] for r in FR])
summ['head_vs_frame0'] = dict(yaw_deg=rng([r['head'][0] - FR[0]['head'][0] for r in FR]), pitch_deg=rng([r['head'][1] - FR[0]['head'][1] for r in FR]),
                              roll_deg=rng([r['head'][2] for r in FR]), total_max_deg=round(max(r['head'][3] for r in FR), 4))
if GAZE_CMP:
    summ['head_vs_frame0_compare_round'] = dict(yaw_deg=rng([g[0] - GAZE_CMP[0][0] for g in GAZE_CMP]), pitch_deg=rng([g[1] - GAZE_CMP[0][1] for g in GAZE_CMP]),
                                                roll_deg=rng([g[2] for g in GAZE_CMP]), total_max_deg=round(max(g[3] for g in GAZE_CMP), 4))
summ['shoulder_mean_z_p2p_mm'] = round(1000 * (max(sh_z) - min(sh_z)), 2)
# standing feet (toe joints, as the idle check)
for s in 'LR':
    toe = [r['heads']['J_Bip_%s_ToeBase' % s] for r in FR]
    t0 = toe[0]
    lo_ = [min(t[i] for t in toe) for i in range(3)]
    hi_ = [max(t[i] for t in toe) for i in range(3)]
    summ['toe_%s_max_vs_f0_mm' % s] = round(1000 * max((t - t0).length for t in toe), 3)
    summ['toe_%s_box_diag_mm' % s] = round(1000 * math.dist(lo_, hi_), 3)
# joint step per frame (local rotations; frame 359 -> 360 is the step into the seam)
steps = []
for f in range(NF):
    a_, b_ = FR[f]['q'], FR[f + 1]['q']
    for n in KEYED:
        steps.append((qang(a_[n], b_[n]), n, f))
steps.sort(reverse=True)
summ['joint_step_max'] = [round(steps[0][0], 3), steps[0][1], steps[0][2]]
summ['joint_step_max_arms'] = next([round(x, 3), n, f] for x, n, f in steps if n in ARM_BONES)
summ['joint_step_max_hips_spine_head'] = next([round(x, 3), n, f] for x, n, f in steps if n.startswith('J_Bip_C'))
summ['joint_step_max_head'] = next([round(x, 3), n, f] for x, n, f in steps if n == HEAD)
idle_steps = max((qang(idle_q(n, f), idle_q(n, f + 1)), n, f) for n in KEYED for f in range(NF))
summ['joint_step_max_in_idle_v2'] = [round(idle_steps[0], 3), idle_steps[1], idle_steps[2]]
# seam
summ['seam_rot_max_deg'] = round(max(qang(FR[0]['q'][n], FR[NF]['q'][n]) for n in KEYED), 6)
summ['seam_joint_max_mm'] = round(1000 * max((FR[0]['heads'][n] - FR[NF]['heads'][n]).length for n in KEYED), 6)
summ['seam_muzzle_max_mm'] = round(1000 * max((FR[0][s]['muzzle'] - FR[NF][s]['muzzle']).length for s in 'LR'), 6)
summ['seam_face_keys_max'] = round(max(abs(FR[0]['keys'][k] - FR[NF]['keys'][k]) for k in FACE_KEYS), 6)
# body against the idle, key for key
dev, devw = 0.0, None
off0 = {n: idle_q(n, 0).inverted() @ FR[0]['q'][n] for n in (UC, HEAD)}
off_dev = {n: 0.0 for n in (UC, HEAD)}
for f in range(NF + 1):
    for n in KEYED:
        if n in ARM_BONES:
            continue
        if n in off0:
            off_dev[n] = max(off_dev[n], qang(idle_q(n, f).inverted() @ FR[f]['q'][n], off0[n]))
            continue
        d_ = qang(idle_q(n, f), FR[f]['q'][n])
        if d_ > dev:
            dev, devw = d_, (n, f)
summ['body_vs_idle_max_deg'] = round(dev, 6)
summ['body_vs_idle_worst'] = devw
summ['hips_loc_vs_idle_max_mm'] = round(1000 * max((idle_loc('J_Bip_C_Hips', f) - FR[f]['hips_loc']).length for f in range(NF + 1)), 6)
summ['offset_upper_chest_yaw_deg'] = round(math.degrees(2.0 * math.atan2(off0[UC].y, off0[UC].w)), 4)
summ['offset_head_yaw_deg'] = round(math.degrees(2.0 * math.atan2(off0[HEAD].y, off0[HEAD].w)), 4)
summ['offset_constancy_max_deg'] = {n: round(v, 6) for n, v in off_dev.items()}
summ['face_vs_idle_max'] = round(max(abs(FCF[k].evaluate(float(f)) - FR[f]['keys'][k]) for k in FACE_KEYS for f in range(NF + 1)), 6)
summ['arm_bones_compared'] = 'not compared (rebuilt)'
# the pose V2 at frame 0
POSE = bpy.data.actions['Yoru_Aim_Pose_V2_full']
FCP = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(POSE)}
summ['frame0_vs_pose_V2_max_deg'] = round(max(qang(Quaternion([FCP[('pose.bones["%s"].rotation_quaternion' % n, i)].evaluate(0.0) for i in range(4)]),
                                                   FR[0]['q'][n]) for n in KEYED), 6)
log('summary', json.dumps(summ))

# ------------------------------------------------------------------ pass 2: clearance and visibility on a sample
ext = {int(np.argmax(sh_z)), int(np.argmin(sh_z)), int(np.argmax(sh_y)), int(np.argmin(sh_y))}
SAMPLE = sorted(set(range(0, NF + 1, STEP)) | ext)
fl, fr_ = MW @ PB['J_Bip_L_Foot'].head, MW @ PB['J_Bip_R_Foot'].head
scene.frame_set(0)
fl, fr_ = MW @ PB['J_Bip_L_Foot'].head, MW @ PB['J_Bip_R_Foot'].head
FEET = Vector((0.5 * (fl.x + fr_.x), 0.5 * (fl.y + fr_.y), 0.0))
p = math.radians(15.0)
CAM = Vector((FEET.x + 0.35, FEET.y - 4.4 * math.cos(p), 1.35 + 4.4 * math.sin(p)))
CL, VI = {}, {}
for i, f in enumerate(SAMPLE):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    co, _ = mesh_world(body)
    CL[f] = clearance(co)
    VI[f] = visibility(CAM)
    if i % 20 == 0:
        log('sample %d/%d frame %d: %s | vis %s' % (i + 1, len(SAMPLE), f, json.dumps({s: {k: round(v * 1000, 1) if isinstance(v, float) else v
                                                                                            for k, v in CL[f][s].items()} for s in 'LR'}),
                                                    {s: round(v, 3) for s, v in VI[f].items()}))
for s in 'LR':
    for key in ('forearm_hand', 'elbow_end', 'upper_arm_whole', 'pistol'):
        f_min = min(SAMPLE, key=lambda f: CL[f][s][key])
        summ[s]['clear_%s_min_mm' % key] = [round(1000 * CL[f_min][s][key], 2), f_min]
    summ[s]['cuts_arm_total'] = sum(CL[f][s]['cut'] for f in SAMPLE)
    summ[s]['cuts_pistol_total'] = sum(CL[f][s]['pistol_cut'] + CL[f][s]['pistol_other_cut'] for f in SAMPLE)
    f_v = min(SAMPLE, key=lambda f: VI[f][s])
    summ[s]['visible_game_min'] = [round(VI[f_v][s], 3), f_v]
    summ[s]['visible_game_max'] = round(max(VI[f][s] for f in SAMPLE), 3)
    summ[s]['visible_game_frame0'] = round(VI[0][s], 3)
summ['sample_frames'] = dict(step=STEP, count=len(SAMPLE), breathing_extremes=sorted(ext))
summ['game_camera'] = [round(v, 4) for v in CAM]
log('clearance / visibility done')

# ------------------------------------------------------------------ pass 3: contacts (this round and the earlier one) and the key comparison
CONTACTS = {}
for tag, a in [('this', ACT)] + ([('compare', CMP['Yoru_Aim_Idle'])] if 'Yoru_Aim_Idle' in CMP else []):
    use(a)
    CONTACTS[tag] = {}
    for f in SAMPLE:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        CONTACTS[tag][f] = contacts()
    log('contacts', tag, {k: max(CONTACTS[tag][f][k] for f in SAMPLE) for k in CONTACTS[tag][SAMPLE[0]]})
use(ACT)
scene.frame_set(0)
csum = {}
for k in CONTACTS['this'][SAMPLE[0]]:
    row = dict(max_this=max(CONTACTS['this'][f][k] for f in SAMPLE), frame0=CONTACTS['this'][0][k])
    if 'compare' in CONTACTS:
        inc = [(CONTACTS['this'][f][k] - CONTACTS['compare'][f][k], f) for f in SAMPLE]
        row.update(max_compare=max(CONTACTS['compare'][f][k] for f in SAMPLE), max_increase=max(inc)[0], frame_of_max_increase=max(inc)[1],
                   frames_with_more=sum(1 for d_, _ in inc if d_ > 0), frames_with_less=sum(1 for d_, _ in inc if d_ < 0))
    csum[k] = row
summ['contacts_triangle_pairs'] = csum
KEYDIFF = {}
for n, a in CMP.items():
    cur = bpy.data.actions.get(n)
    if cur is not None:
        KEYDIFF[n] = key_diff(cur, a)
summ['keys_vs_compare_round'] = KEYDIFF
if 'Yoru_Aim_Idle' in CMP:                                           # the earlier round's head step (local keys)
    _fc = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(CMP['Yoru_Aim_Idle'])}
    _dp = 'pose.bones["%s"].rotation_quaternion' % HEAD
    _hq = [Quaternion([_fc[(_dp, i)].keyframe_points[f].co[1] for i in range(4)]) for f in range(NF + 1)]
    _st = max((qang(_hq[f], _hq[f + 1]), f) for f in range(NF))
    summ['compare_joint_step_max_head'] = [round(_st[0], 3), HEAD, _st[1]]
log('contacts', json.dumps(csum), '| keys differ', json.dumps(KEYDIFF))

# ------------------------------------------------------------------ write
per_frame = dict(t=[f / 30.0 for f in range(NF + 1)], shoulder_mean_z_mm=[1000 * (z - sh_z[0]) for z in sh_z],
                 shoulder_mean_y_mm=[1000 * (y - sh_y[0]) for y in sh_y])
for s in 'LR':
    per_frame['muzzle_%s_z_mm' % s] = [1000 * (r[s]['muzzle'].z - FR[0][s]['muzzle'].z) for r in FR]
    per_frame['muzzle_%s_y_mm' % s] = [1000 * (r[s]['muzzle'].y - FR[0][s]['muzzle'].y) for r in FR]
    per_frame['muzzle_%s_3d_mm' % s] = [1000 * (r[s]['muzzle'] - FR[0][s]['muzzle']).length for r in FR]
    per_frame['shoulder_%s_z_mm' % s] = [1000 * (r[s]['S'].z - FR[0][s]['S'].z) for r in FR]
    per_frame['elbow_flex_%s' % s] = [r[s]['flex'] for r in FR]
    per_frame['visible_%s' % s] = {str(f): VI[f][s] for f in SAMPLE}
    per_frame['clear_forearm_hand_%s_mm' % s] = {str(f): 1000 * CL[f][s]['forearm_hand'] for f in SAMPLE}
    per_frame['clear_elbow_end_%s_mm' % s] = {str(f): 1000 * CL[f][s]['elbow_end'] for f in SAMPLE}
per_frame['head_yaw_deg'] = [r['head'][0] - FR[0]['head'][0] for r in FR]
per_frame['head_pitch_deg'] = [r['head'][1] - FR[0]['head'][1] for r in FR]
per_frame['head_roll_deg'] = [r['head'][2] for r in FR]
if GAZE_CMP:
    per_frame['compare_head_yaw_deg'] = [g[0] - GAZE_CMP[0][0] for g in GAZE_CMP]
    per_frame['compare_head_pitch_deg'] = [g[1] - GAZE_CMP[0][1] for g in GAZE_CMP]
    per_frame['compare_head_roll_deg'] = [g[2] for g in GAZE_CMP]
per_frame['contacts'] = {tag: {str(f): v for f, v in d_.items()} for tag, d_ in CONTACTS.items()}
res = dict(date='2026-10-31', stage=1, round=int(KV.get('round', 2 if COMPARE else 1)), file=bpy.data.filepath, compare=COMPARE,
           action='Yoru_Aim_Idle', face_action='Yoru_Aim_Idle_Face', frames=NF + 1, fps=30, summary=summ, per_frame=per_frame)
for k in ('pose_check', 'solver', 'try1'):
    if KV.get(k) and os.path.exists(KV[k]):
        d_ = json.load(open(KV[k]))
        if k == 'pose_check':
            res['step0_pose_check'] = {kk: d_[kk] for kk in ('actions_after', 'active_on_open', 'nla', 'pistols', 'full_vs_r5_full_V2_frame0',
                                                             'layer_plus_nla_stand_vs_r5_full_V2_frame0')}
        else:
            pf = d_['per_frame']
            res[k + '_solver'] = dict(follow=d_.get('follow', 'none (hands fixed in all 3 axes)'),
                                      flex_deg={s: rng([x['flex'] for x in pf[s]]) for s in 'LR'},
                                      reach_deficit_max_mm={s: round(max(x['deficit_mm'] for x in pf[s]), 2) for s in 'LR'},
                                      shoulder_wrist_mm={s: rng([x['dist_mm'] for x in pf[s]]) for s in 'LR'},
                                      wrist_slide_mm={s: rng([x.get('wrist_slide_mm', 0.0) for x in pf[s]]) for s in 'LR'})
            if k == 'try1':
                res['try1_solver']['elbow_flex_per_frame'] = {s: [x['flex'] for x in pf[s]] for s in 'LR'}
json.dump(res, open(OUT, 'w'), indent=1, default=lambda o: list(o) if hasattr(o, '__len__') else str(o))
log('wrote', OUT)
log('DONE')
