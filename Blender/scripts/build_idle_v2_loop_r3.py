"""
Yoru - IDLE v2, round 3: the loop on A2 with clearer (still calm) motion and the polish: blink, follow-through of hair / ears / tail with offset
phases, a soft bust spring on the breath, a head with a tiny life of its own while the eyes keep looking ahead.  No gestures.
12 s at 30 fps: keys on every frame 0 .. 360, key 360 == key 0, the scene plays 0 .. 359.  Every layer is periodic in 12 s (whole numbers of
cycles, springs in their periodic steady state, blinks away from the seam), so the loop is seamless by construction.
Why 12 s instead of 8 s: three breaths of different length and depth (3.8 / 4.4 / 3.8 s) and two blinks at uneven intervals repeat less
obviously than the 8 s loop with two identical breaths; the seam is exact either way.

Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>).read(), ns); info = ns['bake_loop'](bpy.data.objects['Yoru_A2'])
Background:  blender -b <stage .blend> --python build_idle_v2_loop_r3.py -- <out .blend> [armature name, default Yoru_A2]

Layers (round 2 -> round 3 amplitudes are listed in P3; the user asked for about three times the motion of round 2):
  breath   three breaths per loop, quicker in than out, depths 1.00 / 0.85 / 0.94: the upper chest opens, the clavicles lift the shoulders
           (about 9 to 10 mm at the deepest breath), the spine takes back part of it so the upper body does not rock
  weight   the pelvis drifts about +-7 mm sideways and +-5 mm forward with a small roll / yaw; the spine takes back 60 %; the feet stay planted
  head     looks ahead, own motion below 2 deg; the eyes cancel 85 % of it (the gaze stays ahead)
  arms     hang from the shoulders and follow them 0.4 s later; the fingers relax a touch on the out-breath
  tail     slow travelling S-wave (12 s + 6 s + 4 s components) plus a follow-through of the pelvis drift 0.8 s later, tip about +-3 cm
  hair     every strand follows the head drift and the breath with a delay that grows towards the tip and differs from strand to strand
  ears     slow sway plus a lag behind the head turn, below 2 deg
  bust     a damped spring on the rise of the chest (periodic steady state): it lags on the in-breath and settles softly
  blink    two blinks per loop from blink_model.py (seed search: uneven intervals, none near the seam), shape key Fcl_EYE_Close
"""
import bpy, sys, os, math, re, time
import numpy as np
from mathutils import Vector, Quaternion, Euler

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_idle_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
L = {}
exec(compile(open(os.path.join(_HERE, 'build_idle_v2_lib.py'), encoding='utf-8').read(), os.path.join(_HERE, 'build_idle_v2_lib.py'), 'exec'), L)
BM = {}
exec(compile(open(os.path.join(_HERE, 'blink_model.py'), encoding='utf-8').read(), os.path.join(_HERE, 'blink_model.py'), 'exec'), BM)

FPS = 30
LOOP = 12.0
NF = int(round(FPS * LOOP))          # 360
TAU = 2.0 * math.pi
W = TAU / LOOP
HAIR_RE = re.compile(r'^J_Sec_Hair(\d+)_(\d+)$')

