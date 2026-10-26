"""Run v2 (polish of the old sprint): numbers for one run clip, in the background.  Checks only errors and smoothness, not beauty.
usage: blender -b --factory-startup <blend> --python build_run_v2_measure.py -- <action name> <out json> [armature object name] [no_gear]
Per frame of the loop (frame range 0 .. NF-1 of the action, 60 fps):
  gear     exact intersection test of hands / forearms / elbows / upper arms against torso, thighs and gear WITH the bust (GearTester)
  gap      least distance of the hand meshes to the gear (m, negative = inside)
  pos      armature-space position of the joints (hands, elbows, shoulders, knees, ankles, toes, head, hips, tail joints)
  rot      world orientation steps per frame in degrees (largest step of every bone, and the largest change of the step)
  hand     hand speed relative to the chest (m/s) and the share of the cycle in which it is below 0.4 m/s ("frozen fist")
  tail     what the game camera sees of the tail: projected length (% of the real length) and distance from the body's middle line
"""
import bpy, sys, os, math, json
from mathutils import Vector, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
ACTION, OUT = argv[0], argv[1]
ARM_NAME = argv[2] if len(argv) > 2 and argv[2] != '-' else None
NO_GEAR = 'no_gear' in argv
SCRIPTS = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
ns = {'__file__': os.path.join(SCRIPTS, 'build_lauf_v2_lib.py')}
exec(compile(open(ns['__file__'], encoding='utf-8').read(), ns['__file__'], 'exec'), ns)
LB = ns

scene = bpy.context.scene
arm = bpy.data.objects[ARM_NAME] if ARM_NAME else next(o for o in bpy.data.objects if o.type == 'ARMATURE')
act = bpy.data.actions[ACTION]
arm.animation_data.action = act
slot = getattr(arm.animation_data, 'action_slot', None)
if hasattr(arm.animation_data, 'action_slot') and act.slots:
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
NF = f1 - f0                                     # key NF == key 0 (loop)
Hm = LB['load']('build_idle_v2_lib.py')['humanoid_map']()
pbs = arm.pose.bones


def nm(side, part):
    return Hm[('left' if side == 'L' else 'right') + part]


TRACK = {'hips': Hm['hips'], 'spine': Hm['spine'], 'chest': Hm['chest'], 'upperChest': Hm['upperChest'], 'neck': Hm['neck'], 'head': Hm['head']}
for s in 'LR':
    for p in ('Shoulder', 'UpperArm', 'LowerArm', 'Hand', 'UpperLeg', 'LowerLeg', 'Foot', 'Toes'):
        TRACK[s + p] = nm(s, p)
for i in range(1, 9):
    TRACK['Tail%d' % i] = 'J_Opt_C_CatTail%d_01' % i

tester = None
if not NO_GEAR:
    W, Lm, rig, tester = LB['make_tester'](arm, True)
pos = {k: [] for k in TRACK}
rot = {k: [] for k in TRACK}
gear, gap, checks = [], [], []
for f in range(f0, f0 + NF):
    scene.frame_set(f)
    for k, n in TRACK.items():
        pb = pbs[n]
        pos[k].append(list(pb.head))
        rot[k].append(pb.matrix.to_quaternion())
    if tester:
        res, g = tester.test()
        gear.append(res)
        gap.append(g)
        rc = Lm['run_checks'](rig)
        checks.append({k: rc[k] for k in ('leg_gap', 'tail_gap', 'sole_min_L', 'sole_min_R', 'hand_gap')})
    print('frame', f, flush=True)


def ang(a, b):
    d = abs(a.dot(b))
    return math.degrees(2.0 * math.acos(min(1.0, d)))


steps = {}
for k, qs in rot.items():
    st = [ang(qs[i], qs[(i + 1) % NF]) for i in range(NF)]
    ch = [abs(st[(i + 1) % NF] - st[i]) for i in range(NF)]
    steps[k] = dict(max_step=round(max(st), 2), at=st.index(max(st)), max_change=round(max(ch), 2), mean_step=round(sum(st) / NF, 2))

