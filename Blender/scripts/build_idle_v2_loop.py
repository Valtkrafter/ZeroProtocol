"""
Yoru - IDLE v2, round 2: first BLOCKOUT of the idle loop on the stance A2 (soft curves, no gestures).
8 s loop at 30 fps (the old idle used 30 fps): keys on every frame 0 .. 240, key 240 == key 0, the scene plays 0 .. 239.
Every movement is periodic in the 8 s (whole numbers of cycles), so the loop is seamless by construction.

Live (MCP):  ns = {}; exec(open(<this file>).read(), ns); info = ns['bake_loop'](bpy.data.objects['Yoru_A2'])
Background:  blender -b <stage .blend> --python build_idle_v2_loop.py -- <out .blend> [armature name, default Yoru_A2]

Layers (several harmonics with offsets, no pure sine waves):
  breath  2 breaths per loop (4 s each), quicker in (about 42 %) than out, the 2nd a little shallower: the chest and the upper chest lift,
          the clavicles rise 0.15 s later, the pelvis does not take part, the head keeps still (the neck absorbs it)
  weight  the pelvis drifts a few millimetres (sideways +-3 mm, forward +-2 mm) with a tiny roll / yaw; the spine takes back most of it,
          the feet stay planted (two-bone IK to fixed feet: no sliding)
  head    looks straight ahead, counter-movements below 1 deg
  arms    hang from the shoulders and follow them 0.35 s later (wrist target = shoulder position 0.35 s ago + offset), the fingers relax
          a touch on the out-breath
  tail    slow travelling S-wave from the base to the tip (one sway per loop plus a smaller harmonic), tip about +-2.5 cm, no wagging
  hair, ears, bust  very small, delayed
"""
import bpy, sys, os, math, re, time
from mathutils import Vector, Quaternion, Euler

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else r'C:\Users\valen\ZeroProtocol\Blender\scripts',
                   'build_idle_v2_lib.py')
if not os.path.exists(LIB):
    LIB = r'C:\Users\valen\ZeroProtocol\Blender\scripts\build_idle_v2_lib.py'
L = {}
exec(compile(open(LIB, encoding='utf-8').read(), LIB, 'exec'), L)

FPS = 30
LOOP = 8.0
NF = int(round(FPS * LOOP))          # 240
TAU = 2.0 * math.pi
W = TAU / LOOP
HAIR_RE = re.compile(r'^J_Sec_Hair(\d+)_(\d+)$')

P = dict(
    breath_period=4.0, breath_warp=0.15,           # warp > 0: the in-breath is quicker than the out-breath
    breath_depth2=0.84,                            # the second breath of the loop is a little shallower
    # deg per full breath: hips, spine, chest, upperChest (+ = the top tips back).  The lower spine gives back what the upper chest takes,
    # so the ribcage opens and lifts without rocking the whole upper body back (a first try with 0.35 / 0.8 / 1.2 moved the head 11 mm)
    breath_lean=(0.0, -0.3, 0.3, 0.8),
    breath_clav=2.6, clav_lag=0.15,                # clavicles rise (deg; the shoulders go up about 3 mm) and their delay (s)
    sway_x=0.0030, sway_y=0.0020, sway_z=0.0005,   # pelvis drift (m)
    sway_roll=0.35, sway_yaw=0.45,                 # pelvis roll / yaw (deg)
    spine_take=0.6,                                # share of the pelvis roll / yaw the spine turns back (the chest stays calmer)
    head_pitch_breath=-0.25, head_pitch=0.35, head_yaw=0.6, head_roll=0.3,
    arm_lag=0.35,                                  # s
    finger_relax=2.0, finger_lag=0.5,              # deg more curl on the out-breath, delay (s)
    tail_amp_y=(0.5, 1.0, 1.6, 2.2, 2.8, 3.4, 3.4, 4.0),   # deg sideways swing per tail joint (base .. tip)
    tail_amp_z=(1.0, 1.2, 0.8, 0.4, 0.0, 0.0, 0.0, 0.0),   # deg turn of the first joints (they point backwards)
    tail_phase=0.45,                               # rad per joint: the wave travels from the base to the tip
    hair_amp=0.5, ear_amp=1.0, bust_k=3.0, bust_lag=0.2,
)


def breath(t, p=P):
    """0 (out) .. 1 (in), two breaths per loop, the in-breath quicker, the second breath of the loop shallower"""
    ph = (t / p['breath_period']) % 1.0
    w = ph + p['breath_warp'] * math.sin(TAU * ph)
    b = 0.5 - 0.5 * math.cos(TAU * w)
    depth = 0.5 * (1.0 + p['breath_depth2']) + 0.5 * (1.0 - p['breath_depth2']) * math.cos(W * (t - 1.7))
    return b * depth


def s_main(t):
    """slow drift of the weight: one cycle per loop plus two smaller harmonics (normalised to about +-1)"""
    return (math.sin(W * t + 0.4) + 0.30 * math.sin(2 * W * t + 1.9) + 0.15 * math.sin(3 * W * t + 0.7)) / 1.25


