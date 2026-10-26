"""
Yoru - IDLE v2: makes the self-contained idle file from the stage copy: only the chosen Yoru (collection A2_Kontrapost) with the loop and the
blink, standing at the origin, the floor, the scene at 30 fps 0 .. NF-1, EEVEE, the 3D view in Material Preview without overlays looking at her
from the front right.  All textures are packed and there are no libraries, so the file can simply be copied (e.g. to Blender/Yoru_Idle_v2.blend
once the user has approved it); the script checks that no external path is left.
usage: blender -b --factory-startup <stage copy .blend> --python build_idle_v2_finalize.py -- <out .blend> [action name, default Yoru_Idle_v2]
The stage copy is not changed (the result is saved under a new name).
"""
import bpy, sys, os, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
ACTION = argv[1] if len(argv) > 1 else 'Yoru_Idle_v2'
KEEP = 'A2_Kontrapost'
DROP = ('A_Kontrapost', 'B_Catwalk', 'C_Kompakt')
log = lambda *a: print('[finalize]', *a, flush=True)

arm = next(o for o in bpy.data.collections[KEEP].all_objects if o.type == 'ARMATURE')
keep_objs = set(o.name for o in bpy.data.collections[KEEP].all_objects)
# 1. the other Yorus and the floor labels go (their meshes stay where the kept Yoru uses them)
removed = []
for cn in DROP:
    col = bpy.data.collections.get(cn)
    if not col:
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
log('removed', len(removed), 'objects:', removed)
# the icosphere of the glTF import is only the bone display shape (2 m wide at the origin): never in a render, its collection excluded
for o in bpy.data.objects:
    if o.name.startswith('Icosphere'):
        o.hide_render = True
        o.hide_viewport = True
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name == 'glTF_not_exported':
        lc.exclude = True
# 2. the kept Yoru: origin, plain names
arm.location = Vector((0.0, 0.0, 0.0))
for c in arm.children:
    base = c.name.split('_A2')[0].split('.')[0]
    if base in ('Body', 'Face', 'Hair') and bpy.data.objects.get(base) is None:
        c.name = base
arm.name = 'Yoru'
bpy.data.collections[KEEP].name = 'Yoru_Idle_v2'
# 3. only the final actions stay (earlier tries live on in the stage copy)
act = bpy.data.actions[ACTION]
blink = None
for c in arm.children:
    sk = c.data.shape_keys if c.type == 'MESH' else None
    if sk and sk.animation_data and sk.animation_data.action:
        blink = sk.animation_data.action
gone = []
for a in list(bpy.data.actions):
    if a != act and a != blink:
        gone.append(a.name)
        bpy.data.actions.remove(a)
log('actions kept:', act.name, blink.name if blink else None, '| removed:', gone)
# 4. scene
scene = bpy.context.scene
nf = int(round(act.frame_range[1] - act.frame_range[0]))
scene.render.fps, scene.render.fps_base = 30, 1.0
scene.frame_start, scene.frame_end = 0, nf - 1
scene.frame_current = 0
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    log('engine', e)
scene.render.filepath = '//'
# 5. the 3D view of the saved layout: Material Preview, no overlays, looking at her from the front right
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
# 6. nothing may point outside the file
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
