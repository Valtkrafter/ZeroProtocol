"""
Yoru - WALK v2: the gait library (no side effects on import; live and background).
Round 1: three SWAGGER variants A / B / C.  They differ ONLY in the swagger: hip rotation, pelvic tilt (hip drop), counter-rotation of the
shoulders, lateral hip sway and the track width of the feet.  Tempo, step length, arms, head, tail and face are the same in all three.

Cycle: NF = 29 frames at 30 fps = 0.967 s for two steps (cadence 124 steps/min); 1.2 m/s -> stride 1.16 m, step 0.58 m.
She walks IN PLACE (the armature object stays put); the floor of build_walk_v2_stage.py moves backwards at 1.2 m/s.  A planted foot moves
backwards at exactly 1.2 m/s in armature space, so it stays on its floor tile.  Phase phi = frame / NF: right heel strike at phi 0, left at 0.5.

Foot roll (local phase psi of one foot, 0 = its heel strike):
  0    .. psi1  heel rocker: the foot turns down about the back edge of the boot heel, which rides on the floor (smoothstep, soft contact)
  psi1 .. psi2  flat
  psi2 .. beta  heel-off: the foot turns up about the TOE JOINT, the toes stay flat on the floor
  beta .. 1     swing: Hermite curves that meet position and speed of the ankle at toe-off and at the next heel strike (no kink), plus a lift
                and an outward arc so the swinging boot passes the standing one; the foot pitch follows a spline, the toes straighten.
Legs: two-bone IK from the posed hip joint to the ankle; the pelvis height is the highest one that keeps the knee bent by at least
knee_min deg in every frame (the standing knee is never locked).
Bones (as build_idle_v2_lib.py): a world-space rotation delta D per bone relative to the T-pose, basis Q = R^-1 Dp^-1 D R.
Arms: hinge model in the frame of the chest's heading: upper arm abduction + swing, elbow flexion about the hinge, forearm roll = hinge roll
plus at most 18 deg towards the palm (no twist bones in this rig), the hand trails the swing a little.  Small swing, close to the gear.

Live:   ns = {'__file__': <this file>}; exec(open(<this file>, encoding='utf-8').read(), ns)
        info = ns['bake_variant'](bpy.data.objects['Yoru_Walk_B'], 'B')
Blender axes for Yoru: +Y forward, her right = +X, up = +Z.
"""
import bpy, os, math, sys, time
from mathutils import Vector, Quaternion, Euler, Matrix

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_idle_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'


def _load(name):
    ns = {'__file__': os.path.join(_HERE, name)}
    exec(compile(open(os.path.join(_HERE, name), encoding='utf-8').read(), os.path.join(_HERE, name), 'exec'), ns)
    return ns


L = _load('build_idle_v2_lib.py')
eul, aim, perp, two_bone_ik = L['eul'], L['aim'], L['perp'], L['two_bone_ik']

FPS = 30
NF = 29
T = NF / float(FPS)
SPEED = 1.2
STRIDE = SPEED * T                 # 1.16 m per cycle (per unit of phase)
TAU = 2.0 * math.pi
HEEL_BACK_Y = -0.079               # back edge of the boot heel on the floor (rest pose, measured on the mesh)
FINGERS = ('Index', 'Middle', 'Ring', 'Little')
PARTS = ('Proximal', 'Intermediate', 'Distal')
# face B 'kuehl-wachsam' (same values as EXPRESSIONS['B'] in build_idle_v2_face.py)
FACE_B = {'Fcl_EYE_Angry': 0.40, 'Fcl_EYE_Fun': 0.16, 'Fcl_MTH_Neutral': 0.55, 'Fcl_MTH_Close': 0.20, 'Fcl_BRW_Angry': 0.50}

