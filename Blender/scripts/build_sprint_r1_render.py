"""
Yoru - NEW SPRINT, round 1: preview renders (saves nothing).  60 fps actions (36 frames per cycle).
Background:
  blender -b --factory-startup <.blend> --python build_sprint_r1_render.py -- <out dir> <gait json> view=<game|front|side|back>
          [action=<name>] [frames=0-107 | frames=0,3,6] [res=WxH] [crop=body|wide] [samples=8]
view=game : the game's follow camera (behind her, 0.35 m right of the pivot, pivot 1.35 m high, 4.75 m away = 4.4 m + 0.35 m while sprinting,
            15 deg down, vertical field of view 66 deg = 60 + 6 while sprinting), parented to the armature, which moves through the world with the
            ground motion of the gait JSON (stance_dip model: the ground slows down while a foot is on the ground, steady in the flight), so the
            planted feet stand on the floor.  crop=body renders only a fixed window around the arms, pistols and upper body (joints and muzzles over
            one cycle) at the full resolution given by res; crop=wide a larger window with the floor around her.
view=front: close-up from the front, in place.  view=side: orthographic from her right, in place.  view=back: orthographic from behind, in place.
World: 1 m checker floor, posts every 3 m on both sides.  Writes <out dir>/<view>_<frame:03d>.png.
"""
import bpy, bmesh, sys, os, math, json, time
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, GAIT = argv[0], argv[1]
KV = dict(a.split('=', 1) for a in argv[2:] if '=' in a)
VIEW = KV.get('view', 'game')
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


for fc in fcurves_of(act):                                           # endless cycle
    if not any(m.type == 'CYCLES' for m in fc.modifiers):
        fc.modifiers.new('CYCLES')
g = json.load(open(GAIT))
FPS = 60.0
VT = g['speed'] * NF / FPS                                            # stride (m)
sv = g['speed_variation']
A_ = sv['amplitude']
B_ = sv['stance_share']


def dip_integral(phi):
    k = int(math.floor(phi / 0.5 + 1e-12))
    q = phi - 0.5 * k
    if q < B_:
        return k * (2.0 * B_ / math.pi) + (B_ / math.pi) * (1.0 - math.cos(math.pi * q / B_))
    return (k + 1) * (2.0 * B_ / math.pi)


def ground(t):
    """how far the ground has moved back under the in-place sprint at frame t (m): G of build_run.py / build_sprint_r1.py"""
    n, r = divmod(t, NF)
    phi = r / float(NF)
    return n * VT + VT * (phi * (1.0 + A_ * 4.0 * B_ / math.pi) - A_ * dip_integral(phi))


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
    vs = [bm.verts.new(v) for v in ((-7, -12, 0), (7, -12, 0), (7, 140, 0), (-7, 140, 0))]
    bm.faces.new(vs)


def posts(bm):
    for x in (-2.2, 2.2):
        y = -6.0
        while y < 140:
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.LocRotScale(Vector((x, y, 0.6)), None, Vector((0.12, 0.12, 1.2))))
            y += 3.0


mesh_object('game_floor', floor, material('game_floor', (0.34, 0.36, 0.40, 1), (0.22, 0.23, 0.26, 1)))
if VIEW == 'game':
    mesh_object('game_posts', posts, material('game_posts', (0.55, 0.45, 0.30, 1)))
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print('engine:', e)
RX, RY = (int(v) for v in KV.get('res', '640x360').split('x'))
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

# ---------------------------------------------------------------- cameras
cd = bpy.data.cameras.new('cam')
cd.clip_end = 300
cam = bpy.data.objects.new('cam', cd)
scene.collection.objects.link(cam)
scene.camera = cam
if VIEW == 'game':
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(66.0)
    cam.parent = arm
    pitch = math.radians(15.0)
    dist = 4.75
    cam.location = (0.35, -dist * math.cos(pitch), 1.35 + dist * math.sin(pitch))
    cam.rotation_euler = (math.radians(90.0) - pitch, 0.0, 0.0)
