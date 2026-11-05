"""
Yoru - AIM POSE objective measurements (saves nothing but the optional JSON).  Written by the main agent for the A3 review (2026-10-29).
  blender -b <blend> --python aim_measure.py -- [out.json=<path>] <action> [<action> ...]
  e.g. blender -b Blender/work/Aim/Yoru_Aim_r1.blend --python Blender/scripts/aim_measure.py -- out.json=m.json Yoru_Aim_r1_A Yoru_Aim_r1_B Yoru_Aim_r1_C
For every action: set on the armature, first frame of its range, then (World: +Y forward = the aim line, her right = +X, up = +Z; m and deg):
  hips_rot_deg     rotation of the hips against the rest pose (the upper-body layer needs 0);  pelvis_drop_cm  hips joint below its rest height
  stance           knee_L/R (flexion, deg), feet_spacing_x / feet_stagger_y (ankle joints, m), hips_vs_feet_y_cm / shoulders_vs_feet_y_cm / head_vs_feet_y_cm (ahead + / behind - of the middle
                   between the ankles; a squat shows as hips far behind), hips_height_m
  lean             hips joint -> neck joint against the vertical, side view (+ = forward);  shoulder_yaw  line between the upper-arm joints seen from above,
                   relative to the line between the upper-leg joints (+ = right shoulder forward);  shoulder_roll the same seen from behind (+ = right shoulder up)
  head_yaw/pitch   where the face points (the head's rest forward turned by the pose) against +Y: yaw + = to her right, pitch + = up
  per side S (R / L):
    hand_rel_S       wrist joint minus shoulder joint: (outward x, forward y, up z)
    elbow_S          interior angle upper arm - forearm;  uarm_elev_S  upper arm against straight down (0 hanging, 90 horizontal);
    uarm_az_S / farm_az_S  upper arm / forearm seen from above, 0 = forward, + = outward;  elbow_out_S  elbow outward of the shoulder joint (cm)
    barrel_yaw_S / barrel_pitch_S  pistol barrel against +Y (yaw + = outward, pitch + = up);  wrist_bend_S  forearm vs barrel;  cant_S  roll of the pistol about its barrel (+ = top tilts outward)
    muzzle_S         muzzle point (x, y, z) in the world;  muzzle_vs_head_cm_S  muzzle height minus head joint height
    cut_S            triangle pairs of forearm, hand and the elbow end of the upper arm (t > 0.8) that cut through the vest / torso / thigh polygons (0 = clean)
    clr_arm_S        least vertex distance (mm) of forearm and hand to those polygons (>= 3 wanted);  clr_uarm_S  the same for the whole upper arm (it may rest on the vest)
    pcut_S / clr_pistol_S  pistol triangles cutting the gear / least distance of the pistol to it (mm);  pother_S  pistol cutting the other pistol or arm
  muzzle_gap (m); converge_m  distance ahead of the muzzles where the two barrel lines come closest (None = parallel or diverging);  muzzle_sep_at_converge (m)
  cam_game / cam_ads / cam_side: head_cover = share of the head disc hidden by a pistol that is nearer to the camera than the head; muzzle_S = muzzle screen position
    (half-heights of the picture from the centre; the crosshair is the centre);  game = the game camera (pivot 1.35 m, 4.4 m behind, 0.35 m right, 15 deg down, vertical
    fov 60), ads = aim camera (1.30 m, 2.4 m, 0.58 m, 15 deg, fov 42), side = orthographic from 6 m to her right.
The clearance test is an independent copy of clearance_exact() of build_sprint_r1.py (arm part polygons against the gear polygons, alpha-cut coat hem ignored).
"""
import bpy, sys, math, json
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = None
FRAME = None                                                       # frame=<n> measures that frame instead of the first frame of the action
acts = []
for a in argv:
    if a.startswith('out.json='):
        OUT = a.split('=', 1)[1]
    elif a.startswith('frame='):
        FRAME = int(a.split('=', 1)[1])
    else:
        acts.append(a)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Body']
ad = arm.animation_data
scene = bpy.context.scene
P = arm.pose.bones
MW = arm.matrix_world


def pos(name):
    return MW @ P[name].head


def ang(a, b):
    a, b = a.normalized(), b.normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))


# ------------------------------------------------------------------ gear polygons (vest, torso, thighs, bust ... but no hair), alpha-cut polygons dropped
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
        ARM_PARTS[(_s, part)] = (polys, sorted({v_ for pl in polys for v_ in pl}))
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


