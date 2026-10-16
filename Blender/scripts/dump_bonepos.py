"""Bone head positions per frame (Unity axes) of a finished Blender animation, for the Unity pose parity test (PoseParityTest).
usage: blender -b --factory-startup <blend> --python dump_bonepos.py -- [<pose.json> <out.json>]
without arguments the walk is dumped (Yoru_Walk_pose.json -> Yoru_Walk_bonepos.json)"""
import bpy, json, sys

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
POSE = args[0] if len(args) > 0 else r'C:\Users\valen\ZeroProtocol\Blender\Yoru_Walk_pose.json'
OUT = args[1] if len(args) > 1 else r'C:\Users\valen\ZeroProtocol\Blender\Yoru_Walk_bonepos.json'
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
pose = json.load(open(POSE))
hmap = pose['humanoid_map']
keys = list(hmap)
names = [k[0].upper() + k[1:] for k in keys]
NF = pose['frames'] - 1
frames = []
for f in range(NF):
    scene.frame_set(f)
    pb = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
    row = []
    for k in keys:
        h = pb[hmap[k]].head
        row.append([h.x, h.z, h.y])                        # Blender (x, y, z) -> Unity (x, z, y)
    frames.append(row)
json.dump({'frames': NF, 'bones': names, 'pos': frames, 'note': 'bone head positions in Unity axes (x right, y up, z forward), model origin = floor, metres'},
          open(OUT, 'w'))
print('DUMPED', len(names), 'bones', NF, 'frames')