P3 = dict(
    breaths=((3.8, 1.00), (4.4, 0.85), (3.8, 0.94)),   # (seconds, depth); sum = LOOP.  Round 2: 2 x 4 s, depths 1.0 / 0.84
    breath_warp=0.15,                                   # > 0: the in-breath is quicker than the out-breath
    breath_lean=(0.0, -0.85, 0.85, 2.4),                # deg per full breath: hips, spine, chest, upperChest.  Round 2: (0, -0.3, 0.3, 0.8)
    # clavicles (deg, s).  Round 2: 2.6 deg (shoulders 3.4 mm).  6.5 deg gave 8.7 mm = only 2.0 px at 1080p in a Unity-like shoulder camera
    # (4.4 m, field of view 60 deg), at the edge of what one can see; 8.2 deg gives about 11 mm, still a calm breath.
    breath_clav=8.2, clav_lag=0.15,
    sway_x=0.0080, sway_y=0.0055, sway_z=0.0012,        # m.  Round 2: 0.0030 / 0.0020 / 0.0005
    # the whole body rises a little on the in-breath (knees straighten a touch, the feet stay planted).  From the shoulder camera the long
    # hair covers the shoulders and hangs from the head, so without this the breath moved the visible picture by only about 1 px.
    breath_rise=0.0035,
    drop_extra=0.0030,       # the hips sit 3 mm lower than in the still A2, so the standing knee never locks when the body rises (deficit 1.2 mm without)
    sway_roll=0.9, sway_yaw=1.1, spine_take=0.6,        # deg.  Round 2: 0.35 / 0.45
    head_pitch_breath=-0.45, head_pitch=0.65, head_yaw=1.1, head_roll=0.5,  # deg (below 2 deg from the middle).  Round 2: -0.25 / 0.35 / 0.6 / 0.3
    eye_follow=0.85,                                    # share of the head's own motion the eyes cancel
    arm_lag=0.20,                                       # s.  Round 2: 0.35; 0.40 let the arms rise only part of the way at the top of the breath
    finger_relax=4.0, finger_lag=0.5,                   # deg, s.  Round 2: 2.0
    tail_amp_y=(1.25, 2.5, 4.1, 5.5, 7.1, 8.5, 8.5, 10.0),  # deg sideways per joint (tip about +-3 cm).  Round 2: (0.5 .. 4.0)
    tail_amp_z=(2.5, 3.0, 2.0, 1.0, 0.0, 0.0, 0.0, 0.0),
    tail_phase=0.45, tail_follow=0.4, tail_follow_lag=0.8,
    hair_amp=0.32,                                      # deg per joint and unit; the tips reach just under 2 deg in all.  Round 2: 0.5 per joint, no follow-through
    hair_lag0=0.15, hair_lag_depth=0.12, hair_lag_chain=0.06,
    ear_amp=1.2, ear_follow=0.45, ear_lag=0.15,         # deg.  Round 2: 1.0
    bust_f0=1.1, bust_zeta=0.30, bust_gain=1.4,         # Hz, damping ratio, deg per unit of the spring lag
    blink_seed_start=1,
)


# ------------------------------------------------------------------ time functions (all periodic in LOOP)
def breath(t, p=P3):
    """0 (out) .. depth (in); breaths of different length and depth; at every boundary the value and the speed are 0, so it is smooth"""
    t = t % LOOP
    acc = 0.0
    for dur, depth in p['breaths']:
        if t < acc + dur:
            ph = (t - acc) / dur
            w = ph + p['breath_warp'] * math.sin(TAU * ph)
            return depth * (0.5 - 0.5 * math.cos(TAU * w))
        acc += dur
    return 0.0


def s_main(t):
    return (math.sin(W * t + 0.4) + 0.45 * math.sin(2 * W * t + 1.9) + 0.25 * math.sin(3 * W * t + 0.7)) / 1.45


def s_fwd(t):
    return (math.sin(W * t + 2.2) + 0.40 * math.sin(2 * W * t + 0.3) + 0.2 * math.sin(4 * W * t + 2.6)) / 1.35


def s_yaw(t):
    return (math.sin(W * t + 1.1) + 0.35 * math.sin(3 * W * t + 2.4) + 0.2 * math.sin(2 * W * t + 0.9)) / 1.3


def head_angles(t, p=P3):
    b = breath(t)
    pitch = p['head_pitch_breath'] * b + p['head_pitch'] * (math.sin(W * t + 2.0) + 0.4 * math.sin(3 * W * t + 0.5) + 0.2 * math.sin(5 * W * t + 1.4)) / 1.4
    yaw = p['head_yaw'] * (math.sin(W * t + 0.9) + 0.45 * math.sin(2 * W * t + 2.2) + 0.25 * math.sin(4 * W * t + 1.1)) / 1.5
    roll = p['head_roll'] * (math.sin(W * t + 2.6) + 0.35 * math.sin(3 * W * t + 1.2)) / 1.25
    return pitch, yaw, roll


