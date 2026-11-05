"""
Yoru - AIM POSE r4: still renders of Yoru_Aim_r4.blend (saves nothing; a copy of build_aim_r3b_render.py, which stays untouched).
Views here: front, side, front34 as round 2, ots = the game camera 0.25 m further right (0.60 m right of the pivot, pivot 1.35 m, 4.4 m behind,
15 deg down, vertical FOV 60, whole figure crop like game), game_body = the real game camera (0.35 m right) on head to hips.  Variants A1, A2.  A copy of build_aim_r1_render.py (stays untouched) for round 2:
the pictures use the FULL actions (Yoru_Aim_r2_<V>_full = upper body + its own stance, so A shows its right foot in front), the game cameras stand
over the middle between the ankles (as aim_measure.py), and there is a new view 'front'.  One COMMON crop window per view for A, B and C.
  game       the real game camera, static: pivot 1.35 m above the middle of the feet, camera 4.4 m behind the pivot, 0.35 m to the right, 15 deg down,
             vertical field of view 60 deg; border crop around the whole figure
  game_body  the same camera, border crop on head to hips, arms and pistols
  ads        the aim camera (values of ThirdPersonCamera.cs): pivot 1.30 m, 2.4 m behind, 0.58 m right, 15 deg down, vertical FOV 42 deg, full frame
  front      perspective from straight in front, 50 mm lens (36 mm sensor), looking 11 deg down onto her, whole figure (to lay beside the Tomb Raider
             viewer picture Blender/previews/ref_aim/TR_viewer_AimLevel_x3.png)
  front34    orthographic from her front right (35 deg off the front), side: orthographic from her right
World and light as the sprint renders (1 m checker floor, posts every 3 m in the game views, sun 3.5, background 0.20 / 0.23 / 0.30, EEVEE).
Background:
  blender -b --factory-startup <Yoru_Aim_r2.blend> --python build_aim_r2_render.py -- <out dir> [variants=A,B,C]
          [views=game,game_body,ads,front,front34,side] [stance_set=1] [res_game=4480x2520] [res_body=9600x5400] [res_ads=2560x1440]
          [res_ortho=1080x1350] [samples=32] [scale=1.0]
Writes <out dir>/<variant>/<view>.png; with stance_set=1 also <out dir>/B_stance/<S1|S2|S3>/<side|front>.png (B arms on the three stances).
"""
import bpy, bmesh, sys, os, math, time
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
VARS = [v for v in KV.get('variants', 'V1,V2').split(',') if v]
VIEWS = [v for v in KV.get('views', 'front,side,front34,ots,game_body').split(',') if v]
SCALE = float(KV.get('scale', 1.0))
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ad = arm.animation_data
T0 = time.time()
STANCE_SET = {}


def res_of(key, default):
    w, h = (int(v) for v in KV.get(key, default).split('x'))
    return int(round(w * SCALE)), int(round(h * SCALE))


def use_action(name):
    act = bpy.data.actions[name]
    ad.action = act
    if hasattr(ad, 'action_slot') and ad.action_slot is None and len(act.slots):
        ad.action_slot = act.slots[0]
    scene.frame_set(1)
    scene.frame_set(0)
    bpy.context.view_layer.update()


def use_variant(v):
    use_action('Yoru_Aim_r4_full_%s' % v)


def feet_mid():
    a = arm.matrix_world @ arm.pose.bones['J_Bip_L_Foot'].head
    b = arm.matrix_world @ arm.pose.bones['J_Bip_R_Foot'].head
    return Vector((0.5 * (a.x + b.x), 0.5 * (a.y + b.y), 0.0))


# ---------------------------------------------------------------- world (as build_sprint_r1_render.py)
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
post_ob = mesh_object('game_posts', posts, material('game_posts', (0.55, 0.45, 0.30, 1)))
try:
    scene.render.engine = 'BLENDER_EEVEE'
except TypeError as e:
    print('engine:', e)
try:
    scene.eevee.taa_render_samples = int(KV.get('samples', 32))
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
sun = bpy.data.lights.new('sun_game', 'SUN')
sun.energy = 3.5
so = bpy.data.objects.new('sun_game', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(35))
world = bpy.data.worlds.new('w_game')
world.use_nodes = True
next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND').inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
scene.world = world

# ---------------------------------------------------------------- cameras (the game ones over the middle between the ankles)
use_variant(VARS[0] if VARS else 'V1')
FM = feet_mid()
print('FEET_MID %.4f %.4f' % (FM.x, FM.y), flush=True)


def persp_cam(name, pivot, dist, right, pitch_deg, fov):
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(fov)
    cd.clip_end = 300
    cd.clip_start = 0.05
    ob = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(ob)
    p = math.radians(pitch_deg)
    ob.location = (FM.x + right, FM.y - dist * math.cos(p), pivot + dist * math.sin(p))
    ob.rotation_euler = (math.radians(90.0) - p, 0.0, 0.0)
    return ob