WALK = dict(
    # feet
    beta=0.60, psi1=0.10, psi2=0.30,            # toe-off, foot flat, heel-off (fractions of the cycle after the heel strike)
    theta_hs=13.0, theta_to=42.0,               # deg: toes up at the heel strike, heel up at toe-off
    toe_out=5.0,                                # deg
    heel_y=0.24,                                # m: the back edge of the heel touches down this far in front of the hip joints
    swing_peak_u=0.25, swing_peak_z=0.195, swing_mid_z=0.148,   # ankle height in the swing (m): early peak, low and level pass
    pass_clear=0.106,                           # m: centre-to-centre distance of the boots when the swinging one passes (boot 92 mm wide)
    knee_min=6.0, knee_min_swing=4.5,           # deg: least knee bend of the standing / the swinging leg (IK clamps at 3.6) -> pelvis height
    # pelvis and spine
    bob=0.030, bob_low=0.0,                     # m peak-to-peak (smooth, sinusoidal), lowest at each heel strike, highest at mid-stance
    pelvis_pitch=0.5,                           # deg, twice per cycle
    lean=(-3.0, 1.5, 1.5, 0.0),                 # deg about X per bone hips / spine / chest / upperChest (+ = top tips back)
    roll_over=0.25, chest_lag=0.02,             # the chest counter-rolls 25 % beyond level (shoulder line against the hips)
    chest_spring=0.6, spring_lag=0.06,          # deg: the rib cage gives a little after each heel strike
    head_pitch=-5.0, neck_share=0.45, head_follow=0.08,
    shoulder_drop=4.0, shoulder_back=3.0, shoulder_prot=2.0, shoulder_settle=0.6,
    # arms (same in every variant)
    arm_ab={'R': 12.0, 'L': 12.0},              # deg out from hanging straight down (the gear holds the arm off the hip)
    arm_ab_swing=4.0, arm_carry_swing=4.0,      # deg: further out at the back of the swing, further in at the front
    arm_swing0=8.0, arm_swing=4.0,              # deg: upper arm forward at rest, swing amplitude (small)
    elbow0=24.0, elbow_swing=10.0,              # deg: elbow bend at the back of the swing, extra bend at the front
    arm_carry={'R': 12.0, 'L': 12.0},           # deg: forearm leans out beyond the upper arm (carrying angle), fitted against the gear
    arm_lag=0.04,                               # phase lag of the arms behind the legs
    palm_back=0.25, twist_max=18.0,
    hand_flex=8.0, hand_dev=4.0, hand_flop=6.0, hand_lag=0.10, wrist_max=40.0,
    finger_curl={'R': {'Index': (10, 18, 12), 'Middle': (16, 26, 16), 'Ring': (20, 30, 18), 'Little': (26, 34, 20)},
                 'L': {'Index': (10, 18, 12), 'Middle': (16, 26, 16), 'Ring': (20, 30, 18), 'Little': (26, 34, 20)}},
    thumb={'R': (-18.0, -10.0, -8.0), 'L': (-18.0, -10.0, -8.0)},
    # tail: soft S (swan neck) seen from the side: leaves the rump back and down, sweeps back level, rises, the tip eases back
    # (first try (0, -0.90, -0.44) at the root: the tail ran 1 to 2 mm past the rump; now it leaves flatter and bends down later)
    tail=[(0.0, -0.98, -0.16), (0.0, -0.92, -0.40), (0.0, -0.76, -0.65), (0.0, -0.86, -0.51), (0.0, -1.0, 0.0),
          (0.0, -0.82, 0.57), (0.0, -0.70, 0.70), (0.0, -0.80, 0.60)],
    tail_scale=0.72, tail_yaw_keep=0.35, tail_roll_keep=0.35,
    tail_amp=(1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 6.5, 7.5), tail_lag=0.035, tail_phase=0.36,
    ears=(8.0, -2.0),                           # face B: ears a little forward
)

VARIANTS = {
    'A': dict(label='A  kontrolliert', track=0.11, hip_yaw=4.0, hip_roll=3.0, shoulder_yaw=3.0, sway=0.014),
    'B': dict(label='B  Swagger', track=0.05, hip_yaw=7.0, hip_roll=5.0, shoulder_yaw=5.0, sway=0.020),
    'C': dict(label='C  Catwalk', track=0.015, hip_yaw=9.0, hip_roll=6.0, shoulder_yaw=6.0, sway=0.025),
}
# pelvis height offset per variant (m, negative = lower), from find_pelvis(rig, geos, WALK, (key,)); filled by fit_pelvis_all()
Z_OFF = {}
# per variant, per side, per frame: extra abduction (deg) that keeps forearm and hand clear of the swinging hip gear (fit_arm_extra)
ARM_EXTRA = {}


def log(*a):
    print('[walk_v2]', *a, flush=True)


# ------------------------------------------------------------------ curves
def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def herm(p0, m0, p1, m1, u):
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * m0 + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * m1


def spline(keys, u):
    """keys (u, value, slope per u or None = Catmull-Rom), sorted"""
    sl = []
    for i, (x, y, m) in enumerate(keys):
        if m is None:
            m = (keys[i + 1][1] - keys[i - 1][1]) / (keys[i + 1][0] - keys[i - 1][0])
        sl.append(m)
    for i in range(len(keys) - 1):
        x0, y0, _ = keys[i]
        x1, y1, _ = keys[i + 1]
        if u <= x1 or i == len(keys) - 2:
            h = x1 - x0
            return herm(y0, sl[i] * h, y1, sl[i + 1] * h, (u - x0) / h)


def lift_bump(u):
    u = min(max(u, 0.0), 1.0)
    return (u * u * (1.0 - u) ** 2.5) / 0.045443


