"""READ-ONLY (never saved): how much do the VISIBLE meshes move?  Hair mesh relative to the head, arm width against the torso in the front view.
Frames 0..35 of Blender/Yoru_Run.blend (stage 1)."""
import bpy, math
import numpy as np
from mathutils import Vector

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
B = arm.data.bones
NF = 36
print('AUDIT mesh objects:', [(o.name, len(o.data.vertices)) for o in bpy.data.objects if o.type == 'MESH'])
HEAD = 'J_Bip_C_Head'

# sample bone matrices and evaluated meshes
head_m = []
meshes = {'Hair': [], 'Body': []}
for f in range(NF):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm.evaluated_get(dg)
    head_m.append(ae.pose.bones[HEAD].matrix.copy())
    for name in meshes:
        ob = bpy.data.objects[name]
        oe = ob.evaluated_get(dg)
        me = oe.to_mesh()
        co = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        mw = np.array(oe.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
        meshes[name].append(co.copy())
        oe.to_mesh_clear()

# ---- hair relative to the head frame
H = np.stack(meshes['Hair'])                      # (NF, N, 3) world
inv = [np.array(m.inverted()) for m in head_m]
Hh = np.stack([H[f] @ inv[f][:3, :3].T + inv[f][:3, 3] for f in range(NF)])
mean = Hh.mean(axis=0)
dev = np.linalg.norm(Hh - mean, axis=2).max(axis=0) * 1000.0      # per vertex: largest distance from its mean position in the head frame (mm)
rest_z = H[0][:, 2]
print('AUDIT hair vertices %d' % H.shape[1])
for lo, hi, label in ((0.0, 9.0, 'all'), (1.20, 9.0, 'above 1.20 m (scalp, ears region)'), (1.00, 1.20, 'neck / shoulder height 1.00..1.20 m'), (0.0, 1.00, 'below 1.00 m (long locks)')):
    sel = (rest_z >= lo) & (rest_z < hi)
    if sel.sum() == 0:
        continue
    d = dev[sel]
    print('AUDIT hair %-40s n=%6d | motion in the head frame: median %5.1f mm, 90%% %5.1f mm, 99%% %5.1f mm, max %5.1f mm' % (
        label, sel.sum(), np.median(d), np.percentile(d, 90), np.percentile(d, 99), d.max()))
# mean shift of the long locks against the head frame at rest (is there any wind streaming)?
Hrest_local = []
ob = bpy.data.objects['Hair']
co0 = np.empty(len(ob.data.vertices) * 3)
ob.data.vertices.foreach_get('co', co0)
co0 = co0.reshape(-1, 3)
mw = np.array(ob.matrix_world)
co0 = co0 @ mw[:3, :3].T + mw[:3, 3]
hr = np.array(B[HEAD].matrix_local.inverted())
rest_h = co0 @ hr[:3, :3].T + hr[:3, 3]
for lo, hi, label in ((1.00, 1.20, 'neck / shoulder height'), (0.0, 1.00, 'long locks')):
    sel = (co0[:, 2] >= lo) & (co0[:, 2] < hi)
    if sel.sum() == 0:
        continue
    shift = (mean[sel] - rest_h[sel]) * 1000.0
    print('AUDIT hair %-24s mean shift against the rest pose in the head frame: x %+5.1f  y (vertical) %+5.1f  z (+ = backward) %+5.1f mm' % (label, *shift.mean(axis=0)))

# ---- arms against the torso (front view): body mesh vertices
Bm = np.stack(meshes['Body'])                      # (NF, N, 3)
ob = bpy.data.objects['Body']
arm_groups = [vg.index for vg in ob.vertex_groups if any(k in vg.name for k in ('UpperArm', 'LowerArm', 'Hand', 'Shoulder', 'Thumb', 'Index', 'Middle', 'Ring', 'Little'))]
wa = np.zeros(len(ob.data.vertices))
for v in ob.data.vertices:
    for g in v.groups:
        if g.group in arm_groups:
            wa[v.index] += g.weight
is_arm = wa > 0.3
rz = Bm[0][:, 2]
body_sel = (~is_arm) & (rz > 0.95) & (rz < 1.30)
arm_sel = is_arm & (rz > 0.55)
print('AUDIT body mesh vertices %d, arm vertices %d, torso-band vertices %d' % (Bm.shape[1], is_arm.sum(), body_sel.sum()))
tw, aw, el = [], [], []
for f in range(NF):
    tw.append(np.abs(Bm[f][body_sel, 0]).max() * 1000.0)
    aw.append(np.abs(Bm[f][arm_sel, 0]).max() * 1000.0)
print('AUDIT front view: torso half width (z 0.95..1.30 m, without arms): %.0f..%.0f mm | outermost arm point: %.0f..%.0f mm (mean %.0f) -> arms stick out %.0f mm beyond the torso edge on average' % (
    min(tw), max(tw), min(aw), max(aw), sum(aw) / NF, sum(aw) / NF - sum(tw) / NF))
print('AUDIT done')
