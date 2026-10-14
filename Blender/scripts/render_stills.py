"""Renders a few still frames of Yoru_Idle.blend (side view and back view) for a quick look at the tail.
usage: blender -b --factory-startup <Yoru_Idle.blend> --python render_stills.py -- <out dir> <frames, comma separated>
"""
import bpy, sys, os, math

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
FRAMES = [int(x) for x in argv[1].split(',')]
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene

for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Icosphere'):
        o.hide_render = True

# floor
import numpy as np
n = 1024
img = bpy.data.images.new('floor_grid', n, n)
a = np.zeros((n, n, 4), dtype=np.float32)
a[..., :3] = (0.55, 0.58, 0.62)
a[..., 3] = 1.0
step = n // 16
for k in range(0, n, step):
    a[k:k + 2, :, :3] = (0.25, 0.27, 0.30)
    a[:, k:k + 2, :3] = (0.25, 0.27, 0.30)
img.pixels.foreach_set(a.ravel())
mat = bpy.data.materials.new('floor')
mat.use_nodes = True
bsdf = next(nd for nd in mat.node_tree.nodes if nd.type == 'BSDF_PRINCIPLED')
tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
tex.image = img
mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0, 0, 0))
bpy.context.active_object.data.materials.append(mat)

ENGINE = argv[2] if len(argv) > 2 else 'BLENDER_EEVEE'
scene.render.engine = ENGINE
scene.render.resolution_x, scene.render.resolution_y = 540, 720
if ENGINE == 'CYCLES':
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
else:
    try:
        scene.eevee.taa_render_samples = 24
    except Exception:
        pass
sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 3.5
so = bpy.data.objects.new('sun', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(35))
world = bpy.data.worlds.new('w')
world.use_nodes = True
bgn = next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND')
bgn.inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
bgn.inputs['Strength'].default_value = 1.0
scene.world = world
scene.render.image_settings.file_format = 'PNG'

target = bpy.data.objects.new('target', None)
target.location = (0, -0.12, 0.72)
scene.collection.objects.link(target)


def cam(name, loc, scale):
    d = bpy.data.cameras.new(name)
    d.type = 'ORTHO'
    d.ortho_scale = scale
    d.clip_end = 60
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    c = o.constraints.new('TRACK_TO')
    c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return o


cams = {'side': cam('side', (6.0, -0.12, 0.8), 1.25), 'back': cam('back', (0.0, -6.0, 0.8), 1.25)}
for f in FRAMES:
    scene.frame_set(f)
    for key, c in cams.items():
        scene.camera = c
        scene.render.filepath = os.path.join(OUT, '%s_%03d.png' % (key, f))
        bpy.ops.render.render(write_still=True)
print('STILLS DONE')
