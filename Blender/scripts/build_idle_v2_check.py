"""
Yoru - IDLE v2: error checks of the baked loop (numbers only; they catch errors, they do not judge the look).
Live (MCP):  ns = {}; exec(open(<this file>).read(), ns); print(ns['check_loop'](bpy.data.objects['Yoru_A2'], nf=360))
Background:  blender -b <stage .blend> --python build_idle_v2_check.py -- [armature name, default Yoru_A2] [frames per loop, default 240]

REUSABLE (walk, run, sprint, any Yoru clip):  arm_gear_check(arm_obj, frames=None, t_min=0.6)
  The corrected measurement of the arms against the torso / thigh / belt gear.  After the glTF import every bone of this rig points UP, so
  pose_bone.tail is NOT on the limb (the old checks in build_idle.py / build_walk.py / build_aim_pose.py sampled head -> tail and missed the arm).
  Here the arm runs from joint to joint (shoulder -> elbow -> wrist -> knuckles), and a mesh test tells how deep visible arm / hand vertices
  sit behind the surface of the visible torso, thigh and gear vertices (the alpha-cut coat hem is ignored).
  Example (any open scene with a Yoru armature; for the old walk file the armature is called 'Armature'):
      import bpy
      ns = {}; exec(open(r'C:\\Users\\valen\\ZeroProtocol\\Blender\\scripts\\build_idle_v2_check.py', encoding='utf-8').read(), ns)
      r = ns['arm_gear_check'](bpy.data.objects['Armature'], frames=range(0, 21, 3))
      print(r['L']['forearm_hand_mm'], r['R']['forearm_hand_mm'])     # deepest forearm / hand / finger vertex inside the gear, per side
  Returned per side: forearm_hand_mm (should be < 5: resting on the gear is fine, sinking in is not), upper_arm_cloth_mm (the elbow half of the
  upper arm against the side of the vest; the armpit half is skipped, cloth against cloth under the arm is hidden, < 15 is fine),
  capsule_clearance_mm (joint-to-joint capsules, upper arm r 40 mm, forearm 33, hand 22, fingers 14; negative = touching), worst frames, where.

arm_mesh_intersections(arm_obj, frames)  (round 6) the EXACT test for the verdict: triangle pairs where arm / hand really cut through
  torso, thighs or gear (BVH overlap), plus how close the hands rest on the gear.  arm_gear_check() above is quick but reports false depths
  of up to about 6 mm where a hand rests on a curved surface (it projects onto the normal of the nearest gear VERTEX).
  Example:  r = ns['arm_mesh_intersections'](bpy.data.objects['Yoru'], range(0, 360, 5))
            r['intersecting_triangle_pairs'] -> {'L Hand': 0, 'L LowerArm': 0, 'L UpperArm': 46, ...}
  The upper arm counts only from the middle to the elbow; the inner sleeve pressing into the side of the vest at armpit height is normal
  for arms that hang close (hidden between arm and body).

screen_motion(arm_obj, frames, ...)  how many pixels the shoulder line moves in the game-camera picture (render camera of
build_idle_v2_render_r2.py 'game', and a camera like the Unity one: field of view 60 deg, 1080 p, 4.4 m behind, 0.35 m to the right).
  - foot sliding: the sole vertices of both shoes over the loop (max distance from their place at frame 0)
  - joint jumps: the largest rotation of any keyed bone from one frame to the next (limit 15 deg)
  - penetrations: arms (mesh test against torso, thighs and gear), legs against each other, tail against the body, soles against the floor
  - seam: frame 240 against frame 0 and the speed across the seam (239 -> 240 against 0 -> 1)
  - ranges: how far the pelvis, the chest, the shoulders, the hands, the head and the tail tip move (so the layers can be judged)
"""
import bpy, sys, os, math

LIB = r'C:\Users\valen\ZeroProtocol\Blender\scripts\build_idle_v2_lib.py'
L = {}
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'), L)


