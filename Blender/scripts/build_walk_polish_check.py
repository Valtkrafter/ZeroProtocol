"""
Yoru - WALK POLISH (polish of the v1 walk in Yoru_Walk.blend, no rebuild): error checks of one walk action.  Saves nothing.
Background:
  blender -b --factory-startup <blend> --python build_walk_polish_check.py -- <out json> [action name, default: the armature's action]
Measures (only to catch errors, they do not decide what looks good):
  joint_step   largest local rotation (bone against its parent) of any keyed humanoid bone from one frame to the next, the seam
               (last frame -> frame 0) included; limit 15 deg.  Top 6 listed.
  slide_mm     shoe vertices that touch the floor (z < 3 mm) in two neighbouring frames must move backwards exactly with the scrolling
               floor (Floor_scrolling, the +-5 % speed wobble included); largest horizontal deviation per frame and the drift summed over a stance.
  speed_m_s    mean backward speed of the floor over the cycle and of the planted shoe vertices (target 1.5).
  arms         mesh test of build_idle_v2_lib.arm_penetration (forearm, hand, fingers and the elbow half of the upper arm against torso,
               thighs and gear, through the vertex normals; 0 = nothing inside) and the capsule clearance arm_clearance, per frame.
  knees        knee flexion per frame (angle thigh / shin), at heel strike and its peak in the loading phase.
  elbows       elbow flexion (angle upper arm / forearm), wrist bend (forearm / hand) per frame, hand height above the floor.
  legs         run_checks: closest vertices of the two legs below the thigh gear, lowest sole points.
FIX 27.10. (round 1): Floor_scrolling does not move in Yoru_Walk.blend, so the slide test now uses the ground motion of the gait model
(G(phi) of build_walk.py with speed and speed_variation from Yoru_Walk_gait.json) whenever the floor object stands still.  The arm test
also reports the elbow half of the upper arm (pen_upper) and where the deepest forearm / hand vertex sits.
"""
import bpy, sys, os, math, json
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
ACT = argv[1] if len(argv) > 1 else None
GAIT = r'C:\Users\valen\ZeroProtocol\Blender\Yoru_Walk_gait.json'
_HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
GLB = r'C:\Users\valen\ZeroProtocol\Blender\work\Yoru_V2.glb'
LIB = {'__name__': 'idle_lib', '__file__': os.path.join(_HERE, 'build_idle_v2_lib.py')}
exec(compile(open(LIB['__file__'], encoding='utf-8').read(), LIB['__file__'], 'exec'), LIB)

scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if ACT:
    arm.animation_data.action = bpy.data.actions[ACT]
action = arm.animation_data.action
H = LIB['humanoid_map'](GLB)
rig = LIB['Rig'](arm, H)
NF = int(round(action.frame_range[1] - action.frame_range[0]))
F0 = int(round(action.frame_range[0]))
FRAMES = list(range(F0, F0 + NF))
pbs = arm.pose.bones


def fcurves_of(act):
    out = []
    try:
        out = list(act.fcurves)
    except Exception:
        pass
    if not out:
        for l in act.layers:
            for s in l.strips:
                for cb in s.channelbags:
                    out += list(cb.fcurves)
    return out


keyed = sorted({fc.data_path.split('"')[1] for fc in fcurves_of(action) if fc.data_path.startswith('pose.bones["')})
humanoid = set(H.values())
keyed_h = [b for b in keyed if b in humanoid]

floor = bpy.data.objects.get('Floor_scrolling')


def floor_y(f):
    scene.frame_set(f)
    return floor.matrix_world.translation.y if floor else 0.0


body = rig.body
vis = LIB['visible_vertices'](body)
dom = LIB['vertex_groups_by_bone'](rig)
shoe = {s: [i for i, n in enumerate(dom) if vis[i] and n in (H[('left' if s == 'L' else 'right') + 'Foot'], H[('left' if s == 'L' else 'right') + 'Toes'])]
        for s in ('L', 'R')}


def ang(a, b):
    return math.degrees(a.angle(b)) if a.length > 1e-9 and b.length > 1e-9 else 0.0


