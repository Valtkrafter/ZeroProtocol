"""
Yoru - DODGE FROM THE WALK (forward sprint burst), one shot, 60 fps, IN PLACE (the ground scrolls under her), built procedurally on the VRM skeleton.
Same method and the same rig conventions as build_run.py (world-space rotation deltas D per humanoid bone, legs by two-bone IK to planted feet, foot / toe
geometry of the real shoe), but one-shot instead of a cycle.  The setup and the helpers are taken from build_run.py itself (exec of its first parts).

Run (background Blender; ALWAYS --factory-startup and absolute paths):
  blender -b --factory-startup --python build_dodge.py -- <Yoru.glb> <output dir> build
  env DODGE_SPRINGS=0 skips the hair / ear / bust simulation (fast design runs), DODGE_TABLE=0 hides the per frame table.

Version 2 (after the user's critique of the first version: stuttering start, upright trunk at the start, frozen air pose, boxer arms, abrupt stop, stiff tail and hair):
  - she starts from the WALK pose (walking arms, walking tail, small lean) and builds up: lean, arm swing, elbow bend and tail shape blend in over the first steps
  - a real sprint burst: push-off (stance 1), two fast sprint strides (stances 2 and 3), the legs keep cycling in the air (heel kick, knee drive, reach, paw back)
  - run-out: a braking step (stance 4) and a first walking step (stance 5), the speed falls smoothly to the walk speed, the body comes up again
  - arms swing like in the run (elbow 66 .. 100 deg, fists at chest height), amplitude grows with the speed
  - tail: rest curve of the walk -> aerodynamic arch -> walk, plus a spring cascade (every joint trails the one before) driven by lean, bob and pelvis yaw
  - hair, ears and bust: the VRM spring bone algorithm of build_run.py (verlet, colliders) on the real motion with the real world travel and a speed dependent wind
The ground speed of the pelvis (PD.V_KEYS) is the design curve: every stance only lets the pelvis travel as far as the leg can reach over the planted foot, so
nothing slides; the same curve is exported (Yoru_DodgeWalk_gait.json, speed_per_frame) for the character controller in Unity.
Blender axes for Yoru: +Y forward, her left = -X, up = +Z.
"""
import os, sys, math, json, time, bisect

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = open(os.path.join(_HERE, 'build_run.py'), encoding='utf-8').read().split('\n')


def _find(prefix):
    for i, l in enumerate(_SRC):
        if l.startswith(prefix):
            return i
    raise RuntimeError('marker not found in build_run.py: ' + prefix)


# --- setup + helpers of build_run.py (imports, argv: GLB OUT, rig maps H / HEAD0 / R / order, deg, eul, aim, two_bone_ik, herm5, rot2, set_linear ...)
exec(compile('\n'.join(_SRC[_find('import bpy, sys, math, cmath'):_find('# ------------------------------------------------------------------ parameters')]), 'build_run.py[setup]', 'exec'), globals())
# --- foot geometry of the real shoe, leg lengths (low_rel, toe_bend, HIP_DROP, LEG_L1 / LEG_L2 / LEG_SUM, HIP_X ...)
exec(compile('\n'.join(_SRC[_find('# foot geometry from the rig'):_find('class Gait:')]), 'build_run.py[geometry]', 'exec'), globals())
import numpy as np

T0D = time.time()
DEBUG_TABLE = os.environ.get('DODGE_TABLE', '1') == '1'
USE_SPRINGS = os.environ.get('DODGE_SPRINGS', '1') == '1'


def dlog(*a):
    print('[dodge %5.1fs]' % (time.time() - T0D), *a, flush=True)


