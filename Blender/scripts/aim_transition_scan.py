"""
Yoru - TRANSITION SCAN (main agent, saves nothing but the optional JSON).  Written 2026-10-31 for the stage-2 review (Aim_In, Sprint_To_Aim, Aim_Out).
  blender -b <blend> --python aim_transition_scan.py -- [out.json=<path>] [belt=<z in m>] [zone_from=<action>] [last=<n>] <action> [<action> ...]
For EVERY frame of every action (first to last key frame, whole numbers; the action alone, no NLA).  World: +Y forward, her right = +X, up = +Z; mm and deg.
Gear polygons = the same set as aim_measure.py (vest, torso, thighs, skirt pieces, no hair, alpha-cut polygons dropped).  They are split ONCE (in the pose of zone_from,
default Yoru_Aim_Pose_V2_full) into  low = centroid below the belt line (hip and belt pouches, thighs; belt=1.00 m, the top of the hips-weighted gear)  and  up = above (vest, chest).
Per frame and side S (R / L):
  arm_low_S / arm_up_S    least distance of forearm + hand vertices to the low / up gear;   elb_low_S / elb_up_S  the same for the elbow end of the upper arm (t > 0.8)
  pis_low_S / pis_up_S    the same for the pistol surface samples
  cut_S                   triangle pairs of forearm, hand and elbow end cutting any gear polygon (0 wanted);  pcut_S  pistol cutting the gear (> 0 = still inside the holster)
  pother_S                pistol cutting the other pistol or the other forearm / hand
  elbow_out_S             elbow outward of the shoulder joint (cm);  froll_S / wroll_S  forearm / wrist roll as in the animator's check (twist of the LowerArm / Hand against a pure hinge at the elbow, deg)
  wbend_S                 forearm against the barrel;  barrel_yaw_S / barrel_pitch_S / cant_S as in aim_measure.py;  self_hit_S  1 = a ray from the muzzle along the barrel hits her body within 1.5 m
  head_yaw / head_pitch   as in aim_measure.py;   hips_rot  rotation of the hips against the rest pose (deg)
Per action also the largest single-frame rotation step of any bone (top 5) and a minima / maxima summary with the frame.
"""
import bpy, sys, math, json
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_point_line

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = None
BELT = 1.00
ZONE_FROM = 'Yoru_Aim_Pose_V2_full'
LAST = None
acts = []
for a in argv:
    if a.startswith('out.json='):
        OUT = a.split('=', 1)[1]
    elif a.startswith('belt='):
        BELT = float(a.split('=', 1)[1])
    elif a.startswith('zone_from='):
        ZONE_FROM = a.split('=', 1)[1]
    elif a.startswith('last='):
        LAST = int(a.split('=', 1)[1])
    else:
        acts.append(a)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Body']
ad = arm.animation_data
ad.use_nla = False
scene = bpy.context.scene
P = arm.pose.bones
MW = arm.matrix_world


def pos(name):
    return MW @ P[name].head


def ang(a, b):
    a, b = a.normalized(), b.normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))


def set_action(name):
    ad.action = bpy.data.actions[name]
    if getattr(ad, 'action_slot', None) is None and len(ad.action.slots):
        ad.action_slot = ad.action.slots[0]


# ------------------------------------------------------------------ gear and arm polygons (copied from aim_measure.py)
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
dom = [vg_names.get(max(v.groups, key=lambda g: g.weight).group, '') if v.groups else '' for v in body.data.vertices]
SOLID = {'J_Bip_C_Hips', 'J_Bip_C_Spine', 'J_Bip_C_Chest', 'J_Bip_C_UpperChest', 'J_Bip_L_UpperLeg', 'J_Bip_R_UpperLeg', 'J_Bip_L_LowerLeg', 'J_Bip_R_LowerLeg'}
_inv = invisible_polygons()
VIS = [False] * len(body.data.vertices)
for _p in body.data.polygons:
    if _p.index not in _inv:
        for _v in _p.vertices:
            VIS[_v] = True
GEAR = [list(p.vertices) for p in body.data.polygons
        if p.index not in _inv and all(VIS[v_] and (dom[v_] in SOLID or (dom[v_].startswith('J_Sec_') and 'Hair' not in dom[v_])) for v_ in p.vertices)]
