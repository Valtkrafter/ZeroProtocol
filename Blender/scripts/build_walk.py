"""
Yoru - WALK cycle (one gait cycle = two steps, in place, 30 fps), built procedurally on the VRM skeleton.
Same method as build_idle.py (world-space rotation deltas D per humanoid bone, pose basis Q = R^-1 * Dp^-1 * D * R,
legs by two-bone IK to planted feet, arms fitted numerically against the body mesh), plus a real gait model.

Run (background Blender; ALWAYS --factory-startup and absolute paths):
  blender -b --factory-startup --python build_walk.py -- <Yoru.glb> <output dir> [build|design|trace|summary|envelope] [KEY=VALUE ...]
THEN (the blink is a separate step; this script writes a Yoru_Walk.blend WITHOUT it, 26 frames, not endless):
  blender -b --factory-startup <output dir>/Yoru_Walk.blend --python build_blink.py -- <output dir> [SEED=247] [CYCLES=20]
  (makes the walk endless with Cycles modifiers, keys the blinks of blink_model.py on the shape key Fcl_EYE_Close, writes Yoru_Blink.json)

SPEC pass (default, spec = 1; the user's 4-stage order "AAA anime locomotion"): 60 % stance / 40 % swing, ankles planted on +-25 mm, pelvis wave
(2 per cycle) fitted under the reach limit of the legs, hips shift 28 mm, roll 6.5 / yaw 8 deg, spine / chest split, neck + head locked and the
head bone kept on x = 0, arms 14 fwd / 18 back with the ordered elbow / wrist lags, tail with a down-then-up rest curve and travelling waves.
spec_report() measures every ordered number on the finished keys.  spec = 0 amp_norm = 0 (plus the old keys) gives the earlier feminine
version back (kept in Blender/work/versions/*_v6_feminin.*).  Dev modes: SPECSCAN=1 / 2 (design tables).

Gait model (all numbers come from the rig, nothing is eyeballed on the foot):
  - Walk speed SPEED (m/s) and cycle time NF/FPS give the stride length  S = SPEED * T.  The character stays in place, so
    during stance the planted point of the foot moves backwards at the ground speed (no foot sliding).  The ground speed is not
    constant: it wobbles by +-speed_var (5 %) twice per cycle, fastest at heel strike / double support (the body is lowest) and slowest
    at mid stance (the body has risen over the stance leg), like the speed of a real walker; G(phi) is how far the ground has moved.
  - Each foot has a phase  phi in [0,1)  (0 = heel strike, right foot at frame 0, left foot half a cycle later).
      stance   0 .. PH_TO : heel rocker (pivot = rear edge of the heel, foot pitch falls from TH_HS to 0),
                            foot flat (heel and ball both fixed to the ground),
                            heel rise (pivot = toe joint "ToeBase", foot pitches TH_TO toes-down, the toe bone bends up
                            so the toe part stays flat on the ground)
      swing    PH_TO .. 1 : ankle path = quintic Hermite in the ground frame (position, velocity and acceleration match the
                            stance at both ends -> soft toe-off and a heel strike with zero speed relative to the ground),
                            height = clearance bump of the LOWEST sole point (never through the floor, never floating).
  - Pelvis: height curve (2 humps per cycle) fitted so that both legs always reach their feet (knees never lock),
    sideways shift over the stance foot, yaw / roll, chest counter-rotation, arms swing against the legs.
  - Arms hang outward (24 / 28 deg, thigh pouches + holster); the swing is clearance-checked against the mesh with
    the same numeric check as the idle.  Tail / ears / hair are animated for the preview (the baked Unity clip only
    carries the humanoid bones; spring-bone physics does the rest there).
Styles (command line overrides  KEY=VALUE  after "build"):
  NEWEST (default now): the swagger style below with bigger, flowing arm swing (swing_f=20 swing_b=13 elbow_k=1.3 hand_k=1.6, forearm trails by 0.07 and hand by 0.14 of a cycle,
                    arm_abd=3, arm_h2=0.12, pro=2) and bust / hair moved by a spring simulation of the body motion (sec_on=1, bust_d1=6.5 bust_d2=11 bust_yaw=3 hair_deg=3);
                    the previous swagger version with the stiffer arms is kept in Blender/work/versions/*_v3_swagger.*
  swagger / "bad" (default, the user's wish after the lively version): yaw_p=9.5 roll_p=5.5 yaw_c=11.5 sway=0.024 BASE=0.050 TOE_OUT=8
                    torso_comp=1.3 pitch_amp=1.8 swing_f=13 swing_b=9 elbow_k=1.2 hand_k=1.4 + arms close to the body ARM_UP=23 ARM_FORE=14 ARM_FFWD=40
                    (the shoulder pads / vest / hip gear stop the arms at about this hang, see ARMGRID=3; ARM_FIT=1 fits them against the gear instead)
  lively (second version, Blender/work/versions/*_v2_lebendig.*): yaw_p=6 roll_p=3.2 yaw_c=8 sway=0.018 BASE=0.068 TOE_OUT=8 swing_f=17 swing_b=11
                    elbow_k=1.7 hand_k=2 torso_comp=0.6 pitch_amp=1 tail_yaw=2.8 tail_pit=1.2 ear_amp=2.4 hair_amp=2.2 ARM_FIT=1 ARM_UP=8 ARM_FORE=6 ARM_FFWD=30
  calm (first version, Blender/work/versions/*_v1_ruhig.*):  yaw_p=3.5 roll_p=1.8 yaw_c=5.5 sway=0.012 BASE=0.062 TOE_OUT=6
                    swing_f=11 swing_b=7 elbow_k=1.3 hand_k=1.5 torso_comp=0.95 pitch_amp=0.5 tail_yaw=2 tail_pit=0.8 ear_amp=1.6 hair_amp=1.4
Speed and cadence:  default now SPEED=1.50 NF=21 (171 steps/min; the first walk was SPEED=1.15 NF=26, an earlier try SPEED=1.30 NF=28);
                    NF / SPEED / PH_TO / KNEE_* / HARM change the gait itself (NF below 21 does not build).
Blender axes for Yoru: +Y forward, her left = -X, up = +Z.
"""
import bpy, sys, math, cmath, json, struct, os, time, re
from mathutils import Vector, Quaternion, Euler, Matrix
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = argv[0], argv[1]
DESIGN_ONLY = len(argv) > 2 and argv[2] == 'design'
os.makedirs(OUT, exist_ok=True)

FPS = 30
TWO_PI = 2.0 * math.pi
T0 = time.time()


def log(*a):
    print('[walk %5.1fs]' % (time.time() - T0), *a, flush=True)


# ------------------------------------------------------------------ import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Body']
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name.startswith('Icosphere'):
        o.hide_render = True
        o.hide_viewport = True
scene = bpy.context.scene
scene.render.fps = FPS

with open(GLB, 'rb') as f:
    f.read(12)
    clen, _ = struct.unpack('<II', f.read(8))
    js = json.loads(f.read(clen).decode('utf-8'))
nodes = js['nodes']
H = {h['bone']: nodes[h['node']]['name'] for h in js['extensions']['VRM']['humanoid']['humanBones']}
bones = arm.data.bones
R = {b.name: b.matrix_local.to_quaternion() for b in bones}          # rest orientation, armature space
HEAD0 = {b.name: b.head_local.copy() for b in bones}
TAIL0 = {b.name: b.tail_local.copy() for b in bones}

order = []                                                           # parents before children
queue = [b for b in bones if b.parent is None]
while queue:
    b = queue.pop(0)
    order.append(b.name)
    queue.extend(b.children)

hum_names = set(H.values())
HAIR_RE = re.compile(r'^J_Sec_Hair(\d+)_(\d+)$')
HAIR = [b.name for b in bones if HAIR_RE.match(b.name)]
TAIL_EARS = ['J_Opt_C_CatTail%d_01' % i for i in range(1, 9)] + ['J_Opt_%s_CatEar%d_01' % (sd, k) for sd in 'LR' for k in (1, 2)]
BUST_BONES = [n for n in ('J_Sec_L_Bust1', 'J_Sec_L_Bust2', 'J_Sec_R_Bust1', 'J_Sec_R_Bust2') if n in bones]
EXTRA = [n for n in TAIL_EARS if n in bones] + HAIR + BUST_BONES


def nm(side, part):                                                  # side 'L'/'R'
    return H[('left' if side == 'L' else 'right') + part]


# ------------------------------------------------------------------ helpers
def deg(x):
    return math.radians(x)


def eul(rx=0.0, ry=0.0, rz=0.0):                                     # degrees, X first, then Y, then Z (world axes)
    return Euler((deg(rx), deg(ry), deg(rz)), 'XYZ').to_quaternion()


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    s = d.cross(n)
    return Matrix((d, n, s)).transposed().to_quaternion()


def aim(rest_dir, rest_nrm, tgt_dir, tgt_nrm):
    return frame_rot(tgt_dir, tgt_nrm) @ frame_rot(rest_dir, rest_nrm).inverted()


def two_bone_ik(Hp, T, pole, L1, L2):
    """knee position and the (clamped) ankle position; returns also the unclamped distance ratio d/(L1+L2)"""
    v = T - Hp
    d = v.length
    d_c = min(max(d, abs(L1 - L2) + 1e-4), (L1 + L2) * 0.9995)
    u = v.normalized()
    a = (L1 * L1 - L2 * L2 + d_c * d_c) / (2.0 * d_c)
    h = math.sqrt(max(L1 * L1 - a * a, 0.0))
    p = pole - u * pole.dot(u)
    p.normalize()
    K = Hp + u * a + p * h
    return K, Hp + u * d_c, d - d_c, d / (L1 + L2)


def sstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def herm5(p0, v0, a0, p1, v1, a1, u):
    """quintic Hermite: values, first and second derivatives with respect to u at u = 0 and u = 1"""
    u2 = u * u
    u3 = u2 * u
    u4 = u3 * u
    u5 = u4 * u
    return ((1 - 10 * u3 + 15 * u4 - 6 * u5) * p0 + (u - 6 * u3 + 8 * u4 - 3 * u5) * v0
            + (0.5 * u2 - 1.5 * u3 + 1.5 * u4 - 0.5 * u5) * a0 + (10 * u3 - 15 * u4 + 6 * u5) * p1
            + (-4 * u3 + 7 * u4 - 3 * u5) * v1 + (0.5 * u3 - u4 + 0.5 * u5) * a1)


def herm3(p0, m0, p1, m1, w):
    w2 = w * w
    w3 = w2 * w
    return (2 * w3 - 3 * w2 + 1) * p0 + (w3 - 2 * w2 + w) * m0 + (-2 * w3 + 3 * w2) * p1 + (w3 - w2) * m1


def rot2(th, dy, dz):
    """rotate the (y, z) vector about the lateral axis by th (radians, toes up = positive: +Y turns towards +Z)"""
    c, s = math.cos(th), math.sin(th)
    return dy * c - dz * s, dy * s + dz * c


