"""
Yoru - SPRINT LEAN CORRECTION, r6b (2026-10-29, round 2 of the lean correction): copy of build_sprint_r6.py (stays untouched) with three MORE
UPRIGHT variants.  The user saw L20 / L23 / L26 of round 1 and said "her body still leans too much forward" (even L20 is too much).
New variants, named by the measured mean lean hips->neck (sprint_measure.py), see LEAN_VARIANTS below:
  L16 / L12 / L08 : hips->neck 16 / 12 / 8 deg, skull (head_pitch) 8 / 6 / 4 deg = half of the trunk, neck->head line = trunk + 4 deg.
  Same method as r6: pelvis and upper chest scaled down together, the r5 twist axes (twist_conj) so the shoulder rock / turn stay as r5.
  Everything else (legs, feet, bounce, turn, tempo 5.0 m/s / 0.60 s / 36 frames at 60 fps, stance share 0.2222, dip 0.08, tail, hair) as r5.
Run (background Blender; ALWAYS --factory-startup and absolute paths), one process per lean variant, then the merge:
  blender -b --factory-startup --python build_sprint_r6b.py -- <Yoru_V2.glb> <output dir> [build|design|check] LV=<L16|L12|L08> [KEY=VALUE ...]
      -> <output dir>/r6b_parts/Yoru_Sprint_r6_<LV>.blend (action Yoru_Sprint_r6_<LV>), Yoru_Sprint_r6_<LV>_gait.json, _arms.json, _tail.json
  blender -b --factory-startup --python build_sprint_r6b.py -- <Yoru_V2.glb> <output dir> merge
      -> <output dir>/Yoru_Sprint_r6b.blend with the actions Yoru_Sprint_r6_L16, _L12, _L08 (from r6b_parts) plus Yoru_Sprint_r6_L20, _L23, _L26
         and Yoru_Sprint_r5_P2 (appended from <output dir>/Yoru_Sprint_r6.blend, read only) and <output dir>/Yoru_Sprint_r6b_gait.json.
  (LV=L20 / L23 / L26 still rebuild the round-1 variants into r6b_parts if ever needed; the merge takes those from Yoru_Sprint_r6.blend.)
Design mode (LV=..., no keys, a few seconds): prints the HEAD / BODY lines of sprint_measure.py plus the BACK line (lower back hips->upper chest,
upper back upper chest->neck, mean angle against the vertical in the side view).

----- the original description of the run machinery (build_run.py) follows -----

Run gait model (the numbers come from the rig and from physics, nothing is eyeballed on the foot):
  - 5.0 m/s, 36 frames at 60 fps = 0.6 s per cycle = 200 steps / min, step 1.5 m.  Her legs are only 0.743 m: at this speed a foot can be on the
    ground for only 0.13 s, the rest is a flight phase (both feet off the ground, 0.17 s per step), like a sprinter.
  - ONE continuous leg model (class Gait), no switching between solvers.  Every foot has a phase phi in [0,1) (0 = touchdown, right foot at frame 0,
    left foot half a cycle later).
      stance 0 .. PH_TO : she lands on the ball of the foot (toes slightly down); the toe joint stays planted in the ground frame for the whole stance
                          (0.0 mm slip); the heel rises from the touchdown on with a pitch rate that grows smoothly to a steady value (HEEL_DELAY /
                          HEEL_RAMP / TH_TO), so the foot never jumps.
      flight / swing    : the ankle is described by its fore-aft position (quintic Hermite pieces: a smooth stop at a rear extreme T_REAR frames after the
                          toe off, the forward travel, a smooth start from a forward extreme T_FWD frames before the touchdown; at the touchdown the foot
                          moves BACKWARDS against the ground by RHO x the running speed = the clawing back of a sprinter) and by the LENGTH OF THE LEG
                          (pieces again: the leg goes on lengthening a little after the toe off up to the knee KN_EXT, bends to KN_SW, reaches out again
                          before the touchdown), so the knee is shaped directly and the foot never leaves its reach.  The foot pitch is one smooth
                          curve of the whole cycle.  Every piece starts and ends with the position, speed and acceleration of its neighbour: no corner.
  - Pelvis height = the physical curve: a half-sine dip in every stance, an arc in every flight (shares KD / KA of the physical values), smoothed:
    lowest at mid stance, highest in the middle of the flight.  The ankle placement at touchdown (A_HS) is fitted so that the knee has KN_TO degrees of
    flexion at toe off, the height (Z_TD) so that it has KN_TD at touchdown (or that the stance knee peaks at KN_MS); nothing is derived backwards from a knee curve.
  - The ground speed is not constant: it dips by speed_var while a foot is on the ground (slowest at mid stance) and is steady in the flight.
  - Spine: forward lean (hips 6 deg, upper chest 17 deg, built up along the spine), a chest nod twice per cycle that travels up the spine with a lag, the
    chest turns against the pelvis (chest_net_yaw), the head stays on the centre line (head_lock).
  - Head: neck and head cancel about 75 % of the trunk's turn, the rest follows through a moment later (head_yaw +-2 deg, head_nod +-1.5 deg at twice the step rate).
  - Arms: compact and narrow.  The upper arm swings swing_f forward / swing_b back on a rounded triangle wave that is a little quicker forward than back
    (crisp reversals, a low peak speed), the elbow closes to e_fwd in the forward swing and opens to e_back behind with the forearm trailing, the forearms
    point inwards in front of the chest (fore_in) and outwards behind (fore_back = the carrying angle of the elbow).  The hang of the upper arm is fitted
    against the gear per phase of the swing (fit_arm_hang), the shoulder blades glide with the arm.
  - Tail: an aerodynamic arch (tail_abs: +30 deg at the rump, levelling out towards joint 6) with travelling waves, every joint trailing the one before by
    0.65 rad: sideways once per cycle and up / down twice, the amplitude growing from 2 deg at the base to 10 deg at joint 6.
  - Hair, ears: spring bones (VRM algorithm) with a headwind (wind_hair / wind_ear) on top of the motion of the body.
Blender axes for Yoru: +Y forward, her left = -X, up = +Z.
"""
import bpy, sys, math, cmath, json, struct, os, time, re
from mathutils import Vector, Quaternion, Euler, Matrix
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT = argv[0], argv[1]
DESIGN_ONLY = len(argv) > 2 and argv[2] == 'design'
os.makedirs(OUT, exist_ok=True)
LVS_R6 = ('L20', 'L23', 'L26')                                       # round 1 (built by build_sprint_r6.py, read from Yoru_Sprint_r6.blend)
LVS_NEW = ('L16', 'L12', 'L08')                                      # r6b: the more upright variants built here
LVS = LVS_R6 + LVS_NEW                                               # all lean variants (mean lean hips->neck in deg)
LV = next((a_.split('=', 1)[1] for a_ in argv[3:] if a_.startswith('LV=')), 'L12')
PARTS_DIR = os.path.join(OUT, 'r6b_parts')                           # r6b: one build per lean variant lands here (r6_parts stays untouched)
os.makedirs(PARTS_DIR, exist_ok=True)
GAIT_SAME = ('speed', 'stride', 'cycle_seconds', 'frames', 'steps_per_minute', 'step_length', 'speed_variation')   # must equal r5


def merge_r6b():
    """r6b: one .blend with the three new lean variants (r6b_parts) plus L20 / L23 / L26 and r5 P2 (appended from Yoru_Sprint_r6.blend, read
    only) and the gait JSON (r5 numbers + the per-variant values; the round-1 values come from Yoru_Sprint_r6_gait.json)"""
    part = lambda lv: os.path.join(PARTS_DIR, 'Yoru_Sprint_r6_%s.blend' % lv)
    r6_blend = os.path.join(OUT, 'Yoru_Sprint_r6.blend')
    save_ = os.path.join(OUT, 'Yoru_Sprint_r6b.blend')
    assert os.path.normcase(os.path.abspath(save_)) != os.path.normcase(os.path.abspath(r6_blend))
    bpy.ops.wm.open_mainfile(filepath=part(LVS_NEW[0]))
    for lv in LVS_NEW[1:]:
        with bpy.data.libraries.load(part(lv), link=False) as (src_, dst_):
            dst_.actions = [a_ for a_ in src_.actions if a_ == 'Yoru_Sprint_r6_' + lv]
    with bpy.data.libraries.load(r6_blend, link=False) as (src_, dst_):
        dst_.actions = [a_ for a_ in src_.actions if a_ in ['Yoru_Sprint_r6_' + lv for lv in LVS_R6] + ['Yoru_Sprint_r5_P2']]
    names = ['Yoru_Sprint_r6_' + lv for lv in LVS_NEW + LVS_R6] + ['Yoru_Sprint_r5_P2']
    for n_ in names:
        bpy.data.actions[n_].use_fake_user = True
    arm_ = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    arm_.animation_data.action = bpy.data.actions['Yoru_Sprint_r6_L12']
    if getattr(arm_.animation_data, 'action_slot', None) is None and len(bpy.data.actions['Yoru_Sprint_r6_L12'].slots):
        arm_.animation_data.action_slot = bpy.data.actions['Yoru_Sprint_r6_L12'].slots[0]
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=save_)
    print('MERGE saved', save_, 'actions:', sorted(a_.name for a_ in bpy.data.actions if a_.name.startswith('Yoru_Sprint_r')), flush=True)
    r5g = json.load(open(os.path.join(OUT, 'Yoru_Sprint_r5_gait.json')))
    r6g = json.load(open(os.path.join(OUT, 'Yoru_Sprint_r6_gait.json')))
    gs = {lv: json.load(open(os.path.join(PARTS_DIR, 'Yoru_Sprint_r6_%s_gait.json' % lv))) for lv in LVS_NEW}
    for lv, g_ in gs.items():
        diff_ = [k_ for k_ in GAIT_SAME if json.dumps(g_[k_], sort_keys=True) != json.dumps(r5g[k_], sort_keys=True)]
        print('MERGE gait %s: keys that differ from r5 (must be none): %s' % (lv, diff_), flush=True)
    out_ = {k_: r5g[k_] for k_ in GAIT_SAME}
    for k_ in r6g:                                                   # the keys that were the same in every round-1 variant ...
        if k_ not in out_ and k_ not in ('variants', 'lean_variants', 'note'):
            vals_ = [json.dumps(gs[lv].get(k_), sort_keys=True) for lv in LVS_NEW]
            if all(v_ == json.dumps(r6g[k_], sort_keys=True) for v_ in vals_):
                out_[k_] = r6g[k_]                                   # ... and in every new one stay at the top
    out_['variants'] = {lv: 'Yoru_Sprint_r6_' + lv for lv in LVS}
    out_['variants']['R5'] = 'Yoru_Sprint_r5_P2'
    out_['lean_variants'] = {lv: dict(r6g['lean_variants'][lv]) for lv in LVS_R6}
    for lv in LVS_R6:                                                # a round-1 top key that differs in a new variant moves into every variant
        for k_ in r6g:
            if k_ not in out_ and k_ not in ('variants', 'lean_variants', 'note'):
                out_['lean_variants'][lv][k_] = r6g[k_]
    for lv in LVS_NEW:
        out_['lean_variants'][lv] = {k_: gs[lv][k_] for k_ in gs[lv] if (k_ not in out_ and k_ not in ('variants',)) or k_ == 'trunk'}
    out_['note'] = ('r6b lean correction, round 2: speed, stride, cycle, frames, stance share and dip are the r5 numbers; the values that depend on '
                    'the lean (trunk, fitted leg placement, pelvis height, springs) are listed per variant under lean_variants (L20 / L23 / L26 from '
                    'Yoru_Sprint_r6_gait.json, L16 / L12 / L08 built by build_sprint_r6b.py)')
    with open(os.path.join(OUT, 'Yoru_Sprint_r6b_gait.json'), 'w') as f_:
        json.dump(out_, f_, indent=1)
    print('MERGE gait written; top keys:', sorted(out_.keys()), '; per-variant keys:', sorted(out_['lean_variants'][LVS_NEW[0]].keys()), flush=True)


if len(argv) > 2 and argv[2] == 'merge':
    merge_r6b()
    sys.exit(0)

FPS = 60
TWO_PI = 2.0 * math.pi
T0 = time.time()