ARM_PARTS = {}
for _s in 'LR':
    hand_set = {'J_Bip_%s_Hand' % _s} | {'J_Bip_%s_%s%s' % (_s, f_, p_) for f_ in ('Index', 'Middle', 'Ring', 'Little', 'Thumb') for p_ in ('Proximal', 'Intermediate', 'Distal')}
    for part, bset in (('UpperArm', {'J_Bip_%s_UpperArm' % _s}), ('LowerArm', {'J_Bip_%s_LowerArm' % _s}), ('Hand', hand_set)):
        polys = [list(p.vertices) for p in body.data.polygons if p.index not in _inv and all(dom[v_] in bset and VIS[v_] for v_ in p.vertices)]
        ARM_PARTS[(_s, part)] = polys
NV = len(body.data.vertices)


def body_coords():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    arr = np.empty(NV * 3, dtype=np.float64)
    me.vertices.foreach_get('co', arr)
    ev.to_mesh_clear()
    arr = arr.reshape(NV, 3)
    mw = np.array(body.matrix_world.to_3x3())
    arr = arr @ mw.T + np.array(body.matrix_world.translation)
    return [Vector(c) for c in arr]


PISTOLS = {}
for o in bpy.data.objects:
    if o.name.startswith('PLATZHALTER_Pistole'):
        PISTOLS['L' if (o.name.endswith('_L') or '_L.' in o.name) else 'R'] = o


def pistol_geometry(ob):
    mwp = ob.matrix_world
    co = [mwp @ v.co for v in ob.data.vertices]
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


def nearest_min(bvh, pts):
    if bvh is None:
        return 99.9
    m = 99.9
    for q in pts:
        h = bvh.find_nearest(q, 0.5)
        if h[0] is not None and h[3] < m:
            m = h[3]
    return m


def verts_of(polys):
    return sorted({v for pl in polys for v in pl})


REST_Q = {b.name: b.matrix_local.to_quaternion() for b in arm.data.bones}
HEAD0 = {b.name: b.head_local.copy() for b in arm.data.bones}
REST_FA = {s: (HEAD0['J_Bip_%s_Hand' % s] - HEAD0['J_Bip_%s_LowerArm' % s]).normalized() for s in 'LR'}
REST_N = Vector((0.0, 0.0, -1.0))


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed().to_quaternion()


def signed_about(q, axis):
    ax, an = q.to_axis_angle()
    a = math.degrees(an) * (1.0 if ax.dot(axis) >= 0 else -1.0)
    return (a + 180.0) % 360.0 - 180.0


def rolls(s, ua_j, la_j, hd_j):
    """forearm roll (tw_e) and wrist roll (tw_w) as in the animator's check (build_aim_s1_check.py): twist of the LowerArm / Hand rotation against a pure hinge at the elbow"""
    sx = 1.0 if s == 'R' else -1.0
    ua, fo = (la_j - ua_j).normalized(), (hd_j - la_j).normalized()
    cr = ua.cross(fo)
    if cr.length < 1e-6:
        return 0.0, 0.0
    n_ = cr.normalized() * (-sx)
    lo, ha = 'J_Bip_%s_LowerArm' % s, 'J_Bip_%s_Hand' % s
    Df = (MW.to_quaternion() @ P[lo].matrix.to_quaternion()) @ REST_Q[lo].inverted()
    Dh = (MW.to_quaternion() @ P[ha].matrix.to_quaternion()) @ REST_Q[ha].inverted()
    Df0 = frame_rot(fo, n_) @ frame_rot(REST_FA[s], REST_N).inverted()
    tw_e = signed_about(Df @ Df0.inverted(), fo)
    hdir = (Dh @ REST_FA[s]).normalized()
    tw = signed_about(Dh @ (fo.rotation_difference(hdir) @ Df0).inverted(), hdir)
    return tw_e, tw - tw_e


# ------------------------------------------------------------------ zones, fixed once
set_action(ZONE_FROM if ZONE_FROM in bpy.data.actions else acts[0])
scene.frame_set(int(round(ad.action.frame_range[0])))
bpy.context.view_layer.update()
_co0 = body_coords()
LOW = [pl for pl in GEAR if sum(_co0[v].z for v in pl) / len(pl) < BELT]
UP = [pl for pl in GEAR if sum(_co0[v].z for v in pl) / len(pl) >= BELT]
print('gear polygons %d: low %d, up %d (belt line z = %.3f m, zones from %s)' % (len(GEAR), len(LOW), len(UP), BELT, ad.action.name))