def pistol_geometry(ob):
    mwp = ob.matrix_world
    co = [mwp @ v.co for v in ob.data.vertices]
    polys = [list(p.vertices) for p in ob.data.polygons]
    samples = list(co)
    for p in ob.data.polygons:                                       # a 4 x 4 grid on every face (the boxes are coarse)
        vs = [co[i] for i in p.vertices]
        if len(vs) != 4:
            continue
        for a_ in (0.125, 0.375, 0.625, 0.875):
            for b_ in (0.125, 0.375, 0.625, 0.875):
                samples.append(vs[0].lerp(vs[1], a_).lerp(vs[3].lerp(vs[2], a_), b_))
    return co, polys, samples


def clearance_all(pistols):
    from mathutils.geometry import intersect_point_line
    co = body_coords()
    gear = BVHTree.FromPolygons(co, GEAR, all_triangles=False)
    out = {}
    pg = {s: pistol_geometry(o) for s, o in pistols.items()}
    pb_ = {s: BVHTree.FromPolygons(g[0], g[1], all_triangles=False) for s, g in pg.items()}
    abvh = {}
    for s in 'LR':
        sh = MW @ P['J_Bip_%s_UpperArm' % s].head
        el = MW @ P['J_Bip_%s_LowerArm' % s].head
        r = dict(cut=0, arm_min=9.0, uarm_min=9.0, pcut=None, pistol_min=None, pother=None)
        for part in ('UpperArm', 'LowerArm', 'Hand'):
            polys, vids = ARM_PARTS[(s, part)]
            if part == 'UpperArm':
                polys = [pl for pl in polys if intersect_point_line(co[pl[0]], sh, el)[1] > 0.8]
            if polys:
                tb = BVHTree.FromPolygons(co, polys, all_triangles=False)
                abvh[(s, part)] = tb
                r['cut'] += len(tb.overlap(gear))
            for v_ in vids:
                hit = gear.find_nearest(co[v_])
                if hit[0] is None:
                    continue
                if part == 'UpperArm':
                    r['uarm_min'] = min(r['uarm_min'], hit[3])
                else:
                    r['arm_min'] = min(r['arm_min'], hit[3])
        if s in pg:
            r['pcut'] = len(pb_[s].overlap(gear))
            r['pistol_min'] = min(gear.find_nearest(q)[3] for q in pg[s][2])
        out[s] = r
    for s, o in (('L', 'R'), ('R', 'L')):
        if s in pg and o in pg:
            n = len(pb_[s].overlap(pb_[o]))
            for part in ('LowerArm', 'Hand'):
                if (o, part) in abvh:
                    n += len(pb_[s].overlap(abvh[(o, part)]))
            out[s]['pother'] = n
    return out


# ------------------------------------------------------------------ cameras (perspective; screen units = half heights of the picture)
def look_cam(eye, fwd, fov_y_deg=None, ortho_h=None):
    f = fwd.normalized()
    r = f.cross(Vector((0, 0, 1))).normalized()
    u = r.cross(f)
    return dict(eye=eye, f=f, r=r, u=u, t=math.tan(math.radians(fov_y_deg) / 2.0) if fov_y_deg else None, oh=ortho_h)


def project(cam, p):
    d = p - cam['eye']
    depth = d.dot(cam['f'])
    if cam['oh']:
        return d.dot(cam['r']) / (cam['oh'] / 2.0), d.dot(cam['u']) / (cam['oh'] / 2.0), depth
    return d.dot(cam['r']) / (depth * cam['t']), d.dot(cam['u']) / (depth * cam['t']), depth


def game_cams(feet):
    pit = math.radians(15.0)
    fwd = Vector((0.0, math.cos(pit), -math.sin(pit)))
    piv_g = feet + Vector((0.0, 0.0, 1.35))
    piv_a = feet + Vector((0.0, 0.0, 1.30))

    def back(d):
        return Vector((0.0, -math.cos(pit), math.sin(pit))) * d
    return {'game': look_cam(piv_g + back(4.4) + Vector((0.35, 0, 0)), fwd, fov_y_deg=60.0),
            'ads': look_cam(piv_a + back(2.4) + Vector((0.58, 0, 0)), fwd, fov_y_deg=42.0),
            'side': look_cam(feet + Vector((6.0, 0.12, 0.88)), Vector((-1.0, 0.0, 0.0)), ortho_h=1.95)}


