"""
Yoru - IDLE v2, round 7: more life in EARS, TAIL and HAIR (the user: "Ohren und Schwanz leicht wigglen, Haare ganz leicht im Wind, es soll
geil aussehen").  Body, arms, face and blink stay bit for bit; only the ear, tail and hair curves of the action change.

  hair   a light, steady breeze from her front right (blows towards the back left): every strand leans a little downwind and soft waves travel
         from the root to the tip (periods 3 / 2.4 / 1.5 s, phase lag per depth and across the head in the wind direction), plus two gentle
         gusts per loop.  The wind never blows 'upwind' (the deflection stays >= 0), and per chain the component that would push a strand into
         the body is removed, so strands only move away from shoulders, gear and face.  The fringe gets a quarter of the wind (the eyes stay free).
         Added on top of the round 3 motion: Q = Q_round6 @ Q_wind (Q_wind = R^-1 rel_wind R, rel about the axis strand x wind).
  ears   single flicks, never both ears at once, at uneven times (a quick swivel of the opening outwards with a small tilt back: in 2 frames,
         back with a damped spring and a small overshoot; one double flick), plus slow 'listening' turns (an ear turns a few degrees, holds,
         turns back).  On top of the round 6 ears (B angle + round 3 follow-through): Q = Q_round6 @ Q_event.
  tail   the round 3 S-wave with more swing in the lower half (the upper tail stays close to the rump: 8 mm clearance there), a quicker partial
         wave in the tip (3 s), a slow curl-in / curl-out of the tip and one small tip flick per loop.  Recomputed from the joint directions
         (the tail basis rotations depend only on them: Q_i = R^-1 rot_(i-1)^-1 rot_i R).
  Everything is periodic in the 12 s loop (frame 360 == frame 0); events are placed inside the loop and settle before the seam.
Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>).read(), ns); print(ns['bake_dynamics'](bpy.data.objects['Yoru_A2']))
Background:  blender -b <stage .blend> --python build_idle_v2_dynamics_r7.py -- <out .blend> [armature, default Yoru_A2]
"""
import bpy, sys, os, math, re
from mathutils import Vector, Quaternion, Euler, Matrix

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_idle_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'


def _load(name):
    ns = {'__file__': os.path.join(_HERE, name)}
    exec(compile(open(os.path.join(_HERE, name), encoding='utf-8').read(), os.path.join(_HERE, name), 'exec'), ns)
    return ns


R3 = _load('build_idle_v2_loop_r3.py')
L = R3['L']
NF, FPS, LOOP = R3['NF'], R3['FPS'], R3['LOOP']
TAU = 2.0 * math.pi
W = TAU / LOOP
HAIR_RE = re.compile(r'^J_Sec_Hair(\d+)_(\d+)$')
d2r = math.radians