def periodic_spring(x, f0, zeta, fps=FPS):
    """steady-state response y of a damped spring whose anchor follows the periodic signal x (samples over exactly one loop)"""
    x = np.asarray(x, dtype=float)
    n = len(x)
    X = np.fft.rfft(x)
    w = TAU * np.fft.rfftfreq(n, 1.0 / fps)
    w0 = TAU * f0
    H = w0 * w0 / (w0 * w0 - w * w + 2j * zeta * w0 * w)
    return np.fft.irfft(X * H, n)


def sample(fn):
    return np.array([fn(f / FPS) for f in range(NF)])


def interp_periodic(arr):
    arr = np.asarray(arr)

    def f(t):
        x = (t * FPS) % NF
        i = int(math.floor(x))
        u = x - i
        return float(arr[i % NF] * (1 - u) + arr[(i + 1) % NF] * u)
    return f


# ------------------------------------------------------------------ per-frame parameters
def frame_params(t, V0, C0, sec, shoulder_hist=None, p=P3):
    V = dict(V0)
    C = dict(C0)
    b = breath(t)
    bl = breath(t - p['clav_lag'])
    s1, s2, sy = s_main(t), s_fwd(t), s_yaw(t)
    V['shift'] = (V0['shift'][0] + p['sway_x'] * s1, V0['shift'][1] + p['sway_y'] * s2)
    V['drop'] = V0['drop'] + p.get('drop_extra', 0.0) - p['sway_z'] * (b - 0.5) - p.get('breath_rise', 0.0) * breath(t - 0.1)
    d_roll = -p['sway_roll'] * s1
    d_yaw = p['sway_yaw'] * sy
    k = p['spine_take']
    V['roll'] = (V0['roll'][0] + d_roll, V0['roll'][1] - 0.5 * k * d_roll, V0['roll'][2] - 0.3 * k * d_roll, V0['roll'][3] - 0.2 * k * d_roll)
    V['yaw'] = (V0['yaw'][0] + d_yaw, V0['yaw'][1] - 0.4 * k * d_yaw, V0['yaw'][2] - 0.35 * k * d_yaw, V0['yaw'][3] - 0.25 * k * d_yaw)
    V['lean'] = tuple(V0['lean'][i] + p['breath_lean'][i] * b for i in range(4))
    C['shoulder_drop_side'] = {s: v - p['breath_clav'] * bl for s, v in C0['shoulder_drop_side'].items()}
    hp, hy, hr = head_angles(t, p)
    C['head_pitch'] = C0['head_pitch'] + hp
    C['head_yaw'] = hy
    C['head_roll'] = hr
    if shoulder_hist is not None:
        C['wrist_extra'] = {s: shoulder_hist[s](t - p['arm_lag']) - shoulder_hist[s](t) for s in ('L', 'R')}
    bf = breath(t - p['finger_lag'])
    C['finger_curl'] = {s: {fn: tuple(c + p['finger_relax'] * (1.0 - bf) for c in cs) for fn, cs in C0['finger_curl'][s].items()} for s in ('L', 'R')}
    # tail: travelling S-wave + follow-through of the pelvis drift
    tail = []
    for i, d in enumerate(C0['tail']):
        ph = p['tail_phase'] * i
        wave = (math.sin(W * t - ph + 0.3) + 0.40 * math.sin(2 * W * t - 1.5 * ph + 1.2) + 0.15 * math.sin(3 * W * t - 2.0 * ph + 2.0)) / 1.35
        follow = -s_main(t - p['tail_follow_lag'] - 0.12 * i)
        ay = p['tail_amp_y'][i] * ((1.0 - p['tail_follow']) * wave + p['tail_follow'] * follow)
        az = p['tail_amp_z'][i] * math.sin(W * t - ph + 1.8)
        q = Euler((0.0, math.radians(ay), math.radians(az)), 'XYZ').to_quaternion()
        tail.append(tuple(q @ Vector(d).normalized()))
    C['tail'] = tail
    return V, C, b