def log(*a):
    print('[run %5.1fs]' % (time.time() - T0), *a, flush=True)


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
    NF = 36                  # frames per gait cycle (two steps); key NF == key 0.  26 = the first, slower walk (1.15 m/s, 138 steps/min)
    SPEED = 5.0             # walk speed in m/s  (stride length = SPEED * NF / FPS), the mean over a cycle.  The user found 1.15 too slow;
                             # with her 74 cm legs 1.50 m/s at 171 steps/min (step 0.525 m) keeps the knees / pelvis of the slow walk
                             # (sweep: Blender/work/speed_sweep/sweep.txt; 1.6 and more needs bent knees of 25 deg and more)
    speed_var = 0.08         # the ground speed wobbles by +- this share twice per cycle (a real walker slows down a little over every stance leg); 0 = constant
    speed_var_phase = 0.0    # cycle phase of the fastest ground speed = where the pelvis is lowest (right heel strike at 0, measured: the pelvis wave has its minimum at 0.00); the second peak is at +0.5
    PH_TO = 0.2222           # toe off (share of the cycle): 8 frames of ground contact per foot at 36 frames
    TH_TO = 55.57             # foot pitch at toe off (deg, toes down); the ankle joint then has about -20 deg (plantar flexion)
    HEEL_DELAY = 0.9042         # frames after the touchdown before the heel starts to rise
    HEEL_RAMP = 1.601          # frames over which the heel rise speeds up (quintic smooth step) to its steady pitch rate
    SW_STOP_T = 4.698          # frames after the toe off until the foot has stopped turning toes-down (the heel whips up, speed fades smoothly)
    TH_SW_MID = 62.0         # pitch of the foot (deg, toes down) at SW_MID_U of the swing: it comes up while the shank swings forward
    SW_MID_U = 0.5698          # ... this share of the swing (about where the knee is bent most)
    TAU_RELAX = 20.1         # toe bone bend (deg) of the relaxed foot in the swing (in the stance the toes stay flat on the ground) ...
    TAU_U = 0.6174             # ... reached at this share of the swing
    T_REAR = 4.482             # swing: frames after the toe off until the foot has come to rest at its rear extreme (the heel whips up behind)
    T_FWD = 2.932              # swing: frames before the touchdown at which the foot is at its forward extreme
    P_FWD = 1.669              # swing: time warp of the forward travel between the two extremes (above 1: the foot comes forward later, a lower knee lift)
    KN_EXT = 21.7            # swing: knee flexion of the longest leg after the toe off (deg): the push-off extension
    KN_SW = 87.01            # swing: knee flexion at the most bent point (deg) ...
    SW_FLEX_U = 0.5336         # ... reached at this share of the swing
    LATE_EXT = 4.147          # swing: before the touchdown the leg reaches out this many degrees of knee flexion straighter than the touchdown knee
    BASE = 0.05             # ankle distance from the midline (m); the hip joints are 0.0751; narrow = cat-like track
    TOE_OUT = 0.0           # toes point outward by this angle (deg), negative = slightly towards the midline
    KNEE_OUT = 0.0           # the knees point outward by this angle while the feet point nearly straight (keeps the thighs apart)
    CIRC = 0.02             # the swing foot moves out by this much at mid swing and lands back on the narrow track (m)
    SW_YAW = 0.5             # the swing leg turns with the pelvis by this share
    A_HS = 0.27              # ankle y relative to the hip joint at heel strike (fitted)
    # --- pelvis
    z_peak = 0.84            # hips bone height at mid stance (fitted); rest = 0.8955
    bob = 0.055              # peak to peak height change (m)
    sway = 0.018             # sideways shift over the stance foot (m)
    yaw_p = 8.0              # pelvis yaw (deg)
    roll_p = 5.0             # pelvis drop on the swing side (deg)
    yaw_c = 5.0             # chest counter rotation (deg, world)
    lean = 17.0              # forward lean of the upper chest (deg, world pitch = hips + spine + chest + upper chest)
    hips_lean = 6.0          # ... of which the hips carry this much (deg, world pitch of the hips)
    lean_cum = (0.36, 0.68, 1.0)      # share of the rest of the lean (lean - hips_lean) reached at spine, chest and upper chest
    pitch_amp = 0.6          # pelvis nod with the steps (deg)
    lean_dyn = 2.3           # chest nod: the upper chest dives into every down pose (twice per cycle); 2.3 gives a measured world pitch wave of 2.0 deg (the roll / yaw of the pelvis take a bit of it)
    nod_share = (0.15, 0.45, 0.72, 1.0)   # share of that nod at hips, spine, chest, upper chest (with the lag sp_lag every spine joint nods about 0.5 deg)
    down_extra = 0.0       # the hips sink this much deeper at the down pose than the reach fit needs (weight is caught)
    down_phase = None        # cycle phase of the down pose after heel strike
    down_w = 0.05            # width of the dip (fraction of the cycle)
    rebound = 0.0           # the pelvis springs back above its curve after the dip by this share of the dip (springy step)
    rebound_dt = 0.12        # ... this far after the dip (fraction of the cycle)
    surge = 0.0            # forward / backward pelvis surge (m)
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
    # --- arms (stage 3: compact, narrow, crisp).  The upper arm swings from the shoulder on a rounded triangle wave (crisp reversals and a lower peak
    # speed than a sine of the same size), a little quicker forward than back; the elbow closes on the forward swing and opens loosely behind, the
    # forearm trailing the upper arm; in front of the chest the forearms point inwards; how far the elbow stands out is fitted against the gear per
    # phase of the swing (fit_arm_hang), so the arm is as narrow as the gear allows at every moment
    ARM_FIT = 1              # 0 = take the hang as given (hang_in / hang_out), 1 = fit it against the gear
    ARM_WANT = -0.012        # wanted arm clearance to the gear (m); slightly negative lets the sleeve touch the gear
    LEGGRID = 0              # 1 = only print a table of track widths and swing arcs against leg intersections and stop
    swing_f = 16.0           # forward swing of the upper arm from the plumb line (deg): the trunk itself leans 17 deg, so the elbow stays at the ribs (a swing of +38 pushes it 13 cm ahead and the arm out like a punch)
    swing_b = 38.0           # backward swing (deg): the arm drives back behind the hip
    swing_tri = 0.09         # wave shape of the swing: 0 = sine, 1/9 = triangle wave (even speed, quick turns); the peak speed is (1 - 3 c) / (1 + c) of the sine's
    swing_skew = 0.08        # the forward drive is this share quicker than the way back (crisp, asymmetric timing)
    e_fwd = 100.0            # elbow flexion in the forward swing (deg): a bent arm, the fist stays below the chin at the chest
    e_back = 66.0            # ... and in the back swing: the forearm hangs open (less than 66 raises the speed of forearm and hand over 8 deg / frame: with the swing above the forearm turns p-p 88 deg)
    lag_e = 0.10             # the elbow closes this part of a cycle after the upper arm is furthest forward (the forearm trails)
    hang_in = 8.0            # outward angle of the upper arm in the frontal plane at the forward swing (deg), start value and lower limit of the fit
    hang_out = 22.0          # ... at the back swing, start value of the fit (the elbow passes the gear at the waist)
    hang_max = 34.0          # the fit never opens the arm further than this
    hang_rate = 1.2          # the hang changes by at most this many degrees per frame (smooth envelope over the fitted minimum)
    hang_add = 3.0           # the finished hang is opened this many degrees further (the user wanted the arms a little further out)
    hang_tab = None          # filled by the build: outward angle of the upper arm (deg) per frame of the arm phase (0 = furthest forward)
    fore_in = 11.0           # the forearm points inwards by this angle (deg) at the forward swing (convergence in front of the chest)
    fore_back = 20.0         # ... and outwards by this angle at the back swing (the carrying angle of the elbow: the hand passes outside the hip gear while the upper arm stays close)
    wr_base = 2.0            # wrist flexion (deg)
    wr_amp = 2.0             # wrist flick (deg)
    lag_w = 0.17             # the hand trails the forearm by this part of a cycle
    pro = 9.0                # shoulder blade: the shoulder joint moves forward with the arm and back with it (deg of the collar bone)
    # hands (the user found them stiff): relaxed curl that grows from index to little finger, a travelling curl wave with an overlapping delay per
    # finger and per joint, a little spread, thumb that moves, wrist flick + sideways deviation + palm turn that lag behind the arm swing
    fing_dyn = (5.0, 7.0, 6.0)          # curl wave per phalanx (deg)
    fing_lag = 0.30                      # cycle phase at which the fingers are most curled (0 = arm furthest forward)
    fing_lag_f = 0.020                   # extra delay per finger (index first, little finger last), fraction of a cycle
    fing_lag_p = 0.014                   # extra delay per phalanx
    fing_spread = (4.0, 1.5, -1.5, -5.0)  # spread of the knuckle joints (deg): index forward, little finger backward
    thumb_dyn = 6.0                      # thumb swing (deg)
    wr_dev = 3.0                         # sideways wrist deviation (deg)
    wr_dev_lag = 0.22                    # ... its delay (fraction of a cycle)
    palm_turn = 0.15                     # palm sways forward / back by about atan(this) degrees
    palm_lag = 0.16
    thumb_add = 30.0         # the thumb is brought alongside the hand (deg)
    # relaxed, ready hand: curls (proximal, intermediate, distal) per finger; the standard VRoid hand is spread and straight
    fingers = {'Index': (35.0, 48.0, 28.0), 'Middle': (45.0, 58.0, 34.0), 'Ring': (55.0, 66.0, 38.0), 'Little': (62.0, 72.0, 42.0)}
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
    tail_mode = 'wave'       # 'wave' = spec: rest curve (down at the base, up at the tip) + travelling sine waves; 'spring' = earlier spring cascade
    tail_abs = [30.0, 27.0, 22.0, 15.0, 8.0, 2.0, 2.0, 2.0]   # stage 3 rest curve: an aerodynamic arch, rising +30 deg from the rump and levelling out towards joint 6; the
                             # zero-length joints 7 and 8 carry the tip on in the same direction.  Direction of each joint above the horizontal (deg, world, side view)
    tail_dphi = -0.65        # phase offset per joint (rad), base to tip, for both waves (the tip trails the base)
    tail_lat = (2.0, 10.0)   # lateral wave (once per cycle): amplitude per joint (deg) at the base joint and at joint 6, linear in between, none beyond
    tail_lat_ph = 0.0        # phase of the lateral wave at the base (rad), relative to the pelvic yaw
    tail_vert = (2.0, 10.0)  # vertical wave (twice per cycle, one per step): amplitude per joint (deg), same progression
    tail_vert_ph = 0.0       # phase of the vertical wave at the base (rad), relative to the pelvis height
    ear_on = 1
    # --- spring bones: bust, hair and cat ears are simulated with the algorithm of the VRM / UniVRM spring bones (60 steps per second, the character
    # walks through the world at SPEED so the air drag acts) and written as bone rotations; the values are the ones to set in Unity afterwards
    spring_on = 1
    spring_sub = 1           # simulation steps per animation frame (2 at 30 fps = the 60 Hz of the game)
    spring_cycles = 10       # the simulation runs this many gait cycles, the last one is kept (periodic steady state)
    spring_world = 0         # 1 = the character moves through the world (headwind / trailing), 0 = standing on the spot
    spring_debug = 0
    spring_coll = 1          # 1 = the hair is pushed out of the collider spheres of the VRM
    bust_stiff = 0.80        # VRoid default 0.74: lower = softer, slower wobble that overshoots (jelly)
    bust_drag = 0.05         # VRoid default 0.05: low = it rings on for several swings after every step
    hair_stiff_mul = 1.4     # factor on the stiffness of every strand (the VRM has 0.4 .. 1.0 per strand)
    hair_drag = 0.40         # VRoid default 0.4: calm enough that the strands do not chatter at the impacts (0.28 gave 31 strands over 8 deg / frame, 0.40 only 23)
    ear_stiff = 1.6          # VRoid default 1.5: softer ears tilt back in the wind and flick at the steps
    ear_drag = 0.14          # VRoid default 0.05 (rings): more damping makes them flutter less
    spring_gravity = 0.0     # extra gravity power on all simulated bones (VRM: 0)
    spring_smooth = 1        # [1 2 1] / 4 smoothing passes over the frames of the simulated directions (0 = raw simulation)
    wind_hair = 0.19         # headwind on the hair strands: a steady push backwards (same unit as the stiffness, m/s), so the hair streams out behind her
    wind_ear = 0.30          # ... on the cat ears
    wind_lift = 0.25         # ... with this share of it pointing upwards (the airflow over the head lifts the strands)
    spring_dirs = None       # filled by the build: bone -> list of world directions of the bone axis per frame
    spring_axes = None       # bone -> rest direction of its axis (world)
    # --- RUN (sprint) model: ball of the foot first, flight phase, physical pelvis curve (see the docstring)
    TH_TD = -6.0             # foot pitch at touchdown (deg, negative = toes down: she lands on the ball of the foot, the heel almost touches)
    RHO = 0.0               # at touchdown the foot moves backwards against the ground by this share of the running speed (clawing = less braking)
    Z_TD = 0.85              # hips bone height at touchdown / toe off (m), fitted by fit_run()
    KD = 0.2478                # share of the physical dip of the hips in the stance  (g * t_flight * t_stance / (2 pi))
    KA = 1.0                # share of the physical rise of the hips in the flight (g * t_flight^2 / 8)
    ZSMOOTH = 0.012          # the pelvis curve is smoothed over this share of a cycle (no corner at touchdown / toe off)
    KN_TD = 27.42             # knee flexion at touchdown (deg)
    KN_TO = 25.72             # knee flexion at toe off (deg): sets how far ahead of the hip the foot lands (A_HS is fitted for it when A_FIT = 1)
    KN_MS = 0.0              # > 0: fit Z_TD so that the knee flexion peaks at this value in the stance (instead of KN_TD at the touchdown)
    A_FIT = 1                # 1 = fit A_HS (ankle ahead of the hip at touchdown) for KN_TO, 0 = keep the given A_HS
    chest_net_yaw = 8.0      # the chest turns against the pelvis: its own world yaw peaks at this many degrees (opposite to the pelvis yaw)
    neck_pitch = 6.0         # neck and head lean forward a little with the body (world pitch, deg) instead of being kept exactly level
    head_pitch = 9.0         # (the gaze stays ahead while the trunk leans 17 deg)
    # --- head stabilisation (stage 3): neck and head cancel 80..85 % of the trunk's motion, the rest follows through a moment later
    head_yaw = 0.25          # share of the upper chest's yaw that the head keeps (0.25 of 8 deg = +-2.0 deg)
    head_roll = 0.15         # share of the upper chest's roll that the head keeps
    head_nod = 1.5           # the head dips by this many degrees into every down pose (twice per cycle)
    head_lag = 0.04          # the head trails the upper chest by this part of a cycle


# ------------------------------------------------------------------ SPRINT r1: tactical trunk (calmer than the run), same legs, tempo and stance share
for _k, _v in dict(BASE=0.038, CIRC=0.025,            # narrower track (run: 0.05 / 0.02)
                   yaw_p=6.0, roll_p=3.5, sway=0.012,  # calmer pelvis (run: 8 / 5 / 0.018)
                   lean=20.0, hips_lean=7.0,           # 20 deg forward lean at the upper chest (run: 17 / 6)
                   pitch_amp=0.5, lean_dyn=1.6,        # smaller chest nod (run: 0.6 / 2.3)
                   KD=0.20, KA=0.60,                   # smaller stance dip and flight rise of the pelvis (run: 0.2478 / 1.0)
                   chest_net_yaw=4.0,                  # the compact arms need less shoulder counter-turn (run: 8)
                   neck_pitch=10.0, head_pitch=6.0, head_yaw=0.2, head_nod=1.0,   # head calm, gaze ahead
                   ARM_FIT=0).items():
    setattr(P, _k, _v)
P.tail_lat = (1.0, 3.5)                                              # calmer tail waves (run: 2..10 deg), no wagging
P.tail_vert = (1.5, 6.0)
P.tail_counter = 0.8             # the tail root turns against 80 % of the pelvis yaw (seen from behind it does not swing from side to side)
P.wind_hair = 0.14               # headwind on the hair (run: 0.19); the guide wants a weak hair wind
P.variant = 'A'
# ---- SPRINT r3: energetic trunk and legs (targets of the main agent's critique, measured with sprint_measure.py)
for _k, _v in dict(lean=39.0, hips_lean=14.5,                  # hips->neck about 24 deg (the rest pose has the neck 5 deg behind the hips)
                   yaw_p=8.5, roll_p=5.0, sway=0.012,           # pelvis turn and drop
                   chest_net_yaw=10.5, lean_dyn=3.0, pitch_amp=0.6,   # the shoulders turn against the pelvis, the chest nods with every step
                   KA=1.30, KD=0.36,                            # pelvis bounce 5..6 cm
                   KN_SW=108.0, KN_TO=21.5,                     # r4: knee 21.5 at toe off (r3 22); 20 gives 15.3, 17..18 up to 15.7 deg/frame
                   # at the thigh (3d step at the toe off), the stance share is fixed; the heel already rises 0.9 frames after the touchdown
                                       # heel to the buttocks, fuller push-off (run: 87 / 25.7; 16 at toe off gave 16 deg/frame)
                   SW_FLEX_U=0.45, P_FWD=1.4, T_REAR=3.0,       # the knee folds while the foot is still behind (heel to the buttocks, no high knee)
                   swing_skew=0.15,                             # the forward drive of the arm is quicker (a snap), the way back softer
                   head_yaw=0.25, head_roll=0.2, head_nod=1.2, neck_pitch=14.0, head_pitch=8.0).items():
    setattr(P, _k, _v)
for _k, _v in dict(lean=44.0, hips_lean=18.0,                  # r5: hips->neck about 28 deg, more forward tilt of the pelvis
                   neck_pitch=26.0, head_pitch=16.0, head_nod=3.0, head_lag=0.04,   # r5: the skull tips forward with the body, +-3 deg, trails 1.4 frames
                   hair_drag=0.32, hair_stiff_mul=1.15, spring_smooth=2).items():   # r5: softer hair (r4 0.40 / 1.4 / 1); 0.22 / 0.9 chattered (32 deg/frame)
    setattr(P, _k, _v)
# ---- r6: LESS FORWARD LEAN (the user, in the game: "the body is leaned down too far").  Only these four numbers change against r5
# (r5: lean 44 / hips_lean 18 / neck_pitch 26 / head_pitch 16 = hips->neck 28.3, neck->head 33, skull 16).  Pelvis and upper chest are scaled
# down by the same factor (the trunk keeps the r5 shape, the back stays rounded); neck->head = trunk + 4 deg; skull about half of the trunk.
# head_nod 3 / head_lag 0.04 and the chest nod (lean_dyn, pitch_amp) stay as r5.  Values fitted with the design mode against sprint_measure.py.
# Shoulder motion kept as r5 (the user liked the back view: r4 shoulder roll 14.0, r5 16.7 deg p2p).  Without a fix the same chest twist turns
# about a more upright spine axis: seen from behind the shoulders rocked less (L20: shoulder roll p2p 11.0 instead of 16.7 with the twist trimmed
# to keep the top view, about 11.8 untrimmed) and seen from above they turned more (29.9 instead of 28.7).  Fix (twist_conj): every spine joint and
# the shoulder blades twist / bend sideways about the r5 axes (twist_ref = r5 lean, r5 hips_lean; twist_clav = 1).  With the head lock off this
# reproduces r5 exactly (yaw 26.12 / roll 22.64 p2p in both); the head lock (60 %, as r5) then takes part of the rock back because the head sits
# off the r5 axis, so the axis is tilted 1.5 x as far (twist_gain) and the twist trimmed (chest_net_yaw) until the measured shoulder yaw and roll
# equal r5 (28.67 / 16.70).  The head sways a little more sideways: 2.9 / 2.6 / 2.3 cm p2p (r5 2.1).
# ---- r6b (round 2): "her body still leans too much forward" (about L20).  Three more upright variants, same method (start values extrapolated
# from L20..L26 per measured degree: lean 1.31, hips_lean 0.53, neck_pitch 1.0; they hit the targets directly: hips->neck 15.96 / 11.96 / 7.96,
# neck->head 19.99 / 15.99 / 11.99, skull 8.0 / 6.0 / 4.0).  The shoulder motion was then fitted to r5 with build_sprint_r6b_fit.py (design mode):
# shoulder yaw p2p 28.67, roll p2p 16.70 AND the sideways head sway 2.08 cm p2p (with the head lock of r5, 0.6, the head swayed 3.3 / 3.6 / 4.0 cm
# and the upper back bent sideways 4.8 / 6.2 / 7.7 deg p2p, r5 2.2).  Unknowns chest_net_yaw, twist_gain, head_lock_share.  Note: on an upright
# trunk r5's shoulder rock (it came from the twist of a trunk leaning 28 deg) can only come from the shoulder blades: relative to the chest the
# shoulder joint rises and sinks 16 / 21 / 25 mm p2p (r5 4 mm), up when that arm swings back, as the r5 shoulder in the world.  Without the
# shoulder-blade tilt (twist_clav=0) the fit has no solution (roll stays at about 10..14 deg).
LEAN_VARIANTS = {
    'L20': dict(lean=33.13, hips_lean=13.55, neck_pitch=16.85, head_pitch=10.0, chest_net_yaw=10.3),
    'L23': dict(lean=37.13, hips_lean=15.15, neck_pitch=19.85, head_pitch=11.5, chest_net_yaw=10.4),
    'L26': dict(lean=41.06, hips_lean=16.81, neck_pitch=22.85, head_pitch=13.0, chest_net_yaw=10.5),
    'L16': dict(lean=27.89, hips_lean=11.43, neck_pitch=12.85, head_pitch=8.0, chest_net_yaw=9.046, twist_gain=2.502, head_lock_share=0.791),
    'L12': dict(lean=22.65, hips_lean=9.31, neck_pitch=8.85, head_pitch=6.0, chest_net_yaw=7.918, twist_gain=2.633, head_lock_share=0.814),
    'L08': dict(lean=17.41, hips_lean=7.19, neck_pitch=4.85, head_pitch=4.0, chest_net_yaw=4.280, twist_gain=3.301, head_lock_share=0.826),
}
for _lv in LEAN_VARIANTS.values():                                   # r6b: defaults only (a variant may set its own twist_gain)
    for _k, _v in dict(twist_ref=(44.0, 18.0), twist_gain=1.5, twist_clav=1).items():
        _lv.setdefault(_k, _v)
