"""Renders still frames of Yoru_Walk.blend (EEVEE, dark world so the pale tail shows) from several views.
usage: blender -b <Yoru_Walk.blend> --python render_walk_stills.py -- <out dir> <frames, comma separated> [views, comma separated: side,back,front,three]
The floor in the file (Floor_scrolling) moves backwards at the walk speed, so a planted foot stays on its checker cell.
"""
import bpy, sys, os, math

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
FRAMES = [int(x) for x in argv[1].split(',')]
VIEWS = argv[2].split(',') if len(argv) > 2 else ['side', 'back']
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene

for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Icosphere'):
        o.hide_render = True

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 600, 720
try:
    scene.eevee.taa_render_samples = 16
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
scene.world = world
scene.render.image_settings.file_format = 'PNG'

target = bpy.data.objects.new('target', None)
target.location = (0, -0.05, 0.80)
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


# 'feet': looks from the right and above at the shoes on the moving floor (a planted shoe must stay on its checker cell)
target_feet = bpy.data.objects.new('target_feet', None)
target_feet.location = (0.0, 0.0, 0.05)
scene.collection.objects.link(target_feet)
feet = cam('feet', (3.0, 0.0, 2.2), 1.1)
feet.constraints[0].target = target_feet
target_chest = bpy.data.objects.new('target_chest', None)
target_chest.location = (0.0, 0.03, 1.22)
scene.collection.objects.link(target_chest)
chest_side = cam('chest_side', (6.0, 0.03, 1.22), 0.55)
chest_side.constraints[0].target = target_chest
chest_front = cam('chest_front', (0.0, 6.0, 1.22), 0.55)
chest_front.constraints[0].target = target_chest
# 'top': straight down, forward is up in the picture (shows the hip and shoulder rotation, the arm swing and the foot placement)
top = bpy.data.objects.new('top', bpy.data.cameras.new('top'))
top.data.type = 'ORTHO'
top.data.ortho_scale = 1.9
top.data.clip_end = 60
top.location = (0.0, -0.02, 6.0)
top.rotation_euler = (0.0, 0.0, 0.0)
scene.collection.objects.link(top)
# 'hand': follows her right hand from the outside (fingers, thumb, wrist)
hand = bpy.data.objects.new('hand', bpy.data.cameras.new('hand'))
hand.data.type = 'ORTHO'
hand.data.ortho_scale = 0.40
hand.data.clip_end = 60
hand.rotation_euler = (math.radians(90), 0.0, math.radians(90))        # looks along -X
scene.collection.objects.link(hand)
target_wide = bpy.data.objects.new('target_wide', None)
target_wide.location = (0.0, -0.30, 0.80)
scene.collection.objects.link(target_wide)
side_wide = cam('side_wide', (6.0, -0.30, 0.80), 2.5)
side_wide.constraints[0].target = target_wide
cams = {'side_wide': side_wide, 'top': top, 'hand': hand, 'feet': feet, 'chest_side': chest_side, 'chest_front': chest_front,
        'side': cam('side', (6.0, -0.05, 0.8), 2.0),
        'back': cam('back', (0.0, -6.0, 0.8), 2.0),
        'front': cam('front', (0.0, 6.0, 0.8), 2.0),
        'three': cam('three', (6.0 * math.sin(math.radians(145)), 6.0 * math.cos(math.radians(145)), 1.6), 2.0)}
arm_obj = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for f in FRAMES:
    scene.frame_set(f)
    for key in VIEWS:
        scene.camera = cams[key]
        if key == 'hand':
            hp = arm_obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones['J_Bip_R_Hand'].head
            hand.location = (hp.x + 3.0, hp.y, hp.z - 0.03)
        scene.render.filepath = os.path.join(OUT, '%s_%03d.png' % (key, f))
        bpy.ops.render.render(write_still=True)
print('STILLS DONE')