# ------------------------------------------------------------------ feet
class FootGeo:
    def __init__(self, rig, side):
        nm = rig.nm
        self.side = side
        self.sx = 1.0 if side == 'R' else -1.0
        self.A0 = rig.HEAD0[nm(side, 'Foot')].copy()
        self.T0 = rig.HEAD0[nm(side, 'Toes')].copy()
        self.Hc0 = Vector((self.A0.x, HEEL_BACK_Y, 0.0))
        # sole points (rest) for the clearance check: heel back / heel front / sole under the ball (foot bone), toe tip (toe bone)
        self.sole_foot = [Vector((self.A0.x, -0.079, 0.0)), Vector((self.A0.x, -0.040, 0.0)), Vector((self.A0.x, 0.060, 0.0005))]
        self.sole_toe = [Vector((self.A0.x, 0.112, 0.003))]


def yaw_q(sx, P):
    return Quaternion((0.0, 0.0, 1.0), math.radians(-sx * P['toe_out']))


def stance(geo, psi, P, Vv):
    qy = yaw_q(geo.sx, P)
    Wh = Vector((geo.sx * Vv['track'] / 2.0, P['heel_y'] - STRIDE * psi, 0.0))   # back edge of the heel on the floor (moves with it)
    if psi < P['psi2']:
        pitch = P['theta_hs'] * (1.0 - smooth(psi / P['psi1'])) if psi < P['psi1'] else 0.0
        dq = qy @ Quaternion((1.0, 0.0, 0.0), math.radians(pitch))
        return Wh + dq @ (geo.A0 - geo.Hc0), dq, dq.copy(), pitch
    u = (psi - P['psi2']) / (P['beta'] - P['psi2'])
    pitch = -P['theta_to'] * u * u                                                   # the heel rise speeds up into the push-off
    Wt = Wh + qy @ (geo.T0 - geo.Hc0)                                               # toe joint, stays on its spot
    dq = qy @ Quaternion((1.0, 0.0, 0.0), math.radians(pitch))
    return Wt + dq @ (geo.A0 - geo.T0), dq, qy.copy(), pitch


def swing(geo, psi, P, Vv):
    b = P['beta']
    span = 1.0 - b
    u = (psi - b) / span
    h = 1e-4
    a_to = stance(geo, b - 1e-9, P, Vv)[0]
    v_to = (a_to - stance(geo, b - h, P, Vv)[0]) / h
    a_hs = stance(geo, 0.0, P, Vv)[0]
    v_hs = (stance(geo, h, P, Vv)[0] - a_hs) / h
    ankle = herm(a_to, v_to * span, a_hs, v_hs * span, u)
    # height: the heel rises early in the swing (the knee folds), the foot passes low and level, and lands without vertical speed
    zk = [(0.0, a_to.z, v_to.z * span), (P['swing_peak_u'], P['swing_peak_z'], 0.0), (0.62, P['swing_mid_z'], None), (1.0, a_hs.z, v_hs.z * span)]
    ankle.z = spline(zk, u)
    ankle = ankle + Vector((geo.sx * max(0.0, P['pass_clear'] - Vv['track']) * math.sin(math.pi * u) ** 2, 0.0, 0.0))
    rate_to = -2.0 * P['theta_to'] / (b - P['psi2'])
    keys = [(0.0, -P['theta_to'], rate_to * span), (0.12, -P['theta_to'] - 3.0, 0.0), (0.40, -14.0, None), (0.65, 0.0, None),
            (0.88, 9.0, None), (1.0, P['theta_hs'], 0.0)]
    pitch = spline(keys, u)
    dq = yaw_q(geo.sx, P) @ Quaternion((1.0, 0.0, 0.0), math.radians(pitch))
    bend = P['theta_to'] * (1.0 - smooth(u / 0.4))
    return ankle, dq, dq @ Quaternion((1.0, 0.0, 0.0), math.radians(bend)), pitch


def foot(geo, psi, P, Vv):
    psi %= 1.0
    return stance(geo, psi, P, Vv) if psi < P['beta'] else swing(geo, psi, P, Vv)


def sole_heights(geo, ankle, dq, dtoe):
    """z of the sole points for this foot pose (foot points, toe tip)"""
    zs = [(ankle + dq @ (p - geo.A0)).z for p in geo.sole_foot]
    toe_joint = ankle + dq @ (geo.T0 - geo.A0)
    zs += [(toe_joint + dtoe @ (p - geo.T0)).z for p in geo.sole_toe]
    return zs


# ------------------------------------------------------------------ pelvis, spine, arms
def pelvis(phi, Vv, P, z_off):
    x = Vv['sway'] * math.sin(TAU * (phi - 0.03))
    z = z_off + 0.5 * P['bob'] * (1.0 - math.cos(2.0 * TAU * (phi - P['bob_low'])))
    yaw = Vv['hip_yaw'] * math.cos(TAU * (phi - 0.02))
    roll = -Vv['hip_roll'] * math.sin(TAU * (phi + P.get('roll_lead', 0.02)))    # the standing hip is highest near mid-stance
    pitch = P['pelvis_pitch'] * math.cos(2.0 * TAU * (phi - P['bob_low']))
    return Vector((x, 0.0, z)), yaw, roll, pitch