def scan_frame():
    co = body_coords()
    g_all = BVHTree.FromPolygons(co, GEAR, all_triangles=False)
    g_low = BVHTree.FromPolygons(co, LOW, all_triangles=False) if LOW else None
    g_up = BVHTree.FromPolygons(co, UP, all_triangles=False) if UP else None
    r = {}
    hips, head = pos('J_Bip_C_Hips'), pos('J_Bip_C_Head')
    hb = P['J_Bip_C_Hips']
    r['hips_rot'] = round(math.degrees((hb.matrix.to_quaternion() @ hb.bone.matrix_local.to_quaternion().inverted()).angle), 3)
    hp = P['J_Bip_C_Head']
    dq = hp.matrix.to_quaternion() @ hp.bone.matrix_local.to_quaternion().inverted()
    fw = (MW.to_3x3() @ (dq @ Vector((0.0, 1.0, 0.0)))).normalized()
    r['head_yaw'] = round(math.degrees(math.atan2(fw.x, fw.y)), 2)
    r['head_pitch'] = round(math.degrees(math.asin(max(-1.0, min(1.0, fw.z)))), 2)
    pg = {s: pistol_geometry(o) for s, o in PISTOLS.items()}
    pbv = {s: BVHTree.FromPolygons(g[0], g[1], all_triangles=False) for s, g in pg.items()}
    abv = {}
    for s in 'RL':
        sx = 1.0 if s == 'R' else -1.0
        ua, la, hd = pos('J_Bip_%s_UpperArm' % s), pos('J_Bip_%s_LowerArm' % s), pos('J_Bip_%s_Hand' % s)
        elb_polys = [pl for pl in ARM_PARTS[(s, 'UpperArm')] if intersect_point_line(co[pl[0]], ua, la)[1] > 0.8]
        fa_polys = ARM_PARTS[(s, 'LowerArm')] + ARM_PARTS[(s, 'Hand')]
        fa_pts = [co[v] for v in verts_of(fa_polys)]
        el_pts = [co[v] for v in verts_of(elb_polys)]
        allp = fa_polys + elb_polys
        tb = BVHTree.FromPolygons(co, allp, all_triangles=False) if allp else None
        abv[s] = BVHTree.FromPolygons(co, fa_polys, all_triangles=False) if fa_polys else None
        r['cut_' + s] = len(tb.overlap(g_all)) if tb else 0
        r['arm_low_' + s] = round(nearest_min(g_low, fa_pts) * 1000, 1)
        r['arm_up_' + s] = round(nearest_min(g_up, fa_pts) * 1000, 1)
        r['elb_low_' + s] = round(nearest_min(g_low, el_pts) * 1000, 1)
        r['elb_up_' + s] = round(nearest_min(g_up, el_pts) * 1000, 1)
        r['elbow_out_' + s] = round((la.x - ua.x) * sx * 100, 1)
        fr_, wr_ = rolls(s, ua, la, hd)
        r['froll_' + s] = round(fr_, 2)
        r['wroll_' + s] = round(wr_, 2)
        if s in pg:
            po = PISTOLS[s]
            mwp = po.matrix_world
            barrel = (mwp.to_3x3() @ Vector((0, 1, 0))).normalized()
            top = (mwp.to_3x3() @ Vector((0, 0, 1))).normalized()
            ymax = max(v.co.y for v in po.data.vertices)
            front = [mwp @ v.co for v in po.data.vertices if v.co.y > ymax - 1e-4]
            muzzle = sum(front, Vector()) / len(front)
            r['barrel_yaw_' + s] = round(math.degrees(math.atan2(barrel.x * sx, barrel.y)), 1)
            r['barrel_pitch_' + s] = round(math.degrees(math.asin(max(-1.0, min(1.0, barrel.z)))), 1)
            r['wbend_' + s] = round(ang(hd - la, barrel), 1)
            up_ref = Vector((0, 0, 1)) - barrel * barrel.z
            if up_ref.length > 1e-6:
                up_ref.normalize()
                r['cant_' + s] = round(math.degrees(math.atan2(barrel.dot(up_ref.cross(top)), up_ref.dot(top))) * sx, 1)
            r['pcut_' + s] = len(pbv[s].overlap(g_all))
            r['pis_low_' + s] = round(nearest_min(g_low, pg[s][2]) * 1000, 1)
            r['pis_up_' + s] = round(nearest_min(g_up, pg[s][2]) * 1000, 1)
            hit = g_all.ray_cast(muzzle, barrel, 1.5)
            r['self_hit_' + s] = 1 if hit[0] is not None else 0
    for s, o in (('L', 'R'), ('R', 'L')):
        if s in pg and o in pg:
            n = len(pbv[s].overlap(pbv[o]))
            if abv.get(o) is not None:
                n += len(pbv[s].overlap(abv[o]))
            r['pother_' + s] = n
    return r


