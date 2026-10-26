"""
Yoru - IDLE v2, round 4: facial expressions for the idle (stills, no animation).  Only the face shape keys of the VRoid model and a touch of
head / ear pose; the body stays the still A2 stance.  The variants differ in ONE thing: the mood.
  N  Neutral   = the face as it is now (all expression keys 0)
  A  ruhig-selbstsicher  calm, sure of herself: brows relaxed, eyes a little soft, mouth corners a breath up (a half smirk), chin a touch down
  B  kühl-wachsam        cool, watchful: brows a little lowered, eyes a little narrower and attentive, mouth straight, ears forward
  C  sanft               soft: eyes softer, a minimal smile, brows a little raised (not sad, not cute), head a hair tilted
Shape keys of the model (Face mesh, VRoid): Fcl_ALL_* (whole face), Fcl_BRW_* (brows), Fcl_EYE_* (eyes, incl. Close, Spread, Iris_Hide,
Highlight_Hide), Fcl_MTH_* (mouth, vowels A I U E O), Fcl_HA_* (teeth / fangs).  The eyes have bones (J_Adj_L/R_FaceEye) for the gaze.

Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>).read(), ns); ns['make_face_row'](bpy.data.objects['Yoru_A2'])
Background stills:  blender -b <stage .blend> --python build_idle_v2_face.py -- render <out dir> [armature, default: every Gesicht_* Yoru]
  writes <out dir>/<key>/face_front.png, face_34.png, front34.png
NOTE: all copies of Yoru in the stage share ONE face mesh (linked duplicates), and shape key values live on the mesh; every face Yoru made
here therefore gets its own copy of the face mesh (with its own shape keys, without the blink animation).
"""
import bpy, sys, os, math
from mathutils import Vector, Quaternion, Euler, Matrix

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_idle_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
L = {}
exec(compile(open(os.path.join(_HERE, 'build_idle_v2_lib.py'), encoding='utf-8').read(), os.path.join(_HERE, 'build_idle_v2_lib.py'), 'exec'), L)

# shape key values (0..1) per expression; head = (pitch, roll, yaw) in deg added to the still head (pitch - = chin down, roll + = her right ear down);
# ears = deg about X (+ = tips forward) and about Y (+ = tips outwards) for both ears
# The fringe hides the brows (the brow keys hardly show); the mood is carried by the eyes (EYE_Fun lifts the lower lid = softer,
# EYE_Angry lowers the upper lid at the inner corner = focused) and the mouth (MTH_Fun = closed smile, MTH_Neutral / MTH_Close = straight,
# MTH_Angry = corners down).  EYE_Joy (^^) and MTH_Joy (open laugh) are too much for the persona and are not used.
EXPRESSIONS = {
    'N': dict(label='Neutral (jetzt)', keys={}, head=(0.0, 0.0, 0.0), ears=(0.0, 0.0)),
    # A: upper lids a little lowered (relaxed, knowing) + a small closed smile with the corners up
    'A': dict(label='A  ruhig-selbstsicher',
              keys={'Fcl_EYE_Angry': 0.22, 'Fcl_EYE_Fun': 0.28, 'Fcl_MTH_Fun': 0.40, 'Fcl_MTH_Up': 0.40, 'Fcl_BRW_Fun': 0.30},
              head=(-2.0, 1.5, 0.0), ears=(-4.0, 3.0)),
    # B: focused squint (upper lid down at the inner corner, lower lid up a little), mouth straight and closed, ears forward
    'B': dict(label='B  kühl-wachsam',
              keys={'Fcl_EYE_Angry': 0.40, 'Fcl_EYE_Fun': 0.16, 'Fcl_MTH_Neutral': 0.55, 'Fcl_MTH_Close': 0.20, 'Fcl_BRW_Angry': 0.50},
              head=(-3.0, 0.0, 0.0), ears=(8.0, -2.0)),
    # C: soft eyes (lower lid up, upper lid NOT lowered), a warmer closed smile, head a little tilted, ears relaxed
    'C': dict(label='C  sanft',
              keys={'Fcl_EYE_Fun': 0.52, 'Fcl_EYE_Sorrow': 0.08, 'Fcl_MTH_Fun': 0.65, 'Fcl_BRW_Sorrow': 0.30},
              head=(0.0, 3.0, 0.0), ears=(-7.0, 5.0)),
}
ORDER = ('N', 'A', 'B', 'C')
FACE_X = {'N': 0.9, 'A': 0.3, 'B': -0.3, 'C': -0.9}         # live row of the four faces (x), at FACE_Y; seen from the front N A B C left to right
FACE_Y = 2.2


