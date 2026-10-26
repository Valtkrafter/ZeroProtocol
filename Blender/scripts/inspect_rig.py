"""Prints rest positions (armature space, metres) of the humanoid bones and the body bounding box.  READ-ONLY.
usage: blender -b --factory-startup --python inspect_rig.py -- <Yoru.glb>
"""
import bpy, sys, json, struct

argv = sys.argv[sys.argv.index('--') + 1:]
GLB = argv[0]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Body']
with open(GLB, 'rb') as f:
    f.read(12)
    clen, _ = struct.unpack('<II', f.read(8))
    js = json.loads(f.read(clen).decode('utf-8'))
nodes = js['nodes']
H = {h['bone']: nodes[h['node']]['name'] for h in js['extensions']['VRM']['humanoid']['humanBones']}
bones = arm.data.bones
print('ARM matrix_world', [round(x, 3) for x in arm.matrix_world.translation], 'scale', [round(x, 3) for x in arm.scale])
for key in ['hips', 'spine', 'chest', 'upperChest', 'neck', 'head', 'leftShoulder', 'leftUpperArm', 'leftLowerArm', 'leftHand',
            'rightShoulder', 'rightUpperArm', 'rightLowerArm', 'rightHand', 'leftUpperLeg', 'leftLowerLeg', 'leftFoot', 'rightFoot']:
    if key in H:
        b = bones[H[key]]
        print('BONE %-14s %-22s head %s tail %s' % (key, H[key], [round(x, 3) for x in b.head_local], [round(x, 3) for x in b.tail_local]))
vs = [v.co for v in body.data.vertices]
xs, ys, zs = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
print('BODY bbox x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f' % (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
print('OBJECTS', [(o.name, o.type) for o in bpy.data.objects if o.type in ('MESH', 'ARMATURE')][:20])