P.head_lock_share = 0.6         # the head keeps half of the trunk's sideways motion (it goes along, damped; the gaze stays ahead)
P.tail_abs = [26.0, 15.0, 5.0, -1.0, 3.0, 10.0, 14.0, 14.0]       # soft S-curve in the side view: up at the root, a dip, the tip rising
P.tail_counter = 0.4
P.tail_lat = (1.5, 6.0)
P.tail_vert = (2.0, 8.0)
P.arm_ph = 0.14                  # arm phase lead: an arm is furthest forward in the middle of the flight after the toe off of its own side (NTE, measured)
P.wr_max = 35.0                  # the wrist bends at most this much (barrel against forearm)
P.alpha_tab = None               # fitted abduction of the upper arm per side and frame (deg), see fit_arm_alpha
P.alpha_max = 29.0
P.CLEAR = 0.003                  # least distance arm / pistol to the body and gear (m)
# barrel: angle from straight DOWN towards forward (deg): 90 = level forward, 55 = 35 deg below level, -10 = down and 10 deg back;
# bar(pa) = bar0 + barA * wave(pa - lag_w) in the world (root) frame, bar_in = inward turn of the barrel (deg)
# stab = share of the chest's oscillating rotation that the arms do NOT follow (gimbal), pro = shoulder blade glide (deg)
VARIANTS = {
    # sigw0 = centre of the upper arm swing in the WORLD (deg, + = elbow in front); eps = elbow flexion (inner angle = 180 - eps)
    # lag_e < 0: the elbow bends AHEAD of the upper arm (it is bent in the forward drive); bar_delay: the barrel follows the forearm of
    # bar_delay cycles ago; barrel elevation = clamp(el_k * that forearm elevation + el_c, el_lo, el_hi) + el_play * wave(pa - lag_w)
    'P2': dict(label='P2  Lauf frei (Runde 5)', sigw0=-9.5, sigA=25.5, eps0=82.0, epsA=20.0, rho=12.0, alpha0=14.0, stab=0.0,
               bar0=0.0, barA=0.0, bar_in=4.0, pro=10.0, lag_e=-0.03, lag_w=0.07, mode='run3', carry=15.0, bar_delay=0.07,
               el_k=0.95, el_c=0.0, el_lo=-45.0, el_hi=30.0, el_play=3.0),
}
# upper arm -35 .. +16 (world; r3 -35 .. +30), elbow flexion 102 in front .. 62 behind (inner 78 .. 118)
P.min_down = 2.0                 # mode run: the barrel never points higher than this many degrees below level
# r6b: the lean variant is applied here (after the defaults above, so a variant may also set P values such as alpha_max); ARM_TWEAKS = changes of
# the arm variant P2 per lean variant (none unless the clearance or the look needs them, see the notes there)
for _k, _v in LEAN_VARIANTS[LV].items():
    setattr(P, _k, _v)
ARM_TWEAKS = {}
for _k, _v in ARM_TWEAKS.get(LV, {}).items():
    VARIANTS['P2'][_k] = _v
GRIP = {'Index': (4.0, 10.0, 8.0), 'Middle': (68.0, 74.0, 44.0), 'Ring': (72.0, 78.0, 46.0), 'Little': (75.0, 80.0, 48.0)}   # around the handle, index along the frame
GRIP_SPREAD = {'Index': 22.0, 'Middle': 0.0, 'Ring': -2.0, 'Little': -4.0}
THUMB = (20.0, 30.0, 18.0, 10.0)   # thumb: turn towards the barrel (deg about z), curl of proximal / intermediate / distal
GRIP_AT = (0.058, -0.010, 0.020)   # grip centre from the wrist: along the hand, towards the thumb, towards the palm (m)

for _tok in argv[3:]:                                                # e.g.  SPEED=1.3 NF=32 PH_TO=0.6 (design experiments)
    if '=' in _tok:
        _k, _v = _tok.split('=', 1)
        if _k == 'LV':                                               # r6: the lean variant, applied above
            pass
        elif _k == 'twist_ref':                                      # r6: e.g. twist_ref=44,18 or twist_ref=none
            P.twist_ref = None if _v == 'none' else tuple(float(t) for t in _v.split(','))
        elif _k == 'tail_mode':
            P.tail_mode = _v
        elif _k == 'variants':                                       # e.g. variants=A,C
            VARIANTS = {k_: v_ for k_, v_ in VARIANTS.items() if k_ in _v.split(',')}
        elif '.' in _k:                                              # e.g. A.sig0=3  (a parameter of one variant)
            _vk, _pk = _k.split('.', 1)
            if _vk in VARIANTS:
                VARIANTS[_vk][_pk] = float(_v)
        elif _k in ('GRIP_AT', 'THUMB'):
            globals()[_k] = tuple(float(t) for t in _v.split(','))
        elif _k in ('tail_abs', 'tail_walk', 'lock_w', 'tail_lat', 'tail_vert'):
            setattr(P, _k, [float(t) for t in _v.split(',')])
        else:
            setattr(P, _k, int(_v) if _k in ('NF', 'HARM', 'LEGGRID', 'ARM_FIT', 'sec_on', 'spec', 'SPECSCAN', 'amp_norm', 'head_lock', 'twist_clav',
                                             'head_free', 'ear_on', 'spring_on', 'spring_sub', 'spring_cycles', 'spring_world', 'spring_coll', 'spring_debug', 'spring_smooth', 'A_FIT') else float(_v))

NF = P.NF
T_CYCLE = NF / FPS
VT = P.SPEED * T_CYCLE                                               # stride length (m)
if P.down_phase is None:
    P.down_phase = P.PH_TO / 2.0                                     # the "down pose" of the run = mid stance


def _dip_integral(phi):
    """integral of the stance dip from 0 to phi in cycle units (period half a cycle: sin(pi q / b) while a foot is on the ground, 0 in the flight)"""
    b = P.PH_TO
    k = int(math.floor(phi / 0.5 + 1e-12))
    q = phi - 0.5 * k
    if q < b:
        return k * (2.0 * b / math.pi) + (b / math.pi) * (1.0 - math.cos(math.pi * q / b))
    return (k + 1) * (2.0 * b / math.pi)


def ground_rate(phi):
    """ground speed under the character as a multiple of the mean speed at the cycle phase phi: it dips by speed_var while a foot is on the ground
    (braking, then push: slowest at mid stance) and is steady in the flight phase"""
    b = P.PH_TO
    q = phi % 0.5
    dip = math.sin(math.pi * q / b) if q < b else 0.0
    return 1.0 + P.speed_var * (4.0 * b / math.pi - dip)


def G(phi):
    """how far the ground has moved back (m) since the right touchdown (phi = 0); G(1) = VT, the stride"""
    b = P.PH_TO
    return VT * (phi * (1.0 + P.speed_var * 4.0 * b / math.pi) - P.speed_var * _dip_integral(phi))


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


def pieces_eval(pieces, x):
    """chain of quintic Hermite pieces, every piece (x0, x1, p0, v0, a0, p1, v1, a1) with v and a the derivatives with respect to x: position,
    speed and acceleration are continuous where the pieces meet"""
    for (x0, x1, p0, v0, a0, p1, v1, a1) in pieces:
        if x <= x1:
            ln = x1 - x0
            return herm5(p0, v0 * ln, a0 * ln * ln, p1, v1 * ln, a1 * ln * ln, (x - x0) / ln)
    return pieces[-1][5]


def extreme_accels(x, y):
    """accelerations at the interior knots of a chain whose speed is zero there (an extreme): the value that fits both neighbours"""
    acc = [0.0] * len(x)
    for i in range(1, len(x) - 1):
        acc[i] = (y[i - 1] - y[i]) / (x[i] - x[i - 1]) ** 2 + (y[i + 1] - y[i]) / (x[i + 1] - x[i]) ** 2
    return acc


HIP_DROP = 0.0387                                                    # the hips bone is this far above the hip joints
LEG_L1 = (HEAD0[nm('R', 'LowerLeg')] - HEAD0[nm('R', 'UpperLeg')]).length          # thigh
LEG_L2 = (HEAD0[nm('R', 'Foot')] - HEAD0[nm('R', 'LowerLeg')]).length              # shank
LEG_SUM = LEG_L1 + LEG_L2
HIP_X = abs(HEAD0[nm('R', 'UpperLeg')].x)                                           # the hip joints are this far from the centre line


def knee_ratio(knee_deg):
    """leg length d / (L1 + L2) of a leg with this knee flexion"""
    c = math.cos(math.radians(knee_deg))
    return math.sqrt(LEG_L1 ** 2 + LEG_L2 ** 2 + 2.0 * LEG_L1 * LEG_L2 * c) / (LEG_L1 + LEG_L2)