def bone_quats(arm, names, frame):
    bpy.context.scene.frame_set(frame)
    return {n: arm.pose.bones[n].rotation_quaternion.copy() for n in names}


def check_loop(arm, nf=240, sample_step=20):
    scene = bpy.context.scene
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    body = rig.body
    act = arm.animation_data.action
    keyed = sorted({fc.data_path.split('"')[1] for fc in L_action_fcurves(act) if fc.data_path.endswith('rotation_quaternion')})
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    feet = [i for i, n in enumerate(dom) if vis[i] and n in (rig.nm('L', 'Foot'), rig.nm('L', 'Toes'), rig.nm('R', 'Foot'), rig.nm('R', 'Toes'))]
    res = {}
    # --- joint jumps over every frame, and the seam
    prev = bone_quats(arm, keyed, 0)
    first = dict(prev)
    max_jump, where = 0.0, None
    track = {k: [] for k in ('hips', 'upperChest', 'shoulderL', 'handL', 'handR', 'head', 'tail_tip')}
    head_rot = []
    pb = arm.pose.bones
    M = arm.matrix_world
    for f in range(0, nf + 1):
        q = bone_quats(arm, keyed, f) if f > 0 else prev
        if f > 0:
            for n in keyed:
                a = math.degrees(prev[n].rotation_difference(q[n]).angle)
                a = min(a, 360.0 - a)
                if a > max_jump:
                    max_jump, where = a, (n, f)
            prev = q
        track['hips'].append(pb[H['hips']].head.copy())
        track['upperChest'].append(pb[H['upperChest']].head.copy())
        track['shoulderL'].append(pb[rig.nm('L', 'UpperArm')].head.copy())
        track['handL'].append(pb[rig.nm('L', 'Hand')].head.copy())
        track['handR'].append(pb[rig.nm('R', 'Hand')].head.copy())
        track['head'].append(pb[H['head']].head.copy())
        track['tail_tip'].append(pb['J_Opt_C_CatTail8_end_01'].head.copy())
        head_rot.append((pb[H['head']].matrix.to_quaternion()))
    res['max_joint_step_deg'] = round(max_jump, 3)
    res['max_joint_step_at'] = where
    last = bone_quats(arm, keyed, nf)
    res['seam_pose_diff_deg'] = round(max(min(math.degrees(first[n].rotation_difference(last[n]).angle), 360 - math.degrees(first[n].rotation_difference(last[n]).angle)) for n in keyed), 4)
    q1, q239 = bone_quats(arm, keyed, 1), bone_quats(arm, keyed, nf - 1)
    v_start = max(math.degrees(first[n].rotation_difference(q1[n]).angle) % 360 for n in keyed)
    v_end = max(math.degrees(q239[n].rotation_difference(last[n]).angle) % 360 for n in keyed)
    res['seam_speed_deg_per_frame'] = (round(min(v_start, 360 - v_start), 3), round(min(v_end, 360 - v_end), 3))

    def rng(vs):
        xs, ys, zs = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
        return tuple(round((max(a) - min(a)) * 1000.0, 1) for a in (xs, ys, zs))      # mm
    res['range_mm'] = {k: rng(v) for k, v in track.items()}
    hr = head_rot
    res['head_turn_range_deg'] = round(max(math.degrees(hr[0].rotation_difference(h).angle) for h in hr), 2)
    acc = [0.0, 0.0, 0.0, 0.0]                                       # mean orientation of the head over the loop
    for h in hr:
        s = 1.0 if h.dot(hr[0]) >= 0 else -1.0
        for i in range(4):
            acc[i] += s * h[i]
    from mathutils import Quaternion as Qt
    mean = Qt(acc).normalized()
    res['head_from_mean_max_deg'] = round(max(min(math.degrees(mean.rotation_difference(h).angle), 360 - math.degrees(mean.rotation_difference(h).angle)) for h in hr), 2)
    # --- mesh checks on sampled frames
    feet0 = None
    slide = 0.0
    arm_pen = {'L': (0.0, 0.0), 'R': (0.0, 0.0)}
    worst = {'tail_gap': 9.0, 'leg_gap': 9.0, 'sole_min': 9.0, 'sole_max_lift_R': 0.0}
    for f in list(range(0, nf, sample_step)) + [nf - 1]:
        scene.frame_set(f)
        co = L['evaluated_coords'](body)
        pts = [co[i] for i in feet]
        if feet0 is None:
            feet0 = pts
        else:
            slide = max(slide, max((a - b).length for a, b in zip(pts, feet0)))
        p = L['arm_penetration'](rig, 0.6)
        for s in ('L', 'R'):
            arm_pen[s] = (max(arm_pen[s][0], p[s][2]), max(arm_pen[s][1], p[s][3]))
        c = L['run_checks'](rig)
        worst['tail_gap'] = min(worst['tail_gap'], c['tail_gap'])
        worst['leg_gap'] = min(worst['leg_gap'], c['leg_gap'])
        worst['sole_min'] = min(worst['sole_min'], c['sole_min_L'], c['sole_min_R'])
        worst['sole_max_lift_R'] = max(worst['sole_max_lift_R'], c['sole_min_R'])
    res['foot_slide_mm'] = round(slide * 1000.0, 2)
    res['arm_pen_mm (upper arm cloth contact, forearm/hand)'] = {s: (round(v[0] * 1000, 1), round(v[1] * 1000, 1)) for s, v in arm_pen.items()}
    res['tail_gap_min_mm'] = round(worst['tail_gap'] * 1000, 1)
    res['leg_gap_min_mm'] = round(worst['leg_gap'] * 1000, 1)
    res['sole_min_mm'] = round(worst['sole_min'] * 1000, 2)
    scene.frame_set(0)
    return res