def action_fcurves(action):
    """all f-curves of an action (old API: action.fcurves, layered actions of Blender 4.4+: layers / strips / channelbags)"""
    if hasattr(action, 'fcurves'):
        return list(action.fcurves)
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def set_linear(action):
    """straight lines between the keys (the preference keyframe_new_interpolation_type is not honoured by keyframe_insert in 5.x)"""
    n = 0
    for fc in action_fcurves(action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
            n += 1
    return n


# ------------------------------------------------------------------ parameters
class P:
    # --- gait timing and speed
    NF = 21                  # frames per gait cycle (two steps); key NF == key 0.  26 = the first, slower walk (1.15 m/s, 138 steps/min)
    SPEED = 1.50             # walk speed in m/s  (stride length = SPEED * NF / FPS), the mean over a cycle.  The user found 1.15 too slow;
                             # with her 74 cm legs 1.50 m/s at 171 steps/min (step 0.525 m) keeps the knees / pelvis of the slow walk
                             # (sweep: Blender/work/speed_sweep/sweep.txt; 1.6 and more needs bent knees of 25 deg and more)
    speed_var = 0.05         # the ground speed wobbles by +- this share twice per cycle (a real walker slows down a little over every stance leg); 0 = constant
    speed_var_phase = 0.0    # cycle phase of the fastest ground speed = where the pelvis is lowest (right heel strike at 0, measured: the pelvis wave has its minimum at 0.00); the second peak is at +0.5
    PH_FF = 0.08             # foot flat
    PH_HR = 0.30             # heel rise (earlier: the foot rolls over the ball for longer, stronger push-off)
    PH_TO = 0.60             # toe off
    TH_HS = 10.0             # foot pitch at heel strike (deg, toes up)
    TH_TO = 38.0             # foot pitch at toe off (deg, toes down)
    P_HR = 1.5               # ease-in exponent of the heel rise
    TH_MS = -1.0             # foot pitch at mid swing
    SW_FRAC = 0.4            # share of the stance pitch rate that carries on after toe off
    CLEAR = 0.045            # clearance of the lowest sole point at mid swing (m)
    CLR_GAMMA = 0.65         # below 1 lifts the foot earlier after toe off, above 1 later
    LATE_LIFT = 0.010          # extra height (m) of the sole in late swing (the leg reaches out nearly straight, the foot hovers and then settles)
    LATE_U0 = 0.55           # ... starting at this share of the swing
    SW_V0 = 2.0              # minimum forward speed of the ankle (ground frame, m/s) at toe off
    BASE = 0.025             # ankle distance from the midline (m); the hip joints are 0.0751; narrow = cat-like track
    TOE_OUT = 0.0           # toes point outward by this angle (deg), negative = slightly towards the midline
    KNEE_OUT = 0.0           # the knees point outward by this angle while the feet point nearly straight (keeps the thighs apart)
    CIRC = 0.045             # the swing foot moves out by this much at mid swing and lands back on the narrow track (m)
    SW_YAW = 0.5             # the swing leg turns with the pelvis by this share
    A_HS = 0.245              # ankle y relative to the hip joint at heel strike (fitted)
    # --- pelvis
    z_peak = 0.84            # hips bone height at mid stance (fitted); rest = 0.8955
    bob = 0.055              # peak to peak height change (m)
    sway = 0.028             # sideways shift over the stance foot (m)
    yaw_p = 8.0              # pelvis yaw (deg)
    roll_p = 6.5             # pelvis drop on the swing side (deg)
    yaw_c = 5.0             # chest counter rotation (deg, world)
    lean = 6.0               # forward lean of the torso (deg)
    pitch_amp = 1.5          # pelvis nod with the steps (deg)
    lean_dyn = 2.0           # extra lean that dives into every down pose (deg, twice per cycle)
    down_extra = 0.0       # the hips sink this much deeper at the down pose than the reach fit needs (weight is caught)
    down_phase = 0.105        # cycle phase of the down pose after heel strike
    down_w = 0.05            # width of the dip (fraction of the cycle)
    rebound = 0.0           # the pelvis springs back above its curve after the dip by this share of the dip (springy step)
    rebound_dt = 0.12        # ... this far after the dip (fraction of the cycle)
    surge = 0.004            # forward / backward pelvis surge (m)
    EXT_CAP = 0.9990         # a leg never gets straighter than this (distance / (L1+L2))
    zcoef = None             # fitted pelvis height curve (Fourier coefficients, see fit_envelope)
    KNEE_MID = 18.0          # knee flexion of the standing leg at mid stance (deg)
    MARGIN = 0.0004           # the pelvis stays this far below the reach limit (m)
    FIT_IN = 0.0003           # the fitted pelvis curve is pushed down where it comes closer than this to the reach limit (m)
    FIT_FINAL = 0.0003       # ... and finally lowered until it is this far under the limit everywhere (m)
    KNEE_HS = 5.0            # least knee flexion at heel strike (deg)
    KNEE_ST = 8.0            # least knee flexion while standing (deg)
    KNEE_TO = 20.0           # least knee flexion at toe off (deg)
    HARM = 2                 # harmonics of the step frequency in the pelvis height curve (1 = pure wave, more follow the reach limit closer)
    # --- spine: the counter rotation travels up the spine with a lag (pelvis leads, shoulders trail)
    sp_share = (0.32, 0.68, 1.0)      # share of the shoulder counter rotation reached at spine, chest, upper chest
    sp_lag = (0.018, 0.036, 0.056)    # lag of those levels (fraction of the cycle)
    torso_roll = 0.30        # roll of the shoulders against the pelvis drop (S-curve), share of roll_p
    # --- arms
    ARM_UP = -1.0            # >= 0: use this upper-arm outward angle for both arms (deg)
    ARM_FORE = -99.0         # > -99: forearm outward angle (deg)
    E_MAX = -1.0             # >= 0: elbow flexion in the forward swing (deg)
    ARM_FIT = 0              # 0 = take the arm angles as given (only report the clearance), 1 = fit them against the gear
    ARM_WANT = -0.012        # wanted arm clearance to the gear (m); slightly negative lets the sleeve touch the gear
    LEGGRID = 0              # 1 = only print a table of track widths and swing arcs against leg intersections and stop
    ARMGRID = 0              # >0: only print a table of arm hang combinations (clearance, elbow and wrist distance from the body) and stop
    arm = {'L': dict(up_out=22.8, fore_out=13.0, e_max=26.0),
           'R': dict(up_out=22.8, fore_out=13.0, e_max=26.0)}
    swing_f = 14.0           # forward swing of the upper arm from the shoulder (deg)
    swing_b = 18.0           # backward swing (deg)
    e_min = 6.0              # elbow flexion in the back swing (deg): almost straight
    lag_e = 0.125             # the elbow bend peaks this part of a cycle after the upper arm is furthest forward (overlap)
    e_pow = 1.0              # >1 keeps the elbow straighter for longer
    wr_base = 8.0            # wrist flexion (deg)
    wr_amp = 10.0             # wrist flick (deg)
    lag_w = 0.1944             # the hand trails the forearm by this part of a cycle
    arm_abd = 2.5            # the arm moves in towards the body when it swings forward and out when it swings back (deg)
    arm_h2 = 0.12            # second harmonic of the arm swing (a little dwell at the ends)
    pro = 1.0                # shoulder blade moves forward with the arm (deg)
    arm_fwd0 = 0.0           # static forward tilt of the hanging upper arm (0 = the swing angles are measured from the plumb line; the earlier version used 0.05)
    # hands (the user found them stiff): relaxed curl that grows from index to little finger, a travelling curl wave with an overlapping delay per
    # finger and per joint, a little spread, thumb that moves, wrist flick + sideways deviation + palm turn that lag behind the arm swing
    fing_dyn = (7.0, 10.0, 8.0)          # curl wave per phalanx (deg)
    fing_lag = 0.55                      # cycle phase at which the fingers are most curled (0 = arm furthest forward)
    fing_lag_f = 0.020                   # extra delay per finger (index first, little finger last), fraction of a cycle
    fing_lag_p = 0.014                   # extra delay per phalanx
    fing_spread = (4.0, 1.5, -1.5, -5.0)  # spread of the knuckle joints (deg): index forward, little finger backward
    thumb_dyn = 6.0                      # thumb swing (deg)
    wr_dev = 4.0                         # sideways wrist deviation (deg)
    wr_dev_lag = 0.22                    # ... its delay (fraction of a cycle)
    palm_turn = 0.30                     # palm sways forward / back by about atan(this) degrees
    palm_lag = 0.16
    thumb_add = 36.0         # the thumb is brought alongside the hand (deg)
    # relaxed, ready hand: curls (proximal, intermediate, distal) per finger; the standard VRoid hand is spread and straight
    fingers = {'Index': (22.0, 30.0, 16.0), 'Middle': (28.0, 38.0, 20.0), 'Ring': (34.0, 44.0, 24.0), 'Little': (40.0, 50.0, 28.0)}
    # --- bust, hair, ears, tail: small spring simulations of the body motion (preview; Unity uses spring bones)
    sec_on = 1               # 1 = bust and hair are moved by a spring simulation of the body motion
    bust_d1 = 6.5            # bust bounce at the first bone (deg)
    bust_d2 = 11.0           # bust bounce at the second bone (deg)
    bust_yaw = 3.0           # sideways sway (deg)
    bust_w = 15.0            # natural frequency of the bust (rad/s)
    bust_z = 0.22            # damping ratio of the bust
    hair_deg = 3.0           # hair strand swing per joint (deg)
    hair_w = 9.0             # natural frequency of the hair (rad/s)
    hair_z = 0.40            # damping ratio of the hair
    hair_lag = 0.03          # seconds of delay per joint along a strand
    sec = None               # filled by the build: bone name -> list of (rx, ry, rz) in degrees per frame
    tail_dyn = None          # filled by the build: tail joint -> list of (pitch, yaw) per frame
    tail_w = 17.0            # every tail joint follows the one before with a spring of this frequency (rad/s) -> travelling S-curve
    tail_z = 0.45            # damping ratio of that spring
    tail_amp = 7.0           # peak sideways bend per tail joint (deg); the spring cascade supplies the phase (S-curve)
    tail_pw = 13.0           # natural frequency of the vertical wave (rad/s)
    tail_pg = 7.5            # peak tail pitch whip at the tip joints (deg)
    ear_w = 24.0             # natural frequency of the ears (rad/s)
    ear_z = 0.16             # damping ratio of the ears (springy, a visible after-bounce)
    ear_g = 8.0              # ear pitch swing at the first joint (deg)
    # --- tail rest curve (idle values)
    tail = [8.0, -13.0, -23.0, -30.0, -32.0, -35.0, 0.0, -40.0]   # rest pitch per joint (idle values, see Yoru_Idle_tail.json)
    tail_lift = 0.0          # extra lift of the first joints (deg), fitted against the legs
    TAIL_CLEAR = 0.006       # least distance between the tail mesh and the body (m)
    tail_scale = 0.72         # uniform scale of the whole tail (keyed on the root joint); Unity must set the same local scale on the tail root bone
    tail_walk = [18.0, -6.0, -10.0, -14.0, -18.0, -15.0, 0.0, 15.0]   # walking rest curve: rises over the hips, arcs down like a swan neck, tip flicks up (a soft S in the side view, not a rod and not the idle's C-roll)
    tail_pa = 4.5            # peak pitch wave per tail joint (deg); the spring cascade supplies the phase
    # --- SPEC pass (the user's biomechanical order of 2026-10-14 night): the pelvis follows a formula, the head is locked on the centre
    # line, the spine splits the pelvic roll / yaw, arms and tail follow stated numbers.  spec = 0 gives the earlier feminine version back.
    spec = 1
    SPECSCAN = 0             # 1 = only print a table (step length x ankle placement -> knee flexion at the down / passing poses) and stop
    zb = 0.88                # hips bone base height (m) of the formula curve; fitted by spec_zb(): the highest base for which both legs reach
    z_c2 = 0.012             # Z(phi) = zb - z_c2 * cos(2 phi) - z_s2 * sin(2 phi),  phi = 2 pi * cycle phase (0 = right heel strike)
    z_s2 = 0.003
    zformula = 0             # 1 = the ordered formula as it stands (with z_amp), 0 = the same wave form fitted under the reach limit of the legs (fit_envelope with one harmonic)
    z_amp = 1.0              # scale of the formula's amplitude (1 = exactly the ordered 0.012 / 0.003); lower only if the legs cannot follow it
    knee_pts = None          # spec pass: (foot phase, least knee flexion in deg) table, see knee_min_flex
    KN_DOWN = 12.5           # least stance knee flexion at the down pose (spec: 12 .. 15 deg)
    KN_PASS = 6.0            # least stance knee flexion at the passing pose (spec: 5 .. 8 deg)
    KN_HS = 3.5              # least knee flexion at heel strike and in late swing
    amp_norm = 1             # 1 = yaw / roll amplitudes are the exact peak values (the small 2nd harmonics are scaled in)
    head_lock = 1            # 1 = the spine rolls just enough that the head bone stays on the centre line (x = 0)
    roll_abs = (0.5, 1.0, 1.0)      # cumulative share of the pelvic roll that is absorbed by spine, chest, upper chest (spec: 50 % + the remaining 50 %)
    yaw_abs_spine = 0.40     # the spine absorbs this share of the pelvic yaw
    chest_twist = 5.0        # the chest twists this many degrees against the spine, opposite to the pelvis (net chest yaw about 0)
    lock_w = (0.4, 0.8, 1.0)  # how the head-lock roll is shared by spine, chest and upper chest
    head_free = 0            # 1 = the head keeps the small nod / turn of the earlier version, 0 = gaze locked forward and level
    sway_ph = 0.0            # phase shift of the sideways hip shift (fraction of a cycle); 0 = X = sway * sin(phi), maximal over the right foot at 25 %
    arm_spec = 1             # 1 = upper arm 14 fwd / 18 back, elbow 16 +- 10 with -45 deg lag, wrist -70 deg lag +- 6
    swing_exact = 1          # 1 = the extremes of the arm swing are exactly swing_f / swing_b (the small 2nd harmonic is scaled in)
    tail_mode = 'wave'       # 'wave' = spec: rest curve (down at the base, up at the tip) + travelling sine waves; 'spring' = earlier spring cascade
    tail_abs = [-38.0, -42.0, -44.0, -40.0, -26.0, -6.0, 20.0, 40.0]   # spec rest curve: direction of each tail joint above the horizontal (deg, world, side view)
    tail_dphi = -0.55        # phase offset per joint (rad), base to tip, for both waves (the tip trails the base)
    tail_lat = 6.0           # lateral wave amplitude per joint (deg)
    tail_lat_ph = 0.0        # phase of the lateral wave at the base (rad), relative to the pelvic yaw
    tail_vert = 3.0          # vertical follow-through amplitude per joint (deg), at twice the step frequency (1 per step)
    tail_vert_ph = 0.0       # phase of the vertical wave at the base (rad), relative to the pelvis height
    ear_on = 1
    # --- spring bones: bust, hair and cat ears are simulated with the algorithm of the VRM / UniVRM spring bones (60 steps per second, the character
    # walks through the world at SPEED so the air drag acts) and written as bone rotations; the values are the ones to set in Unity afterwards
    spring_on = 1
    spring_sub = 2           # simulation steps per animation frame (2 at 30 fps = the 60 Hz of the game)
    spring_cycles = 10       # the simulation runs this many gait cycles, the last one is kept (periodic steady state)
    spring_world = 0         # 1 = the character moves through the world (headwind / trailing), 0 = standing on the spot
    spring_debug = 0
    spring_coll = 1          # 1 = the hair is pushed out of the collider spheres of the VRM
    bust_stiff = 0.40        # VRoid default 0.74: lower = softer, slower wobble that overshoots (jelly)
    bust_drag = 0.05         # VRoid default 0.05: low = it rings on for several swings after every step
    hair_stiff_mul = 1.4     # factor on the stiffness of every strand (the VRM has 0.4 .. 1.0 per strand)
    hair_drag = 0.28         # VRoid default 0.4 is heavy and makes the hair stream out horizontally while walking; 0.12 swings freely
    ear_stiff = 2.2          # VRoid default 1.5: stiffer ears follow the body less
    ear_drag = 0.30          # VRoid default 0.05 (rings): damped ears flutter much less
    spring_gravity = 0.0     # extra gravity power on all simulated bones (VRM: 0)
    spring_dirs = None       # filled by the build: bone -> list of world directions of the bone axis per frame
    spring_axes = None       # bone -> rest direction of its axis (world)


for _tok in argv[3:]:                                                # e.g.  SPEED=1.3 NF=32 PH_TO=0.6 (design experiments)
    if '=' in _tok:
        _k, _v = _tok.split('=', 1)
        if _k == 'tail_mode':
            P.tail_mode = _v
        elif _k in ('tail_abs', 'tail_walk', 'lock_w'):
            setattr(P, _k, [float(t) for t in _v.split(',')])
        else:
            setattr(P, _k, int(_v) if _k in ('NF', 'HARM', 'ARMGRID', 'LEGGRID', 'ARM_FIT', 'sec_on', 'spec', 'SPECSCAN', 'amp_norm', 'head_lock',
                                             'head_free', 'arm_spec', 'swing_exact', 'ear_on', 'spring_on', 'spring_sub', 'spring_cycles', 'spring_world', 'spring_coll', 'spring_debug') else float(_v))

for _sd in ('L', 'R'):
    if P.ARM_UP >= 0.0:
        P.arm[_sd]['up_out'] = P.ARM_UP
    if P.ARM_FORE > -99.0:
        P.arm[_sd]['fore_out'] = P.ARM_FORE
    if P.E_MAX >= 0.0:
        P.arm[_sd]['e_max'] = P.E_MAX

NF = P.NF
T_CYCLE = NF / FPS
VT = P.SPEED * T_CYCLE                                               # stride length (m)


def ground_rate(phi):
    """ground speed under the character as a multiple of the mean speed at the cycle phase phi (period: half a cycle)"""
    return 1.0 + P.speed_var * math.cos(2.0 * TWO_PI * (phi - P.speed_var_phase))


def G(phi):
    """how far the ground has moved back (m) since the right heel strike (phi = 0); G(1) = VT, the stride"""
    k = 2.0 * TWO_PI
    return VT * (phi + P.speed_var / k * (math.sin(k * (phi - P.speed_var_phase)) + math.sin(k * P.speed_var_phase)))


def dG(phi):
    """speed of the ground in metres per cycle (derivative of G by the cycle phase)"""
    return VT * ground_rate(phi)

PEAK_P = P.PH_TO / 2.0                                               # cycle phase of mid stance of the right foot

# foot geometry from the rig + the measured sole profile (rest pose, flat foot, +Y forward)
A0 = HEAD0[nm('R', 'Foot')]
J0 = HEAD0[nm('R', 'Toes')]
A0y, A0z = A0.y, A0.z                                                # ankle
J0y, J0z = J0.y, J0.z                                                # toe joint (ball of the foot)
HRy, HRz = -0.081, 0.0                                               # rear edge of the heel (ground contact)
SOLE_FOOT = [(-0.081, 0.0), (-0.060, 0.0), (-0.035, 0.0), (0.0, 0.0), (0.03, 0.0), (0.06, 0.0)]   # sole points of the foot bone
SOLE_TOE = [(J0y, 0.0), (0.10, 0.0), (0.124, 0.006)]                 # sole points of the toe bone


def low_rel(th, tau):
    """lowest sole point (z) relative to the ankle for foot pitch th and toe bend tau (radians, toes up = positive)"""
    best = 1e9
    for (py, pz) in SOLE_FOOT:
        best = min(best, rot2(th, py - A0y, pz - A0z)[1])
    jz = rot2(th, J0y - A0y, J0z - A0z)[1]
    for (py, pz) in SOLE_TOE:
        best = min(best, jz + rot2(th + tau, py - J0y, pz - J0z)[1])
    return best


def toe_bend(th):
    """the toe part stays flat while the foot pitches toes-down; smooth version of max(0, -th)"""
    e = deg(2.0)
    return 0.5 * (-th + math.sqrt(th * th + e * e)) - 0.5 * e


class Gait:
    """foot trajectory of one foot as a function of its cycle phase phi (0 = heel strike) in the character frame"""

    def __init__(self, a_hs):
        th0 = deg(P.TH_HS)
        ry, _ = rot2(th0, A0y - HRy, A0z - HRz)
        self.y_h0 = a_hs - ry                                        # heel rear edge y at heel strike
        self._build_swing()

    # ----- stance
    def theta_stance(self, phi):
        if phi < P.PH_FF:
            return deg(P.TH_HS) * (1.0 - sstep(phi / P.PH_FF))
        if phi < P.PH_HR:
            return 0.0
        u = min((phi - P.PH_HR) / (P.PH_TO - P.PH_HR), 1.0)
        return -deg(P.TH_TO) * u ** P.P_HR

    def y_stance(self, phi):
        th = self.theta_stance(phi)
        if phi <= P.PH_HR:
            hr_y = self.y_h0 - G(phi)
            ry, _ = rot2(th, A0y - HRy, A0z - HRz)
            return hr_y + ry
        hr_y_hr = self.y_h0 - G(P.PH_HR)
        j_y = hr_y_hr + (J0y - HRy) - (G(phi) - G(P.PH_HR))          # the toe joint is fixed to the ground from heel rise on
        ry, _ = rot2(th, A0y - J0y, A0z - J0z)
        return j_y + ry

    # ----- swing
    def _build_swing(self):
        h = 1e-5
        f = self.y_stance
        to = P.PH_TO
        y0, y1, y2 = f(to), f(to - h), f(to - 2 * h)
        v0 = (y0 - y1) / h
        a0 = (y0 - 2 * y1 + y2) / (h * h)
        z0, z1, z2 = f(0.0), f(h), f(2 * h)
        v1 = (-3 * z0 + 4 * z1 - z2) / (2 * h)
        a1 = (z0 - 2 * z1 + z2) / (h * h)
        D = 1.0 - to
        self.D = D
        # only position and velocity are matched (C1): the stance accelerations are dominated by the short heel rocker and would overshoot
        v0w = max(v0 + dG(to), P.SW_V0 * T_CYCLE)                     # the swing leg is kicked forward at toe off
        self.sw_y = (y0 + G(to), v0w * D, 0.0, z0 + G(1.0), (v1 + dG(0.0)) * D, 0.0)
        # swing pitch: two segments (toe off -> mid swing -> heel strike)
        self.UA = 0.42
        th_to = self.theta_stance(to)
        dth = (self.theta_stance(to) - self.theta_stance(to - h)) / h
        self.sw_th = (th_to, P.SW_FRAC * dth * D * self.UA, deg(P.TH_MS), deg(P.TH_HS))

    def theta_swing(self, phi):
        u = (phi - P.PH_TO) / self.D
        th_to, m0, th_a, th_hs = self.sw_th
        if u <= self.UA:
            return herm3(th_to, m0, th_a, 0.0, u / self.UA)
        w = (u - self.UA) / (1.0 - self.UA)
        return th_a + (th_hs - th_a) * sstep(w)

    def y_swing(self, phi):
        u = (phi - P.PH_TO) / self.D
        p0, v0, a0, p1, v1, a1 = self.sw_y
        return herm5(p0, v0, a0, p1, v1, a1, u) - G(phi)

    def clearance(self, phi):
        u = (phi - P.PH_TO) / self.D
        c = P.CLEAR * math.sin(math.pi * u ** P.CLR_GAMMA) ** 2
        if P.LATE_LIFT > 0.0 and u > P.LATE_U0:                       # the foot hovers a little higher while the leg reaches out, then settles onto the ground
            w = (u - P.LATE_U0) / (1.0 - P.LATE_U0)
            c += P.LATE_LIFT * math.sin(math.pi * w ** 1.5) ** 2
        return c

    # ----- everything at once
    def state(self, phi):
        """returns (ankle y, ankle z, foot pitch, toe bend)  [metres / radians, toes up positive]"""
        phi = phi % 1.0
        if phi < P.PH_TO:
            th = self.theta_stance(phi)
            y = self.y_stance(phi)
            c = 0.0
        else:
            th = self.theta_swing(phi)
            y = self.y_swing(phi)
            c = self.clearance(phi)
        tau = toe_bend(th)
        z = c - low_rel(th, tau)
        return y, z, th, tau

    def in_stance(self, phi):
        return (phi % 1.0) < P.PH_TO


# ------------------------------------------------------------------ pose solver
PARTS = ('Proximal', 'Intermediate', 'Distal')
GAIT = Gait(P.A_HS)


_SHAPE_MAX = {}


def _unit(key, fn):
    """1 / (largest value of the shape over the cycle): the amplitudes in the parameters are then the exact peak values"""
    if key not in _SHAPE_MAX:
        _SHAPE_MAX[key] = 1.0 / max(abs(fn(i / 720.0)) for i in range(720))
    return _SHAPE_MAX[key]


def _yaw_shape(p):
    return math.cos(TWO_PI * (p - 0.01)) + 0.14 * math.cos(2.0 * TWO_PI * (p - 0.07))


def _roll_shape(p):
    return math.cos(TWO_PI * (p - PEAK_P - 0.03)) + 0.12 * math.cos(2.0 * TWO_PI * (p - PEAK_P + 0.02))


def pelvis_yaw(p, par=P):
    """world yaw of the pelvis (deg), right hip forward at the right heel strike; a second harmonic so it is not a pure sine wave"""
    return par.yaw_p * (_unit('yaw', _yaw_shape) if par.amp_norm else 1.0) * _yaw_shape(p)


def pelvis_roll(p, par=P):
    """pelvic drop towards the swing side (deg, rotation about +Y: negative = left side down)"""
    return -par.roll_p * (_unit('roll', _roll_shape) if par.amp_norm else 1.0) * _roll_shape(p)


def lean_dive(p, par=P):
    """the torso dives into every down pose: extra forward lean in degrees, twice per cycle"""
    return par.lean_dyn * math.cos(2.0 * TWO_PI * (p - par.down_phase))


def down_bump(p, par=P):
    """0..1 bump around the two down poses (period half a cycle)"""
    d = ((p - par.down_phase + 0.25) % 0.5) - 0.25
    return math.exp(-0.5 * (d / par.down_w) ** 2) - par.rebound * math.exp(-0.5 * ((d - par.rebound_dt) / (1.3 * par.down_w)) ** 2)


def pelvis_z(p, par=P):
    """hips bone height (m): the reach-fitted curve (highest at the passing pose) minus the weight-catching dip at the down poses
    (spec pass: the formula  zb - z_c2 cos(2 phi) - z_s2 sin(2 phi): lowest just after heel strike, highest at the passing pose)"""
    if par.spec and par.zformula and par.zcoef is None and par.bob != 0.0:
        a2 = 2.0 * TWO_PI * p
        return par.zb - par.z_amp * (par.z_c2 * math.cos(a2) + par.z_s2 * math.sin(a2))
    ph = TWO_PI * (p - PEAK_P)
    if par.zcoef is not None:
        z = par.zcoef[0]
        for j in range(1, (len(par.zcoef) - 1) // 2 + 1):
            z += par.zcoef[2 * j - 1] * math.cos(2.0 * j * ph) + par.zcoef[2 * j] * math.sin(2.0 * j * ph)
        return z - par.down_extra * down_bump(p, par)
    shape = 0.5 * (1.0 + math.cos(2.0 * ph))                          # 1 at mid stance, 0 at double support
    return par.z_peak - par.bob * (1.0 - shape)


def _arm_k_range(par):
    """largest and smallest value of the arm swing shape (cosine plus its small second harmonic) over the cycle"""
    key = ('arm_k', par.arm_h2)
    if key not in _SHAPE_MAX:
        ks = [math.cos(TWO_PI * (i / 720.0)) + par.arm_h2 * math.cos(2.0 * TWO_PI * (i / 720.0) + 0.6) for i in range(720)]
        _SHAPE_MAX[key] = (max(ks), min(ks))
    return _SHAPE_MAX[key]


def tail_rest_up(par):
    """rest pitch per tail joint relative to its parent (deg, positive = up).  Spec pass: from the wanted absolute direction of every joint
    in the side view (par.tail_abs: down at the base, towards horizontal in the middle, up at the tip); the mean forward pitch of the
    pelvis is taken out so the angles hold in the world."""
    if par.spec and par.tail_mode == 'wave':
        a = par.tail_abs
        return [a[0] + (-0.40 * par.lean)] + [a[i] - a[i - 1] for i in range(1, 8)]
    return par.tail_walk


def spec_levels(p, par):
    """spec pass: cumulative (pitch, roll, yaw) in degrees of spine, chest and upper chest.  The spine absorbs half of the pelvic roll and
    40 % of the pelvic yaw, the chest the other half of the roll and a counter twist of chest_twist degrees against the spine, so the chest
    ends up level and (almost) without yaw; the forward lean builds up along the spine."""
    cum_lean = (0.62, 0.82, 1.0)
    dive_share = (0.35, 0.60, 0.80)
    twist = par.chest_twist / max(par.yaw_p, 1e-6)
    yaw_abs = (par.yaw_abs_spine, par.yaw_abs_spine + twist, par.yaw_abs_spine + twist)
    out = []
    for i in range(3):
        lag = par.sp_lag[i]
        pit = -(cum_lean[i] * par.lean + dive_share[i] * lean_dive(p - lag, par))
        roll = pelvis_roll(p - lag, par) * (1.0 - par.roll_abs[i])
        yaw = pelvis_yaw(p - lag, par) * (1.0 - yaw_abs[i])
        out.append([pit, roll, yaw])
    return out


def head_pos(levels, pel, hips_d, neck_q):
    """world position of the head bone for cumulative spine levels (forward kinematics with the same composition as compute_pose)"""
    D = eul(rx=pel[0], ry=pel[1], rz=pel[2])
    pos = HEAD0[H['hips']] + hips_d
    prev_name, prev = H['hips'], pel
    for name_, cur in zip((H['spine'], H['chest'], H['upperChest']), levels):
        pos = pos + D @ (HEAD0[name_] - HEAD0[prev_name])
        D = D @ eul(rx=cur[0] - prev[0], ry=cur[1] - prev[1], rz=cur[2] - prev[2])
        prev_name, prev = name_, cur
    pos = pos + D @ (HEAD0[H['neck']] - HEAD0[prev_name])
    return pos + neck_q @ (HEAD0[H['head']] - HEAD0[H['neck']])


def lock_head(levels, pel, hips_d, neck_q, par):
    """extra roll c (deg) that is added to the spine levels (weights par.lock_w) so that the head bone stays on x = 0: the hips shift over
    the stance foot and the pelvis rolls, the torso leans back over the centre line.  Secant iteration on the exact forward kinematics."""
    def xh(c):
        lv = [[l[0], l[1] + c * w, l[2]] for l, w in zip(levels, par.lock_w)]
        return head_pos(lv, pel, hips_d, neck_q).x

    x0 = xh(0.0)
    c1 = -1.5
    slope = (xh(c1) - x0) / c1
    c = -x0 / slope
    for _ in range(3):
        c -= xh(c) / slope
    return c


def solve(f, par=P, light=False):
    """pose at frame f (cycle phase p = f / NF); light = pelvis, spine and legs only (design search)"""
    p = (f / NF) % 1.0
    c1 = math.cos(TWO_PI * p)                                         # +1 at the right heel strike
    s1 = math.sin(TWO_PI * p)
    ph = TWO_PI * (p - PEAK_P)
    rel = {}
    absd = {}
    diag = {'reach_deficit': 0.0}

    # --- pelvis: rotation in the walking direction, drop to the swing side, nod, and weight (see pelvis_z)
    yaw_w = pelvis_yaw(p, par)
    roll_w = pelvis_roll(p, par)
    pitch_w = -0.40 * par.lean + par.pitch_amp * math.cos(2.0 * ph + 1.0) - 0.35 * lean_dive(p, par)
    rel[H['hips']] = eul(rx=pitch_w, ry=roll_w, rz=yaw_w)

    # --- spine: the counter rotation, the opposite roll (S-curve) and the forward lean travel up the spine with a lag
    # (spec pass: the spine and chest split the pelvic roll / yaw, see spec_levels, and the head is locked on the centre line)
    if par.spec:
        levels = spec_levels(p, par)
    else:
        levels = []
        cum_lean = (0.62, 0.82, 1.0)
        dive_share = (0.35, 0.60, 0.80)
        for i in range(3):
            share, lag = par.sp_share[i], par.sp_lag[i]
            yaw_l = -par.yaw_c * share * (math.cos(TWO_PI * (p - lag)) + 0.10 * math.cos(2.0 * TWO_PI * (p - lag - 0.05)))
            roll_l = -par.torso_roll * share * pelvis_roll(p - lag, par)
            pit_l = -(cum_lean[i] * par.lean + dive_share[i] * lean_dive(p - lag, par))
            levels.append([pit_l, roll_l, yaw_l])
    hips_rest = HEAD0[H['hips']]
    if par.spec:
        sway_x = par.sway * math.sin(TWO_PI * (p - par.sway_ph))          # X(phi) = sway * sin(phi): over the right foot at 25 % of the cycle
    else:
        sway_x = par.sway * (math.cos(ph) + 0.12 * math.cos(2.0 * ph + 1.2))
    hips_d = Vector((sway_x,
                     -par.surge * math.sin(2.0 * ph),
                     pelvis_z(p, par) - hips_rest.z))

    # --- neck and head: calm and level (absolute world orientation), the neck takes part of the shoulder counter rotation
    if par.spec and not par.head_free:                                # spec: neck and head cancel everything, the gaze stays level and forward
        absd[H['neck']] = Quaternion()
        absd[H['head']] = Quaternion()
        if par.head_lock and not light:
            c_lock = lock_head(levels, (pitch_w, roll_w, yaw_w), hips_d, absd[H['neck']], par)
            for lv_, w_ in zip(levels, par.lock_w):
                lv_[1] += c_lock * w_
            diag['head_lock_roll'] = c_lock
    else:
        psi_u = levels[2][2]                                          # world yaw of the shoulders
        yaw_h = 0.6 * math.sin(TWO_PI * p + 0.7)
        pit_h = 0.4 * math.sin(2.0 * ph + 0.4) + 0.6
        rol_h = -0.25 * math.cos(ph)
        absd[H['neck']] = eul(rx=0.5 * pit_h, ry=0.5 * rol_h, rz=0.45 * psi_u + 0.5 * yaw_h)
        absd[H['head']] = eul(rx=pit_h, ry=rol_h, rz=yaw_h)
    prev = (pitch_w, roll_w, yaw_w)
    for name_, cur in zip((H['spine'], H['chest'], H['upperChest']), levels):
        rel[name_] = eul(rx=cur[0] - prev[0], ry=cur[1] - prev[1], rz=cur[2] - prev[2])
        prev = cur

    # --- shoulders (clavicles): sink a little at every down pose, shoulder blade moves forward with the arm
    for side, sx in (('L', -1.0), ('R', 1.0)):
        sw = s1 * (1.0 if side == 'L' else -1.0)
        kf = c1 if side == 'L' else -c1                               # +1 = this arm swings forward
        drop = 1.5 * math.cos(2.0 * TWO_PI * (p - par.down_phase - 0.02))
        rel[nm(side, 'Shoulder')] = eul(ry=sx * (4.0 + 0.8 * sw + drop), rz=sx * par.pro * kf)

    if light:
        return rel, absd, hips_d, _legs(p, par, rel), diag

    # --- cat tail: rest curve plus a travelling wave (par.tail_dyn, see tail_ear_tables): every joint trails the one before
    rest_up = tail_rest_up(par)
    for i in range(1, 9):
        up = rest_up[i - 1] + (par.tail_lift if i <= 2 else 0.0)
        pit_t, yaw_t = (0.0, 0.0)
        if par.tail_dyn is not None:
            pit_t, yaw_t = par.tail_dyn[i - 1][int(round(f)) % NF]
        rel['J_Opt_C_CatTail%d_01' % i] = eul(rx=-(up + pit_t), rz=yaw_t)

    # --- hair (first pass only, the spring simulation replaces it): small bouncing wave down every strand
    for name in ([] if par.spec else HAIR):
        m = HAIR_RE.match(name)
        depth, chain = int(m.group(1)), int(m.group(2))
        rel[name] = eul(rx=2.0 * math.sin(2.0 * TWO_PI * p + 0.6 * chain - 0.35 * depth),
                        ry=1.2 * math.sin(TWO_PI * p + 0.4 * chain - 0.3 * depth))

    # --- arms: absolute directions + palm normals; swing against the legs (left arm forward at the right heel strike).
    # The upper arm swings from the shoulder; the elbow is almost straight in the back swing and bends gently in the forward
    # swing, its bend peaks after the upper arm (overlapping action); the wrist trails again; the arm comes in towards the body
    # in front and goes out behind.
    k_hi, k_lo = _arm_k_range(par)

    def swing(ph_):
        k_ = math.cos(TWO_PI * ph_) + par.arm_h2 * math.cos(2.0 * TWO_PI * ph_ + 0.6)
        if par.swing_exact:                                           # the extremes are exactly swing_f forward and swing_b back
            k_ = (2.0 * k_ - (k_hi + k_lo)) / (k_hi - k_lo)
        return k_, deg(0.5 * (par.swing_f - par.swing_b) + 0.5 * (par.swing_f + par.swing_b) * k_)

    for side, sx in (('L', -1.0), ('R', 1.0)):
        ap = par.arm[side]
        pa = p if side == 'L' else p + 0.5                            # phase of this arm (forward at 0)
        k_u, sig_u = swing(pa)
        k_e = (0.5 + 0.5 * math.cos(TWO_PI * (pa - par.lag_e))) ** par.e_pow
        e_fl = deg(par.e_min + (ap['e_max'] - par.e_min) * k_e)       # elbow flexion
        k_w = math.cos(TWO_PI * (pa - par.lag_w))
        b_f = sig_u + e_fl                                            # forearm pitch = upper arm pitch + elbow flexion
        b_h = b_f + deg(par.wr_base + par.wr_amp * k_w)
        a_u = deg(ap['up_out'] - par.arm_abd * k_u)
        a_f = deg(ap['fore_out'] - 0.6 * par.arm_abd * k_u)
        rest_dir = Vector((sx, 0, 0))
        rest_nrm = Vector((0, 0, -1))
        d0 = Vector((sx * math.sin(a_u), par.arm_fwd0, -math.cos(a_u)))
        cs, sn = math.cos(sig_u), math.sin(sig_u)                     # swing about the lateral axis (forward = +Y)
        d_u = Vector((d0.x, d0.y * cs - d0.z * sn, d0.y * sn + d0.z * cs))
        d_f = Vector((sx * math.sin(a_f), math.sin(b_f), -math.cos(b_f) * math.cos(a_f)))
        d_h = Vector((sx * (0.12 + math.tan(deg(par.wr_dev)) * math.cos(TWO_PI * (pa - par.wr_dev_lag))), math.sin(b_h), -0.97))
        absd[nm(side, 'UpperArm')] = aim(rest_dir, rest_nrm, d_u, Vector((-sx, -0.15, 0.0)))
        absd[nm(side, 'LowerArm')] = aim(rest_dir, rest_nrm, d_f, Vector((-sx, -0.12, 0.0)))
        absd[nm(side, 'Hand')] = aim(rest_dir, rest_nrm, d_h, Vector((-sx, -0.22 - par.palm_turn * math.cos(TWO_PI * (pa - par.palm_lag)), 0.0)))
        # relaxed, ready hand: fingers loosely closed (a little tighter in the forward swing), thumb alongside the hand
        for fi, (fn, curls) in enumerate(par.fingers.items()):
            for pj, (part, c) in enumerate(zip(PARTS, curls)):
                wave = math.cos(TWO_PI * (pa - par.fing_lag - par.fing_lag_f * fi - par.fing_lag_p * pj))
                q_ = Quaternion((0, 1, 0), deg(sx * (c + par.fing_dyn[pj] * wave)))
                if pj == 0:
                    q_ = eul(rz=sx * par.fing_spread[fi]) @ q_
                rel[nm(side, fn + part)] = q_
        tw = math.cos(TWO_PI * (pa - par.fing_lag - 0.04))
        rel[nm(side, 'ThumbProximal')] = eul(rz=-sx * par.thumb_add) @ Quaternion((0, 1, 0), deg(sx * (10.0 + par.thumb_dyn * tw)))
        rel[nm(side, 'ThumbIntermediate')] = Quaternion((0, 1, 0), deg(sx * (18.0 + 0.6 * par.thumb_dyn * math.cos(TWO_PI * (pa - par.fing_lag - 0.07)))))
        rel[nm(side, 'ThumbDistal')] = Quaternion((0, 1, 0), deg(sx * (12.0 + 0.5 * par.thumb_dyn * math.cos(TWO_PI * (pa - par.fing_lag - 0.10)))))

    # --- bust, hair and ears: spring simulation of the body motion (computed by the build, see secondary_tables)
    if par.sec is not None:
        i_ = int(round(f)) % NF
        for name_, rots_ in par.sec.items():
            rx_, ry_, rz_ = rots_[i_]
            rel[name_] = eul(rx=rx_, ry=ry_, rz=rz_)

    return rel, absd, hips_d, _legs(p, par, rel), diag


def swing_weight(phi, par=P):
    """0 while the foot is on the ground, 1 in the middle of the swing (smooth)"""
    a = sstep((phi - (par.PH_TO - 0.05)) / 0.10)
    b = 1.0 - sstep((phi - 0.88) / 0.12)
    return a * b


def _legs(p, par, rel):
    """foot targets from the gait model: ankle position, foot rotation, yaw, toe bend, foot phase per side.
    Narrow cat-like track; the swing foot goes out a little around the other leg and lands back on the track; the swing leg turns
    with the pelvis, a planted foot never turns."""
    legs = {}
    psi = pelvis_yaw(p, par)
    for side, sx in (('R', 1.0), ('L', -1.0)):
        phi = p if side == 'R' else (p + 0.5) % 1.0
        y, z, th, tau = GAIT.state(phi)
        sw = swing_weight(phi, par)
        u_sw = (phi - par.PH_TO) / (1.0 - par.PH_TO)
        circ = par.CIRC * math.sin(math.pi * u_sw) ** 2 if 0.0 <= u_sw <= 1.0 else 0.0
        x = sx * (par.BASE + circ)
        turn = par.SW_YAW * psi * sw
        yaw = (-par.TOE_OUT if side == 'R' else par.TOE_OUT) + turn                 # foot direction (planted: constant)
        yaw_knee = (-par.KNEE_OUT if side == 'R' else par.KNEE_OUT) + turn          # direction of the knee bend plane
        legs[side] = (Vector((x, y, z)), eul(rx=math.degrees(th), rz=yaw), yaw_knee, tau, phi)
        rel[nm(side, 'Toes')] = eul(rx=math.degrees(tau))
    return legs


def compute_pose(f, par=P):
    rel, absd, hips_d, legs, diag = solve(f, par)
    D = {}
    Q = {}
    ik = {}
    hips_name = H['hips']
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        if par.spring_dirs is not None and name in par.spring_dirs:      # spring bone: the axis points where the simulation put it
            D[name] = (Dp @ par.spring_axes[name]).rotation_difference(par.spring_dirs[name][int(round(f)) % NF]) @ Dp
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
                K0 = HEAD0[nm(side, 'LowerLeg')]
                A0_ = HEAD0[nm(side, 'Foot')]
                L1 = (K0 - Hp0).length
                L2 = (A0_ - K0).length
                T, foot_rot, yaw, tau, phi = legs[side]
                pole = Vector((-math.sin(deg(yaw)), math.cos(deg(yaw)), 0.0))
                K, Teff, deficit, ext = two_bone_ik(Hp, T, pole, L1, L2)
                diag['reach_deficit'] = max(diag['reach_deficit'], deficit)
                diag['ext_' + side] = ext
                a1 = (Hp - K).normalized()
                a2 = (Teff - K).normalized()
                diag['knee_' + side] = 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, a1.dot(a2)))))
                diag['hip_' + side] = Hp.copy()
                ik[side] = (K, Teff)
                D[name] = (K0 - Hp0).rotation_difference(K - Hp)
            elif name == nm(side, 'LowerLeg'):
                K0 = HEAD0[name]
                A0_ = HEAD0[nm(side, 'Foot')]
                K, Teff = ik[side]
                D[name] = (A0_ - K0).rotation_difference(Teff - K)
            elif name == nm(side, 'Foot'):
                D[name] = legs[side][1]
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    hips_loc = R[hips_name].inverted() @ hips_d
    diag['legs'] = legs
    return Q, hips_loc, D, diag, hips_d


