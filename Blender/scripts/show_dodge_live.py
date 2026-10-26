"""Starts the dodge preview in a normal Blender window:  blender.exe Yoru_DodgeWalk.blend --python show_dodge_live.py [-- light | rt]

The dodge is a ONE-SHOT clip (sprint burst out of the walk, 48 frames = 0.8 s).  It is played in place on a loop: the ground under her scrolls backwards at the pelvis speed of the dodge
(a planted shoe stays on its checker cell), and every loop ends with a short hold of the last pose.
Speed schedule (so the user sees it in real time AND slowly without touching anything): 3 loops REAL TIME (60 fps), 2 loops HALF speed (30 fps),
2 loops QUARTER speed (15 fps), then again.  The label in the corner says which speed is running.  Argument rt = real time only; light = one view, no overlays.
Real time = sync mode FRAME_DROP: frames are skipped when the viewport is slower, the clock never runs slow.
Text in the corner of every view: frame number, phase, ground speed of the pelvis, distance travelled, which foot is on the ground.
The view is set up in small steps from a timer, only while the 3D view really has a size and the window is not minimised (like show_run_live.py):
  1. EEVEE (the only engine that honours the alpha-cut of Yoru's "Onepiece" material),  2. the 3D view is split: LEFT front right, RIGHT side,  3. Material Preview, then play.
Keys in the window: Space = pause / play, then the arrow keys (mouse over a 3D view) step frame by frame, Shift + Left = back to frame 0.
"""
import bpy, os, sys, time, json
from mathutils import Vector, Matrix

LIGHT = 'light' in sys.argv
RT_ONLY = 'rt' in sys.argv
HOLD = 20                                                      # frames of the last pose that are held at the end of every loop
SCHEDULE = [(60, 'Echtzeit (1x)')] * 3 + [(30, 'Zeitlupe (1/2)')] * 2 + [(15, 'Zeitlupe (1/4)')] * 2
STATE = {'step': 0, 'tries': 0, 'frames': 0, 't0': None, 'side_area': None, 'samples': [], 'loop': 0, 'last_frame': -1, 'speed_label': SCHEDULE[0][1]}
BLEND_DIR = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ''
GAIT = {}
try:
    import glob
    with open(sorted(glob.glob(os.path.join(BLEND_DIR, '*_gait.json')))[0]) as fh:
        GAIT = json.load(fh)
except Exception as e:
    print('gait json not found:', e)
FPS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'dodge', 'live_fps.txt')


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


STANCE_NAMES = GAIT.get('stance_names') or ['Abdruck', 'Sprintschritt', 'Sprintschritt', 'Bremsschritt', 'Auslaufschritt']
SIDE_DE = {'R': 'rechts', 'L': 'links'}


def stance_at(f):
    """(index, stance) of the foot contact that holds frame f, or (None, None) in a flight"""
    for i, s in enumerate(GAIT.get('stances', [])):
        td = 0.0 if s['td'] is None else s['td']
        to = 1e9 if s['to'] is None else s['to']
        if td <= f <= to:
            return i, s
    return None, None


def phase_of(f):
    ph = GAIT.get('phases')
    if ph:
        txt = ph[0][1]
        for f0, tx in ph:
            if f >= f0:
                txt = tx
        return txt
    if not GAIT.get('stances'):
        return ''
    i, s = stance_at(f)
    if s is None:
        return 'FLUG'
    name = STANCE_NAMES[i] if i < len(STANCE_NAMES) else 'Schritt'
    tail = ', geht in Run oder Joggen über' if s['to'] is None else ''
    return '%s, %s%s' % (name, SIDE_DE[s['side']], tail)


def foot_down(side, f):
    for w in GAIT.get('ground', {}).get(side, []):
        if w[0] <= f <= w[1]:
            return True
    for s in GAIT.get('stances', []):
        td = 0.0 if s['td'] is None else s['td']
        to = 1e9 if s['to'] is None else s['to']
        if s['side'] == side and td <= f <= to:
            return True
    return False


def draw_label():
    try:
        import blf
        scene = bpy.context.scene
        n = int(GAIT.get('frames', 48))
        f = min(max(int(scene.frame_current), 0), n - 1)
        held = scene.frame_current > n - 1
        lines = [GAIT.get('title', 'Ausweichen im Gehen') + '   Bild %02d / %d%s' % (f, n - 1, '  (Pause am Ende)' if held else ''), phase_of(f)]
        sp = GAIT.get('speed_per_frame')
        tr = GAIT.get('travel_per_frame')
        if sp and tr:
            lines.append('Tempo %.1f m/s    Weg %.2f m' % (sp[f], tr[f]))
        lines.append('Fuss rechts: %s    Fuss links: %s' % ('Boden' if foot_down('R', f) else 'Luft', 'Boden' if foot_down('L', f) else 'Luft'))
        lines.append(STATE['speed_label'])
        reg = bpy.context.region
        font = 0
        for i, text in enumerate(lines):
            try:
                blf.size(font, 20 if i == 0 else 17)
            except TypeError:
                blf.size(font, 20 if i == 0 else 17, 72)
            blf.color(font, 1.0, 0.86, 0.35, 1.0) if i in (0, 4) else blf.color(font, 0.92, 0.95, 1.0, 1.0)
            blf.position(font, 80, reg.height - 130 - i * 26, 0)
            blf.draw(font, text)
    except Exception as e:
        if not STATE.get('draw_err'):
            STATE['draw_err'] = True
            print('label draw failed:', e)


