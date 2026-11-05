"""
Yoru - SPRINT / RUN objective measurements (saves nothing but the optional JSON).  Written by the main agent for the round-2 critique (2026-10-28).
  blender -b --factory-startup <blend> --python sprint_measure.py -- [out.json=<path>] <action> [<action> ...]
  e.g. blender -b --factory-startup Blender/work/Sprint/Yoru_Sprint_r2.blend --python Blender/scripts/sprint_measure.py -- Yoru_Sprint_r2_M
The last key of an action repeats the first one and is skipped.  World axes: +Y forward, -X = her left, +Z up.  All values over one cycle as
(min, max, mean); *_p2p = peak to peak.
  lean              hips joint -> neck joint against the vertical in the side view (deg, + = leaning forward)
  hips_z_p2p_cm     vertical bounce of the pelvis;  hips_x_p2p_cm sideways sway;  head_x_p2p_cm / head_z_p2p_cm the same for the head
  shoulder_yaw / pelvis_yaw   turn of the line between the two upper-arm / upper-leg joints seen from above (deg); *_roll the same seen from behind
  elbow_L/R         interior angle between upper arm and forearm (deg);  uarm_swing_L/R  upper arm against the vertical in the side view (+ = elbow in front)
  hand_z_rel / hand_y_rel   hand against the shoulder joint (m, up / forward);  elbow_x_rel  sideways distance elbow - shoulder (m)
  knee_L/R          knee flexion (deg, 0 = straight)
"""
import bpy, sys, math, json

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = None
acts = []
for a in argv:
    if a.startswith('out.json='):
        OUT = a.split('=', 1)[1]
    else:
        acts.append(a)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ad = arm.animation_data
scene = bpy.context.scene


def pos(pb):
    return arm.matrix_world @ pb.head


def ang(a, b):
    a = a.normalized()
    b = b.normalized()
    return math.degrees(math.acos(max(-1, min(1, a.dot(b)))))


res = {}
for name in acts:
    ad.action = bpy.data.actions[name]
    if getattr(ad, 'action_slot', None) is None and len(ad.action.slots):
        ad.action_slot = ad.action.slots[0]
    fr = ad.action.frame_range
    f0, f1 = int(round(fr[0])), int(round(fr[1]))
    P = arm.pose.bones
    rows = []
    for f in range(f0, f1):
        scene.frame_set(f)
        bpy.context.view_layer.update()

        def g(k):
            return pos(P[k])
        hips, neck, head = g('J_Bip_C_Hips'), g('J_Bip_C_Neck'), g('J_Bip_C_Head')
        sl, sr = g('J_Bip_L_UpperArm'), g('J_Bip_R_UpperArm')
        ll, lr = g('J_Bip_L_UpperLeg'), g('J_Bip_R_UpperLeg')
        r = {'lean': math.degrees(math.atan2((neck - hips).y, (neck - hips).z)),
             'neck_tilt': math.degrees(math.atan2((head - neck).y, (head - neck).z)),       # neck joint -> head joint against the vertical (+ = head tipped forward)
             'head_fwd_cm': (head.y - hips.y) * 100.0,                                      # how far the head is ahead of the pelvis
             'body_lean': math.degrees(math.atan2((head - 0.5 * (g('J_Bip_L_Foot') + g('J_Bip_R_Foot'))).y, (head - 0.5 * (g('J_Bip_L_Foot') + g('J_Bip_R_Foot'))).z)),   # mid-feet -> head against the vertical
             'hips_z': hips.z, 'hips_x': hips.x, 'head_x': head.x, 'head_z': head.z,
             'shoulder_yaw': math.degrees(math.atan2((sr - sl).y, (sr - sl).x)),
             'pelvis_yaw': math.degrees(math.atan2((lr - ll).y, (lr - ll).x)),
             'shoulder_roll': math.degrees(math.atan2((sr - sl).z, (sr - sl).x)),
             'pelvis_roll': math.degrees(math.atan2((lr - ll).z, (lr - ll).x))}
        hb = (arm.matrix_world @ P['J_Bip_C_Head'].matrix).to_3x3() @ P['J_Bip_C_Head'].bone.y_axis   # skull "up" direction in the world
        r['head_pitch'] = math.degrees(math.atan2(hb.y, hb.z))                                  # 0 = skull upright, + = tipped forward (the face looks down)
        for s in 'LR':
            ua, la, hd = g('J_Bip_%s_UpperArm' % s), g('J_Bip_%s_LowerArm' % s), g('J_Bip_%s_Hand' % s)
            r['elbow_' + s] = ang(ua - la, hd - la)
            v = la - ua
            r['uarm_swing_' + s] = math.degrees(math.atan2(v.y, -v.z))
            r['hand_z_rel_' + s] = hd.z - ua.z
            r['hand_y_rel_' + s] = hd.y - ua.y
            r['elbow_x_rel_' + s] = abs(la.x - ua.x)
            ul, kn, an = g('J_Bip_%s_UpperLeg' % s), g('J_Bip_%s_LowerLeg' % s), g('J_Bip_%s_Foot' % s)
            r['knee_' + s] = 180.0 - ang(ul - kn, an - kn)
        rows.append(r)

    def rng(k):
        v = [r[k] for r in rows]
        return (round(min(v), 2), round(max(v), 2), round(sum(v) / len(v), 2))
    out = {k: rng(k) for k in rows[0]}
    p2p = lambda k, s=1.0: round((max(r[k] for r in rows) - min(r[k] for r in rows)) * s, 2)
    out['hips_z_p2p_cm'], out['hips_x_p2p_cm'] = p2p('hips_z', 100), p2p('hips_x', 100)
    out['head_x_p2p_cm'], out['head_z_p2p_cm'] = p2p('head_x', 100), p2p('head_z', 100)
    for k in ('shoulder_yaw', 'pelvis_yaw', 'shoulder_roll', 'pelvis_roll'):
        out[k + '_p2p'] = p2p(k)
    res[name] = out
if OUT:
    json.dump(res, open(OUT, 'w'), indent=1)
KEYS = ('lean', 'neck_tilt', 'head_pitch', 'head_fwd_cm', 'body_lean', 'hips_z_p2p_cm', 'hips_x_p2p_cm', 'head_x_p2p_cm', 'head_z_p2p_cm', 'shoulder_yaw_p2p', 'pelvis_yaw_p2p', 'shoulder_roll_p2p', 'pelvis_roll_p2p',
        'elbow_L', 'elbow_R', 'uarm_swing_L', 'uarm_swing_R', 'hand_z_rel_L', 'hand_y_rel_L', 'elbow_x_rel_L', 'knee_L', 'knee_R')
for name, o in res.items():
    print('==', name)
    for k in KEYS:
        print('  %-18s %s' % (k, o[k]))
