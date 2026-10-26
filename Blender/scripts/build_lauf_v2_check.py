"""
Yoru - LAUF v2: error checks and pose numbers of the clip 'Yoru_Lauf' in a work file (nothing is saved).
Background:  blender -b --factory-startup <Yoru_Lauf_v2_roundN.blend> --python build_lauf_v2_check.py -- [armature name, default Yoru_Lauf]
Checks (60 fps, 40 frames per cycle):
  slide_mm        shoe vertices that touch the floor (z < 3 mm) in two neighbouring frames must move backwards with the floor (G(phi) of the gait);
                  largest deviation (a planted foot sliding)
  joint_step      largest rotation of any keyed bone from one 60 fps frame to the next and over two frames (= one 30 fps frame), across the seam
  accel_step      largest change of that rotation speed between neighbouring frames (a kink / pop)
  seam_deg        pose difference frame 40 against frame 0
  arms            exact intersection test (GearTester, WITH the bust): hand and forearm beyond the elbow end must be 0
  forearm_twist   twist of the forearm about its own axis against the upper arm (limit about 18 deg)
  tail_gap_mm     tail (joints 2 .. 8) against hips, legs, feet and coat (at least 8 mm); leg_gap_mm; sole_min_mm
Pose numbers: trunk lean (hips joint -> neck joint against the vertical), head ahead of the hips, upper arm swing against the plumb line
(side view), elbow flexion, hand height, knee flexion (stance / swing), pelvis bob, head bob (and in pixels of the game camera)
"""
import bpy, sys, os, math
from mathutils import Vector
from mathutils.kdtree import KDTree

SCRIPTS = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
ns = {'__file__': os.path.join(SCRIPTS, 'build_lauf_v2_lib.py')}
exec(compile(open(ns['__file__'], encoding='utf-8').read(), ns['__file__'], 'exec'), ns)
LB = ns
NF, FPS = LB['NF'], LB['FPS']


def twist_deg(arm, side, nm):
    pb = arm.pose.bones[nm(side, 'LowerArm')]
    R = arm.data.bones[pb.name].matrix_local.to_quaternion()
    sx = 1.0 if side == 'R' else -1.0
    a = (R.inverted() @ Vector((sx, 0.0, 0.0))).normalized()
    q = pb.matrix_basis.to_quaternion()
    return abs(math.degrees(2.0 * math.atan2(q.x * a.x + q.y * a.y + q.z * a.z, q.w)))


