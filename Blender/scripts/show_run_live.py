"""Starts the run preview in a normal Blender window:  blender.exe Yoru_Run.blend --python show_run_live.py [-- light | slow]

The playback is REAL TIME (1.0x): the scene runs at 60 fps with frame dropping (sync mode FRAME_DROP), so one 36-frame gait cycle always takes 0.60 s
of the clock, even if the viewport cannot draw all 60 frames a second (then it skips frames, it never plays slower).  After 9 s the script measures the
frames really drawn per second and the clock time of every gait cycle and writes both into Blender/work/run/live_fps.txt.
The view is set up in small steps from a timer, only while the 3D view really has a size (a minimised window has none):
  1. EEVEE as render engine (the only engine that honours the alpha-cut of Yoru's "Onepiece" material; Workbench shows a fake long dress)
  2. the 3D view is split in two: LEFT the whole body from the front right (she runs towards the camera),
     RIGHT the side view (stride, lean, arm swing, tail)
  3. Material Preview shading in both, then the playback
Arguments: light = one view only and no overlays (cheaper to draw, more frames a second);  slow = half speed (30 fps, every frame drawn; only for looking at details).
The floor under her moves backwards at exactly the running speed: a planted shoe must stay on its checker cell.
"""
import bpy, os, sys, time
from mathutils import Vector, Matrix

SLOW = 'slow' in sys.argv
LIGHT = 'light' in sys.argv
STATE = {'step': 0, 'tries': 0, 'frames': 0, 't0': None, 'side_area': None, 'samples': []}
FPS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'run', 'live_fps.txt')


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


def on_frame(scene, *args):
    STATE['frames'] += 1
    STATE['samples'].append((time.perf_counter(), scene.frame_current))


def cycle_report(period, fps_target):
    """clock time of the gait cycles of the playback: (mean seconds per cycle, cycles counted, drawn frames per second, share of dropped frames)"""
    s = STATE['samples']
    if len(s) < 4:
        return 0.0, 0, 0.0, 1.0
    marks = []                                                # the first drawn frame of every cycle (the cycle number changes or the timeline wraps)
    for (t0, f0), (t1, f1) in zip(s, s[1:]):
        if f1 // period != f0 // period or f1 < f0:
            marks.append(t1)
    dur = s[-1][0] - s[0][0]
    drawn = (len(s) - 1) / dur if dur > 0 else 0.0
    if len(marks) < 2:
        return 0.0, 0, drawn, 1.0 - drawn / fps_target
    mean = (marks[-1] - marks[0]) / (len(marks) - 1)
    return mean, len(marks) - 1, drawn, 1.0 - drawn / fps_target


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


def setup_side_area(sa):
    """the right view: her right side, nearly orthographic (long lens, far away), the whole body"""
    sp = sa.spaces.active
    rv = sp.region_3d
    rv.view_perspective = 'PERSP'
    rv.view_rotation = look_rotation((-1.0, 0.0, 0.0))
    rv.view_distance = 7.5
    rv.view_location = Vector((0.0, -0.05, 0.84))
    sp.lens = 100.0
    sp.overlay.show_overlays = False
    sp.show_gizmo = False
    sp.shading.type = 'MATERIAL'
    try:
        sp.show_object_viewport_armature = False
    except Exception:
        pass
    print('side view at', tuple(round(v, 3) for v in rv.view_location))


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
        scene.sync_mode = 'FRAME_DROP'                        # real time: frames are skipped when the viewport is slower, the clock never runs slow
        scene.render.fps_base = 1.0
        scene.render.fps = 30 if SLOW else 60                 # the keys are made for 60 fps (36 frames = 0.6 s); 30 only with the argument slow (half speed)
        # she faces +Y, her right is +X: the camera stands in front of her, a little to her right and above, looking at her
        r3d.view_perspective = 'PERSP'
        r3d.view_rotation = look_rotation((-0.50, -0.86, -0.10))
        r3d.view_distance = 3.6
        r3d.view_location = Vector((0.0, 0.0, 0.88))
        space.overlay.show_floor = False
        space.overlay.show_axis_x = False
        space.overlay.show_axis_y = False
        if LIGHT:
            space.overlay.show_overlays = False
            space.show_gizmo = False
        try:
            space.show_object_viewport_armature = False       # no bone spheres over her
        except Exception as e:
            print('armature filter:', e)
        STATE['step'] = 1
        return 1.0
    if s == 1 and LIGHT:                                      # light: one view only (no split)
        STATE['step'] = 3
        a.spaces.active.shading.type = 'MATERIAL'
        return 3.0
    if s == 1:                                                # split: left body, right side view
        STATE['step'] = 2                                     # whatever happens below, the next step runs
        n_before = len([x for x in w.screen.areas if x.type == 'VIEW_3D'])
        with bpy.context.temp_override(window=w, screen=w.screen, area=a):
            bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
        areas = sorted([x for x in w.screen.areas if x.type == 'VIEW_3D'], key=lambda x: x.x)
        print('3D views: %d -> %d' % (n_before, len(areas)))
        if len(areas) >= 2:
            STATE['body_area'], STATE['side_area'] = areas[0], areas[-1]
        return 1.5
    if s == 2:
        STATE['step'] = 3
        sa = STATE.get('side_area')
        if sa is not None:
            setup_side_area(sa)
        else:                                                 # the split did not work: one view with the whole body
            r3d.view_distance = 4.2
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
        STATE['samples'] = []
        print('run preview running (%s)' % ('slow motion, 30 fps' if SLOW else 'real time, 60 fps'))
        return 9.0
    if s == 4:                                                # measure: drawn frames per second and the clock time of one gait cycle
        STATE['step'] = 5
        period = 36
        try:
            act = next(o for o in bpy.data.objects if o.type == 'ARMATURE').animation_data.action
            period = int(round(act.frame_range[1] - act.frame_range[0]))
        except Exception:
            pass
        target = float(scene.render.fps)
        mean, n_cyc, drawn, dropped = cycle_report(period, target)
        speed = (period / target) / mean if mean > 0 else 0.0           # 1.0 = real time
        try:
            os.makedirs(os.path.dirname(FPS_FILE), exist_ok=True)
            with open(FPS_FILE, 'w') as fh:
                fh.write('viewport: %.1f frames drawn per second (target %d, %.0f %% of the frames are skipped); one gait cycle of %d frames takes %.3f s of clock time '
                         '(mean of %d cycles, target %.3f s) = %.2fx real time%s\n' % (
                             drawn, target, 100.0 * max(dropped, 0.0), period, mean, n_cyc, period / target, speed, ' (slow motion on request)' if SLOW else ''))
        except Exception as e:
            print('fps file:', e)
        print('viewport %.1f frames/s, cycle %.3f s (%.2fx)' % (drawn, mean, speed))
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
