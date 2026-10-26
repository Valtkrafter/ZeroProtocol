"""Renders the idle v2 stand candidates (one Yoru per collection A_Kontrapost / B_Catwalk / C_Kompakt, standing side by side) as stills.
usage: blender -b <copy of the stage .blend> --python build_idle_v2_render.py -- <out dir> [variants, default A,B,C] [views, default front34,side,back]
Writes <out dir>/stills_<V>/<view>_000.png (600 x 720, the layout of render_walk_stills.py / aim_sheet.py).
Only the variant that is rendered is visible; the cameras look at its armature.  EEVEE (the only engine that honours the alpha cut of the
"Onepiece" material), a sun and the dark world of render_walk_stills.py so the pale tail and hair show.
Views: front34 = front right (35 deg), side = from her right, back = from behind, back34 = behind right (30 deg),
       game = like the shoulder camera of the game (perspective, 4.4 m behind her, 0.35 m to the right, above her, ThirdPersonCamera.cs).
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KEYS = argv[1].split(',') if len(argv) > 1 else ['A', 'B', 'C']
VIEWS = argv[2].split(',') if len(argv) > 2 else ['front34', 'side', 'back']
COLL = {'A': 'A_Kontrapost', 'B': 'B_Catwalk', 'C': 'C_Kompakt'}
scene = bpy.context.scene

try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print('engine:', e)
scene.render.resolution_x, scene.render.resolution_y = 600, 720
scene.render.resolution_percentage = 100
try:
    scene.eevee.taa_render_samples = 16
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
    if o.name.startswith('Label_'):
        o.hide_render = True

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
for k in KEYS:
    for kk, objs in coll_objs.items():
        for o in objs:
            if o.type == 'MESH' and o.name.startswith('Icosphere'):
                continue
            o.hide_render = (kk != k)
    armo = next(o for o in coll_objs[k] if o.type == 'ARMATURE')
    base = armo.matrix_world.translation.copy()
    target.location = base + Vector((0.0, -0.05, 0.80))
    os.makedirs(os.path.join(OUT, 'stills_%s' % k), exist_ok=True)
    for view in VIEWS:
        o, rel = CAMS[view]
        o.location = base + rel
        scene.camera = o
        scene.render.filepath = os.path.join(OUT, 'stills_%s' % k, '%s_000.png' % view)
        bpy.ops.render.render(write_still=True)
        print('rendered', k, view, flush=True)
print('STILLS DONE')
