"""Idle v2, round 2: renders stills or the frames of the loop for one or more Yorus of the stage (collections A_Kontrapost, B_Catwalk,
C_Kompakt, A2_Kontrapost).  Only the Yoru that is rendered is visible; the cameras look at its armature.
usage: blender -b <stage copy> --python build_idle_v2_render_r2.py -- <out dir> <variants, e.g. A2> <views, e.g. front34,side,game> <frames> [samples] [scale %] [floor half size m]
       frames: '0' or '0,24,48' or '0-239' (inclusive) or '0-239:2' (every 2nd)
       floor half size: makes the floor 'Boden' that big for the render only (the file is not saved), so no floor edge shows in the picture
Writes <out dir>/stills_<V>/<view>_<frame:03d>.png (600 x 720 at 100 %).  EEVEE, a sun and the dark world of render_walk_stills.py.
Views: front34 = front right (35 deg), side = from her right, back = from behind, back34 = behind right (30 deg), front = front,
       game = like the shoulder camera of the game (perspective, 4.4 m behind her, 0.35 m to the right, above her, ThirdPersonCamera.cs).
"""
import bpy, sys, os, math, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KEYS = argv[1].split(',')
VIEWS = argv[2].split(',')
FR = argv[3]
SAMPLES = int(argv[4]) if len(argv) > 4 else 16
SCALE = int(argv[5]) if len(argv) > 5 else 100
FLOOR = float(argv[6]) if len(argv) > 6 else 0.0
COLL = {'A': 'A_Kontrapost', 'B': 'B_Catwalk', 'C': 'C_Kompakt', 'A2': 'A2_Kontrapost'}


def parse_frames(s):
    out = []
    for part in s.split(','):
        step = 1
        if ':' in part:
            part, st = part.split(':')
            step = int(st)
        if '-' in part:
            a, b = part.split('-')
            out.extend(range(int(a), int(b) + 1, step))
        else:
            out.append(int(part))
    return out


FRAMES = parse_frames(FR)
scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print('engine:', e)
scene.render.resolution_x, scene.render.resolution_y = 600, 720
scene.render.resolution_percentage = SCALE
try:
    scene.eevee.taa_render_samples = SAMPLES
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
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
    if o.name.startswith('Label_') or o.name.startswith('Icosphere'):   # the icosphere is the bone shape of the glTF import (2 m wide)
        o.hide_render = True
if FLOOR > 0.0 and 'Boden' in bpy.data.objects:
    fl = bpy.data.objects['Boden']
    for v, c in zip(fl.data.vertices, ((-FLOOR, -FLOOR), (FLOOR, -FLOOR), (FLOOR, FLOOR), (-FLOOR, FLOOR))):
        v.co = (c[0], c[1], 0.0)
    fl.data.update()
# the live file may have hidden collections (viewport); for rendering every collection takes part, visibility is set per object below
for lc in bpy.context.view_layer.layer_collection.children:
    if lc.name in COLL.values():
        lc.exclude = False
        lc.hide_viewport = False

target = bpy.data.objects.new('target_render', None)
scene.collection.objects.link(target)


def cam(name, rel_loc, scale=2.0, lens=None):
    d = bpy.data.cameras.new(name)
    if lens:
        d.type = 'PERSP'
        d.lens = lens
    else:
        d.type = 'ORTHO'
        d.ortho_scale = scale
    d.clip_end = 60
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    c = o.constraints.new('TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return o, Vector(rel_loc)


CAMS = {
    'front34': cam('front34', (6.0 * math.sin(math.radians(35)), 6.0 * math.cos(math.radians(35)), 1.3)),
    'side': cam('side', (6.0, -0.05, 0.8)),
    'back': cam('back', (0.0, -6.0, 0.8)),
    'back34': cam('back34', (6.0 * math.sin(math.radians(150)), 6.0 * math.cos(math.radians(150)), 1.6)),
    'front': cam('front', (0.0, 6.0, 0.8)),
    'game': cam('game', (0.35, -4.4, 1.75), lens=72.0),
}
coll_objs = {k: list(bpy.data.collections[COLL[k]].all_objects) for k in COLL if COLL[k] in bpy.data.collections}
T0 = time.time()
n = 0
for k in KEYS:
    for kk, objs in coll_objs.items():
        for o in objs:
            if o.type == 'MESH' and o.name.startswith('Icosphere'):
                continue
            o.hide_render = (kk != k)
            if kk == k:
                o.hide_viewport = False
    armo = next(o for o in coll_objs[k] if o.type == 'ARMATURE')
    base = armo.matrix_world.translation.copy()
    target.location = base + Vector((0.0, -0.05, 0.80))
    os.makedirs(os.path.join(OUT, 'stills_%s' % k), exist_ok=True)
    for f in FRAMES:
        scene.frame_set(f)
        for view in VIEWS:
            o, rel = CAMS[view]
            o.location = base + rel
            scene.camera = o
            scene.render.filepath = os.path.join(OUT, 'stills_%s' % k, '%s_%03d.png' % (view, f))
            bpy.ops.render.render(write_still=True)
            n += 1
        if f % 20 == 0:
            print('rendered', k, 'frame', f, '%.1f s per picture' % ((time.time() - T0) / max(n, 1)), flush=True)
print('STILLS DONE', n, 'pictures in %.0f s' % (time.time() - T0))
