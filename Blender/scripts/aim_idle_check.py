"""
Yoru - AIM IDLE loop check (main agent, saves nothing but the optional JSON).  Written 2026-10-31 for the stage-1 review of Yoru_Aim_Idle.
  blender -b <blend> --python aim_idle_check.py -- <action> [out.json=<path>] [last=360]
Over EVERY frame of the action (no mesh evaluation, so it is quick):
  muzzle_*         muzzle point of PLATZHALTER_Pistole_L/R in the world: vertical range (mm), 3D range (mm) over the loop
  chest_z_p2p_mm   vertical range of the UpperChest joint;  shoulder_z_p2p_mm  of the two upper-arm joints  (the breathing the hands must not follow)
  elbow_L/R        elbow flexion (0 = straight): min, max over the loop
  barrel_dev_deg   largest angle between a barrel and its direction in frame 0
  seam             last frame against frame 0: largest bone rotation delta (deg) and location delta (mm)
  foot_p2p_mm      range of the foot and toe joints (x, y) over the loop (stance drift, the Idle v2 has about 1.4 mm)
  step_max_deg     largest single-frame rotation step of any bone (deg per frame);  head_step_max_deg the same for the head
  gaze_yaw/pitch_range_deg  head gaze as in aim_measure.py (+ yaw = to her right, + pitch = up);  head_world_dev_max_deg  largest rotation of the head in the world against the first frame (0 = locked)
"""
import bpy, sys, math, json
from mathutils import Vector, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = None
LAST = None
acts = []
for a in argv:
    if a.startswith('out.json='):
        OUT = a.split('=', 1)[1]
    elif a.startswith('last='):
        LAST = int(a.split('=', 1)[1])
    else:
        acts.append(a)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ad = arm.animation_data
scene = bpy.context.scene
P = arm.pose.bones
MW = arm.matrix_world
PIST = {}
for o in bpy.data.objects:
    if o.name.startswith('PLATZHALTER_Pistole'):
        PIST['L' if (o.name.endswith('_L') or '_L.' in o.name) else 'R'] = o


def pos(n):
    return MW @ P[n].head


def ang(a, b):
    a, b = a.normalized(), b.normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))


res = {}
for name in acts:
    ad.action = bpy.data.actions[name]
    if getattr(ad, 'action_slot', None) is None and len(ad.action.slots):
        ad.action_slot = ad.action.slots[0]
    f0 = int(round(ad.action.frame_range[0]))
    f1 = LAST if LAST is not None else int(round(ad.action.frame_range[1]))
    rows = []
    quats = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        r = {}
        for s, po in PIST.items():
            ymax = max(v.co.y for v in po.data.vertices)
            front = [po.matrix_world @ v.co for v in po.data.vertices if v.co.y > ymax - 1e-4]
            r['muzzle_' + s] = sum(front, Vector()) / len(front)
            r['barrel_' + s] = (po.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
        r['chest_z'] = pos('J_Bip_C_UpperChest').z
        r['sh_z'] = [pos('J_Bip_L_UpperArm').z, pos('J_Bip_R_UpperArm').z]
        hp = P['J_Bip_C_Head']
        hq = hp.matrix.to_quaternion()
        fw = (MW.to_3x3() @ ((hq @ hp.bone.matrix_local.to_quaternion().inverted()) @ Vector((0, 1, 0)))).normalized()
        r['head_q'] = hq.copy()
        r['gaze'] = (math.degrees(math.atan2(fw.x, fw.y)), math.degrees(math.asin(max(-1.0, min(1.0, fw.z)))))
        for s in 'LR':
            ua, la, hd = pos('J_Bip_%s_UpperArm' % s), pos('J_Bip_%s_LowerArm' % s), pos('J_Bip_%s_Hand' % s)
            r['elbow_' + s] = 180.0 - ang(ua - la, hd - la)
            r['foot_' + s] = pos('J_Bip_%s_Foot' % s)
            r['toe_' + s] = pos('J_Bip_%s_ToeBase' % s)
        rows.append(r)
        quats.append({pb.name: (pb.matrix_basis.to_quaternion(), pb.matrix_basis.translation.copy()) for pb in P})
    o = {'frames': len(rows)}
    for s in PIST:
        zs = [r['muzzle_' + s].z for r in rows]
        o['muzzle_%s_vertical_mm' % s] = round((max(zs) - min(zs)) * 1000, 2)
        ms = [r['muzzle_' + s] for r in rows]
        c = sum(ms, Vector()) / len(ms)
        o['muzzle_%s_3d_mm' % s] = round(max((m - c).length for m in ms) * 2000, 2)
        o['barrel_dev_%s_deg' % s] = round(max(ang(rows[0]['barrel_' + s], r['barrel_' + s]) for r in rows), 3)
    o['chest_z_p2p_mm'] = round((max(r['chest_z'] for r in rows) - min(r['chest_z'] for r in rows)) * 1000, 2)

    def _dev(a, b):
        x = math.degrees(a.rotation_difference(b).angle)
        return min(x, 360.0 - x)
    o['gaze_yaw_range_deg'] = [round(min(r['gaze'][0] for r in rows), 3), round(max(r['gaze'][0] for r in rows), 3)]
    o['gaze_pitch_range_deg'] = [round(min(r['gaze'][1] for r in rows), 3), round(max(r['gaze'][1] for r in rows), 3)]
    o['head_world_dev_max_deg'] = round(max(_dev(rows[0]['head_q'], r['head_q']) for r in rows), 3)
    o['shoulder_z_p2p_mm'] = [round((max(r['sh_z'][i] for r in rows) - min(r['sh_z'][i] for r in rows)) * 1000, 2) for i in (0, 1)]
    for s in 'LR':
        es = [r['elbow_' + s] for r in rows]
        o['elbow_%s' % s] = [round(min(es), 2), round(max(es), 2)]
        for k in ('foot', 'toe'):
            xs = [r['%s_%s' % (k, s)] for r in rows]
            o['%s_%s_p2p_mm' % (k, s)] = [round((max(v.x for v in xs) - min(v.x for v in xs)) * 1000, 2), round((max(v.y for v in xs) - min(v.y for v in xs)) * 1000, 2)]
    # seam and the largest single-frame step
    a0, a1 = quats[0], quats[-1]
    o['seam_deg'] = round(max(math.degrees((a0[n][0].rotation_difference(a1[n][0])).angle) for n in a0), 4)
    o['seam_mm'] = round(max((a0[n][1] - a1[n][1]).length for n in a0) * 1000, 4)
    step, step_bone = 0.0, ''
    for i in range(1, len(quats)):
        for n in quats[i]:
            d = math.degrees((quats[i - 1][n][0].rotation_difference(quats[i][n][0])).angle)
            if d > step:
                step, step_bone = d, n
    o['step_max_deg'] = [round(step, 3), step_bone]
    hs = 0.0
    for i in range(1, len(quats)):
        hs = max(hs, _dev(quats[i - 1]['J_Bip_C_Head'][0], quats[i]['J_Bip_C_Head'][0]))
    o['head_step_max_deg'] = round(hs, 3)
    res[name] = o
if OUT:
    json.dump(res, open(OUT, 'w'), indent=1)
for name, o in res.items():
    print('==', name)
    for k, v in o.items():
        print('  %-24s %s' % (k, v))
