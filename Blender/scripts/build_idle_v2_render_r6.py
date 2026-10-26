"""Idle v2, round 6: renders the frames of a FINAL idle file (one Yoru called 'Yoru' at the origin) for the arm video.
usage: blender -b --factory-startup <Blender/Yoru_Idle_v2.blend> --python build_idle_v2_render_r6.py -- <out dir> <views> <frames> [samples]
       views: front34 (whole body, orthographic 2 m), arms34 (arms close-up from the front right, hip to shoulder, 1.1 m away, 40 mm),
              armside (arms close-up from her right side, 1.1 m away, 40 mm), game (shoulder camera of the game)
       frames: '0' or '0,24' or '0-359'
Writes <out dir>/stills_r6/<view>_<frame:03d>.png (600 x 720).  EEVEE, sun, dark world, floor +-10 m, the icosphere never rendered.
"""
import bpy, sys, os, math, time
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
VIEWS = argv[1].split(',')
SAMPLES = int(argv[3]) if len(argv) > 3 else 16


def parse_frames(s):
    out = []
    for part in s.split(','):
        if '-' in part:
            a, b = part.split('-')
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


FRAMES = parse_frames(argv[2])
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 600, 720
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = SAMPLES
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.look = 'None'
sun = bpy.data.lights.new('sun_render', 'SUN')
sun.energy = 3.5
so = bpy.data.objects.new('sun_render', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(35))
world = bpy.data.worlds.new('w_render')
world.use_nodes = True
next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND').inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
scene.world = world
for o in bpy.data.objects:
    if o.name.startswith(('Label_', 'Icosphere')):
        o.hide_render = True
fl = bpy.data.objects.get('Boden')
if fl:
    for v, c in zip(fl.data.vertices, ((-10, -10), (10, -10), (10, 10), (-10, 10))):
        v.co = (c[0], c[1], 0.0)
arm = bpy.data.objects['Yoru']
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


a35, a25 = math.radians(35.0), math.radians(25.0)
tgt_body = base + Vector((0.0, -0.05, 0.80))
tgt_arms = base + Vector((0.02, 0.0, 0.97))
CAMS = {}
CAMS['front34'] = cam('front34', ortho=2.0); look(CAMS['front34'], base + Vector((6 * math.sin(a35), 6 * math.cos(a35), 1.3)), tgt_body)
# (50 mm from 1.0 m cut the hands off at the bottom edge)
CAMS['arms34'] = cam('arms34', lens=40.0); look(CAMS['arms34'], tgt_arms + Vector((math.sin(a25), math.cos(a25), 0.12)).normalized() * 1.1, tgt_arms)
CAMS['armside'] = cam('armside', lens=40.0); look(CAMS['armside'], tgt_arms + Vector((1.0, 0.0, 0.10)).normalized() * 1.1, tgt_arms)
CAMS['game'] = cam('game', lens=72.0); look(CAMS['game'], base + Vector((0.35, -4.4, 1.75)), tgt_body)
os.makedirs(os.path.join(OUT, 'stills_r6'), exist_ok=True)
T0 = time.time()
n = 0
for f in FRAMES:
    scene.frame_set(f)
    for view in VIEWS:
        scene.camera = CAMS[view]
        scene.render.filepath = os.path.join(OUT, 'stills_r6', '%s_%03d.png' % (view, f))
        bpy.ops.render.render(write_still=True)
        n += 1
    if f % 30 == 0:
        print('rendered frame', f, '%.2f s per picture' % ((time.time() - T0) / max(n, 1)), flush=True)
print('STILLS DONE', n, 'pictures in %.0f s' % (time.time() - T0))