# ------------------------------------------------------------------ parameters
class PD:
    NFD = 48                     # frames 0 .. 47 (0.783 s)
    # stances in order (frames at 60 fps): side, touchdown (None = the clip starts in this stance), toe off (None = she stays on it to the end),
    # ankle ahead of the pelvis at the touchdown (m), foot pitch at the touchdown (deg, toes up = positive), at toe off (deg), support knee flexion keys (frame, deg)
    STANCES = [
        dict(side='R', td=None, to=6.0, ahead=0.0, th_land=0.0, th_to=-50.0, knee=[(0, 24.0), (2, 36.0), (3.5, 41.0), (5, 39.0), (6, 38.0)]),
        dict(side='L', td=12.0, to=17.0, ahead=0.20, th_land=-4.0, th_to=-40.0, knee=[(12, 30.0), (13.5, 44.0), (15, 56.0), (16, 46.0), (17, 36.0)]),
        dict(side='R', td=23.0, to=28.0, ahead=0.20, th_land=-4.0, th_to=-40.0, knee=[(23, 30.0), (24.5, 44.0), (26, 54.0), (27, 46.0), (28, 36.0)]),
        dict(side='L', td=32.0, to=38.0, ahead=0.28, th_land=6.0, th_to=-30.0, knee=[(32, 34.0), (34, 56.0), (36, 64.0), (37, 52.0), (38, 40.0)]),
        dict(side='R', td=40.0, to=None, ahead=0.24, th_land=8.0, th_to=0.0, knee=[(40, 40.0), (42, 40.0), (44, 34.0), (47, 26.0)]),
    ]
    z_smooth = 2                                 # passes of [1 2 1] / 4 over the pelvis height (takes the spikes off the contacts; the planted legs only have to be reachable)
    FLIGHT_RISE = [0.012, 0.012, 0.006, 0.002]   # rise (m) of the pelvis above the straight line in the flights between the stances (ballistic arcs)
    # ground speed of the pelvis (m/s) at frames: the design curve
    V_KEYS = [(0, 1.5), (1.5, 1.85), (3, 2.7), (4.5, 3.8), (6, 4.8), (9, 6.2), (12, 7.0), (15, 7.5), (17, 7.7), (20, 7.9), (23, 7.8), (26, 7.4), (28, 7.1), (30, 6.8), (32, 6.4), (35, 5.5),
              (38, 4.7), (40, 4.1), (42, 3.3), (44, 2.6), (46, 2.0), (47, 1.75)]
    X_KEYS = [(0, 0.018), (4, 0.014), (9, 0.0), (14.5, -0.02), (20, 0.0), (25.5, 0.016), (30, 0.0), (35, -0.02), (40, 0.0), (44, 0.012), (47, 0.018)]   # pelvis sway (+X = her right)
    # world pitch of the upper chest (deg, forward lean)
    LEAN_KEYS = [(0, 7), (2, 15), (4, 25), (6, 33), (9, 40), (12, 43), (16, 45), (20, 45), (24, 44), (28, 41), (32, 37), (35, 31), (38, 25), (41, 19), (44, 12), (47, 7)]
    lean_share = (0.50, 0.68, 0.86, 1.0)         # hips, spine, chest, upper chest: share of the lean reached (cumulative world pitch)
    YAW_KEYS = [(0, 0.0), (6, -4.0), (12, -4.5), (17, 0.0), (23, 4.5), (28, 0.5), (32, -3.5), (36, -1.0), (40, 2.5), (44, 1.5), (47, 0.3)]               # pelvis yaw (deg, negative = left hip forward)
    ROLL_KEYS = [(0, 0.0), (3, 2.5), (9, 0.0), (14.5, -2.5), (20, 0.0), (25.5, 2.5), (30, 0.0), (35, -3.0), (40, 0.5), (44, 1.8), (47, 0.5)]            # pelvis roll (deg)
    chest_counter = 0.6                          # the chest turns against the pelvis by this share of the pelvis yaw
    neck_share, head_share = 0.15, 0.25          # head (world pitch share of the upper-chest lean)
    # feet
    BASE = 0.05                                  # ankle distance from the midline (m)
    CIRC = 0.03                                  # swing foot goes out by this much at mid swing
    R_MAX = 0.984                                # longest leg (d / (L1 + L2)) in the swings
    TH0 = -4.0                                   # foot pitch at the start (deg, toes up positive)
    HEEL_DELAY, HEEL_RAMP = 0.6, 1.6             # first stance: frames of flat foot, frames of the heel rise ramp
    # swings of every foot, in order (R: before stance 3 and 5, L: to stance 2, 4 and then free).  Knots (frame, value, speed): y' = ankle ahead of the pelvis (in place, m),
    # r = leg length ratio d / (L1 + L2) (0.97 = knee 28 deg, 0.9 = 52, 0.8 = 74, 0.7 = 91, 0.6 = 106); speed 0 = smooth stop (an extreme), None = monotone estimate.
    # auto_back = frames after the toe off until the foot stops moving backwards (the knot is computed from the toe off speed), auto_fwd = frames before the touchdown
    # of the extreme forward position (the foot then paws back to the ground speed).  pitch = interior knots of the foot pitch (deg), toes up positive.
    SWINGS = {
        'R': [dict(auto_back=2.0, auto_fwd=2.5, y=[(13.0, -0.10, None), (17.5, 0.28, None)],
                   r=[(9.0, 0.82, None), (12.0, 0.66, 0.0), (16.0, 0.74, None), (19.0, 0.93, None), (21.0, 0.965, None)],
                   pitch=[(9, -72.0), (13, -64.0), (18, -32.0), (21, -10.0)]),
              dict(auto_back=2.0, auto_fwd=2.5, y=[(33.5, -0.06, None)],
                   r=[(31.0, 0.86, None), (33.5, 0.68, 0.0), (36.0, 0.85, None), (38.0, 0.955, None)],
                   pitch=[(30.5, -62.0), (34, -52.0), (37, -22.0), (38.8, -4.0)])],
        'L': [dict(free_a=((0.04, 1.5), (0.94, 0.0)), auto_fwd=3.0, y=[(3.5, 0.21, None), (7.0, 0.34, None)],
                   r=[(3.5, 0.86, 0.0), (7.0, 0.94, None), (9.5, 0.96, None), (11.0, 0.965, None)],
                   pitch=[(0, -14.0), (4, -26.0), (7, -12.0), (10, 0.0)]),
              dict(auto_back=2.0, auto_fwd=2.5, y=[(24.0, -0.08, None), (28.0, 0.28, None)],
                   r=[(20.0, 0.87, None), (23.0, 0.66, 0.0), (27.0, 0.78, None), (29.5, 0.95, None)],
                   pitch=[(20, -68.0), (24, -60.0), (28, -30.0), (30.5, -8.0)]),
              dict(free_b=((-0.07, 1.6), (0.93, 0.0)), auto_back=2.5, y=[(44.0, -0.22, None)],
                   r=[(41.0, 0.84, None), (43.5, 0.76, 0.0)],
                   pitch=[(41, -52.0), (44, -30.0)], end_pitch=-12.0)],
    }
    # sprint amount (0 = walking, 1 = full sprint) of the arms / fingers and of the tail (a little later)
    S_ARM_KEYS = [(0, 0.0), (2, 0.1), (5, 0.45), (8, 0.8), (11, 1.0), (30, 1.0), (34, 0.85), (38, 0.6), (42, 0.3), (47, 0.0)]
    S_TAIL_KEYS = [(0, 0.0), (3, 0.1), (6, 0.5), (9, 0.9), (12, 1.0), (28, 1.0), (32, 0.9), (36, 0.5), (40, 0.15), (44, 0.0), (47, 0.0)]
    # arm swing of the RIGHT arm, -1 .. +1 (+1 = furthest forward, the left arm is the mirror image): extremes just before the opposite foot lands
    ARM_N_KEYS = [(0, 0.0), (5, 0.5), (11, 1.0), (16.5, 0.0), (22, -1.0), (26.5, 0.0), (31, 1.0), (35, 0.1), (39, -0.8), (43, -0.15), (47, 0.0)]
    # (walk value, sprint value): mean swing (deg from the plumb line, + forward), amplitude, elbow flexion mean, elbow follows the swing by ELBOW_K,
    # upper arm outward angle (walk / sprint at the back swing / sprint at the forward swing), forearm outward angle (walk / back swing / forward swing)
    ARM_MEAN, ARM_AMP, ELBOW_MID, ELBOW_K = (-2.0, 2.0), (16.0, 34.0), (14.0, 74.0), 0.35
    HANG = (26.0, 27.0, 11.0)
    FORE = (6.0, 20.0, -11.0)
    fingers_walk = {'Index': (22.0, 30.0, 16.0), 'Middle': (28.0, 38.0, 20.0), 'Ring': (34.0, 44.0, 24.0), 'Little': (40.0, 50.0, 28.0)}
    fingers_run = {'Index': (35.0, 48.0, 28.0), 'Middle': (45.0, 58.0, 34.0), 'Ring': (55.0, 66.0, 38.0), 'Little': (62.0, 72.0, 42.0)}
    thumb_add = 33.0
    # tail: rest curve of the walk, aerodynamic arch of the sprint (direction of every joint above the horizontal, world, side view), spring cascade on top
    tail_walk = [-38.0, -42.0, -44.0, -40.0, -26.0, -6.0, 20.0, 40.0]
    tail_sprint = [26.0, 22.0, 16.0, 10.0, 8.0, 10.0, 16.0, 22.0]
    tail_scale = 0.72
    tail_w, tail_z = 17.0, 0.45                  # every joint follows the one before with a spring of this frequency (rad/s) and damping
    tail_lat = (3.0, 12.0)                       # peak sideways bend per joint (deg) at the base and at joint 6 (the cascade supplies the phase)
    tail_vert = (3.0, 14.0)                      # peak pitch wave per joint (deg)
    tail_bob_gain = 700.0                        # deg per m of pelvis height change added to the pitch drive
    tail_acc_gain = 0.5                          # deg per m/s2 of ground acceleration added to the pitch drive (braking throws the tip up)
    # hair, ears and bust: spring bones of the VRM (same numbers as build_run.py)
    spring_pre = 45                              # frames of walking before the clip (the springs settle)
    bust_stiff, bust_drag = 0.80, 0.05
    ear_stiff, ear_drag = 1.6, 0.14
    hair_stiff_mul, hair_drag = 1.4, 0.30
    wind_hair, wind_ear, wind_lift = 0.19, 0.30, 0.25       # headwind at 5 m/s (scaled with (v / 5) ** wind_exp)
    wind_exp = 1.2
    pseudo_hair, pseudo_ear, pseudo_bust = 0.8, 0.5, 0.4       # share of the inertial push of the ground acceleration (the simulation runs in place)
    spring_smooth = 2
    spring_coll = 1                              # 1 = the strands are pushed out of the collider spheres of the VRM


for _kv in os.environ.get('DODGE_OVR', '').split(','):                   # quick sweeps: DODGE_OVR="hair_drag=0.45,spring_smooth=2"
    if '=' in _kv:
        _k, _v = [s.strip() for s in _kv.split('=')]
        setattr(PD, _k, type(getattr(PD, _k))(float(_v)))

NFD = PD.NFD
PARTS = ('Proximal', 'Intermediate', 'Distal')
FIRST, LAST = 0.0, float(NFD - 1)


# ------------------------------------------------------------------ numeric helpers
class CSpline:
    """C2 cubic spline through (x, y); natural ends, or clamped end slopes d0 / dn"""

    def __init__(self, xs, ys, d0=None, dn=None):
        xs = np.array(xs, float)
        ys = np.array(ys, float)
        n = len(xs)
        h = np.diff(xs)
        A = np.zeros((n, n))
        r = np.zeros(n)
        for i in range(1, n - 1):
            A[i, i - 1], A[i, i], A[i, i + 1] = h[i - 1], 2.0 * (h[i - 1] + h[i]), h[i]
            r[i] = 6.0 * ((ys[i + 1] - ys[i]) / h[i] - (ys[i] - ys[i - 1]) / h[i - 1])
        if d0 is None:
            A[0, 0] = 1.0
        else:
            A[0, 0], A[0, 1], r[0] = 2.0 * h[0], h[0], 6.0 * ((ys[1] - ys[0]) / h[0] - d0)
        if dn is None:
            A[-1, -1] = 1.0
        else:
            A[-1, -1], A[-1, -2], r[-1] = 2.0 * h[-1], h[-1], 6.0 * (dn - (ys[-1] - ys[-2]) / h[-1])
        self.M = np.linalg.solve(A, r)
        self.x, self.y, self.h = xs, ys, h

    def __call__(self, x):
        xs = self.x
        x = min(max(x, xs[0]), xs[-1])
        i = max(0, min(len(xs) - 2, bisect.bisect_right(xs.tolist(), x) - 1))
        h = self.h[i]
        a, b = xs[i + 1] - x, x - xs[i]
        return (self.M[i] * a ** 3 + self.M[i + 1] * b ** 3) / (6.0 * h) + (self.y[i] / h - self.M[i] * h / 6.0) * a + (self.y[i + 1] / h - self.M[i + 1] * h / 6.0) * b


def pchip(xs, ys):
    """monotone cubic Hermite interpolant (Fritsch-Carlson): no overshoot between the keys"""
    xs = [float(v) for v in xs]
    ys = [float(v) for v in ys]
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0.0:
            m[i] = 0.0
        else:
            w1, w2 = 2.0 * h[i] + h[i - 1], h[i] + 2.0 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def fn(x):
        x = min(max(x, xs[0]), xs[-1])
        i = max(0, min(n - 2, bisect.bisect_right(xs, x) - 1))
        t = (x - xs[i]) / h[i]
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h[i] * m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h[i] * m[i + 1])
    return fn