# hand speed relative to the chest (in the chest's own frame, m/s at 60 fps)
hand = {}
for s in 'LR':
    sp = []
    for i in range(NF):
        j = (i + 1) % NF
        qa, qb = rot['upperChest'][i], rot['upperChest'][j]
        pa = qa.inverted() @ (Vector(pos[s + 'Hand'][i]) - Vector(pos['upperChest'][i]))
        pb_ = qb.inverted() @ (Vector(pos[s + 'Hand'][j]) - Vector(pos['upperChest'][j]))
        sp.append((pb_ - pa).length * 60.0)
    hand[s] = dict(speed=[round(x, 3) for x in sp], frozen_share=round(sum(1 for x in sp if x < 0.4) / NF, 3), max=round(max(sp), 2), min=round(min(sp), 2))

# the tail as the game camera sees it (4.4 m behind, 0.35 m to the right, 1.75 m high, looking at (0, -0.05, 0.8)), perspective projection
cam = Vector((0.35, -4.4, 1.75))
tgt = Vector((0.0, -0.05, 0.80))
fwd = (tgt - cam).normalized()
right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
up = right.cross(fwd).normalized()
tail = []
for i in range(NF):
    pts = [Vector(pos['Tail%d' % k][i]) for k in range(1, 9)]
    pr = []
    for p in pts:
        v = p - cam
        z = v.dot(fwd)
        pr.append((v.dot(right) / z, v.dot(up) / z))
    # real length versus projected length (both in metres at the character's distance 4.4 m)
    real = sum((pts[k + 1] - pts[k]).length for k in range(7))
    proj = sum(math.hypot(pr[k + 1][0] - pr[k][0], pr[k + 1][1] - pr[k][1]) for k in range(7)) * 4.4
    tip = pts[7]
    tail.append(dict(real=round(real, 3), proj=round(proj, 3), proj_share=round(proj / max(real, 1e-6), 3),
                     tip_x=round(tip.x, 3), tip_y=round(tip.y, 3), tip_z=round(tip.z, 3),
                     lateral=round(max(abs(p.x) for p in pts), 3)))

summary = dict(action=ACTION, frames=NF, steps={k: v for k, v in steps.items()}, hand=hand, tail=tail)
if tester:
    keys = sorted(gear[0].keys())
    summary['gear_frames_with_hits'] = {k: sum(1 for r in gear if r[k] > 0) for k in keys}
    summary['gear_total_pairs'] = {k: sum(r[k] for r in gear) for k in keys}
    summary['gap_min'] = {s: round(min(g[s] for g in gap), 4) for s in 'LR'}
    summary['checks'] = checks
    summary['leg_gap_min'] = round(min(c['leg_gap'] for c in checks), 4)
    summary['tail_gap_min'] = round(min(c['tail_gap'] for c in checks), 4)
    summary['hand_gap_min'] = round(min(c['hand_gap'] for c in checks), 4)
    summary['gear'] = gear
    summary['gap'] = gap
summary['pos'] = {k: [[round(c, 4) for c in p] for p in v] for k, v in pos.items()}
json.dump(summary, open(OUT, 'w'), indent=1)
print('MEASURE DONE', OUT)
big = sorted(steps.items(), key=lambda kv: -kv[1]['max_step'])[:12]
print('largest rotation steps (deg / frame):', [(k, v['max_step'], v['at']) for k, v in big])
print('hand speed relative to chest: ', {s: (hand[s]['min'], hand[s]['max'], hand[s]['frozen_share']) for s in 'LR'})
print('tail projected share of its length (min, mean, max): ', min(t['proj_share'] for t in tail), round(sum(t['proj_share'] for t in tail) / NF, 3), max(t['proj_share'] for t in tail))
if tester:
    print('gear hits (frames with hits):', summary['gear_frames_with_hits'])
    print('leg gap min', summary['leg_gap_min'], 'tail gap min', summary['tail_gap_min'], 'hand-to-hand gap min', summary['hand_gap_min'])
    print('gear pairs total:', summary['gear_total_pairs'], 'gap min', summary['gap_min'])