P7 = dict(
    # ---- wind in the hair
    # first try: from the front right towards the back LEFT and BACK, 2.4 deg lean, waves +-2.3 deg: the tips moved only 1 to 7 mm more
    # than before and mostly along the view of the shoulder camera (invisible).  Now mostly sideways (from her right) and stronger waves.
    wind_dir=(-1.0, -0.45, 0.0),             # where the breeze blows TO (from her right front towards her left, a little back)
    wind_base=3.8,                           # deg at the strand tip: the steady lean downwind (>= the sum of the waves: never upwind)
    wind_waves=((3.0, 2.0, 0.0), (2.4, 1.2, 0.7), (1.5, 0.6, 1.9)),   # (period s, deg, phase); the periods divide 12 s
    wind_gusts=((3.9, 1.1, 2.2), (9.3, 0.9, 1.6)),                     # (centre s, half width s, extra deg)
    wind_depth_phase=0.55,                   # rad per joint from root to tip (the wave travels down the strand)
    wind_space_phase=3.0,                    # rad per metre along the wind (the wave crosses the head)
    wind_depth_delay=0.06,                   # s per joint for the gusts
    tip_flutter=(1.0, 0.7),                  # (period s, deg) a light flutter on the last two joints of the long strands
    # the strands on her LEFT (downwind) side lie on the left shoulder: less wind there (with 0.6 / 1.0 for chains 2 / 3 they pressed up
    # to 23 more triangle pairs into the shoulder in single frames)
    chain_gain={1: 0.6, 2: 0.4, 3: 0.7, 4: 1.0, 5: 1.0, 6: 1.0, 7: 0.35, 8: 0.35, 9: 0.25, 10: 0.25, 11: 0.25, 12: 0.25,
                13: 0.35, 14: 0.35, 15: 0.35, 16: 0.35, 17: 0.35, 18: 1.0, 19: 1.0, 20: 0.35, 21: 0.35},
    # ---- ears: (side, time s, peak deg, flicks) and slow listening turns (side, start s, deg, hold s)
    ear_flicks=(('L', 2.6, 9.0, 1), ('R', 5.1, 11.0, 1), ('L', 7.4, 6.0, 1), ('R', 10.2, 10.0, 2)),
    ear_listen=(('L', 3.4, 5.0, 2.4), ('R', 7.9, 4.0, 1.9)),
    # a flick tips the ear OUTWARDS (that is what reads as a twitch, from the front as well as from behind), with some swivel of the
    # opening and a little tilt back.  (A pure swivel about the long axis of the ear hardly changed the picture: tried first.)
    ear_out_share=1.0, ear_swivel_share=0.6, ear_tilt_share=0.25,
    ear2_gain=1.35, ear2_lag=1.0 / 30.0,     # the upper part of the ear whips a little more, one frame later
    # ---- tail
    # x the round 3 sideways amplitude per joint (base .. tip): the middle of the tail swings about twice as far; the hook (joints 6..8)
    # only a little more (with 2.0 the hook turned upwards on one side of its swing and the tip rose onto the light skin band)
    tail_gain=(1.2, 1.2, 1.5, 1.8, 2.0, 1.3, 1.3, 1.2),
    tail_tipwave=(0.0, 0.0, 0.0, 0.0, 2.5, 3.0, 3.0, 3.5),  # deg, 3 s, travelling towards the tip
    # start s, in s, hold s, out s, deg (joints 6..8 roll in further).  22 deg lifted the tip to 0.725 m, onto the edge of the light skin
    # band behind the right thigh (it starts at 0.72 .. 0.75 m there); the hook has to stay on the dark stocking
    tail_curl=(5.3, 1.0, 0.7, 1.6, 10.0),
    tail_flick=(10.6, 0.18, 0.55, 10.0),                    # time s, attack s, release s, deg (the tip joint, sideways); 0.12 s was 6 deg/frame
)


# ------------------------------------------------------------------ small periodic helpers
def wrap(dt):
    return (dt + LOOP / 2.0) % LOOP - LOOP / 2.0


def bump(t, centre, half):
    d = wrap(t - centre)
    return 0.5 * (1.0 + math.cos(math.pi * d / half)) if abs(d) < half else 0.0


def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def hold_env(t, start, t_in, hold, t_out):
    """0 -> 1 (smooth, t_in) -> hold -> 0 (smooth, t_out); periodic"""
    d = (t - start) % LOOP
    if d < t_in:
        return smoothstep(d / t_in)
    d -= t_in
    if d < hold:
        return 1.0
    d -= hold
    if d < t_out:
        return 1.0 - smoothstep(d / t_out)
    return 0.0


def flick_env(t, t0, attack=2.0 / 30.0, tau=0.10, period=0.55):
    """quick out (attack), then a damped return with a small overshoot; 0 outside; periodic"""
    d = (t - t0) % LOOP
    if d > 1.2:
        return 0.0
    if d < attack:
        return math.sin(0.5 * math.pi * d / attack) ** 2
    r = d - attack
    return math.exp(-r / tau) * math.cos(TAU * r / period)