def frame_params(t, V0, C0, shoulder_hist=None, p=P):
    """the variant and the common parameters at the time t (seconds)"""
    V = dict(V0)
    C = dict(C0)
    b = breath(t)
    bl = breath(t - p['clav_lag'])
    s1 = s_main(t)
    s2 = (math.sin(W * t + 2.2) + 0.35 * math.sin(2 * W * t + 0.3)) / 1.2
    yaw_n = (math.sin(W * t + 1.1) + 0.3 * math.sin(3 * W * t + 2.4)) / 1.15
    # --- pelvis drift (feet stay planted through the leg IK)
    V['shift'] = (V0['shift'][0] + p['sway_x'] * s1, V0['shift'][1] + p['sway_y'] * s2)
    V['drop'] = V0['drop'] - p['sway_z'] * (b - 0.5)
    d_roll = -p['sway_roll'] * s1
    d_yaw = p['sway_yaw'] * yaw_n
    k = p['spine_take']
    V['roll'] = (V0['roll'][0] + d_roll, V0['roll'][1] - 0.5 * k * d_roll, V0['roll'][2] - 0.3 * k * d_roll, V0['roll'][3] - 0.2 * k * d_roll)
    V['yaw'] = (V0['yaw'][0] + d_yaw, V0['yaw'][1] - 0.4 * k * d_yaw, V0['yaw'][2] - 0.35 * k * d_yaw, V0['yaw'][3] - 0.25 * k * d_yaw)
    bl4 = p['breath_lean']
    V['lean'] = tuple(V0['lean'][i] + bl4[i] * b for i in range(4))
    # --- clavicles rise with the breath, a moment later
    C['shoulder_drop_side'] = {s: v - p['breath_clav'] * bl for s, v in C0['shoulder_drop_side'].items()}
    # --- head: still, tiny counter-movements
    C['head_pitch'] = C0['head_pitch'] + p['head_pitch_breath'] * b + p['head_pitch'] * (math.sin(W * t + 2.0) + 0.4 * math.sin(2 * W * t + 0.5)) / 1.3
    C['head_yaw'] = p['head_yaw'] * (math.sin(W * t + 0.9) + 0.4 * math.sin(3 * W * t + 1.7)) / 1.3
    C['head_roll'] = p['head_roll'] * (math.sin(W * t + 2.6) + 0.3 * math.sin(2 * W * t + 1.2)) / 1.2
    # --- arms follow the shoulders with a delay
    if shoulder_hist is not None:
        C['wrist_extra'] = {s: shoulder_hist[s](t - p['arm_lag']) - shoulder_hist[s](t) for s in ('L', 'R')}
    # --- fingers relax a touch on the out-breath
    bf = breath(t - p['finger_lag'])
    C['finger_curl'] = {s: {fn: tuple(c + p['finger_relax'] * (1.0 - bf) for c in cs) for fn, cs in C0['finger_curl'][s].items()} for s in ('L', 'R')}
    # --- tail: travelling S-wave
    tail = []
    for i, d in enumerate(C0['tail']):
        ph = p['tail_phase'] * i
        ay = p['tail_amp_y'][i] * (math.sin(W * t - ph + 0.3) + 0.35 * math.sin(2 * W * t - 1.5 * ph + 1.2)) / 1.2
        az = p['tail_amp_z'][i] * math.sin(W * t - ph + 1.8)
        q = Euler((0.0, math.radians(ay), math.radians(az)), 'XYZ').to_quaternion()
        tail.append(tuple(q @ Vector(d).normalized()))
    C['tail'] = tail
    return V, C, b


def extra_rel(rig, t, p=P):
    """small rotations of hair, ears and bust relative to their parents"""
    rel = {}
    deg = math.radians
    for name in rig.bones.keys():
        m = HAIR_RE.match(name)
        if m:
            depth, chain = int(m.group(1)), int(m.group(2))
            a = p['hair_amp']
            rel[name] = Euler((deg(a * math.sin(2 * W * t + 0.6 * chain - 0.35 * depth)),
                               deg(0.6 * a * math.sin(W * t + 0.4 * chain - 0.3 * depth)), 0.0), 'XYZ').to_quaternion()
    for side, ph in (('L', 0.6), ('R', 2.1)):
        e = p['ear_amp'] * (math.sin(2 * W * t + ph) + 0.3 * math.sin(3 * W * t + 2 * ph)) / 1.2
        for k, f in ((1, 1.0), (2, 0.6)):
            n = 'J_Opt_%s_CatEar%d_01' % (side, k)
            if n in rig.bones:
                rel[n] = Euler((deg(f * e), 0.0, 0.0), 'XYZ').to_quaternion()
    lag = breath(t) - breath(t - p['bust_lag'])
    for n in ('J_Sec_L_Bust1', 'J_Sec_R_Bust1'):
        if n in rig.bones:
            rel[n] = Euler((deg(-p['bust_k'] * lag), 0.0, 0.0), 'XYZ').to_quaternion()
    return rel


