"""
Yoru - AIM POSE r3, stage 1: still renders of Yoru_Aim_r3.blend (saves nothing).  The full actions Yoru_Aim_r3_full_Sa / _Sb from four fixed views
(the same framing for both): front (perspective, 50 mm lens on a 36 mm sensor, 11 deg from above, whole figure), side (orthographic from her right),
front34 (orthographic from her front right, 35 deg off the front), top (orthographic straight down, forward = up in the picture: pelvis, chest and
foot turn).  World and light as the sprint renders (1 m checker floor, sun 3.5, background 0.20 / 0.23 / 0.30, EEVEE).
  blender -b --factory-startup <Yoru_Aim_r3.blend> --python build_aim_r3_render.py -- <out dir> [setups=Sa,Sb] [views=front,side,front34,top]
          [res=1080x1350] [samples=32] [scale=1.0]
Writes <out dir>/<setup>/<view>.png
"""
import bpy, bmesh, sys, os, math, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
SETUPS = KV.get('setups', 'Sa,Sb').split(',')
VIEWS = KV.get('views', 'front,side,front34,top').split(',')
SCALE = float(KV.get('scale', 1.0))
RX, RY = (int(round(int(v) * SCALE)) for v in KV.get('res', '1080x1350').split('x'))
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ad = arm.animation_data
T0 = time.time()
for o in bpy.data.objects:
    if o.name.startswith(('Floor', 'Label_', 'Icosphere')):
        o.hide_render = True
m = bpy.data.materials.new('game_floor')
m.use_nodes = True
nt = m.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
bsdf.inputs['Roughness'].default_value = 0.8
tc, ck = nt.nodes.new('ShaderNodeTexCoord'), nt.nodes.new('ShaderNodeTexChecker')
ck.inputs['Scale'].default_value = 1.0
ck.inputs['Color1'].default_value = (0.34, 0.36, 0.40, 1)
ck.inputs['Color2'].default_value = (0.22, 0.23, 0.26, 1)
nt.links.new(tc.outputs['Object'], ck.inputs['Vector'])
nt.links.new(ck.outputs['Color'], bsdf.inputs['Base Color'])
me = bpy.data.meshes.new('game_floor')
bm = bmesh.new()
bm.faces.new([bm.verts.new(v) for v in ((-7, -12, 0), (7, -12, 0), (7, 40, 0), (-7, 40, 0))])
bm.to_mesh(me)
bm.free()
fl = bpy.data.objects.new('game_floor', me)
scene.collection.objects.link(fl)
fl.data.materials.append(m)
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print('engine:', e)
try:
    scene.eevee.taa_render_samples = int(KV.get('samples', 32))
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = RX, RY, 100
sun = bpy.data.lights.new('sun_game', 'SUN')
sun.energy = 3.5
so = bpy.data.objects.new('sun_game', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(35))
world = bpy.data.worlds.new('w_game')
world.use_nodes = True
next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND').inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
scene.world = world


def cam(name, loc, target, ortho=None, lens=None):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
        cd.sensor_width = 36.0
        cd.sensor_fit = 'AUTO'
    cd.clip_end = 60
    ob = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob


d11 = math.radians(11.0)
CAMS = {'front': cam('cam_front', (0.0, 0.03 + 2.75 * math.cos(d11), 0.84 + 2.75 * math.sin(d11)), (0.0, 0.03, 0.84), lens=50.0),
        'side': cam('cam_side', (6.0, -0.12, 0.82), (0.0, -0.12, 0.82), ortho=1.9),
        'front34': cam('cam_front34', (6.0 * math.sin(math.radians(35)), 6.0 * math.cos(math.radians(35)), 1.3), (0.0, 0.05, 0.82), ortho=1.9),
        'top': cam('cam_top', (-0.02, -0.18, 6.0), (-0.02, -0.18, 0.0), ortho=1.4)}
CAMS['top'].rotation_euler = (0.0, 0.0, 0.0)                         # straight down, forward (+Y) up in the picture
done = 0
for sk in SETUPS:
    act = bpy.data.actions['Yoru_Aim_r3_full_' + sk]
    ad.action = act
    if hasattr(ad, 'action_slot') and ad.action_slot is None and len(act.slots):
        ad.action_slot = act.slots[0]
    scene.frame_set(1)
    scene.frame_set(0)
    for vw in VIEWS:
        scene.camera = CAMS[vw]
        p = os.path.join(OUT, sk, vw + '.png')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        done += 1
print('RENDER DONE', done, 'stills in %.0f s' % (time.time() - T0), flush=True)