def d_dt(fun, f, order=1, h=0.05, side=0):
    """derivative of fun(frame) with respect to TIME (seconds); h in frames.  side 0 = central, -1 = backward (only values at f, f - h, f - 2h: the end of a stance),
    +1 = forward (f, f + h, f + 2h: the start of a stance), so a stance function is never evaluated outside the stance"""
    if side == 0:
        if order == 1:
            return (fun(f + h) - fun(f - h)) / (2.0 * h) * FPS
        return (fun(f + h) - 2.0 * fun(f) + fun(f - h)) / (h * h) * FPS * FPS
    s = float(side)
    f0, f1, f2 = fun(f), fun(f + s * h), fun(f + 2.0 * s * h)
    if order == 1:
        return s * (-3.0 * f0 + 4.0 * f1 - f2) / (2.0 * h) * FPS
    return (f0 - 2.0 * f1 + f2) / (h * h) * FPS * FPS


def lp_seq(y, w, z, sub=10):
    """x'' = w^2 (y - x) - 2 z w x' for the samples y (one per frame), starting at rest on y[0]: the spring follows y with a lag; returns x per frame"""
    n = len(y)
    dt = 1.0 / FPS / sub
    x, v = float(y[0]), 0.0
    out = []
    for i in range(n):
        out.append(x)
        a0, a1 = y[i], y[min(i + 1, n - 1)]
        for k in range(sub):
            tgt = a0 + (a1 - a0) * (k / sub)
            v += (w * w * (tgt - x) - 2.0 * z * w * v) * dt
            x += v * dt
    return out


# ------------------------------------------------------------------ the design curves
_V = pchip([k[0] for k in PD.V_KEYS], [k[1] for k in PD.V_KEYS])
_GRID = np.arange(-2.0, NFD + 2.0, 0.02)
_S_TAB = np.concatenate([[0.0], np.cumsum(0.5 * (np.array([_V(x) for x in _GRID[1:]]) + np.array([_V(x) for x in _GRID[:-1]])) * 0.02 / FPS)])
_S0 = float(np.interp(0.0, _GRID, _S_TAB))


def V(f):
    """ground speed of the pelvis (m/s)"""
    return _V(f)


def S(f):
    """distance the pelvis has travelled since frame 0 (m)"""
    return float(np.interp(f, _GRID, _S_TAB)) - _S0


def S_world(f):
    """the same, but before the clip she walks on at the speed of frame 0 (used by the spring simulation)"""
    return S(f) if f >= 0.0 else V(0.0) * f / FPS


Xs = CSpline([k[0] for k in PD.X_KEYS], [k[1] for k in PD.X_KEYS])
Lean = CSpline([k[0] for k in PD.LEAN_KEYS], [k[1] for k in PD.LEAN_KEYS])
Yaw = CSpline([k[0] for k in PD.YAW_KEYS], [k[1] for k in PD.YAW_KEYS])
Roll = CSpline([k[0] for k in PD.ROLL_KEYS], [k[1] for k in PD.ROLL_KEYS])
S_ARM = pchip([k[0] for k in PD.S_ARM_KEYS], [k[1] for k in PD.S_ARM_KEYS])
S_TAIL = pchip([k[0] for k in PD.S_TAIL_KEYS], [k[1] for k in PD.S_TAIL_KEYS])
ARM_N = pchip([k[0] for k in PD.ARM_N_KEYS], [k[1] for k in PD.ARM_N_KEYS])


def mix(a, b, s):
    return a * (1.0 - s) + b * s


def ankle_from_ball(yb, th):
    """toe joint planted at y = yb (ground frame): ankle y and z for the foot pitch th (rad, toes up positive); the toe part lies flat on the ground"""
    ry, _ = rot2(th, A0y - J0y, A0z - J0z)
    return yb + ry, -low_rel(th, toe_bend(th))


def ball_from_ankle(ya, th):
    ry, _ = rot2(th, A0y - J0y, A0z - J0z)
    return ya - ry