def keyed_bones(rig):
    names = set(rig.H.values()) | set(rig.tail_bones)
    for n in rig.bones.keys():
        if HAIR_RE.match(n) or n.startswith('J_Opt_L_CatEar') or n.startswith('J_Opt_R_CatEar') or n in ('J_Sec_L_Bust1', 'J_Sec_R_Bust1'):
            names.add(n)
    return [n for n in rig.order if n in names and not n.endswith('_end_01')]


def periodic_interp(values):
    """function t -> Vector, periodic over the loop, from per-frame samples (frames 0 .. NF-1)"""
    def f(t):
        x = (t * FPS) % NF
        i = int(math.floor(x))
        u = x - i
        return values[i % NF].lerp(values[(i + 1) % NF], u)
    return f


def compute_frames(rig, key='A2', V0=None, C0=None, p=P):
    V0 = dict(V0 or L['VARIANTS'][key])
    V0['arm_adj'] = V0.get('arm_adj', {})
    C0 = C0 or L['COMMON2']
    # pass 1: where the shoulders are on every frame (the arms do not change the torso)
    sh = {'L': [], 'R': []}
    for f in range(NF):
        V, C, b = frame_params(f / FPS, V0, C0, None, p)
        C['extra_rel'] = extra_rel(rig, f / FPS, p)
        Q, hips_loc, D, Pp, diag = L['compute_pose'](rig, V, C)
        for s in ('L', 'R'):
            sh[s].append(Pp[rig.nm(s, 'UpperArm')].copy())
    hist = {s: periodic_interp(sh[s]) for s in ('L', 'R')}
    # pass 2: the full pose with the delayed arms; frame NF repeats frame 0
    frames = []
    for f in range(NF + 1):
        t = (f % NF) / FPS
        V, C, b = frame_params(t, V0, C0, hist, p)
        C['extra_rel'] = extra_rel(rig, t, p)
        Q, hips_loc, D, Pp, diag = L['compute_pose'](rig, V, C)
        frames.append((Q, hips_loc, b, diag))
    return frames


def action_fcurves(action):
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


def bake_action(rig, frames, name='Yoru_Idle_v2_A2', tail_scale=0.72):
    """keys on every frame through the f-curves (fast), LINEAR, plus a Cycles modifier on every curve (endless loop)"""
    arm = rig.arm
    names = keyed_bones(rig)
    ad = arm.animation_data_create()
    old = ad.action
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad.action = act
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    Q0, loc0 = frames[0][0], frames[0][1]
    for n in names:
        pb = arm.pose.bones[n]
        pb.rotation_quaternion = Q0[n]
        pb.keyframe_insert('rotation_quaternion', frame=0)
    pbh = arm.pose.bones[rig.H['hips']]
    pbh.location = loc0
    pbh.keyframe_insert('location', frame=0)
    if rig.tail_bones:
        arm.pose.bones[rig.tail_bones[0]].scale = Vector((tail_scale,) * 3)
    fcs = {(fc.data_path, fc.array_index): fc for fc in action_fcurves(act)}
    nfr = len(frames)
    prev = {}
    series = {n: [] for n in names}
    for f in range(nfr):                                        # keep the quaternion signs continuous
        for n in names:
            q = frames[f][0][n]
            if n in prev and prev[n].dot(q) < 0.0:
                q = -q
            prev[n] = q
            series[n].append(q)

    def fill(fc, vals):
        kp = fc.keyframe_points
        if len(kp) < len(vals):
            kp.add(len(vals) - len(kp))
        co = []
        for f, v in enumerate(vals):
            co.extend((float(f), float(v)))
        kp.foreach_set('co', co)
        for k in kp:
            k.interpolation = 'LINEAR'
        fc.update()
        if not any(m.type == 'CYCLES' for m in fc.modifiers):
            fc.modifiers.new('CYCLES')

    for n in names:
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        for i in range(4):
            fill(fcs[(dp, i)], [series[n][f][i] for f in range(nfr)])
    dp = 'pose.bones["%s"].location' % rig.H['hips']
    for i in range(3):
        fill(fcs[(dp, i)], [frames[f][1][i] for f in range(nfr)])
    return act, old


def bake_loop(arm_obj, key='A2', set_scene=True):
    H = L['humanoid_map']()
    rig = L['Rig'](arm_obj, H)
    t0 = time.time()
    frames = compute_frames(rig, key)
    t1 = time.time()
    act, old = bake_action(rig, frames)
    scene = bpy.context.scene
    if set_scene:
        scene.render.fps = FPS
        scene.render.fps_base = 1.0
        scene.frame_start, scene.frame_end = 0, NF - 1
    scene.frame_set(0)
    return {'action': act.name, 'frames': len(frames), 'compute_s': round(t1 - t0, 1), 'bake_s': round(time.time() - t1, 1),
            'breath_max': round(max(fr[2] for fr in frames), 3)}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    out = argv[0]
    name = argv[1] if len(argv) > 1 else 'Yoru_A2'
    info = bake_loop(bpy.data.objects[name])
    print('[idle_v2 loop]', info, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('[idle_v2 loop] saved', out, flush=True)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
