"""
Yoru - WALK v2, round 3 (from build_walk_v2_check_r2.py): error checks of N070 / N083 / N097 in Yoru_Walk_v2_round3.blend (copy of build_walk_v2_check.py, adapted: armatures
Yoru_R2_<key>, the floor moves with the ground motion of build_walk.py (+-5 % speed wobble), forearm twist, tail against the hands).
Background:  blender -b --factory-startup <Yoru_Walk_v2_round2.blend> --python build_walk_v2_check_r2.py -- [keys, default Neu,NeuPlus]
Per variant:
  slide_mm       floor contact: shoe vertices that touch the floor (z < 3 mm) in two neighbouring frames must move backwards with the floor
                 (exactly SPEED / FPS = 40 mm per frame); the largest deviation (planted foot sliding on the floor)
  speed_m_s      mean backward speed of the planted shoe vertices (should be 1.2)
  joint_step     largest rotation of any keyed bone from one frame to the next, across the seam too (limit 15 deg)
  seam           pose difference frame NF against frame 0 (deg)
  arms           exact intersection test (GearTester): hand and forearm beyond the elbow end must be 0; elbow end and upper arm
                 (sleeve against the side of the vest, hidden) are reported; hand-to-gear distance range
  knees          least knee bend of the standing and of the swinging leg; tail / leg / sole gaps (run_checks of build_idle_v2_lib.py)
  head_bob_mm    vertical travel of the head joint; game_px: how many pixels that is in the game camera (4.4 m, 72 mm, 720 px)
"""
import bpy, sys, os, math
from mathutils import Vector

_HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
W = {'__file__': os.path.join(_HERE, 'build_walk_v2_lib.py')}
exec(compile(open(W['__file__'], encoding='utf-8').read(), W['__file__'], 'exec'), W)
L = W['L']
NF, FPS, SPEED = W['NF'], W['FPS'], W['SPEED']
R2 = {'__file__': os.path.join(_HERE, 'build_walk_v2_round3.py')}
exec(compile(open(R2['__file__'], encoding='utf-8').read(), R2['__file__'], 'exec'), R2)


def twist_deg(arm, rig, side):
    pb = arm.pose.bones[rig.nm(side, 'LowerArm')]
    R = arm.data.bones[pb.name].matrix_local.to_quaternion()
    sx = 1.0 if side == 'R' else -1.0
    a = (R.inverted() @ Vector((sx, 0.0, 0.0))).normalized()
    q = pb.matrix_basis.to_quaternion()
    return abs(math.degrees(2.0 * math.atan2(q.x * a.x + q.y * a.y + q.z * a.z, q.w)))