def arm_signal(side, phi, P):
    """-1 = arm back, +1 = arm forward; the right arm is back just after the right heel strike"""
    c = math.cos(TAU * (phi - P['arm_lag']))
    return -c if side == 'R' else c


def compute_walk(rig, phi, Vv, P, z_off, geos, arm_extra=None):
    H, R, HEAD0, nm = rig.H, rig.R, rig.HEAD0, rig.nm
    hips_d, yaw, roll, pitch = pelvis(phi, Vv, P, z_off)
    roll_l = pelvis(phi - P['chest_lag'], Vv, P, z_off)[2]
    sh_yaw = -Vv['shoulder_yaw'] * math.cos(TAU * (phi - 0.03))
    tot_yaw = sh_yaw - yaw
    tot_roll = -(1.0 + P['roll_over']) * roll_l
    spring = -P['chest_spring'] * math.cos(2.0 * TAU * (phi - P['bob_low'] - P['spring_lag']))
    lean = P['lean']
    rel = {H['hips']: eul(rx=lean[0] + pitch, ry=roll, rz=yaw),
           H['spine']: eul(rx=lean[1], ry=0.45 * tot_roll, rz=0.35 * tot_yaw),
           H['chest']: eul(rx=lean[2] + 0.4 * spring, ry=0.35 * tot_roll, rz=0.35 * tot_yaw),
           H['upperChest']: eul(rx=lean[3] + 0.6 * spring, ry=0.20 * tot_roll, rz=0.30 * tot_yaw)}
    s_arm = {s: arm_signal(s, phi, P) for s in ('L', 'R')}
    s_lag = {s: arm_signal(s, phi - P['hand_lag'], P) for s in ('L', 'R')}
    ex, ey = P['ears']
    for side, sx in (('L', -1.0), ('R', 1.0)):
        back = P['shoulder_back'] - P['shoulder_prot'] * s_arm[side]
        drop = P['shoulder_drop'] + P['shoulder_settle'] * math.cos(2.0 * TAU * (phi - P['bob_low'] - 0.10))
        rel[nm(side, 'Shoulder')] = eul(ry=sx * drop, rz=-sx * back)
        for fn in FINGERS:
            for part, c in zip(PARTS, P['finger_curl'][side][fn]):
                rel[nm(side, fn + part)] = Quaternion((0, 1, 0), math.radians(sx * c))
        t1, t2, t3 = P['thumb'][side]
        rel[nm(side, 'ThumbProximal')] = eul(rx=t1)
        rel[nm(side, 'ThumbIntermediate')] = eul(rz=sx * t2)
        rel[nm(side, 'ThumbDistal')] = eul(rz=sx * t3)
        n = 'J_Opt_%s_CatEar1_01' % side
        if n in rig.bones:
            rel[n] = Euler((math.radians(ex), math.radians(sx * ey), 0.0), 'XYZ').to_quaternion()
    head_abs = eul(rx=P['head_pitch'], rz=P['head_follow'] * sh_yaw)
    feet = {}
    for side in ('L', 'R'):
        psi = (phi if side == 'R' else phi + 0.5) % 1.0
        feet[side] = foot(geos[side], psi, P, Vv) + (psi,)
    tail_frame = eul(rx=lean[0], ry=P['tail_roll_keep'] * roll, rz=P['tail_yaw_keep'] * yaw)
    hips_name = H['hips']
    D, Q, Pp, legs, arms = {}, {}, {}, {}, {}
    diag = {'knee': {}, 'deficit': {}, 'sole_min': {}, 'psi': {}, 'twist': {}, 'elbow': {}}
    for name in rig.order:
        b = rig.bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        Pp[name] = HEAD0[name].copy() if parent is None else Pp[parent] + D[parent] @ (HEAD0[name] - HEAD0[parent])
        if name == hips_name:
            Pp[name] = Pp[name] + hips_d
        D[name] = Dp @ rel[name] if name in rel else Dp.copy()
        if name == H['neck']:
            D[name] = Dp.slerp(head_abs, P['neck_share'])
        elif name == H['head']:
            D[name] = head_abs.copy()
        elif name in rig.tail_bones:
            i = rig.tail_bones.index(name)
            w = P['tail_amp'][i] * math.sin(TAU * (phi - P['tail_phase'] - P['tail_lag'] * i))
            dvec = Quaternion((0.0, 0.0, 1.0), math.radians(w)) @ Vector(P['tail'][i]).normalized()
            D[name] = tail_frame @ Vector((0.0, -1.0, 0.0)).rotation_difference(dvec)
        for side, sx in (('L', -1.0), ('R', 1.0)):
            if name == nm(side, 'UpperLeg'):
                geo = geos[side]
                ankle, dq, dtoe, fpitch, psi = feet[side]
                Hp = Pp[name]
                K0 = HEAD0[nm(side, 'LowerLeg')]
                A0 = HEAD0[nm(side, 'Foot')]
                L1, L2 = (K0 - HEAD0[name]).length, (A0 - K0).length
                qy = yaw_q(sx, P)
                pole = qy @ Vector((sx * 0.10, 1.0, 0.0))
                K, Teff, deficit = two_bone_ik(Hp, ankle, pole, L1, L2)
                dth = (K - Hp).normalized()
                dsh = (Teff - K).normalized()
                foot_fwd = qy @ Vector((0.0, 1.0, 0.0))
                knee_face = perp(pole.normalized(), dth) or perp(foot_fwd, dth)
                shin_face = perp(knee_face.lerp(foot_fwd, 0.5), dsh) or knee_face
                legs[side] = (dsh, shin_face, dq, dtoe)
                D[name] = aim((K0 - HEAD0[name]).normalized(), Vector((0, 1, 0)), dth, knee_face)
                diag['knee'][side] = math.degrees(dth.angle(dsh))
                diag['deficit'][side] = deficit
                diag['sole_min'][side] = min(sole_heights(geo, ankle, dq, dtoe))
                diag['psi'][side] = psi
            elif name == nm(side, 'LowerLeg'):
                dsh, shin_face, dq, dtoe = legs[side]
                A0 = HEAD0[nm(side, 'Foot')]
                D[name] = aim((A0 - HEAD0[name]).normalized(), Vector((0, 1, 0)), dsh, shin_face)
            elif name == nm(side, 'Foot'):
                D[name] = legs[side][2].copy()
            elif name == nm(side, 'Toes'):
                D[name] = legs[side][3].copy()
            elif name == nm(side, 'UpperArm'):
                arms[side] = solve_arm(rig, side, sx, Pp[name], D[H['upperChest']], s_arm[side], s_lag[side], P,
                                       (arm_extra or {}).get(side, 0.0))
                D[name] = arms[side]['Du']
                diag['twist'][side] = arms[side]['twist']
                diag['elbow'][side] = arms[side]['flex']
            elif name == nm(side, 'LowerArm'):
                D[name] = arms[side]['Df']
            elif name == nm(side, 'Hand'):
                D[name] = arms[side]['Dh']
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    hips_loc = R[hips_name].inverted() @ hips_d
    return Q, hips_loc, diag