def face_child(arm):
    return next(c for c in arm.children if c.type == 'MESH' and c.data.shape_keys and 'Fcl_EYE_Close' in c.data.shape_keys.key_blocks)


def apply_expression(arm, key, rig=None):
    """sets the shape keys of this Yoru's face and poses the body as the still A2 with the head / ear touch of the expression"""
    E = EXPRESSIONS[key]
    face = face_child(arm)
    for kb in face.data.shape_keys.key_blocks:
        if kb.name != 'Basis':
            kb.value = E['keys'].get(kb.name, 0.0)
    rig = rig or L['Rig'](arm, L['humanoid_map']())
    C = dict(L['COMMON2'])
    hp, hr, hy = E['head']
    C['head_pitch'] = C['head_pitch'] + hp
    C['head_roll'] = hr
    C['head_yaw'] = hy
    ex, ey = E['ears']
    rel = {}
    for side, sx in (('L', -1.0), ('R', 1.0)):
        n = 'J_Opt_%s_CatEar1_01' % side
        if n in rig.bones:
            rel[n] = Euler((math.radians(ex), math.radians(sx * ey), 0.0), 'XYZ').to_quaternion()
    C['extra_rel'] = rel
    V = dict(L['VARIANTS']['A2'])
    V['arm_adj'] = {}
    L['pose_variant'](rig, 'A2', C, V)
    return face


def make_face_yoru(src_arm, key, x, y):
    """a still Yoru of its own for one expression: armature copy, body / hair shared, the FACE mesh copied (own shape keys, no blink action)"""
    cname = 'Gesicht_' + key
    col = bpy.data.collections.get(cname) or bpy.data.collections.new(cname)
    if col.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(col)
    name = 'Yoru_Gesicht_' + key
    arm = bpy.data.objects.get(name)
    if arm is None:
        arm = src_arm.copy()
        arm.animation_data_clear()
        arm.name = name
        col.objects.link(arm)
        for ch in src_arm.children:
            c2 = ch.copy()
            col.objects.link(c2)
            c2.parent = arm
            c2.matrix_parent_inverse = ch.matrix_parent_inverse.copy()
            for m in c2.modifiers:
                if m.type == 'ARMATURE':
                    m.object = arm
            if c2.data.shape_keys and 'Fcl_EYE_Close' in c2.data.shape_keys.key_blocks:
                c2.data = ch.data.copy()                          # own face mesh + own shape keys
                if c2.data.shape_keys.animation_data:
                    c2.data.shape_keys.animation_data_clear()      # no blink here
            c2.name = ch.name.split('_A2')[0].split('.')[0] + '_Gesicht_' + key
    arm.location = Vector((x, y, 0.0))
    return arm


def make_label_upright(text, x, y, z, name):
    ob = bpy.data.objects.get(name)
    if ob:
        return ob
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = text
    cu.size = 0.045
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (x, y, z)
    ob.rotation_euler = (math.radians(90.0), 0.0, math.radians(180.0))      # upright, readable from the front (+Y)
    ob.hide_render = True
    mat = bpy.data.materials.get('Label_Gesicht_Material') or bpy.data.materials.new('Label_Gesicht_Material')
    mat.use_nodes = True
    bsdf = next(n_ for n_ in mat.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.95, 0.85, 0.45, 1.0)
    cu.materials.append(mat)
    return ob


def make_face_row(src_arm):
    """live: four still Yorus (N, A, B, C) side by side with their faces; returns the armatures"""
    rig_cache = {}
    out = {}
    H = L['humanoid_map']()
    for k in ORDER:
        arm = make_face_yoru(src_arm, k, FACE_X[k], FACE_Y)
        apply_expression(arm, k, L['Rig'](arm, H))
        make_label_upright(EXPRESSIONS[k]['label'].replace('  ', ' '), FACE_X[k], FACE_Y + 0.12, 1.70, 'Label_Gesicht_' + k)
        out[k] = arm
    return out