def smooth01(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (10.0 - 15.0 * x + 6.0 * x * x)


# ------------------------------------------------------------------ legs
# The feet are described in the IN-PLACE frame (y' = metres ahead of the pelvis, the pelvis does not move fore-aft); a planted foot is fixed in the GROUND frame
# (y' = y_ground - S(f), so it slides backwards under the pelvis at the ground speed).  Stance feet follow the real shoe (toe joint planted while the heel rises,
# flat sole otherwise), swing feet are quintic Hermite paths through knots in the fore-aft position AND in the LEG LENGTH (knee flexion), so a foot can never be asked
# for a place the leg cannot reach.  The pelvis height follows from the support leg's knee flexion in the stances and from a small ballistic arc in the flights.
LEG_L = LEG_SUM
DX = HIP_X - PD.BASE                                                             # sideways distance hip joint - ankle (m)


def hip_yz(f, zb):
    """hip joint (y relative to the hips bone, z) for the hips bone height zb: the hip joints sit HIP_DROP below the hips bone, which pitches forward"""
    p = deg(float(Lean(f)) * PD.lean_share[0])
    return -HIP_DROP * math.sin(p), zb - HIP_DROP * math.cos(p)


def ratio_of(f, y, z, zb):
    hy, hz = hip_yz(f, zb)
    return math.sqrt((y - hy) ** 2 + (hz - z) ** 2 + DX * DX) / LEG_L


def z_from_ratio(f, y, r, zb):
    hy, hz = hip_yz(f, zb)
    return hz - math.sqrt(max((r * LEG_L) ** 2 - (y - hy) ** 2 - DX * DX, 1e-6))


class StanceFoot:
    """a foot on the ground: state(f) = (y' in place, z, pitch, toe bend)"""

    def __init__(self, sp):
        self.sp = sp
        self.side, self.td, self.to = sp['side'], sp['td'], sp['to']
        self.first = self.td is None
        self.f0 = 0.0 if self.first else float(self.td)
        self.f1 = float(self.to) if self.to is not None else LAST
        self.knee = CSpline([k[0] for k in sp['knee']], [k[1] for k in sp['knee']])
        if self.first:
            self.th0 = deg(PD.TH0)
            tto = deg(sp['th_to'])
            self.rate = (tto - self.th0) / (self.to - PD.HEEL_DELAY - 0.5 * PD.HEEL_RAMP)          # rad per frame of the steady heel rise
            self.yb = ball_from_ankle(S(0.0) + 0.0, self.th0)                                       # the ankle is under the pelvis at frame 0
        else:
            self.yA = S(self.td) + sp['ahead']
            if self.to is not None:
                n = self.to - self.td
                fin, rl = min(2.2, 0.3 * n), min(3.0, 0.45 * n)
                self.thc = CSpline([self.td, self.td + fin, self.to - rl, self.to], [deg(sp['th_land']), 0.0, 0.0, deg(sp['th_to'])], d0=0.0, dn=deg(-8.0))
                self.yb = ball_from_ankle(self.yA, 0.0)

    def th_first(self, f):
        t = f - PD.HEEL_DELAY
        if t <= 0.0:
            return self.th0
        tr = PD.HEEL_RAMP
        if t < tr:
            x = t / tr
            return self.th0 + self.rate * tr * (2.5 * x ** 4 - 3.0 * x ** 5 + x ** 6)
        return self.th0 + self.rate * (0.5 * tr + (t - tr))

    def state(self, f):
        if self.first:
            th = self.th_first(f)
            ya, z = ankle_from_ball(self.yb, th)
            return ya - S(f), z, th, toe_bend(th)
        if self.to is None:
            th = deg(self.sp['th_land']) * (1.0 - smooth01((f - self.td) / 2.2))
            return self.yA - S(f), -low_rel(th, toe_bend(th)), th, toe_bend(th)
        th = float(self.thc(f))
        if th >= 0.0:
            ya, z = self.yA, -low_rel(th, toe_bend(th))
        else:
            ya, z = ankle_from_ball(self.yb, th)
        return ya - S(f), z, th, toe_bend(th)


STF = [StanceFoot(sp) for sp in PD.STANCES]


# ---- the pelvis height from the support leg (stances) and ballistic arcs (flights)
_zb_vals = {}
for _st in STF:
    for _f in range(int(math.ceil(_st.f0)), int(math.floor(_st.f1)) + 1):
        _s = _st.state(float(_f))
        _r = knee_ratio(float(_st.knee(_f)))
        _p = deg(float(Lean(_f)) * PD.lean_share[0])
        _hy = -HIP_DROP * math.sin(_p)
        _zh = _s[1] + math.sqrt(max((_r * LEG_L) ** 2 - (_s[0] - _hy) ** 2 - DX * DX, 1e-6))
        _zb_vals[_f] = _zh + HIP_DROP * math.cos(_p)
for _k, (_a, _b) in enumerate(zip(STF[:-1], STF[1:])):
    _fa, _fb = int(_a.f1), int(_b.f0)
    for _f in range(_fa + 1, _fb):
        _u = (_f - _fa) / float(_fb - _fa)
        _zb_vals[_f] = (1.0 - _u) * _zb_vals[_fa] + _u * _zb_vals[_fb] + 4.0 * PD.FLIGHT_RISE[_k] * _u * (1.0 - _u)
_zs = [_zb_vals[f] for f in range(NFD)]
for _ in range(PD.z_smooth):
    _zs = [0.25 * _zs[max(f - 1, 0)] + 0.5 * _zs[f] + 0.25 * _zs[min(f + 1, NFD - 1)] for f in range(NFD)]
Zb = CSpline(list(range(NFD)), _zs)


def knot_path(fa, fb, a_fn, b_fn, knots, free_a=None, free_b=None):
    """path of one channel (y' or leg ratio) of a swing foot between frames fa and fb as quintic Hermite pieces through the knots (frame, value, speed or None).
    A stance end (a_fn / b_fn) gives value, speed and acceleration of the planted foot, a free end the numbers (value, speed per second) in free_a / free_b.
    Knots without a speed get the monotone (PCHIP) estimate, so the path never overshoots its knots; knots with speed 0 are smooth stops; interior acceleration is 0."""
    K = []
    if a_fn is not None:
        K.append([fa, a_fn(fa), d_dt(a_fn, fa, 1, side=-1) / FPS, d_dt(a_fn, fa, 2, side=-1) / FPS ** 2])
    else:
        K.append([fa, free_a[0], free_a[1] / FPS, 0.0])
    for f, p, v in knots:
        K.append([f, p, v, 0.0])
    if b_fn is not None:
        K.append([fb, b_fn(fb), d_dt(b_fn, fb, 1, side=1) / FPS, d_dt(b_fn, fb, 2, side=1) / FPS ** 2])
    else:
        K.append([fb, free_b[0], free_b[1] / FPS, 0.0])
    for i in range(len(K) - 1):
        if not K[i + 1][0] > K[i][0] + 0.5:
            raise RuntimeError('swing knots not increasing: %s' % [(round(k[0], 2), round(k[1], 3)) for k in K])
    for i in range(1, len(K) - 1):
        if K[i][2] is None:
            h0, h1 = K[i][0] - K[i - 1][0], K[i + 1][0] - K[i][0]
            d0, d1 = (K[i][1] - K[i - 1][1]) / h0, (K[i + 1][1] - K[i][1]) / h1
            if d0 * d1 <= 0.0:
                K[i][2] = 0.0
            else:
                w1, w2 = 2.0 * h1 + h0, h1 + 2.0 * h0
                K[i][2] = (w1 + w2) / (w1 / d0 + w2 / d1)
    pieces = [(K[i][0], K[i + 1][0], K[i][1], K[i][2], K[i][3], K[i + 1][1], K[i + 1][2], K[i + 1][3]) for i in range(len(K) - 1)]
    return lambda f: pieces_eval(pieces, f)


def swing_state(f, fa, fb, paths, pitch, tau):
    py, pr = paths
    y = py(f)
    r = pr(f)
    e = 0.01
    r = 0.5 * (r + PD.R_MAX - math.sqrt((r - PD.R_MAX) ** 2 + e * e))                 # smooth minimum: the leg never gets longer than R_MAX
    z = z_from_ratio(f, y, r, float(Zb(f)))
    th, ta_ = float(pitch(f)), float(tau(f))
    u = (f - fa) / float(fb - fa)
    w = smooth01(u / 0.06) * (1.0 - smooth01((u - 0.94) / 0.06))                  # safety net: the sole never goes through the floor (faded out at both ends)
    z_floor = -low_rel(th, ta_) + 0.002
    if w > 0.0 and z < z_floor:
        z += w * (z_floor - z)
    return y, z, th, ta_


class Swing:
    def __init__(self, side, fa, fb, sa, sb, spec):
        self.side, self.fa, self.fb = side, fa, fb
        T = fb - fa
        ky = []
        if sa is not None and spec.get('auto_back'):
            ya = sa.state(fa)[0]
            va = d_dt(lambda f: sa.state(f)[0], fa, 1, side=-1) / FPS                    # y' per frame (negative: the planted foot moves back)
            tb = spec['auto_back']
            ky.append((fa + tb, ya + 0.5 * va * tb, 0.0))
        ky += list(spec['y'])
        if sb is not None and spec.get('auto_fwd'):
            yb = sb.state(fb)[0]
            vb = d_dt(lambda f: sb.state(f)[0], fb, 1, side=1) / FPS
            tf = spec['auto_fwd']
            ky.append((fb - tf, yb - 0.5 * vb * tf, 0.0))
        self.knots_y = ky
        free_a, free_b = spec.get('free_a'), spec.get('free_b')
        py = knot_path(fa, fb, (lambda f: sa.state(f)[0]) if sa else None, (lambda f: sb.state(f)[0]) if sb else None, ky,
                       free_a[0] if free_a else None, free_b[0] if free_b else None)
        ra = (lambda f: ratio_of(f, sa.state(f)[0], sa.state(f)[1], float(Zb(f)))) if sa else None
        rb = (lambda f: ratio_of(f, sb.state(f)[0], sb.state(f)[1], float(Zb(f)))) if sb else None
        pr = knot_path(fa, fb, ra, rb, spec['r'], free_a[1] if free_a else None, free_b[1] if free_b else None)
        self.paths = (py, pr)
        # foot pitch
        pk = spec['pitch']
        if sa is not None:
            xs, ys = [fa] + [k[0] for k in pk], [sa.state(fa)[2]] + [deg(k[1]) for k in pk]
            d0 = d_dt(lambda f: sa.state(f)[2], fa, 1, side=-1) / FPS
        else:
            xs, ys, d0 = [k[0] for k in pk], [deg(k[1]) for k in pk], 0.0
        if sb is not None:
            xs.append(fb)
            ys.append(sb.state(fb)[2])
            dn = d_dt(lambda f: sb.state(f)[2], fb, 1, side=1) / FPS
        else:
            xs.append(fb)
            ys.append(deg(spec.get('end_pitch', -12.0)))
            dn = 0.0
        self.pitch = CSpline(xs, ys, d0=d0, dn=dn)
        # toe bend
        ta = sa.state(fa)[3] if sa else deg(20.0)
        tb_ = sb.state(fb)[3] if sb else deg(14.0)
        if sa is not None and sb is not None:
            self.tau = CSpline([fa, fa + 0.5 * T, fb - 3.0, fb], [ta, deg(24.0), deg(18.0), tb_], d0=0.0, dn=0.0)
        elif sa is None:
            self.tau = CSpline([fa, fa + 6.0, fb - 3.0, fb], [ta, deg(22.0), deg(15.0), tb_], d0=0.0, dn=0.0)
        else:
            self.tau = CSpline([fa, fa + 6.0, fb], [ta, deg(20.0), tb_], d0=0.0, dn=0.0)

    def state(self, f):
        return swing_state(f, self.fa, self.fb, self.paths, self.pitch, self.tau)


SWG = {'R': [], 'L': []}
for _side in 'RL':
    _sts = [s for s in STF if s.side == _side]
    _pts = []
    if _sts[0].td is not None:
        _pts.append((FIRST, None, float(_sts[0].td), _sts[0]))
    for _a, _b in zip(_sts[:-1], _sts[1:]):
        _pts.append((float(_a.to), _a, float(_b.td), _b))
    if _sts[-1].to is not None:
        _pts.append((float(_sts[-1].to), _sts[-1], LAST, None))
    assert len(_pts) == len(PD.SWINGS[_side]), 'swing specs do not match the stances of %s: %d vs %d' % (_side, len(_pts), len(PD.SWINGS[_side]))
    for _k, (_fa, _sa, _fb, _sb) in enumerate(_pts):
        SWG[_side].append(Swing(_side, _fa, _fb, _sa, _sb, PD.SWINGS[_side][_k]))


def foot_state(side, f):
    for st in STF:
        if st.side == side and st.f0 - 1e-9 <= f <= st.f1 + 1e-9:
            return st.state(f)
    for sw in SWG[side]:
        if sw.fa - 1e-9 <= f <= sw.fb + 1e-9:
            return sw.state(f)
    raise RuntimeError('no foot state for %s at frame %s' % (side, f))


def swing_of(side, f):
    for sw in SWG[side]:
        if sw.fa < f < sw.fb:
            return sw
    return None


# ------------------------------------------------------------------ tail: design shape + spring cascade
def tail_design_abs(f):
    s = float(S_TAIL(f))
    return [mix(w_, p_, s) for w_, p_ in zip(PD.tail_walk, PD.tail_sprint)]


def tail_amp(span, i):
    """peak bend (deg) of tail joint i (0-based): grows linearly from span[0] at the base to span[1] at joint 6; the zero-length joints 7 and 8 get nothing"""
    return span[0] + (span[1] - span[0]) * i / 5.0 if i < 6 else 0.0


def compute_tail_tab():
    n = NFD
    lv0 = [PD.lean_share[0] * float(Lean(f)) for f in range(n)]
    yaw = [float(Yaw(f)) for f in range(n)]
    zb = [float(Zb(f)) for f in range(n)]
    zbar = sum(zb) / n
    vv = [V(f) for f in range(n)]
    acc = [(V(f + 0.5) - V(f - 0.5)) * FPS for f in range(n)]
    design = [tail_design_abs(f) for f in range(n)]
    rel_d = []                                                                            # design: relative bend of every joint (joint 1 gives back the hips pitch)
    for f in range(n):
        a = design[f]
        rel_d.append([a[0] - lv0[f]] + [a[i] - a[i - 1] for i in range(1, 8)])
    tab = [[[rel_d[f][i], 0.0] for f in range(n)] for i in range(8)]                      # [joint][frame] = [pitch, yaw]
    # vertical wave: drive = hips pitch + bob of the pelvis + ground acceleration (deg), every joint a spring behind the one before
    p_prev = [lv0[f] + PD.tail_bob_gain * (zb[f] - zbar) - PD.tail_acc_gain * acc[f] for f in range(n)]
    w_prev = yaw
    peaks = []
    for i in range(6):
        wi = PD.tail_w * (1.0 - 0.03 * (i + 1))
        p_cur = lp_seq(p_prev, wi * 0.8, 0.35)
        diff = [p_cur[f] - p_prev[f] for f in range(n)]
        amp = max(1e-9, max(abs(v) for v in diff))
        a_i = tail_amp(PD.tail_vert, i)
        w_cur = lp_seq(w_prev, wi, PD.tail_z)
        dw = [w_cur[f] - w_prev[f] for f in range(n)]
        wamp = max(1e-9, max(abs(v) for v in dw))
        a_w = tail_amp(PD.tail_lat, i)
        for f in range(n):
            tab[i][f][0] += a_i * diff[f] / amp
            tab[i][f][1] = a_w * dw[f] / wamp
        peaks.append((a_i, a_w))
        p_prev, w_prev = p_cur, w_cur
    dlog('tail: spring cascade, peak pitch wave per joint %s deg, lateral %s deg' % ([round(p[0], 1) for p in peaks], [round(p[1], 1) for p in peaks]))
    return tab


TAIL_TAB = compute_tail_tab()


# ------------------------------------------------------------------ pose at frame f
def arm_state(f, side):
    """(upper arm swing from the plumb line, elbow flexion, upper arm outward angle, forearm outward angle) in radians; the right arm and the left arm are mirror images"""
    s = float(S_ARM(f))
    n = float(ARM_N(f)) * (1.0 if side == 'R' else -1.0)
    mean, amp = mix(PD.ARM_MEAN[0], PD.ARM_MEAN[1], s), mix(PD.ARM_AMP[0], PD.ARM_AMP[1], s)
    sig = mean + amp * n
    e = mix(PD.ELBOW_MID[0], PD.ELBOW_MID[1], s) + PD.ELBOW_K * amp * n
    kf = 0.5 * (n + 1.0)                                                                   # 1 = furthest forward
    a_u = mix(PD.HANG[0], PD.HANG[1] + (PD.HANG[2] - PD.HANG[1]) * kf, s)
    a_f = mix(PD.FORE[0], PD.FORE[1] + (PD.FORE[2] - PD.FORE[1]) * kf, s)
    return deg(sig), deg(e), deg(a_u), deg(a_f)


def solve_d(f):
    rel, absd = {}, {}
    hips_rest = HEAD0[H['hips']]
    lean = float(Lean(f))
    lv = [s * lean for s in PD.lean_share]
    yaw, roll = float(Yaw(f)), float(Roll(f))
    rel[H['hips']] = eul(rx=-lv[0], ry=roll, rz=yaw)
    prev = (lv[0], roll, yaw)
    ch_yaw = -PD.chest_counter * yaw
    ch_roll = -0.5 * roll
    for name_, k_, cur_p in zip((H['spine'], H['chest'], H['upperChest']), (0.4, 0.8, 1.0), lv[1:]):
        cur = (cur_p, roll + (ch_roll - roll) * k_, yaw + (ch_yaw - yaw) * k_)
        rel[name_] = eul(rx=-(cur[0] - prev[0]), ry=cur[1] - prev[1], rz=cur[2] - prev[2])
        prev = cur
    hips_d = Vector((float(Xs(f)), 0.0, float(Zb(f)) - hips_rest.z))
    # neck and head: the gaze stays ahead while the trunk dives (world pitch, forward positive = negative rx)
    absd[H['neck']] = eul(rx=-PD.neck_share * lean, rz=0.5 * ch_yaw)
    absd[H['head']] = eul(rx=-PD.head_share * lean, rz=0.3 * ch_yaw)
    for side, sx in (('L', -1.0), ('R', 1.0)):
        rel[nm(side, 'Shoulder')] = eul(ry=sx * 4.0)
    # arms: absolute directions (like build_run): swing from the plumb line, elbow bent, fists at chest height in the sprint
    s_arm = float(S_ARM(f))
    for side, sx in (('L', -1.0), ('R', 1.0)):
        sig_u, e_fl, a_u, a_f = arm_state(f, side)
        b_f = sig_u + e_fl
        rest_dir, rest_nrm = Vector((sx, 0, 0)), Vector((0, 0, -1))
        d0 = Vector((sx * math.sin(a_u), 0.0, -math.cos(a_u)))
        cs, sn = math.cos(sig_u), math.sin(sig_u)
        d_u = Vector((d0.x, d0.y * cs - d0.z * sn, d0.y * sn + d0.z * cs))
        d_f = Vector((sx * math.sin(a_f), math.sin(b_f), -math.cos(b_f) * math.cos(a_f)))
        b_h = b_f + deg(4.0)
        d_h = Vector((sx * math.sin(0.5 * a_f), math.sin(b_h), -math.cos(b_h)))
        absd[nm(side, 'UpperArm')] = aim(rest_dir, rest_nrm, d_u, Vector((-sx, -0.15, 0.0)))
        absd[nm(side, 'LowerArm')] = aim(rest_dir, rest_nrm, d_f, Vector((-sx, -0.12, 0.0)))
        absd[nm(side, 'Hand')] = aim(rest_dir, rest_nrm, d_h, Vector((-sx, -0.22, 0.0)))
        for fn in PD.fingers_run:
            for pj, part in enumerate(PARTS):
                c = mix(PD.fingers_walk[fn][pj], PD.fingers_run[fn][pj], s_arm)
                rel[nm(side, fn + part)] = Quaternion((0, 1, 0), deg(sx * c))
        rel[nm(side, 'ThumbProximal')] = eul(rz=-sx * PD.thumb_add) @ Quaternion((0, 1, 0), deg(sx * 10.0))
        rel[nm(side, 'ThumbIntermediate')] = Quaternion((0, 1, 0), deg(sx * 18.0))
        rel[nm(side, 'ThumbDistal')] = Quaternion((0, 1, 0), deg(sx * 12.0))
    # tail: design shape + spring cascade (tables per frame)
    fi = min(max(int(round(f)), 0), NFD - 1)
    for i in range(1, 9):
        pit, yw = TAIL_TAB[i - 1][fi]
        rel['J_Opt_C_CatTail%d_01' % i] = eul(rx=-pit, rz=yw)
    # legs: ankle targets in place (y' + hips y), narrow track, swing foot goes out a little
    legs = {}
    for side, sx in (('R', 1.0), ('L', -1.0)):
        y_, z_, th_, tau_ = foot_state(side, f)
        sw = swing_of(side, f)
        circ = PD.CIRC * (0.5 - 0.5 * math.cos(math.pi * 2.0 * (f - sw.fa) / (sw.fb - sw.fa))) if sw else 0.0
        x_ = sx * (PD.BASE + circ)
        legs[side] = (Vector((x_, hips_rest.y + y_, z_)), eul(rx=math.degrees(th_)), 0.0, tau_, 0.0)
        rel[nm(side, 'Toes')] = eul(rx=math.degrees(tau_))
    return rel, absd, hips_d, legs, {'reach_deficit': 0.0, 'lean': lean, 'lv': lv}


SPR_DIRS, SPR_AXES = None, None


def compute_pose_d(f):
    rel, absd, hips_d, legs, diag = solve_d(f)
    D, Q, ik = {}, {}, {}
    hips_name = H['hips']
    fi = min(max(int(round(f)), 0), NFD - 1)
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        if SPR_DIRS is not None and name in SPR_DIRS:                         # spring bone: the axis points where the simulation put it
            D[name] = (Dp @ SPR_AXES[name]).rotation_difference(SPR_DIRS[name][fi]) @ Dp
        elif name in rel:
            D[name] = Dp @ rel[name]
        elif name in absd:
            D[name] = absd[name]
        else:
            D[name] = Dp.copy()
        for side in ('L', 'R'):
            if name == nm(side, 'UpperLeg'):
                Hp0 = HEAD0[name]
                hip_head = HEAD0[hips_name]
                Hp = hip_head + hips_d + D[hips_name] @ (Hp0 - hip_head)
                K0, A0_ = HEAD0[nm(side, 'LowerLeg')], HEAD0[nm(side, 'Foot')]
                L1, L2 = (K0 - Hp0).length, (A0_ - K0).length
                T, foot_rot, yaw, tau, phi = legs[side]
                pole = Vector((-math.sin(deg(yaw)), math.cos(deg(yaw)), 0.0))
                K, Teff, deficit, ext = two_bone_ik(Hp, T, pole, L1, L2)
                diag['reach_deficit'] = max(diag['reach_deficit'], deficit)
                diag['ext_' + side] = ext
                a1, a2 = (Hp - K).normalized(), (Teff - K).normalized()
                diag['knee_' + side] = 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, a1.dot(a2)))))
                ik[side] = (K, Teff)
                D[name] = (K0 - Hp0).rotation_difference(K - Hp)
            elif name == nm(side, 'LowerLeg'):
                K0, A0_ = HEAD0[name], HEAD0[nm(side, 'Foot')]
                K, Teff = ik[side]
                D[name] = (A0_ - K0).rotation_difference(Teff - K)
            elif name == nm(side, 'Foot'):
                D[name] = legs[side][1]
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    return Q, R[hips_name].inverted() @ hips_d, D, diag, hips_d


