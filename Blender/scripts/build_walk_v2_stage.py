"""
Yoru - WALK v2, round 1: the STAGE (live in the user's Blender and in the background build).
Three Yorus side by side (A kontrolliert, B Swagger, C Catwalk, 1.2 m apart, seen from the front A is on the left), a checker floor that
scrolls backwards at exactly the walking speed (the Yorus walk in place, a planted shoe stays on its tile), labels in front of the feet.
Everything lives in the collection 'Walk_v2' (children Walk_v2_A / _B / _C / Walk_v2_Beschriftung).

Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>, encoding='utf-8').read(), ns)
             ns['clear_default_objects'](); arm = ns['import_yoru']('A'); ns['make_scroll_floor'](); ns['setup_view']()
Background:  used by build_walk_v2_round1.py (no main here).
Floor: checker tiles of TILE m; the mapping location is keyed linearly (extrapolated), SPEED m/s backwards.  One gait cycle moves the floor
by SPEED * NF / FPS = 1.16 m = two checker periods, so the loop over any whole number of cycles is seamless.
Blender axes for Yoru: +Y forward, her right = +X, up = +Z.
"""
import bpy, os, math
from mathutils import Vector, Matrix

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_idle_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
L = {}
exec(compile(open(os.path.join(_HERE, 'build_idle_v2_lib.py'), encoding='utf-8').read(), os.path.join(_HERE, 'build_idle_v2_lib.py'), 'exec'), L)

GLB = r'C:\Users\valen\ZeroProtocol\Blender\work\Yoru_V2.glb'
ROOT = 'Walk_v2'
KEYS = ('A', 'B', 'C')
X_POS = {'A': 1.2, 'B': 0.0, 'C': -1.2}
SUB = {k: 'Walk_v2_' + k for k in KEYS}
LABEL_COLL = 'Walk_v2_Beschriftung'
LABEL_TEXT = {'A': 'A  kontrolliert', 'B': 'B  Swagger', 'C': 'C  Catwalk'}
FPS = 30
NF = 29                      # one gait cycle (two steps) = 29 frames = 0.967 s
SPEED = 1.2                  # m/s
TILE = 0.29                  # m; checker period 0.58 m, the cycle moves 1.16 m = two periods
FLOOR_HALF = 8.0


def log(*a):
    print('[walk_v2 stage]', *a, flush=True)


def ensure_coll(name, parent=None):
    scene = bpy.context.scene
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    par = parent if parent is not None else scene.collection
    if col.name not in [c.name for c in par.children]:
        par.children.link(col)
    return col


def root_coll():
    return ensure_coll(ROOT)


def clear_default_objects():
    """the three objects of Blender's start file (the user allowed deleting them in the fresh walk file)"""
    gone = []
    for name, typ in (('Cube', 'MESH'), ('Light', 'LIGHT'), ('Camera', 'CAMERA')):
        o = bpy.data.objects.get(name)
        if o is not None and o.type == typ:
            bpy.data.objects.remove(o, do_unlink=True)
            gone.append(name)
    return gone


def import_yoru(key='A', glb=GLB):
    """imports Yoru_V2.glb into Walk_v2_<key>; hides the 2 m icosphere of the import and excludes 'glTF_not_exported'"""
    root = root_coll()
    col = ensure_coll(SUB[key], root)
    vl = bpy.context.view_layer
    vl.active_layer_collection = L['find_layer_collection'](vl.layer_collection, col.name)
    before = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb)
    new = [o for o in bpy.data.objects if o.name not in before]
    for o in new:
        if o.type == 'MESH' and o.name.startswith('Icosphere'):
            o.hide_viewport = True
            o.hide_render = True
            o.hide_set(True)
    lc = L['find_layer_collection'](vl.layer_collection, 'glTF_not_exported')
    if lc:
        lc.exclude = True
    arm = next(o for o in new if o.type == 'ARMATURE')
    arm.name = 'Yoru_Walk_' + key
    for ch in arm.children:
        ch.name = ch.name.split('.')[0] + '_Walk_' + key
    arm.location = Vector((X_POS[key], 0.0, 0.0))
    vl.active_layer_collection = L['find_layer_collection'](vl.layer_collection, root.name)
    return arm