def secondary_tables(head_pos, chest_z):
    """springs in their periodic steady state, driven by the head drift and the rise of the chest (per frame arrays)"""
    hx = np.asarray([v.x for v in head_pos])
    hy = np.asarray([v.y for v in head_pos])
    cz = np.asarray(chest_z)
    tables = {}
    # hair: the strands lag behind the head drift (relative motion = spring - anchor); per strand a little softer / stiffer
    for f0 in (0.9, 1.1, 1.3):
        tables[('hair_x', f0)] = periodic_spring(hx, f0, 0.25) - hx
        tables[('hair_y', f0)] = periodic_spring(hy, f0, 0.25) - hy
    tables['bust'] = periodic_spring(cz, P3['bust_f0'], P3['bust_zeta']) - cz
    return tables


def extra_rel(rig, t, f, sec, p=P3):
    rel = {}
    d2r = math.radians
    # hair: follow-through of the head drift (normalised) + a faint breath, delay grows towards the tip and differs per strand
    nx = sec['hair_norm_x']
    ny = sec['hair_norm_y']
    for name in rig.bones.keys():
        m = HAIR_RE.match(name)
        if not m:
            continue
        depth, chain = int(m.group(1)), int(m.group(2))
        f0 = (0.9, 1.1, 1.3)[chain % 3]
        lag = p['hair_lag0'] + p['hair_lag_depth'] * depth + p['hair_lag_chain'] * (chain % 5)
        tl = t - lag
        lat = sec['hair_x_f'][f0](tl) / nx
        fwd = sec['hair_y_f'][f0](tl) / ny
        brz = 0.35 * math.sin(W * tl * 2 + 0.7 * chain) + 0.25 * math.sin(3 * W * tl + 0.4 * chain)
        a = p['hair_amp'] * (0.6 + 0.25 * depth)
        rel[name] = Euler((d2r(a * (0.7 * fwd + 0.3 * brz + 0.25 * (breath(tl) - 0.5))), d2r(a * (0.75 * lat + 0.25 * brz)), 0.0), 'XYZ').to_quaternion()
    # ears: slow sway + a lag behind the head turn (the tip lags more)
    hp, hy, hr = head_angles(t - p['ear_lag'], p)
    hp2, hy2, hr2 = head_angles(t - 2 * p['ear_lag'], p)
    hpn, hyn, hrn = head_angles(t, p)
    for side, ph, sx in (('L', 0.6, -1.0), ('R', 2.1, 1.0)):
        sway = p['ear_amp'] * (math.sin(2 * W * t + ph) + 0.35 * math.sin(3 * W * t + 2 * ph) + 0.2 * math.sin(5 * W * t + ph)) / 1.3
        lag1 = p['ear_follow'] * (hy - hyn)
        lag2 = p['ear_follow'] * (hy2 - hyn)
        for k, fac, lg in ((1, 1.0, lag1), (2, 0.6, lag2)):
            n = 'J_Opt_%s_CatEar%d_01' % (side, k)
            if n in rig.bones:
                rel[n] = Euler((d2r(fac * sway * 0.6), d2r(sx * fac * 0.4 * sway), d2r(lg)), 'XYZ').to_quaternion()
    # bust: damped spring on the chest rise (lags on the in-breath, settles softly)
    bl = sec['bust_f'](t)
    for n, fac in (('J_Sec_L_Bust1', 1.0), ('J_Sec_R_Bust1', 1.0), ('J_Sec_L_Bust2', 0.6), ('J_Sec_R_Bust2', 0.6)):
        if n in rig.bones:
            rel[n] = Euler((d2r(-p['bust_gain'] * fac * bl), 0.0, 0.0), 'XYZ').to_quaternion()
    # eyes: cancel most of the head's own motion, the gaze stays ahead
    hp, hy, hr = head_angles(t, p)
    base = L['eul'](rx=L['COMMON2']['head_pitch'])
    cur = L['eul'](rx=L['COMMON2']['head_pitch'] + hp, ry=hr, rz=hy)
    counter = Quaternion().slerp(cur.inverted() @ base, p['eye_follow'])
    for n in (rig.H.get('leftEye'), rig.H.get('rightEye')):
        if n:
            rel[n] = counter
    return rel