def arm_gear_check(arm_obj, frames=None, t_min=0.6):
    """the corrected arm-against-gear measurement (see the head of this file).  frames None = only the current frame."""
    scene = bpy.context.scene
    H = L['humanoid_map']()
    rig = L['Rig'](arm_obj, H)
    if rig.body is None:
        raise RuntimeError('no child mesh called Body* under ' + arm_obj.name)
    cur = scene.frame_current
    frs = [cur] if frames is None else list(frames)
    out = {s: {'forearm_hand_mm': 0.0, 'upper_arm_cloth_mm': 0.0, 'capsule_clearance_mm': 9999.0,
               'worst_frame_forearm': None, 'worst_frame_capsule': None, 'where': None} for s in ('L', 'R')}
    for f in frs:
        if frames is not None:
            scene.frame_set(f)
        pen = L['arm_penetration'](rig, t_min)
        cap = L['arm_clearance'](rig)
        for s in ('L', 'R'):
            o = out[s]
            if pen[s][3] * 1000.0 > o['forearm_hand_mm']:
                o['forearm_hand_mm'] = round(pen[s][3] * 1000.0, 1)
                o['worst_frame_forearm'] = f
                o['where'] = pen[s][4]                                # (vertex, arm bone, body bone) of the deepest forearm / hand point
            o['upper_arm_cloth_mm'] = max(o['upper_arm_cloth_mm'], round(pen[s][2] * 1000.0, 1))
            if cap[s][0] * 1000.0 < o['capsule_clearance_mm']:
                o['capsule_clearance_mm'] = round(cap[s][0] * 1000.0, 1)
                o['worst_frame_capsule'] = (f, cap[s][1])
    if frames is not None:
        scene.frame_set(cur)
    return out