# ------------------------------------------------------------------ hair
def hair_layout(rig):
    """per hair bone: chain, depth, chain length, rest direction of the strand at this joint, root position"""
    bones = rig.bones
    chains = {}
    for b in bones:
        m = HAIR_RE.match(b.name)
        if m:
            chains.setdefault(int(m.group(2)), []).append((int(m.group(1)), b.name))
    out = {}
    for c, lst in chains.items():
        lst.sort()
        n = len(lst)
        heads = [rig.HEAD0[name] for _, name in lst]
        for k, (depth, name) in enumerate(lst):
            if k + 1 < n:
                d = heads[k + 1] - heads[k]
            else:
                d = heads[k] - heads[k - 1] if n > 1 else Vector((0.0, 0.0, -1.0))
            if d.length < 1e-6:
                d = Vector((0.0, 0.0, -1.0))
            out[name] = dict(chain=c, depth=depth, n=n, dir=d.normalized(), root=heads[0].copy())
    return out


def chain_wind_dir(root, p=P7):
    """the global wind direction without the part that would push this chain into the head / body"""
    w = Vector(p['wind_dir']).normalized()
    radial = Vector((root.x, root.y + 0.02, 0.0))
    if radial.length > 0.03:
        n_out = radial.normalized()
        inward = w.dot(n_out)
        if inward < 0.0:
            w = (w - n_out * inward).normalized()
    return w


def wind_deg(t, phase, depth, p=P7):
    """deflection at the strand tip in degrees (>= 0: the wind never pulls upwind)"""
    v = p['wind_base']
    for period, amp, ph in p['wind_waves']:
        v += amp * math.sin(TAU * t / period - phase * (period / 3.0) ** -0.3 + ph)
    for centre, half, extra in p['wind_gusts']:
        v += extra * bump(t - p['wind_depth_delay'] * depth, centre, half)
    return max(v, 0.0)


def hair_wind_rel(lay, t, p=P7):
    """per hair bone the extra rotation (world rest axes) from the wind"""
    rel = {}
    w_global = Vector(p['wind_dir']).normalized()
    for name, h in lay.items():
        gain = p['chain_gain'].get(h['chain'], 0.5)
        w = chain_wind_dir(h['root'], p)
        axis = h['dir'].cross(w)
        if axis.length < 1e-4:
            continue
        axis.normalize()
        phase = p['wind_depth_phase'] * h['depth'] + p['wind_space_phase'] * h['root'].dot(w_global)
        tip = gain * wind_deg(t, phase, h['depth'], p)
        n = h['n']
        share = h['depth'] / (n * (n + 1) / 2.0)            # more bend towards the tip, the shares add up to 1
        ang = tip * share
        if h['depth'] >= n - 1 and gain >= 0.9:                   # the last two joints of the long strands flutter a little
            fp, fa = p['tip_flutter']
            k = 1.0 if h['depth'] == n else 0.6
            ang += k * fa * math.sin(TAU * t / fp - phase * 1.3 - 0.8 * (h['depth'] - n + 1) + 0.4)
        rel[name] = Quaternion(axis, d2r(ang))
    return rel


# ------------------------------------------------------------------ ears
def ear_axes(rig):
    """per side: the long axis of the ear (base -> tip) and the axis that tilts the tip backwards"""
    out = {}
    for s in ('L', 'R'):
        base = rig.HEAD0['J_Opt_%s_CatEar1_01' % s]
        tip = rig.HEAD0['J_Opt_%s_CatEar2_end_01' % s]
        a = (tip - base).normalized()
        back = Vector((0.0, -1.0, 0.0))
        tilt_axis = a.cross(back)                           # rotating the tip towards -Y (back) about a x back
        out[s] = (a, tilt_axis.normalized())
    return out


def ear_event_rel(rig, axes, t, p=P7):
    """per ear bone the extra rotation: flicks (swivel outwards + a little tilt back) and slow listening turns"""
    rel = {}
    for s, sx in (('L', -1.0), ('R', 1.0)):
        a, tilt = axes[s]
        out_sign = -sx                                       # +angle about the ear axis turns the opening outwards on the left ear
        for part, gain, lag in (('1', 1.0, 0.0), ('2', p['ear2_gain'] - 1.0, p['ear2_lag'])):
            tt = t - lag
            swivel = 0.0
            for side, t0, peak, count in p['ear_flicks']:
                if side != s:
                    continue
                e = flick_env(tt, t0)
                if count == 2:
                    e = max(e, 0.75 * flick_env(tt, t0 + 0.20))
                swivel += peak * e
            listen = 0.0
            for side, start, deg, hold in p['ear_listen']:
                if side == s:
                    listen += deg * hold_env(tt, start, 0.6, hold, 0.9)
            ang_out = gain * p['ear_out_share'] * swivel                       # tip outwards (about the forward axis)
            ang_sw = gain * (p['ear_swivel_share'] * swivel + (listen if part == '1' else 0.0))
            ang_tilt = gain * p['ear_tilt_share'] * swivel
            q = Quaternion(Vector((0.0, 1.0, 0.0)), d2r(sx * ang_out)) @ Quaternion(a, d2r(out_sign * ang_sw)) @ Quaternion(tilt, d2r(ang_tilt))
            rel['J_Opt_%s_CatEar%s_01' % (s, part)] = q
    return rel


