"""Plays the slides of Yoru_Run_Kritik_Stufe1.blend (made by build_run_kritik.py) one after the other in a normal Blender window, in REAL TIME:
  blender.exe Yoru_Run_Kritik_Stufe1.blend --python show_run_kritik_live.py [-- hold=N] [-- shots=<dir>]
The run keeps playing at 60 fps (frame dropping, never slower than the clock); every slide shows the measured problems of the critique as coloured
overlay (red = as it is, green = the plan) in its own camera view.  Slide 4 (foot twitch) runs at a quarter of the speed, the text says so.
  hold=N    stay on slide N (1 .. 9) instead of cycling
  shots=D   test mode: save a screenshot of every slide into directory D and quit
The 3D view is maximised and set up in small steps from a timer, only while the window really has a size (a minimised window has none)."""
import bpy, json, os, sys, time

ARGV = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
HOLD = next((int(a.split('=')[1]) for a in ARGV if a.startswith('hold=')), 0)
SHOTS = next((a.split('=', 1)[1] for a in ARGV if a.startswith('shots=')), '')
STATE = {'step': 0, 'tries': 0, 'slide': -1, 'samples': [], 'errors': 0, 't_slide': 0.0}
FPS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'run', 'live_fps_kritik.txt')


def find_view3d():
    best = (None, None)
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D' and (best[1] is None or a.width * a.height > best[1].width * best[1].height):
                best = (w, a)
    return best


def window_minimized():
    """True while the Blender window of this process is minimised (Windows only): changing a minimised window crashed Blender when it was restored"""
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


def on_frame(scene, *args):
    STATE['samples'].append((time.perf_counter(), scene.frame_current))


def apply_slide(i, w, a):
    """show slide i: its collection, its camera, its speed (a quarter speed slide restarts the playback)"""
    scene = bpy.context.scene
    slides = json.loads(scene['kritik'])
    sd = slides[i]
    lc = bpy.context.view_layer.layer_collection
    for j, other in enumerate(slides):
        lc.children[other['name']].hide_viewport = (j != i)
    scene.camera = bpy.data.objects[sd['camera']]
    floor = bpy.data.objects.get('Floor_scrolling')
    if floor is not None:
        floor.hide_viewport = not sd.get('floor', True)
    if scene.render.fps != sd['fps']:
        scene.render.fps = sd['fps']
        try:
            with bpy.context.temp_override(window=w, screen=w.screen, area=a):
                if bpy.context.screen.is_animation_playing:
                    bpy.ops.screen.animation_cancel(restore_frame=False)
                    bpy.ops.screen.animation_play()
        except Exception as e:
            print('restart playback:', e)
    STATE['slide'] = i
    STATE['t_slide'] = time.time()
    for ar in w.screen.areas:
        ar.tag_redraw()
    print('slide %d / %d: %s (%d fps)' % (i + 1, len(slides), sd['name'], sd['fps']))
    return sd


def shot(w, a, path):
    try:
        with bpy.context.temp_override(window=w, screen=w.screen, area=a):
            bpy.ops.screen.screenshot_area(filepath=path)
        print('screenshot', path)
    except Exception as e:
        print('screenshot_area failed:', e)
        try:
            with bpy.context.temp_override(window=w, screen=w.screen):
                bpy.ops.screen.screenshot(filepath=path)
        except Exception as e2:
            print('screenshot failed:', e2)


