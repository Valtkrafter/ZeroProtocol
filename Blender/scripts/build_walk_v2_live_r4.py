"""
Walk v2, round 4: puts R3 | R4a | R4b into the user's LIVE Blender (MCP) next to each other and plays them in real time.
Appends the collection 'Walk_v2_R4' from Blender/work/Walk_v2/Yoru_Walk_v2_round4.blend; the collections of earlier rounds (Walk_v2,
Walk_v2_R2, Walk_v2_R3) are only excluded from the view layer (not deleted).  Nothing is saved.
Live (MCP):  exec(open(r'C:\\Users\\valen\\ZeroProtocol\\Blender\\scripts\\build_walk_v2_live_r4.py', encoding='utf-8').read())
"""
import bpy

PATH = r'C:\Users\valen\ZeroProtocol\Blender\work\Walk_v2\Yoru_Walk_v2_round4.blend'


def _find_lc(lc, name):
    if lc.name == name:
        return lc
    for c in lc.children:
        r = _find_lc(c, name)
        if r:
            return r
    return None


def show_round4():
    scene = bpy.context.scene
    vl = bpy.context.view_layer
    for old in ('Walk_v2', 'Walk_v2_R2', 'Walk_v2_R3'):
        lc = _find_lc(vl.layer_collection, old)
        if lc:
            lc.exclude = True
    if 'Walk_v2_R4' not in bpy.data.collections:
        with bpy.data.libraries.load(PATH, link=False) as (src, dst):
            dst.collections = ['Walk_v2_R4']
        scene.collection.children.link(bpy.data.collections['Walk_v2_R4'])
    scene.render.fps = 30
    scene.frame_start, scene.frame_end = 0, 24
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
                sp.region_3d.view_distance = 4.6
                sp.region_3d.view_location = (0.0, 0.0, 0.95)
                with bpy.context.temp_override(window=win, area=area):
                    if not bpy.context.screen.is_animation_playing:
                        bpy.ops.screen.animation_play()
                break
    return {o.name: o.animation_data.action.name for o in bpy.data.objects if o.type == 'ARMATURE' and o.name.startswith('Yoru_R4')}


print(show_round4())