# ------------------------------------------------------------------ background stills
def _setup_render(scene, res=(600, 600)):
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        pass
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    try:
        scene.eevee.taa_render_samples = 32
    except Exception:
        pass
    scene.render.image_settings.file_format = 'PNG'
    if not bpy.data.objects.get('sun_face'):
        sun = bpy.data.lights.new('sun_face', 'SUN')
        sun.energy = 3.5
        so = bpy.data.objects.new('sun_face', sun)
        scene.collection.objects.link(so)
        so.rotation_euler = (math.radians(55), 0, math.radians(35))
    world = bpy.data.worlds.get('w_face') or bpy.data.worlds.new('w_face')
    world.use_nodes = True
    next(n_ for n_ in world.node_tree.nodes if n_.type == 'BACKGROUND').inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
    scene.world = world
    for o in bpy.data.objects:
        if o.name.startswith(('Label_', 'Icosphere')):
            o.hide_render = True


def _cam(name, persp_lens=None, ortho=None):
    o = bpy.data.objects.get(name)
    if o:
        return o
    d = bpy.data.cameras.new(name)
    if persp_lens:
        d.type, d.lens = 'PERSP', persp_lens
    else:
        d.type, d.ortho_scale = 'ORTHO', ortho
    d.clip_start, d.clip_end = 0.05, 60.0
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    return o


def _look(cam, eye, target):
    fwd = (target - eye).normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    cam.matrix_world = Matrix((right, up, -fwd)).transposed().to_4x4()
    cam.location = eye


def render_face_set(arm, out_dir, keys=ORDER, only_this=True):
    """renders face_front / face_34 (85 mm, close) and front34 (the normal full-figure still) for every expression on this ONE Yoru"""
    scene = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    if only_this:
        keep = set([arm.name] + [c.name for c in arm.children] + ['Boden'])
        for o in bpy.data.objects:
            if o.type in ('MESH', 'CURVE', 'FONT'):
                o.hide_render = (o.name not in keep) or o.name.startswith(('Label_', 'Icosphere'))
    cam_f = _cam('cam_face_front', persp_lens=85.0)
    cam_q = _cam('cam_face_34', persp_lens=85.0)
    cam_w = _cam('cam_front34_far', ortho=2.0)
    for k in keys:
        apply_expression(arm, k, rig)
        bpy.context.view_layer.update()
        M = arm.matrix_world
        head = M @ arm.pose.bones[H['head']].head
        target = head + Vector((0.0, 0.035, 0.065))
        d = os.path.join(out_dir, k)
        os.makedirs(d, exist_ok=True)
        _setup_render(scene, (600, 600))
        _look(cam_f, target + Vector((0.0, 0.85, 0.0)), target)
        scene.camera = cam_f
        scene.render.filepath = os.path.join(d, 'face_front.png')
        bpy.ops.render.render(write_still=True)
        a = math.radians(35.0)
        _look(cam_q, target + Vector((0.85 * math.sin(a), 0.85 * math.cos(a), 0.0)), target)
        scene.camera = cam_q
        scene.render.filepath = os.path.join(d, 'face_34.png')
        bpy.ops.render.render(write_still=True)
        _setup_render(scene, (600, 720))
        base = M.translation.copy()
        tgt = base + Vector((0.0, -0.05, 0.80))
        _look(cam_w, base + Vector((6.0 * math.sin(a), 6.0 * math.cos(a), 1.3)), tgt)
        scene.camera = cam_w
        scene.render.filepath = os.path.join(d, 'front34.png')
        bpy.ops.render.render(write_still=True)
        print('[face] rendered', k, flush=True)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    if argv[0] != 'render':
        raise SystemExit('usage: ... -- render <out dir> [armature] [look=<colour look, e.g. AgX - Medium High Contrast>]')
    out = argv[1]
    looks = [a.split('=', 1)[1] for a in argv[2:] if a.startswith('look=')]
    rest = [a for a in argv[2:] if not a.startswith('look=')]
    if looks:
        bpy.context.scene.view_settings.view_transform = 'AgX'
        bpy.context.scene.view_settings.look = looks[0]
    names = [rest[0]] if rest else None
    if names:
        arm = bpy.data.objects[names[0]]
        render_face_set(arm, out)
    else:
        for k in ORDER:
            arm = bpy.data.objects.get('Yoru_Gesicht_' + k)
            if arm:
                render_face_set(arm, out, keys=(k,))
    print('[face] DONE', flush=True)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
