"""Pose export of a finished v2 animation for the Unity baker (same format as Blender/Yoru_Idle_pose.json, written by build_idle.py).

usage (background Blender, the .blend is opened first):
  blender -b --factory-startup <blend> --python export_pose_v2.py -- <out pose.json> [<action name>] [<glb with the VRM humanoid map>]
  e.g. blender -b --factory-startup Blender/Yoru_Idle_v2.blend --python Blender/scripts/export_pose_v2.py -- Blender/Yoru_Idle_v2_pose.json Yoru_Idle_v2

Then:  python Blender/scripts/export_stream.py Blender/Yoru_Idle_v2_pose.json Tools/AnimStreams/Yoru_Idle.json Yoru_Idle 1

Per frame (first frame ... last frame, plus one more frame that repeats the first, so the loop is seamless):
  D[node]            = world rotation of the posed bone * inverse(world rotation of the bone in the T-pose (rest)),  [w, x, y, z]
  hips_world_offset  = world displacement of the hips head against its rest position
Blender axes (+Y forward, -X = her left, +Z up). Only the humanoid bones (VRM map) are written; ears, tail and hair are not humanoid.
"""
import bpy, json, sys, struct

args = sys.argv[sys.argv.index('--') + 1:]
OUT = args[0]
ACTION = args[1] if len(args) > 1 else None
GLB = args[2] if len(args) > 2 else r'C:\Users\valen\ZeroProtocol\Blender\work\Yoru_V2.glb'

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if ACTION:
    arm.animation_data.action = bpy.data.actions[ACTION]
act = arm.animation_data.action
f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
fps = scene.render.fps
print('armature', arm.name, 'action', act.name, 'range', f0, f1, 'fps', fps, 'scale', tuple(arm.scale), 'loc', tuple(arm.location))

with open(GLB, 'rb') as f:
    f.read(12)
    clen, _ = struct.unpack('<II', f.read(8))
    js = json.loads(f.read(clen).decode('utf-8'))
nodes = js['nodes']
H = {h['bone']: nodes[h['node']]['name'] for h in js['extensions']['VRM']['humanoid']['humanBones']}
missing = [n for n in H.values() if n not in arm.data.bones]
assert not missing, 'bones missing in the armature: %s' % missing

for o in bpy.data.objects:                                   # only the pose is needed, skip the mesh evaluation
    if o.type == 'MESH':
        o.hide_viewport = True

mw = arm.matrix_world


def rot(m):
    return m.to_3x3().normalized().to_quaternion()


R0 = {n: rot(mw @ arm.data.bones[n].matrix_local) for n in H.values()}
hips = H['hips']
hips_rest = mw @ arm.data.bones[hips].head_local

prev = {}


def eval_frame(f, keep_sign=True):
    scene.frame_set(f)
    ev = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    D = {}
    for n in H.values():
        q = rot(mw @ ev.pose.bones[n].matrix) @ R0[n].inverted()
        if keep_sign and n in prev and prev[n].dot(q) < 0:
            q = -q
        prev[n] = q
        D[n] = [q.w, q.x, q.y, q.z]
    off = (mw @ ev.pose.bones[hips].head) - hips_rest
    return D, [off.x, off.y, off.z]


# the loop: if the last key of the action already repeats the first one (same pose), it is the closing frame; else add one more frame
Da, offa = eval_frame(f0, False)
Db, offb = eval_frame(f1, False)
same = max(abs(x - y) for n in H.values() for x, y in zip(Da[n], Db[n]))
closing_in_action = same < 2e-3 or max(abs(x - y) for n in H.values() for x, y in zip(Da[n], [-v for v in Db[n]])) < 2e-3
total = (f1 - f0 + 1) if closing_in_action else (f1 - f0 + 2)
print('first/last key differ by', same, '-> closing frame in action:', closing_in_action, ', frames written:', total)
prev.clear()
frames_data = []
for i in range(total):
    D, off = eval_frame(f0 + i)
    frames_data.append({'frame': i, 'hips_world_offset': off, 'D': D})
n_loop = total - 1

# seam check: the extra frame must equal the first one
seam = max(abs(a - b) for n in H.values() for a, b in zip(frames_data[0]['D'][n], frames_data[-1]['D'][n]))
print('frames', len(frames_data), 'seam max |dq|', seam)

with open(OUT, 'w') as f:
    json.dump({'fps': fps, 'frames': len(frames_data), 'loop_seconds': n_loop / fps,
               'note': 'D = world-space rotation delta from the T-pose per humanoid bone (Blender axes: +Y forward, -X = her left); source ' + bpy.data.filepath,
               'humanoid_map': H, 'hips_rest': [hips_rest.x, hips_rest.y, hips_rest.z], 'data': frames_data}, f)
print('WROTE', OUT)
