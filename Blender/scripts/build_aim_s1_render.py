"""
Yoru - AIM SUITE STAGE 1: PNG frames of the aim-idle loop for the preview video (saves nothing; world, light and cameras as build_aim_r5_render.py).
  blender -b <Blender/work/Aim/Yoru_Aim_s1.blend> --python build_aim_s1_render.py -- <out dir> [frames=0-358] [step=2] [views=front34,game_body]
          [samples=16] [res_front=768x960] [res_game=8960x5040] [action=Yoru_Aim_Idle]
  front34    orthographic from her front right (35 deg off the front, 6 m, ortho scale 1.9 m), whole figure (as round 5)
  game_body  the REAL game camera: pivot 1.35 m over the middle between the ankles (frame 0), 4.4 m behind the pivot, 0.35 m right, 15 deg down,
             vertical FOV 60 deg; border crop on head to hips, arms and pistols, ONE window for the whole loop (union over 6 frames)
Writes <out dir>/<view>/f_<frame>.png; frames already there are skipped (the run can be resumed).
"""
import bpy, bmesh, sys, os, math, time
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = os.path.abspath(argv[0])                                       # absolute: Blender resolves a relative render path against the drive root
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
F0, F1 = (int(x) for x in KV.get('frames', '0-358').split('-'))
STEP = int(KV.get('step', 2))
VIEWS = [v for v in KV.get('views', 'front34,game_body').split(',') if v]
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ad = arm.animation_data
act = bpy.data.actions[KV.get('action', 'Yoru_Aim_Idle')]
ad.action = act
if hasattr(ad, 'action_slot') and len(act.slots):
    ad.action_slot = act.slots[0]
T0 = time.time()


def res_of(key, default):
    w, h = (int(v) for v in KV.get(key, default).split('x'))
    return w, h


# ---------------------------------------------------------------- world (as build_aim_r5_render.py)
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
    scene.eevee.taa_render_samples = int(KV.get('samples', 16))
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

# ---------------------------------------------------------------- cameras
scene.frame_set(0)
fl = arm.matrix_world @ arm.pose.bones['J_Bip_L_Foot'].head
fr = arm.matrix_world @ arm.pose.bones['J_Bip_R_Foot'].head
FM = Vector((0.5 * (fl.x + fr.x), 0.5 * (fl.y + fr.y), 0.0))


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


CAM = {'game_body': persp_cam('cam_game', 1.35, 4.4, 0.35, 15.0, 60.0),
       'front34': ortho_cam('cam_front34', (6.0 * math.sin(math.radians(35)), 6.0 * math.cos(math.radians(35)), 1.3), (0.0, 0.05, 0.82), 1.9)}
RES = {'game_body': res_of('res_game', '8960x5040'), 'front34': res_of('res_front', '768x960')}


def figure_points():
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
            if w.z > zcut:
                pts.append(w)
        ev.to_mesh_clear()
    for o in bpy.data.objects:
        if o.name.startswith('PLATZHALTER_Pistole'):
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    return pts


def game_window():
    cam = CAM['game_body']
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = RES['game_body']
    xs, ys = [], []
    for f in (0, 60, 117, 150, 210, 279):
        scene.frame_set(f)
        for w in figure_points():
            q = world_to_camera_view(scene, cam, w)
            xs.append(q.x)
            ys.append(q.y)
    cx, cy, w, h = 0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys)), max(xs) - min(xs), max(ys) - min(ys)
    w, h = w * 1.22, h * 1.10
    win = (max(0.0, cx - w / 2), min(1.0, cx + w / 2), max(0.0, cy - h / 2), min(1.0, cy + h / 2))
    print('WINDOW game_body x %.4f..%.4f y %.4f..%.4f -> %d x %d px' % (win[0], win[1], win[2], win[3], (win[1] - win[0]) * RES['game_body'][0],
                                                                     (win[3] - win[2]) * RES['game_body'][1]), flush=True)
    return win


WIN = game_window() if 'game_body' in VIEWS else None
n_done = 0
for f in range(F0, F1 + 1, STEP):
    todo = [v for v in VIEWS if not os.path.exists(os.path.join(OUT, v, 'f_%03d.png' % f))]
    if not todo:
        continue
    scene.frame_set(f)
    for v in todo:
        scene.camera = CAM[v]
        scene.render.resolution_x, scene.render.resolution_y = RES[v]
        scene.render.resolution_percentage = 100
        post_ob.hide_render = v != 'game_body'
        r = scene.render
        r.use_border = r.use_crop_to_border = v == 'game_body'
        if v == 'game_body':
            r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = WIN
        path = os.path.join(OUT, v, 'f_%03d.png' % f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        r.filepath = path
        bpy.ops.render.render(write_still=True)
        n_done += 1
    print('RENDERED frame %d (%s) %.0f s' % (f, ','.join(todo), time.time() - T0), flush=True)
print('RENDER DONE', n_done, 'images in %.0f s' % (time.time() - T0), flush=True)