# ------------------------------------------------------------------ design: ankle placement + pelvis height fitted against the legs
LEG_L1 = (HEAD0[nm('R', 'LowerLeg')] - HEAD0[nm('R', 'UpperLeg')]).length
LEG_L2 = (HEAD0[nm('R', 'Foot')] - HEAD0[nm('R', 'LowerLeg')]).length


def probe(f, par=P):
    """pelvis + legs only (fast): per side (extension d/(L1+L2), knee flexion in degrees, ankle target, hip joint)"""
    rel, absd, hips_d, legs, diag = solve(f, par, light=True)
    q = rel[H['hips']]
    hip_head = HEAD0[H['hips']]
    out = {}
    for side in ('L', 'R'):
        Hp0 = HEAD0[nm(side, 'UpperLeg')]
        Hp = hip_head + hips_d + q @ (Hp0 - hip_head)
        T, _, yaw, _, phi = legs[side]
        pole = Vector((-math.sin(deg(yaw)), math.cos(deg(yaw)), 0.0))
        K, Teff, deficit, ext = two_bone_ik(Hp, T, pole, LEG_L1, LEG_L2)
        a1 = (Hp - K).normalized()
        a2 = (Teff - K).normalized()
        knee = 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, a1.dot(a2)))))
        out[side] = (ext, knee, T, Hp, phi)
    return out