def fk_positions(D, hips_d):
    pos = {}
    for name in order:
        b = bones[name]
        if name == H['hips']:
            pos[name] = HEAD0[name] + hips_d
        elif b.parent is None:
            pos[name] = HEAD0[name].copy()
        else:
            pn = b.parent.name
            pos[name] = pos[pn] + D[pn] @ (HEAD0[name] - HEAD0[pn])
    return pos


# ------------------------------------------------------------------ hair, ears, bust: spring bones of the VRM (verlet) on the finished motion
NODE_OF = {n_['name']: i_ for i_, n_ in enumerate(nodes)}
VRM_SEC = js['extensions']['VRM']['secondaryAnimation']


def fromto_mats(a, b):
    """rotation matrices (n, 3, 3) that turn the unit vectors a (n, 3) onto the unit vectors b (n, 3) by the shortest way"""
    v = np.cross(a, b)
    c = np.einsum('ij,ij->i', a, b)
    n = a.shape[0]
    K = np.zeros((n, 3, 3))
    K[:, 0, 1], K[:, 0, 2] = -v[:, 2], v[:, 1]
    K[:, 1, 0], K[:, 1, 2] = v[:, 2], -v[:, 0]
    K[:, 2, 0], K[:, 2, 1] = -v[:, 1], v[:, 0]
    k = 1.0 / np.maximum(1.0 + c, 1e-6)
    return np.eye(3)[None] + K + np.einsum('nij,njk->nik', K, K) * k[:, None, None]