def knee_of_ratio(r):
    """knee flexion (deg) of a leg with the length ratio d / (L1 + L2)"""
    c = ((r * LEG_SUM) ** 2 - LEG_L1 ** 2 - LEG_L2 ** 2) / (2.0 * LEG_L1 * LEG_L2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


class Gait:
    """foot trajectory of one foot as a function of its cycle phase phi (0 = touchdown) in the character frame.
    RUN: she lands on the ball of the foot, the toe joint is planted in the ground frame for the whole stance, then the swing / flight.
    One continuous model for the whole cycle, no switching between solvers: the foot pitch is one curve (stance heel rise + quintic Hermite pieces
    in the swing), the ankle path of the swing is made of quintic Hermite pieces in the fore-aft direction and in the LEG LENGTH (so the knee is
    shaped directly: it stops extending after the toe off, bends, reaches out again before the touchdown), and all of them start and end with the
    position, the speed and the acceleration of the stance: neither the foot nor the leg has a corner anywhere."""

    def __init__(self, a_td):
        th0 = deg(P.TH_TD)
        ry, _ = rot2(th0, A0y - J0y, A0z - J0z)
        self.y_j0 = a_td - ry                                        # toe joint y at touchdown, so that the ankle lands a_td ahead of the hip
        self.D = 1.0 - P.PH_TO                                       # share of the cycle in which the foot is off the ground
        self._leg_key = None
        self._build_pitch()
        self._build_swing()

    # ----- foot pitch (radians, toes up positive)
    def _build_pitch(self):
        """Stance: the foot is flat for HEEL_DELAY frames, then the heel rises with a pitch rate that grows smoothly (quintic smooth step over
        HEEL_RAMP frames) to a steady rate that carries the foot from TH_TD to -TH_TO at toe off.  Swing: the foot keeps turning toes-down for a moment
        (speed and acceleration continue from the stance, the heel whips up; SW_STOP_T frames), then it comes up through -TH_SW_MID at SW_MID_U of
        the swing while the shank swings forward (this is what makes the ankle dorsiflex in the swing) and reaches TH_TD for the next touchdown with
        speed and acceleration zero, like at the start of the stance."""
        S = P.PH_TO * NF                                             # frames of ground contact
        td, to = deg(P.TH_TD), -deg(P.TH_TO)
        self.rate = (to - td) / (S - P.HEEL_DELAY - 0.5 * P.HEEL_RAMP)   # steady pitch rate of the heel rise (rad per frame, negative = toes down)
        t1 = P.SW_STOP_T
        u1 = t1 / (self.D * NF)
        p1 = to + 0.5 * self.rate * t1                               # a smooth stop from the speed `rate` within t1 frames turns by half of rate x t1
        u2 = P.SW_MID_U
        p2 = -deg(P.TH_SW_MID)
        v0 = self.rate * NF * self.D                                 # pitch speed at toe off per swing fraction
        v2 = (td - p1) / (1.0 - u1)                                  # mean speed of the rise
        self.pitch_pieces = [(0.0, u1, to, v0, 0.0, p1, 0.0, 0.0),
                             (u1, u2, p1, 0.0, 0.0, p2, v2, 0.0),
                             (u2, 1.0, p2, v2, 0.0, td, 0.0, 0.0)]
        # toes: in the stance they bend with the heel rise (the toe bone stays flat on the ground); after the toe off they relax slowly to TAU_RELAX
        # (a quick relaxing would turn the toe bone as fast as the heel rise) and are flat again for the touchdown
        h = 1e-4
        to_ph = P.PH_TO
        tau_to = toe_bend(self.theta_stance(to_ph))
        v_tau = (3.0 * tau_to - 4.0 * toe_bend(self.theta_stance(to_ph - h)) + toe_bend(self.theta_stance(to_ph - 2.0 * h))) / (2.0 * h)
        tau_r, tau_td = deg(P.TAU_RELAX), toe_bend(td)
        self.tau_pieces = [(0.0, P.TAU_U, tau_to, v_tau * self.D, 0.0, tau_r, 0.0, 0.0),
                           (P.TAU_U, 0.80, tau_r, 0.0, 0.0, tau_r, 0.0, 0.0),
                           (0.80, 1.0, tau_r, 0.0, 0.0, tau_td, 0.0, 0.0)]

    def theta_stance(self, phi):
        t = phi * NF - P.HEEL_DELAY
        td = deg(P.TH_TD)
        if t <= 0.0:
            return td
        tr = P.HEEL_RAMP
        if t < tr:
            x = t / tr
            return td + self.rate * tr * (2.5 * x ** 4 - 3.0 * x ** 5 + x ** 6)
        return td + self.rate * (0.5 * tr + (t - tr))

    def theta_swing(self, phi):
        return pieces_eval(self.pitch_pieces, (phi - P.PH_TO) / self.D)

    def tau_swing(self, phi):
        return pieces_eval(self.tau_pieces, (phi - P.PH_TO) / self.D)

    # ----- ankle path in the stance
    def y_stance(self, phi):
        th = self.theta_stance(phi)
        j_y = self.y_j0 - G(phi)                                     # the toe joint is fixed to the ground for the whole stance
        ry, _ = rot2(th, A0y - J0y, A0z - J0z)
        return j_y + ry

    def z_stance(self, phi):
        th = self.theta_stance(phi)
        return -low_rel(th, toe_bend(th))                            # the lowest sole point is on the ground

    # ----- the leg: length of the leg (ankle to hip joint) for an ankle position, and back
    @staticmethod
    def lateral(phi):
        """sideways distance between the hip joint and the ankle (m): the foot track is narrower than the hips, the swing foot goes out around the other leg"""
        u_sw = (phi - P.PH_TO) / (1.0 - P.PH_TO)
        circ = P.CIRC * math.sin(math.pi * u_sw) ** 2 if 0.0 <= u_sw <= 1.0 else 0.0
        return HIP_X - (P.BASE + circ)

    def ratio(self, phi, y, z):
        """leg length d / (L1 + L2) for an ankle at (y, z) ahead of / above the ground, hips height of the phase phi"""
        zh = pelvis_z(phi) - HIP_DROP
        dx = self.lateral(phi)
        return math.sqrt(y * y + (zh - z) ** 2 + dx * dx) / LEG_SUM

    def z_of_ratio(self, phi, y, r):
        zh = pelvis_z(phi) - HIP_DROP
        dx = self.lateral(phi)
        return zh - math.sqrt(max((r * LEG_SUM) ** 2 - y * y - dx * dx, 1e-6))

    # ----- ankle path in the swing / flight
    def _build_swing(self):
        """the ankle path of the swing in the CHARACTER frame, fore-aft direction y: from the toe off (position, speed and acceleration continue from the
        stance) the foot slows down and comes to rest at a rear extreme T_REAR frames later (the heel whips up behind), goes forward to a forward extreme
        T_FWD frames before the touchdown and from there it speeds up to the touchdown spot, which it reaches with a backward speed of (1 + RHO) x the
        running speed (in the ground frame the foot claws back at RHO x speed).  Quintic Hermite pieces; every stop and every start is smooth (speed and
        acceleration zero) and the distance of a stop is half of speed x time, so the path has no overshoot."""
        h = 1e-4
        f = self.y_stance
        to = P.PH_TO
        y_to = f(to)
        s_to = (3.0 * y_to - 4.0 * f(to - h) + f(to - 2.0 * h)) / (2.0 * h)
        a_to = (y_to - 2.0 * f(to - h) + f(to - 2.0 * h)) / (h * h)
        z0, z1, z2 = f(0.0), f(h), f(2.0 * h)
        s_td = (-3.0 * z0 + 4.0 * z1 - z2) / (2.0 * h)
        a_td = (z0 - 2.0 * z1 + z2) / (h * h)
        s_arr = s_td - P.RHO * dG(0.0)
        t_r, t_f = P.T_REAR / NF, P.T_FWD / NF
        x = [to, to + t_r, 1.0 - t_f, 1.0]
        y = [y_to, y_to + 0.5 * s_to * t_r, z0 - 0.5 * s_arr * t_f, z0]
        vel = [s_to, 0.0, 0.0, s_arr]
        acc = [a_to, 0.0, 0.0, a_td]
        self.y_x = x
        self.y_pieces = [(x[i], x[i + 1], y[i], vel[i], acc[i], y[i + 1], vel[i + 1], acc[i + 1]) for i in range(3)]

    def y_swing(self, phi):
        """first and last piece: stops / starts as described above; between the two extremes the foot travels forward with a smooth step of the warped time
        u ^ P_FWD (above 1 the foot stays back longer and comes forward later: a lower knee lift)"""
        x = self.y_x
        if phi <= x[1]:
            return pieces_eval(self.y_pieces[:1], phi)
        if phi >= x[2]:
            return pieces_eval(self.y_pieces[2:], phi)
        u = (phi - x[1]) / (x[2] - x[1])
        w = u ** P.P_FWD
        y1, y2 = self.y_pieces[0][5], self.y_pieces[2][2]
        return y1 + (y2 - y1) * w * w * w * (10.0 - 15.0 * w + 6.0 * w * w)

    def _leg_pieces(self):
        """leg length ratio d / (L1 + L2) of the swing as quintic Hermite pieces: starts with the value, speed and acceleration of the planted leg at the toe
        off, goes on to the longest leg (knee KN_EXT, a smooth stop), then to the most bent knee (KN_SW at SW_FLEX_U of the swing), reaches out again
        (LATE_EXT degrees of knee flexion straighter than at the touchdown, a smooth start towards the planted leg) and ends with the value, speed and
        acceleration of the planted leg at the touchdown.  Depends on the hips height, so it is rebuilt when Z_TD changes."""
        key = (P.Z_TD, P.KD, P.KA, P.BASE, P.CIRC, self.y_j0, P.TH_TO, P.TH_TD, P.HEEL_DELAY, P.HEEL_RAMP, P.PH_TO, P.KN_EXT, P.KN_SW, P.SW_FLEX_U, P.LATE_EXT)
        if key == self._leg_key:
            return self._leg_pcs
        h = 1e-4
        to = P.PH_TO

        def r_st(ph):
            return self.ratio(ph, self.y_stance(ph), self.z_stance(ph))
        r_to = r_st(to)
        v_to = (3.0 * r_to - 4.0 * r_st(to - h) + r_st(to - 2.0 * h)) / (2.0 * h)
        a_to = (r_to - 2.0 * r_st(to - h) + r_st(to - 2.0 * h)) / (h * h)
        r0, r1, r2 = r_st(0.0), r_st(h), r_st(2.0 * h)
        v_td = (-3.0 * r0 + 4.0 * r1 - r2) / (2.0 * h)
        a_td = (r0 - 2.0 * r1 + r2) / (h * h)
        r_ext = knee_ratio(P.KN_EXT)
        if v_to > 1e-6 and r_ext > r_to:                              # the leg is still lengthening: it stops smoothly at the knee KN_EXT
            t_e = max((r_ext - r_to) / (0.5 * v_to), 0.8 / NF)
        else:
            r_ext, t_e = r_to, 1.0 / NF
        r_late = knee_ratio(max(knee_of_ratio(r0) - P.LATE_EXT, 4.0))
        if v_td < -1e-6 and r_late > r0:                              # the planted leg shortens at once: the leg before it is longer and starts shortening smoothly
            t_l = max((r0 - r_late) / (0.5 * v_td), 0.8 / NF)
        else:
            r_late, t_l = r0, 1.0 / NF
        x = [to, to + t_e, to + P.SW_FLEX_U * self.D, 1.0 - t_l, 1.0]
        r = [r_to, r_ext, knee_ratio(P.KN_SW), r_late, r0]
        vel = [v_to, 0.0, 0.0, 0.0, v_td]
        acc = [a_to, 0.0, 0.0, 0.0, a_td]
        self._leg_pcs = [(x[i], x[i + 1], r[i], vel[i], acc[i], r[i + 1], vel[i + 1], acc[i + 1]) for i in range(4)]
        self._leg_key = key
        return self._leg_pcs

    def swing_z(self, phi, y, th, tau):
        """ankle height in the swing from the planned leg length.  Safety net: the sole never goes through the floor (smooth maximum); it is faded out
        towards toe off and touchdown, where the planned height is exactly the one of the planted foot (the net would lift the ankle there)."""
        z = self.z_of_ratio(phi, y, pieces_eval(self._leg_pieces(), phi))
        u = (phi - P.PH_TO) / self.D
        w = sstep(u / 0.06) * (1.0 - sstep((u - 0.94) / 0.06))
        if w <= 0.0:
            return z
        z_floor = -low_rel(th, tau) + 0.002
        e = 0.002
        return z + w * (0.5 * (z + z_floor + math.sqrt((z - z_floor) ** 2 + e * e)) - z)

    # ----- everything at once
    def state(self, phi):
        """returns (ankle y, ankle z, foot pitch, toe bend)  [metres / radians, toes up positive]"""
        phi = phi % 1.0
        if phi < P.PH_TO:
            th = self.theta_stance(phi)
            y = self.y_stance(phi)
            tau = toe_bend(th)
            z = -low_rel(th, tau)
        else:
            th = self.theta_swing(phi)
            y = self.y_swing(phi)
            tau = self.tau_swing(phi)
            z = self.swing_z(phi, y, th, tau)
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


_ZTAB = {}


def _ztab(par):
    """the vertical curve of the hips (m, relative to the height at touchdown / toe off) over one cycle, 720 samples: in the stance of each foot a
    half-sine dip (the legs give way), in the flight an arc (up and down again).  The physical sizes are  dip = g t_flight t_stance / (2 pi)  and
    rise = g t_flight^2 / 8; KD and KA take a share of them (a sprinter bounces more than a pretty run should).  Smoothed a little so that
    touchdown and toe off have no corner."""
    key = (par.PH_TO, par.KD, par.KA, par.ZSMOOTH, NF, FPS)
    if key in _ZTAB:
        return _ZTAB[key]
    n = 720
    b = par.PH_TO
    tau_s = b * T_CYCLE
    t_f = (0.5 - b) * T_CYCLE
    dip = par.KD * 9.81 * t_f * tau_s / (2.0 * math.pi)
    rise = par.KA * 9.81 * t_f * t_f / 8.0
    raw = []
    for i in range(n):
        q = (i / n) % 0.5
        if q < b:
            raw.append(-dip * math.sin(math.pi * q / b))
        else:
            s_ = (q - b) / (0.5 - b)
            raw.append(4.0 * rise * s_ * (1.0 - s_))
    w = max(1, int(round(par.ZSMOOTH * n)))
    out = []
    for i in range(n):
        acc = ws = 0.0
        for j in range(-w, w + 1):
            wt = 1.0 - abs(j) / (w + 1.0)
            acc += wt * raw[(i + j) % n]
            ws += wt
        out.append(acc / ws)
    _ZTAB[key] = out
    return out


def pelvis_z(p, par=P):
    """hips bone height (m): Z_TD plus the physical curve of _ztab (lowest at mid stance of each foot, highest in the middle of each flight)"""
    tab = _ztab(par)
    n = len(tab)
    x = (p % 1.0) * n
    i0 = int(x)
    fr = x - i0
    return par.Z_TD + tab[i0 % n] * (1.0 - fr) + tab[(i0 + 1) % n] * fr


def arm_wave(p, par=P):
    """shape of the arm swing at the arm phase p (0 = furthest forward, the opposite leg's touchdown): +1 = furthest forward, -1 = furthest back.
    A rounded triangle wave (swing_tri) on a time axis that runs quicker over the forward drive (second half of the cycle) than over the way back."""
    th = TWO_PI * p + par.swing_skew * (math.cos(TWO_PI * p) - 1.0)
    return (math.cos(th) + par.swing_tri * math.cos(3.0 * th)) / (1.0 + par.swing_tri)


def hang_of(pa, par=P):
    """outward angle (deg) of the upper arm at the arm phase pa: the table fitted against the gear, before the fit a plain wave between hang_in
    (forward swing) and hang_out (back swing)"""
    if par.hang_tab is not None:
        x = (pa % 1.0) * NF
        i0 = int(x)
        fr = x - i0
        return par.hang_tab[i0 % NF] * (1.0 - fr) + par.hang_tab[(i0 + 1) % NF] * fr
    return par.hang_in + par.hang_add + (par.hang_out - par.hang_in) * (0.5 - 0.5 * arm_wave(pa, par))


P.variant = list(VARIANTS)[0]


def arm_phase(p, side, par=P):
    """phase of this arm's swing (0 = furthest forward); counter to the legs, the left arm is forward shortly before the right touchdown"""
    return (p + (0.0 if side == 'L' else 0.5) + par.arm_ph) % 1.0


def alpha_of(side, f, V, par=P):
    """abduction of the upper arm (deg): the fitted table (per side and frame) or the variant's start value"""
    if par.alpha_tab is None:
        return V['alpha0']
    tab = par.alpha_tab[side]
    x = f % NF
    i0 = int(math.floor(x))
    fr = x - i0
    return tab[i0 % NF] * (1.0 - fr) + tab[(i0 + 1) % NF] * fr


def arm_chain(side, f, pa, Dc, par, V):
    """SPRINT r1 arm: world directions of upper arm u, forearm fo, hand h and the palm normal n.  The upper arm hangs down the trunk in the frame
    of the (stabilised) upper chest Dc, is abducted by alpha about the chest's forward axis and swings by sigma about the chest's lateral axis (one
    clean swing plane); the elbow axis is the lateral axis turned inwards by rho about the upper arm (constant); the forearm is the upper arm turned
    by eps about that axis (a pure hinge, the palm normal stays on the axis, so nothing twists); the hand turns from the forearm towards the barrel
    target by the shortest rotation, at most wr_max."""
    sx = 1.0 if side == 'R' else -1.0
    sig = (V['sig0'] if 'sig0' in V else V['sigw0'] + par.lean) + V['sigA'] * arm_wave(pa, par)   # r3: centre given in the world
    eps = V['eps0'] + V['epsA'] * arm_wave(pa - V['lag_e'], par)
    alpha = alpha_of(side, f, V, par)
    cx, cy, cz = Dc @ Vector((1.0, 0.0, 0.0)), Dc @ Vector((0.0, 1.0, 0.0)), Dc @ Vector((0.0, 0.0, 1.0))
    v = Quaternion((1.0, 0.0, 0.0), deg(sig)) @ (Quaternion((0.0, 1.0, 0.0), deg(-sx * alpha)) @ Vector((0.0, 0.0, -1.0)))
    u = (cx * v.x + cy * v.y + cz * v.z).normalized()
    a0 = (cx - u * cx.dot(u)).normalized()
    a = (Quaternion(u, deg(-sx * V['rho'])) @ a0).normalized()
    fo = (Quaternion(a, deg(eps)) @ u).normalized()
    n = a * (-sx)
    if V.get('carry'):                                               # carrying angle: the more the elbow opens, the more the forearm points outwards
        t_ = (V['eps0'] + V['epsA'] - eps) / max(2.0 * V['epsA'], 1e-6)   # 0 = most bent (front), 1 = most open (behind)
        fo = (fo + a * (sx * math.tan(deg(V['carry'] * min(max(t_, 0.0), 1.0))))).normalized()
        n = (n - fo * n.dot(fo)).normalized()
    bar = deg(V['bar0'] + V['barA'] * arm_wave(pa - V['lag_w'], par))
    if V.get('mode') == 'run3':                                      # r3: the wrist turns the barrel towards an elevation that follows the forearm
        e_f = math.degrees(math.asin(max(-1.0, min(1.0, fo.z))))
        if V.get('bar_delay'):                                       # r4: the forearm of bar_delay cycles ago (same chest frame)
            pd_ = pa - V['bar_delay']
            sd_ = (V['sig0'] if 'sig0' in V else V['sigw0'] + par.lean) + V['sigA'] * arm_wave(pd_, par)
            ed_ = V['eps0'] + V['epsA'] * arm_wave(pd_ - V['lag_e'], par)
            vd_ = Quaternion((1.0, 0.0, 0.0), deg(sd_)) @ (Quaternion((0.0, 1.0, 0.0), deg(-sx * alpha)) @ Vector((0.0, 0.0, -1.0)))
            ud_ = (cx * vd_.x + cy * vd_.y + cz * vd_.z).normalized()
            ad_ = (Quaternion(ud_, deg(-sx * V['rho'])) @ (cx - ud_ * cx.dot(ud_)).normalized()).normalized()
            fd_ = (Quaternion(ad_, deg(ed_)) @ ud_).normalized()
            e_f = math.degrees(math.asin(max(-1.0, min(1.0, fd_.z))))
        e_t = min(max(V['el_k'] * e_f + V['el_c'], V['el_lo']), V['el_hi']) + V['el_play'] * arm_wave(pa - V['lag_w'], par)
        best = None
        for _k in range(-35, 36):
            b_ = (Quaternion(n, sx * deg(float(_k))) @ fo).normalized()
            b_ = (b_ + n * math.tan(deg(V['bar_in']))).normalized()
            err_ = abs(math.degrees(math.asin(max(-1.0, min(1.0, b_.z)))) - e_t) + 0.02 * abs(_k)
            if best is None or err_ < best[0]:
                best = (err_, b_)
        b = best[1]
    elif V.get('mode') == 'run':                                       # natural run: the barrel follows the forearm, dropped towards the little finger
        lim_ = deg(par.wr_max)
        d_ = bar
        for _k in range(40):
            b = (Quaternion(n, sx * d_) @ fo).normalized()
            b = (b + n * math.tan(deg(V['bar_in']))).normalized()
            if b.z <= -math.sin(deg(par.min_down)) or d_ >= lim_:
                break
            d_ = min(lim_, d_ + deg(1.0))                            # never up: the wrist drops a little more where the forearm points up
    elif V.get('mode') == 'rel':                                       # the barrel = forearm bent towards the little finger by bar (ulnar deviation)
        b = (Quaternion(n, sx * bar) @ fo).normalized()
        b = (b + n * math.tan(deg(V['bar_in']))).normalized()        # ... and towards the palm by bar_in (the barrels run along the thighs)
    else:
        bi = deg(V['bar_in'])
        b = Vector((-sx * math.sin(bi) * math.sin(bar), math.cos(bi) * math.sin(bar), -math.cos(bar)))
    ang = fo.angle(b)
    lim = deg(par.wr_max)
    h = b.copy() if ang <= lim else fo.slerp(b, lim / ang)
    return u, fo, h.normalized(), n, {'sig': sig, 'eps': eps, 'alpha': alpha, 'wrist_want': math.degrees(ang), 'wrist': math.degrees(min(ang, lim))}


def tail_rest_up(par):
    """rest pitch per tail joint relative to its parent (deg, positive = up).  Spec pass: from the wanted absolute direction of every joint
    in the side view (par.tail_abs: down at the base, towards horizontal in the middle, up at the tip); the mean forward pitch of the
    pelvis is taken out so the angles hold in the world."""
    if par.spec and par.tail_mode == 'wave':
        a = par.tail_abs
        return [a[0] + (-par.hips_lean)] + [a[i] - a[i - 1] for i in range(1, 8)]
    return par.tail_walk


def spec_levels(p, par):
    """spec pass: cumulative (pitch, roll, yaw) in degrees of spine, chest and upper chest.  The spine absorbs half of the pelvic roll and
    40 % of the pelvic yaw, the chest the other half of the roll and a counter twist of chest_twist degrees against the spine, so the chest
    ends up level and (almost) without yaw; the forward lean builds up along the spine."""
    twist = (1.0 + par.chest_net_yaw / max(par.yaw_p, 1e-6)) - par.yaw_abs_spine   # chest world yaw = - chest_net_yaw / yaw_p * pelvis yaw
    yaw_abs = (par.yaw_abs_spine, par.yaw_abs_spine + twist, par.yaw_abs_spine + twist)
    out = []
    for i in range(3):
        lag = par.sp_lag[i]
        pit = -(par.hips_lean + par.lean_cum[i] * (par.lean - par.hips_lean) + par.nod_share[i + 1] * lean_dive(p - lag, par))
        roll = pelvis_roll(p - lag, par) * (1.0 - par.roll_abs[i])
        yaw = pelvis_yaw(p - lag, par) * (1.0 - yaw_abs[i])
        out.append([pit, roll, yaw])
    return out


def parent_pitch(i, lean, hips_lean, par):
    """r6: mean forward pitch (deg) of the parent of spine level i (0 = spine: the hips, 1 = chest: the spine, 2 = upper chest: the chest,
    3 = the clavicles: the upper chest)"""
    return hips_lean if i == 0 else hips_lean + par.lean_cum[i - 1] * (lean - hips_lean)


def twist_conj(i, q, par):
    """r6: every spine joint twists and bends sideways about the SAME world axes as in r5 (par.twist_ref = r5 lean, r5 hips_lean).  The relative
    rotation q of a level is applied in its parent's frame, whose axis now stands more upright; conjugated by the pitch difference d it turns about
    the r5 axis again, so the shoulders rock (seen from behind) and turn (seen from above) as in r5 while the trunk leans less.  The forward pitch
    itself is unchanged (a rotation about the lateral axis commutes with the conjugation)."""
    ref = getattr(par, 'twist_ref', None)
    if not ref:
        return q
    d = parent_pitch(i, ref[0], ref[1], par) - parent_pitch(i, par.lean, par.hips_lean, par)
    c = eul(rx=-getattr(par, 'twist_gain', 1.0) * d)                 # twist_gain > 1: the head lock (which now works against a head that sits off
    return c @ q @ c.inverted()                                       # the r5 axis) takes some of the rock back, the gain gives it back


def head_pos(levels, pel, hips_d, neck_q, par=None):
    """world position of the head bone for cumulative spine levels (forward kinematics with the same composition as compute_pose)"""
    D = eul(rx=pel[0], ry=pel[1], rz=pel[2])
    pos = HEAD0[H['hips']] + hips_d
    prev_name, prev = H['hips'], pel
    for i_, (name_, cur) in enumerate(zip((H['spine'], H['chest'], H['upperChest']), levels)):
        pos = pos + D @ (HEAD0[name_] - HEAD0[prev_name])
        D = D @ twist_conj(i_, eul(rx=cur[0] - prev[0], ry=cur[1] - prev[1], rz=cur[2] - prev[2]), par if par is not None else P)
        prev_name, prev = name_, cur
    pos = pos + D @ (HEAD0[H['neck']] - HEAD0[prev_name])
    return pos + neck_q @ (HEAD0[H['head']] - HEAD0[H['neck']])


def lock_head(levels, pel, hips_d, neck_q, par):
    """extra roll c (deg) that is added to the spine levels (weights par.lock_w) so that the head bone stays on x = 0: the hips shift over
    the stance foot and the pelvis rolls, the torso leans back over the centre line.  Secant iteration on the exact forward kinematics."""
    def xh(c):
        lv = [[l[0], l[1] + c * w, l[2]] for l, w in zip(levels, par.lock_w)]
        return head_pos(lv, pel, hips_d, neck_q, par).x

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
    pitch_w = -par.hips_lean + par.pitch_amp * math.cos(2.0 * ph + 1.0) - par.nod_share[0] * lean_dive(p, par)
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
    if par.spec and not par.head_free:                                # the gaze stays level and forward; a share of the trunk's motion follows through
        trail = spec_levels(p - par.head_lag, par)[2]                 # the upper chest a moment ago: the head trails it (pitch, roll, yaw in deg)
        yaw_h = par.head_yaw * trail[2]
        rol_h = par.head_roll * trail[1]
        nod_h = par.head_nod * math.cos(2.0 * TWO_PI * (p - par.down_phase - par.head_lag))      # the head dips with the chest into every down pose
        absd[H['neck']] = eul(rx=-par.neck_pitch - 0.4 * nod_h, ry=0.5 * rol_h, rz=0.5 * yaw_h)
        absd[H['head']] = eul(rx=-par.head_pitch - nod_h, ry=rol_h, rz=yaw_h)
        if par.head_lock and not light:
            c_lock = lock_head(levels, (pitch_w, roll_w, yaw_w), hips_d, absd[H['neck']], par)
            c_lock *= getattr(par, 'head_lock_share', 1.0)
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
    for i_, (name_, cur) in enumerate(zip((H['spine'], H['chest'], H['upperChest']), levels)):
        rel[name_] = twist_conj(i_, eul(rx=cur[0] - prev[0], ry=cur[1] - prev[1], rz=cur[2] - prev[2]), par)   # r6: r5 twist axes
        prev = cur

    # --- shoulders (clavicles): sink a little at every down pose; the shoulder blade glides forward with the arm and back with it
    V_ = VARIANTS[par.variant]
    for side, sx in (('L', -1.0), ('R', 1.0)):
        sw = s1 * (1.0 if side == 'L' else -1.0)
        k_s = arm_wave(arm_phase(p, side, par) - 0.03, par)          # +1 = this arm swings forward (the shoulder blade trails a little)
        drop = 1.2 * math.cos(2.0 * TWO_PI * (p - par.down_phase - 0.02))
        rel[nm(side, 'Shoulder')] = eul(ry=sx * (4.0 + 0.6 * sw + drop), rz=sx * V_['pro'] * k_s)
        if getattr(par, 'twist_clav', 0):                            # r6 (switch): the shoulder blade glides about the r5 axes too
            rel[nm(side, 'Shoulder')] = twist_conj(3, rel[nm(side, 'Shoulder')], par)

    if light:
        return rel, absd, hips_d, _legs(p, par, rel), diag

    # --- cat tail: rest curve plus a travelling wave (par.tail_dyn, see tail_ear_tables): every joint trails the one before
    rest_up = tail_rest_up(par)
    for i in range(1, 9):
        up = rest_up[i - 1] + (par.tail_lift if i <= 2 else 0.0)
        pit_t, yaw_t = (0.0, 0.0)
        if par.tail_dyn is not None:
            pit_t, yaw_t = par.tail_dyn[i - 1][int(round(f)) % NF]
        if i == 1:                                                    # SPRINT r1: the root turns against the pelvis yaw, the tail stays in line like a rudder
            yaw_t -= par.tail_counter * pelvis_yaw(p, par)
        rel['J_Opt_C_CatTail%d_01' % i] = eul(rx=-(up + pit_t), rz=yaw_t)

    # --- hair (first pass only, the spring simulation replaces it): small bouncing wave down every strand
    for name in ([] if par.spec else HAIR):
        m = HAIR_RE.match(name)
        depth, chain = int(m.group(1)), int(m.group(2))
        rel[name] = eul(rx=2.0 * math.sin(2.0 * TWO_PI * p + 0.6 * chain - 0.35 * depth),
                        ry=1.2 * math.sin(TWO_PI * p + 0.4 * chain - 0.3 * depth))

    # --- arms (SPRINT r1): upper arm, forearm and hand are solved in compute_pose (arm_chain, they need the posed shoulder); here only the
    # pistol grip: middle, ring and little finger around the handle, the index finger straight along the frame (not on the trigger), the thumb
    # along the other side of the frame
    for side, sx in (('L', -1.0), ('R', 1.0)):
        for fn, curls in GRIP.items():
            for pj, (part, c) in enumerate(zip(PARTS, curls)):
                q_ = Quaternion((0, 1, 0), deg(sx * c))
                if pj == 0:
                    q_ = eul(rz=sx * GRIP_SPREAD[fn]) @ q_
                rel[nm(side, fn + part)] = q_
        rel[nm(side, 'ThumbProximal')] = eul(rz=-sx * THUMB[0]) @ Quaternion((0, 1, 0), deg(sx * THUMB[1]))
        rel[nm(side, 'ThumbIntermediate')] = Quaternion((0, 1, 0), deg(sx * THUMB[2]))
        rel[nm(side, 'ThumbDistal')] = Quaternion((0, 1, 0), deg(sx * THUMB[3]))

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
    Pp = {}                                                           # posed joint positions (armature space), for the arms
    armc = {}
    hips_name = H['hips']
    p_ = (f / NF) % 1.0
    V_ = VARIANTS[par.variant]
    dc_mean = eul(rx=-par.lean)                                       # the upper chest without its oscillation (pure forward lean)
    for name in order:
        b = bones[name]
        parent = b.parent.name if b.parent else None
        Dp = D[parent] if parent else Quaternion()
        Pp[name] = HEAD0[name].copy() if parent is None else Pp[parent] + D[parent] @ (HEAD0[name] - HEAD0[parent])
        if name == hips_name:
            Pp[name] = Pp[name] + hips_d
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
            elif name == nm(side, 'UpperArm'):
                sx_ = 1.0 if side == 'R' else -1.0
                dc = dc_mean.slerp(D[H['upperChest']], 1.0 - V_['stab'])
                u_, fo_, h_, n_, info_ = arm_chain(side, f, arm_phase(p_, side, par), dc, par, V_)
                rd_, rn_ = Vector((sx_, 0.0, 0.0)), Vector((0.0, 0.0, -1.0))
                Df_ = aim(rd_, rn_, fo_, n_)
                armc[side] = (aim(rd_, rn_, u_, n_), Df_, fo_.rotation_difference(h_) @ Df_)
                info_['shoulder'] = Pp[name].copy()
                diag['arm_' + side] = info_
                D[name] = armc[side][0]
            elif name == nm(side, 'LowerArm'):
                D[name] = armc[side][1]
            elif name == nm(side, 'Hand'):
                D[name] = armc[side][2]
        Q[name] = R[name].inverted() @ Dp.inverted() @ D[name] @ R[name]
    hips_loc = R[hips_name].inverted() @ hips_d
    diag['legs'] = legs
    diag['Pp'] = Pp
    return Q, hips_loc, D, diag, hips_d


# ------------------------------------------------------------------ design: ankle placement + pelvis height fitted against the legs
FOOT_REST = HEAD0[nm('R', 'Toes')] - HEAD0[nm('R', 'Foot')]                            # ankle -> ball of the foot in the rest pose
ANK_REST = math.degrees((HEAD0[nm('R', 'LowerLeg')] - HEAD0[nm('R', 'Foot')]).angle(FOOT_REST))   # angle shank / foot of the rest pose (= ankle joint 0)


def probe(f, par=P):
    """pelvis + legs only (fast): per side (extension d/(L1+L2), knee flexion in degrees, ankle target, hip joint, foot phase,
    thigh angle in degrees (+ = knee ahead of the hip), ankle joint in degrees (+ = dorsiflexion, - = plantar flexion))"""
    rel, absd, hips_d, legs, diag = solve(f, par, light=True)
    q = rel[H['hips']]
    hip_head = HEAD0[H['hips']]
    out = {}
    for side in ('L', 'R'):
        Hp0 = HEAD0[nm(side, 'UpperLeg')]
        Hp = hip_head + hips_d + q @ (Hp0 - hip_head)
        T, foot_rot, yaw, _, phi = legs[side]
        pole = Vector((-math.sin(deg(yaw)), math.cos(deg(yaw)), 0.0))
        K, Teff, deficit, ext = two_bone_ik(Hp, T, pole, LEG_L1, LEG_L2)
        a1 = (Hp - K).normalized()
        a2 = (Teff - K).normalized()
        knee = 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, a1.dot(a2)))))
        th_v = K - Hp
        thigh = math.degrees(math.atan2(th_v.y, -th_v.z))
        ankle = ANK_REST - math.degrees((K - Teff).angle(foot_rot @ FOOT_REST))
        out[side] = (ext, knee, T, Hp, phi, thigh, ankle)
    return out