def knee_min_flex(phi, par=P):
    """smallest knee flexion (deg) a leg may have at foot phase phi: nearly straight at heel strike, a clear bend before toe off"""
    pts = [(0.0, par.KNEE_HS), (0.06, par.KNEE_ST), (0.40, par.KNEE_ST), (par.PH_TO, par.KNEE_TO), (0.80, 0.8 * par.KNEE_TO), (1.0, par.KNEE_HS)]
    if par.spec:
        # contact (nearly straight) -> down (the knee takes the weight: 12 .. 15 deg) -> passing (soft, never locked: 5 .. 8 deg) -> push-off
        pts = par.knee_pts or [(0.0, par.KN_HS), (0.10, par.KN_DOWN), (PEAK_P, par.KN_PASS), (0.45, 0.5 * (par.KN_PASS + par.KNEE_TO)),
                               (par.PH_TO, par.KNEE_TO), (0.78, 13.0), (0.90, par.KN_HS), (1.0, par.KN_HS)]   # the swing leg reaches out nearly straight before it lands
    phi = phi % 1.0
    for (a, ka), (b, kb) in zip(pts, pts[1:]):
        if a <= phi <= b:
            return ka + (kb - ka) * (phi - a) / (b - a)
    return par.KNEE_HS


def ext_cap(phi, par=P):
    return min(par.EXT_CAP, math.cos(math.radians(knee_min_flex(phi, par)) / 2.0))


def violation(o, par=P):
    return max(o['R'][0] - ext_cap(o['R'][4], par), o['L'][0] - ext_cap(o['L'][4], par))


def design_metrics(par=P):
    """max leg extension over the cycle plus a per-frame table (knee flexion R, L, extension R, L)"""
    worst = 0.0
    kn = []
    for f in range(NF):
        o = probe(f, par)
        worst = max(worst, o['L'][0], o['R'][0])
        kn.append((o['R'][1], o['L'][1], o['R'][0], o['L'][0], violation(o, par)))
    return worst, kn


def fit_z_peak(par, knee_mid):
    """hips height at mid stance such that the standing knee is flexed by knee_mid degrees"""
    lo, hi = 0.70, 0.95
    f_mid = PEAK_P * NF
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        par.z_peak = mid
        k = probe(f_mid, par)['R'][1]
        if k > knee_mid:        # knee too bent -> raise the pelvis
            lo = mid
        else:
            hi = mid
    par.z_peak = 0.5 * (lo + hi)
    return par.z_peak


def fit_bob(par):
    """smallest bob for which no leg gets longer than EXT_CAP"""
    lo, hi = 0.0, 0.20
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        par.bob = mid
        worst, _ = design_metrics(par)
        if worst > par.EXT_CAP:
            lo = mid
        else:
            hi = mid
    par.bob = hi
    return hi


def reach_limit(f, par):
    """highest hips height at frame f for which both legs still reach their feet (EXT_CAP)"""
    zc = par.zcoef
    par.zcoef = None
    lo, hi = 0.60, 1.05
    saved = (par.z_peak, par.bob)
    par.bob = 0.0
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        par.z_peak = mid
        o = probe(f, par)
        if violation(o, par) > 0.0:
            hi = mid
        else:
            lo = mid
    par.z_peak, par.bob = saved
    par.zcoef = zc
    return lo


def fit_envelope(par, knee_mid=None, harmonics=None, samples=None):
    """pelvis height = smooth periodic curve (few harmonics of the step frequency) that stays under the reach limit of both
    legs and under the height that gives the wanted knee flexion at mid stance. Weighted least squares, the weights grow where
    the curve would poke through the limit, so the curve ends up as high as its shape allows.
    returns (bob peak-to-peak, highest, lowest, phase of the lowest, phase of the highest)"""
    knee_mid = par.KNEE_MID if knee_mid is None else knee_mid
    harmonics = par.HARM if harmonics is None else int(harmonics)
    samples = samples or NF * 4
    par.zcoef = None
    z_cap = fit_z_peak(par, knee_mid)
    xs = [i / samples for i in range(samples)]
    E = [reach_limit(x * NF, par) for x in xs]
    # the final pelvis height is the fitted curve minus down_extra * down_bump (a dip and a spring-back above the curve):
    # the curve itself may be higher than the reach limit where the dip lowers it and must stay lower where the rebound lifts it
    E = [e + par.down_extra * min(down_bump(x, par), 0.0) for e, x in zip(E, xs)]       # only the spring-back (negative part) lowers the allowed curve; the dip may go deeper than the reach limit
    target = [min(e - par.MARGIN, z_cap) for e in E]
    n = 1 + 2 * harmonics
    rows = []
    for x in xs:
        ph = TWO_PI * (x - PEAK_P)
        row = [1.0]
        for j in range(1, harmonics + 1):
            row += [math.cos(2.0 * j * ph), math.sin(2.0 * j * ph)]
        rows.append(row)

    def solve_weighted(w):
        A = [[0.0] * n for _ in range(n)]
        b = [0.0] * n
        for row, tgt, wi in zip(rows, target, w):
            for r in range(n):
                b[r] += wi * row[r] * tgt
                for c in range(n):
                    A[r][c] += wi * row[r] * row[c]
        M = [A[r] + [b[r]] for r in range(n)]
        for c in range(n):
            piv = max(range(c, n), key=lambda r: abs(M[r][c]))
            M[c], M[piv] = M[piv], M[c]
            for r in range(n):
                if r != c:
                    fct = M[r][c] / M[c][c]
                    for k in range(c, n + 1):
                        M[r][k] -= fct * M[c][k]
        return [M[r][n] / M[r][r] for r in range(n)]

    def curve(coef):
        return [sum(c * r for c, r in zip(coef, row)) for row in rows]

    w = [1.0] * samples
    coef = solve_weighted(w)
    for it in range(14):
        zs = curve(coef)
        for k in range(samples):
            over = zs[k] - (E[k] - par.FIT_IN)
            if over > 0.0:
                w[k] *= 1.0 + 6.0 * over / 0.004
        coef = solve_weighted(w)
    zs = curve(coef)
    viol = max(z - (e - par.FIT_FINAL) for z, e in zip(zs, E))
    coef[0] -= max(viol, 0.0)
    par.zcoef = coef
    zs = curve(coef)
    return max(zs) - min(zs), max(zs), min(zs), xs[zs.index(min(zs))], xs[zs.index(max(zs))]


def fit_gait():
    """ankle placement at heel strike with the smallest pelvis bob; sets P.A_HS, GAIT and P.zcoef"""
    global GAIT
    best = None
    for a in [x / 100.0 for x in range(24, 46, 1)]:
        P.A_HS = a
        GAIT = Gait(a)
        res = fit_envelope(P)
        if best is None or res[0] < best[0][0]:
            best = (res, a, list(P.zcoef))
    res, a, coef = best
    P.A_HS = a
    GAIT = Gait(a)
    P.zcoef = coef
    return res, a


def spec_zb(par, samples=None):
    """spec pass: the highest base height zb of the formula pelvis curve for which both legs still reach their feet (extension caps
    from the knee flexion table), found by bisection over the whole cycle"""
    samples = samples or NF * 4
    lo, hi = 0.70, 1.00
    for _ in range(34):
        mid = 0.5 * (lo + hi)
        par.zb = mid
        worst = max(violation(probe(k * NF / samples, par), par) for k in range(samples))
        if worst > 0.0:
            hi = mid
        else:
            lo = mid
    par.zb = lo
    return lo


def spec_stats(par):
    """right leg: knee flexion at heel strike, the loading peak (phase 0 .. 0.20) and the mid-stance / passing minimum (0.20 .. 0.42), pelvis range"""
    ks = [(k / (NF * 4.0), probe(k / 4.0, par)['R'][1]) for k in range(NF * 4)]
    hs = ks[0][1]
    load = max(k for (x, k) in ks if x <= 0.20)
    xs_l = [x for (x, k) in ks if x <= 0.20 and k == load][0]
    mid = min(k for (x, k) in ks if 0.20 <= x <= 0.42)
    xs_m = [x for (x, k) in ks if 0.20 <= x <= 0.42 and k == mid][0]
    zs = [pelvis_z(k / (NF * 4.0), par) for k in range(NF * 4)]
    par._down_flex = probe(0.10 * NF, par)['R'][1]
    return hs, load, xs_l, mid, xs_m, min(zs), max(zs)


TRACE = len(argv) > 2 and argv[2] == 'trace'
if P.SPECSCAN == 2:                                                  # detailed table for one setting (A_HS from the parameters)
    GAIT = Gait(P.A_HS)
    if P.zformula:
        zb_ = spec_zb(P)
        E_ = None
    else:
        fit_envelope(P, knee_mid=P.KN_PASS, harmonics=P.HARM)
        zb_ = P.zcoef[0]
        zc_ = P.zcoef
        E_ = []
        for k in range(NF * 2):
            E_.append(reach_limit(k / 2.0, P))
    log('SPEC TRACE: stride %.3f A_HS %.3f zb %.4f' % (VT, P.A_HS, zb_))
    log('phase  pelvis z  reach E | R: phi  ext   cap   knee  ankle(y,z)        | L: phi  ext   cap   knee  ankle(y,z)')
    for k in range(NF * 2):
        f_ = k / 2.0
        o_ = probe(f_, P)
        r_, l_ = o_['R'], o_['L']
        log('%.3f  %.4f  %s | %.3f %.4f %.4f %5.1f (%+.3f,%.3f) | %.3f %.4f %.4f %5.1f (%+.3f,%.3f)' % (
            f_ / NF, pelvis_z(f_ / NF, P), ('%.4f' % E_[k]) if E_ else '  -   ', r_[4], r_[0], ext_cap(r_[4], P), r_[1], r_[2].y, r_[2].z,
            l_[4], l_[0], ext_cap(l_[4], P), l_[1], l_[2].y, l_[2].z))
    sys.exit(0)