def simulate_springs():
    """bust, hair and cat ears with the spring bone algorithm of the VRM (UniVRM), as in build_run.py:  next = current + (current - previous) * (1 - drag)
    + parent rotation * rest axis * stiffness * dt + (gravity + wind) * dt, then the bone length is restored and the hair is pushed out of the collider spheres.
    One shot: PD.spring_pre frames of walking at the speed of frame 0 come first (settling), then the dash with its real world travel; the wind grows with the speed."""
    dt = 1.0 / FPS
    PRE = PD.spring_pre
    names, parent, depth, axis, length, stiff, drag, hit, coll, kind, rootpar = [], [], [], [], [], [], [], [], [], [], []
    sphere_src = {}
    for g in VRM_SEC['boneGroups']:
        kd = g.get('comment', '')
        if kd not in ('Bust', 'CatEar', 'Hair'):
            continue
        st, dr = g.get('stiffiness', 0.5), g.get('dragForce', 0.4)
        if kd == 'Bust':
            st, dr = PD.bust_stiff, PD.bust_drag
        elif kd == 'CatEar':
            st, dr = PD.ear_stiff, PD.ear_drag
        else:
            st, dr = st * PD.hair_stiff_mul, PD.hair_drag
        cg = g.get('colliderGroups') or []
        for ci in cg:
            sphere_src[ci] = True
        for root_idx in g['bones']:
            rname = nodes[root_idx]['name']
            if rname not in bones or bones[rname].parent is None:
                continue
            chain = [rname]
            b = bones[rname]
            while b.children:
                b = b.children[0]
                chain.append(b.name)
            first = len(names)
            for k, bn in enumerate(chain):
                head = HEAD0[bn]
                if k + 1 < len(chain):
                    off = HEAD0[chain[k + 1]] - head
                elif nodes[NODE_OF[bn]].get('children'):
                    off = bones[bn].tail_local - bones[bn].head_local
                else:
                    off = (head - HEAD0[bones[bn].parent.name]).normalized() * 0.07
                names.append(bn)
                parent.append(first + k - 1 if k > 0 else -1)
                depth.append(k)
                axis.append(np.array(off.normalized()))
                length.append(off.length)
                stiff.append(st)
                drag.append(dr)
                hit.append(g.get('hitRadius', 0.02))
                coll.append(bool(cg))
                kind.append(kd)
                rootpar.append(bones[rname].parent.name if k == 0 else None)
    N = len(names)
    axis, length, stiff, drag, hit = np.array(axis), np.array(length), np.array(stiff), np.array(drag), np.array(hit)
    coll, parent, depth = np.array(coll), np.array(parent), np.array(depth)
    roots = [i for i in range(N) if parent[i] < 0]
    root_slot = {i: k for k, i in enumerate(roots)}
    by_depth = [np.array([i for i in range(N) if depth[i] == d]) for d in range(int(depth.max()) + 1)]
    spheres = []
    for ci in sorted(sphere_src):
        cgrp = VRM_SEC['colliderGroups'][ci]
        bn = nodes[cgrp['node']]['name']
        for c_ in cgrp['colliders']:
            o_ = c_['offset']
            spheres.append((bn, Vector((o_['x'], -o_['z'], o_['y'])), c_['radius']))
    M = len(spheres)
    sph_r = np.array([r_ for (_, _, r_) in spheres])
    # the moving parents: root joints, parent rotations and collider centres at every sample (in place) + the world travel
    T = PRE + NFD
    root_pos = np.zeros((T, len(roots), 3))
    root_R = np.zeros((T, len(roots), 3, 3))
    sph_c = np.zeros((T, M, 3))
    shift = np.zeros((T, 3))                     # in place: the world travel is replaced by the inertial push of the acceleration and by the wind (a constant
                                                 # velocity in the world frame would only act as a drag on the strands)
    wscale = np.zeros(T)
    accv = np.zeros(T)
    global SPR_DIRS, SPR_AXES
    SPR_DIRS, SPR_AXES = None, None
    for k in range(T):
        f_ = float(k - PRE)
        Q_, hl_, D_, dg_, hd_ = compute_pose_d(max(f_, 0.0))
        pos_ = fk_positions(D_, hd_)
        for i in roots:
            root_pos[k, root_slot[i]] = np.array(pos_[names[i]])
            root_R[k, root_slot[i]] = np.array(D_[rootpar[i]].to_matrix())
        for j, (bn, off, r_) in enumerate(spheres):
            sph_c[k, j] = np.array(pos_[bn] + D_[bn] @ off)
        wscale[k] = (V(max(f_, 0.0)) / 5.0) ** PD.wind_exp
        accv[k] = (V(max(f_, 0.0) + 0.5) - V(max(f_ - 0.5, 0.0))) * FPS if f_ > 0.0 else 0.0
    cur = np.zeros((N, 3))
    R_new = np.zeros((N, 3, 3))
    for d_idx in by_depth:
        for i in d_idx:
            if parent[i] < 0:
                head, Rp = root_pos[0, root_slot[i]] + shift[0], root_R[0, root_slot[i]]
            else:
                head, Rp = cur[parent[i]], R_new[parent[i]]
            cur[i] = head + Rp @ axis[i] * length[i]
            R_new[i] = Rp
    prev = cur.copy()
    wind = np.zeros((N, 3))
    for i in range(N):
        w_ = {'Hair': PD.wind_hair, 'CatEar': PD.wind_ear}.get(kind[i], 0.0)
        wind[i] = (0.0, -w_, w_ * PD.wind_lift)
    kp_arr = np.array([{'Hair': PD.pseudo_hair, 'CatEar': PD.pseudo_ear, 'Bust': PD.pseudo_bust}[kind[i]] for i in range(N)])
    rec_dir = np.zeros((NFD, N, 3))
    rec_def = np.zeros((NFD, N))
    for k in range(T):
        new_tail = np.zeros((N, 3))
        heads = np.zeros((N, 3))
        axis_w_all = np.zeros((N, 3))
        push = np.zeros((N, 3))
        push[:, 1] = -accv[k] * dt * kp_arr
        grav = (wind * wscale[k] + push) * dt
        for d_idx in by_depth:
            if parent[d_idx[0]] < 0:
                slots = [root_slot[i] for i in d_idx]
                head = root_pos[k, slots] + shift[k]
                Rp = root_R[k, slots]
            else:
                pi = parent[d_idx]
                head = new_tail[pi]
                Rp = R_new[pi]
            a_w = np.einsum('nij,nj->ni', Rp, axis[d_idx])
            cu, pv = cur[d_idx], prev[d_idx]
            nx = cu + (cu - pv) * (1.0 - drag[d_idx])[:, None] + a_w * (stiff[d_idx] * dt)[:, None] + grav[d_idx]
            v_ = nx - head
            nx = head + v_ / np.linalg.norm(v_, axis=1, keepdims=True) * length[d_idx][:, None]
            sel = np.nonzero(coll[d_idx])[0]
            if len(sel) and M and PD.spring_coll:
                for j in range(M):
                    c_ = sph_c[k, j] + shift[k]
                    rr = sph_r[j] + hit[d_idx[sel]]
                    dv = nx[sel] - c_
                    dist = np.linalg.norm(dv, axis=1)
                    hm = dist <= rr
                    if hm.any():
                        tgt = c_ + dv[hm] / np.maximum(dist[hm], 1e-9)[:, None] * rr[hm][:, None]
                        w_ = tgt - head[sel][hm]
                        nx[sel[hm]] = head[sel][hm] + w_ / np.linalg.norm(w_, axis=1, keepdims=True) * length[d_idx][sel][hm][:, None]
            new_tail[d_idx] = nx
            heads[d_idx] = head
            axis_w_all[d_idx] = a_w
            dirn = (nx - head) / length[d_idx][:, None]
            R_new[d_idx] = np.einsum('nij,njk->nik', fromto_mats(a_w, dirn), Rp)
        prev, cur = cur, new_tail
        if k >= PRE:
            f_ = k - PRE
            rec = (cur - heads) / length[:, None]
            rec_dir[f_] = rec
            rec_def[f_] = np.degrees(np.arccos(np.clip(np.einsum('ni,ni->n', rec, axis_w_all), -1.0, 1.0)))
    for _ in range(PD.spring_smooth):                                          # [1 2 1] / 4 along the frames: takes the sharpest corners off the impacts
        sm = rec_dir.copy()
        sm[1:-1] = 0.25 * rec_dir[:-2] + 0.5 * rec_dir[1:-1] + 0.25 * rec_dir[2:]
        rec_dir = sm / np.linalg.norm(sm, axis=2, keepdims=True)
    stp = np.degrees(np.arccos(np.clip(np.einsum('fni,fni->fn', rec_dir[1:], rec_dir[:-1]), -1.0, 1.0)))
    dlog('springs: change of direction per frame: largest %.1f deg, %d of %d bones over 12 deg / frame, %d over 20' % (float(stp.max()), int((stp.max(axis=0) > 12.0).sum()), N, int((stp.max(axis=0) > 20.0).sum())))
    top = sorted(range(N), key=lambda i: -stp[:, i].max())[:6]
    dlog('springs: largest steps: ' + '; '.join('%s %.0f deg at frame %d (%s)' % (names[i], stp[:, i].max(), int(stp[:, i].argmax()) + 1, kind[i]) for i in top))
    for kd in ('Bust', 'CatEar', 'Hair'):
        sel_ = [i for i in range(N) if kind[i] == kd]
        dlog('springs: %s per-frame change: mean of the largest %.1f deg, largest %.1f deg, bones over 15: %d of %d' % (kd, float(np.mean([stp[:, i].max() for i in sel_])), float(max(stp[:, i].max() for i in sel_)), sum(1 for i in sel_ if stp[:, i].max() > 15.0), len(sel_)))
    SPR_DIRS = {names[i]: [Vector(rec_dir[f_, i]) for f_ in range(NFD)] for i in range(N)}
    SPR_AXES = {names[i]: Vector(axis[i]) for i in range(N)}
    rep_ = {'bones': N, 'spheres': M}
    for kd in ('Bust', 'CatEar', 'Hair'):
        sel_ = [i for i in range(N) if kind[i] == kd]
        rep_[kd] = (float(rec_def[:, sel_].max()), float(rec_def[:, sel_].mean())) if sel_ else (0.0, 0.0)
    dlog('springs: %d bones, %d collider spheres; deflection from the bone axis (max / mean deg): bust %.1f / %.1f, ears %.1f / %.1f, hair %.1f / %.1f; wind at the peak speed x %.2f' % (
        N, M, rep_['Bust'][0], rep_['Bust'][1], rep_['CatEar'][0], rep_['CatEar'][1], rep_['Hair'][0], rep_['Hair'][1], float(wscale.max())))
    return rep_