# ------------------------------------------------------------------ tail
def tail_dirs(t, p=P7):
    """joint directions in the hips frame: the round 3 wave with more swing, a quick tip wave, a curl and a flick"""
    P3 = R3['P3']
    base = L['COMMON2']['tail']
    out = []
    curl_axis = None
    for i, d in enumerate(base):
        ph = P3['tail_phase'] * i
        wave = (math.sin(W * t - ph + 0.3) + 0.40 * math.sin(2 * W * t - 1.5 * ph + 1.2) + 0.15 * math.sin(3 * W * t - 2.0 * ph + 2.0)) / 1.35
        follow = -R3['s_main'](t - P3['tail_follow_lag'] - 0.12 * i)
        ay = P3['tail_amp_y'][i] * p['tail_gain'][i] * ((1.0 - P3['tail_follow']) * wave + P3['tail_follow'] * follow)
        ay += p['tail_tipwave'][i] * math.sin(4 * W * t - 0.9 * i + 0.5)
        az = P3['tail_amp_z'][i] * min(p['tail_gain'][i], 1.2) * math.sin(W * t - ph + 1.8)
        q = Euler((0.0, d2r(ay), d2r(az)), 'XYZ').to_quaternion()
        out.append(q @ Vector(d).normalized())
    # curl of the tip: joints 6..8 roll further about the axis of the rest curl
    d5, d8 = Vector(base[4]).normalized(), Vector(base[7]).normalized()
    curl_axis = d5.cross(d8).normalized()
    start, t_in, hold, t_out, deg = p['tail_curl']
    c = deg * hold_env(t, start, t_in, hold, t_out)
    tf, att, rel_t, fdeg = p['tail_flick']
    fl = fdeg * flick_env(t, tf, att, rel_t / 4.0, rel_t * 1.6)
    for i, share in ((5, 0.5), (6, 0.5), (7, 1.0)):
        out[i] = Quaternion(curl_axis, d2r(c * share)) @ out[i]
    out[7] = Euler((0.0, d2r(fl), 0.0), 'XYZ').to_quaternion() @ out[7]
    return out


def tail_Q(rig, dirs):
    R = rig.R
    Q = {}
    prev = Quaternion()
    for i, name in enumerate(rig.tail_bones):
        rot = Vector((0.0, -1.0, 0.0)).rotation_difference(dirs[i])
        Q[name] = R[name].inverted() @ prev.inverted() @ rot @ R[name]
        prev = rot
    return Q


# ------------------------------------------------------------------ baking
def _fcurves(act):
    return R3['action_fcurves'](act)


