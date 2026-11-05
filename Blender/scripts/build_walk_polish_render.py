"""
Yoru - WALK POLISH: renders still frames of one walk file (the old Yoru_Walk.blend or a polish copy) for the before / after video and the
contact sheet.  Render setup taken over from build_walk_v2_render_r4.py (EEVEE, a sun, the dark world of the idle renders, same cameras).
usage:
  blender -b --factory-startup <blend> --python build_walk_polish_render.py -- <out dir> <views> <frames> [scale %, default 70] [samples, 16]
  views: comma separated of  game, close34, closeSide, front34, side, back, armR
  frames: '0-20' or '0,5,10' (inclusive ranges allowed)
Writes <out dir>/<view>_<frame:03d>.png (600 x 720 at scale %).
Views: game = the shoulder camera of the game (4.4 m behind, 0.35 m to the right, 72 mm);  close34 = 85 mm close-up from the front right
(40 deg) from the feet to the shoulders;  closeSide = 85 mm close-up from her right, feet to shoulders;  front34 / side / back = ortho full body;
armR = 85 mm close-up of the right elbow and hand.
Round 2 additions: closeFront = 85 mm straight from the front, hips to shoulders (shows the arms' in / out path); an optional argument
action=<name> anywhere after '--' renders that action instead of the assigned one.
"""
import bpy, sys, os, math, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
ACT = next((a.split('=', 1)[1] for a in argv if a.startswith('action=')), None)
argv = [a for a in argv if not a.startswith('action=')]
if ACT:
    _arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    _arm.animation_data.action = bpy.data.actions[ACT]
    if getattr(_arm.animation_data, 'action_slot', None) is None and len(_arm.animation_data.action.slots):
        _arm.animation_data.action_slot = _arm.animation_data.action.slots[0]
OUT = argv[0]
VIEWS = argv[1].split(',')
FRS = argv[2]
SCALE = int(argv[3]) if len(argv) > 3 else 70
SAMPLES = int(argv[4]) if len(argv) > 4 else 16
os.makedirs(OUT, exist_ok=True)
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


S40, C40 = math.sin(math.radians(40)), math.cos(math.radians(40))
CAMS = {
    'game': cam('game', (0.35, -4.4, 1.75), lens=72.0),
    'close34': cam('close34', (3.4 * S40, 3.4 * C40, 0.95), lens=85.0, tgt=(0.0, 0.0, 0.66)),
    'closeSide': cam('closeSide', (3.4, 0.02, 0.85), lens=85.0, tgt=(0.0, 0.02, 0.66)),
    'front34': cam('front34', (6.0 * math.sin(math.radians(35)), 6.0 * math.cos(math.radians(35)), 1.3)),
    'side': cam('side', (6.0, -0.05, 0.8)),
    'back': cam('back', (0.0, -6.0, 0.8)),
    'armR': cam('armR', (1.45, 1.05, 1.05), lens=85.0, tgt=(0.13, 0.02, 0.93)),
    'closeFront': cam('closeFront', (0.0, 2.6, 0.98), lens=85.0, tgt=(0.0, 0.0, 0.95)),
}


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
for f in parse_frames(FRS):
    scene.frame_set(f)
    for view in VIEWS:
        o, rel, tgt = CAMS[view]
        target.location = tgt
        o.location = rel
        scene.camera = o
        scene.render.filepath = os.path.join(OUT, '%s_%03d.png' % (view, f))
        bpy.ops.render.render(write_still=True)
        n += 1
print('STILLS DONE', n, 'pictures in %.0f s' % (time.time() - T0), flush=True)