SPRING_REP = None
if USE_SPRINGS:
    SPRING_REP = simulate_springs()
    dlog('springs simulated')


# ------------------------------------------------------------------ keys
def build_action():
    if arm.animation_data and arm.animation_data.action:
        old = arm.animation_data.action
        arm.animation_data.action = None
        bpy.data.actions.remove(old)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
    keyed = None
    prev = {}
    out, diags = [], []
    for f in range(NFD):
        Q, hips_loc, D, diag, hips_d = compute_pose_d(float(f))
        diags.append(diag)
        if keyed is None:
            keyed = [n for n in order if n in hum_names or n in EXTRA]
        for n in keyed:
            q = Q[n]
            if n in prev and prev[n].dot(q) < 0:
                q = -q
            prev[n] = q
            pb = arm.pose.bones[n]
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=f)
        pbh = arm.pose.bones[H['hips']]
        pbh.location = hips_loc
        pbh.keyframe_insert('location', frame=f)
        pbt = arm.pose.bones['J_Opt_C_CatTail1_01']
        pbt.scale = (PD.tail_scale,) * 3
        pbt.keyframe_insert('scale', frame=f)
        out.append({'frame': f, 'hips_world_offset': list(hips_d), 'D': {n: [D[n].w, D[n].x, D[n].y, D[n].z] for n in H.values()}, '_D': D, '_hips_d': hips_d})
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action.name = 'Yoru_DodgeWalk'
        arm.animation_data.action.use_fake_user = True
        set_linear(arm.animation_data.action)
    return out, diags


frames_data, DIAGS = build_action()
dlog('keys built: %d frames' % NFD)