per = {k: [] for k in ('knee_L', 'knee_R', 'elbow_L', 'elbow_R', 'wrist_L', 'wrist_R', 'hand_z_L', 'hand_z_R', 'hand_y_L', 'hand_y_R',
                       'hand_x_L', 'hand_x_R', 'pen_L', 'pen_R', 'clear_L', 'clear_R', 'floor_y', 'leg_gap', 'sole_min_L', 'sole_min_R',
                       'upper_pitch_L', 'upper_pitch_R', 'hips_z')}
local_q = {b: [] for b in keyed_h}
shoe_co = {'L': [], 'R': []}
for f in FRAMES + [F0 + NF]:
    scene.frame_set(f)
    per['floor_y'].append(floor.matrix_world.translation.y if floor else 0.0)
    if f == F0 + NF:
        for b in keyed_h:
            pb = pbs[b]
            m = pb.matrix if pb.parent is None else pb.parent.matrix.inverted() @ pb.matrix
            local_q[b].append(m.to_quaternion())
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        for s in ('L', 'R'):
            shoe_co[s].append([me.vertices[i].co.copy() for i in shoe[s]])
        ev.to_mesh_clear()
        break
    for b in keyed_h:
        pb = pbs[b]
        m = pb.matrix if pb.parent is None else pb.parent.matrix.inverted() @ pb.matrix
        local_q[b].append(m.to_quaternion())
    hips = pbs[H['hips']].head
    per['hips_z'].append(hips.z)
    for s in ('L', 'R'):
        side = 'left' if s == 'L' else 'right'
        hp, kn, an = pbs[H[side + 'UpperLeg']].head, pbs[H[side + 'LowerLeg']].head, pbs[H[side + 'Foot']].head
        per['knee_' + s].append(ang(kn - hp, an - kn))
        sh, el, wr = pbs[H[side + 'UpperArm']].head, pbs[H[side + 'LowerArm']].head, pbs[H[side + 'Hand']].head
        kn2 = pbs[H[side + 'MiddleProximal']].head
        per['elbow_' + s].append(ang(el - sh, wr - el))
        per['wrist_' + s].append(ang(wr - el, kn2 - wr))
        per['hand_z_' + s].append(wr.z)
        per['hand_y_' + s].append(wr.y - hips.y)
        per['hand_x_' + s].append(wr.x - hips.x)
        u = (el - sh).normalized()
        per['upper_pitch_' + s].append(math.degrees(math.atan2(u.y, -u.z)))
    pen = LIB['arm_penetration'](rig)
    cl = LIB['arm_clearance'](rig)
    for s in ('L', 'R'):
        per.setdefault('pen_upper_' + s, []).append(round(pen[s][2] * 1000.0, 2))   # elbow half of the upper arm (mm inside)
        if pen[s][3] > 0.001:
            per.setdefault('pen_where_' + s, []).append((f, round(pen[s][3] * 1000.0, 1), pen[s][4]))
        per['pen_' + s].append(round(pen[s][3] * 1000.0, 2))          # forearm / hand / fingers (mm inside)
        per['clear_' + s].append(round(cl[s][0] * 1000.0, 1))
    rc = LIB['run_checks'](rig)
    per['leg_gap'].append(round(rc['leg_gap'] * 1000.0, 1))
    per['sole_min_L'].append(round(rc['sole_min_L'] * 1000.0, 1))
    per['sole_min_R'].append(round(rc['sole_min_R'] * 1000.0, 1))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    for s in ('L', 'R'):
        shoe_co[s].append([me.vertices[i].co.copy() for i in shoe[s]])
    ev.to_mesh_clear()

# joint steps (local rotation, across the seam: frame NF is the first frame again)
steps = []
for b, qs in local_q.items():
    for i in range(NF):
        a = math.degrees(qs[i].rotation_difference(qs[i + 1]).angle)
        a = min(a, 360.0 - a)
        steps.append((round(a, 2), b, '%d->%d' % (FRAMES[i], FRAMES[i] + 1)))
steps.sort(reverse=True)
seam = max(math.degrees(local_q[b][0].rotation_difference(local_q[b][NF]).angle) for b in keyed_h)