if P.SPECSCAN == 1:
    log('SPEC SCAN (NF %d, PH_TO %.2f): step | A_HS | zb | pelvis | knee flexion: heel strike, loading peak (at phase), mid stance min (at phase)' % (NF, P.PH_TO))
    for vt_ in [float(x) for x in os.environ.get('SCAN_VT', '0.78,0.84,0.90,0.96').split(',')]:
        VT = vt_
        for amp_ in [float(x) for x in os.environ.get('SCAN_AMP', '0.4,0.6,0.8,1.0').split(',')]:
            P.z_amp = amp_
            for a_ in [float(x) for x in os.environ.get('SCAN_A', '0.15,0.18,0.21,0.24').split(',')]:
                P.A_HS = a_
                GAIT = Gait(a_)
                if P.zformula:
                    zb_ = spec_zb(P)
                    ext_ = ''
                else:
                    r_ = fit_envelope(P, knee_mid=P.KN_PASS, harmonics=P.HARM)
                    zb_ = P.zcoef[0]
                    ext_ = ' (fit: lowest at %.2f, highest at %.2f)' % (r_[3], r_[4])
                hs_, load_, xl_, mid_, xm_, zlo_, zhi_ = spec_stats(P)
                log('stride %.2f (step %.3f, %.2f m/s) amp %.1f A_HS %.2f | zb %.4f pelvis %.4f..%.4f (%.1f mm) | knee: HS %4.1f  down(0.10) %4.1f  load %4.1f (at %.2f)  mid %4.1f (at %.2f)%s' % (
                    vt_, vt_ / 2.0, vt_ / T_CYCLE, amp_, a_, zb_, zlo_, zhi_, 1000.0 * (zhi_ - zlo_), hs_, P._down_flex, load_, xl_, mid_, xm_, ext_))
    sys.exit(0)

log('stride %.3f m, cycle %.3f s, speed %.2f m/s (%.0f steps/min), step %.3f m = %.2f x leg, leg L1/L2 %.4f/%.4f' % (
    VT, T_CYCLE, P.SPEED, 120.0 / T_CYCLE, VT / 2, VT / 2 / 0.857, LEG_L1, LEG_L2))
if TRACE:
    a_hs = float(argv[3]) if len(argv) > 3 and '=' not in argv[3] else P.A_HS
    P.A_HS = a_hs
    GAIT = Gait(a_hs)
    if a_hs <= 0:
        fit_gait()
        a_hs = P.A_HS
    log('trace: A_HS %.3f z_peak %.3f bob %.3f  y_h0 %.3f' % (a_hs, P.z_peak, P.bob, GAIT.y_h0))
    log('phi    ankle_y  ankle_z  pitch  toe | R: ext  knee  hipz | L: ext knee')
    for f in range(NF):
        o = probe(f, P)
        y, z, th, tau = GAIT.state(f / NF)
        log('%.3f  %+.3f  %.3f  %+6.1f  %5.1f | %.4f %5.1f %.3f | %.4f %5.1f   foot R at (%.3f,%.3f) L at (%.3f,%.3f)' % (
            f / NF, y, z, math.degrees(th), math.degrees(tau), o['R'][0], o['R'][1], o['R'][3].z, o['L'][0], o['L'][1],
            o['R'][2].y, o['R'][2].z, o['L'][2].y, o['L'][2].z))
    sys.exit(0)
if len(argv) > 2 and argv[2] == 'summary':
    res, a = fit_gait()
    worst, kn = design_metrics(P)
    stance = [k[0] for i, k in enumerate(kn) if (i / NF) < P.PH_TO]
    log('SUMMARY NF=%d v=%.2f step=%.3f cadence=%.0f | A_HS %.2f bob %.3f pelvis %.3f..%.3f | stance knee: HS %.0f, max %.0f, min %.0f, TO %.0f | swing max %.0f' % (
        NF, P.SPEED, VT / 2, 120.0 / T_CYCLE, a, res[0], res[2], res[1], kn[0][0], max(stance), min(stance), kn[int(P.PH_TO * NF)][0], max(k[0] for k in kn)))
    sys.exit(0)
if len(argv) > 2 and argv[2] == 'envelope':
    P.A_HS = float(argv[3])
    GAIT = Gait(P.A_HS)
    log('reach limit of the hips height per frame (cap %.4f), binding leg' % P.EXT_CAP)
    for f in range(NF):
        e = reach_limit(f, P)
        saved = (P.z_peak, P.bob)
        P.bob = 0.0
        P.z_peak = e + 0.002
        o = probe(f, P)
        P.z_peak, P.bob = saved
        bind = 'R' if o['R'][0] > o['L'][0] else 'L'
        log('frame %2d p=%.3f  E=%.3f  binding %s (R phi %.2f ext %.4f | L phi %.2f ext %.4f)' % (
            f, f / NF, e, bind, o['R'][4], o['R'][0], o['L'][4], o['L'][0]))
    sys.exit(0)
if DESIGN_ONLY:
    for knee_mid in (15.0, 22.0, 30.0):
        best = None
        for a in [x / 100.0 for x in range(26, 44, 2)]:
            P.A_HS = a
            GAIT = Gait(a)
            res = fit_envelope(P, knee_mid)
            if best is None or res[0] < best[0][0]:
                best = (res, a, list(P.zcoef))
        res, a, coef = best
        P.A_HS = a
        GAIT = Gait(a)
        P.zcoef = coef
        worst, kn = design_metrics(P)
        kmax = max(max(k[0], k[1]) for k in kn)
        log('knee at mid stance %.0f deg -> A_HS %.2f, bob %.3f m (hips %.3f .. %.3f, lowest at p=%.2f, highest at p=%.2f), ext max %.4f, max knee %.1f deg' % (
            knee_mid, a, res[0], res[2], res[1], res[3], res[4], worst, kmax))
    sys.exit(0)


# ================================================================== build
log('--- build: stride %.3f m, cycle %d frames (%.3f s), speed %.2f m/s' % (VT, NF, T_CYCLE, P.SPEED))
scene.frame_start = 0
scene.frame_end = NF

# ------------------------------------------------------------------ 1. gait design: ankle placement + pelvis curve
if P.spec:
    GAIT = Gait(P.A_HS)
    res = fit_envelope(P, knee_mid=P.KN_PASS, harmonics=P.HARM)       # the pelvis wave under the reach limit of the legs (see the knee table)
    a = P.A_HS
else:
    res, a = fit_gait()
worst_ext, kn_table = design_metrics(P)
log('design: ankle at heel strike %.2f m ahead of the hip, pelvis %.3f .. %.3f m (bob %.3f m), max leg extension %.4f' % (
    a, res[2], res[1], res[0], worst_ext))
kn_mid = probe(PEAK_P * NF, P)['R'][1]
log('knee flexion: standing leg at mid stance %.1f deg, maximum (swing) %.1f deg' % (kn_mid, max(max(k[0], k[1]) for k in kn_table)))


# ------------------------------------------------------------------ 2. keyframes
def build_action(par=P):
    if arm.animation_data and arm.animation_data.action:
        old_action = arm.animation_data.action
        arm.animation_data.action = None
        bpy.data.actions.remove(old_action)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
    keyed = None
    prev = {}
    max_deficit = 0.0
    frames_data = []
    for f in range(NF + 1):
        Q, hips_loc, D, diag, hips_d = compute_pose(f, par)
        max_deficit = max(max_deficit, diag['reach_deficit'])
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
        if par.tail_scale != 1.0:
            pbt = arm.pose.bones['J_Opt_C_CatTail1_01']
            pbt.scale = (par.tail_scale, par.tail_scale, par.tail_scale)
            pbt.keyframe_insert('scale', frame=f)
        frames_data.append({'frame': f, 'hips_world_offset': list(hips_d),
                            'D': {n: [D[n].w, D[n].x, D[n].y, D[n].z] for n in H.values()}})
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action.name = 'Yoru_Walk'
        arm.animation_data.action.use_fake_user = True
        set_linear(arm.animation_data.action)
    return max_deficit, frames_data


max_def, frames_data = build_action(P)
log('keys built, feet reach deficit %.5f m' % max_def)

_INVISIBLE = [None]


def invisible_polygons():
    """polygons of the body mesh that are cut away by the alpha of their texture (the long coat hem of the VRoid outfit): they are not
    visible, so they must not count as a collision; sampled once from the textures at the UVs of every polygon"""
    if _INVISIBLE[0] is not None:
        return _INVISIBLE[0]
    import numpy as np
    me = body.data
    imgs = {}
    for mi, m in enumerate(me.materials):
        if m is None or not m.use_nodes:
            continue
        for n_ in m.node_tree.nodes:
            if n_.type == 'TEX_IMAGE' and n_.image:
                w_, h_ = n_.image.size
                px = np.array(n_.image.pixels[:], dtype=np.float32).reshape(h_, w_, 4)[:, :, 3]
                imgs[mi] = (px, w_, h_)
                break
    uv = me.uv_layers.active.data
    out = set()
    for poly in me.polygons:
        im = imgs.get(poly.material_index)
        if im is None:
            continue
        px, w_, h_ = im
        a_ = 0.0
        for li in poly.loop_indices:
            u_, v_ = uv[li].uv
            a_ += px[int(min(max(v_, 0.0), 0.9999) * h_), int(min(max(u_, 0.0), 0.9999) * w_)]
        if a_ / len(poly.loop_indices) < 0.3:
            out.add(poly.index)
    _INVISIBLE[0] = out
    log('invisible (alpha-cut) polygons ignored in the collision check: %d of %d' % (len(out), len(me.polygons)))
    return out


def visible_vertices():
    """vertices that belong to at least one visible polygon (the long coat hem of the outfit is cut away by the alpha of its texture
    and is not a real obstacle for arms, tail or legs)"""
    inv = invisible_polygons()
    vis = [False] * len(body.data.vertices)
    for poly in body.data.polygons:
        if poly.index not in inv:
            for vi in poly.vertices:
                vis[vi] = True
    return vis


# ------------------------------------------------------------------ 3. clearance of the arms against the gear (numbers only)
vg_names = {vg.index: vg.name for vg in body.vertex_groups}
torso_like = {H['hips'], H['spine'], H['chest'], H['upperChest']}
thigh_like = {H['leftUpperLeg'], H['rightUpperLeg']}
torso_idx, thigh_idx = [], []
VIS = visible_vertices()
for v in body.data.vertices:
    if not v.groups or not VIS[v.index]:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    n = vg_names.get(g.group, '')
    if n in torso_like or n.startswith('J_Sec_'):
        torso_idx.append(v.index)
    elif n in thigh_like:
        thigh_idx.append(v.index)
log('body verts', len(body.data.vertices), 'torso-like', len(torso_idx), 'thigh-like', len(thigh_idx))


def arm_points(dg):
    arm_ev = arm.evaluated_get(dg)
    pts = []
    for side in ('L', 'R'):
        for part, r in (('UpperArm', 0.050), ('LowerArm', 0.042), ('Hand', 0.036)):
            pb = arm_ev.pose.bones[nm(side, part)]
            h, tl = pb.head.copy(), pb.tail.copy()
            n = 8
            for i in range(3 if part == 'UpperArm' else 0, n + 1):
                pts.append((h.lerp(tl, i / n), r, side, part))
            if part == 'Hand':
                d = (tl - h).normalized()
                for i in range(1, 5):
                    pts.append((tl + d * (0.02 * i), 0.03, side, 'Fingers'))
    return pts


def evaluated_coords():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    co = [v.co.copy() for v in me.vertices]
    ev.to_mesh_clear()
    return dg, co


def min_clearance(frames):
    worst = {'L': (9.0, None), 'R': (9.0, None)}
    for f in frames:
        scene.frame_set(f)
        dg, co = evaluated_coords()
        kd = KDTree(len(torso_idx) + len(thigh_idx))
        for i, vi in enumerate(torso_idx + thigh_idx):
            kd.insert(co[vi], i)
        kd.balance()
        for pnt, r, side, part in arm_points(dg):
            _, _, dist = kd.find(pnt)
            c = dist - r
            if c < worst[side][0]:
                worst[side] = (c, (f, part, tuple(round(x, 3) for x in pnt)))
    return worst


def arm_closeness(frames):
    """mean distance of elbow and wrist from the body midline over the frames, per side (m)"""
    acc = {'L': [0.0, 0.0, 0], 'R': [0.0, 0.0, 0]}
    for f in frames:
        scene.frame_set(f)
        arm_ev = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for side in ('L', 'R'):
            pb_l = arm_ev.pose.bones[nm(side, 'LowerArm')]
            pb_h = arm_ev.pose.bones[nm(side, 'Hand')]
            acc[side][0] += abs(pb_l.head.x)
            acc[side][1] += abs(pb_h.head.x)
            acc[side][2] += 1
    return {sd: (v[0] / v[2], v[1] / v[2]) for sd, v in acc.items()}


if P.ARMGRID:
    rows = []
    frames_g = list(range(0, NF, 2))
    ups, fos, ffs = (14, 17, 20, 23, 26), (-6, 0, 6, 12, 18), (20, 35, 50, 65)
    if P.ARMGRID == 4:                                                # the walk's own elbow model: almost straight back, slight bend forward
        ups, fos, ffs = (16.0, 18.0, 20.0, 22.0, 24.0, 26.0), (6, 10, 14, 18), (22, 28, 34)
    if P.ARMGRID == 2:                                                # fine grid around the interesting region
        ups, fos, ffs = (17.0, 18.5, 20.0, 21.5, 23.0), (8, 11, 14, 17), (35, 45, 55)
    if P.ARMGRID == 3:                                                # moderate elbow bend (a long forearm swinging forward looks like pointing)
        ups, fos, ffs = (20.0, 21.5, 23.0, 24.5, 26.0), (8, 11, 14, 17), (25, 32, 40, 47)
    for up in ups:
        for fo in fos:
            for ff in ffs:
                for sd in ('L', 'R'):
                    P.arm[sd].update(up_out=float(up), fore_out=float(fo), e_max=float(ff))
                build_action(P)
                w = min_clearance(frames_g)
                cl = arm_closeness(frames_g)
                rows.append((up, fo, ff, min(w['L'][0], w['R'][0]), cl['L'][0], cl['L'][1], w['L'][1][1] if w['L'][0] < 0.0 else '-'))
    log('ARM GRID: upper-out forearm-out elbow-fwd | clearance(min L,R) | elbow x | wrist x | limiting part')
    for r in sorted(rows, key=lambda r: (r[3] < -0.010, r[4] + 1.5 * r[5])):
        log('  up %4.1f fore %3d elbow %2d | clear %+.4f | elbow x %.3f wrist x %.3f | %s' % r)
    sys.exit(0)


# The arms should hang as close to the body as the gear allows (far-out arms look masculine). When an arm touches the gear the
# cheapest parameter is changed: more elbow bend (hand moves forward), then the carrying angle of the forearm, last the
# outward angle of the upper arm. Each step tries all three and keeps the one that gains most clearance per "cost".
ARM_STEP = {'e_max': 3.0, 'fore_out': 1.5, 'up_out': 1.5}
ARM_COST = {'e_max': 0.3, 'fore_out': 1.0, 'up_out': 2.5}
if P.arm_spec:                                                        # the elbow bend (16 +- 10 deg) is ordered: only the hang of the arm may change
    ARM_STEP.pop('e_max')
ARM_MAX = {'e_max': 60.0, 'fore_out': 32.0, 'up_out': 32.0}
ARM_WANT = P.ARM_WANT                                                 # wanted clearance to the gear (m)
fit_frames = list(range(0, NF, 2))
for attempt in range(40 if P.ARM_FIT else 0):
    build_action(P)
    w = min_clearance(fit_frames)
    need = [sd for sd in ('L', 'R') if w[sd][0] < ARM_WANT]
    log('arm clearance L %.4f R %.4f | upper out %.1f/%.1f, forearm out %.1f/%.1f, elbow %.1f/%.1f' % (
        w['L'][0], w['R'][0], P.arm['L']['up_out'], P.arm['R']['up_out'], P.arm['L']['fore_out'], P.arm['R']['fore_out'],
        P.arm['L']['e_max'], P.arm['R']['e_max']))
    if not need:
        break
    base = {sd: w[sd][0] for sd in need}
    best = {}
    for key in ARM_STEP:
        saved = {sd: P.arm[sd][key] for sd in need}
        for sd in need:
            if P.arm[sd][key] + ARM_STEP[key] <= ARM_MAX[key]:
                P.arm[sd][key] += ARM_STEP[key]
        build_action(P)
        w2 = min_clearance(fit_frames)
        for sd in need:
            score = (w2[sd][0] - base[sd]) / ARM_COST[key]
            if P.arm[sd][key] == saved[sd]:
                score = -9.0                                          # already at its limit
            if sd not in best or score > best[sd][0]:
                best[sd] = (score, key)
        for sd in need:
            P.arm[sd][key] = saved[sd]
    for sd in need:
        score, key = best[sd]
        P.arm[sd][key] += ARM_STEP[key]
        log('  side', sd, '->', key, '%.1f' % P.arm[sd][key], '(gain per cost %.4f) worst at' % score, w[sd][1])