elif VIEW == 'front':
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(26.0)
    cam.location = (0.0, 3.2, 1.0)
    cam.rotation_euler = (math.radians(90.0), 0.0, math.radians(180.0))
elif VIEW == 'hand':                                                 # close-up of one hand with its pistol (side=R|L), the camera follows the hand
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(30.0)
    cd.clip_start = 0.02
else:
    cd.type = 'ORTHO'
    cd.ortho_scale = 1.95
    if VIEW == 'side':                                               # from her right side (+X), looking at -X
        cam.location = (6.0, 0.12, 0.88)
        cam.rotation_euler = (math.radians(90.0), 0.0, math.radians(90.0))
    else:                                                            # back: from behind (-Y), looking forward
        cam.location = (0.0, -6.0, 0.88)
        cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)

# ---------------------------------------------------------------- frames
fr = KV.get('frames', '0-%d' % (NF - 1))
if '-' in fr:
    a_, b_ = fr.split('-')
    FRAMES = list(range(int(a_), int(b_) + 1))
else:
    FRAMES = [int(x) for x in fr.split(',')]
y0 = arm.location.y
moving = VIEW == 'game'
CROP = KV.get('crop') if VIEW == 'game' else None
if CROP:
    from bpy_extras.object_utils import world_to_camera_view
    names = ['J_Bip_C_Neck', 'J_Bip_C_Head', 'J_Bip_C_Hips'] + ['J_Bip_%s_%s' % (s, p) for s in 'LR' for p in ('Shoulder', 'UpperArm', 'LowerArm', 'Hand', 'Middle3')]
    if CROP == 'wide':
        names += ['J_Bip_%s_%s' % (s, p) for s in 'LR' for p in ('LowerLeg', 'Foot', 'ToeBase')]
    pist = [o for o in bpy.data.objects if o.name.startswith('PLATZHALTER_Pistole')]
    xs, ys = [], []
    for t in range(NF):
        scene.frame_set(t)
        arm.location.y = y0 + ground(t)
        bpy.context.view_layer.update()
        pts = [arm.matrix_world @ arm.pose.bones[n].head for n in names if arm.pose.bones.get(n)]
        for o in pist:
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        for q in pts:
            p = world_to_camera_view(scene, cam, q)
            xs.append(p.x)
            ys.append(p.y)
    cx, cy, w, h = 0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys)), max(xs) - min(xs), max(ys) - min(ys)
    w, h = (w * 1.35, h * 1.22) if CROP == 'body' else (w * 3.2, h * 1.35)
    r = scene.render
    r.use_border, r.use_crop_to_border = True, True
    r.border_min_x, r.border_max_x = max(0.0, cx - w / 2), min(1.0, cx + w / 2)
    r.border_min_y, r.border_max_y = max(0.0, cy - h / 2), min(1.0, cy + h / 2)
    print('CROP', CROP, 'x %.3f..%.3f y %.3f..%.3f' % (r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y), flush=True)
T0 = time.time()
for t in FRAMES:
    scene.frame_set(t)
    arm.location.y = y0 + (ground(t) if moving else 0.0)
    bpy.context.view_layer.update()
    if VIEW == 'hand':
        sd = KV.get('side', 'R')
        hb = arm.pose.bones['J_Bip_%s_Hand' % sd]
        tgt = arm.matrix_world @ hb.head
        off = Vector([float(v) for v in KV.get('off', '0.34,0.30,0.06').split(',')])
        if sd == 'L':
            off.x = -off.x
        cam.location = tgt + off
        cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(OUT, '%s_%03d.png' % (VIEW, t))
    bpy.ops.render.render(write_still=True)
print('RENDER DONE', VIEW, len(FRAMES), 'frames, NF', NF, 'stride %.3f m' % VT, 'in %.0f s' % (time.time() - T0), flush=True)