def hull_contains(poly_pts, q):
    """q (N x 2) inside the convex hull of poly_pts (monotone chain)"""
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in poly_pts))
    if len(pts) < 3:
        return np.zeros(len(q), dtype=bool)

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
    hull = lo[:-1] + up[:-1]
    ok = np.ones(len(q), dtype=bool)
    for i in range(len(hull)):
        a, b = hull[i], hull[(i + 1) % len(hull)]
        ok &= ((b[0] - a[0]) * (q[:, 1] - a[1]) - (b[1] - a[1]) * (q[:, 0] - a[0])) >= 0
    return ok


PISTOLS = {}
for o in bpy.data.objects:
    if o.name.startswith('PLATZHALTER_Pistole'):
        PISTOLS['L' if (o.name.endswith('_L') or '_L.' in o.name) else 'R'] = o

res = {}
for name in acts:
    ad.action = bpy.data.actions[name]
    if getattr(ad, 'action_slot', None) is None and len(ad.action.slots):
        ad.action_slot = ad.action.slots[0]
    scene.frame_set(FRAME if FRAME is not None else int(round(ad.action.frame_range[0])))
    bpy.context.view_layer.update()
    r = {}
    hips, neck, head = pos('J_Bip_C_Hips'), pos('J_Bip_C_Neck'), pos('J_Bip_C_Head')
    sl, sr = pos('J_Bip_L_UpperArm'), pos('J_Bip_R_UpperArm')
    ll, lr = pos('J_Bip_L_UpperLeg'), pos('J_Bip_R_UpperLeg')
    fl, fr_ = pos('J_Bip_L_Foot'), pos('J_Bip_R_Foot')
    feet = Vector((0.5 * (fl.x + fr_.x), 0.5 * (fl.y + fr_.y), 0.0))
    hb = P['J_Bip_C_Hips']
    r['hips_rot_deg'] = round(math.degrees((hb.matrix.to_quaternion() @ hb.bone.matrix_local.to_quaternion().inverted()).angle), 2)
    r['pelvis_drop_cm'] = round((MW @ hb.bone.head_local).z * 100 - hips.z * 100, 1)
    r['lean'] = round(math.degrees(math.atan2((neck - hips).y, (neck - hips).z)), 1)
    r['shoulder_yaw'] = round(math.degrees(math.atan2((sr - sl).y, (sr - sl).x)) - math.degrees(math.atan2((lr - ll).y, (lr - ll).x)), 1)
    r['shoulder_roll'] = round(math.degrees(math.atan2((sr - sl).z, (sr - sl).x)), 1)
    for s in 'LR':                                                     # the stance (legs and feet): knee flexion, where the body sits over the feet
        ul_, kn_, an_ = pos('J_Bip_%s_UpperLeg' % s), pos('J_Bip_%s_LowerLeg' % s), pos('J_Bip_%s_Foot' % s)
        r['knee_' + s] = round(180.0 - ang(ul_ - kn_, an_ - kn_), 1)
    mid_ = (fl + fr_) * 0.5
    r['feet_spacing_x'] = round(abs(fl.x - fr_.x), 3)                # ankle joints, sideways
    r['feet_stagger_y'] = round(abs(fl.y - fr_.y), 3)                # ankle joints, front to back
    r['hips_vs_feet_y_cm'] = round((hips.y - mid_.y) * 100, 1)       # pelvis joint ahead (+) or behind (-) of the middle between the ankles
    r['shoulders_vs_feet_y_cm'] = round((((sl + sr) * 0.5) - mid_).y * 100, 1)
    r['head_vs_feet_y_cm'] = round((head - mid_).y * 100, 1)
    r['hips_height_m'] = round(hips.z, 3)
    hp = P['J_Bip_C_Head']
    dq = hp.matrix.to_quaternion() @ hp.bone.matrix_local.to_quaternion().inverted()
    fw = (MW.to_3x3() @ (dq @ Vector((0.0, 1.0, 0.0)))).normalized()
    r['head_yaw'] = round(math.degrees(math.atan2(fw.x, fw.y)), 1)
    r['head_pitch'] = round(math.degrees(math.asin(max(-1.0, min(1.0, fw.z)))), 1)
    clr = clearance_all(PISTOLS)
    pist = {}
    for s in 'RL':
        sx = 1.0 if s == 'R' else -1.0
        ua, la, hd = pos('J_Bip_%s_UpperArm' % s), pos('J_Bip_%s_LowerArm' % s), pos('J_Bip_%s_Hand' % s)
        rel = hd - ua
        r['hand_rel_' + s] = [round(rel.x * sx, 3), round(rel.y, 3), round(rel.z, 3)]
        r['elbow_' + s] = round(ang(ua - la, hd - la), 1)
        r['uarm_elev_' + s] = round(ang(la - ua, Vector((0, 0, -1))), 1)
        r['uarm_az_' + s] = round(math.degrees(math.atan2((la - ua).x * sx, (la - ua).y)), 1)
        r['farm_az_' + s] = round(math.degrees(math.atan2((hd - la).x * sx, (hd - la).y)), 1)
        r['elbow_out_' + s] = round((la.x - ua.x) * sx * 100, 1)
        c = clr[s]
        r['cut_' + s] = c['cut']
        r['clr_arm_' + s] = round(c['arm_min'] * 1000, 1)
        r['clr_uarm_' + s] = round(c['uarm_min'] * 1000, 1)
        po = PISTOLS.get(s)
        if po is not None:
            mwp = po.matrix_world
            barrel = (mwp.to_3x3() @ Vector((0, 1, 0))).normalized()
            top = (mwp.to_3x3() @ Vector((0, 0, 1))).normalized()
            vs = [mwp @ v.co for v in po.data.vertices]
            ymax = max(v.co.y for v in po.data.vertices)
            front = [mwp @ v.co for v in po.data.vertices if v.co.y > ymax - 1e-4]
            muzzle = sum(front, Vector()) / len(front)
            r['barrel_yaw_' + s] = round(math.degrees(math.atan2(barrel.x * sx, barrel.y)), 1)
            r['barrel_pitch_' + s] = round(math.degrees(math.asin(max(-1.0, min(1.0, barrel.z)))), 1)
            r['wrist_bend_' + s] = round(ang(hd - la, barrel), 1)
            up_ref = Vector((0, 0, 1)) - barrel * barrel.z
            if up_ref.length > 1e-6:
                up_ref.normalize()
                r['cant_' + s] = round(math.degrees(math.atan2(barrel.dot(up_ref.cross(top)), up_ref.dot(top))) * sx, 1)
            r['muzzle_' + s] = [round(v, 3) for v in muzzle]
            r['muzzle_vs_head_cm_' + s] = round((muzzle.z - head.z) * 100, 1)
            r['pcut_' + s] = c['pcut']
            r['clr_pistol_' + s] = round(c['pistol_min'] * 1000, 1)
            r['pother_' + s] = c['pother']
            pist[s] = dict(barrel=barrel, muzzle=muzzle, verts=vs)
    if len(pist) == 2:
        a, b = pist['R'], pist['L']
        r['muzzle_gap'] = round((a['muzzle'] - b['muzzle']).length, 3)
        d1, d2, w = a['barrel'], b['barrel'], a['muzzle'] - b['muzzle']
        den = 1.0 - d1.dot(d2) ** 2
        r['converge_m'] = None
        if den > 1e-5:
            t1 = (d1.dot(d2) * d2.dot(w) - d1.dot(w)) / den
            t2 = (d2.dot(w) - d1.dot(d2) * d1.dot(w)) / den
            if t1 > 0 and t2 > 0:
                r['converge_m'] = round(0.5 * (t1 + t2), 2)
                r['muzzle_sep_at_converge'] = round(((a['muzzle'] + d1 * t1) - (b['muzzle'] + d2 * t2)).length, 3)
    cams = game_cams(feet)
    hc = head + Vector((0, 0, 0.075))
    for cn, cam in cams.items():
        cx, cy, cd = project(cam, hc)
        rad = (0.085 / (cd * cam['t'])) if not cam['oh'] else 0.085 / (cam['oh'] / 2.0)
        g = np.random.RandomState(1).uniform(-1, 1, (3000, 2)) * rad
        g = g[(g ** 2).sum(1) <= rad * rad] + np.array([cx, cy])
        cover = np.zeros(len(g), dtype=bool)
        info = {}
        for s, pd in pist.items():
            pts = [project(cam, v) for v in pd['verts']]
            near = [(x, y) for x, y, dp in pts if dp < cd - 0.02]
            if len(near) >= 3:
                cover |= hull_contains(near, g)
            mx, my, _ = project(cam, pd['muzzle'])
            info['muzzle_' + s] = [round(mx, 2), round(my, 2)]
        info['head_cover'] = round(float(cover.mean()), 3)
        r['cam_' + cn] = info
    res[name] = r

if OUT:
    json.dump(res, open(OUT, 'w'), indent=1)
for name, o in res.items():
    print('==', name)
    for k, v in o.items():
        print('  %-24s %s' % (k, v))