# final check on every frame; if one frame still touches, keep adding elbow bend / carrying angle
for attempt in range(10):
    build_action(P)
    w = min_clearance(list(range(NF)))
    bad = [sd for sd in ('L', 'R') if w[sd][0] < min(0.002, P.ARM_WANT - 0.002)] if P.ARM_FIT else []
    if not bad:
        break
    for sd in bad:
        P.arm[sd]['fore_out'] += 1.5
        P.arm[sd]['up_out'] += 1.0
        log('  all-frames check: side', sd, 'clearance %.4f, opened a little more' % w[sd][0], w[sd][1])
max_def, frames_data = build_action(P)
w = min_clearance(list(range(NF)))
log('final arm clearance L %.4f R %.4f (all frames); upper arm out %.1f / %.1f, forearm out %.1f / %.1f, elbow bend in the forward swing %.1f / %.1f deg' % (
    w['L'][0], w['R'][0], P.arm['L']['up_out'], P.arm['R']['up_out'], P.arm['L']['fore_out'], P.arm['R']['fore_out'],
    P.arm['L']['e_max'], P.arm['R']['e_max']))

# ------------------------------------------------------------------ 3b. bust and hair: small spring simulation of the body motion
BUST1 = {'L': 'J_Sec_L_Bust1', 'R': 'J_Sec_R_Bust1'}
BUST2 = {'L': 'J_Sec_L_Bust2', 'R': 'J_Sec_R_Bust2'}


def pose_heads(names):
    out = {n: [] for n in names}
    for f in range(NF):
        scene.frame_set(f)
        ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        for n in names:
            out[n].append(ae.pose.bones[n].head.copy())
    return out


def accel(points, axis):
    n = len(points)
    return [(points[(i + 1) % n][axis] - 2.0 * points[i][axis] + points[(i - 1) % n][axis]) * FPS * FPS for i in range(n)]


def periodic_response(acc, w, z, cycles=12, sub=10):
    """x'' + 2 z w x' + w^2 x = -acc(t) for a periodic acceleration (one sample per frame); returns the steady state at the frame times"""
    n = len(acc)
    dt = 1.0 / FPS / sub
    x = v = 0.0
    res = []
    for c in range(cycles):
        res = []
        for i in range(n):
            res.append(x)
            a0, a1 = acc[i], acc[(i + 1) % n]
            for k in range(sub):
                a = a0 + (a1 - a0) * (k / sub)
                v += (-2.0 * z * w * v - w * w * x - a) * dt
                x += v * dt
    return res


def shifted(table, frames_late):
    """periodic table delayed by frames_late (linear interpolation)"""
    n = len(table)
    out = []
    for i in range(n):
        t = i - frames_late
        i0 = int(math.floor(t))
        fr = t - i0
        out.append(table[i0 % n] * (1.0 - fr) + table[(i0 + 1) % n] * fr)
    return out


def periodic_filter(y, w, z):
    """steady state of a periodic signal y (one sample per frame) through the spring  H(s) = w^2 / (s^2 + 2 z w s + w^2)  (via the DFT)"""
    n = len(y)
    T = n / FPS
    Y = [sum(y[i] * cmath.exp(-2j * math.pi * k * i / n) for i in range(n)) for k in range(n)]
    for k in range(n):
        kk = k if k <= n // 2 else k - n
        om = TWO_PI * kk / T
        Y[k] *= (w * w) / (w * w - om * om + 2j * z * w * om)
    return [(sum(Y[k] * cmath.exp(2j * math.pi * k * i / n) for k in range(n)) / n).real for i in range(n)]


def tail_wave_tables(par, psi, zs):
    """spec pass: lateral sway (one wave per cycle, driven by the pelvic rotation / hip sway) and vertical follow-through (two waves per cycle,
    driven by the pelvis height); every joint repeats the wave of the joint before with a phase offset of tail_dphi (negative = it trails),
    so the tail is never rotated as one block.  The lateral wave goes against the pelvic yaw (the tail root does not follow the pelvis
    at once), the vertical one against the vertical speed of the pelvis (the tail droops while the pelvis rises)."""
    n = NF
    ymax = max(abs(v) for v in psi)
    yhat = [v / ymax for v in psi]
    vel = [0.5 * (zs[(k + 1) % n] - zs[(k - 1) % n]) for k in range(n)]
    vmax = max(abs(v) for v in vel)
    vhat = [v / vmax for v in vel]
    out = []
    for i in range(8):
        d_lat = (-par.tail_dphi * i + par.tail_lat_ph) / TWO_PI * n                       # frames of delay (1 wave per cycle)
        d_vert = (-par.tail_dphi * i + par.tail_vert_ph) / (2.0 * TWO_PI) * n              # frames of delay (2 waves per cycle)
        yl = shifted(yhat, d_lat)
        vl = shifted(vhat, d_vert)
        a_lat = par.tail_lat * (0.8 + 0.4 * i / 7.0)
        out.append([(-par.tail_vert * vl[k], -a_lat * yl[k]) for k in range(n)])
    return out


def tail_ear_tables(par):
    """tail: every joint is a spring that follows the one before it, so the sideways wave of the pelvis travels down the tail
    (S-curve) and the vertical bob whips the tip; ears: springy after-bounce of the vertical acceleration (after the down pose)"""
    n = NF
    ps = [i / n for i in range(n)]
    psi = [pelvis_yaw(q, par) for q in ps]                              # world yaw of the tail root (the pelvis), degrees
    zs = [pelvis_z(q, par) for q in ps]
    acc = [(zs[(k + 1) % n] - 2.0 * zs[k] + zs[(k - 1) % n]) * FPS * FPS for k in range(n)]
    if par.spec and par.tail_mode == 'wave':
        tail = tail_wave_tables(par, psi, zs)
        e1 = periodic_response(acc, par.ear_w, par.ear_z)
        e2 = periodic_response(acc, par.ear_w * 1.15, par.ear_z)
        eref = max(1e-9, max(abs(v) for v in e1))
        ears = {}
        for side in ('L', 'R'):
            ears['J_Opt_%s_CatEar1_01' % side] = [(par.ear_g * e1[k] / eref, 0.0, 0.0) for k in range(n)]
            ears['J_Opt_%s_CatEar2_01' % side] = [(0.8 * par.ear_g * e2[k] / eref, 0.0, 0.0) for k in range(n)]
        log('tail: travelling waves, lateral %.1f deg and vertical %.1f deg per joint, phase offset %.2f rad per joint (base to tip)' % (
            par.tail_lat, par.tail_vert, par.tail_dphi))
        return tail, ears
    dyn = []
    w_prev = psi
    zbar = sum(zs) / n
    p_prev = [-0.40 * par.lean - par.pitch_amp * 0.0 + 90.0 * (zs[k] - zbar) + 0.6 * psi[k] * 0.0 for k in range(n)]   # vertical bob of the tail root in degrees
    pit_rel = []
    for i in range(1, 9):
        w_i = par.tail_w * (1.0 - 0.03 * i)
        w_cur = periodic_filter(w_prev, w_i, par.tail_z)
        diff = [w_cur[k] - w_prev[k] for k in range(n)]
        amp = max(1e-9, max(abs(v) for v in diff))
        a_i = par.tail_amp * (0.75 + 0.55 * (i - 1) / 7.0)            # the wave grows a little towards the tip
        yaw_rel = [a_i * v / amp for v in diff]
        w_prev = w_cur
        p_cur = periodic_filter(p_prev, par.tail_pw * (1.0 - 0.03 * i), 0.35)
        pdiff = [p_cur[k] - p_prev[k] for k in range(n)]
        pamp = max(1e-9, max(abs(v) for v in pdiff))
        a_pi = par.tail_pa * (0.7 + 0.6 * (i - 1) / 7.0)
        pit_rel.append([a_pi * v / pamp for v in pdiff])
        p_prev = p_cur
        dyn.append([yaw_rel])
    tail = []
    for i in range(8):
        tail.append([(pit_rel[i][k], dyn[i][0][k]) for k in range(n)])
    e1 = periodic_response(acc, par.ear_w, par.ear_z)
    e2 = periodic_response(acc, par.ear_w * 1.15, par.ear_z)
    eref = max(1e-9, max(abs(v) for v in e1))
    ears = {}
    for side in ('L', 'R'):
        ears['J_Opt_%s_CatEar1_01' % side] = [(par.ear_g * e1[k] / eref, 0.0, 0.0) for k in range(n)]
        ears['J_Opt_%s_CatEar2_01' % side] = [(0.8 * par.ear_g * e2[k] / eref, 0.0, 0.0) for k in range(n)]
    log('tail wave: root yaw %.1f deg peak, joint 1..8 relative yaw peak %s deg; ear springs: after-bounce peak %.1f deg' % (
        max(abs(v) for v in psi), [round(max(abs(t[1]) for t in tail[i]), 1) for i in range(8)], par.ear_g))
    return tail, ears