# floor contact slide
fy = per['floor_y']
if max(fy) - min(fy) < 1e-6:                                         # the floor stands still: ground motion of the gait model
    g = json.load(open(GAIT))
    VT = g['speed'] * NF / 30.0
    a = g['speed_variation']['amplitude']
    ph0 = g['speed_variation']['phase_of_max']
    k = 4.0 * math.pi
    fy = [-VT * (p + a / k * (math.sin(k * (p - ph0)) + math.sin(k * ph0))) for p in (i / float(NF) for i in range(NF + 1))]
    per['floor_y'] = fy
slide = {}
speeds = []
for s in ('L', 'R'):
    worst, drift_run, drift_max = 0.0, 0.0, 0.0
    for i in range(NF):
        d_floor = fy[i + 1] - fy[i]
        a_, b_ = shoe_co[s][i], shoe_co[s][i + 1]
        res = []
        for k in range(len(a_)):
            if a_[k].z < 0.003 and b_[k].z < 0.003:
                dv = b_[k] - a_[k]
                res.append(math.hypot(dv.x, dv.y - d_floor))
                speeds.append(-dv.y * 30.0)
        if res:
            r = max(res)
            worst = max(worst, r)
            drift_run += sum(res) / len(res)
            drift_max = max(drift_max, drift_run)
        else:
            drift_run = 0.0
    slide[s] = {'max_per_frame_mm': round(worst * 1000.0, 2), 'stance_drift_mm': round(drift_max * 1000.0, 2)}
floor_speed = -(fy[NF] - fy[0]) / (NF / 30.0) if floor else None

# knees: heel strike = the frame where the sole first touches after the swing (lowest sole point < 3 mm)
knee_info = {}
for s in ('L', 'R'):
    sm = per['sole_min_' + s]
    hs = [i for i in range(NF) if sm[i] < 3.0 and sm[i - 1] >= 3.0]
    i0 = hs[0] if hs else 0
    kn = per['knee_' + s]
    window = [kn[(i0 + j) % NF] for j in range(0, 6)]
    knee_info[s] = {'heel_strike_frame': FRAMES[i0], 'at_contact': round(kn[i0], 1), 'loading_peak': round(max(window), 1),
                    'min': round(min(kn), 1), 'max': round(max(kn), 1)}

rnd = lambda xs, n=1: [round(x, n) for x in xs]
res = {
    'action': action.name, 'frames': NF, 'first': F0,
    'joint_step_top': steps[:6], 'joint_step_over_15': [s_ for s_ in steps if s_[0] > 15.0], 'seam_deg': round(seam, 3),
    'slide': slide, 'floor_speed_m_s': round(floor_speed, 4) if floor_speed else None,
    'planted_vertex_speed_m_s': round(sum(speeds) / len(speeds), 4) if speeds else None,
    'pen_mm_max': {s: max(per['pen_' + s]) for s in ('L', 'R')}, 'clear_mm_min': {s: min(per['clear_' + s]) for s in ('L', 'R')},
    'pen_upper_mm_max': {s: max(per['pen_upper_' + s]) for s in ('L', 'R')},
    'pen_where': {s: per.pop('pen_where_' + s, []) for s in ('L', 'R')},
    'knees': knee_info,
    'elbow_range': {s: (round(min(per['elbow_' + s]), 1), round(max(per['elbow_' + s]), 1)) for s in ('L', 'R')},
    'wrist_range': {s: (round(min(per['wrist_' + s]), 1), round(max(per['wrist_' + s]), 1)) for s in ('L', 'R')},
    'hand_z_range': {s: (round(min(per['hand_z_' + s]), 3), round(max(per['hand_z_' + s]), 3)) for s in ('L', 'R')},
    'leg_gap_min_mm': min(per['leg_gap']), 'sole_min_mm': {s: min(per['sole_min_' + s]) for s in ('L', 'R')},
    'per_frame': {k: rnd(v, 3 if k.startswith(('hand', 'hips', 'floor')) else 1) for k, v in per.items()},
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as fh:
    json.dump(res, fh, indent=1)
print('CHECK', json.dumps({k: v for k, v in res.items() if k != 'per_frame'}))