def keyed_bones(rig):
    names = set(rig.H.values()) | set(rig.tail_bones)
    for n in rig.bones.keys():
        if HAIR_RE.match(n) or n.startswith('J_Opt_L_CatEar') or n.startswith('J_Opt_R_CatEar') or n.startswith('J_Sec_L_Bust') or n.startswith('J_Sec_R_Bust'):
            names.add(n)
    return [n for n in rig.order if n in names and not n.endswith('_end_01')]


def compute_frames(rig, key='A2', V0=None, C0=None, p=P3):
    V0 = dict(V0 or L['VARIANTS'][key])
    V0['arm_adj'] = V0.get('arm_adj', {})
    C0 = C0 or L['COMMON2']
    # pass 1: the torso alone -> shoulders, head drift, chest rise
    sh = {'L': [], 'R': []}
    head_pos = []
    for f in range(NF):
        V, C, b = frame_params(f / FPS, V0, C0, None, None, p)
        Q, hips_loc, D, Pp, diag = L['compute_pose'](rig, V, C)
        for s in ('L', 'R'):
            sh[s].append(Pp[rig.nm(s, 'UpperArm')].copy())
        head_pos.append(Pp[rig.H['head']].copy())
    # chest rise for the bust: the breath itself is the cleanest driver (the bones only rotate); 1 unit = a full breath
    chest = np.array([breath(f / FPS) for f in range(NF)])
    tables = secondary_tables(head_pos, chest)
    sec = {'hair_x_f': {f0: interp_periodic(tables[('hair_x', f0)]) for f0 in (0.9, 1.1, 1.3)},
           'hair_y_f': {f0: interp_periodic(tables[('hair_y', f0)]) for f0 in (0.9, 1.1, 1.3)},
           'bust_f': interp_periodic(tables['bust'] / max(1e-9, np.abs(tables['bust']).max())),
           'hair_norm_x': max(1e-9, max(np.abs(tables[('hair_x', f0)]).max() for f0 in (0.9, 1.1, 1.3))),
           'hair_norm_y': max(1e-9, max(np.abs(tables[('hair_y', f0)]).max() for f0 in (0.9, 1.1, 1.3)))}
    hist = {}
    for s in ('L', 'R'):
        arr = sh[s]

        def mk(arr=arr):
            def g(t):
                x = (t * FPS) % NF
                i = int(math.floor(x))
                u = x - i
                return arr[i % NF].lerp(arr[(i + 1) % NF], u)
            return g
        hist[s] = mk()
    frames = []
    for f in range(NF + 1):
        t = (f % NF) / FPS
        V, C, b = frame_params(t, V0, C0, sec, hist, p)
        C['extra_rel'] = extra_rel(rig, t, f % NF, sec, p)
        Q, hips_loc, D, Pp, diag = L['compute_pose'](rig, V, C)
        frames.append((Q, hips_loc, b, diag))
    return frames


# ------------------------------------------------------------------ blink
def choose_blinks(p=P3, tries=2000):
    """two single blinks in the loop: first one 1.0 .. 4.5 s, uneven intervals (also across the seam), none within 0.8 s of the seam"""
    for seed in range(p['blink_seed_start'], p['blink_seed_start'] + tries):
        groups = BM['schedule_groups'](seed, LOOP, None, 0.8, None)
        if len(groups) != 2 or any(len(g) != 1 for g in groups):
            continue
        b1, b2 = groups[0][0], groups[1][0]
        i1 = b2.start - b1.start
        i2 = LOOP - b2.start + b1.start
        if not (1.0 <= b1.start <= 4.5 and 3.5 <= i1 <= 7.5 and 3.5 <= i2 <= 8.5 and abs(i1 - i2) >= 1.2 and b2.end <= LOOP - 0.8):
            continue
        return seed, [b1, b2]
    raise RuntimeError('no blink seed found')