def fit_z_td(par, kn_td):
    """hips height at touchdown such that the right knee has kn_td degrees of flexion at the touchdown (frame 0)"""
    lo, hi = 0.60, 1.05
    for _ in range(36):
        mid = 0.5 * (lo + hi)
        par.Z_TD = mid
        k = probe(0.0, par)['R'][1]
        if k > kn_td:                                                # too bent -> raise the pelvis
            lo = mid
        else:
            hi = mid
    par.Z_TD = 0.5 * (lo + hi)
    return par.Z_TD


def stance_knee_peak(par):
    """largest knee flexion of the right leg in the stance (half frame steps from the touchdown to the toe off)"""
    return max(probe(k * 0.5, par)['R'][1] for k in range(int(par.PH_TO * NF * 2.0) + 1))


def fit_z_ms(par, kn_ms):
    """hips height at touchdown / toe off such that the knee flexion peaks at kn_ms degrees in the stance"""
    lo, hi = 0.60, 1.05
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        par.Z_TD = mid
        if stance_knee_peak(par) > kn_ms:                            # too bent -> raise the pelvis
            lo = mid
        else:
            hi = mid
    par.Z_TD = 0.5 * (lo + hi)
    return par.Z_TD


def fit_run():
    """A_HS (how far ahead of the hip the ankle lands) such that the knee has KN_TO degrees of flexion at toe off, and Z_TD (hips height at
    touchdown / toe off) such that the knee has KN_TD degrees at touchdown (KN_MS = 0) or peaks at KN_MS degrees in the stance (KN_MS > 0).
    The pelvis curve around Z_TD is the physical one (see pelvis_z): lowest at mid stance, highest in the middle of the flight."""
    global GAIT

    def fit_z():
        return fit_z_ms(P, P.KN_MS) if P.KN_MS > 0.0 else fit_z_td(P, P.KN_TD)

    if P.A_FIT:
        lo, hi = 0.02, 0.55
        for _ in range(22):
            a = 0.5 * (lo + hi)
            P.A_HS = a
            GAIT = Gait(a)
            fit_z()
            k_to = probe(P.PH_TO * NF - 1e-3, P)['R'][1]
            if k_to > P.KN_TO:                                       # too bent at toe off -> land closer to the hip
                hi = a
            else:
                lo = a
        P.A_HS = 0.5 * (lo + hi)
    GAIT = Gait(P.A_HS)
    fit_z()
    mets = [probe(k / 4.0, P) for k in range(NF * 4)]
    ext_max = max(max(o['R'][0], o['L'][0]) for o in mets)
    st = [o['R'][1] for k, o in enumerate(mets) if k / (4.0 * NF) <= P.PH_TO]
    th = [o['R'][5] for o in mets]
    zs = [pelvis_z(k / (4.0 * NF), P) for k in range(NF * 4)]
    to_ = probe(P.PH_TO * NF - 1e-3, P)['R']
    return ('fit: the ankle lands %.3f m ahead of the hip, hips %.4f m high at touchdown / toe off; knee flexion: touchdown %.1f, stance maximum %.1f, '
            'toe off %.1f deg; thigh %.1f .. %+.1f deg, ankle joint at toe off %+.1f; pelvis %.4f .. %.4f m (%.1f mm); largest leg extension %.4f' % (
                P.A_HS, P.Z_TD, mets[0]['R'][1], max(st), to_[1], min(th), max(th), to_[6], min(zs), max(zs), 1000.0 * (max(zs) - min(zs)), ext_max))


TRACE = len(argv) > 2 and argv[2] == 'trace'
if TRACE:
    log(fit_run())
    log('frame  phi   pelvis  | R ankle (y, z)    pitch  thigh  knee  ankle | L: knee  thigh  ankle   | pitch step')
    prev_th = None
    for k in range(NF * 2):
        f_ = k / 2.0
        o_ = probe(f_, P)
        r_, l_ = o_['R'], o_['L']
        y_, z_, th_, tau_ = GAIT.state(f_ / NF)
        step_ = '' if prev_th is None else '%+5.1f' % (math.degrees(th_ - prev_th) * 2.0)          # half frame steps -> degrees per frame
        log('%5.1f  %.3f  %.4f | (%+.3f, %.3f)  %+5.1f  %+5.1f  %5.1f  %+5.1f | %5.1f  %+5.1f  %+5.1f | %s' % (
            f_, f_ / NF, pelvis_z(f_ / NF, P), r_[2].y, r_[2].z, math.degrees(th_), r_[5], r_[1], r_[6], l_[1], l_[5], l_[6], step_))
        prev_th = th_
    sys.exit(0)


# ================================================================== build
log('--- build: stride %.3f m, cycle %d frames (%.3f s), speed %.2f m/s, %d steps / min' % (VT, NF, T_CYCLE, P.SPEED, 120.0 / T_CYCLE))
scene.frame_start = 0
scene.frame_end = NF

# ------------------------------------------------------------------ 1. gait design: ankle placement + pelvis height
FIT_REPORT = fit_run()
log(FIT_REPORT)
kn_table = []
for f_ in range(NF):
    o_ = probe(f_, P)
    kn_table.append((o_['R'][1], o_['L'][1], o_['R'][0], o_['L'][0], 0.0))
kn_mid = max(k_[0] for i_, k_ in enumerate(kn_table) if i_ / NF <= P.PH_TO)
log('knee flexion of the right leg: stance maximum %.1f deg, swing maximum %.1f deg' % (kn_mid, max(k_[0] for k_ in kn_table)))


# ------------------------------------------------------------------ 2. keyframes
ACTION_NAME = ['Yoru_Sprint_r6_work']


def build_action(par=P):
    if arm.animation_data and arm.animation_data.action:
        old_action = arm.animation_data.action
        arm.animation_data.action = None
        if not old_action.name.startswith('Yoru_Sprint_r') or old_action.name == 'Yoru_Sprint_r6_work':
            bpy.data.actions.remove(old_action)                      # a finished variant stays in the file
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
        arm.animation_data.action.name = ACTION_NAME[0]
        arm.animation_data.action.use_fake_user = True
        set_linear(arm.animation_data.action)
    return max_deficit, frames_data


def arm_numbers(par=P, frames=None):
    """per frame and side: upper arm swing (deg from the plumb line, + = forward, world side view), elbow flexion (3d), abduction, wrist bend,
    barrel angle below the horizontal, wrist / palm / elbow positions (m) and the hand position in the frame of the upper chest"""
    out = []
    for f in (range(NF) if frames is None else frames):
        Q_, hl_, D_, dg_, hd_ = compute_pose(f, par)
        Pp_ = dg_['Pp']
        row = {}
        for side in ('L', 'R'):
            sx = 1.0 if side == 'R' else -1.0
            S, K, W = Pp_[nm(side, 'UpperArm')], Pp_[nm(side, 'LowerArm')], Pp_[nm(side, 'Hand')]
            u, fo = (K - S).normalized(), (W - K).normalized()
            hd = D_[nm(side, 'Hand')] @ Vector((sx, 0.0, 0.0))
            top = D_[nm(side, 'Hand')] @ Vector((0.0, 1.0, 0.0))
            nrm = D_[nm(side, 'Hand')] @ Vector((0.0, 0.0, -1.0))
            palm = W + hd * GRIP_AT[0] + top * GRIP_AT[1] + nrm * GRIP_AT[2]
            muzzle = palm + hd * 0.16
            dc = D_[H['upperChest']]
            hc = dc.inverted() @ (palm - Pp_[H['upperChest']])
            row[side] = dict(sig_w=math.degrees(math.atan2(u.y, -u.z)), elbow=math.degrees(u.angle(fo)), alpha=dg_['arm_' + side]['alpha'],
                             wrist=dg_['arm_' + side]['wrist'], wrist_want=dg_['arm_' + side]['wrist_want'],
                             barrel_below=math.degrees(math.asin(max(-1.0, min(1.0, -hd.z)))),
                             barrel_yaw=math.degrees(math.atan2(-sx * hd.x, hd.y)), cant=math.degrees(math.atan2(-sx * top.x, top.z)),
                             barrel_fwd=math.degrees(math.atan2(hd.y, -hd.z)), barrel_out=math.degrees(math.atan2(sx * hd.x, -hd.z)),
                             W=W.copy(), K=K.copy(), palm=palm, muzzle=muzzle, hand_chest=hc, S=S.copy())
        row['hips'] = Pp_[H['hips']].copy()
        out.append(row)
    return out


