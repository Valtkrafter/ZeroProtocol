"""
Lauf v2, round 1: puts 'Neu' (Lauf W, NTE reference) and 'Alt' (the old sprint, Blender/Yoru_Run.blend) into the user's LIVE Blender (MCP) next to
each other, each on its own floor lane that scrolls with its ground speed (a planted shoe stays on its tile), and plays them in real time.
Appends the collection 'Lauf_v2_R1' from Blender/work/Lauf_v2/Yoru_Lauf_v2_round1.blend; the collections of earlier rounds (Walk_v2,
Walk_v2_R2, Walk_v2_R3, Walk_v2_R4) are only excluded from the view layer (not deleted).  Nothing is saved.
Scene: 60 fps, frames 0 .. 359 (9 cycles of Neu = 10 cycles of Alt, both loop seamlessly), FRAME_DROP (real time).
Live (MCP):  exec(open(r'C:\\Users\\valen\\ZeroProtocol\\Blender\\scripts\\build_lauf_v2_live_r1.py', encoding='utf-8').read())
"""
import bpy
from mathutils import Vector, Quaternion, Matrix
import math

PATH = r'C:\Users\valen\ZeroProtocol\Blender\work\Lauf_v2\Yoru_Lauf_v2_round1.blend'
ROOT = 'Lauf_v2_R1'
OLD = ('Walk_v2', 'Walk_v2_R2', 'Walk_v2_R3', 'Walk_v2_R4')


def _find_lc(lc, name):
    if lc.name == name:
        return lc
    for c in lc.children:
        r = _find_lc(c, name)
        if r:
            return r
    return None


def _view_rot(eye_dir):
    e = Vector(eye_dir).normalized()
    right = Vector((0.0, 0.0, 1.0)).cross(e).normalized()
    up = e.cross(right).normalized()
    return Matrix((right, up, e)).transposed().to_quaternion()


def show_round1():
    scene = bpy.context.scene
    vl = bpy.context.view_layer
    for old in OLD:
        lc = _find_lc(vl.layer_collection, old)
        if lc:
            lc.exclude = True
    if ROOT not in bpy.data.collections:
        with bpy.data.libraries.load(PATH, link=False) as (src, dst):
            dst.collections = [ROOT]
        scene.collection.children.link(bpy.data.collections[ROOT])
    else:
        lc = _find_lc(vl.layer_collection, ROOT)
        if lc:
            lc.exclude = False
    scene.render.fps = 60
    scene.render.fps_base = 1.0
    scene.frame_start, scene.frame_end = 0, 359
    try:
        scene.sync_mode = 'FRAME_DROP'
    except Exception:
        pass
    scene.frame_set(0)
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                sp = area.spaces.active
                sp.shading.type = 'MATERIAL'
                sp.overlay.show_overlays = False
                r3 = sp.region_3d
                r3.view_perspective = 'PERSP'
                sp.lens = 50
                r3.view_location = Vector((0.0, 0.0, 0.82))
                r3.view_rotation = _view_rot((math.sin(math.radians(28)), math.cos(math.radians(28)), 0.18))
                r3.view_distance = 4.6
                with bpy.context.temp_override(window=win, area=area):
                    if not bpy.context.screen.is_animation_playing:
                        bpy.ops.screen.animation_play()
                break
    return {o.name: o.animation_data.action.name for o in bpy.data.collections[ROOT].all_objects
            if o.type == 'ARMATURE' and o.animation_data and o.animation_data.action}


print(show_round1())