def solve_arm(rig, side, sx, S, Dc, s, s_lag, P, extra=0.0):
    """hinge model in the frame of the chest's heading (yaw only: the arm hangs with gravity, the shoulders carry its swing plane)"""
    f = Dc @ Vector((0.0, 1.0, 0.0))
    Fy = Quaternion((0.0, 0.0, 1.0), math.atan2(-f.x, f.y))
    alpha = math.radians(P['arm_swing0'] + P['arm_swing'] * s)
    beta = math.radians(P['elbow0'] + P['elbow_swing'] * 0.5 * (s + 1.0))
    # the arm swings around the hip: a little further out at the back of the swing, back in at the front (as in a real walk)
    ab = math.radians(P['arm_ab'][side] - P['arm_ab_swing'] * s + extra)
    du_l = Quaternion((1.0, 0.0, 0.0), alpha) @ Quaternion((0.0, 1.0, 0.0), -sx * ab) @ Vector((0.0, 0.0, -1.0))
    fl_l = perp(Vector((0.0, 1.0, 0.0)), du_l)
    df_l = du_l * math.cos(beta) + fl_l * math.sin(beta)
    # carrying angle: the forearm leans out a little more than the upper arm, so the hand passes outside the hip gear while the elbow
    # stays close to the body
    df_l = Quaternion(fl_l, -sx * math.radians(P['arm_carry'][side] - P['arm_carry_swing'] * s)) @ df_l
    du, df, fl = Fy @ du_l, (Fy @ df_l).normalized(), Fy @ fl_l
    rest_dir = Vector((sx, 0.0, 0.0))
    Du = aim(rest_dir, Vector((0, 1, 0)), du, fl)
    flex = du.angle(df)
    hinge = Du @ Vector((0.0, 0.0, sx))
    sgn = 1.0 if hinge.dot(du.cross(df)) >= 0 else -1.0
    Df0 = Quaternion(hinge, sgn * flex) @ Du
    n0 = perp(Df0 @ Vector((0.0, 0.0, -1.0)), df)
    palm = Fy @ Vector((-sx, -P['palm_back'], 0.0)).normalized()
    nt = perp(palm, df) or n0
    ang = math.atan2(n0.cross(nt).dot(df), n0.dot(nt))
    tm = math.radians(P['twist_max'])
    ang_c = max(-tm, min(tm, ang))
    nf = Quaternion(df, ang_c) @ n0
    Df = aim(rest_dir, Vector((0, 0, -1)), df, nf)
    fh = math.radians(P['hand_flex'])
    dev = math.radians(P['hand_dev'] + P['hand_flop'] * (s - s_lag))
    ulnar = sx * nf.cross(df)
    dh = (df * (math.cos(fh) * math.cos(dev)) + nf * math.sin(fh) + ulnar * math.sin(dev)).normalized()
    a = df.angle(dh)
    wm = math.radians(P['wrist_max'])
    if a > wm:
        dh = df.slerp(dh, wm / a)
    nh = perp(nf, dh) or nf
    Dh = aim(rest_dir, Vector((0, 0, -1)), dh, nh)
    return dict(Du=Du, Df=Df, Dh=Dh, twist=math.degrees(ang_c), flex=math.degrees(flex))