def copy_yoru(src_arm, key):
    """another Yoru: own armature (own action), the meshes share their data with the original (all three wear face B, so sharing the
    face shape keys is fine in round 1)"""
    col = ensure_coll(SUB[key], root_coll())
    name = 'Yoru_Walk_' + key
    arm2 = bpy.data.objects.get(name)
    if arm2 is not None:
        return arm2
    arm2 = src_arm.copy()
    arm2.animation_data_clear()
    arm2.name = name
    col.objects.link(arm2)
    for ch in src_arm.children:
        c2 = ch.copy()
        col.objects.link(c2)
        c2.parent = arm2
        c2.matrix_parent_inverse = ch.matrix_parent_inverse.copy()
        for m in c2.modifiers:
            if m.type == 'ARMATURE':
                m.object = arm2
        c2.name = ch.name.split('_Walk_')[0] + '_Walk_' + key
    arm2.location = Vector((X_POS[key], 0.0, 0.0))
    return arm2


def _fcurves_of(action):
    if hasattr(action, 'fcurves'):
        try:
            return list(action.fcurves)
        except Exception:
            pass
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def make_scroll_floor(name='Boden_Walk'):
    ob = bpy.data.objects.get(name)
    if ob is not None:
        return ob
    me = bpy.data.meshes.new(name)
    s = FLOOR_HALF
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    me.uv_layers.new()
    ob = bpy.data.objects.new(name, me)
    root_coll().objects.link(ob)
    mat = bpy.data.materials.new(name + '_Material')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n_ for n_ in nt.nodes if n_.type == 'BSDF_PRINCIPLED')
    chk = nt.nodes.new('ShaderNodeTexChecker')
    chk.inputs['Color1'].default_value = (0.215, 0.225, 0.255, 1.0)
    chk.inputs['Color2'].default_value = (0.105, 0.112, 0.130, 1.0)
    chk.inputs['Scale'].default_value = 1.0 / TILE
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.name = 'Scroll'
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], chk.inputs['Vector'])
    nt.links.new(chk.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.85
    me.materials.append(mat)
    # pattern at p = checker(p + T): T.y growing at SPEED moves the tiles towards -Y (backwards under her feet)
    loc = mp.inputs['Location']
    loc.default_value = (0.0, 0.0, 0.0)
    loc.keyframe_insert('default_value', index=1, frame=0)
    loc.default_value = (0.0, SPEED * NF / FPS, 0.0)
    loc.keyframe_insert('default_value', index=1, frame=NF)
    for fc in _fcurves_of(nt.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'
        fc.extrapolation = 'LINEAR'
        fc.update()
    return ob


def make_labels():
    col = ensure_coll(LABEL_COLL, root_coll())
    out = []
    for k in KEYS:
        name = 'Label_Walk_' + k
        ob = bpy.data.objects.get(name)
        if ob is None:
            cu = bpy.data.curves.new(name, 'FONT')
            cu.body = LABEL_TEXT[k]
            cu.size = 0.13
            cu.align_x = 'CENTER'
            ob = bpy.data.objects.new(name, cu)
            col.objects.link(ob)
            mat = bpy.data.materials.new(name + '_Material')
            mat.use_nodes = True
            bsdf = next(n_ for n_ in mat.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED')
            bsdf.inputs['Base Color'].default_value = (0.90, 0.80, 0.40, 1.0)
            cu.materials.append(mat)
        ob.location = (X_POS[k], 0.62, 0.003)
        ob.rotation_euler = (0.0, 0.0, math.pi)              # reads from the front
        ob.hide_render = True
        out.append(ob)
    return out


def scene_settings(nf_play=NF):
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.frame_start, scene.frame_end = 0, nf_play - 1
    try:
        scene.render.engine = 'BLENDER_EEVEE'
    except TypeError as e:
        log('engine', e)
    try:
        scene.sync_mode = 'FRAME_DROP'                       # play in real time
    except Exception as e:
        log('sync', e)


def _view_rot(eye_dir):
    e = Vector(eye_dir).normalized()
    right = Vector((0.0, 0.0, 1.0)).cross(e).normalized()
    up = e.cross(right).normalized()
    return Matrix((right, up, e)).transposed().to_quaternion()


def setup_view(target=(0.0, 0.0, 0.82), eye_dir=(math.sin(math.radians(32)), math.cos(math.radians(32)), 0.30), dist=6.4, lens=50.0):
    """live only: material preview, no overlays, front three-quarter view on all three Yorus"""
    done = 0
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            sp = area.spaces.active
            sp.shading.type = 'MATERIAL'
            sp.overlay.show_overlays = False
            sp.lens = lens
            r3 = sp.region_3d
            r3.view_perspective = 'PERSP'
            r3.view_location = Vector(target)
            r3.view_rotation = _view_rot(eye_dir)
            r3.view_distance = dist
            done += 1
    return done


def play(on=True):
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                with bpy.context.temp_override(window=win, area=area):
                    playing = bool(bpy.context.screen.is_animation_playing)
                    if playing != on:
                        bpy.ops.screen.animation_play()
                return True
    return False