def arm_mesh_intersections(arm_obj, frames, t_min=0.5):
    """EXACT penetration test (round 6): counts triangle pairs where the arm mesh really cuts through the torso / thigh / gear mesh
    (BVHTree.overlap), per side and arm part, over the frames.  0 = nothing passes through.  Use this for the verdict: the quick vertex
    test of arm_gear_check() reports false depths of up to about 6 mm where a hand rests on a curved surface (it projects onto the normal of
    the nearest gear VERTEX).  The upper arm counts only beyond t_min of its length (the armpit end touches the side of the vest by nature).
    Also returns the smallest distance of the hand vertices to the gear surface (m, BVH, unsigned) = how close the hand rests.
    Example:  r = ns['arm_mesh_intersections'](bpy.data.objects['Yoru'], range(0, 360, 10))"""
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import intersect_point_line
    scene = bpy.context.scene
    H = L['humanoid_map']()
    rig = L['Rig'](arm_obj, H)
    nm = rig.nm
    body = rig.body
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    solid = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg']}
    gear_v = set(i for i, n in enumerate(dom) if vis[i] and (n in solid or (n.startswith('J_Sec_') and 'Hair' not in n and 'Bust' not in n)))
    gear_polys = [list(p.vertices) for p in body.data.polygons if all(v in gear_v for v in p.vertices)]
    parts = {}
    for s in ('L', 'R'):
        hand = {nm(s, 'Hand')} | {nm(s, f + p) for f in ('Index', 'Middle', 'Ring', 'Little') for p in ('Proximal', 'Intermediate', 'Distal')} | \
               {nm(s, 'Thumb' + p) for p in ('Proximal', 'Intermediate', 'Distal')}
        parts[(s, 'Hand')] = hand
        parts[(s, 'LowerArm')] = {nm(s, 'LowerArm')}
        parts[(s, 'UpperArm')] = {nm(s, 'UpperArm')}
    part_polys = {k: [list(p.vertices) for p in body.data.polygons if all(dom[v] in bset and vis[v] for v in p.vertices)] for k, bset in parts.items()}
    hand_ids = {s: [i for i, n in enumerate(dom) if vis[i] and n in parts[(s, 'Hand')]] for s in ('L', 'R')}
    cur = scene.frame_current
    res = {k: 0 for k in parts}
    worst_frame = {k: None for k in parts}
    hand_min = {s: 9.0 for s in ('L', 'R')}
    hand_max = {s: 0.0 for s in ('L', 'R')}
    for f in frames:
        scene.frame_set(f)
        co = L['evaluated_coords'](body)
        bg = BVHTree.FromPolygons(co, gear_polys, all_triangles=False)
        for k, polys in part_polys.items():
            use = polys
            if k[1] == 'UpperArm':
                sh, el = arm_obj.pose.bones[nm(k[0], 'UpperArm')].head, arm_obj.pose.bones[nm(k[0], 'LowerArm')].head
                use = [p for p in polys if intersect_point_line(co[p[0]], sh, el)[1] > t_min]
            if not use:
                continue
            n = len(BVHTree.FromPolygons(co, use, all_triangles=False).overlap(bg))
            if n > res[k]:
                res[k], worst_frame[k] = n, f
        for s in ('L', 'R'):
            d = min(bg.find_nearest(co[i])[3] for i in hand_ids[s])
            hand_min[s] = min(hand_min[s], d)
            hand_max[s] = max(hand_max[s], d)
    scene.frame_set(cur)
    return {'intersecting_triangle_pairs': {'%s %s' % k: v for k, v in res.items()}, 'worst_frame': {'%s %s' % k: v for k, v in worst_frame.items()},
            'hand_to_gear_mm': {s: (round(hand_min[s] * 1000, 2), round(hand_max[s] * 1000, 2)) for s in ('L', 'R')}}