# ------------------------------------------------------------------ report
def report():
    rep = {}
    rep['reach_deficit_mm_max'] = 1000.0 * max(d['reach_deficit'] for d in DIAGS)
    for side in ('L', 'R'):
        ks = [d['knee_' + side] for d in DIAGS]
        es = [d['ext_' + side] for d in DIAGS]
        rep['knee_%s_deg' % side] = (min(ks), max(ks))
        rep['leg_ratio_%s' % side] = (min(es), max(es))
    hz = [Zb(f) for f in range(NFD)]
    rep['pelvis_z_m'] = (min(hz), max(hz))
    rep['travel_m'] = S(LAST)
    rep['speed_ms'] = (min(V(f) for f in range(NFD)), max(V(f) for f in range(NFD)))
    # planted contact: ankle (flat) / toe joint (rolling) in the ground frame during every stance
    slip = {}
    for k, st in enumerate(STF):
        name_foot, name_toe = nm(st.side, 'Foot'), nm(st.side, 'Toes')
        ya, yt = [], []
        for f in range(int(math.ceil(st.f0)), int(math.floor(st.f1)) + 1):
            pos = fk_positions(frames_data[f]['_D'], frames_data[f]['_hips_d'])
            th = st.state(float(f))[2]
            if th >= 0.0:
                ya.append(pos[name_foot].y + S(f))
            else:
                yt.append(pos[name_toe].y + S(f))
        slip['stance %d %s ankle' % (k + 1, st.side)] = 1000.0 * (max(ya) - min(ya)) if len(ya) > 1 else 0.0
        slip['stance %d %s toe joint' % (k + 1, st.side)] = 1000.0 * (max(yt) - min(yt)) if len(yt) > 1 else 0.0
    rep['planted_slip_mm'] = slip
    names = list(H.values())
    steps = {}
    for n in names:
        qs = [frames_data[f]['_D'][n] for f in range(NFD)]
        st_ = [math.degrees(2.0 * math.acos(min(1.0, abs(qs[i + 1].dot(qs[i]))))) for i in range(NFD - 1)]
        ch = [abs(st_[i + 1] - st_[i]) for i in range(len(st_) - 1)]
        steps[n] = (max(st_), max(ch), int(np.argmax(st_)))
    rep['bone_steps'] = steps
    # the points of the critique, as numbers
    rep['stance_travel_m'] = [(S(st.f1) - S(st.f0)) for st in STF]
    sr = []
    for st in STF:
        sr.append(max(DIAGS[f]['ext_' + st.side] for f in range(int(math.ceil(st.f0)), int(math.floor(st.f1)) + 1)))
    rep['stance_leg_ratio_max'] = sr
    acc = [(V(f + 0.5) - V(f - 0.5)) * FPS for f in range(NFD)]
    rep['accel_ms2'] = (min(acc), max(acc))
    rep['pelvis_dip_start_mm'] = 1000.0 * (Zb(0) - min(Zb(f) for f in range(0, 7)))
    rep['lean_deg'] = {f: float(Lean(f)) for f in (0, 2, 4, 6, 12, 20, 32, 44, 47)}
    elb, swing = [], []
    for side in ('L', 'R'):
        for f in range(NFD):
            sg, e, _, _ = arm_state(float(f), side)
            elb.append(math.degrees(e))
            swing.append(math.degrees(sg))
    rep['elbow_deg'] = (min(elb), max(elb))
    rep['arm_swing_deg'] = (min(swing), max(swing))
    tp = []
    for i in range(8):
        tp.append(max(TAIL_TAB[i][f][0] for f in range(NFD)) - min(TAIL_TAB[i][f][0] for f in range(NFD)))
    rep['tail_pitch_pp_deg'] = tp
    return rep


REP = report()
if DEBUG_TABLE:
    dlog('frame |  v m/s  S m | hipsZ | R ankle y z th | ratio knee | L ankle y z th | ratio knee')
    for f in range(NFD):
        sR, sL = foot_state('R', f), foot_state('L', f)
        d = DIAGS[f]
        dlog('f%02d | %5.2f %5.2f | %.3f | %+.3f %.3f %+4.0f | %.3f %3.0f | %+.3f %.3f %+4.0f | %.3f %3.0f' % (
            f, V(f), S(f), Zb(f), sR[0], sR[1], math.degrees(sR[2]), d['ext_R'], d['knee_R'], sL[0], sL[1], math.degrees(sL[2]), d['ext_L'], d['knee_L']))
dlog('reach deficit max %.2f mm | knee L %.0f..%.0f R %.0f..%.0f deg | leg ratio L %.3f..%.3f R %.3f..%.3f | pelvis z %.3f..%.3f | travel %.2f m | speed %.1f..%.1f m/s' % (
    REP['reach_deficit_mm_max'], *REP['knee_L_deg'], *REP['knee_R_deg'], *REP['leg_ratio_L'], *REP['leg_ratio_R'], *REP['pelvis_z_m'], REP['travel_m'], *REP['speed_ms']))
dlog('planted contact slip (mm): ' + ', '.join('%s %.1f' % (k, v) for k, v in REP['planted_slip_mm'].items() if v > 0.0))
dlog('stance travel (m): ' + ', '.join('%.2f' % v for v in REP['stance_travel_m']) + ' | ground acceleration %.1f .. %.1f m/s2' % REP['accel_ms2'] + ' | longest support leg ratio per stance: ' + ', '.join('%.3f' % v for v in REP['stance_leg_ratio_max']))
dlog('critique: pelvis dip in the first 6 frames %.0f mm | lean %s | elbow %.0f..%.0f deg | arm swing %.0f..%.0f deg | tail pitch range per joint %s deg' % (
    REP['pelvis_dip_start_mm'], {k: round(v) for k, v in REP['lean_deg'].items()}, *REP['elbow_deg'], *REP['arm_swing_deg'], [round(v) for v in REP['tail_pitch_pp_deg']]))
_groups = {'legs': [nm(s, p) for s in 'LR' for p in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')], 'trunk': [H['hips'], H['spine'], H['chest'], H['upperChest']],
           'head': [H['neck'], H['head']], 'arms': [nm(s, p) for s in 'LR' for p in ('UpperArm', 'LowerArm', 'Hand')]}
for g, ns in _groups.items():
    worst = max(ns, key=lambda n: REP['bone_steps'][n][0])
    dlog('steps %-5s: largest %.1f deg / frame (%s, frame %d), largest change of step %.1f' % (g, REP['bone_steps'][worst][0], worst, REP['bone_steps'][worst][2], max(REP['bone_steps'][n][1] for n in ns)))
over8 = sorted([(v[0], k) for k, v in REP['bone_steps'].items() if v[0] > 8.0], reverse=True)
dlog('bones over 8 deg / frame: %d  %s' % (len(over8), ', '.join('%s %.1f (f%d)' % (k, v, REP['bone_steps'][k][2]) for v, k in over8[:12])))

# ------------------------------------------------------------------ outputs
speed_pf = [V(f) for f in range(NFD)]
summary = {'frames': NFD, 'fps': FPS, 'seconds': (NFD - 1) / FPS, 'travel_m': S(LAST), 'speed_per_frame': speed_pf, 'travel_per_frame': [S(f) for f in range(NFD)],
           'stances': [{'side': st.side, 'td': st.td, 'to': st.to} for st in STF],
           'note': 'ground speed of the pelvis (m/s) and travelled distance per frame; the character controller replays this curve during the dodge (clip is in place)',
           'report': {k: (list(v) if isinstance(v, tuple) else v) for k, v in REP.items() if k not in ('bone_steps', 'lean_deg')}}
with open(os.path.join(OUT, 'Yoru_DodgeWalk_gait.json'), 'w') as fh:
    json.dump(summary, fh, indent=1)
with open(os.path.join(OUT, 'Yoru_DodgeWalk_pose.json'), 'w') as fh:
    json.dump({'fps': FPS, 'frames': NFD, 'loop_seconds': (NFD - 1) / FPS, 'speed': 0.0, 'note': 'D = world-space rotation delta from the T-pose per humanoid bone (Blender axes: +Y forward, -X = her left); in place',
               'humanoid_map': H, 'hips_rest': list(HEAD0[H['hips']]), 'data': [{'frame': d['frame'], 'hips_world_offset': d['hips_world_offset'], 'D': d['D']} for d in frames_data]}, fh)


def make_floor():
    mat = bpy.data.materials.new('floor')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n_ for n_ in nt.nodes if n_.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    ck = nt.nodes.new('ShaderNodeTexChecker')
    ck.inputs['Scale'].default_value = 2.0                           # 0.5 m cells
    ck.inputs['Color1'].default_value = (0.42, 0.46, 0.52, 1.0)
    ck.inputs['Color2'].default_value = (0.22, 0.25, 0.30, 1.0)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], ck.inputs['Vector'])
    nt.links.new(ck.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.9
    bpy.ops.mesh.primitive_plane_add(size=10.0, location=(0, 0, -0.001))
    fl = bpy.context.active_object
    fl.name = 'Floor_scrolling'
    fl.data.materials.append(mat)
    loc = mp.inputs['Location']
    for f_ in range(NFD):
        loc.default_value = (0.0, S(f_), 0.0)
        loc.keyframe_insert('default_value', index=1, frame=f_)
    ad = mat.node_tree.animation_data
    if ad and ad.action:
        set_linear(ad.action)
    return fl


try:
    make_floor()
    dlog('floor with scrolling checker added')
except Exception as e:
    dlog('floor not added:', repr(e)[:200])
scene.frame_start, scene.frame_end = 0, NFD - 1
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Yoru_DodgeWalk.blend'))
dlog('saved', os.path.join(OUT, 'Yoru_DodgeWalk.blend'))
dlog('DONE')