# ------------------------------------------------------------------ pelvis height
def make_geos(rig):
    return {s: FootGeo(rig, s) for s in ('L', 'R')}


def knee_margin(rig, geos, P, z_off, keys=('A', 'B', 'C')):
    """least (knee bend - limit) over all frames: the standing leg needs knee_min, the swinging leg knee_min_swing (it may reach almost
    straight just before the heel strike, as in a real walk)"""
    worst = 180.0
    for k in keys:
        for f in range(NF):
            dg = compute_walk(rig, f / float(NF), VARIANTS[k], P, z_off, geos)[2]
            for s, kn in dg['knee'].items():
                lim = P['knee_min'] if dg['psi'][s] < P['beta'] else P.get('knee_min_swing', 3.0)
                worst = min(worst, kn - lim)
    return worst


def find_pelvis(rig, geos, P=WALK, keys=('A', 'B', 'C'), lo=-0.12, hi=0.0, iters=18):
    """highest pelvis (z offset of the hips, m) that keeps the knees bent (knee_margin >= 0) in every frame of every variant"""
    if knee_margin(rig, geos, P, hi, keys) >= 0.0:
        return hi
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if knee_margin(rig, geos, P, mid, keys) >= 0.0:
            lo = mid
        else:
            hi = mid
    return lo


# ------------------------------------------------------------------ frames and baking
def fit_pelvis_all(rig, P=WALK, keys=('A', 'B', 'C')):
    """per variant the highest pelvis that keeps the knees bent (same leg work in every variant; the narrow track and the stronger hip
    tilt of C lengthen the standing leg, so C walks a few millimetres lower)"""
    geos = make_geos(rig)
    for k in keys:
        Z_OFF[k] = find_pelvis(rig, geos, P, (k,))
    return dict(Z_OFF)


def compute_frames(rig, key, P=WALK, z_off=None, geos=None):
    geos = geos or make_geos(rig)
    z = Z_OFF[key] if z_off is None else z_off
    ex = ARM_EXTRA.get(key, {})
    out = []
    for f in range(NF + 1):
        extra = {s: ex[s][f % NF] for s in ex}
        out.append(compute_walk(rig, (f % NF) / float(NF), VARIANTS[key], P, z, geos, extra))
    return out


def keyed_names(rig):
    names = set(rig.H.values()) | set(rig.tail_bones)
    for side in ('L', 'R'):
        for k in (1, 2):
            n = 'J_Opt_%s_CatEar%d_01' % (side, k)
            if n in rig.bones:
                names.add(n)
    return [n for n in rig.order if n in names and not n.endswith('_end_01')]


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


def bake(rig, frames, name, tail_scale=0.72):
    """keys on every frame 0 .. NF (key NF == key 0), linear, Cycles modifier: the clip loops endlessly"""
    arm = rig.arm
    names = keyed_names(rig)
    ad = arm.animation_data_create()
    old = bpy.data.actions.get(name)
    if old is not None:
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
    flips = 0
    for n in names:
        series, prev = [], None
        for fr in frames:
            q = fr[0][n].copy()
            if prev is None and q.w < 0.0:
                q = -q
            if prev is not None and prev.dot(q) < 0.0:
                q = -q
            series.append(q)
            prev = q
        if series[-1].dot(series[0]) < 0.0:
            flips += 1
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        for i in range(4):
            _fill(fcs[(dp, i)], [q[i] for q in series])
    dp = 'pose.bones["%s"].location' % rig.H['hips']
    for i in range(3):
        _fill(fcs[(dp, i)], [fr[1][i] for fr in frames])
    return act, flips


def face_child(arm):
    return next(c for c in arm.children if c.type == 'MESH' and c.data.shape_keys and 'Fcl_EYE_Close' in c.data.shape_keys.key_blocks)


def apply_face_b(arm):
    face = face_child(arm)
    for kb in face.data.shape_keys.key_blocks:
        if kb.name != 'Basis':
            kb.value = FACE_B.get(kb.name, 0.0)
    return face