def arm_summary(rows, label):
    def rng(key, side, fn=lambda v: v):
        vs = [fn(r[side][key]) for r in rows]
        return min(vs), max(vs)
    lines = []
    for side in ('L', 'R'):
        lines.append('%s %s: upper arm %+.1f..%+.1f deg (world), elbow %.1f..%.1f, abduction %.1f..%.1f, wrist %.1f..%.1f (wanted up to %.1f), '
                     'barrel %.1f..%.1f deg below level (from straight down: fwd %.1f..%.1f, out %.1f..%.1f), barrel yaw in %.1f..%.1f, cant %.1f..%.1f; palm z %.3f..%.3f, palm y-hips %.3f..%.3f, '
                     'palm |x| %.3f..%.3f, elbow |x| %.3f..%.3f, elbow z %.3f..%.3f; palm travel in chest frame %.0f mm (y) %.0f mm (z)' % (
                         label, side, *rng('sig_w', side), *rng('elbow', side), *rng('alpha', side), *rng('wrist', side), rng('wrist_want', side)[1],
                         *rng('barrel_below', side), *rng('barrel_fwd', side), *rng('barrel_out', side), *rng('barrel_yaw', side), *rng('cant', side),
                         *rng('palm', side, lambda v: v.z), *[a - b for a, b in zip(rng('palm', side, lambda v: v.y), (0.0, 0.0))],
                         *rng('palm', side, lambda v: abs(v.x)), *rng('K', side, lambda v: abs(v.x)), *rng('K', side, lambda v: v.z),
                         1000.0 * (rng('hand_chest', side, lambda v: v.y)[1] - rng('hand_chest', side, lambda v: v.y)[0]),
                         1000.0 * (rng('hand_chest', side, lambda v: v.z)[1] - rng('hand_chest', side, lambda v: v.z)[0])))
    return lines


def body_numbers(par=P):
    """the quantities of sprint_measure.py, computed from the pose solver (no mesh): lean hips->neck, pelvis bounce, head sideways, shoulder and
    pelvis turn / roll, knee, elbow inner angle, upper arm swing, hand height against the shoulder"""
    rows = []
    for f in range(NF):
        Q_, hl_, D_, dg_, hd_ = compute_pose(f, par)
        Pp_ = dg_['Pp']
        g_ = lambda k: Pp_[k]
        hips, neck, head = g_(H['hips']), g_(H['neck']), g_(H['head'])
        sl, sr = g_(nm('L', 'UpperArm')), g_(nm('R', 'UpperArm'))
        ll, lr = g_(nm('L', 'UpperLeg')), g_(nm('R', 'UpperLeg'))
        fm_ = 0.5 * (g_(nm('L', 'Foot')) + g_(nm('R', 'Foot')))
        hb_ = D_[H['head']] @ Vector((0.0, 0.0, 1.0))
        r = {'lean': math.degrees(math.atan2((neck - hips).y, (neck - hips).z)), 'hips_z': hips.z, 'head_x': head.x,
             'shoulder_roll': math.degrees(math.atan2((sr - sl).z, (sr - sl).x)),
             'neck_tilt': math.degrees(math.atan2((head - neck).y, (head - neck).z)), 'head_pitch': math.degrees(math.atan2(hb_.y, hb_.z)),
             'head_fwd': 100.0 * (head.y - hips.y), 'body_lean': math.degrees(math.atan2((head - fm_).y, (head - fm_).z)),
             'shoulder_yaw': math.degrees(math.atan2((sr - sl).y, (sr - sl).x)), 'pelvis_yaw': math.degrees(math.atan2((lr - ll).y, (lr - ll).x)),
             'pelvis_roll': math.degrees(math.atan2((lr - ll).z, (lr - ll).x)), 'knee': dg_['knee_R']}
        uc_ = g_(H['upperChest'])                                    # r6b: how the rounding is shared (side view, + = forward)
        r['back_lo'] = math.degrees(math.atan2((uc_ - hips).y, (uc_ - hips).z))
        r['back_hi'] = math.degrees(math.atan2((neck - uc_).y, (neck - uc_).z))
        r['sh_y_hips'] = 0.5 * (sl.y + sr.y) - hips.y                # shoulder joints against the hips joint (m)
        r['sh_z_hips'] = 0.5 * (sl.z + sr.z) - hips.z
        r['bend_lo'] = math.degrees(math.atan2((uc_ - hips).x, (uc_ - hips).z))    # seen from behind: side bend of the lower / upper back, neck
        r['bend_hi'] = math.degrees(math.atan2((neck - uc_).x, (neck - uc_).z))
        r['bend_nk'] = math.degrees(math.atan2((head - neck).x, (head - neck).z))
        dci_ = D_[H['upperChest']].inverted()                        # right shoulder joint in the frame of the upper chest: glide (y), shrug (z)
        shc_ = dci_ @ (sr - uc_)
        r['sh_glide'], r['sh_shrug'] = shc_.y, shc_.z
        ua, la, hd = g_(nm('R', 'UpperArm')), g_(nm('R', 'LowerArm')), g_(nm('R', 'Hand'))
        r['elbow'] = math.degrees((ua - la).angle(hd - la))
        v = la - ua
        r['uarm'] = math.degrees(math.atan2(v.y, -v.z))
        r['hand_z'] = hd.z - ua.z
        rows.append(r)
    mm = lambda k: (min(r[k] for r in rows), max(r[k] for r in rows))
    out = {k: mm(k) for k in rows[0]}
    mean_ = lambda k: sum(r[k] for r in rows) / NF
    log('HEAD neck_tilt %.1f..%.1f (mean %.2f) | head_pitch %.1f..%.1f (mean %.1f) | head ahead of the pelvis %.1f..%.1f cm (mean %.1f) | body_lean %.1f..%.1f (mean %.1f)' % (
        out['neck_tilt'][0], out['neck_tilt'][1], mean_('neck_tilt'), out['head_pitch'][0], out['head_pitch'][1], mean_('head_pitch'), out['head_fwd'][0], out['head_fwd'][1],
        mean_('head_fwd'), out['body_lean'][0], out['body_lean'][1], mean_('body_lean')))
    log('BACK lower back hips->upper chest mean %.2f | upper back upper chest->neck mean %.2f | shoulders against the hips: y %.3f, z %.3f m (mean)' % (
        mean_('back_lo'), mean_('back_hi'), mean_('sh_y_hips'), mean_('sh_z_hips')))
    log('BEND seen from behind, p2p: lower back %.2f | upper back %.2f | neck->head %.2f deg | right shoulder in the chest frame p2p: glide %.1f mm, shrug %.1f mm' % (
        out['bend_lo'][1] - out['bend_lo'][0], out['bend_hi'][1] - out['bend_hi'][0], out['bend_nk'][1] - out['bend_nk'][0],
        1000.0 * (out['sh_glide'][1] - out['sh_glide'][0]), 1000.0 * (out['sh_shrug'][1] - out['sh_shrug'][0])))

    def corr_(a, b):
        ma, mb = mean_(a), mean_(b)
        sab = sum((r[a] - ma) * (r[b] - mb) for r in rows)
        return sab / max(1e-12, math.sqrt(sum((r[a] - ma) ** 2 for r in rows) * sum((r[b] - mb) ** 2 for r in rows)))
    log('SHOULDER correlation with the right upper arm swing (+ = forward): glide %+.2f, shrug %+.2f' % (corr_('sh_glide', 'uarm'), corr_('sh_shrug', 'uarm')))
    return ('lean %.1f..%.1f (mean %.2f) | hips_z p2p %.1f cm | head_x p2p %.2f cm | shoulder yaw p2p %.2f | shoulder roll p2p %.2f | pelvis yaw p2p %.1f | pelvis roll p2p %.1f | '
            'knee %.0f..%.0f | elbow inner %.0f..%.0f | upper arm %.0f..%.0f | hand z - shoulder %.2f..%.2f' % (
                out['lean'][0], out['lean'][1], sum(r['lean'] for r in rows) / NF, 100 * (out['hips_z'][1] - out['hips_z'][0]),
                100 * (out['head_x'][1] - out['head_x'][0]), out['shoulder_yaw'][1] - out['shoulder_yaw'][0],
                out['shoulder_roll'][1] - out['shoulder_roll'][0], out['pelvis_yaw'][1] - out['pelvis_yaw'][0],
                out['pelvis_roll'][1] - out['pelvis_roll'][0], out['knee'][0], out['knee'][1], out['elbow'][0], out['elbow'][1], out['uarm'][0], out['uarm'][1],
                out['hand_z'][0], out['hand_z'][1]))


if DESIGN_ONLY:
    for vk in VARIANTS:
        P.variant = vk
        log('BODY %s: %s' % (vk, body_numbers(P)))
        for ln in arm_summary(arm_numbers(P), vk):
            log(ln)
    sys.exit(0)

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


KEYED = [n for n in order if n in hum_names or n in EXTRA]


def set_pose(f, par=P):
    """puts the armature into the pose of frame f without keys (the action is taken off): for the fits that measure the mesh in many poses"""
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action = None
    Q, hips_loc, D, diag, hips_d = compute_pose(f, par)
    for n in KEYED:
        pb = arm.pose.bones[n]
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Q[n]
    arm.pose.bones[H['hips']].location = hips_loc
    bpy.context.view_layer.update()


def clearance_now():
    """clearance (m) of the left and the right arm against the gear (torso, thighs, bust) in the pose that is set"""
    dg, co = evaluated_coords()
    kd = KDTree(len(torso_idx) + len(thigh_idx))
    for i, vi in enumerate(torso_idx + thigh_idx):
        kd.insert(co[vi], i)
    kd.balance()
    out = {'L': 9.0, 'R': 9.0}
    for pnt, r, side, part in arm_points(dg):
        _, _, dist = kd.find(pnt)
        out[side] = min(out[side], dist - r)
    return out