res = {}
for name in acts:
    set_action(name)
    f0 = int(round(ad.action.frame_range[0]))
    f1 = LAST if LAST is not None else int(round(ad.action.frame_range[1]))
    rows, quats = [], []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        r = scan_frame()
        r['frame'] = f
        rows.append(r)
        quats.append({pb.name: pb.matrix_basis.to_quaternion() for pb in P})
    steps = []
    for i in range(1, len(quats)):
        for n in quats[i]:
            d = quats[i - 1][n].rotation_difference(quats[i][n])
            if d.w < 0:
                d.negate()
            steps.append((math.degrees(d.angle), n, rows[i]['frame']))
    steps.sort(reverse=True)
    res[name] = {'rows': rows, 'step_top5': [[round(a, 2), n, f] for a, n, f in steps[:5]]}

if OUT:
    json.dump(res, open(OUT, 'w'), indent=1)

COLS = [('arm_low', 'aL'), ('arm_up', 'aU'), ('elb_low', 'eL'), ('elb_up', 'eU'), ('pis_low', 'pL'), ('pis_up', 'pU')]
for name, o in res.items():
    rows = o['rows']
    print('==', name, '(%d frames, %d..%d)' % (len(rows), rows[0]['frame'], rows[-1]['frame']))
    print('  mm to gear below / above the belt:  aL aU = forearm+hand, eL eU = elbow end, pL pU = pistol;  cut / pcut = triangle pairs (arm / pistol);  eo = elbow out cm;  fr / wr = forearm / wrist twist deg')
    print('  fr |      R: aL    aU    eL    eU    pL    pU cut pc |      L: aL    aU    eL    eU    pL    pU cut pc | eoR  eoL | frR   frL   wrR   wrL | hyaw hpit')
    for r in rows:
        def side(s):
            return '%6.1f%6.1f%6.1f%6.1f%6.1f%6.1f %3d %2d' % tuple([r[k + '_' + s] for k, _ in COLS] + [r['cut_' + s], r.get('pcut_' + s, -1)])
        print('  %2d | %s | %s | %4.1f %4.1f | %5.1f %5.1f %5.1f %5.1f | %4.1f %4.1f' % (r['frame'], side('R'), side('L'), r['elbow_out_R'], r['elbow_out_L'],
              r['froll_R'], r['froll_L'], r['wroll_R'], r['wroll_L'], r['head_yaw'], r['head_pitch']))
    print('  summary (all frames):')
    for s in 'RL':
        for k, _ in COLS:
            m = min(rows, key=lambda r: r[k + '_' + s])
            print('    min %s_%s %.1f mm at frame %d' % (k, s, m[k + '_' + s], m['frame']))
        print('    cut_%s total %d, pcut_%s frames with the pistol inside the gear: %s' % (s, sum(r['cut_' + s] for r in rows), s, [r['frame'] for r in rows if r.get('pcut_' + s, 0) > 0]))
        print('    max elbow_out_%s %.1f cm, max |froll| %.1f, max |wroll| %.1f, max wbend %.1f, max |cant| %.1f, self_hit frames %s' % (
            s, max(r['elbow_out_' + s] for r in rows), max(abs(r['froll_' + s]) for r in rows), max(abs(r['wroll_' + s]) for r in rows),
            max(r.get('wbend_' + s, 0) for r in rows), max(abs(r.get('cant_' + s, 0)) for r in rows), [r['frame'] for r in rows if r.get('self_hit_' + s)]))
    print('    head_yaw range %.2f .. %.2f, hips_rot max %.3f, pother total %d / %d' % (min(r['head_yaw'] for r in rows), max(r['head_yaw'] for r in rows),
          max(r['hips_rot'] for r in rows), sum(r.get('pother_R', 0) for r in rows), sum(r.get('pother_L', 0) for r in rows)))
    print('    largest single-frame steps (deg, bone, frame):', o['step_top5'])
