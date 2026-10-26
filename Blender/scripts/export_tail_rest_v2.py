"""Mean shape of the cat tail in a finished v2 idle, for YoruSecondaryMotion (standing tail rest shape in Unity).

usage (background Blender):
  blender -b --factory-startup Blender/Yoru_Idle_v2.blend --python Blender/scripts/export_tail_rest_v2.py -- <out json> [<action name>]

For every tail joint (J_Opt_C_CatTail1_01 .. 8_01), over the loop: the world rotation delta from the T-pose, with the world delta of the hips taken out
(E_i = D_hips^-1 * D_i), averaged over all frames (quaternion mean) and mapped to Unity axes as in export_stream.py ([-x, -z, -y, w]).
Also the mean head position of every joint (and the tip of the last one) relative to the hips head, with the hips rotation taken out, Unity axes, metres,
so the shape can be checked in Unity.  Blender: +Y forward, -X = her left, +Z up.
"""
import bpy, json, sys
from mathutils import Quaternion, Vector

args = sys.argv[sys.argv.index('--') + 1:]
OUT = args[0]
ACTION = args[1] if len(args) > 1 else 'Yoru_Idle_v2'
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.animation_data.action = bpy.data.actions[ACTION]
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_viewport = True
mw = arm.matrix_world
HIPS = 'J_Bip_C_Hips'
TAIL = ['J_Opt_C_CatTail%d_01' % i for i in range(1, 9)]


def rot(m):
    return m.to_3x3().normalized().to_quaternion()


R0 = {n: rot(mw @ arm.data.bones[n].matrix_local) for n in [HIPS] + TAIL}
n_frames = 360
acc = {n: Quaternion((0, 0, 0, 0)) for n in TAIL}
pos_acc = [Vector((0, 0, 0)) for _ in range(len(TAIL) + 1)]
ref = {}
for f in range(n_frames):
    scene.frame_set(f)
    ev = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    Dh = rot(mw @ ev.pose.bones[HIPS].matrix) @ R0[HIPS].inverted()
    hips_head = mw @ ev.pose.bones[HIPS].head
    for i, n in enumerate(TAIL):
        Di = rot(mw @ ev.pose.bones[n].matrix) @ R0[n].inverted()
        E = Dh.inverted() @ Di
        if n in ref and ref[n].dot(E) < 0:
            E = -E
        ref.setdefault(n, E)
        acc[n] = Quaternion((acc[n].w + E.w, acc[n].x + E.x, acc[n].y + E.y, acc[n].z + E.z))
        pos_acc[i] += Dh.inverted() @ ((mw @ ev.pose.bones[n].head) - hips_head)
    pos_acc[len(TAIL)] += Dh.inverted() @ ((mw @ ev.pose.bones[TAIL[-1]].tail) - hips_head)

delta_unity = []
for n in TAIL:
    q = acc[n]
    q.normalize()
    delta_unity.append([-q.x, -q.z, -q.y, q.w])                   # Blender (w,x,y,z) -> Unity (x,y,z,w), as export_stream.py
pos_unity = []
for p in pos_acc:
    p = p / n_frames
    pos_unity.append([p.x, p.z, p.y])                              # Blender (x,y,z) -> Unity (x,z,y)
json.dump({'joints': TAIL, 'delta': delta_unity, 'positions': pos_unity, 'frames': n_frames,
           'note': 'delta = mean over the idle loop of D_hips^-1 * D_joint (world axes, Unity xyzw); positions = joint heads + tip relative to the hips head, hips rotation removed (Unity axes, m)'},
          open(OUT, 'w'), indent=1)
print('WROTE', OUT)
for n, d, p in zip(TAIL + ['tip'], delta_unity + [None], pos_unity):
    print(n, [round(x, 3) for x in d] if d else '', [round(x, 3) for x in p])
