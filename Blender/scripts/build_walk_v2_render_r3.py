"""Walk v2, round 3 (copy of build_walk_v2_render.py for the collections Walk_v2_R3_Alt / _N070 / _N083 / _N097): renders pictures of the variants from the work file (only the Yoru that is rendered is visible, the scrolling floor stays).
usage: blender -b --factory-startup <Yoru_Walk_v2_roundN.blend> --python build_walk_v2_render.py -- <out dir> <jobs>
  jobs: semicolon separated  'keys|views|frames'  e.g.  'A,B,C|front34,game|0-28;A,B,C|side|0,7;A,C|armR,armL,back|0,7'
  frames: '0' or '0,7' or '0-28' (inclusive)
Writes <out dir>/<V>/<view>_<frame:03d>.png (600 x 720 at SCALE %).  EEVEE, a sun and the dark world of the idle renders.
Views: front34 = front right (35 deg, ortho), side = from her right (ortho), back = from behind (ortho), game = the shoulder camera of the game
(4.4 m behind, 0.35 m to the right, 72 mm, as build_idle_v2_render_r2.py), armR / armL = 85 mm close-ups of elbow and hand from front-right /
front-left at hip height."""
import bpy, sys, os, math, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
JOBS = [j.split('|') for j in argv[1].split(';')]
SCALE = int(argv[2]) if len(argv) > 2 else 70
SAMPLES = int(argv[3]) if len(argv) > 3 else 16
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
    if o.name.startswith('Label_') or o.name.startswith('Icosphere'):
        o.hide_render = True
target = bpy.data.objects.new('target_render', None)
scene.collection.objects.link(target)


def cam(name, rel_loc, scale=2.0, lens=None, tgt=(0.0, -0.05, 0.80)):
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
    return o, Vector(rel_loc), Vector(tgt)


CAMS = {
    'front34': cam('front34', (6.0 * math.sin(math.radians(35)), 6.0 * math.cos(math.radians(35)), 1.3)),
    'side': cam('side', (6.0, -0.05, 0.8)),
    'back': cam('back', (0.0, -6.0, 0.8)),
    'game': cam('game', (0.35, -4.4, 1.75), lens=72.0),
    'armR': cam('armR', (1.45, 1.05, 1.05), lens=85.0, tgt=(0.13, 0.02, 0.93)),
    'armL': cam('armL', (-1.45, 1.05, 1.05), lens=85.0, tgt=(-0.13, 0.02, 0.93)),
}
coll = {k: list(bpy.data.collections['Walk_v2_R3_' + k].all_objects) for k in ('Alt', 'N070', 'N083', 'N097')}


def parse_frames(s):
    out = []
    for part in s.split(','):
        if '-' in part:
            a, b = part.split('-')
            out.extend(range(int(a), int(b) + 1))
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
        armo = next(o for o in coll[k] if o.type == 'ARMATURE')
        base = armo.matrix_world.translation.copy()
        os.makedirs(os.path.join(OUT, k), exist_ok=True)
        for f in parse_frames(frs):
            scene.frame_set(f)
            for view in views.split(','):
                o, rel, tgt = CAMS[view]
                target.location = base + tgt
                o.location = base + rel
                scene.camera = o
                scene.render.filepath = os.path.join(OUT, k, '%s_%03d.png' % (view, f))
                bpy.ops.render.render(write_still=True)
                n += 1
        print('rendered', k, views, '%.2f s per picture' % ((time.time() - T0) / max(n, 1)), flush=True)
print('STILLS DONE', n, 'pictures in %.0f s' % (time.time() - T0))
