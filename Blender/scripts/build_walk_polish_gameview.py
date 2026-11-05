"""
Yoru - WALK POLISH, round 2: game-like preview (saves nothing).  The walk is built in place; here the character moves forward through the
world by the ground motion of the gait, G(phase) of build_walk.py with the +-5 % wobble from the gait JSON, so planted feet stand still on
the floor.  Follow camera like the game's third-person camera: behind the character, 4.4 m from the pivot, pivot 1.35 m high, shoulder
offset 0.35 m to the right, 15 deg down, 60 deg vertical field of view (camera parented to the character's root).  World: 1 m checker floor,
posts every 3 m on both sides.
Background:
  blender -b --factory-startup <walk .blend> --python build_walk_polish_gameview.py -- <out dir> <gait json> [action=<name>] [seconds=4]
          [res=640x360] [samples=8] [frames=N] [crop=body|wide]
Writes <out dir>/g_000.png ... (one per frame at 30 fps).
Round 3: crop=body renders only a fixed window around arms and legs (taken from the joints over one cycle) at the full resolution given by
res (a real high-resolution close view from the game camera, not an enlargement); crop=wide is a larger window with the floor around her.
"""
import bpy, bmesh, sys, os, math, json, time
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, GAIT = argv[0], argv[1]
KV = dict(a.split('=', 1) for a in argv[2:] if '=' in a)
SEC = float(KV.get('seconds', 4.0))
RX, RY = (int(v) for v in KV.get('res', '640x360').split('x'))
os.makedirs(OUT, exist_ok=True)
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ad = arm.animation_data
if KV.get('action'):
    ad.action = bpy.data.actions[KV['action']]
    if getattr(ad, 'action_slot', None) is None and len(ad.action.slots):
        ad.action_slot = ad.action.slots[0]
act = ad.action
NF = int(round(act.frame_range[1] - act.frame_range[0]))


def fcurves_of(a):
    out = []
    try:
        out = list(a.fcurves)
    except Exception:
        pass
    if not out:
        for l in a.layers:
            for s in l.strips:
                for cb in s.channelbags:
                    out += list(cb.fcurves)
    return out


for fc in fcurves_of(act):                                           # endless walk
    if not any(m.type == 'CYCLES' for m in fc.modifiers):
        fc.modifiers.new('CYCLES')
g = json.load(open(GAIT))
VT = g['speed'] * NF / 30.0
A = g['speed_variation']['amplitude']
PH0 = g['speed_variation']['phase_of_max']
K4 = 4.0 * math.pi


def ground(t):
    """how far the ground has moved back under the in-place walk at frame t (m)"""
    n, r = divmod(t, NF)
    p = r / float(NF)
    return n * VT + VT * (p + A / K4 * (math.sin(K4 * (p - PH0)) + math.sin(K4 * PH0)))


# ---------------------------------------------------------------- world
for o in bpy.data.objects:
    if o.name.startswith(('Floor', 'Label_', 'Icosphere')):
        o.hide_render = True


def material(name, col_a, col_b=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = 0.8
    if col_b is None:
        bsdf.inputs['Base Color'].default_value = col_a
        return m
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ck = nt.nodes.new('ShaderNodeTexChecker')
    ck.inputs['Scale'].default_value = 1.0
    ck.inputs['Color1'].default_value = col_a
    ck.inputs['Color2'].default_value = col_b
    nt.links.new(tc.outputs['Object'], ck.inputs['Vector'])
    nt.links.new(ck.outputs['Color'], bsdf.inputs['Base Color'])
    return m


def mesh_object(name, build, mat):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def floor(bm):
    vs = [bm.verts.new(v) for v in ((-7, -10, 0), (7, -10, 0), (7, 130, 0), (-7, 130, 0))]
    bm.faces.new(vs)


def posts(bm):
    for x in (-2.2, 2.2):
        y = -6.0
        while y < 130:
            bmesh.ops.create_cube(bm, size=1.0, matrix=__import__('mathutils').Matrix.LocRotScale(Vector((x, y, 0.6)), None, Vector((0.12, 0.12, 1.2))))
            y += 3.0


mesh_object('game_floor', floor, material('game_floor', (0.34, 0.36, 0.40, 1), (0.22, 0.23, 0.26, 1)))
mesh_object('game_posts', posts, material('game_posts', (0.55, 0.45, 0.30, 1)))
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print('engine:', e)
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = RX, RY, 100
try:
    scene.eevee.taa_render_samples = int(KV.get('samples', 8))
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'
sun = bpy.data.lights.new('sun_game', 'SUN')
sun.energy = 3.5
so = bpy.data.objects.new('sun_game', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(35))
world = bpy.data.worlds.new('w_game')
world.use_nodes = True
next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND').inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
scene.world = world

# ---------------------------------------------------------------- game camera on the character's root
cd = bpy.data.cameras.new('game_cam')
cd.sensor_fit = 'VERTICAL'
cd.angle_y = math.radians(60.0)
cd.clip_end = 200
cam = bpy.data.objects.new('game_cam', cd)
scene.collection.objects.link(cam)
cam.parent = arm
pitch = math.radians(15.0)
cam.location = (0.35, -4.4 * math.cos(pitch), 1.35 + 4.4 * math.sin(pitch))
cam.rotation_euler = (math.radians(90.0) - pitch, 0.0, 0.0)
scene.camera = cam

T0 = time.time()
N = int(KV.get('frames', round(SEC * 30)))
y0 = arm.location.y
CROP = KV.get('crop')                                                # round 3: body = arms and legs, wide = body + floor around it
if CROP:
    from bpy_extras.object_utils import world_to_camera_view
    names = ['J_Bip_C_Neck', 'J_Bip_C_Hips'] + ['J_Bip_%s_%s' % (s, p) for s in 'LR' for p in
                                                ('UpperArm', 'LowerArm', 'Hand', 'Middle3', 'LowerLeg', 'Foot', 'ToeBase')]
    xs, ys = [], []
    for t in range(NF):
        scene.frame_set(t)
        arm.location.y = y0 + ground(t)
        bpy.context.view_layer.update()
        for n in names:
            pb = arm.pose.bones.get(n)
            if pb:
                p = world_to_camera_view(scene, cam, arm.matrix_world @ pb.head)
                xs.append(p.x)
                ys.append(p.y)
    cx, cy, w, h = 0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys)), max(xs) - min(xs), max(ys) - min(ys)
    w, h = (w * 1.6, h * 1.18) if CROP == 'body' else (w * 4.2, h * 1.7)
    r = scene.render
    r.use_border, r.use_crop_to_border = True, True
    r.border_min_x, r.border_max_x = max(0.0, cx - w / 2), min(1.0, cx + w / 2)
    r.border_min_y, r.border_max_y = max(0.0, cy - h / 2 - 0.02 * h), min(1.0, cy + h / 2)
    print('CROP', CROP, 'x %.3f..%.3f y %.3f..%.3f' % (r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y), flush=True)
for t in range(N):
    scene.frame_set(t)
    arm.location.y = y0 + ground(t)
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(OUT, 'g_%03d.png' % t)
    bpy.ops.render.render(write_still=True)
print('GAMEVIEW DONE', N, 'frames, NF', NF, 'stride %.3f m' % VT, 'in %.0f s' % (time.time() - T0), flush=True)
