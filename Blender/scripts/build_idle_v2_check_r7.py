"""
Yoru - IDLE v2, round 7: checks for ears, tail and hair (numbers only; compare two actions on the same Yoru).
Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>).read(), ns)
             ns['motion'](arm, 'Yoru_Idle_v2', 'Yoru_Idle_v2_r7')       -> ranges in mm and pixels (game camera, front three-quarter)
             ns['contacts'](arm, 'Yoru_Idle_v2_r7', frames)               -> hair vs body / gear / face, ears vs hair, tail clearance
Background:  blender -b --factory-startup <file> --python build_idle_v2_check_r7.py -- <armature> <action new> [action old]
  - hair tips: the hair vertex farthest from its last joint on each long strand (chains 3, 4, 5, 6, 18, 19), the side locks (1, 2) and the
    fringe (9 .. 12); ear tips (CatEar2_end), tail tip (CatTail8_end)
  - pixels: render camera 'game' of build_idle_v2_render_r2.py (72 mm, 600 x 720, 4.4 m behind, 0.35 m right) and the orthographic
    'front34' still (2 m over 720 px)
  - intersections: triangle pairs (BVH overlap) of the hair mesh against the visible torso / shoulders / gear and against the face; of the
    ears (body vertices of the ear bones) against the hair mesh; compared frame by frame with the old action
  - tail: least distance of the tail (joints 3+) to hips / legs / coat (run_checks), every frame step
"""
import bpy, sys, os, math, re
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(HERE, 'build_idle_v2_lib.py')):
    HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
L = {}
exec(compile(open(os.path.join(HERE, 'build_idle_v2_lib.py'), encoding='utf-8').read(), os.path.join(HERE, 'build_idle_v2_lib.py'), 'exec'), L)
HAIR_RE = re.compile(r'^J_Sec_Hair(\d+)_(\d+)$')
CH = {'long': (3, 4, 5, 6, 18, 19), 'side': (1, 2), 'fringe': (9, 10, 11, 12)}


def set_action(arm, name):
    ad = arm.animation_data
    act = bpy.data.actions[name]
    ad.action = act
    if hasattr(ad, 'action_slot') and act.slots:
        ad.action_slot = act.slots[0]


def _children(arm):
    hair = next(c for c in arm.children if c.type == 'MESH' and c.name.startswith('Hair'))
    face = next(c for c in arm.children if c.type == 'MESH' and c.name.startswith('Face'))
    body = next(c for c in arm.children if c.type == 'MESH' and c.name.startswith('Body'))
    return body, face, hair


def _dominant(obj):
    names = {vg.index: vg.name for vg in obj.vertex_groups}
    out = []
    for v in obj.data.vertices:
        out.append(names[max(v.groups, key=lambda g: g.weight).group] if v.groups else '')
    return out


