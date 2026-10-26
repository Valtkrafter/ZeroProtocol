"""Idle v2, round 7: renders frames of ONE Yoru for the dynamics video and for looking at ears, tail and hair up close.
usage: blender -b --factory-startup <file .blend> --python build_idle_v2_render_r7.py -- <out dir> <views> <frames> [armature, default Yoru] [samples] [scale %]
       views: front34 (whole body, orthographic 2 m), head (head, ears and hair from the front, a little from her right, 85 mm, head to chest),
              tail (from behind on her right at hip height, 70 mm, hips to knees), game (shoulder camera of the game)
       frames: '0' or '0,24' or '0-359' or '150-170:2'
Writes <out dir>/stills_r7/<view>_<frame:03d>.png (600 x 720 at 100 %).  EEVEE, sun, dark world, floor +-10 m; only this Yoru and the floor
are rendered (a stage file holds several), the icosphere never.  The head view uses the colour look 'AgX - Medium High Contrast' (the pale
face reads washed out otherwise), the others plain AgX.
"""
import bpy, sys, os, math, time
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
VIEWS = argv[1].split(',')
ARM = argv[3] if len(argv) > 3 else 'Yoru'
SAMPLES = int(argv[4]) if len(argv) > 4 else 16
SCALE = int(argv[5]) if len(argv) > 5 else 100


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


FRAMES = parse_frames(argv[2])
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 600, 720
scene.render.resolution_percentage = SCALE
scene.eevee.taa_render_samples = SAMPLES
scene.render.image_settings.file_format = 'PNG'
sun = bpy.data.lights.new('sun_render', 'SUN')
sun.energy = 3.5
so = bpy.data.objects.new('sun_render', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(35))
world = bpy.data.worlds.new('w_render')
world.use_nodes = True
next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND').inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
scene.world = world
arm = bpy.data.objects[ARM]
keep = set([arm.name] + [c.name for c in arm.children] + ['Boden'])
for o in bpy.data.objects:
    if o.type in ('MESH', 'CURVE', 'FONT'):
        o.hide_render = (o.name not in keep) or o.name.startswith(('Icosphere', 'Label_'))
for lc in bpy.context.view_layer.layer_collection.children:          # collections hidden in the viewport still render; make sure
    pass                                                               # nothing of this Yoru sits in an excluded collection
fl = bpy.data.objects.get('Boden')
if fl:
    for v, c in zip(fl.data.vertices, ((-10, -10), (10, -10), (10, 10), (-10, 10))):
        v.co = (c[0], c[1], 0.0)
base = arm.matrix_world.translation.copy()


def cam(name, lens=None, ortho=None):
    d = bpy.data.cameras.new(name)
    if lens:
        d.type, d.lens = 'PERSP', lens
    else:
        d.type, d.ortho_scale = 'ORTHO', ortho
    d.clip_start, d.clip_end = 0.05, 60
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    return o


def look(o, eye, target):
    fwd = (target - eye).normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    o.matrix_world = Matrix((right, up, -fwd)).transposed().to_4x4()
    o.location = eye


a35 = math.radians(35.0)
tgt_body = base + Vector((0.0, -0.05, 0.80))
CAMS = {}
CAMS['front34'] = cam('front34', ortho=2.0); look(CAMS['front34'], base + Vector((6 * math.sin(a35), 6 * math.cos(a35), 1.3)), tgt_body)
tgt_head = base + Vector((0.0, -0.03, 1.36))
a20 = math.radians(20.0)
CAMS['head'] = cam('head', lens=85.0); look(CAMS['head'], tgt_head + Vector((math.sin(a20), math.cos(a20), 0.10)).normalized() * 1.6, tgt_head)
tgt_ears = base + Vector((0.0, -0.02, 1.47))
CAMS['ears'] = cam('ears', lens=85.0); look(CAMS['ears'], tgt_ears + Vector((0.0, 1.0, 0.12)).normalized() * 1.2, tgt_ears)   # both ears, from the front
tgt_tail = base + Vector((0.05, -0.12, 0.74))
a150 = math.radians(145.0)
CAMS['tail'] = cam('tail', lens=70.0); look(CAMS['tail'], tgt_tail + Vector((math.sin(a150), math.cos(a150), 0.05)).normalized() * 1.6, tgt_tail)
CAMS['game'] = cam('game', lens=72.0); look(CAMS['game'], base + Vector((0.35, -4.4, 1.75)), tgt_body)
os.makedirs(os.path.join(OUT, 'stills_r7'), exist_ok=True)
T0 = time.time()
n = 0
for f in FRAMES:
    scene.frame_set(f)
    for view in VIEWS:
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Medium High Contrast' if view in ('head', 'ears') else 'None'
        scene.camera = CAMS[view]
        scene.render.filepath = os.path.join(OUT, 'stills_r7', '%s_%03d.png' % (view, f))
        bpy.ops.render.render(write_still=True)
        n += 1
    if f % 30 == 0:
        print('rendered frame', f, '%.2f s per picture' % ((time.time() - T0) / max(n, 1)), flush=True)
print('STILLS DONE', n, 'pictures in %.0f s' % (time.time() - T0))
