"""Lauf v2: renders stills of 'Neu' (Yoru_Lauf) and / or 'Alt' from the work file (only the rendered Yoru and her floor lane are visible).
usage: blender -b --factory-startup <Yoru_Lauf_v2_roundN.blend> --python build_lauf_v2_render.py -- <out dir> <jobs> [samples]
  jobs: semicolon separated  'keys|views|frames'  e.g.  'Neu|side,back|0-39;Neu|armSide,armBack|0-39:2'
  frames: '0' or '0,7' or '0-39' (inclusive) or '0-39:2' (every second)
Views (sizes as the NTE strips):
  side     380 x 500  from her right at hip height, perspective (82 mm, 4 m), the figure centred, head and feet in the picture (like the NTE side clip)
  back     360 x 500  the game camera of the project (4.4 m behind, 0.35 m to the right, 1.75 m high, 72 mm)
  armSide  500 x 400  close-up of the upper body from her right (85 mm, 3 m, chest height)
  armBack  480 x 440  close-up of the upper body from behind (85 mm, 3 m)
Writes <out dir>/<key>/<view>_<frame:03d>.png.  EEVEE, a sun and the dark world of the idle renders."""
import bpy, sys, os, math, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
JOBS = [j.split('|') for j in argv[1].split(';')]
SAMPLES = int(argv[2]) if len(argv) > 2 else 16
scene = bpy.context.scene
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print('engine:', e)
scene.render.resolution_percentage = 100
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
    if o.name.startswith('Label_') or o.name.startswith('Icosphere'):
        o.hide_render = True
target = bpy.data.objects.new('target_render', None)
scene.collection.objects.link(target)


def cam(name, rel_loc, lens, tgt, size):
    d = bpy.data.cameras.new(name)
    d.type = 'PERSP'
    d.lens = lens
    d.clip_end = 80
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    c = o.constraints.new('TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return o, Vector(rel_loc), Vector(tgt), size


CAMS = {
    'side': cam('side', (4.0, 0.05, 0.86), 82.0, (0.0, 0.05, 0.80), (380, 500)),
    'back': cam('back', (0.35, -4.4, 1.75), 72.0, (0.0, -0.05, 0.80), (360, 500)),
    'armSide': cam('armSide', (3.0, 0.10, 1.10), 85.0, (0.0, 0.10, 1.02), (500, 400)),
    'armBack': cam('armBack', (0.10, -3.0, 1.25), 85.0, (0.0, 0.0, 1.00), (480, 440)),
    'arm34': cam('arm34', (2.2 * math.sin(math.radians(40)), 2.2 * math.cos(math.radians(40)), 1.25), 85.0, (0.0, 0.08, 1.05), (500, 400)),
    'arm34L': cam('arm34L', (-2.2 * math.sin(math.radians(40)), 2.2 * math.cos(math.radians(40)), 1.25), 85.0, (0.0, 0.08, 1.05), (500, 400)),
    'side95': cam('side95', (4.0, 0.05, 0.86), 95.0, (0.0, 0.05, 0.82), (380, 500)),
    'back88': cam('back88', (0.35, -4.4, 1.75), 88.0, (0.0, -0.05, 0.82), (360, 500)),
}
KEYS = {'Neu': ('Lauf_v2_R1_Neu', 'Boden_Lauf_Neu'), 'Alt': ('Lauf_v2_R1_Alt', 'Boden_Lauf_Alt')}
coll = {k: list(bpy.data.collections[c].all_objects) for k, (c, _) in KEYS.items() if c in bpy.data.collections}


def parse_frames(s):
    out = []
    for part in s.split(','):
        step = 1
        if ':' in part:
            part, step = part.split(':')
            step = int(step)
        if '-' in part:
            a, b = part.split('-')
            out.extend(range(int(a), int(b) + 1, step))
        else:
            out.append(int(part))
    return out


T0 = time.time()
n = 0
for keys, views, frs in JOBS:
    for k in keys.split(','):
        for kk, objs in coll.items():
            for o in objs:
                if o.type == 'MESH' and o.name.startswith('Icosphere'):
                    continue
                o.hide_render = (kk != k)
        for kk, (_, fl) in KEYS.items():
            if fl in bpy.data.objects:
                ob_ = bpy.data.objects[fl]
                ob_.hide_render = (kk != k)
                if kk == k:                          # render session only (not saved): the lane spans the whole picture
                    for v_ in ob_.data.vertices:
                        v_.co.x = -12.0 if v_.co.x < 0.0 or (v_.co.x == 0.0 and k == 'Alt') else 12.0
        armo = next(o for o in coll[k] if o.type == 'ARMATURE')
        base = armo.matrix_world.translation.copy()
        os.makedirs(os.path.join(OUT, k), exist_ok=True)
        for f in parse_frames(frs):
            scene.frame_set(f)
            for view in views.split(','):
                o, rel, tgt, size = CAMS[view]
                scene.render.resolution_x, scene.render.resolution_y = size
                target.location = base + tgt
                o.location = base + rel
                scene.camera = o
                scene.render.filepath = os.path.join(OUT, k, '%s_%03d.png' % (view, f))
                bpy.ops.render.render(write_still=True)
                n += 1
        print('rendered', k, views, '%.2f s per picture' % ((time.time() - T0) / max(n, 1)), flush=True)
print('STILLS DONE', n, 'pictures in %.0f s' % (time.time() - T0))