def check(arm_name='Yoru_Lauf', gait=None):
    gait = gait or LB['GAIT_NEU']
    scene = bpy.context.scene
    arm = bpy.data.objects[arm_name]
    W, L, rig, tester = LB['make_tester'](arm, True)
    nm, H = rig.nm, rig.H
    body = rig.body
    vis = L['visible_vertices'](body)
    dom = L['vertex_groups_by_bone'](rig)
    feet = {s: [i for i, n in enumerate(dom) if vis[i] and n in (nm(s, 'Foot'), nm(s, 'Toes'))] for s in ('L', 'R')}
    names = W['keyed_names'](rig)
    names = [n for n in names if n in arm.pose.bones]
    pbs = arm.pose.bones
    base = arm.matrix_world.translation.copy()
    qs, cos = [], []
    slide, slide_at, speeds = 0.0, None, []
    arms_tot, gaps = {}, {'L': [], 'R': []}
    worst = {'tail_gap': 9.0, 'leg_gap': 9.0, 'sole_min': 9.0}
    tw = 0.0
    num = {'trunk': [], 'head_ahead': [], 'elbow': [], 'upper': {'L': [], 'R': []}, 'hand_z': [], 'knee_st': [], 'knee_sw': [], 'pelvis': [], 'head_z': []}
    for f in range(NF + 1):
        scene.frame_set(f)
        qs.append({n: pbs[n].rotation_quaternion.copy() for n in names})
        if f == NF:
            break
        co = L['evaluated_coords'](body)
        if cos:
            prev = cos[-1]
            exp = -(LB['ground'](gait, f / float(NF)) - LB['ground'](gait, (f - 1) / float(NF)))
            for s in ('L', 'R'):
                for i in feet[s]:
                    if co[i].z < 0.003 and prev[i].z < 0.003:
                        d = co[i] - prev[i]
                        dev = math.sqrt(d.x ** 2 + (d.y - exp) ** 2 + d.z ** 2)
                        speeds.append(-d.y * FPS)
                        if dev > slide:
                            slide, slide_at = dev, (s, f, i)
        cos.append(co)
        tw = max(tw, twist_deg(arm, 'L', nm), twist_deg(arm, 'R', nm))
        res, gap = tester.test()
        for k, v in res.items():
            arms_tot[k] = arms_tot.get(k, 0) + v
        for s in ('L', 'R'):
            gaps[s].append(gap[s])
        c = L['run_checks'](rig)
        worst['tail_gap'] = min(worst['tail_gap'], c['tail_gap'])
        if c['tail_gap'] <= worst['tail_gap']:
            worst['tail_at'] = (f, c['tail_gap_at'])
        worst['leg_gap'] = min(worst['leg_gap'], c['leg_gap'])
        worst['sole_min'] = min(worst['sole_min'], c['sole_min_L'], c['sole_min_R'])
        hp = pbs[H['hips']].head
        nk = pbs[H['neck']].head
        hd = pbs[H['head']].head
        v = nk - hp
        num['trunk'].append(math.degrees(math.atan2(v.y, v.z)))
        num['head_ahead'].append(hd.y - hp.y)
        num['pelvis'].append(hp.z)
        num['head_z'].append(hd.z)
        for s in ('L', 'R'):
            sh, el, wr = pbs[nm(s, 'UpperArm')].head, pbs[nm(s, 'LowerArm')].head, pbs[nm(s, 'Hand')].head
            num['elbow'].append(math.degrees((el - sh).angle(wr - el)))
            u = el - sh
            num['upper'][s].append(math.degrees(math.atan2(u.y, -u.z)))
            num['hand_z'].append(wr.z)
            th, kn, an = pbs[nm(s, 'UpperLeg')].head, pbs[nm(s, 'LowerLeg')].head, pbs[nm(s, 'Foot')].head
            k_ = math.degrees((kn - th).angle(an - kn))
            psi = ((f / float(NF)) + (0.0 if s == 'R' else 0.5)) % 1.0
            (num['knee_st'] if psi < gait['PH_TO'] else num['knee_sw']).append(k_)
    # rotation steps (60 fps and over two frames), acceleration kinks, seam
    def ang(a, b):
        x = math.degrees(a.rotation_difference(b).angle)
        return min(x, 360.0 - x)
    step1 = step2 = acc = 0.0
    at1 = at2 = atc = None
    for n in names:
        seq = [q[n] for q in qs[:NF]]
        sp = [ang(seq[i], seq[(i + 1) % NF]) for i in range(NF)]
        for i in range(NF):
            if sp[i] > step1:
                step1, at1 = sp[i], (n, i)
            s2 = ang(seq[i], seq[(i + 2) % NF])
            if s2 > step2:
                step2, at2 = s2, (n, i)
            d = abs(sp[i] - sp[i - 1])
            if d > acc:
                acc, atc = d, (n, i)
    seam = max(ang(qs[0][n], qs[NF][n]) for n in names)
    bob = max(num['head_z']) - min(num['head_z'])
    out = dict(slide_mm=round(slide * 1000, 2), slide_at=slide_at, ground_speed_m_s=round(sum(speeds) / max(1, len(speeds)), 3),
               contact_pairs=len(speeds), joint_step_60fps_deg=(round(step1, 2), at1), joint_step_30fps_deg=(round(step2, 2), at2),
               accel_step_deg=(round(acc, 2), atc), seam_deg=round(seam, 4),
               arms=dict(sorted(arms_tot.items())), hand_gap_mm={s: (round(min(v) * 1000, 1), round(max(v) * 1000, 1)) for s, v in gaps.items()},
               forearm_twist_deg=round(tw, 1), tail_gap_mm=round(worst['tail_gap'] * 1000, 1), tail_at=worst.get('tail_at'),
               leg_gap_mm=round(worst['leg_gap'] * 1000, 1), sole_min_mm=round(worst['sole_min'] * 1000, 1),
               trunk_lean_deg=(round(min(num['trunk']), 1), round(sum(num['trunk']) / NF, 1), round(max(num['trunk']), 1)),
               head_ahead_of_hips_m=round(sum(num['head_ahead']) / NF, 3),
               upper_arm_deg={s: (round(min(v), 1), round(max(v), 1)) for s, v in num['upper'].items()},
               elbow_deg=(round(min(num['elbow']), 1), round(max(num['elbow']), 1)),
               hand_z_m=(round(min(num['hand_z']), 3), round(max(num['hand_z']), 3)),
               knee_stance_deg=(round(min(num['knee_st']), 1), round(max(num['knee_st']), 1)),
               knee_swing_max_deg=round(max(num['knee_sw']), 1),
               pelvis_z_m=(round(min(num['pelvis']), 3), round(max(num['pelvis']), 3)),
               head_bob_mm=round(bob * 1000, 1), head_bob_game_px=round(bob * 1440.0 / 4.4, 1))
    return out


if bpy.app.background and '--' in sys.argv:
    argv = sys.argv[sys.argv.index('--') + 1:]
    name = argv[0] if argv else 'Yoru_Lauf'
    res = check(name)
    for k, v in res.items():
        print('[lauf_v2 check]', k, v, flush=True)