def secondary_tables(par):
    heads = pose_heads([BUST1['L'], BUST1['R'], H['head']])
    sec = {}
    # bust: vertical drive -> pitch of the chain (tip up / down), sideways drive -> yaw
    ref = 1e-9
    resp = {}
    for side in ('L', 'R'):
        pts = heads[BUST1[side]]
        zr = periodic_response(accel(pts, 2), par.bust_w, par.bust_z)
        xr = periodic_response(accel(pts, 0), par.bust_w, par.bust_z)
        resp[side] = (zr, xr)
        ref = max(ref, max(abs(v) for v in zr))
    log('bust response: vertical amplitude %.1f mm, sideways %.1f mm (before scaling)' % (
        1000.0 * max(max(abs(v) for v in resp[s_][0]) for s_ in resp), 1000.0 * max(max(abs(v) for v in resp[s_][1]) for s_ in resp)))
    for side in ('L', 'R'):
        zr, xr = resp[side]
        zn = [v / ref for v in zr]
        xn = [max(-1.0, min(1.0, v / ref)) for v in xr]
        sec[BUST1[side]] = [(par.bust_d1 * zn[i], 0.0, -par.bust_yaw * xn[i]) for i in range(NF)]
        z2 = shifted(zn, 0.02 * FPS)                                   # the second bone trails a little
        x2 = shifted(xn, 0.02 * FPS)
        sec[BUST2[side]] = [(par.bust_d2 * z2[i], 0.0, -1.3 * par.bust_yaw * x2[i]) for i in range(NF)]
        if side == 'L':
            up_f = max(range(NF), key=lambda i: zn[i])
            dn_f = min(range(NF), key=lambda i: zn[i])
            log('bust bounce: highest at frame %d, lowest at frame %d (heel strikes are at frames 0 and %d)' % (up_f, dn_f, NF // 2))
    # hair: the strands follow the vertical and sideways motion of the head, later joints trail a little more
    hp = heads[H['head']]
    hz = periodic_response(accel(hp, 2), par.hair_w, par.hair_z)
    hx = periodic_response(accel(hp, 0), par.hair_w, par.hair_z)
    href = max(1e-9, max(abs(v) for v in hz))
    hzn = [v / href for v in hz]
    hxn = [max(-1.0, min(1.0, v / href)) for v in hx]
    log('hair response: vertical amplitude %.1f mm, sideways %.1f mm (before scaling)' % (1000.0 * href, 1000.0 * max(abs(v) for v in hx)))
    for name in HAIR:
        m = HAIR_RE.match(name)
        depth, chain = int(m.group(1)), int(m.group(2))
        lag = (depth - 1) * par.hair_lag * FPS
        wdep = 0.55 + 0.45 * (depth - 1) / 4.0
        var = 1.0 + 0.18 * math.sin(1.7 * chain)                       # strands do not move all alike
        zt = shifted(hzn, lag + 0.15 * math.sin(2.3 * chain))
        xt = shifted(hxn, lag + 0.2 * math.cos(1.9 * chain))
        sec[name] = [(par.hair_deg * wdep * var * zt[i], -0.6 * par.hair_deg * wdep * var * xt[i], 0.0) for i in range(NF)]
    return sec


import numpy as np

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


def fk_positions(D, hips_d):
    """world position of every bone head from the world rotation deltas D (same composition as the armature evaluation)"""
    pos = {}
    for name in order:
        b = bones[name]
        if name == H['hips']:                                              # the hips carry the whole body translation (its parent bone, if any, stays at rest)
            pos[name] = HEAD0[name] + hips_d
        elif b.parent is None:
            pos[name] = HEAD0[name].copy()
        else:
            pn = b.parent.name
            pos[name] = pos[pn] + D[pn] @ (HEAD0[name] - HEAD0[pn])
    return pos


def simulate_springs(par):
    """bust, hair and cat ears with the spring bone algorithm of the VRM (UniVRM): per bone a verlet step of the tail point
        next = current + (current - previous) * (1 - drag) + parent rotation * rest axis * stiffness * dt + gravity * dt,
    then the length of the bone is restored and the hair is pushed out of the collider spheres of the VRM.  The parents move with the
    finished walk (pass without secondary motion); the simulation runs several gait cycles and keeps the last one (steady state).
    Sets par.spring_dirs / par.spring_axes and returns a report dict."""
    SUB = par.spring_sub
    dt = 1.0 / (FPS * SUB)
    # ---- chains
    names, parent, depth, axis, length, stiff, drag, hit, coll, kind, rootpar = [], [], [], [], [], [], [], [], [], [], []
    sphere_src = {}
    for g in VRM_SEC['boneGroups']:
        kd = g.get('comment', '')
        if kd not in ('Bust', 'CatEar', 'Hair'):
            continue
        st, dr = g.get('stiffiness', 0.5), g.get('dragForce', 0.4)
        if kd == 'Bust':
            st, dr = par.bust_stiff, par.bust_drag
        elif kd == 'CatEar':
            st, dr = par.ear_stiff, par.ear_drag
        else:
            st, dr = st * par.hair_stiff_mul, par.hair_drag
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
                elif nodes[NODE_OF[bn]].get('children'):                   # the VRM has an end node: the bone vector of the rig
                    off = bones[bn].tail_local - bones[bn].head_local
                else:                                                      # UniVRM: 7 cm further along the direction parent -> bone
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
    axis = np.array(axis)
    length = np.array(length)
    stiff = np.array(stiff)
    drag = np.array(drag)
    hit = np.array(hit)
    coll = np.array(coll)
    parent = np.array(parent)
    depth = np.array(depth)
    roots = [i for i in range(N) if parent[i] < 0]
    root_slot = {i: k for k, i in enumerate(roots)}
    by_depth = [np.array([i for i in range(N) if depth[i] == d]) for d in range(int(depth.max()) + 1)]
    # ---- colliders (VRM node-local offsets -> rig axes: x -> x, y -> z, z -> -y)
    spheres = []
    for ci in sorted(sphere_src):
        cgrp = VRM_SEC['colliderGroups'][ci]
        bn = nodes[cgrp['node']]['name']
        for c_ in cgrp['colliders']:
            o_ = c_['offset']
            spheres.append((bn, Vector((o_['x'], -o_['z'], o_['y'])), c_['radius']))
    M = len(spheres)
    sph_r = np.array([r_ for (_, _, r_) in spheres])
    # ---- the moving parents: root joints, parent rotations and collider centres at SUB samples per frame
    T = NF * SUB
    root_pos = np.zeros((T, len(roots), 3))
    root_R = np.zeros((T, len(roots), 3, 3))
    sph_c = np.zeros((T, M, 3))
    saved = (par.spring_dirs, par.spring_axes)
    par.spring_dirs, par.spring_axes = None, None
    for k in range(T):
        Q_, hl_, D_, dg_, hd_ = compute_pose(k / SUB, par)
        pos_ = fk_positions(D_, hd_)
        for i in roots:
            root_pos[k, root_slot[i]] = np.array(pos_[names[i]])
            root_R[k, root_slot[i]] = np.array(D_[rootpar[i]].to_matrix())
        for j, (bn, off, r_) in enumerate(spheres):
            sph_c[k, j] = np.array(pos_[bn] + D_[bn] @ off)
    par.spring_dirs, par.spring_axes = saved
    if par.spring_debug:
        for k in (0, 6, 12, 18):
            Q_, hl_, D_, dg_, hd_ = compute_pose(k / SUB, par)
            pos_ = fk_positions(D_, hd_)
            log('debug sample %d: head pos %s, D head %s, hair root pos %s, hips_d %s' % (k, tuple(round(1000 * v, 1) for v in pos_[H['head']]), tuple(round(v, 4) for v in D_[H['head']]), tuple(round(1000 * v, 1) for v in pos_['J_Sec_Hair1_01']), tuple(round(1000 * v, 1) for v in hd_)))
    v_world = par.SPEED if par.spring_world else 0.0
    acc_ = (np.roll(root_pos, -1, axis=0) - 2.0 * root_pos + np.roll(root_pos, 1, axis=0)) / (dt * dt)
    ri = [k for k, i in enumerate(roots) if kind[i] == 'Hair']
    rb = [k for k, i in enumerate(roots) if kind[i] == 'Bust']
    if par.spring_debug:
        r0 = ri[0]
        log('springs: first hair root position per sample (mm): ' + ' | '.join('%d:(%.1f,%.1f,%.1f)' % (k, *(1000.0 * root_pos[k, r0])) for k in range(0, T, 3)))
    log('springs: root parents: ' + ', '.join(sorted(set('%s<-%s' % (kind[i], rootpar[i]) for i in roots))))
    log('springs: acceleration of the hair roots (head) max x %.2f y %.2f z %.2f m/s2; bust roots x %.2f y %.2f z %.2f m/s2' % (
        *np.abs(acc_[:, ri]).max(axis=(0, 1)), *np.abs(acc_[:, rb]).max(axis=(0, 1))))
    ydir = np.array([0.0, 1.0, 0.0])
    # ---- state: tails at rest on the first sample
    cur = np.zeros((N, 3))
    R_new = np.zeros((N, 3, 3))
    for d_idx in by_depth:
        for i in d_idx:
            if parent[i] < 0:
                head, Rp = root_pos[0, root_slot[i]], root_R[0, root_slot[i]]
            else:
                head, Rp = cur[parent[i]], R_new[parent[i]]
            cur[i] = head + Rp @ axis[i] * length[i]
            R_new[i] = Rp
    prev = cur.copy()
    if par.spring_debug == 2:                                                  # which axis mapping of the collider offsets keeps the rest hair outside the spheres?
        for label, mp in (('x,-z,y', lambda o: Vector((o[0], -o[2], o[1]))), ('x,z,y', lambda o: Vector((o[0], o[2], o[1]))),
                          ('-x,-z,y', lambda o: Vector((-o[0], -o[2], o[1]))), ('-x,z,y', lambda o: Vector((-o[0], o[2], o[1]))),
                          ('x,y,z', lambda o: Vector((o[0], o[1], o[2]))), ('x,-y,z', lambda o: Vector((o[0], -o[1], o[2])))):
            pen_n, pen_sum, pen_max = 0, 0.0, 0.0
            pos0 = fk_positions({n_: Quaternion() for n_ in order}, Vector())
            # recompute spheres with this mapping
            sph2 = []
            for ci in sorted(sphere_src):
                cgrp = VRM_SEC['colliderGroups'][ci]
                for c_ in cgrp['colliders']:
                    o_ = c_['offset']
                    sph2.append((nodes[cgrp['node']]['name'], mp((o_['x'], o_['y'], o_['z'])), c_['radius']))
            for i in range(N):
                if not coll[i]:
                    continue
                tail = np.array(HEAD0[names[i]]) + axis[i] * length[i]
                worst = 0.0
                for (bn, off, r_) in sph2:
                    c_ = np.array(pos0[bn] + off)
                    pen = r_ + hit[i] - np.linalg.norm(tail - c_)
                    worst = max(worst, pen)
                if worst > 0.0:
                    pen_n += 1
                    pen_sum += worst
                    pen_max = max(pen_max, worst)
            log('collider mapping %-8s: %d hair tails start inside a sphere, mean depth %.1f mm, max %.1f mm' % (label, pen_n, 1000.0 * pen_sum / max(pen_n, 1), 1000.0 * pen_max))
    grav = np.array([0.0, 0.0, -par.spring_gravity]) * dt
    rec_dir = np.zeros((NF, N, 3))
    rec_tail = np.zeros((NF, N, 3))
    rec_def = np.zeros((NF, N))
    last_cycle = [None, None]
    for cyc in range(par.spring_cycles):
        for k in range(T):
            t = (cyc * T + k) * dt
            shift = ydir * (v_world * t)
            new_tail = np.zeros((N, 3))
            heads = np.zeros((N, 3))
            axis_w_all = np.zeros((N, 3))
            for d_idx in by_depth:
                if d_idx[0] in root_slot or parent[d_idx[0]] < 0:
                    slots = [root_slot[i] for i in d_idx]
                    head = root_pos[k, slots] + shift
                    Rp = root_R[k, slots]
                else:
                    pi = parent[d_idx]
                    head = new_tail[pi]
                    Rp = R_new[pi]
                a_w = np.einsum('nij,nj->ni', Rp, axis[d_idx])
                cu, pv = cur[d_idx], prev[d_idx]
                nx = cu + (cu - pv) * (1.0 - drag[d_idx])[:, None] + a_w * (stiff[d_idx] * dt)[:, None] + grav
                v_ = nx - head
                nx = head + v_ / np.linalg.norm(v_, axis=1, keepdims=True) * length[d_idx][:, None]
                sel = np.nonzero(coll[d_idx])[0]
                if len(sel) and M and par.spring_coll:
                    for j in range(M):
                        c_ = sph_c[k, j] + shift
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
            if k % SUB == 0 and cyc >= par.spring_cycles - 2:
                f_ = k // SUB
                rec = (cur - heads) / length[:, None]
                if cyc == par.spring_cycles - 2:
                    if last_cycle[0] is None:
                        last_cycle[0] = np.zeros((NF, N, 3))
                    last_cycle[0][f_] = rec
                else:
                    rec_dir[f_] = rec
                    rec_tail[f_] = cur - shift
                    rec_def[f_] = np.degrees(np.arccos(np.clip(np.einsum('ni,ni->n', rec, axis_w_all), -1.0, 1.0)))
    periodic = float(np.degrees(np.arccos(np.clip(np.einsum('fni,fni->fn', rec_dir, last_cycle[0]), -1.0, 1.0))).max())
    par.spring_dirs = {names[i]: [Vector(rec_dir[f_, i]) for f_ in range(NF)] for i in range(N)}
    par.spring_axes = {names[i]: Vector(axis[i]) for i in range(N)}
    rep_ = {'bones': N, 'spheres': M, 'periodic_error_deg': periodic}
    for kd in ('Bust', 'CatEar', 'Hair'):
        sel_ = [i for i in range(N) if kind[i] == kd]
        rep_[kd] = (float(rec_def[:, sel_].max()), float(rec_def[:, sel_].mean())) if sel_ else (0.0, 0.0)
    rep_['tails'] = {names[i]: rec_tail[:, i] for i in range(N)}
    worst_i = sorted(range(N), key=lambda i: -rec_def[:, i].max())[:8]
    log('springs: largest deflections: ' + '; '.join('%s %.0f deg at frame %d (L %.3f, k %.2f, drag %.2f, depth %d)' % (names[i], rec_def[:, i].max(), int(rec_def[:, i].argmax()), length[i], stiff[i], drag[i], depth[i]) for i in worst_i))
    log('springs: %d bones, %d collider spheres, %d cycles of %d steps; deflection from the bone axis (max / mean deg): bust %.1f / %.1f, ears %.1f / %.1f, hair %.1f / %.1f; periodic to %.2f deg' % (
        N, M, par.spring_cycles, T, rep_['Bust'][0], rep_['Bust'][1], rep_['CatEar'][0], rep_['CatEar'][1], rep_['Hair'][0], rep_['Hair'][1], periodic))
    return rep_


if P.sec_on:
    P.sec = None
    P.tail_dyn = None
    P.spring_dirs = None
    build_action(P)
    if P.spec and P.spring_on:
        P.sec = {}
        P.tail_dyn, _ears_unused = tail_ear_tables(P)
        SPRING_REP = simulate_springs(P)
    else:
        P.sec = secondary_tables(P)
        P.tail_dyn, ear_tab = tail_ear_tables(P)
        P.sec.update(ear_tab)
    max_def, frames_data = build_action(P)
    w = min_clearance(list(range(NF)))
    log('with bust and hair motion: arm clearance L %.4f R %.4f' % (w['L'][0], w['R'][0]))

# ------------------------------------------------------------------ 4. tail: keep the idle's compact roll, lift the root a little if the thighs would touch it
TAIL_BONES = ['J_Opt_C_CatTail%d_01' % i for i in range(1, 9)]
obst_bones = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg'], H['leftLowerLeg'], H['rightLowerLeg']}
obst_idx = []
for v in body.data.vertices:
    if not v.groups or not VIS[v.index]:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    n = vg_names.get(g.group, '')
    if n in obst_bones or n.startswith('J_Sec_L_Coat') or n.startswith('J_Sec_R_Coat') or n.startswith('J_Sec_L_Bust') or n.startswith('J_Sec_R_Bust'):
        obst_idx.append(v.index)


tail_idx = []                                                          # vertices of the tail mesh behind the root (joints 3 .. 8)
_tail_groups = set(TAIL_BONES[2:])
for v in body.data.vertices:
    if v.groups:
        g = max(v.groups, key=lambda g: g.weight)
        if vg_names.get(g.group, '') in _tail_groups:
            tail_idx.append(v.index)
log('tail mesh vertices behind the root:', len(tail_idx))


def min_tail_clearance(frames):
    """smallest distance between a vertex of the tail mesh (joints 3 .. 8) and a visible vertex of the body / thighs / coat over the frames"""
    worst, where = 9.0, None
    reach = [0.0, 9.0, -9.0]                                           # farthest behind the hips (m), lowest z, highest z of the tail mesh
    for f in frames:
        scene.frame_set(f)
        dg, co = evaluated_coords()
        for vi in tail_idx:
            reach[0] = max(reach[0], -co[vi].y)
            reach[1] = min(reach[1], co[vi].z)
            reach[2] = max(reach[2], co[vi].z)
        kd = KDTree(len(obst_idx))
        for i, vi in enumerate(obst_idx):
            kd.insert(co[vi], i)
        kd.balance()
        for vi in tail_idx:
            _, _, dist = kd.find(co[vi])
            if dist < worst:
                worst, where = dist, (f, vg_names.get(max(body.data.vertices[vi].groups, key=lambda g: g.weight).group, ''), tuple(round(x, 3) for x in co[vi]))
    min_tail_clearance.reach = reach
    return worst, where


tail_ok = None
for lift in (0.0, 3.0, 6.0, 9.0, 12.0, 16.0, 20.0, 25.0):
    P.tail_lift = lift
    build_action(P)
    worst, where = min_tail_clearance(list(range(0, NF, 2)))
    log('tail lift %4.1f deg -> min distance tail mesh to legs / body %.4f m at %s | tail reaches %.2f m behind the hips, z %.2f .. %.2f m' % (
        lift, worst, where, min_tail_clearance.reach[0], min_tail_clearance.reach[1], min_tail_clearance.reach[2]))
    if worst >= P.TAIL_CLEAR:
        tail_ok = lift
        break
if tail_ok is None:
    P.tail_lift = 25.0
    log('WARNING: tail still closer than 8 mm to the legs with the largest lift, using', P.tail_lift)
max_def, frames_data = build_action(P)
tail_rest = [round(x + (P.tail_lift if i < 2 else 0.0), 2) for i, x in enumerate(P.tail)]
walk_up = tail_rest_up(P)
tail_walk_rest = [round(x + (P.tail_lift if i < 2 else 0.0), 2) for i, x in enumerate(walk_up)]
with open(os.path.join(OUT, 'Yoru_Walk_tail.json'), 'w') as f:
    json.dump({'restPitch': tail_rest, 'lift': P.tail_lift, 'walkRestPitch': tail_walk_rest,
               'walkAbsoluteAngles': [round(a + (P.tail_lift if i < 2 else 0.0), 1) for i, a in enumerate(P.tail_abs)] if (P.spec and P.tail_mode == 'wave') else None}, f)


# ------------------------------------------------------------------ 5. foot contact, floor and sliding check on the real mesh
def pick_vertices(side):
    foot, toe = nm(side, 'Foot'), nm(side, 'Toes')
    heel, tip, ball = None, None, None
    for v in body.data.vertices:
        if not v.groups:
            continue
        g = max(v.groups, key=lambda g: g.weight)
        n = vg_names.get(g.group, '')
        if n == foot and v.co.z < 0.006 and (heel is None or v.co.y < body.data.vertices[heel].co.y):
            heel = v.index
        if n == toe and v.co.z < 0.03 and (tip is None or v.co.y > body.data.vertices[tip].co.y):
            tip = v.index
        if n == toe and v.co.z < 0.006 and (ball is None or v.co.y < body.data.vertices[ball].co.y):
            ball = v.index
    return heel, tip, ball


shoe_idx = {'L': [], 'R': []}
shoe_groups = {side: {nm(side, 'Foot'), nm(side, 'Toes')} for side in ('L', 'R')}
for v in body.data.vertices:
    if not v.groups:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    n = vg_names.get(g.group, '')
    for side in ('L', 'R'):
        if n in shoe_groups[side]:
            shoe_idx[side].append(v.index)
picks = {side: pick_vertices(side) for side in ('L', 'R')}
log('contact vertices (heel, toe tip, ball):', picks)

track = {}
low_z = {'L': [], 'R': []}
for f in range(NF + 1):
    scene.frame_set(f)
    dg, co = evaluated_coords()
    for side in ('L', 'R'):
        for name, vi in zip(('heel', 'tip', 'ball'), picks[side]):
            track.setdefault((side, name), []).append(co[vi].copy())
        low_z[side].append(min(co[vi].z for vi in shoe_idx[side]))

step = VT / NF
report = {}
for side in ('L', 'R'):
    off = 0.0 if side == 'R' else 0.5
    for name, lo, hi in (('heel', 0.005, P.PH_HR - 0.03), ('ball', P.PH_FF + 0.03, P.PH_TO - 0.03), ('tip', P.PH_FF + 0.03, P.PH_TO - 0.03)):
        errs, zs = [], []
        for f in range(NF):
            phi = (f / NF + off) % 1.0
            phi2 = ((f + 1) / NF + off) % 1.0
            if lo <= phi and phi2 <= hi and phi2 > phi:
                a0, a1 = track[(side, name)][f], track[(side, name)][f + 1]
                errs.append((a1.y - a0.y) + (G(phi2) - G(phi)))
                zs.append(a0.z)
        if errs:
            report[(side, name)] = (max(abs(e) for e in errs) * 1000.0, max(zs) * 1000.0, min(zs) * 1000.0, len(errs))
for k, v in report.items():
    log('planted %s %-5s: speed error max %.1f mm per frame (mean frame step %.1f mm, the ground speed wobbles +-%.0f %%), height %.1f .. %.1f mm, %d steps' % (
        k[0], k[1], v[0], step * 1000.0, P.speed_var * 100.0, v[2], v[1], v[3]))
log('lowest shoe vertex over the cycle: L %.1f mm, R %.1f mm (must stay >= -3 mm)' % (min(low_z['L']) * 1000, min(low_z['R']) * 1000))
swing_clear = []
for side in ('L', 'R'):
    off = 0.0 if side == 'R' else 0.5
    for f in range(NF):
        phi = (f / NF + off) % 1.0
        if P.PH_TO + 0.05 < phi < 0.95:
            swing_clear.append(low_z[side][f])
log('swing: lowest shoe point above the floor %.1f mm .. %.1f mm' % (min(swing_clear) * 1000, max(swing_clear) * 1000))

# ------------------------------------------------------------------ 5b. the two legs must never intersect (triangle overlap test per frame)
from mathutils.bvhtree import BVHTree

leg_groups = {'L': {nm('L', 'UpperLeg'), nm('L', 'LowerLeg'), nm('L', 'Foot'), nm('L', 'Toes')},
              'R': {nm('R', 'UpperLeg'), nm('R', 'LowerLeg'), nm('R', 'Foot'), nm('R', 'Toes')}}
vert_leg = {}
for v in body.data.vertices:
    if not v.groups:
        continue
    g = max(v.groups, key=lambda g: g.weight)
    n = vg_names.get(g.group, '')
    for side in ('L', 'R'):
        if n in leg_groups[side]:
            vert_leg[v.index] = side


LEG_OVERLAP_INFO = [None]
def leg_overlap(frames):
    worst = (0, None)
    mind = (9.0, None)
    for f in frames:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        co = [v.co.copy() for v in me.vertices]
        tris = {'L': [], 'R': []}
        inv = invisible_polygons()
        for t in me.loop_triangles:
            if t.polygon_index in inv:
                continue
            sides = {vert_leg.get(vi) for vi in t.vertices}
            if len(sides) == 1 and None not in sides:
                tris[sides.pop()].append(tuple(t.vertices))
        ev.to_mesh_clear()
        trees = {sd: BVHTree.FromPolygons(co, tris[sd]) for sd in ('L', 'R')}
        pairs = trees['L'].overlap(trees['R'])
        if len(pairs) > worst[0]:
            zs_ = [0.5 * (co[tris['L'][ia][0]].z + co[tris['R'][ib][0]].z) for ia, ib in pairs]
            xs_ = [0.5 * (co[tris['L'][ia][0]].x + co[tris['R'][ib][0]].x) for ia, ib in pairs]
            LEG_OVERLAP_INFO[0] = (f, min(zs_), max(zs_), min(xs_), max(xs_))
            worst = (len(pairs), f)
        # closest vertex distance between the two legs below the crotch (z < 0.70)
        kd = KDTree(sum(1 for vi, sd in vert_leg.items() if sd == 'R' and co[vi].z < 0.70))
        k = 0
        for vi, sd in vert_leg.items():
            if sd == 'R' and co[vi].z < 0.70:
                kd.insert(co[vi], vi)
        kd.balance()
        for vi, sd in vert_leg.items():
            if sd == 'L' and co[vi].z < 0.70:
                _, _, dist = kd.find(co[vi])
                if dist < mind[0]:
                    mind = (dist, f)
    return worst, mind


if P.LEGGRID:
    log('LEG GRID: track half width BASE, outward arc CIRC -> overlapping triangle pairs, closest vertices')
    for base_ in (0.020, 0.026, 0.032, 0.038):
        for circ_ in (0.035, 0.055):
            P.BASE, P.CIRC = base_, circ_
            fit_gait()
            build_action(P)
            ov_, mn_ = leg_overlap(list(range(0, NF, 2)))
            log('  BASE %.3f CIRC %.3f -> overlap pairs %3d (frame %s), closest %.1f mm (frame %s) %s' % (base_, circ_, ov_[0], ov_[1], mn_[0] * 1000.0, mn_[1],
                ('overlap at z %.2f..%.2f, x %.3f..%.3f' % LEG_OVERLAP_INFO[0][1:]) if (ov_[0] and LEG_OVERLAP_INFO[0]) else ''))
    sys.exit(0)

w_ov, w_min = leg_overlap(list(range(NF)))
log('legs: overlapping triangle pairs max %d (frame %s), closest vertices of the two legs below z 0.70: %.1f mm (frame %s)' % (
    w_ov[0], w_ov[1], w_min[0] * 1000.0, w_min[1]))

# ------------------------------------------------------------------ 5c. spec report: every ordered number measured on the finished animation
def spec_report():
    """measures the numbers of the order (pelvis, knees, head, spine, arms, tail, feet) on the finished keys; returns a dict and logs it"""
    rep_ = {}
    ang = lambda q, order='XYZ': [math.degrees(a) for a in q.to_euler(order)]
    hip_x, hip_z, head_x, head_top_x = [], [], [], []
    names = {'hips': H['hips'], 'spine': H['spine'], 'chest': H['chest'], 'upperChest': H['upperChest'], 'neck': H['neck'], 'head': H['head']}
    D_all = []
    for f in range(NF):
        Q_, hips_loc_, D_, diag_, hips_d_ = compute_pose(f, P)
        D_all.append(D_)
        hip_x.append(hips_d_.x)
        hip_z.append(hips_d_.z + HEAD0[H['hips']].z)
    knees = {'R': [], 'L': []}
    arm_pitch = {'L': [], 'R': []}
    fore_pitch = {'L': [], 'R': []}
    ankle_x = {'R': [], 'L': []}
    tail_ang = [[] for _ in range(8)]
    for f in range(NF):
        scene.frame_set(f)
        ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        pbs = ae.pose.bones
        head_x.append(pbs[H['head']].head.x)
        head_top_x.append(pbs[H['head']].tail.x)
        for side in ('R', 'L'):
            hp_, kp_, ap_ = pbs[nm(side, 'UpperLeg')].head, pbs[nm(side, 'LowerLeg')].head, pbs[nm(side, 'Foot')].head
            a1_, a2_ = (hp_ - kp_).normalized(), (ap_ - kp_).normalized()
            knees[side].append(180.0 - math.degrees(math.acos(max(-1.0, min(1.0, a1_.dot(a2_))))))
            ankle_x[side].append(ap_.x)
        for side in ('L', 'R'):
            u_ = pbs[nm(side, 'LowerArm')].head - pbs[nm(side, 'UpperArm')].head
            fo_ = pbs[nm(side, 'Hand')].head - pbs[nm(side, 'LowerArm')].head
            arm_pitch[side].append(math.degrees(math.atan2(u_.y, -u_.z)))
            fore_pitch[side].append(math.degrees(math.atan2(fo_.y, -fo_.z)))
        for j in range(8):
            d_ = D_all[f]['J_Opt_C_CatTail%d_01' % (j + 1)] @ Vector((0.0, -1.0, 0.0))
            tail_ang[j].append(math.degrees(math.atan2(d_.z, -d_.y)))
    rep_['pelvis_z_mm'] = (1000.0 * (min(hip_z) - sum(hip_z) / NF), 1000.0 * (max(hip_z) - sum(hip_z) / NF), 1000.0 * (max(hip_z) - min(hip_z)))
    rep_['pelvis_x_mm'] = 1000.0 * max(abs(v) for v in hip_x)
    rep_['head_x_mm'] = (1000.0 * min(head_x), 1000.0 * max(head_x))
    rep_['head_top_x_mm'] = (1000.0 * min(head_top_x), 1000.0 * max(head_top_x))
    eu = {k: [ang(D_all[f][v]) for f in range(NF)] for k, v in names.items()}
    for k in names:
        rep_['%s_rpy_peak' % k] = tuple(max(abs(e[i]) for e in eu[k]) for i in range(3))     # (pitch rx, roll ry, yaw rz) about world X, Y, Z
    chain = ['hips', 'spine', 'chest', 'upperChest']
    for a_, b_ in zip(chain, chain[1:]):
        rel_e = [ang(D_all[f][names[a_]].inverted() @ D_all[f][names[b_]]) for f in range(NF)]
        rep_['%s_vs_%s_rel_roll_yaw' % (b_, a_)] = (max(abs(e[1]) for e in rel_e), max(abs(e[2]) for e in rel_e))

    def ph_(p_):
        return int(round(p_ * NF)) % NF

    rep_['knee_contact'] = knees['R'][0]
    rep_['knee_down'] = knees['R'][ph_(0.10)]
    rep_['knee_loading_peak'] = max(knees['R'][i] for i in range(0, ph_(0.20) + 1))
    rep_['knee_passing'] = knees['R'][ph_(PEAK_P)]
    rep_['knee_mid_stance_min'] = min(knees['R'][i] for i in range(ph_(0.20), ph_(0.42) + 1))
    for side in ('R', 'L'):
        off_ = 0.0 if side == 'R' else 0.5
        pl = [ankle_x[side][f] for f in range(NF) if ((f / NF + off_) % 1.0) < P.PH_TO]
        rep_['planted_ankle_x_mm_%s' % side] = (1000.0 * min(pl), 1000.0 * max(pl))
        fl = [low_z[side][f] for f in range(NF) if P.PH_FF + 0.01 <= ((f / NF + off_) % 1.0) <= P.PH_HR - 0.01]
        st = [low_z[side][f] for f in range(NF) if ((f / NF + off_) % 1.0) < P.PH_TO]
        rep_['sole_height_flat_mm_%s' % side] = (1000.0 * min(fl), 1000.0 * max(fl))
        rep_['sole_height_stance_mm_%s' % side] = (1000.0 * min(st), 1000.0 * max(st))
    for side in ('L', 'R'):
        rep_['upper_arm_pitch_%s' % side] = (min(arm_pitch[side]), max(arm_pitch[side]))
        ef_ = [fore_pitch[side][i] - arm_pitch[side][i] for i in range(NF)]
        rep_['elbow_flexion_%s' % side] = (min(ef_), max(ef_))
        i_up = arm_pitch[side].index(max(arm_pitch[side]))
        i_el = ef_.index(max(ef_))
        rep_['elbow_peak_lag_deg_%s' % side] = ((i_el - i_up) % NF) * 360.0 / NF
    worst_step, worst_name, worst_frame = 0.0, '', 0
    for f in range(NF):
        for k, v in D_all[f].items():
            if k in EXTRA:
                continue
            a_ = math.degrees((D_all[f][k].inverted() @ D_all[(f + 1) % NF][k]).angle)
            if a_ > worst_step:
                worst_step, worst_name, worst_frame = a_, k, f
    rep_['largest_rotation_step_deg'] = worst_step
    rep_['largest_rotation_step_bone'] = '%s (frame %d -> %d)' % (worst_name, worst_frame, (worst_frame + 1) % NF)
    rep_['pelvis_height_step_mm'] = 1000.0 * max(abs(hip_z[(f + 1) % NF] - hip_z[f]) for f in range(NF))
    rep_['tail_angle_mean'] = [sum(a) / NF for a in tail_ang]
    rep_['tail_angle_range'] = [(min(a), max(a)) for a in tail_ang]
    log('SPEC REPORT')
    log('  pelvis height: %.1f .. +%.1f mm around its mean, peak to peak %.1f mm (order: at most 1.5 cm amplitude); sideways shift +-%.1f mm' % (
        rep_['pelvis_z_mm'][0], rep_['pelvis_z_mm'][1], rep_['pelvis_z_mm'][2], rep_['pelvis_x_mm']))
    log('  head bone x: %.1f .. %.1f mm (order: within +-5 mm), head top x %.1f .. %.1f mm' % (
        rep_['head_x_mm'][0], rep_['head_x_mm'][1], rep_['head_top_x_mm'][0], rep_['head_top_x_mm'][1]))
    for k in names:
        log('  %-10s peak world rotation: pitch %.1f  roll %.1f  yaw %.1f deg' % ((k,) + rep_['%s_rpy_peak' % k]))
    for a_, b_ in zip(chain, chain[1:]):
        log('  %-10s against %-10s: roll %.1f deg, yaw %.1f deg (relative)' % ((b_, a_) + rep_['%s_vs_%s_rel_roll_yaw' % (b_, a_)]))
    log('  knee (right leg): contact %.1f, down (10 %%) %.1f, loading peak %.1f, passing %.1f, mid-stance minimum %.1f deg (order: down 12-15, passing 5-8)' % (
        rep_['knee_contact'], rep_['knee_down'], rep_['knee_loading_peak'], rep_['knee_passing'], rep_['knee_mid_stance_min']))
    log('  planted ankle x: R %.1f .. %.1f mm, L %.1f .. %.1f mm (order: +-25 mm)' % (rep_['planted_ankle_x_mm_R'] + rep_['planted_ankle_x_mm_L']))
    log('  sole height foot-flat: R %.1f .. %.1f mm, L %.1f .. %.1f mm | whole stance: R %.1f .. %.1f, L %.1f .. %.1f mm' % (
        rep_['sole_height_flat_mm_R'] + rep_['sole_height_flat_mm_L'] + rep_['sole_height_stance_mm_R'] + rep_['sole_height_stance_mm_L']))
    for side in ('L', 'R'):
        log('  arm %s: upper arm %.1f .. %.1f deg (order: -18 .. +14), elbow flexion %.1f .. %.1f deg (order: 6 .. 26), elbow peak %.0f deg after the upper arm (order: 45)' % (
            (side,) + rep_['upper_arm_pitch_%s' % side] + rep_['elbow_flexion_%s' % side] + (rep_['elbow_peak_lag_deg_%s' % side],)))
    log('  smoothness: largest rotation step of any humanoid bone between two frames %.1f deg (%s), largest pelvis height step %.1f mm per frame' % (
        rep_['largest_rotation_step_deg'], rep_['largest_rotation_step_bone'], rep_['pelvis_height_step_mm']))
    log('  tail segment direction above horizontal (mean, range): ' + ', '.join(
        '%d: %.0f (%.0f..%.0f)' % (j + 1, rep_['tail_angle_mean'][j], rep_['tail_angle_range'][j][0], rep_['tail_angle_range'][j][1]) for j in range(8)))
    return rep_


SPEC_REPORT = spec_report() if P.spec else {}


def spring_check():
    """the child joints of the keyed spring bones must sit where the simulation put the tails (proves the rotation conversion)"""
    worst = 0.0
    for f in (0, 5, 9, 14, 20):
        scene.frame_set(f)
        pbs = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
        for name, tails in SPRING_REP['tails'].items():
            ch = bones[name].children
            if ch and ch[0].name in P.spring_dirs:
                worst = max(worst, (pbs[ch[0].name].head - Vector(tails[f])).length)
    log('springs: keyed bones follow the simulation to %.2f mm (largest difference of the child joints over 5 frames)' % (worst * 1000.0))
    return worst


SPRING_CHECK = spring_check() if (P.spec and P.spring_on and P.spring_dirs) else None

# ------------------------------------------------------------------ 6. outputs
hz = [fd['hips_world_offset'][2] + HEAD0[H['hips']].z for fd in frames_data[:NF]]
hx = [fd['hips_world_offset'][0] for fd in frames_data[:NF]]
summary = {'speed': P.SPEED, 'stride': VT, 'cycle_seconds': T_CYCLE, 'frames': NF, 'steps_per_minute': 120.0 / T_CYCLE,
           'step_length': VT / 2.0, 'pelvis_height_min': min(hz), 'pelvis_height_max': max(hz), 'pelvis_sway': (max(hx) - min(hx)) / 2.0,
           'knee_max': max(max(k[0], k[1]) for k in kn_table), 'ankle_at_heel_strike': P.A_HS, 'arm_hang': {'L': P.arm['L']['up_out'], 'R': P.arm['R']['up_out']},
           'speed_variation': {'amplitude': P.speed_var, 'phase_of_max': P.speed_var_phase, 'mean_speed': P.SPEED,
                               'speed_per_frame': [ground_rate(f_ / NF) * P.SPEED for f_ in range(NF + 1)],
                               'note': 'ground speed under the character in m/s per frame = SPEED * (1 + amplitude * cos(4 pi (phase - phase_of_max))), phase = cycle phase of the right foot (0 = its heel strike)'},
           'tail_lift': P.tail_lift, 'planted_error_mm': {'%s_%s' % k: round(v[0], 2) for k, v in report.items()},
           'spec_report': {k: (list(v) if isinstance(v, tuple) else v) for k, v in SPEC_REPORT.items()},
           'springs': ({k: v for k, v in SPRING_REP.items() if k != 'tails'} if (P.spec and P.spring_on and P.spring_dirs) else None),
           'spring_params': {'bust_stiffness': P.bust_stiff, 'bust_drag': P.bust_drag, 'hair_stiffness_factor': P.hair_stiff_mul, 'hair_drag': P.hair_drag,
                             'ear_stiffness': P.ear_stiff, 'ear_drag': P.ear_drag, 'tail_scale': P.tail_scale}}
with open(os.path.join(OUT, 'Yoru_Walk_gait.json'), 'w') as f:
    json.dump(summary, f, indent=1)
with open(os.path.join(OUT, 'Yoru_Walk_pose.json'), 'w') as f:
    json.dump({'fps': FPS, 'frames': NF + 1, 'loop_seconds': T_CYCLE, 'speed': P.SPEED, 'stride': VT, 'speed_var': P.speed_var, 'speed_var_phase': P.speed_var_phase,
               'note': 'D = world-space rotation delta from the T-pose per humanoid bone (Blender axes: +Y forward, -X = her left)',
               'humanoid_map': H, 'hips_rest': list(HEAD0[H['hips']]), 'data': frames_data}, f)
log('summary', json.dumps(summary))


# ------------------------------------------------------------------ 7. preview scene: ground that runs backwards at the walk speed
def make_floor():
    mat = bpy.data.materials.new('floor')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n_ for n_ in nt.nodes if n_.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    ck = nt.nodes.new('ShaderNodeTexChecker')
    cells = 6.0
    ck.inputs['Scale'].default_value = cells / VT                    # 6 cells per stride -> the pattern repeats exactly every cycle
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
    for f_ in range(NF + 1):                                         # the ground does not move at a constant speed (speed_var): one key per frame
        loc.default_value = (0.0, G(f_ / NF), 0.0)
        loc.keyframe_insert('default_value', index=1, frame=f_)
    ad = mat.node_tree.animation_data
    if ad and ad.action:
        set_linear(ad.action)
        for fc in action_fcurves(ad.action):
            fc.extrapolation = 'LINEAR'
    return fl


try:
    make_floor()
    log('floor with scrolling checker added')
except Exception as e:
    log('floor not added:', repr(e)[:200])
scene.frame_start, scene.frame_end = 0, NF - 1
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Yoru_Walk.blend'))
log('saved', os.path.join(OUT, 'Yoru_Walk.blend'))
log('DONE')