def _tick():
    if STATE['step'] < 3 and window_minimized():
        return 2.0
    w, a = find_view3d()
    STATE['tries'] += 1
    if a is None or a.width < 200 or a.height < 200:
        return 1.0 if STATE['tries'] < 300 else None
    scene = bpy.context.scene
    slides = json.loads(scene['kritik'])
    s = STATE['step']
    if s == 0:
        try:
            scene.render.engine = 'BLENDER_EEVEE'
        except TypeError as e:
            print('engine:', str(e)[:200])
        scene.frame_set(0)
        scene.sync_mode = 'FRAME_DROP'                        # real time: frames are skipped when the viewport is slower, the clock never runs slow
        scene.render.fps_base = 1.0
        scene.render.fps = 60
        sp = a.spaces.active
        sp.shading.type = 'MATERIAL'
        sp.overlay.show_overlays = False
        sp.show_gizmo = False
        try:
            sp.show_object_viewport_armature = False
        except Exception:
            pass
        STATE['step'] = 1
        return 1.0
    if s == 1:                                                # a big picture: the 3D view alone, without the other editors and without the panels
        STATE['step'] = 2
        try:
            with bpy.context.temp_override(window=w, screen=w.screen, area=a):
                bpy.ops.screen.screen_full_area(use_hide_panels=True)
        except Exception as e:
            print('maximise:', e)
        return 1.5
    if s == 2:                                                # first slide, camera view fitted to the window, start the playback
        STATE['step'] = 3
        sp = a.spaces.active
        r3d = sp.region_3d
        sp.shading.type = 'MATERIAL'
        sp.overlay.show_overlays = False
        sp.show_gizmo = False
        r3d.view_perspective = 'CAMERA'
        apply_slide(max(HOLD - 1, 0), w, a)
        try:
            region = next(r for r in a.regions if r.type == 'WINDOW')
            with bpy.context.temp_override(window=w, screen=w.screen, area=a, region=region):
                bpy.ops.view3d.view_center_camera()           # the camera frame fills the window
        except Exception as e:
            print('fit camera:', e)
        bpy.app.handlers.frame_change_post.append(on_frame)
        with bpy.context.temp_override(window=w, screen=w.screen, area=a):
            bpy.ops.screen.animation_play()
        print('run kritik view running, real time, 60 fps')
        STATE['t0'] = time.time()
        return 2.0
    if s == 3:                                                # slideshow / test shots / hold
        if SHOTS:
            return shots_tick(w, a, slides)
        if STATE['t0'] and time.time() - STATE['t0'] > 9.0 and 'measured' not in STATE:
            STATE['measured'] = True
            measure(scene)
        if HOLD:
            return 5.0
        sd = slides[STATE['slide']]
        if time.time() - STATE['t_slide'] >= sd['dwell']:
            apply_slide((STATE['slide'] + 1) % len(slides), w, a)
        return 0.5
    return None


def measure(scene):
    """clock time of the gait cycles while slide 1 plays at 60 fps (the first 9 s)"""
    sm = STATE['samples']
    if len(sm) < 4:
        return
    period = 36
    marks = []
    for (t0, f0), (t1, f1) in zip(sm, sm[1:]):
        if f1 // period != f0 // period or f1 < f0:
            marks.append(t1)
    dur = sm[-1][0] - sm[0][0]
    drawn = (len(sm) - 1) / dur if dur > 0 else 0.0
    if len(marks) >= 2:
        mean = (marks[-1] - marks[0]) / (len(marks) - 1)
        txt = 'critique view: %.1f frames drawn per second, one gait cycle of %d frames takes %.3f s of clock time (mean of %d cycles, target 0.600 s) = %.2fx real time\n' % (
            drawn, period, mean, len(marks) - 1, 0.6 / mean)
        try:
            with open(FPS_FILE, 'w') as fh:
                fh.write(txt)
        except Exception as e:
            print('fps file:', e)
        print(txt.strip())


def shots_tick(w, a, slides):
    """test mode: every slide gets its screenshot after 3 s, then Blender quits"""
    os.makedirs(SHOTS, exist_ok=True)
    i = STATE['slide']
    if time.time() - STATE['t_slide'] < 3.0:
        return 0.5
    shot(w, a, os.path.join(SHOTS, 'live_%d_%s.png' % (i + 1, slides[i]['name'])))
    if i + 1 >= len(slides):
        bpy.ops.wm.quit_blender()
        return None
    apply_slide(i + 1, w, a)
    return 0.5


def tick():
    """an error in one step must not stop the others: the step counter is advanced before the work, the timer runs on"""
    try:
        return _tick()
    except Exception:
        import traceback
        traceback.print_exc()
        STATE['errors'] += 1
        return 2.0 if STATE['errors'] < 8 else None


bpy.app.timers.register(tick, first_interval=2.0)