def smooth_envelope(need, rate):
    """smallest periodic curve above `need` whose slope never exceeds `rate` per sample (a cone is put under every sample), then softened with a
    binomial filter and lifted again by the largest shortfall"""
    n = len(need)
    cone = [max(need[(i + k) % n] - rate * abs(k) for k in range(-n // 2, n // 2 + 1)) for i in range(n)]
    soft = [(cone[(i - 2) % n] + 4.0 * cone[(i - 1) % n] + 6.0 * cone[i] + 4.0 * cone[(i + 1) % n] + cone[(i + 2) % n]) / 16.0 for i in range(n)]
    lift = max(0.0, max(need[i] - soft[i] for i in range(n)))
    return [s + lift for s in soft]


def fit_arm_hang(par=P):
    """fits the outward angle of the upper arm per phase of the arm swing against the gear.  Every frame is posed with a growing hang angle (the
    same on both arms) until the arm clears the gear by ARM_WANT; the left arm at frame j and the right arm at frame j + NF/2 are at the same phase of
    the swing, the larger need counts.  The table is made smooth (hang_rate) and checked on every frame."""
    half = NF // 2
    need = [par.hang_in] * NF
    for j in range(NF):
        a = par.hang_in
        done = {'L': False, 'R': False}
        while True:
            par.hang_tab = [a] * NF
            set_pose(j, par)
            c = clearance_now()
            for sd in ('L', 'R'):
                if not done[sd] and (c[sd] >= par.ARM_WANT or a >= par.hang_max):
                    ph = j if sd == 'L' else (j + half) % NF
                    need[ph] = max(need[ph], a)
                    done[sd] = True
            if done['L'] and done['R']:
                break
            a += 1.0
    par.hang_tab = [t + par.hang_add for t in smooth_envelope(need, par.hang_rate)]
    for attempt in range(8):
        worst = 9.0
        for j in range(NF):
            set_pose(j, par)
            c = clearance_now()
            worst = min(worst, c['L'], c['R'])
        log('arm hang fit %d: clearance %.4f m over all frames (wanted %.4f)' % (attempt, worst, par.ARM_WANT))
        if worst >= par.ARM_WANT - 0.0015:
            break
        par.hang_tab = [t + 0.8 for t in par.hang_tab]
    log('arm hang (outward angle of the upper arm per phase of the swing, 0 = furthest forward): ' + ' '.join('%.1f' % t for t in par.hang_tab))


# ------------------------------------------------------------------ SPRINT r1: placeholder pistols + EXACT clearance of arms and pistols (BVH)
from mathutils.bvhtree import BVHTree
import numpy as np


def make_pistol(name):
    """PLATZHALTER_Pistole: boxes, local +Y = barrel, +Z = top (thumb side), origin = centre of the grip (it lies in the closed hand)"""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()

    def box(c, s, rx=0.0):
        m = Matrix.Translation(c) @ Euler((deg(rx), 0, 0)).to_matrix().to_4x4() @ Matrix.Diagonal((s[0], s[1], s[2], 1.0))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    box((0.0, 0.060, 0.060), (0.028, 0.190, 0.032))                  # slide
    box((0.0, 0.150, 0.0795), (0.008, 0.010, 0.007))                 # front sight
    box((0.0, 0.085, 0.036), (0.024, 0.140, 0.018))                  # frame / dust cover
    box((0.0, 0.044, 0.004), (0.010, 0.052, 0.007))                  # trigger guard, bottom bar
    box((0.0, 0.068, 0.017), (0.010, 0.007, 0.030))                  # trigger guard, front bar
    box((0.0, 0.032, 0.020), (0.006, 0.006, 0.020), rx=15.0)         # trigger
    box((0.0, -0.004, 0.000), (0.026, 0.044, 0.100), rx=-17.0)       # grip, 17 deg to the barrel
    box((0.0, -0.020, -0.052), (0.027, 0.046, 0.010), rx=-17.0)      # magazine base plate
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(name + '_mat')
    mat.use_nodes = True
    bsdf = next(n_ for n_ in mat.node_tree.nodes if n_.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (0.16, 0.17, 0.19, 1.0)  # gunmetal, a shade lighter than the black outfit so it reads
    bsdf.inputs['Metallic'].default_value = 0.55
    bsdf.inputs['Roughness'].default_value = 0.38
    ob.data.materials.append(mat)
    return ob


def attach_pistols():
    """the pistols hang on the hand bones (child of bone): placed once in the rest pose from the hand's rest frame and GRIP_AT, so they follow
    every action without keys"""
    ad_ = arm.animation_data
    keep = ad_.action if ad_ else None
    if ad_:
        ad_.action = None
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
        pb.scale = Vector((1.0, 1.0, 1.0))
    bpy.context.view_layer.update()
    out = {}
    for side in ('L', 'R'):
        sx = 1.0 if side == 'R' else -1.0
        F, U, N = Vector((sx, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, -1.0))
        Xa = F.cross(U)
        M = Matrix((Xa, F, U)).transposed().to_4x4()
        M.translation = HEAD0[nm(side, 'Hand')] + F * GRIP_AT[0] + U * GRIP_AT[1] + N * GRIP_AT[2]
        ob = make_pistol('PLATZHALTER_Pistole_' + side)
        ob.parent = arm
        ob.parent_type = 'BONE'
        ob.parent_bone = nm(side, 'Hand')
        bpy.context.view_layer.update()
        ob.matrix_world = arm.matrix_world @ M
        bpy.context.view_layer.update()
        out[side] = ob
    if ad_ and keep:
        ad_.action = keep
    return out


PISTOLS = attach_pistols()
log('pistols attached to the hand bones:', ', '.join(o.name for o in PISTOLS.values()))

dom_of = []                                                          # dominant bone per vertex
for v in body.data.vertices:
    dom_of.append(vg_names.get(max(v.groups, key=lambda g: g.weight).group, '') if v.groups else '')
_solid = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg'], H['leftLowerLeg'], H['rightLowerLeg']}
_inv = invisible_polygons()
gear_v = set(i for i, n_ in enumerate(dom_of) if VIS[i] and (n_ in _solid or (n_.startswith('J_Sec_') and 'Hair' not in n_)))
GEAR_POLYS = [list(p.vertices) for p in body.data.polygons if p.index not in _inv and all(v_ in gear_v for v_ in p.vertices)]
ARM_PARTS = {}
for side in ('L', 'R'):
    hand_set = {nm(side, 'Hand')} | {nm(side, f_ + p_) for f_ in ('Index', 'Middle', 'Ring', 'Little', 'Thumb') for p_ in PARTS}
    for part, bset in (('UpperArm', {nm(side, 'UpperArm')}), ('LowerArm', {nm(side, 'LowerArm')}), ('Hand', hand_set)):
        polys = [list(p.vertices) for p in body.data.polygons if p.index not in _inv and all(dom_of[v_] in bset and VIS[v_] for v_ in p.vertices)]
        ARM_PARTS[(side, part)] = (polys, sorted({v_ for pl in polys for v_ in pl}))
log('clearance sets: gear polygons %d; arm parts %s' % (len(GEAR_POLYS), {'%s %s' % k: len(v[0]) for k, v in ARM_PARTS.items()}))
NV = len(body.data.vertices)
VIS_POLYS_IDX = [p.index for p in body.data.polygons if p.index not in _inv and all(VIS[v_] for v_ in p.vertices)]
VIS_POLYS = [list(body.data.polygons[i].vertices) for i in VIS_POLYS_IDX]


def body_coords():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    arr = np.empty(NV * 3, dtype=np.float64)
    me.vertices.foreach_get('co', arr)
    ev.to_mesh_clear()
    mw = body.matrix_world
    arr = arr.reshape(NV, 3)
    if mw != Matrix.Identity(4):
        arr = arr @ np.array(mw.to_3x3()).T + np.array(mw.translation)
    return [Vector(c) for c in arr]


def pistol_geometry(side):
    ob = PISTOLS[side]
    mw = ob.matrix_world
    co = [mw @ v.co for v in ob.data.vertices]
    polys = [list(p.vertices) for p in ob.data.polygons]
    samples = list(co)
    for p in ob.data.polygons:                                       # a 4 x 4 grid on every face (the boxes are coarse)
        vs = [co[i] for i in p.vertices]
        for a_ in (0.125, 0.375, 0.625, 0.875):
            for b_ in (0.125, 0.375, 0.625, 0.875):
                samples.append(vs[0].lerp(vs[1], a_).lerp(vs[3].lerp(vs[2], a_), b_))
    return co, polys, samples


def clearance_exact(t_min=0.8):
    """for the pose that is set: per side the triangle pairs that cut through the gear (upper arm beyond t_min of its length, forearm, hand,
    pistol), the smallest distance (m) of forearm / hand and of the pistol to the gear surface (they must keep CLEAR), the smallest distance of the
    upper arm (it may rest on the side of the vest, it must not cut through), and pistol against the other arm and pistol"""
    from mathutils.geometry import intersect_point_line
    co = body_coords()
    gear = BVHTree.FromPolygons(co, GEAR_POLYS, all_triangles=False)
    pbs = arm.pose.bones
    res = {}
    pist = {s: pistol_geometry(s) for s in ('L', 'R')}
    pbvh = {s: BVHTree.FromPolygons(pist[s][0], pist[s][1], all_triangles=False) for s in ('L', 'R')}
    abvh = {}
    for side in ('L', 'R'):
        sh = arm.matrix_world @ pbs[nm(side, 'UpperArm')].head
        el = arm.matrix_world @ pbs[nm(side, 'LowerArm')].head
        r = {'cut': 0, 'cut_part': None, 'min': 9.0, 'min_part': None, 'up_min': 9.0}
        for part in ('UpperArm', 'LowerArm', 'Hand'):
            polys, vids = ARM_PARTS[(side, part)]
            if part == 'UpperArm':
                polys = [pl for pl in polys if intersect_point_line(co[pl[0]], sh, el)[1] > t_min]
                vids = sorted({v_ for pl in polys for v_ in pl})
            if not polys:
                continue
            tb = BVHTree.FromPolygons(co, polys, all_triangles=False)
            abvh[(side, part)] = tb
            pairs_ = tb.overlap(gear)
            n_cut = len(pairs_)
            if n_cut > r['cut']:
                gb_ = {}
                for ia_, ib_ in pairs_:
                    k_ = dom_of[GEAR_POLYS[ib_][0]]
                    gb_[k_] = gb_.get(k_, 0) + 1
                r['cut'], r['cut_part'] = n_cut, (part, gb_, tuple(round(x, 3) for x in co[GEAR_POLYS[pairs_[0][1]][0]]))
            for v_ in vids:
                hit = gear.find_nearest(co[v_])
                if hit[0] is None:
                    continue
                if part == 'UpperArm':
                    r['up_min'] = min(r['up_min'], hit[3])
                elif hit[3] < r['min']:
                    r['min'], r['min_part'] = hit[3], (part, dom_of[v_], tuple(round(x, 3) for x in co[v_]))
        # pistol against the gear
        n_cut = len(pbvh[side].overlap(gear))
        r['pistol_cut'] = n_cut
        r['pistol_min'], r['pistol_where'] = 9.0, None
        for s_ in pist[side][2]:
            hit = gear.find_nearest(s_)
            if hit[0] is not None and hit[3] < r['pistol_min']:
                r['pistol_min'], r['pistol_where'] = hit[3], tuple(round(x, 3) for x in s_)
        res[side] = r
    # pistols against the other side's pistol and arm
    for side, other in (('L', 'R'), ('R', 'L')):
        n_cut = len(pbvh[side].overlap(pbvh[other]))
        for part in ('LowerArm', 'Hand'):
            if (other, part) in abvh:
                n_cut += len(pbvh[side].overlap(abvh[(other, part)]))
        dmin = min((pbvh[other].find_nearest(s_)[3] for s_ in pist[side][2]), default=9.0)
        res[side]['pistol_other_cut'], res[side]['pistol_other_min'] = n_cut, dmin
    return res


def side_ok(r, need=None):
    need = P.CLEAR if need is None else need
    return (r['cut'] == 0 and r['min'] >= need and r['pistol_cut'] == 0 and r['pistol_min'] >= need and r['pistol_other_cut'] == 0
            and r['pistol_other_min'] >= need)


def fit_arm_alpha(par=P, step=1.5):
    """abduction of the upper arm per side and frame: the smallest alpha (from the variant's alpha0 on) at which arm and pistol keep CLEAR from
    the body and gear; then a smooth periodic envelope (slope <= 1.2 deg per frame) and a check of every frame"""
    V = VARIANTS[par.variant]
    need = {'L': [V['alpha0']] * NF, 'R': [V['alpha0']] * NF}
    stuck = []
    for j in range(NF):
        cur = {'L': V['alpha0'], 'R': V['alpha0']}
        while True:
            par.alpha_tab = {s: [cur[s]] * NF for s in ('L', 'R')}
            set_pose(j, par)
            c = clearance_exact()
            bad = [s for s in ('L', 'R') if not side_ok(c[s]) and cur[s] < par.alpha_max]
            for s in ('L', 'R'):
                if not side_ok(c[s]) and cur[s] >= par.alpha_max:
                    stuck.append((j, s, round(c[s]['min'] * 1000, 1), c[s]['min_part'], round(c[s]['pistol_min'] * 1000, 1), c[s]['pistol_where']))
            if not bad:
                break
            for s in bad:
                cur[s] += step
        need['L'][j], need['R'][j] = cur['L'], cur['R']
    par.alpha_tab = {s: smooth_envelope(need[s], 0.8) for s in ('L', 'R')}
    for attempt in range(6):
        worst = {'L': [], 'R': []}
        for j in range(NF):
            set_pose(j, par)
            c = clearance_exact()
            for s in ('L', 'R'):
                if not side_ok(c[s]):
                    worst[s].append(j)
        if not worst['L'] and not worst['R']:
            break
        for s in ('L', 'R'):
            if worst[s]:
                par.alpha_tab[s] = [min(par.alpha_max, t + 0.8) for t in par.alpha_tab[s]]
    log('variant %s: abduction fitted L %.1f..%.1f R %.1f..%.1f deg (start %.1f); frames that still fail after the fit: L %s R %s; stuck at the limit: %s' % (
        par.variant, min(par.alpha_tab['L']), max(par.alpha_tab['L']), min(par.alpha_tab['R']), max(par.alpha_tab['R']), V['alpha0'],
        worst['L'], worst['R'], stuck[:6]))
    return worst


CHECK_ONLY = len(argv) > 2 and argv[2] == 'check'
if CHECK_ONLY:                                                       # measure the variants at their start values only (no fit), every 3rd frame
    for vk in VARIANTS:
        P.variant = vk
        P.alpha_tab = None
        for j in range(0, NF, 3):
            set_pose(j, P)
            c = clearance_exact()
            log('check %s frame %2d: ' % (vk, j) + ' | '.join('%s arm cut %d %s min %.1f mm %s; pistol cut %d min %.1f mm at %s; other %d %.1f mm' % (
                s, c[s]['cut'], c[s]['cut_part'], c[s]['min'] * 1000, c[s]['min_part'], c[s]['pistol_cut'], c[s]['pistol_min'] * 1000, c[s]['pistol_where'],
                c[s]['pistol_other_cut'], c[s]['pistol_other_min'] * 1000) for s in ('L', 'R')))
    sys.exit(0)

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


def tail_amp(span, i):
    """wave amplitude (deg) of tail joint i (0-based): grows linearly from span[0] at the base to span[1] at joint 6; the zero-length joints 7 and 8
    carry the tip on without bending it"""
    return span[0] + (span[1] - span[0]) * i / 5.0 if i < 6 else 0.0


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
        out.append([(-tail_amp(par.tail_vert, i) * vl[k], -tail_amp(par.tail_lat, i) * yl[k]) for k in range(n)])
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
        log('tail: travelling waves, lateral %.1f .. %.1f deg and vertical %.1f .. %.1f deg per joint (base to joint 6), phase offset %.2f rad per joint' % (
            par.tail_lat + par.tail_vert + (par.tail_dphi,)))
        return tail, ears
    dyn = []
    w_prev = psi
    zbar = sum(zs) / n
    p_prev = [-par.hips_lean + 90.0 * (zs[k] - zbar) for k in range(n)]   # vertical bob of the tail root in degrees
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
        next = current + (current - previous) * (1 - drag) + parent rotation * rest axis * stiffness * dt + (gravity + wind) * dt,
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
    # external push per bone (UniVRM: gravity direction x power): gravity plus the headwind of the run on hair and ears, backwards (she runs towards +Y) and a
    # little up; the bust is not blown
    wind = np.zeros((N, 3))
    for i in range(N):
        w_ = {'Hair': par.wind_hair, 'CatEar': par.wind_ear}.get(kind[i], 0.0)
        wind[i] = (0.0, -w_, w_ * par.wind_lift)
    grav = (np.array([0.0, 0.0, -par.spring_gravity]) + wind) * dt
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
                nx = cu + (cu - pv) * (1.0 - drag[d_idx])[:, None] + a_w * (stiff[d_idx] * dt)[:, None] + grav[d_idx]
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
    for _ in range(par.spring_smooth):                                         # [1 2 1] / 4 along the frames (zero phase): takes the sharpest corners off the impacts
        rec_dir = 0.25 * np.roll(rec_dir, 1, axis=0) + 0.5 * rec_dir + 0.25 * np.roll(rec_dir, -1, axis=0)
        rec_dir /= np.linalg.norm(rec_dir, axis=2, keepdims=True)
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
with open(os.path.join(PARTS_DIR, 'Yoru_Sprint_r6_%s_tail.json' % LV), 'w') as f:
    json.dump({'restPitch': tail_rest, 'lift': P.tail_lift, 'runRestPitch': tail_walk_rest,
               'runAbsoluteAngles': [round(a + (P.tail_lift if i < 2 else 0.0), 1) for i, a in enumerate(P.tail_abs)] if (P.spec and P.tail_mode == 'wave') else None}, f)


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
        track.setdefault((side, 'joint'), []).append(arm.evaluated_get(dg).pose.bones[nm(side, 'Toes')].head.copy())
        low_z[side].append(min(co[vi].z for vi in shoe_idx[side]))

step = VT / NF
report = {}
for side in ('L', 'R'):
    off = 0.0 if side == 'R' else 0.5
    for name, lo, hi in (('ball', 0.005, P.PH_TO - 0.005), ('tip', 0.005, P.PH_TO - 0.005), ('joint', 0.005, P.PH_TO - 0.005)):      # the heel is up from the touchdown on
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
            fit_run()
            build_action(P)
            ov_, mn_ = leg_overlap(list(range(0, NF, 2)))
            log('  BASE %.3f CIRC %.3f -> overlap pairs %3d (frame %s), closest %.1f mm (frame %s) %s' % (base_, circ_, ov_[0], ov_[1], mn_[0] * 1000.0, mn_[1],
                ('overlap at z %.2f..%.2f, x %.3f..%.3f' % LEG_OVERLAP_INFO[0][1:]) if (ov_[0] and LEG_OVERLAP_INFO[0]) else ''))
    sys.exit(0)

w_ov, w_min = leg_overlap(list(range(NF)))
log('legs: overlapping triangle pairs max %d (frame %s), closest vertices of the two legs below z 0.70: %.1f mm (frame %s)' % (
    w_ov[0], w_ov[1], w_min[0] * 1000.0, w_min[1]))

# ------------------------------------------------------------------ 5c. run report: the numbers of the finished animation, measured on the keys
STEP_LIMIT, CHANGE_LIMIT = 8.0, 6.0                                   # degrees per frame: largest world rotation of a bone between two frames, largest change of that rotation


def rot_vector(q_from, q_to):
    """world rotation vector (axis x angle, degrees) that turns q_from into q_to"""
    d = q_to @ q_from.inverted()
    if d.w < 0.0:
        d = Quaternion((-d.w, -d.x, -d.y, -d.z))
    s = math.sqrt(max(0.0, 1.0 - d.w * d.w))
    if s < 1e-9:
        return Vector((0.0, 0.0, 0.0))
    return Vector((d.x, d.y, d.z)) / s * math.degrees(2.0 * math.acos(min(1.0, d.w)))


def bone_motion(D_all):
    """smoothness of every humanoid bone over the looped cycle: per group (legs, trunk, arms and hands) the largest step between two frames, the largest change
    of that step (angular velocity change per frame), the bones and frames where they occur and how many bones are over the limits.  D_all = world rotation per
    frame and bone (frame 0 .. NF - 1, the cycle loops)."""
    legs = {nm(sd, p) for sd in ('L', 'R') for p in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')}
    trunk = {H[k] for k in ('hips', 'spine', 'chest', 'upperChest', 'neck', 'head')}
    out = {}
    for name in D_all[0]:
        if name in EXTRA or name not in hum_names:
            continue
        qs = [D_all[f][name] for f in range(NF)]
        rv = [rot_vector(qs[i], qs[(i + 1) % NF]) for i in range(NF)]
        step = [v.length for v in rv]
        chg = [(rv[i] - rv[i - 1]).length for i in range(NF)]
        out[name] = (max(step), step.index(max(step)), max(chg), chg.index(max(chg)))
    groups = {'legs': legs, 'trunk': trunk, 'arms and hands': set(out) - legs - trunk}
    res = {}
    for g, names in groups.items():
        ms = max(names, key=lambda n: out[n][0])
        mc = max(names, key=lambda n: out[n][2])
        res[g] = {'step_deg': out[ms][0], 'step_bone': '%s frame %d -> %d' % (ms, out[ms][1], (out[ms][1] + 1) % NF),
                  'change_deg': out[mc][2], 'change_bone': '%s at frame %d' % (mc, out[mc][3]),
                  'bones': len(names), 'over_step_limit': sum(1 for n in names if out[n][0] > STEP_LIMIT),
                  'over_change_limit': sum(1 for n in names if out[n][2] > CHANGE_LIMIT)}
    res['all_bones'] = {n: out[n] for n in out}
    return res


def run_report():
    """measures pelvis, head, spine, knees, thighs, flight, arms and tail on the finished keys; returns a dict and logs it"""
    rep_ = {}
    ang = lambda q, order='XYZ': [math.degrees(a) for a in q.to_euler(order)]
    hip_x, hip_z, head_x, head_z = [], [], [], []
    names = {'hips': H['hips'], 'spine': H['spine'], 'chest': H['chest'], 'upperChest': H['upperChest'], 'neck': H['neck'], 'head': H['head']}
    D_all = []
    for f in range(NF):
        Q_, hips_loc_, D_, diag_, hips_d_ = compute_pose(f, P)
        D_all.append(D_)
        hip_x.append(hips_d_.x)
        hip_z.append(hips_d_.z + HEAD0[H['hips']].z)
    knees = {'R': [], 'L': []}
    thigh = {'R': [], 'L': []}
    ankle_z = {'R': [], 'L': []}
    arm_pitch = {'L': [], 'R': []}
    fore_pitch = {'L': [], 'R': []}
    hand_z = {'L': [], 'R': []}
    hand_x = {'L': [], 'R': []}
    elbow_x = {'L': [], 'R': []}
    tail_ang = [[] for _ in range(8)]
    for f in range(NF):
        scene.frame_set(f)
        ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
        pbs = ae.pose.bones
        head_x.append(pbs[H['head']].head.x)
        head_z.append(pbs[H['head']].head.z)
        for side in ('R', 'L'):
            hp_, kp_, ap_ = pbs[nm(side, 'UpperLeg')].head, pbs[nm(side, 'LowerLeg')].head, pbs[nm(side, 'Foot')].head
            a1_, a2_ = (hp_ - kp_).normalized(), (ap_ - kp_).normalized()
            knees[side].append(180.0 - math.degrees(math.acos(max(-1.0, min(1.0, a1_.dot(a2_))))))
            th_ = kp_ - hp_
            thigh[side].append(math.degrees(math.atan2(th_.y, -th_.z)))               # + = knee ahead of the hip
            ankle_z[side].append(ap_.z)
        for side in ('L', 'R'):
            u_ = pbs[nm(side, 'LowerArm')].head - pbs[nm(side, 'UpperArm')].head
            fo_ = pbs[nm(side, 'Hand')].head - pbs[nm(side, 'LowerArm')].head
            arm_pitch[side].append(math.degrees(math.atan2(u_.y, -u_.z)))
            fore_pitch[side].append(math.degrees(math.atan2(fo_.y, -fo_.z)))
            hand_z[side].append(pbs[nm(side, 'Hand')].head.z)
            hand_x[side].append(abs(pbs[nm(side, 'Hand')].head.x))
            elbow_x[side].append(abs(pbs[nm(side, 'LowerArm')].head.x))
        for j in range(8):
            d_ = D_all[f]['J_Opt_C_CatTail%d_01' % (j + 1)] @ Vector((0.0, -1.0, 0.0))
            tail_ang[j].append(math.degrees(math.atan2(d_.z, -d_.y)))
    rep_['pelvis_z_mm'] = (1000.0 * (min(hip_z) - sum(hip_z) / NF), 1000.0 * (max(hip_z) - sum(hip_z) / NF), 1000.0 * (max(hip_z) - min(hip_z)))
    rep_['pelvis_x_mm'] = 1000.0 * max(abs(v) for v in hip_x)
    rep_['head_x_mm'] = (1000.0 * min(head_x), 1000.0 * max(head_x))
    rep_['head_z_p2p_mm'] = 1000.0 * (max(head_z) - min(head_z))
    eu = {k: [ang(D_all[f][v]) for f in range(NF)] for k, v in names.items()}
    for k in names:
        rep_['%s_rpy_peak' % k] = tuple(max(abs(e[i]) for e in eu[k]) for i in range(3))     # (pitch rx, roll ry, yaw rz) about world X, Y, Z
    chain = ['hips', 'spine', 'chest', 'upperChest']
    for a_, b_ in zip(chain, chain[1:]):
        rel_e = [ang(D_all[f][names[a_]].inverted() @ D_all[f][names[b_]]) for f in range(NF)]
        rep_['%s_vs_%s_rel_roll_yaw' % (b_, a_)] = (max(abs(e[1]) for e in rel_e), max(abs(e[2]) for e in rel_e))

    def ph_(p_):
        return int(round(p_ * NF)) % NF

    st_ids = [i for i in range(NF) if i / NF <= P.PH_TO]
    rep_['knee_touchdown'] = knees['R'][0]
    rep_['knee_stance_max'] = max(knees['R'][i] for i in st_ids)
    rep_['knee_stance_max_phase'] = [i for i in st_ids if knees['R'][i] == rep_['knee_stance_max']][0] / NF
    rep_['knee_toe_off'] = knees['R'][ph_(P.PH_TO)]
    rep_['knee_swing_max'] = max(knees['R'])
    rep_['thigh_range_deg'] = (min(thigh['R']), max(thigh['R']))
    rep_['ankle_z_swing_max'] = max(ankle_z['R'])
    # contact and flight, measured on the shoe mesh (lowest vertex of each shoe)
    contact = {sd: [low_z[sd][f] <= 0.004 for f in range(NF)] for sd in ('L', 'R')}
    flight = [f for f in range(NF) if not contact['L'][f] and not contact['R'][f]]
    both = [f for f in range(NF) if contact['L'][f] and contact['R'][f]]
    rep_['contact_frames_per_foot'] = (sum(contact['R']), sum(contact['L']))
    rep_['flight_frames_per_cycle'] = len(flight)
    rep_['frames_with_both_feet_down'] = len(both)
    for side in ('L', 'R'):
        rep_['upper_arm_pitch_%s' % side] = (min(arm_pitch[side]), max(arm_pitch[side]))
        ef_ = [fore_pitch[side][i] - arm_pitch[side][i] for i in range(NF)]
        rep_['elbow_flexion_%s' % side] = (min(ef_), max(ef_))
        rep_['hand_height_%s' % side] = (min(hand_z[side]), max(hand_z[side]))
        rep_['hand_x_%s' % side] = (min(hand_x[side]), max(hand_x[side]))
        rep_['elbow_x_%s' % side] = (min(elbow_x[side]), max(elbow_x[side]))
    worst_step, worst_name, worst_frame = 0.0, '', 0
    for f in range(NF):
        for k, v in D_all[f].items():
            if k in EXTRA:
                continue
            a_ = math.degrees((D_all[f][k].inverted() @ D_all[(f + 1) % NF][k]).angle)
            a_ = min(a_, 360.0 - a_)                                  # the quaternion sign does not matter
            if a_ > worst_step:
                worst_step, worst_name, worst_frame = a_, k, f
    rep_['largest_rotation_step_deg'] = worst_step
    rep_['largest_rotation_step_bone'] = '%s (frame %d -> %d)' % (worst_name, worst_frame, (worst_frame + 1) % NF)
    rep_['motion'] = bone_motion(D_all)
    rep_['pelvis_height_step_mm'] = 1000.0 * max(abs(hip_z[(f + 1) % NF] - hip_z[f]) for f in range(NF))
    rep_['tail_angle_mean'] = [sum(a) / NF for a in tail_ang]
    rep_['tail_angle_range'] = [(min(a), max(a)) for a in tail_ang]
    log('RUN REPORT')
    log('  pelvis height: %.1f .. +%.1f mm around its mean, peak to peak %.1f mm; sideways shift +-%.1f mm; head bone x %.1f .. %.1f mm, head bob %.1f mm peak to peak' % (
        rep_['pelvis_z_mm'] + (rep_['pelvis_x_mm'],) + rep_['head_x_mm'] + (rep_['head_z_p2p_mm'],)))
    for k in names:
        log('  %-10s peak world rotation: pitch %.1f  roll %.1f  yaw %.1f deg' % ((k,) + rep_['%s_rpy_peak' % k]))
    for a_, b_ in zip(chain, chain[1:]):
        log('  %-10s against %-10s: roll %.1f deg, yaw %.1f deg (relative)' % ((b_, a_) + rep_['%s_vs_%s_rel_roll_yaw' % (b_, a_)]))
    log('  knee (right leg): touchdown %.1f, stance maximum %.1f (at phase %.2f), toe off %.1f, swing maximum %.1f deg; thigh from %.1f (behind) to %+.1f deg (ahead); ankle up to %.2f m high' % (
        rep_['knee_touchdown'], rep_['knee_stance_max'], rep_['knee_stance_max_phase'], rep_['knee_toe_off'], rep_['knee_swing_max'],
        rep_['thigh_range_deg'][0], rep_['thigh_range_deg'][1], rep_['ankle_z_swing_max']))
    log('  contact (lowest shoe vertex <= 4 mm): %d frames per foot of %d, flight (no foot down): %d frames per cycle, both feet down: %d frames' % (
        rep_['contact_frames_per_foot'][0], NF, rep_['flight_frames_per_cycle'], rep_['frames_with_both_feet_down']))
    for side in ('L', 'R'):
        log('  arm %s: upper arm %.1f .. %.1f deg, elbow flexion %.1f .. %.1f deg, hand height %.2f .. %.2f m, elbow x %.3f .. %.3f, hand x %.3f .. %.3f m' % (
            (side,) + rep_['upper_arm_pitch_%s' % side] + rep_['elbow_flexion_%s' % side] + rep_['hand_height_%s' % side] + rep_['elbow_x_%s' % side] + rep_['hand_x_%s' % side]))
    log('  smoothness: largest rotation step of any humanoid bone between two frames %.1f deg (%s), largest pelvis height step %.1f mm per frame' % (
        rep_['largest_rotation_step_deg'], rep_['largest_rotation_step_bone'], rep_['pelvis_height_step_mm']))
    for g in ('legs', 'trunk', 'arms and hands'):
        m_ = rep_['motion'][g]
        log('  motion %-14s (%2d bones): largest step %.1f deg/frame (%s), largest change of the step %.1f deg/frame (%s); over %.0f deg: %d bones, over %.0f deg change: %d bones' % (
            g, m_['bones'], m_['step_deg'], m_['step_bone'], m_['change_deg'], m_['change_bone'], STEP_LIMIT, m_['over_step_limit'], CHANGE_LIMIT, m_['over_change_limit']))
    log('  tail segment direction above horizontal (mean, range): ' + ', '.join(
        '%d: %.0f (%.0f..%.0f)' % (j + 1, rep_['tail_angle_mean'][j], rep_['tail_angle_range'][j][0], rep_['tail_angle_range'][j][1]) for j in range(8)))
    return rep_


SPEC_REPORT = run_report()


def spring_check():
    """the child joints of the keyed spring bones must sit where the simulation put the tails (proves the rotation conversion)"""
    worst = 0.0
    for f in (0, NF // 4, NF // 2, (3 * NF) // 4):
        scene.frame_set(f)
        pbs = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones
        for name, tails in SPRING_REP['tails'].items():
            ch = bones[name].children
            if ch and ch[0].name in P.spring_dirs:
                worst = max(worst, (pbs[ch[0].name].head - Vector(tails[f])).length)
    log('springs: keyed bones follow the simulation to %.2f mm (largest difference of the child joints over 5 frames)' % (worst * 1000.0))
    return worst


SPRING_CHECK = spring_check() if (P.spec and P.spring_on and P.spring_dirs) else None
if P.spring_dirs:                                                    # r5: hair must not chatter (largest turn of a strand bone per frame)
    _st = []
    for _n, _d in P.spring_dirs.items():
        if 'Hair' in _n:
            _st.append((max(math.degrees(_d[i].angle(_d[(i + 1) % NF])) for i in range(NF)), _n))
    _st.sort(reverse=True)
    log('hair: largest strand turn per frame %.1f deg (%s); strands over 8 deg/frame: %d of %d' % (_st[0][0], _st[0][1], sum(1 for a in _st if a[0] > 8.0), len(_st)))


# ------------------------------------------------------------------ SPRINT r1: the three arm variants (legs, trunk, tail and springs are shared)
def variant_checks(vk):
    """error checks of the finished action of a variant: exact clearance on every frame, joint steps, seam, hand path in the chest frame"""
    out = {'clear': {}, 'worst': {}}
    worst = {s: {'min': 9.0, 'up_min': 9.0, 'pistol_min': 9.0, 'pistol_other_min': 9.0, 'cut': 0, 'pistol_cut': 0, 'pistol_other_cut': 0} for s in ('L', 'R')}
    where = {s: None for s in ('L', 'R')}
    up_frames, aim_body = {'L': [], 'R': []}, {'L': [], 'R': []}
    for j in range(NF):
        scene.frame_set(j)
        c = clearance_exact()
        co_ = body_coords()                                          # r2: the barrel never points up and never at her own body
        bb_ = BVHTree.FromPolygons(co_, VIS_POLYS, all_triangles=False)
        for s in ('L', 'R'):
            mw_ = PISTOLS[s].matrix_world
            fwd_ = (mw_.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
            muz_ = mw_ @ Vector((0.0, 0.1525, 0.058))
            if fwd_.z > 0.0:
                up_frames[s].append(j)
            hit_ = bb_.ray_cast(muz_ + fwd_ * 0.005, fwd_, 2.5)
            if hit_[0] is not None:
                aim_body[s].append((j, round(hit_[3], 2), dom_of[body.data.polygons[VIS_POLYS_IDX[hit_[2]]].vertices[0]]))
        for s in ('L', 'R'):
            for k_ in ('min', 'up_min', 'pistol_min', 'pistol_other_min'):
                if c[s][k_] < worst[s][k_]:
                    worst[s][k_] = c[s][k_]
                    if k_ == 'min':
                        where[s] = (j, c[s]['min_part'])
            for k_ in ('cut', 'pistol_cut', 'pistol_other_cut'):
                worst[s][k_] = max(worst[s][k_], c[s][k_])
    out['clear'] = {s: {k_: (round(v_ * 1000.0, 1) if 'min' in k_ else v_) for k_, v_ in worst[s].items()} for s in ('L', 'R')}
    out['barrel_up_frames'] = up_frames
    out['barrel_points_at_body'] = aim_body
    out['clear_where'] = where
    # joint steps on the keys (all keyed humanoid bones, deg per frame) and the seam
    names = [n for n in KEYED if n in hum_names]
    qs = []
    for j in range(NF + 1):
        scene.frame_set(j)
        qs.append({n: arm.pose.bones[n].matrix.to_quaternion() for n in names})
    step, sname = 0.0, ''
    for j in range(NF):
        for n in names:
            a_ = math.degrees(qs[j][n].rotation_difference(qs[j + 1][n]).angle)
            a_ = min(a_, 360.0 - a_)
            if a_ > step:
                step, sname = a_, '%s %d->%d' % (n, j, j + 1)
    seam = max(min(math.degrees(qs[0][n].rotation_difference(qs[NF][n]).angle), 360.0 - math.degrees(qs[0][n].rotation_difference(qs[NF][n]).angle)) for n in names)
    out['largest_joint_step_deg'] = (round(step, 2), sname)
    out['seam_deg'] = round(seam, 4)
    return out


ARMS = {}
assert list(VARIANTS) == ['P2'], 'r6 builds only the arm variant P2 (one action per lean variant)'
for vk in list(VARIANTS):
    P.variant = vk
    P.alpha_tab = None
    t_v = time.time()
    fails = fit_arm_alpha(P)
    ACTION_NAME[0] = 'Yoru_Sprint_r6_' + LV
    max_def, frames_data = build_action(P)
    rows = arm_numbers(P)
    for ln in arm_summary(rows, vk):
        log(ln)
    chk = variant_checks(vk)
    log('variant %s checks: clearance %s (where %s); largest joint step %.1f deg/frame (%s); seam %.4f deg; barrel up at frames %s; '
        'barrel points at her body %s; fit %.0f s' % (vk, chk['clear'], chk['clear_where'], chk['largest_joint_step_deg'][0], chk['largest_joint_step_deg'][1],
                                                     chk['seam_deg'], chk['barrel_up_frames'], chk['barrel_points_at_body'], time.time() - t_v))

    def rng_(key, side, fn=lambda v: v):
        vs = [fn(r[side][key]) for r in rows]
        return [round(min(vs), 3), round(max(vs), 3)]
    ARMS[vk] = {'label': VARIANTS[vk]['label'], 'params': dict(VARIANTS[vk]), 'alpha_tab': {s: [round(a, 2) for a in P.alpha_tab[s]] for s in ('L', 'R')},
                'fit_fail_frames': fails, 'checks': chk,
                'per_side': {s: {'upper_arm_world_deg': rng_('sig_w', s), 'elbow_deg': rng_('elbow', s), 'wrist_deg': rng_('wrist', s),
                                 'barrel_below_level_deg': rng_('barrel_below', s), 'barrel_from_down_fwd_deg': rng_('barrel_fwd', s),
                                 'barrel_from_down_out_deg': rng_('barrel_out', s), 'palm_z': rng_('palm', s, lambda v: v.z),
                                 'palm_y': rng_('palm', s, lambda v: v.y), 'palm_abs_x': rng_('palm', s, lambda v: abs(v.x)),
                                 'elbow_abs_x': rng_('K', s, lambda v: abs(v.x)),
                                 'palm_travel_chest_mm': [round(1000 * (rng_('hand_chest', s, lambda v: v.y)[1] - rng_('hand_chest', s, lambda v: v.y)[0]), 1),
                                                          round(1000 * (rng_('hand_chest', s, lambda v: v.z)[1] - rng_('hand_chest', s, lambda v: v.z)[0]), 1)]}
                             for s in ('L', 'R')}}
with open(os.path.join(PARTS_DIR, 'Yoru_Sprint_r6_%s_arms.json' % LV), 'w') as f:
    json.dump(ARMS, f, indent=1, default=str)

# ------------------------------------------------------------------ 6. outputs
hz = [fd['hips_world_offset'][2] + HEAD0[H['hips']].z for fd in frames_data[:NF]]
hx = [fd['hips_world_offset'][0] for fd in frames_data[:NF]]
summary = {'speed': P.SPEED, 'stride': VT, 'cycle_seconds': T_CYCLE, 'frames': NF, 'steps_per_minute': 120.0 / T_CYCLE,
           'step_length': VT / 2.0, 'pelvis_height_min': min(hz), 'pelvis_height_max': max(hz), 'pelvis_sway': (max(hx) - min(hx)) / 2.0,
           'knee_max': max(max(k[0], k[1]) for k in kn_table), 'ankle_at_touchdown': P.A_HS, 'hips_height_at_touchdown': P.Z_TD,
           'variants': {LV: 'Yoru_Sprint_r6_' + LV}, 'trunk': {'lean_upper_chest_deg': P.lean, 'hips_lean_deg': P.hips_lean,
           'neck_pitch_deg': P.neck_pitch, 'head_pitch_deg': P.head_pitch, 'pelvis_yaw_deg': P.yaw_p, 'pelvis_roll_deg': P.roll_p, 'chest_net_yaw_deg': P.chest_net_yaw, 'track_half_width_m': P.BASE},
           'speed_variation': {'model': 'stance_dip', 'amplitude': P.speed_var, 'stance_share': P.PH_TO, 'mean_speed': P.SPEED,
                               'phase_of_max': round(0.5 * (P.PH_TO + 0.5), 4),
                               'phase_of_max_note': 'stance_dip has no single maximum: the speed is at its maximum over the whole flight (phase stance_share .. 0.5 and stance_share + 0.5 .. 1); this is the middle of the first flight, and the slowest point is mid stance (stance_share / 2)',
                               'speed_per_frame': [ground_rate(f_ / NF) * P.SPEED for f_ in range(NF + 1)],
                               'note': 'ground speed under the character in m/s = SPEED * (1 + amplitude * (4 b / pi - dip)), b = stance_share, dip = sin(pi q / b) while a foot is on the ground (q = time since its touchdown as a share of the cycle, period 0.5) and 0 in the flight phase; phase = cycle phase of the right foot (0 = its touchdown)'},
           'tail_lift': P.tail_lift, 'planted_error_mm': {'%s_%s' % k: round(v[0], 2) for k, v in report.items()},
           'run_report': {k: (list(v) if isinstance(v, tuple) else v) for k, v in SPEC_REPORT.items()},
           'springs': ({k: v for k, v in SPRING_REP.items() if k != 'tails'} if (P.spec and P.spring_on and P.spring_dirs) else None),
           'spring_params': {'bust_stiffness': P.bust_stiff, 'bust_drag': P.bust_drag, 'hair_stiffness_factor': P.hair_stiff_mul, 'hair_drag': P.hair_drag,
                             'ear_stiffness': P.ear_stiff, 'ear_drag': P.ear_drag, 'tail_scale': P.tail_scale}}
with open(os.path.join(PARTS_DIR, 'Yoru_Sprint_r6_%s_gait.json' % LV), 'w') as f:
    json.dump(summary, f, indent=1)
log('gait summary written (no pose stream: that is exported only after the user has chosen a variant)')


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
for a_ in [a_ for a_ in bpy.data.actions if a_.name == 'Yoru_Sprint_r6_work']:
    bpy.data.actions.remove(a_)
# r6: no older rounds in the part file; the merge (mode merge) collects the three lean variants and appends r5 P2 for comparison
first = 'Yoru_Sprint_r6_' + LV
arm.animation_data.action = bpy.data.actions[first]
if getattr(arm.animation_data, 'action_slot', None) is None and len(bpy.data.actions[first].slots):
    arm.animation_data.action_slot = bpy.data.actions[first].slots[0]
scene.frame_set(0)
SAVE = os.path.join(PARTS_DIR, 'Yoru_Sprint_r6_%s.blend' % LV)
bpy.ops.wm.save_as_mainfile(filepath=SAVE)
log('saved', SAVE, 'actions:', [a_.name for a_ in bpy.data.actions if a_.name.startswith('Yoru_Sprint_r')])
log('DONE')