def blink_weights(blinks):
    return [BM['weight'](blinks, f / FPS) for f in range(NF + 1)]


# ------------------------------------------------------------------ baking
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


def _fill(fc, vals):
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


def bake_action(rig, frames, name='Yoru_Idle_v2', tail_scale=0.72):
    arm = rig.arm
    names = keyed_bones(rig)
    ad = arm.animation_data_create()
    old = ad.action
    if old is not None and old.name == name:
        old.name = name + '_previous'
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
    prev = {}
    series = {n: [] for n in names}
    for f in range(len(frames)):
        for n in names:
            q = frames[f][0][n]
            if n in prev and prev[n].dot(q) < 0.0:
                q = -q
            prev[n] = q
            series[n].append(q)
    for n in names:
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        for i in range(4):
            _fill(fcs[(dp, i)], [series[n][f][i] for f in range(len(frames))])
    dp = 'pose.bones["%s"].location' % rig.H['hips']
    for i in range(3):
        _fill(fcs[(dp, i)], [frames[f][1][i] for f in range(len(frames))])
    return act, old


def bake_blink(face_obj, weights, name='Yoru_Idle_v2_Blink'):
    sk = face_obj.data.shape_keys
    kb = sk.key_blocks['Fcl_EYE_Close']
    if sk.animation_data is None:
        sk.animation_data_create()
    old = sk.animation_data.action
    if old is not None and old.name == name:
        old.name = name + '_previous'
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    sk.animation_data.action = act
    kb.value = weights[0]
    kb.keyframe_insert('value', frame=0)
    fc = next(fc for fc in action_fcurves(act) if 'Fcl_EYE_Close' in fc.data_path)
    _fill(fc, weights)
    return act


def bake_loop(arm_obj, key='A2', set_scene=True):
    H = L['humanoid_map']()
    rig = L['Rig'](arm_obj, H)
    t0 = time.time()
    frames = compute_frames(rig, key)
    t1 = time.time()
    act, old = bake_action(rig, frames)
    seed, blinks = choose_blinks()
    weights = blink_weights(blinks)
    face = next(c for c in arm_obj.children if c.type == 'MESH' and c.data.shape_keys and 'Fcl_EYE_Close' in c.data.shape_keys.key_blocks)
    bact = bake_blink(face, weights)
    scene = bpy.context.scene
    if set_scene:
        scene.render.fps = FPS
        scene.render.fps_base = 1.0
        scene.frame_start, scene.frame_end = 0, NF - 1
    scene.frame_set(0)
    leg_def = max(max(fr[3]['leg_deficit'].values()) for fr in frames)
    return {'action': act.name, 'previous_action': old.name if old else None, 'blink_action': bact.name, 'frames': len(frames),
            'leg_reach_deficit_mm': round(leg_def * 1000.0, 2),
            'compute_s': round(t1 - t0, 1), 'bake_s': round(time.time() - t1, 1),
            'blink_seed': seed, 'blinks': [(round(b.start, 2), round(b.amp, 2), round(b.end - b.start, 3)) for b in blinks],
            'blink_intervals_s': (round(blinks[1].start - blinks[0].start, 2), round(LOOP - blinks[1].start + blinks[0].start, 2))}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    out = argv[0]
    name = argv[1] if len(argv) > 1 else 'Yoru_A2'
    info = bake_loop(bpy.data.objects[name])
    print('[idle_v2 loop r3]', info, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('[idle_v2 loop r3] saved', out, flush=True)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
