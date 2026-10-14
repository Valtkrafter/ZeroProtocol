"""Close-ups of Yoru's face from Yoru_Walk.blend with the shape key of the blink set to given weights (or to the keyed animation).
usage: blender -b --factory-startup <Yoru_Walk.blend> --python render_blink_stills.py -- <out dir ABSOLUTE> <weights|frames> [views] [frame] [mode]
  weights : comma list, e.g. 0,0.25,0.5,0.75,1   (mode 'w', default: the shape key Fcl_EYE_Close is set by hand, pose of <frame>)
  frames  : comma list of frames (mode 'f': the keyed blink animation + the walk pose of that frame is rendered)
  views   : comma list of eyes, face, eyes_side, eyes_three, face_three, eyes_lr  (default eyes)
file names: <view>_<index 000>.png (index = position in the list)
"""
import bpy, sys, os, math
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
LIST = [float(x) for x in argv[1].split(',')]
VIEWS = argv[2].split(',') if len(argv) > 2 else ['eyes']
FRAME = int(argv[3]) if len(argv) > 3 else 0
MODE = argv[4] if len(argv) > 4 else 'w'
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene

for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Icosphere'):
        o.hide_render = True
    if o.name == 'Floor_scrolling':
        o.hide_render = True

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 800, 600
try:
    scene.eevee.taa_render_samples = 24
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'
try:
    scene.view_settings.view_transform = 'Standard'            # AgX washes the pale face out
    scene.view_settings.look = 'None'
except Exception as e:
    print('view transform:', str(e)[:120])
# soft light from the front (the walk stills are lit from behind): key from the front right above, fill from the left, a bright world
key = bpy.data.lights.new('key', 'SUN')
key.energy = 2.2
ko = bpy.data.objects.new('key', key)
scene.collection.objects.link(ko)
ko.rotation_euler = (math.radians(58), 0, math.radians(205))
fill = bpy.data.lights.new('fill', 'SUN')
fill.energy = 0.7
fo = bpy.data.objects.new('fill', fill)
scene.collection.objects.link(fo)
fo.rotation_euler = (math.radians(75), 0, math.radians(125))
world = bpy.data.worlds.new('w')
world.use_nodes = True
bgn = next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND')
bgn.inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
scene.world = world

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
face = bpy.data.objects['Face']
sk = face.data.shape_keys
close = sk.key_blocks['Fcl_EYE_Close']
if MODE == 'w' and sk.animation_data:
    sk.animation_data.action = None                           # the weight is set by hand, the blink track must not overwrite it


def eye_center():
    pb = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
    l, r = pb['J_Adj_L_FaceEye'].head, pb['J_Adj_R_FaceEye'].head
    return (l + r) * 0.5, l, r


def make_cam(name, ortho_scale=None, lens=None):
    d = bpy.data.cameras.new(name)
    if ortho_scale:
        d.type = 'ORTHO'
        d.ortho_scale = ortho_scale
    else:
        d.lens = lens
    d.clip_start = 0.01
    d.clip_end = 20
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    tgt = bpy.data.objects.new(name + '_t', None)
    scene.collection.objects.link(tgt)
    c = o.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return o, tgt


cams = {}
for name, kw in (('eyes', dict(ortho_scale=0.21)), ('face', dict(ortho_scale=0.40)), ('eyes_side', dict(ortho_scale=0.21)),
                 ('eyes_three', dict(ortho_scale=0.21)), ('face_three', dict(ortho_scale=0.34)), ('eyes_lr', dict(ortho_scale=0.13))):
    cams[name] = make_cam(name, **kw)


def place(frame):
    scene.frame_set(frame)
    c, l, r = eye_center()
    for name, (co, tg) in cams.items():
        tg.location = c
        if name.startswith('eyes_side'):
            co.location = c + Vector((3.0, 0.0, 0.0))
        elif name.endswith('_three'):
            co.location = c + Vector((3.0 * math.sin(math.radians(35)), 3.0 * math.cos(math.radians(35)), 0.35))
        elif name == 'eyes_lr':
            tg.location = r
            co.location = r + Vector((0.0, 3.0, 0.0))
        else:
            co.location = c + Vector((0.0, 3.0, 0.0))
        if name == 'face':
            tg.location = c + Vector((0.0, 0.0, 0.055))
            co.location = tg.location + Vector((0.0, 3.0, 0.0))


for i, v in enumerate(LIST):
    if MODE == 'w':
        place(FRAME)
        close.value = v
    else:
        place(int(v))
    bpy.context.view_layer.update()
    for view in VIEWS:
        scene.camera = cams[view][0]
        name = '%s_%03d.png' % (view, i) if MODE == 'w' else '%s_f%03d.png' % (view, int(v))
        scene.render.filepath = os.path.join(OUT, name)
        bpy.ops.render.render(write_still=True)
print('BLINK STILLS DONE', len(LIST) * len(VIEWS))
