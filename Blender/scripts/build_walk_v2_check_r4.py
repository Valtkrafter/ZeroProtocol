"""
Yoru - WALK v2, round 4 (from build_walk_v2_check_r3.py): error checks of R3 / R4a / R4b in Yoru_Walk_v2_round4.blend, plus the arm timing
(frames from the forward extreme of the upper arm to the extremes of elbow bend, wrist bend and finger curl) and wrist flex / deviation (copy of build_walk_v2_check.py, adapted: armatures
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


def timing(tim, nf):
    """overlap: frames from the forward extreme of the upper arm to the forward extremes of forearm, hand and index finger (their directions
    in the frame of the chest heading)"""
    out = {}
    for s_, rows in tim.items():
        n = len(rows)
        i_u = max(range(n), key=lambda i: rows[i][0])
        res = []
        for c in (1, 2, 3):
            i_c = max(range(n), key=lambda i: rows[i][c])
            res.append((i_c - i_u) % nf)
        out[s_] = dict(forearm=res[0], hand=res[1], finger=res[2])
    return out


def check_variant(key):
    scene = bpy.context.scene
    arm = bpy.data.objects['Yoru_R4_' + key]
    NF = 25
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
    tim, wr_rng, hpath = {}, {}, {}
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
                        exp = -(R2['ground']('N083', f) - R2['ground']('N083', f - 1))
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
            kn_ = pbs[rig.nm(s_, 'MiddleProximal')].head
            sxx = 1.0 if s_ == 'R' else -1.0
            dfv, dhv = (wr_ - el_).normalized(), (kn_ - wr_).normalized()
            Rf_ = arm.data.bones[rig.nm(s_, 'LowerArm')].matrix_local.to_quaternion()
            nfv = (pbs[rig.nm(s_, 'LowerArm')].matrix.to_quaternion() @ Rf_.inverted()) @ Vector((0.0, 0.0, -1.0))
            nfv = (nfv - dfv * nfv.dot(dfv)).normalized()
            ulv = sxx * nfv.cross(dfv)
            wfl = math.degrees(math.atan2(dhv.dot(nfv), dhv.dot(dfv)))
            wdv = math.degrees(math.atan2(dhv.dot(ulv), dhv.dot(dfv)))
            D_uc_ = pbs[rig.H['upperChest']].matrix.to_quaternion() @ arm.data.bones[rig.H['upperChest']].matrix_local.to_quaternion().inverted()
            fwd_ = (D_uc_ @ Vector((0.0, 1.0, 0.0))).normalized()
            idx_ = pbs[rig.nm(s_, 'IndexIntermediate')].matrix.to_quaternion() @ arm.data.bones[rig.nm(s_, 'IndexIntermediate')].matrix_local.to_quaternion().inverted()
            hnd_ = pbs[rig.nm(s_, 'Hand')].matrix.to_quaternion() @ arm.data.bones[rig.nm(s_, 'Hand')].matrix_local.to_quaternion().inverted()
            curl_ = math.degrees((hnd_.inverted() @ idx_).angle)
            tip_ = pbs[rig.nm(s_, 'IndexDistal')].head
            tim.setdefault(s_, []).append(((el_ - sh_).normalized().dot(fwd_), (wr_ - el_).normalized().dot(fwd_), dhv.dot(fwd_), (tip_ - kn_).normalized().dot(fwd_)))
            wr_rng.setdefault(s_, []).append((wfl, wdv))
            rgt_ = fwd_.cross(Vector((0.0, 0.0, 1.0))).normalized()
            rel_ = kn_ - sh_
            hpath.setdefault(s_, []).append((rel_.dot(fwd_), sxx * rel_.dot(rgt_), rel_.z))
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
                forearm_twist_deg=round(tw, 1), elbow_deg=(round(elb[0], 1), round(elb[1], 1)), timing_frames=timing(tim, NF),
                wrist_flex_deg={s_: (round(min(v[0] for v in r_), 1), round(max(v[0] for v in r_), 1)) for s_, r_ in wr_rng.items()},
                hand_path_mm={s_: tuple(round((max(v[i] for v in r_) - min(v[i] for v in r_)) * 1000) for i in range(3)) for s_, r_ in hpath.items()},
                wrist_dev_deg={s_: (round(min(v[1] for v in r_), 1), round(max(v[1] for v in r_), 1)) for s_, r_ in wr_rng.items()}, wrist_z_m=(round(min(hz), 3), round(max(hz), 3)), tail_hand_mm=round(tail_hand * 1000, 1), head_bob_mm=round(bob * 1000, 1), head_bob_game_px=round(bob * 1440.0 / 4.4, 1))


if bpy.app.background and '--' in sys.argv:
    argv = sys.argv[sys.argv.index('--') + 1:]
    keys = argv[0].split(',') if argv else ['R3', 'R4a', 'R4b']
    for k in keys:
        print('[walk_v2 check r4]', k, check_variant(k), flush=True)