def bake_dynamics(arm, base_name='Yoru_Idle_v2', new_name='Yoru_Idle_v2_r7', p=P7):
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    base = bpy.data.actions[base_name]
    act = base.copy()
    if bpy.data.actions.get(new_name):
        bpy.data.actions[new_name].name = new_name + '_previous'
    act.name = new_name
    act.use_fake_user = True
    fcs = {(fc.data_path, fc.array_index): fc for fc in _fcurves(act)}
    lay = hair_layout(rig)
    axes = ear_axes(rig)
    R = rig.R
    hair = sorted(lay.keys())
    ears = ['J_Opt_%s_CatEar%d_01' % (s, k) for s in 'LR' for k in (1, 2)]
    tails = list(rig.tail_bones)

    def old_q(name, f):
        dp = 'pose.bones["%s"].rotation_quaternion' % name
        return Quaternion([fcs[(dp, i)].keyframe_points[f].co[1] for i in range(4)])

    series = {n: [] for n in hair + ears + tails}
    for f in range(NF + 1):
        t = (f % NF) / FPS
        wr = hair_wind_rel(lay, t, p)
        er = ear_event_rel(rig, axes, t, p)
        tq = tail_Q(rig, tail_dirs(t, p))
        for n in hair:
            q = old_q(n, f)
            if n in wr:
                q = q @ (R[n].inverted() @ wr[n] @ R[n])
            series[n].append(q)
        for n in ears:
            series[n].append(old_q(n, f) @ (R[n].inverted() @ er[n] @ R[n]))
        for n in tails:
            series[n].append(tq[n])
    for n, seq in series.items():
        prev = None
        fixed = []
        for q in seq:
            if prev is not None and prev.dot(q) < 0.0:
                q = -q
            fixed.append(q)
            prev = q
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        for i in range(4):
            fc = fcs[(dp, i)]
            cos = []
            for f in range(NF + 1):
                cos.extend((float(f), float(fixed[f][i])))
            fc.keyframe_points.foreach_set('co', cos)
            fc.update()
    ad = arm.animation_data
    ad.action = act
    if hasattr(ad, 'action_slot') and act.slots:
        ad.action_slot = act.slots[0]
    bpy.context.scene.frame_set(0)
    return {'action': act.name, 'hair_bones': len(hair), 'ear_bones': len(ears), 'tail_bones': len(tails)}


# ------------------------------------------------------------------ checks (numbers only)
def curve_groups(name):
    if HAIR_RE.match(name):
        return 'hair'
    if 'CatEar' in name:
        return 'ears'
    if 'CatTail' in name:
        return 'tail'
    return 'other'


def compare_actions(a_name, b_name):
    """number of curves that differ per group (hair, ears, tail, other) and the largest step per frame (deg) and the seam per group"""
    A = {(fc.data_path, fc.array_index): fc for fc in _fcurves(bpy.data.actions[a_name])}
    B = {(fc.data_path, fc.array_index): fc for fc in _fcurves(bpy.data.actions[b_name])}
    changed = {'hair': 0, 'ears': 0, 'tail': 0, 'other': 0}
    total = {'hair': 0, 'ears': 0, 'tail': 0, 'other': 0}
    for k, fc in A.items():
        g = curve_groups(k[0].split('"')[1]) if '"' in k[0] else 'other'
        total[g] += 1
        o = B[k]
        if any(abs(fc.keyframe_points[i].co[1] - o.keyframe_points[i].co[1]) > 1e-9 for i in range(len(fc.keyframe_points))):
            changed[g] += 1
    steps = {'hair': (0.0, None), 'ears': (0.0, None), 'tail': (0.0, None)}
    seam = {'hair': 0.0, 'ears': 0.0, 'tail': 0.0}
    bones = sorted(set(k[0].split('"')[1] for k in A if k[0].endswith('rotation_quaternion')))
    for n in bones:
        g = curve_groups(n)
        if g == 'other':
            continue
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        qs = [Quaternion([A[(dp, i)].keyframe_points[f].co[1] for i in range(4)]) for f in range(NF + 1)]
        for f in range(NF):
            a = math.degrees(qs[f].rotation_difference(qs[f + 1]).angle)
            a = min(a, 360.0 - a)
            if a > steps[g][0]:
                steps[g] = (a, (n, f))
        s = math.degrees(qs[0].rotation_difference(qs[NF]).angle)
        seam[g] = max(seam[g], min(s, 360.0 - s))
    return {'changed_curves': changed, 'curves_per_group': total, 'max_step_deg': {g: (round(v[0], 2), v[1]) for g, v in steps.items()},
            'seam_deg': {g: round(v, 4) for g, v in seam.items()}}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    out = argv[0]
    name = argv[1] if len(argv) > 1 else 'Yoru_A2'
    print('[dynamics r7]', bake_dynamics(bpy.data.objects[name]), flush=True)
    print('[dynamics r7]', compare_actions('Yoru_Idle_v2_r7', 'Yoru_Idle_v2'), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