def bake_variant(arm_obj, key, P=WALK, z_off=None):
    rig = L['Rig'](arm_obj, L['humanoid_map']())
    t0 = time.time()
    frames = compute_frames(rig, key, P, z_off)
    act, flips = bake(rig, frames, 'Yoru_Walk_v2_' + key, P['tail_scale'])
    apply_face_b(arm_obj)
    knees = [min(fr[2]['knee'].values()) for fr in frames]
    defs = [max(fr[2]['deficit'].values()) for fr in frames]
    tw = [max(abs(v) for v in fr[2]['twist'].values()) for fr in frames]
    return dict(action=act.name, frames=len(frames), knee_min=round(min(knees), 2), knee_max_stance=None,
                reach_deficit_mm=round(max(defs) * 1000, 3), forearm_twist_max=round(max(tw), 1), sign_flips=flips,
                seconds=round(time.time() - t0, 2))


# ------------------------------------------------------------------ exact arm test (sets built once)
class GearTester:
    """exact intersection test of the arm / hand mesh against torso, thighs and gear (as arm_mesh_intersections in build_idle_v2_check.py,
    with the vertex sets built once).  The upper arm counts only beyond t_min of its length (the armpit end touches the vest by nature)."""

    def __init__(self, rig, t_min=0.5):
        H, nm = rig.H, rig.nm
        self.rig, self.t_min = rig, t_min
        body = rig.body
        vis = L['visible_vertices'](body)
        dom = L['vertex_groups_by_bone'](rig)
        solid = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg']}
        gear_v = set(i for i, n in enumerate(dom) if vis[i] and (n in solid or (n.startswith('J_Sec_') and 'Hair' not in n and 'Bust' not in n)))
        self.gear_polys = [list(p.vertices) for p in body.data.polygons if all(v in gear_v for v in p.vertices)]
        self.parts = {}
        for s in ('L', 'R'):
            hand = {nm(s, 'Hand')} | {nm(s, f + p) for f in FINGERS for p in PARTS} | {nm(s, 'Thumb' + p) for p in PARTS}
            for part, bset in (('Hand', hand), ('LowerArm', {nm(s, 'LowerArm')}), ('UpperArm', {nm(s, 'UpperArm')})):
                self.parts[(s, part)] = [list(p.vertices) for p in body.data.polygons if all(dom[v] in bset and vis[v] for v in p.vertices)]
        self.hand_ids = {s: [i for i, n in enumerate(dom) if vis[i] and (n == nm(s, 'Hand') or n.startswith('J_Bip_%s_' % s) and
                                                                            any(x in n for x in ('Index', 'Middle', 'Ring', 'Little', 'Thumb')))]
                         for s in ('L', 'R')}

    def test(self):
        from mathutils.bvhtree import BVHTree
        from mathutils.geometry import intersect_point_line
        rig, nm = self.rig, self.rig.nm
        co = L['evaluated_coords'](rig.body)
        bg = BVHTree.FromPolygons(co, self.gear_polys, all_triangles=False)
        res = {}
        pbs = rig.arm.pose.bones
        for k, polys in self.parts.items():
            groups = {k[1]: polys}
            if k[1] == 'UpperArm':
                sh, el = pbs[nm(k[0], 'UpperArm')].head, pbs[nm(k[0], 'LowerArm')].head
                groups = {'UpperArm': [p for p in polys if intersect_point_line(co[p[0]], sh, el)[1] > self.t_min]}
            elif k[1] == 'LowerArm':
                # the elbow end (first 30 % of the forearm) may rest against the side of the vest like the sleeve of the upper arm;
                # the rest of the forearm must stay clear
                el, wr = pbs[nm(k[0], 'LowerArm')].head, pbs[nm(k[0], 'Hand')].head
                groups = {'Elbow': [p for p in polys if intersect_point_line(co[p[0]], el, wr)[1] <= 0.3],
                          'LowerArm': [p for p in polys if intersect_point_line(co[p[0]], el, wr)[1] > 0.3]}
            for g, use in groups.items():
                res['%s %s' % (k[0], g)] = len(BVHTree.FromPolygons(co, use, all_triangles=False).overlap(bg)) if use else 0
        gap = {s: min(bg.find_nearest(co[i])[3] for i in self.hand_ids[s]) for s in ('L', 'R')}
        return res, gap


def pose_frame(rig, fr, tail_scale=0.72):
    L['apply_pose'](rig, fr[0], fr[1], tail_scale)