def on_frame(scene, *args):
    STATE['frames'] += 1
    STATE['samples'].append((time.perf_counter(), scene.frame_current))
    f = scene.frame_current
    if f < STATE['last_frame']:                                # the loop wrapped: next entry of the speed schedule
        STATE['loop'] += 1
        if not RT_ONLY:
            fps, label = SCHEDULE[STATE['loop'] % len(SCHEDULE)]
            scene.render.fps = fps
            STATE['speed_label'] = label
    STATE['last_frame'] = f


def window_minimized():
    """True while the Blender window of this process is minimised (Windows only): changing engine / shading / areas of a minimised window crashed Blender
    when it was restored, so everything waits until the window is open."""
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
    rv.view_distance = 8.0
    rv.view_location = Vector((0.0, -0.05, 0.80))
    sp.lens = 100.0
    sp.overlay.show_overlays = False
    sp.show_gizmo = False
    sp.shading.type = 'MATERIAL'
    try:
        sp.show_object_viewport_armature = False
    except Exception:
        pass


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
        n = int(GAIT.get('frames', 48))
        scene.frame_start = 0
        scene.frame_end = n - 1 + HOLD                        # the clip, then a hold of the last pose
        scene.frame_set(0)
        scene.sync_mode = 'FRAME_DROP'                        # real time: frames are skipped when the viewport is slower, the clock never runs slow
        scene.render.fps_base = 1.0
        scene.render.fps = 60                                 # the keys are made for 60 fps (the schedule switches to 30 / 15 later)
        r3d.view_perspective = 'PERSP'
        r3d.view_rotation = look_rotation((-0.50, -0.86, -0.10))
        r3d.view_distance = 4.0
        r3d.view_location = Vector((0.0, 0.0, 0.84))
        space.overlay.show_floor = False
        space.overlay.show_axis_x = False
        space.overlay.show_axis_y = False
        space.overlay.show_overlays = False                   # no info text over her, only our label
        space.show_gizmo = False
        try:
            space.show_object_viewport_armature = False       # no bone spheres over her
        except Exception as e:
            print('armature filter:', e)
        STATE['step'] = 1
        return 1.0
    if s == 1 and LIGHT:
        STATE['step'] = 3
        a.spaces.active.shading.type = 'MATERIAL'
        return 3.0
    if s == 1:                                                # split: left front right, right side
        STATE['step'] = 2
        with bpy.context.temp_override(window=w, screen=w.screen, area=a):
            bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
        areas = sorted([x for x in w.screen.areas if x.type == 'VIEW_3D'], key=lambda x: x.x)
        print('3D views: %d' % len(areas))
        if len(areas) >= 2:
            STATE['body_area'], STATE['side_area'] = areas[0], areas[-1]
        return 1.5
    if s == 2:
        STATE['step'] = 3
        sa = STATE.get('side_area')
        if sa is not None:
            setup_side_area(sa)
        else:                                                 # the split did not work: one view with the whole body
            r3d.view_distance = 4.6
        for ar in w.screen.areas:                             # Material Preview in EVERY 3D view (the solid mode shows a grey fake of the materials)
            if ar.type == 'VIEW_3D':
                ar.spaces.active.shading.type = 'MATERIAL'
                ar.spaces.active.overlay.show_overlays = False
                ar.spaces.active.show_gizmo = False
        return 4.0
    if s == 3:
        STATE['step'] = 4
        try:
            STATE['draw_handle'] = bpy.types.SpaceView3D.draw_handler_add(draw_label, (), 'WINDOW', 'POST_PIXEL')
        except Exception as e:
            print('draw handler:', e)
        for area in w.screen.areas:
            area.tag_redraw()
        bpy.app.handlers.frame_change_post.append(on_frame)
        with bpy.context.temp_override(window=w, screen=w.screen, area=a):
            bpy.ops.screen.animation_play()
        STATE['t0'] = time.time()
        STATE['frames'] = 0
        STATE['samples'] = []
        print('dodge preview running (real time first, then half and quarter speed)')
        return 9.0
    if s == 4:                                                # measure the first seconds (real time part): drawn frames per second
        STATE['step'] = 5
        sm = STATE['samples']
        if len(sm) > 4:
            dur = sm[-1][0] - sm[0][0]
            drawn = (len(sm) - 1) / dur if dur > 0 else 0.0
            try:
                os.makedirs(os.path.dirname(FPS_FILE), exist_ok=True)
                with open(FPS_FILE, 'w') as fh:
                    fh.write('viewport: %.1f frames drawn per second in the first %.1f s (target %d)\n' % (drawn, dur, scene.render.fps))
            except Exception as e:
                print('fps file:', e)
            print('viewport %.1f frames/s' % drawn)
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
