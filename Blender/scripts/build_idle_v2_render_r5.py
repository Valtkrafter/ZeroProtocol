"""Idle v2, round 5: renders the frames of the FINAL idle file (one Yoru called 'Yoru' at the origin) for the closing video.
usage: blender -b --factory-startup <Blender/Yoru_Idle_v2.blend> --python build_idle_v2_render_r5.py -- <out dir> <views, e.g. front34,side,game,face> <frames> [samples]
       frames: '0' or '0,24,48' or '0-359' (inclusive)
Writes <out dir>/stills_final/<view>_<frame:03d>.png (600 x 720).  EEVEE, a sun and the dark world of render_walk_stills.py, floor +-10 m.
Views: front34, side, game as in build_idle_v2_render_r2.py; face = close-up of the face with an 85 mm lens from the front (the camera stands
still, the head moves only millimetres), rendered with the colour look 'AgX - Medium High Contrast' like the face sheet of round 4 (the pale
face reads washed out with the plain AgX).  The icosphere of the glTF import is never rendered.
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
scene.frame_set(0)
head0 = arm.matrix_world @ arm.pose.bones['J_Bip_C_Head'].head
face_target = head0 + Vector((0.0, 0.035, 0.065))


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


tgt = base + Vector((0.0, -0.05, 0.80))
a35 = math.radians(35.0)
CAMS = {}
CAMS['front34'] = cam('front34', ortho=2.0); look(CAMS['front34'], base + Vector((6 * math.sin(a35), 6 * math.cos(a35), 1.3)), tgt)
CAMS['side'] = cam('side', ortho=2.0); look(CAMS['side'], base + Vector((6.0, -0.05, 0.8)), tgt)
CAMS['game'] = cam('game', lens=72.0); look(CAMS['game'], base + Vector((0.35, -4.4, 1.75)), tgt)
CAMS['face'] = cam('face', lens=85.0); look(CAMS['face'], face_target + Vector((0.0, 0.85, 0.0)), face_target)
os.makedirs(os.path.join(OUT, 'stills_final'), exist_ok=True)
T0 = time.time()
n = 0
for f in FRAMES:
    scene.frame_set(f)
    for view in VIEWS:
        scene.view_settings.look = 'AgX - Medium High Contrast' if view == 'face' else 'None'
        scene.camera = CAMS[view]
        scene.render.filepath = os.path.join(OUT, 'stills_final', '%s_%03d.png' % (view, f))
        bpy.ops.render.render(write_still=True)
        n += 1
    if f % 30 == 0:
        print('rendered frame', f, '%.2f s per picture' % ((time.time() - T0) / max(n, 1)), flush=True)
print('STILLS DONE', n, 'pictures in %.0f s' % (time.time() - T0))