def ortho_cam(name, loc, target, scale):
    cd = bpy.data.cameras.new(name)
    cd.type = 'ORTHO'
    cd.ortho_scale = scale
    cd.clip_end = 60
    ob = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def lens_cam(name, target, dist, down_deg, lens=50.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.sensor_fit = 'AUTO'
    cd.clip_end = 60
    ob = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(ob)
    t = Vector(target)
    d = math.radians(down_deg)
    ob.location = t + Vector((0.0, dist * math.cos(d), dist * math.sin(d)))
    ob.rotation_euler = (t - ob.location).to_track_quat('-Z', 'Y').to_euler()
    return ob


CAM = {'game': persp_cam('cam_game', 1.35, 4.4, 0.35, 15.0, 60.0),
       'ads': persp_cam('cam_ads', 1.30, 2.4, 0.58, 15.0, 42.0),
       'ots': persp_cam('cam_ots', 1.35, 4.4, 0.60, 15.0, 60.0),
       'front': lens_cam('cam_front', (FM.x, FM.y + 0.05, 0.84), 2.75, 11.0),
       'front34': ortho_cam('cam_front34', (6.0 * math.sin(math.radians(35)), 6.0 * math.cos(math.radians(35)), 1.3), (0.0, 0.05, 0.82), 1.9),
       'side': ortho_cam('cam_side', (6.0, 0.15, 0.82), (0.0, 0.15, 0.82), 1.9)}
CAM['game_body'] = CAM['game']
RES = {'ots': res_of('res_game', '4480x2520'), 'game': res_of('res_game', '4480x2520'), 'game_body': res_of('res_body', '9600x5400'), 'ads': res_of('res_ads', '2560x1440'),
       'front': res_of('res_ortho', '1080x1350'), 'front34': res_of('res_ortho', '1080x1350'), 'side': res_of('res_ortho', '1080x1350')}


# ---------------------------------------------------------------- crop windows (common for all variants)
def figure_points(upper_only):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    zcut = (arm.matrix_world @ arm.pose.bones['J_Bip_C_Hips'].head).z - 0.10
    for name in ('Body', 'Face', 'Hair'):
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ob.matrix_world
        for i in range(0, len(me.vertices), 5):
            w = mw @ me.vertices[i].co
            if not upper_only or w.z > zcut:
                pts.append(w)
        ev.to_mesh_clear()
    for o in bpy.data.objects:
        if o.name.startswith('PLATZHALTER_Pistole'):
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    return pts


def window_of(view):
    cam = CAM[view]
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = RES[view]
    xs, ys = [], []
    for v in VARS:
        use_variant(v)
        for w in figure_points(view == 'game_body'):
            q = world_to_camera_view(scene, cam, w)
            xs.append(q.x)
            ys.append(q.y)
    cx, cy, w, h = 0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys)), max(xs) - min(xs), max(ys) - min(ys)
    body_px = h * RES[view][1]
    if view in ('game', 'ots'):
        w, h = max(w * 1.6, h * 0.95 * RES[view][1] / RES[view][0]), h * 1.12
    else:
        w, h = w * 1.22, h * 1.10
    win = (max(0.0, cx - w / 2), min(1.0, cx + w / 2), max(0.0, cy - h / 2), min(1.0, cy + h / 2))
    print('WINDOW %s x %.4f..%.4f y %.4f..%.4f | figure %.0f px high at %dx%d' % (view, win[0], win[1], win[2], win[3], body_px, *RES[view]), flush=True)
    return win, body_px


def render_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


done = 0
for view in VIEWS:
    cam = CAM[view]
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = RES[view]
    scene.render.resolution_percentage = 100
    post_ob.hide_render = view not in ('game', 'game_body', 'ads', 'ots')
    r = scene.render
    r.use_border = r.use_crop_to_border = False
    if view in ('game', 'game_body', 'ots'):
        win, bpx = window_of(view)
        r.use_border, r.use_crop_to_border = True, True
        r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = win
    elif view == 'ads':
        win, bpx = window_of(view)
        r.use_border = False
    for v in VARS:
        use_variant(v)
        render_to(os.path.join(OUT, v, '%s.png' % view))
        done += 1
        print('RENDERED', v, view, '%.0f s' % (time.time() - T0), flush=True)
if KV.get('stance_set') == '1':
    for view in ('side', 'front'):
        scene.camera = CAM[view]
        scene.render.resolution_x, scene.render.resolution_y = RES[view]
        scene.render.use_border = scene.render.use_crop_to_border = False
        post_ob.hide_render = True
        for sk, an in STANCE_SET.items():
            use_action(an)
            render_to(os.path.join(OUT, 'B_stance', sk, '%s.png' % view))
            done += 1
            print('RENDERED B_stance', sk, view, '%.0f s' % (time.time() - T0), flush=True)
print('RENDER DONE', done, 'stills in %.0f s' % (time.time() - T0), flush=True)