def check_variant(key):
    scene = bpy.context.scene
    arm = bpy.data.objects['Yoru_R3_' + key]
    NF = R2['GAIT'][key]['NF']
    rig = L['Rig'](arm, L['humanoid_map']())
    body = rig.body
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    feet = {s: [i for i, n in enumerate(dom) if vis[i] and n in (rig.nm(s, 'Foot'), rig.nm(s, 'Toes'))] for s in ('L', 'R')}
    names = W['keyed_names'](rig)
    tester = W['GearTester'](rig)
    pbs = arm.pose.bones
    prev_q, first_q = None, None
    max_step, step_at = 0.0, None
    prev_co = None
    slide, slide_at, speeds = 0.0, None, []
    arms_tot, gaps = {}, {'L': [], 'R': []}
    worst = {'tail_gap': 9.0, 'leg_gap': 9.0, 'sole_min': 9.0}
    knee_st, knee_sw = 180.0, 180.0
    head_z = []
    tw = 0.0
    elb, hz = [180.0, 0.0], []
    tail_ids = [i for i, n in enumerate(dom) if n in set(rig.tail_bones[1:])]
    hand_ids = tester.hand_ids['L'] + tester.hand_ids['R']
    tail_hand = 9.0
    for f in range(NF + 1):
        scene.frame_set(f)
        q = {n: pbs[n].rotation_quaternion.copy() for n in names}
        if prev_q is not None:
            for n in names:
                a = math.degrees(prev_q[n].rotation_difference(q[n]).angle)
                a = min(a, 360.0 - a)
                if a > max_step:
                    max_step, step_at = a, (n, f)
        else:
            first_q = q
        prev_q = q
        if f == NF:
            seam = max(min(math.degrees(first_q[n].rotation_difference(q[n]).angle), 360 - math.degrees(first_q[n].rotation_difference(q[n]).angle)) for n in names)
            break
        co = L['evaluated_coords'](body)
        if prev_co is not None:
            for s in ('L', 'R'):
                for i in feet[s]:
                    if co[i].z < 0.003 and prev_co[i].z < 0.003:
                        d = co[i] - prev_co[i]
                        exp = -(R2['ground'](key, f) - R2['ground'](key, f - 1))
                        dev = math.sqrt(d.x ** 2 + (d.y - exp) ** 2 + d.z ** 2)
                        speeds.append(-d.y * FPS)
                        if dev > slide:
                            slide, slide_at = dev, (s, f, i)
        prev_co = co
        tw = max(tw, twist_deg(arm, rig, 'L'), twist_deg(arm, rig, 'R'))
        for s_ in ('L', 'R'):
            sh_, el_, wr_ = pbs[rig.nm(s_, 'UpperArm')].head, pbs[rig.nm(s_, 'LowerArm')].head, pbs[rig.nm(s_, 'Hand')].head
            ef = math.degrees((el_ - sh_).angle(wr_ - el_))
            elb[0], elb[1] = min(elb[0], ef), max(elb[1], ef)
            hz.append(wr_.z)
        from mathutils.kdtree import KDTree
        kd = KDTree(len(hand_ids))
        for j, i in enumerate(hand_ids):
            kd.insert(co[i], j)
        kd.balance()
        tail_hand = min(tail_hand, min(kd.find(co[i])[2] for i in tail_ids))
        res, gap = tester.test()
        for k, v in res.items():
            arms_tot[k] = arms_tot.get(k, 0) + v
        for s in ('L', 'R'):
            gaps[s].append(gap[s])
        c = L['run_checks'](rig)
        if c['tail_gap'] < worst['tail_gap']:
            worst['tail_at'] = (f, c['tail_gap_at'])
        worst['tail_gap'] = min(worst['tail_gap'], c['tail_gap'])
        worst['leg_gap'] = min(worst['leg_gap'], c['leg_gap'])
        worst['sole_min'] = min(worst['sole_min'], c['sole_min_L'], c['sole_min_R'])
        for s in ('L', 'R'):
            th, sh, an = pbs[rig.nm(s, 'UpperLeg')].head, pbs[rig.nm(s, 'LowerLeg')].head, pbs[rig.nm(s, 'Foot')].head
            kn = math.degrees((sh - th).angle(an - sh))
            psi = ((f / float(NF)) + (0.0 if s == 'R' else 0.5)) % 1.0
            if psi < W['WALK']['beta']:
                knee_st = min(knee_st, kn)
            else:
                knee_sw = min(knee_sw, kn)
        head_z.append(pbs[rig.H['head']].head.z)
    bob = max(head_z) - min(head_z)
    return dict(slide_mm=round(slide * 1000, 2), slide_at=slide_at, speed_m_s=round(sum(speeds) / max(1, len(speeds)), 4),
                contact_pairs=len(speeds), joint_step_deg=round(max_step, 2), joint_step_at=step_at, seam_deg=round(seam, 4),
                arms=dict(sorted(arms_tot.items())), hand_gap_mm={s: (round(min(v) * 1000, 1), round(max(v) * 1000, 1)) for s, v in gaps.items()},
                knee_min_stance=round(knee_st, 1), knee_min_swing=round(knee_sw, 1),
                tail_gap_mm=round(worst['tail_gap'] * 1000, 1), tail_at=worst.get('tail_at'), leg_gap_mm=round(worst['leg_gap'] * 1000, 1), sole_min_mm=round(worst['sole_min'] * 1000, 1),
                forearm_twist_deg=round(tw, 1), elbow_deg=(round(elb[0], 1), round(elb[1], 1)), wrist_z_m=(round(min(hz), 3), round(max(hz), 3)), tail_hand_mm=round(tail_hand * 1000, 1), head_bob_mm=round(bob * 1000, 1), head_bob_game_px=round(bob * 1440.0 / 4.4, 1))


if bpy.app.background and '--' in sys.argv:
    argv = sys.argv[sys.argv.index('--') + 1:]
    keys = argv[0].split(',') if argv else ['N070', 'N083', 'N097']
    for k in keys:
        print('[walk_v2 check r3]', k, check_variant(k), flush=True)
