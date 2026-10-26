"""
Yoru - IDLE v2, round 5: makes the FINAL self-contained idle file from the stage copy: only the chosen Yoru (collection A2_Kontrapost)
standing at the origin with the body action (Yoru_Idle_v2: 12 s loop, ears with the B angle) and the face action on her shape keys
(Yoru_Idle_v2_Face: blink + expression B), plus the floor.  Every other Yoru of the stage (A, B, C, the four face Yorus) and every label go,
only these two actions stay, the icosphere of the glTF import is never rendered and its collection is excluded, all textures are packed,
no external path (checked).  The 3D view: Material Preview, no overlays, looking at her from the front right.
usage: blender -b --factory-startup <stage copy .blend> --python build_idle_v2_finalize_r5.py -- <out .blend> [body action] [face action]
The stage copy is not changed (the result is saved under a new name).
"""
import bpy, sys, os, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
BODY = argv[1] if len(argv) > 1 else 'Yoru_Idle_v2'
FACE_ACT = argv[2] if len(argv) > 2 else 'Yoru_Idle_v2_Face'
KEEP = 'A2_Kontrapost'
log = lambda *a: print('[finalize r5]', *a, flush=True)

arm = next(o for o in bpy.data.collections[KEEP].all_objects if o.type == 'ARMATURE')
keep_objs = set(o.name for o in bpy.data.collections[KEEP].all_objects)
# round 6: the kept collection may hang under a parent collection (Idle_v2); link it to the scene root first, so removing the
# parent does not take Yoru out of the scene
root = bpy.context.scene.collection
keep_col = bpy.data.collections[KEEP]
if keep_col.name not in [c.name for c in root.children]:
    root.children.link(keep_col)
for parent in list(bpy.data.collections):
    if keep_col.name in [c.name for c in parent.children]:
        parent.children.unlink(keep_col)
removed = []
for col in list(bpy.data.collections):
    if col.name in (KEEP, 'glTF_not_exported'):
        continue
    for o in list(col.all_objects):
        if o.name not in keep_objs:
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(col)
for o in list(bpy.data.objects):
    if o.name.startswith('Label_'):
        removed.append(o.name)
        bpy.data.objects.remove(o, do_unlink=True)
log('removed', len(removed), 'objects')
for o in bpy.data.objects:
    if o.name.startswith('Icosphere'):
        o.hide_render = True
        o.hide_viewport = True
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name == 'glTF_not_exported':
        lc.exclude = True
    if lc.name == KEEP:
        lc.exclude = False
        lc.hide_viewport = False
# the kept Yoru: origin, plain names
arm.location = Vector((0.0, 0.0, 0.0))
for c in arm.children:
    base = c.name.split('_A2')[0].split('.')[0]
    if base in ('Body', 'Face', 'Hair') and bpy.data.objects.get(base) is None:
        c.name = base
    c.hide_set(False)
    c.hide_viewport = False
arm.name = 'Yoru'
bpy.data.collections[KEEP].name = 'Yoru_Idle_v2'
# actions: the body loop on the armature, the face on the shape keys of the face mesh
body = bpy.data.actions[BODY]
face_act = bpy.data.actions[FACE_ACT]
ad = arm.animation_data_create()
ad.action = body
if hasattr(ad, 'action_slot') and body.slots:
    ad.action_slot = body.slots[0]
face = next(c for c in arm.children if c.type == 'MESH' and c.data.shape_keys and 'Fcl_EYE_Close' in c.data.shape_keys.key_blocks)
skad = face.data.shape_keys.animation_data or face.data.shape_keys.animation_data_create()
skad.action = face_act
if hasattr(skad, 'action_slot') and face_act.slots:
    skad.action_slot = face_act.slots[0]
gone = []
for a in list(bpy.data.actions):
    if a not in (body, face_act):
        gone.append(a.name)
        bpy.data.actions.remove(a)
log('actions kept:', body.name, face_act.name, '| removed', len(gone), gone)
# scene
scene = bpy.context.scene
nf = int(round(body.frame_range[1] - body.frame_range[0]))
scene.render.fps, scene.render.fps_base = 30, 1.0
scene.frame_start, scene.frame_end = 0, nf - 1
scene.frame_current = 0
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    log('engine', e)
scene.render.filepath = '//'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'


def look_rotation(look):
    look = Vector(look).normalized()
    right = look.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(look).normalized()
    return Matrix((right, up, -look)).transposed().to_quaternion()


n_views = 0
for scr in bpy.data.screens:
    for area in scr.areas:
        if area.type != 'VIEW_3D':
            continue
        sp = area.spaces.active
        sp.shading.type = 'MATERIAL'
        sp.overlay.show_overlays = False
        try:
            sp.show_object_viewport_armature = False
        except Exception:
            pass
        r3d = sp.region_3d
        if r3d is not None:
            r3d.view_perspective = 'PERSP'
            r3d.view_rotation = look_rotation((-0.55, -0.82, -0.12))
            r3d.view_distance = 3.0
            r3d.view_location = Vector((0.0, 0.0, 0.84))
            n_views += 1
log('3D views set:', n_views)
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file and im.filepath:
        im.pack()
paths = bpy.utils.blend_paths(absolute=True)
log('external paths:', paths, '| libraries:', [l.filepath for l in bpy.data.libraries], '| images packed:',
    all(bool(im.packed_file) for im in bpy.data.images if im.source == 'FILE'))
assert not paths, 'external paths left: %s' % paths
log('objects now:', sorted(o.name for o in bpy.data.objects), '| frames', scene.frame_start, scene.frame_end, '| fps', scene.render.fps)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
log('saved', OUT)
