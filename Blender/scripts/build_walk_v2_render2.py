"""Walk v2, round 2: renders one walk file as it is (any Yoru walk .blend with one armature, e.g. the old Blender/Yoru_Walk.blend, which is
only read, never saved).  Cameras are placed relative to the armature object.  The file's own scrolling floor is used if it has one.
usage: blender -b --factory-startup <walk .blend> --python build_walk_v2_render2.py -- <out dir> <views> <frames> [scale %] [armature name]
  frames: '0,2,4' or '0-28' (inclusive)
Writes <out dir>/<view>_<frame:03d>.png (600 x 720 at SCALE %).  Views as build_walk_v2_render.py (front34, side, back, game, armR, armL)."""
import bpy, sys, os, math, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, VIEWS, FRS = argv[0], argv[1].split(','), argv[2]
SCALE = int(argv[3]) if len(argv) > 3 else 70
ARM = argv[4] if len(argv) > 4 else None
scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print('engine:', e)
scene.render.resolution_x, scene.render.resolution_y = 600, 720
scene.render.resolution_percentage = SCALE
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
for o in list(scene.objects):
    if o.type == 'LIGHT':
        o.hide_render = True
sun = bpy.data.lights.new('sun_render', 'SUN')
sun.energy = 3.5
so = bpy.data.objects.new('sun_render', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(35))
world = bpy.data.worlds.new('w_render')
world.use_nodes = True
bgn = next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND')
bgn.inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
scene.world = world
for o in bpy.data.objects:
    if o.name.startswith('Label_') or o.name.startswith('Icosphere'):
        o.hide_render = True
arm = bpy.data.objects[ARM] if ARM else next(o for o in scene.objects if o.type == 'ARMATURE' and not o.hide_render)
base = arm.matrix_world.translation.copy()
target = bpy.data.objects.new('target_render', None)
scene.collection.objects.link(target)
REL = {'front34': ((6.0 * math.sin(math.radians(35)), 6.0 * math.cos(math.radians(35)), 1.3), None, (0.0, -0.05, 0.80)),
       'side': ((6.0, -0.05, 0.8), None, (0.0, -0.05, 0.80)),
       'back': ((0.0, -6.0, 0.8), None, (0.0, -0.05, 0.80)),
       'game': ((0.35, -4.4, 1.75), 72.0, (0.0, -0.05, 0.80)),
       'armR': ((1.45, 1.05, 1.05), 85.0, (0.13, 0.02, 0.93)),
       'armL': ((-1.45, 1.05, 1.05), 85.0, (-0.13, 0.02, 0.93))}
cams = {}
for v in VIEWS:
    rel, lens, tgt = REL[v]
    d = bpy.data.cameras.new(v)
    if lens:
        d.type, d.lens = 'PERSP', lens
    else:
        d.type, d.ortho_scale = 'ORTHO', 2.0
    d.clip_end = 60
    o = bpy.data.objects.new(v, d)
    scene.collection.objects.link(o)
    c = o.constraints.new('TRACK_TO')
    c.target, c.track_axis, c.up_axis = target, 'TRACK_NEGATIVE_Z', 'UP_Y'
    cams[v] = (o, Vector(rel), Vector(tgt))
frames = []
for part in FRS.split(','):
    if '-' in part:
        a, b = part.split('-')
        frames.extend(range(int(a), int(b) + 1))
    else:
        frames.append(int(part))
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
for f in frames:
    scene.frame_set(f)
    for v in VIEWS:
        o, rel, tgt = cams[v]
        target.location = base + tgt
        o.location = base + rel
        scene.camera = o
        scene.render.filepath = os.path.join(OUT, '%s_%03d.png' % (v, f))
        bpy.ops.render.render(write_still=True)
print('STILLS DONE', len(frames) * len(VIEWS), 'pictures in %.0f s' % (time.time() - T0), 'armature', arm.name, 'frame range', scene.frame_start, scene.frame_end)