def _project(points, cam, target, f_px, size):
    """pinhole projection (camera at cam looking at target, up = world Z), pixel coordinates (x right, y down)"""
    from mathutils import Vector as Vec
    fwd = (target - cam).normalized()
    right = fwd.cross(Vec((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    out = []
    for p in points:
        v = p - cam
        z = v.dot(fwd)
        out.append((size[0] / 2.0 + f_px * v.dot(right) / z, size[1] / 2.0 - f_px * v.dot(up) / z))
    return out


def screen_motion(arm_obj, frames):
    """pixels the shoulder line (middle of both shoulder joints) moves up and down in the game-camera pictures over the given frames"""
    from mathutils import Vector as Vec
    scene = bpy.context.scene
    H = L['humanoid_map']()
    rig = L['Rig'](arm_obj, H)
    M = arm_obj.matrix_world
    base = M.translation.copy()
    cams = {'render_game_720p': (base + Vec((0.35, -4.4, 1.75)), base + Vec((0.0, -0.05, 0.80)), 72.0 / 36.0 * 720.0, (600, 720)),
            'unity_like_1080p': (base + Vec((0.35, -4.30, 2.26)), base + Vec((0.35, 0.0, 1.35)), 540.0 / math.tan(math.radians(30.0)), (1920, 1080))}
    ys = {k: [] for k in cams}
    cur = scene.frame_current
    for f in frames:
        scene.frame_set(f)
        pts = [M @ arm_obj.pose.bones[rig.nm(s, 'UpperArm')].head for s in ('L', 'R')]
        for k, (c, t, fp, size) in cams.items():
            pr = _project(pts, c, t, fp, size)
            ys[k].append(0.5 * (pr[0][1] + pr[1][1]))
    scene.frame_set(cur)
    return {k: round(max(v) - min(v), 2) for k, v in ys.items()}, ys


def secondary_angles(arm_obj, frames):
    """largest swing of hair strands and ears (deg): per joint, and summed down each chain (= how far the tip turns), over the frames"""
    import re as _re
    hair_re = _re.compile(r'^J_Sec_Hair(\d+)_(\d+)$')
    scene = bpy.context.scene
    pbs = arm_obj.pose.bones
    chains = {}
    for pb in pbs:
        m = hair_re.match(pb.name)
        if m:
            chains.setdefault(('hair', int(m.group(2))), []).append(pb.name)
        elif pb.name.startswith(('J_Opt_L_CatEar', 'J_Opt_R_CatEar')) and not pb.name.endswith('_end_01'):
            chains.setdefault(('ear', pb.name[6]), []).append(pb.name)
        elif pb.name.startswith(('J_Sec_L_Bust', 'J_Sec_R_Bust')):
            chains.setdefault(('bust', pb.name[6]), []).append(pb.name)
    cur = scene.frame_current
    base = {}
    best = {'hair_joint': 0.0, 'hair_tip': 0.0, 'ear_joint': 0.0, 'ear_tip': 0.0, 'bust_joint': 0.0}
    rng = {}
    for f in frames:
        scene.frame_set(f)
        for key, names in chains.items():
            tot = 0.0
            for n in names:
                a = math.degrees(pbs[n].rotation_quaternion.angle)
                a = min(a, 360.0 - a)
                tot += a
                kind = key[0]
                if kind + '_joint' in best:
                    best[kind + '_joint'] = max(best[kind + '_joint'], a)
            if key[0] + '_tip' in best:
                best[key[0] + '_tip'] = max(best[key[0] + '_tip'], tot)
    scene.frame_set(cur)
    return {k: round(v, 2) for k, v in best.items()}


def L_action_fcurves(action):
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


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:]
    name = argv[0] if argv else 'Yoru_A2'
    nf = int(argv[1]) if len(argv) > 1 else 240
    print('[idle_v2 check]', check_loop(bpy.data.objects[name], nf=nf), flush=True)
    print('[idle_v2 check] arm_gear_check', arm_gear_check(bpy.data.objects[name], frames=range(0, nf, 10)), flush=True)
    print('[idle_v2 check] screen_motion', screen_motion(bpy.data.objects[name], range(0, nf))[0], flush=True)
