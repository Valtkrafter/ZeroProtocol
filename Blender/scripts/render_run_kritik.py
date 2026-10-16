"""Renders stills of the slides of Yoru_Run_Kritik_Stufe1.blend (made by build_run_kritik.py), two passes per picture:
  A_<slide>_<frame>.png  the character on a dark world (EEVEE),   B_<slide>_<frame>.png  only the overlay + text on a transparent background.
composite_run_kritik.py puts B over A (the overlay is drawn "in front" of the body, like the 3D view does with "In Front").
usage: blender -b --factory-startup <Yoru_Run_Kritik_Stufe1.blend> --python render_run_kritik.py -- <out dir> [slide:frame,slide:frame,...]
slide = index 0 .. 8 of the slide list (the default is one telling frame per slide)."""
import bpy, json, math, os, sys

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
slides = json.loads(scene['kritik'])
DEFAULT = {0: 18, 1: 18, 2: 24, 3: 8, 4: 18, 5: 18, 6: 9, 7: 9, 8: 18}
jobs = []
if len(argv) > 1:
    for tok in argv[1].split(','):
        a, b = tok.split(':')
        jobs.append((int(a), int(b)))
else:
    jobs = sorted(DEFAULT.items())

CHAR = [o for o in bpy.data.objects if o.name in ('Body', 'Face', 'Hair', 'Floor_scrolling')]
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Icosphere'):
        o.hide_render = True
scene.render.engine = 'BLENDER_EEVEE'
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'
sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 3.5
so = bpy.data.objects.new('sun', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(35))
if scene.world is None:                                  # the copy made by build_run_kritik.py has its own dark world
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.045, 0.047, 0.055, 1.0)
    scene.world = world

for idx, f in jobs:
    sd = slides[idx]
    scene.camera = bpy.data.objects[sd['camera']]
    scene.frame_set(f)
    tag = '%s_%03d' % (sd['name'], f)
    # pass A: the character without the overlay
    for s2 in slides:
        bpy.data.collections[s2['name']].hide_render = True
    for o in CHAR:
        o.hide_render = False
    if not sd.get('floor', True):
        bpy.data.objects['Floor_scrolling'].hide_render = True
    so.hide_render = False
    scene.render.film_transparent = False
    scene.render.filepath = os.path.join(OUT, 'A_%s.png' % tag)
    bpy.ops.render.render(write_still=True)
    # pass B: the overlay alone
    for s2 in slides:
        bpy.data.collections[s2['name']].hide_render = (s2['name'] != sd['name'])
    for o in CHAR:
        o.hide_render = True
    so.hide_render = True
    scene.render.film_transparent = True
    scene.render.filepath = os.path.join(OUT, 'B_%s.png' % tag)
    bpy.ops.render.render(write_still=True)
print('KRITIK STILLS DONE')