def fit_arms(rig, keys=('A', 'B', 'C'), P=WALK, z_off=None, start=6.0, step=1.0, stop=18.0, frames=range(0, NF, 2)):
    """per side the least abduction (deg) that keeps arm and hand out of the gear in every sampled frame of every variant"""
    tester = GearTester(rig)
    geos = make_geos(rig)
    result = {}
    for side in ('R', 'L'):
        ab = start
        while ab <= stop:
            P2 = dict(P, arm_ab=dict(P['arm_ab'], **{side: ab}))
            bad = 0
            gaps = []
            for k in keys:
                for f in frames:
                    fr = compute_walk(rig, f / float(NF), VARIANTS[k], P2, Z_OFF[k] if z_off is None else z_off, geos)
                    pose_frame(rig, fr, P['tail_scale'])
                    res, gap = tester.test()
                    bad += sum(v for kk, v in res.items() if kk.startswith(side))
                    gaps.append(gap[side])
            log('fit arm', side, 'abduction', ab, 'intersecting pairs', bad, 'hand gap mm %.1f .. %.1f' % (min(gaps) * 1000, max(gaps) * 1000))
            if bad == 0:
                break
            ab += step
        result[side] = ab
    return result


def fit_arms2(rig, keys=('A', 'B', 'C'), P=WALK, abs_=(9.0, 10.0, 11.0, 12.0), carries=tuple(range(0, 31, 3)), frames=range(0, NF, 3),
              upper_ok=0.012):
    """per side: for each upper-arm abduction the least carrying angle that keeps forearm and hand out of the gear (exact test, every
    sampled frame of every variant); the upper arm (elbow half) may rest against the side of the vest up to upper_ok m (as in the idle).
    Picks the smallest abduction + carry that passes."""
    tester = GearTester(rig)
    geos = make_geos(rig)
    out = {}
    for side in ('R', 'L'):
        best = None
        for ab in abs_:
            for c in carries:
                P2 = dict(P, arm_ab=dict(P['arm_ab'], **{side: ab}), arm_carry=dict(P['arm_carry'], **{side: float(c)}))
                bad, upper, gaps = 0, 0.0, []
                for k in keys:
                    for f in frames:
                        fr = compute_walk(rig, f / float(NF), VARIANTS[k], P2, Z_OFF[k], geos)
                        pose_frame(rig, fr, P['tail_scale'])
                        res, gap = tester.test()
                        bad += res[side + ' Hand'] + res[side + ' LowerArm']
                        gaps.append(gap[side])
                        if bad:
                            break
                        upper = max(upper, L['arm_penetration'](rig, 0.6)[side][2])
                    if bad:
                        break
                if bad == 0:
                    log('fit arm', side, 'abduction', ab, 'carry', c, 'upper arm in vest %.1f mm' % (upper * 1000),
                        'hand gap %.1f .. %.1f mm' % (min(gaps) * 1000, max(gaps) * 1000))
                    if upper <= upper_ok and (best is None or ab + c < best[0] + best[1]):
                        best = (ab, float(c), upper, min(gaps), max(gaps))
                    break
        out[side] = best
    return out


def _periodic_smooth(vals, sigma):
    n = len(vals)
    out = []
    for i in range(n):
        acc = wsum = 0.0
        for d in range(-int(3 * sigma) - 1, int(3 * sigma) + 2):
            w = math.exp(-0.5 * (d / sigma) ** 2)
            acc += w * vals[(i + d) % n]
            wsum += w
        out.append(acc / wsum)
    return out


def fit_arm_extra(rig, key, P=WALK, hi=20.0, iters=6, margin=0.5, tester=None, geos=None):
    """per frame and side the least extra abduction (deg) with no exact intersection of forearm (beyond the elbow end) and hand with the
    gear; then dilated (+-2 frames), smoothed periodically and checked again (bumped where needed).  Stores ARM_EXTRA[key]."""
    tester = tester or GearTester(rig)
    geos = geos or make_geos(rig)
    z = Z_OFF[key]

    def bad(f, extra, side):
        fr = compute_walk(rig, f / float(NF), VARIANTS[key], P, z, geos, extra)
        pose_frame(rig, fr, P['tail_scale'])
        res, gap = tester.test()
        return res[side + ' Hand'] + res[side + ' LowerArm']

    raw = {'L': [0.0] * NF, 'R': [0.0] * NF}
    for side in ('L', 'R'):
        for f in range(NF):
            if bad(f, {side: 0.0}, side) == 0:
                continue
            lo, h = 0.0, hi
            for _ in range(iters):
                mid = 0.5 * (lo + h)
                if bad(f, {side: mid}, side) == 0:
                    h = mid
                else:
                    lo = mid
            raw[side][f] = h + margin
    out = {}
    for side in ('L', 'R'):
        r = raw[side]
        dil = [max(r[(i + d) % NF] for d in range(-2, 3)) for i in range(NF)]
        sm = _periodic_smooth(dil, 1.5)
        for rounds in range(3):
            fails = [f for f in range(NF) if bad(f, {side: sm[f]}, side)]
            if not fails:
                break
            for f in fails:
                for d in range(-2, 3):
                    sm[(f + d) % NF] += 1.0 if d == 0 else 0.5
        out[side] = sm
    ARM_EXTRA[key] = out
    return out
