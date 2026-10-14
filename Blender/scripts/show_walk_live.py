"""Starts the walk preview in a normal Blender window:  blender.exe Yoru_Walk.blend --python show_walk_live.py

The view is set up in small steps from a timer, only while the 3D view really has a size (a minimised window has none):
  1. EEVEE as render engine (the only engine that honours the alpha-cut of Yoru's "Onepiece" material; Workbench shows a fake long dress)
  2. the 3D view is split in two: LEFT the whole body from the front right (she walks towards the camera),
     RIGHT the face close-up (85 mm lens) - there the blinks (shape key Fcl_EYE_Close, Yoru_Blink.json) can be seen
  3. Material Preview shading in both, then the playback (30 fps, real time, frames are dropped when the viewport is slower;
     the timeline is 20 gait cycles long = 17.3 s, the blinks are on it, the walk repeats by itself)
  4. after 6 s of playback the real frame rate of the viewport is counted and written to Blender/work/blink/live_fps.txt
The floor under her moves backwards at exactly the walk speed: a planted shoe must stay on its checker cell.
"""
import bpy, os, time
from mathutils import Vector, Matrix

STATE = {'step': 0, 'tries': 0, 'frames': 0, 't0': None, 'face_area': None}
FPS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'blink', 'live_fps.txt')


def find_view3d():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D':
                return w, a
    return None, None


def look_rotation(look):
    """region_3d.view_rotation is the CAMERA orientation (columns right, up, back) in this Blender build"""
    look = Vector(look).normalized()
    right = look.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(look).normalized()
    return Matrix((right, up, -look)).transposed().to_quaternion()


def eye_center():
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    pb = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
    return (pb['J_Adj_L_FaceEye'].head + pb['J_Adj_R_FaceEye'].head) * 0.5


def on_frame(scene, *args):
    STATE['frames'] += 1


def window_minimized():
    """True while the Blender window of this process is minimised (Windows only). Changing engine / shading / areas of a minimised window
    crashed Blender when it was restored, so everything below waits until the user clicks the window open."""
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.IsIconic.argtypes = [wintypes.HWND]
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        pid = os.getpid()
        res = {'iconic': None}
        proc_t = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def cb(hwnd, lp):
            p = wintypes.DWORD()
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if p.value == pid and u.IsWindowVisible(hwnd):
                buf = ctypes.create_unicode_buffer(300)
                u.GetWindowTextW(hwnd, buf, 300)
                if 'Blender' in buf.value:
                    res['iconic'] = bool(u.IsIconic(hwnd))
                    return False
            return True
        u.EnumWindows(proc_t(cb), 0)
        return res['iconic'] is True
    except Exception as e:
        print('minimised check failed:', e)
        return False


def setup_face_area(fa):
    sp = fa.spaces.active
    rv = sp.region_3d
    c = eye_center()
    rv.view_perspective = 'PERSP'
    rv.view_rotation = look_rotation((0.0, -1.0, 0.0))
    rv.view_distance = 0.78
    rv.view_location = Vector((c.x, c.y, c.z - 0.015))
    sp.lens = 85.0
    sp.overlay.show_overlays = False
    sp.show_gizmo = False
    sp.shading.type = 'MATERIAL'
    try:
        sp.show_object_viewport_armature = False
    except Exception:
        pass
    print('face view at', tuple(round(v, 3) for v in rv.view_location))


def _tick():
    if STATE['step'] < 4 and window_minimized():
        return 2.0                                            # wait (checked every 2 s) until the window is open
    w, a = find_view3d()
    STATE['tries'] += 1
    if a is None or a.width < 200 or a.height < 200:
        return 1.0 if STATE['tries'] < 300 else None          # window not ready: wait
    scene = bpy.context.scene
    space = a.spaces.active
    r3d = space.region_3d
    s = STATE['step']
    if s == 0:
        try:
            scene.render.engine = 'BLENDER_EEVEE'
        except TypeError as e:
            print('engine:', str(e)[:200])
        scene.frame_set(0)
        scene.sync_mode = 'FRAME_DROP'
        # she faces +Y, her right is +X: the camera stands in front of her, a little to her right and above, looking at her
        r3d.view_perspective = 'PERSP'
        r3d.view_rotation = look_rotation((-0.50, -0.86, -0.10))
        r3d.view_distance = 3.3
        r3d.view_location = Vector((0.0, 0.0, 0.88))
        space.overlay.show_floor = False
        space.overlay.show_axis_x = False
        space.overlay.show_axis_y = False
        try:
            space.show_object_viewport_armature = False       # no bone spheres over her
        except Exception as e:
            print('armature filter:', e)
        STATE['step'] = 1
        return 1.0
    if s == 1:                                                # split: left body, right face
        STATE['step'] = 2                                     # whatever happens below, the next step runs
        n_before = len([x for x in w.screen.areas if x.type == 'VIEW_3D'])
        with bpy.context.temp_override(window=w, screen=w.screen, area=a):
            bpy.ops.screen.area_split(direction='VERTICAL', factor=0.52)
        areas = sorted([x for x in w.screen.areas if x.type == 'VIEW_3D'], key=lambda x: x.x)
        print('3D views: %d -> %d' % (n_before, len(areas)))
        if len(areas) >= 2:
            STATE['body_area'], STATE['face_area'] = areas[0], areas[-1]
        return 1.5
    if s == 2:
        STATE['step'] = 3
        fa = STATE.get('face_area')
        if fa is not None:
            setup_face_area(fa)
        else:                                                 # the split did not work: one view, closer, so that the face can still be seen
            r3d.view_distance = 1.4
            r3d.view_location = Vector((0.0, 0.0, 1.35))
        a.spaces.active.shading.type = 'MATERIAL'
        return 4.0
    if s == 3:
        STATE['step'] = 4
        for area in w.screen.areas:
            area.tag_redraw()
        bpy.app.handlers.frame_change_post.append(on_frame)
        with bpy.context.temp_override(window=w, screen=w.screen, area=a):
            bpy.ops.screen.animation_play()
        STATE['t0'] = time.time()
        STATE['frames'] = 0
        print('walk preview running')
        return 6.0
    if s == 4:                                                # count the frames that were really drawn
        STATE['step'] = 5
        dt = time.time() - STATE['t0']
        fps = STATE['frames'] / dt if dt > 0 else 0.0
        try:
            with open(FPS_FILE, 'w') as fh:
                fh.write('viewport frames drawn per second during playback: %.1f (%d frames in %.1f s)\n' % (fps, STATE['frames'], dt))
        except Exception as e:
            print('fps file:', e)
        print('viewport fps %.1f' % fps)
        try:
            bpy.app.handlers.frame_change_post.remove(on_frame)
        except Exception:
            pass
    return None


def tick():
    """an error in one step must not stop the others: the step counter is advanced before the work, the timer runs on"""
    try:
        return _tick()
    except Exception:
        import traceback
        traceback.print_exc()
        STATE['errors'] = STATE.get('errors', 0) + 1
        return 2.0 if STATE['errors'] < 8 else None


bpy.app.timers.register(tick, first_interval=2.0)
