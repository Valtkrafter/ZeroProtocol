"""Numbers of the finished Blender walk that the Unity checks (WalkVerifyTest) compare with: tail tip swing relative to the hips,
swing of the bust / ear / hair spring bones (angle of the pose rotation of their first joints), pelvis, steps.
usage: blender -b --factory-startup <Yoru_Walk.blend> --python dump_reference.py -- <out json>"""
import bpy, sys, json, math
from mathutils import Vector

out = sys.argv[sys.argv.index('--') + 1]
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
NF = int(round(arm.animation_data.action.frame_range[1]))
tail = 'J_Opt_C_CatTail8_01'
mn = [9.0, 9.0, 9.0]
mx = [-9.0, -9.0, -9.0]
hips_z = []
for f in range(NF):
    scene.frame_set(f)
    pb = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
    d = pb[tail].head - pb['J_Bip_C_Hips'].head
    for k in range(3):
        mn[k] = min(mn[k], d[k])
        mx[k] = max(mx[k], d[k])
    hips_z.append(pb['J_Bip_C_Hips'].head.z)


def swing(names):
    big, tot, n = 0.0, 0.0, 0
    for f in range(NF):
        scene.frame_set(f)
        for bn in names:
            q = arm.pose.bones[bn].rotation_quaternion
            a = 2.0 * math.degrees(math.acos(min(1.0, abs(q.w))))
            big = max(big, a)
            tot += a
            n += 1
    return [big, tot / max(1, n)]


pbs = arm.pose.bones
data = {
    'frames': NF,
    'tail_tip_vs_hips': {'x': [mn[0], mx[0]], 'y_reach': [mn[1], mx[1]], 'z_height': [mn[2], mx[2]],
                         'side_mm': (mx[0] - mn[0]) * 1000.0, 'height_mm': (mx[2] - mn[2]) * 1000.0},
    'bust_first': swing([b.name for b in pbs if b.name in ('J_Sec_L_Bust1', 'J_Sec_R_Bust1')]),
    'ear_tip': swing([b.name for b in pbs if b.name.startswith('J_Opt_L_CatEar2')]),
    'hair_first': swing([b.name for b in pbs if b.name.startswith('J_Sec_Hair') and b.name.endswith('_01')]),
    'pelvis_range_mm': (max(hips_z) - min(hips_z)) * 1000.0,
}
json.dump(data, open(out, 'w'), indent=1)
print('REFERENCE', json.dumps(data)[:600])