def _eval(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    co = [v.co.copy() for v in me.vertices]
    ev.to_mesh_clear()
    return co


def tip_vertices(arm):
    """per tracked strand the hair vertex farthest from the last joint of its chain (rest pose)"""
    body, face, hair = _children(arm)
    dom = _dominant(hair)
    bones = arm.data.bones
    chains = {}
    for b in bones:
        m = HAIR_RE.match(b.name)
        if m:
            chains.setdefault(int(m.group(2)), []).append((int(m.group(1)), b.name))
    out = {}
    for c, lst in chains.items():
        names = set(n for _, n in lst)
        root = bones[sorted(lst)[0][1]].head_local
        # the vertices of a strand mostly belong to its middle joints (the last joint has hardly any): take the vertex of the whole
        # chain that lies farthest from the root
        ids = [i for i, n in enumerate(dom) if n in names]
        if not ids:
            continue
        i = max(ids, key=lambda k: (hair.data.vertices[k].co - root).length)
        out[c] = i
    return out


def _project_persp(p, cam, target, f_px, size):
    fwd = (target - cam).normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    v = p - cam
    z = v.dot(fwd)
    return (size[0] / 2.0 + f_px * v.dot(right) / z, size[1] / 2.0 - f_px * v.dot(up) / z)


def _project_ortho(p, eye_dir, target, px_per_m, size):
    fwd = -eye_dir.normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    v = p - target
    return (size[0] / 2.0 + v.dot(right) * px_per_m, size[1] / 2.0 - v.dot(up) * px_per_m)


def motion(arm, old_action, new_action, step=2):
    """range of the tracked points over the loop: (mm x, mm y, mm z, px game x, px game y, px front34 x, px front34 y)"""
    sc = bpy.context.scene
    body, face, hair = _children(arm)
    tips = tip_vertices(arm)
    M = arm.matrix_world
    base = M.translation.copy()
    cam_g, tgt_g = base + Vector((0.35, -4.4, 1.75)), base + Vector((0.0, -0.05, 0.80))
    a35 = math.radians(35.0)
    eye34 = Vector((6 * math.sin(a35), 6 * math.cos(a35), 1.3 - 0.8))
    tgt34 = base + Vector((0.0, -0.05, 0.80))
    res = {}
    for act in (old_action, new_action):
        set_action(arm, act)
        tracks = {}
        for f in range(0, sc.frame_end + 1, step):
            sc.frame_set(f)
            hc = _eval(hair)
            pts = {}
            for group, chs in CH.items():
                for c in chs:
                    if c in tips:
                        pts['hair_%s_%d' % (group, c)] = M @ hc[tips[c]]
            for s in 'LR':
                pts['ear_' + s] = M @ arm.pose.bones['J_Opt_%s_CatEar2_end_01' % s].head
            pts['tail_tip'] = M @ arm.pose.bones['J_Opt_C_CatTail8_end_01'].head
            for k, p in pts.items():
                tracks.setdefault(k, []).append(p)
        out = {}
        for k, ps in tracks.items():
            mm = [round((max(p[i] for p in ps) - min(p[i] for p in ps)) * 1000.0, 1) for i in range(3)]
            g = [_project_persp(p, cam_g, tgt_g, 72.0 / 36.0 * 720.0, (600, 720)) for p in ps]
            o = [_project_ortho(p, eye34, tgt34, 360.0, (600, 720)) for p in ps]
            pg = [round(max(q[i] for q in g) - min(q[i] for q in g), 1) for i in range(2)]
            po = [round(max(q[i] for q in o) - min(q[i] for q in o), 1) for i in range(2)]
            out[k] = (mm, pg, po)
        res[act] = out
    sc.frame_set(0)
    return res


def contacts(arm, action, frames):
    """per frame: hair x body/gear and hair x face triangle pairs, ears x hair pairs, tail clearance (m)"""
    sc = bpy.context.scene
    set_action(arm, action)
    body, face, hair = _children(arm)
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    solid = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['neck'], H['leftShoulder'], H['rightShoulder'],
             H['leftUpperArm'], H['rightUpperArm']}
    body_polys = [list(p.vertices) for p in body.data.polygons
                  if all(vis[v] and (dom[v] in solid or (dom[v].startswith('J_Sec_') and 'Hair' not in dom[v] and 'Bust' not in dom[v])) for v in p.vertices)]
    ear_polys = [list(p.vertices) for p in body.data.polygons if all('CatEar' in dom[v] for v in p.vertices)]
    hair_polys = [list(p.vertices) for p in hair.data.polygons]
    face_polys = [list(p.vertices) for p in face.data.polygons]
    out = []
    for f in frames:
        sc.frame_set(f)
        bc, fc, hc = _eval(body), _eval(face), _eval(hair)
        bh = BVHTree.FromPolygons(hc, hair_polys, all_triangles=False)
        bb = BVHTree.FromPolygons(bc, body_polys, all_triangles=False)
        bf = BVHTree.FromPolygons(fc, face_polys, all_triangles=False)
        be = BVHTree.FromPolygons(bc, ear_polys, all_triangles=False)
        c = L['run_checks'](rig)
        out.append(dict(frame=f, hair_body=len(bh.overlap(bb)), hair_face=len(bh.overlap(bf)), ears_hair=len(be.overlap(bh)),
                        tail_gap_mm=round(c['tail_gap'] * 1000.0, 1)))
    sc.frame_set(0)
    return out


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    arm = bpy.data.objects[argv[0]]
    new = argv[1]
    old = argv[2] if len(argv) > 2 else None
    if old:
        print('[check r7] motion', motion(arm, old, new), flush=True)
    rows = contacts(arm, new, range(0, 360, 10))
    print('[check r7] contacts', rows, flush=True)
