"""
Yoru - AIM SUITE STAGE 2, round 1 (2026-10-31): the transitions into and out of the approved aim pose V2 (Blender/Yoru_Aim.blend), 60 fps.
Spec: Blender/work/Aim/suite_spec_from_gemini.md lines 11-19 and 35-50 plus the brief of the main agent (clearance 15 mm below / 5 mm above the
belt line z = 1.00 m, steps <= 15 deg per frame, forearm roll <= 18, wrist roll <= 12, gaze within 1 deg of V2, no clip stretched).
Steps (absolute paths; each step saves the working file and adds a line to Blender/work/Aim/Yoru_Aim_s2_progress.md):
  blender -b --factory-startup C:/Users/valen/ZeroProtocol/Blender/Yoru_Aim.blend --python C:/Users/valen/ZeroProtocol/Blender/scripts/build_aim_s2.py -- step=init
  blender -b --factory-startup C:/Users/valen/ZeroProtocol/Blender/work/Aim/Yoru_Aim_s2.blend --python .../build_aim_s2.py -- step=in   [design=1]
  ... step=out [design=1],  step=sprint [design=1],  step=analyze (prints the decomposed arm parameters of idle frame 0, V2 and the sprint)
  design=1 measures every frame (mesh clearance, steps, rolls ...) and prints a table WITHOUT saving.
init     opens Yoru_Aim.blend (read only) and saves it as Blender/work/Aim/Yoru_Aim_s2.blend, scene 60 fps.
in       Yoru_Aim_In (frames 0..12), Yoru_Aim_In_Layer (spine and up incl. arms, fingers, eyes, ears, hair, bust; no hips keys),
         Yoru_Aim_In_Stand (hips rotation + location, legs, feet, toes, tail = V2 stand = Idle_v2 frame 0, constant).
out      Yoru_Aim_Out (frames 0..15), _Layer, _Stand (constant V2 stand).
sprint   Yoru_Sprint_To_Aim (frames 0..11), _Layer, _Stand (the sprint's lower body from the chosen phase, faded into the V2 stand).
Every action: rotation keys only (plus the hips location where the source has it), one key per frame, linear interpolation.
Arms: animated through the parameters of build_aim_s2_lib.py (upper-arm pitch / tilt, bend plane, elbow flexion, twists, wrist quaternion),
keyed as FK local rotations (no IK constraint in the file).  Blender: +Y forward, her right = +X, up = +Z.
"""
import bpy, sys, os, math, json, time
sys.path.insert(0, r'C:\Users\valen\ZeroProtocol\Blender\scripts')
import importlib
import build_aim_s2_lib as L
importlib.reload(L)
from mathutils import Vector, Quaternion, Matrix

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
KV = dict(a.split('=', 1) for a in argv if '=' in a)
STEP = KV.get('step', 'analyze')
DESIGN = KV.get('design') == '1'
log = L.log


def save_work(note):
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=L.WORK)
    log('saved', L.WORK)
    L.progress(note)


# ------------------------------------------------------------------ step init
if STEP == 'init':
    assert os.path.normcase(bpy.data.filepath) == os.path.normcase(L.AIM_BLEND), 'init must open Blender/Yoru_Aim.blend'
    sc = bpy.context.scene
    sc.render.fps, sc.render.fps_base = L.FPS, 1.0
    os.makedirs(os.path.dirname(L.WORK), exist_ok=True)
    save_work('init: `Blender/work/Aim/Yoru_Aim_s2.blend` = Speichern unter aus `Blender/Yoru_Aim.blend` (unverändert, Szene 60 fps)')
    log('DONE init')
    sys.exit(0)

assert os.path.normcase(bpy.data.filepath) == os.path.normcase(L.WORK), 'open the working file Blender/work/Aim/Yoru_Aim_s2.blend'
rig = L.Rig()
scene = rig.scene
POSE_FULL = bpy.data.actions['Yoru_Aim_Pose_V2_full']
LAYER_BONES = sorted({L.bone_of(fc.data_path) for fc in L.fcurves_of(bpy.data.actions['Yoru_Aim_Pose_V2']) if L.bone_of(fc.data_path)})
STAND_BONES = sorted({L.bone_of(fc.data_path) for fc in L.fcurves_of(bpy.data.actions['Yoru_Aim_Pose_V2_Stand']) if L.bone_of(fc.data_path)})
KEYED = LAYER_BONES + STAND_BONES
HUMANOID = {n for n in KEYED if n.startswith('J_Bip_') or n.startswith('J_Adj_')}

# idle frame 0 and V2 (local rotations, hips location)
IDLE_ACT = L.append_action(L.IDLE_BLEND, 'Yoru_Idle_v2')
(Q_IDLE0, LOC_IDLE0), = L.read_action(IDLE_ACT, [0.0])[0]
(Q_V2, LOC_V2), = L.read_action(POSE_FULL, [0.0])[0]
assert set(Q_IDLE0) == set(Q_V2) == set(KEYED), 'bone sets differ'
dev_body = max((L.qang(Q_IDLE0[n], Q_V2[n]), n) for n in KEYED if n not in rig.ARM_BONES and n not in ('J_Bip_C_UpperChest', 'J_Bip_C_Head'))
log('V2 vs idle frame 0 outside arms / UC / head: %.6f deg (%s), hips loc %.6f mm' % (dev_body[0], dev_body[1], (LOC_IDLE0 - LOC_V2).length * 1000))


def fk_of(q, loc, names=None):
    return rig.fk(lambda n: q.get(n, Quaternion()), lambda n: loc if n == 'J_Bip_C_Hips' else None, names)


def arm_params_of(q, loc):
    D, P = fk_of(q, loc)
    return {s: rig.decompose(s, D, P, q[rig.ARM3[s][2]]) for s in 'LR'}, D, P


def recon_check(q, loc, label):
    """rebuild the arm local rotations from the decomposed parameters; must match to ~1e-5 deg"""
    prm, D, P = arm_params_of(q, loc)
    err = 0.0
    for s in 'LR':
        up = rig.ARM3[s][0]
        q_ua, q_fa, Du, Df = rig.arm_local(s, prm[s], D[rig.PARENT[up]])
        err = max(err, L.qang(q_ua, q[up]), L.qang(q_fa, q[rig.ARM3[s][1]]))
    log('reconstruction %s: max %.6f deg' % (label, err))
    return prm


def fmt_p(p):
    return 'beta %7.2f gamma %6.2f tau %7.2f flex %6.2f tw_u %7.2f tw_e %7.2f' % (p['beta'], p['gamma'], p['tau'], p['flex'], p['tw_u'], p['tw_e'])


PRM_IDLE0 = recon_check(Q_IDLE0, LOC_IDLE0, 'idle frame 0')
PRM_V2 = recon_check(Q_V2, LOC_V2, 'V2')

if STEP == 'analyze':
    for s in 'RL':
        log('IDLE0 %s %s' % (s, fmt_p(PRM_IDLE0[s])))
        log('V2    %s %s' % (s, fmt_p(PRM_V2[s])))
        log('      %s hand local idle0 -> V2 %.2f deg, fingers max %.2f deg' % (s, L.qang(PRM_IDLE0[s]['qh'], PRM_V2[s]['qh']),
                                                                            max(L.qang(Q_IDLE0[n], Q_V2[n]) for n in rig.FINGERS[s])))
    # the sprint: per frame arm parameters, hand / pistol heights relative to the chest, symmetry
    SPR = L.append_action(L.SPRINT_BLEND, L.SPRINT_ACT)
    frames = list(range(0, 37))
    data, spr_bones = L.read_action(SPR, [float(f) for f in frames])
    log('sprint keyed bones %d; not in the aim key set: %s; aim bones not keyed in the sprint: %s' % (
        len(spr_bones), sorted(set(spr_bones) - set(KEYED)), sorted(set(KEYED) - set(spr_bones))))
    fing_dev = max(L.qang(data[0][0][n], Q_V2[n]) for s in 'LR' for n in rig.FINGERS[s])
    log('sprint fingers vs V2 grip: max %.3f deg' % fing_dev)
    rows = []
    for f, (q, loc) in zip(frames, data):
        prm, D, P = arm_params_of(q, loc)
        uc = P['J_Bip_C_UpperChest']
        hips, neck = P['J_Bip_C_Hips'], P['J_Bip_C_Neck']
        lean = math.degrees(math.atan2((neck - hips).y, (neck - hips).z))
        hd = (D['J_Bip_C_Head'] @ Vector((0.0, 1.0, 0.0))).normalized()
        gyaw, gpitch = math.degrees(math.atan2(hd.x, hd.y)), math.degrees(math.asin(hd.z))
        sl, sr = P['J_Bip_L_UpperArm'], P['J_Bip_R_UpperArm']
        shy = math.degrees(math.atan2((sr - sl).y, (sr - sl).x))
        hy = math.degrees(math.atan2((P['J_Bip_R_UpperLeg'] - P['J_Bip_L_UpperLeg']).y, (P['J_Bip_R_UpperLeg'] - P['J_Bip_L_UpperLeg']).x))
        r = dict(f=f, lean=lean, gyaw=gyaw, gpitch=gpitch, sh_yaw=shy, hip_yaw=hy, hips=list(hips))
        for s in 'RL':
            W = P[rig.ARM3[s][2]]
            r[s] = dict(W_rel_uc=list(W - uc), flex=prm[s]['flex'], beta=prm[s]['beta'], gamma=prm[s]['gamma'], tau=prm[s]['tau'],
                        tw_u=prm[s]['tw_u'], tw_e=prm[s]['tw_e'])
        r['sym_dz'] = (P[rig.ARM3['R'][2]] - P[rig.ARM3['L'][2]]).z
        r['sym_dy'] = (P[rig.ARM3['R'][2]] - P[rig.ARM3['L'][2]]).y
        rows.append(r)
        log('SPR f%2d lean %5.1f gaze %5.1f/%5.1f shoulders %5.1f hips %5.1f | R W-uc (%6.3f %6.3f %6.3f) flex %5.1f beta %6.1f | L W-uc (%6.3f %6.3f %6.3f) flex %5.1f beta %6.1f | dz %6.3f dy %6.3f' % (
            f, lean, gyaw, gpitch, shy, hy, *r['R']['W_rel_uc'], r['R']['flex'], r['R']['beta'], *r['L']['W_rel_uc'], r['L']['flex'], r['L']['beta'],
            r['sym_dz'], r['sym_dy']))
    json.dump(dict(idle0={s: {k: v for k, v in PRM_IDLE0[s].items() if k != 'qh'} for s in 'LR'},
                   V2={s: {k: v for k, v in PRM_V2[s].items() if k != 'qh'} for s in 'LR'}, sprint=rows),
              open(os.path.join(L.ROOT, 'work', 'Aim', 'Yoru_Aim_s2_analyze.json'), 'w'), indent=1)
    log('DONE analyze')
    sys.exit(0)

# ================================================================== the clip engine
UC, HEAD, NECK, HIPS = 'J_Bip_C_UpperChest', 'J_Bip_C_Head', 'J_Bip_C_Neck', 'J_Bip_C_Hips'
NON_ARM_LAYER = [n for n in LAYER_BONES if n not in rig.ARM_BONES]
CHAIN_ARMS = [n for n in rig.ORDER if n in set(rig.chain(rig.ARM3['L'][0]) + rig.chain(rig.ARM3['R'][0]))]
CHAIN_HEAD = rig.chain(HEAD)
IDENT = Quaternion()


def walk(v0, v1, vel):
    """per-frame values from v0 to v1: the per-interval velocities vel (any scale, may contain an overshoot) are scaled so the sum hits v1"""
    sc = (v1 - v0) / sum(vel)
    out = [v0]
    for v in vel:
        out.append(out[-1] + v * sc)
    out[-1] = v1
    return out


def lerp_list(a, b, w):
    return [a + (b - a) * x for x in w]


def gaze_of(D):
    g = (D[HEAD] @ Vector((0.0, 1.0, 0.0))).normalized()
    return math.degrees(math.atan2(g.x, g.y)), math.degrees(math.asin(max(-1.0, min(1.0, g.z))))


def solve_head(q, loc, q_head_base, target_yaw):
    """local yaw y (about the head's own up axis) on top of q_head_base so that the world gaze yaw = target_yaw"""
    def g_of(y):
        qq = dict(q)
        qq[HEAD] = q_head_base @ Quaternion((0.0, 1.0, 0.0), L.deg(y))
        D, P = fk_of(qq, loc, CHAIN_HEAD)
        return gaze_of(D)[0]
    y0, y1 = 0.0, -2.0
    g0, g1 = g_of(y0) - target_yaw, g_of(y1) - target_yaw
    for _ in range(12):
        if abs(g1) < 1e-6 or abs(g1 - g0) < 1e-12:
            break
        y2 = y1 - g1 * (y1 - y0) / (g1 - g0)
        y0, g0 = y1, g1
        y1, g1 = y2, g_of(y2) - target_yaw
    return q_head_base @ Quaternion((0.0, 1.0, 0.0), L.deg(y1)), y1


def wrist_q(s, Df, qh_base, pitch_extra=0.0, ulnar_extra=0.0):
    """hand local quaternion: qh_base plus an extra barrel pitch (+ = muzzle up, world) applied in world space"""
    ha = rig.ARM3[s][2]
    DH = Df @ (rig.R[ha] @ qh_base @ rig.R[ha].inverted())
    if abs(pitch_extra) > 1e-9:
        barrel = (DH @ Vector((rig.SX[s], 0.0, 0.0))).normalized()
        ax = barrel.cross(Vector((0.0, 0.0, 1.0)))
        if ax.length > 1e-6:
            DH = Quaternion(ax.normalized(), L.deg(pitch_extra)) @ DH
    return rig.R[ha].inverted() @ Df.inverted() @ DH @ rig.R[ha]


def compose(N, frame_fn):
    """frame_fn(f) -> (q dict incl. everything, hips loc); returns lists"""
    Q, LOC = [], []
    for f in range(N + 1):
        q, loc = frame_fn(f)
        Q.append(q)
        LOC.append(loc)
    return Q, LOC


def fix_ends(Q, LOC, q_start, loc_start, q_end, loc_end, n_fade=3):
    """exact start and end: q(f) @ slerp(I, d0, fade-out) @ slerp(I, dN, fade-in); residuals are tiny (rounding of the parametrisation)"""
    N = len(Q) - 1
    res = {}
    for n in Q[0]:
        d0 = Q[0][n].inverted() @ q_start[n]
        dN = Q[N][n].inverted() @ q_end[n]
        res[n] = (L.qang(Q[0][n], q_start[n]), L.qang(Q[N][n], q_end[n]))
        for f in range(N + 1):
            a = max(0.0, 1.0 - f / float(n_fade))
            b = max(0.0, 1.0 - (N - f) / float(n_fade))
            Q[f][n] = Q[f][n] @ L.qlerp(IDENT, d0, a) @ L.qlerp(IDENT, dN, b)
    l0, lN = loc_start - LOC[0], loc_end - LOC[N]
    for f in range(N + 1):
        a = max(0.0, 1.0 - f / float(n_fade))
        b = max(0.0, 1.0 - (N - f) / float(n_fade))
        LOC[f] = LOC[f] + l0 * a + lN * b
    worst = max(((v[0], n, 'start') for n, v in res.items()), default=(0, '', ''))
    worst2 = max(((v[1], n, 'end') for n, v in res.items()), default=(0, '', ''))
    log('end fix: largest residual start %.4f deg (%s), end %.4f deg (%s)' % (worst[0], worst[1], worst2[0], worst2[1]))
    for f in range(N + 1):                                             # sign continuity for linear keys
        for n in Q[f]:
            ref = Q[f - 1][n] if f else (q_start[n])
            if Q[f][n].dot(ref) < 0:
                Q[f][n] = -Q[f][n]
    return Q, LOC


def steps_of(Q):
    out = []
    for f in range(1, len(Q)):
        for n in Q[f]:
            out.append((L.qang(Q[f - 1][n], Q[f][n]), n, f))
    out.sort(reverse=True)
    return out


def measure_all(Q, LOC, label):
    meter = L.Meter(rig)
    rows = []
    for f in range(len(Q)):
        L.apply_pose(rig, Q[f], LOC[f])
        r = meter.measure()
        r['frame'] = f
        rows.append(r)
    return rows, meter


def print_table(rows, label):
    log('== %s: mm to gear below (low) / above (up) the belt line 1.00 m; cut = arm triangle pairs, pc = pistol triangle pairs in the gear' % label)
    log('  f |  R armL armU elbL elbU pisL pisU cut pc self eo   fr    wr  bp   by  |  L armL armU elbL elbU pisL pisU cut pc self eo   fr    wr  bp   by  | gaze  lean')
    for r in rows:
        def side(s):
            return '%5.1f%5.1f%5.1f%5.1f%5.1f%5.1f %3d %2d %d%d %4.1f %5.1f %5.1f %4.0f %4.0f' % (
                r['arm_low_' + s], r['arm_up_' + s], r['elb_low_' + s], r['elb_up_' + s], min(r['pis_low_' + s], 999), min(r['pis_up_' + s], 999),
                r['cut_' + s], r['pcut_' + s], r['self_hit_' + s], r['self_hit_any_' + s], r['elbow_out_' + s], r['froll_' + s], r['wroll_' + s],
                r['barrel_pitch_' + s], r['barrel_yaw_' + s])
        log(' %2d | %s | %s | %5.2f %5.1f' % (r['frame'], side('R'), side('L'), r['head_yaw'], r['lean']))
    for r in rows:
        for s in 'RL':
            bad = []
            if r['cut_' + s]:
                bad.append('cut at %s' % r.get('cut_at_' + s))
            for k, lim in (('arm_low', 15), ('elb_low', 15), ('arm_up', 5), ('elb_up', 5)):
                if r['%s_%s' % (k, s)] < lim:
                    bad.append('%s %.1f at %s' % (k, r['%s_%s' % (k, s)], r.get('%s_at_%s' % (k, s))))
            if bad:
                log('   f%d %s: %s' % (r['frame'], s, '; '.join(bad)))


# ------------------------------------------------------------------ writing actions (one key per frame, linear)
def new_action(name, Q, LOC, bones, with_loc):
    old = bpy.data.actions.get(name)
    if old is not None:
        old.name = name + '_old'
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    slot = act.slots.new(id_type='OBJECT', name=rig.arm.name)
    layer = act.layers.new('Layer')
    strip = layer.strips.new(type='KEYFRAME')
    cb = strip.channelbag(slot, ensure=True)
    N = len(Q) - 1
    for n in bones:
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        for i in range(4):
            fc = cb.fcurves.new(dp, index=i, group_name=n)
            fc.keyframe_points.add(N + 1)
            co = []
            for f in range(N + 1):
                co += [float(f), float(Q[f][n][i])]
            fc.keyframe_points.foreach_set('co', co)
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            fc.update()
    if with_loc:
        dp = 'pose.bones["%s"].location' % HIPS
        for i in range(3):
            fc = cb.fcurves.new(dp, index=i, group_name=HIPS)
            fc.keyframe_points.add(N + 1)
            co = []
            for f in range(N + 1):
                co += [float(f), float(LOC[f][i])]
            fc.keyframe_points.foreach_set('co', co)
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
            fc.update()
    if old is not None:
        bpy.data.actions.remove(old)
    return act


def write_clip(name, Q, LOC):
    full = new_action(name, Q, LOC, KEYED, True)
    lay = new_action(name + '_Layer', Q, LOC, LAYER_BONES, False)
    sta = new_action(name + '_Stand', Q, LOC, STAND_BONES, True)
    ad = rig.arm.animation_data
    ad.use_nla = True
    L.set_action(rig.arm, full)
    scene.frame_start, scene.frame_end = 0, len(Q) - 1
    scene.frame_set(0)
    log('actions written: %s (%d bones + hips location), %s (%d), %s (%d + hips location)' % (full.name, len(KEYED), lay.name, len(LAYER_BONES),
                                                                                            sta.name, len(STAND_BONES)))
    return full, lay, sta


def summary(rows, steps, label, holster):
    """the numbers for the progress line and the report; holster[side] = frames in which the pistol is in / leaving / entering the holster"""
    s = {}
    for side in 'RL':
        for k in ('arm_low', 'arm_up', 'elb_low', 'elb_up'):
            m = min(rows, key=lambda r: r['%s_%s' % (k, side)])
            s['%s_%s' % (k, side)] = (round(m['%s_%s' % (k, side)], 1), m['frame'])
        for k in ('pis_low', 'pis_up'):
            rr = [r for r in rows if r['frame'] not in holster[side]]
            m = min(rr, key=lambda r: r['%s_%s' % (k, side)]) if rr else None
            s['%s_%s' % (k, side)] = (round(m['%s_%s' % (k, side)], 1), m['frame']) if m else None
        s['cut_' + side] = sum(r['cut_' + side] for r in rows)
        s['pcut_frames_' + side] = [r['frame'] for r in rows if r['pcut_' + side] > 0]
        s['self_hit_frames_' + side] = [r['frame'] for r in rows if (r['self_hit_' + side] or r['self_hit_any_' + side]) and r['frame'] not in holster[side]]
        s['elbow_out_max_' + side] = round(max(r['elbow_out_' + side] for r in rows), 2)
        s['froll_max_' + side] = round(max(abs(r['froll_' + side]) for r in rows), 2)
        s['wroll_max_' + side] = round(max(abs(r['wroll_' + side]) for r in rows), 2)
    s['gaze_yaw'] = (round(min(r['head_yaw'] for r in rows), 3), round(max(r['head_yaw'] for r in rows), 3))
    s['step_top'] = [(round(a, 2), n, f) for a, n, f in steps[:6]]
    return s


def design_render(Q, LOC, out_dir, tag, frames=None, views=('front', 'right', 'top', 'f34')):
    """quick orthographic workbench pictures of the design poses (scratch only)"""
    os.makedirs(out_dir, exist_ok=True)
    sc = scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'MATERIAL'
    sc.render.resolution_x, sc.render.resolution_y = 520, 620
    for o in bpy.data.objects:
        if o.name.startswith('Icosphere'):
            o.hide_render = True
    cams = {}
    T = Vector((0.05, 0.1, 1.0))
    for k, loc in {'front': (0.05, 5.0, 1.0), 'right': (5.0, 0.1, 1.0), 'top': (0.05, 0.1, 6.0), 'f34': (3.5, 3.5, 1.4), 'left': (-5.0, 0.1, 1.0)}.items():
        cd = bpy.data.cameras.new('dc_' + k)
        cd.type = 'ORTHO'
        cd.ortho_scale = 1.0
        ob = bpy.data.objects.new('dc_' + k, cd)
        sc.collection.objects.link(ob)
        ob.location = loc
        up = 'Y' if k == 'top' else 'Y'
        ob.rotation_euler = (T - Vector(loc)).to_track_quat('-Z', 'Y').to_euler() if k != 'top' else (0.0, 0.0, math.pi)
        cams[k] = ob
    for f in (frames or range(len(Q))):
        L.apply_pose(rig, Q[f], LOC[f])
        for v in views:
            sc.camera = cams[v]
            sc.render.filepath = os.path.join(out_dir, '%s_f%02d_%s.png' % (tag, f, v))
            bpy.ops.render.render(write_still=True)
    log('design pictures in', out_dir)


# ================================================================== Yoru_Aim_In
def spec_aim_in():
    N = 12
    # upper-arm pitch: snappy start, nearly flat top (<= 13.5 deg per frame), fast ease-out into frame 9 with a 1 deg overshoot, settle 10..12
    VB = [5.0, 11.0, 13.0, 13.5, 13.5, 13.5, 13.0, 11.0, 6.2, -0.6, -0.32, -0.10]
    # forearm angle (upper-arm pitch + flexion): up to level by frame 5-6, then the barrel stays level while the arm presses out
    AW = [0.0, 0.07, 0.25, 0.52, 0.80, 0.96, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    SM = [L.cubic_ease(f / 9.0) for f in range(N + 1)]                # twists, tilt, bend plane: 0..9
    FING = [0.0, 0.22, 0.46, 0.68, 0.84, 0.94, 0.985, 1.0] + [1.0] * (N - 7)
    UCW = [0.0] * 5 + [L.cubic_ease((f - 5) / 4.0) for f in range(5, 10)] + [1.0] * 3
    PITCH_OS = [0, 0, 0, 0, 0, 0, 0, 0.3, 0.9, 1.5, 0.8, 0.25, 0.0]   # barrel pitch overshoot (deg, muzzle up), peak at frame 9
    arms = {}
    for s in 'LR':
        p0, p1 = PRM_IDLE0[s], PRM_V2[s]
        beta = walk(p0['beta'], p1['beta'], VB)
        A0, A1 = p0['beta'] + p0['flex'], p1['beta'] + p1['flex']
        A = lerp_list(A0, A1, AW)
        flex = [A[f] - beta[f] for f in range(N + 1)]
        G = float(OPT.get('gmax' + s, OPT.get('gmax', 22.5)))            # elbows out to this tilt while they pass the vest side (<= V2 + 1 cm)
        gw = [0.0, 0.55, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.62, 0.22, 0.06, 0.01, 0.0]
        gamma = [p0['gamma'] + (p1['gamma'] - p0['gamma']) * SM[f] for f in range(N + 1)]
        gamma = [gamma[f] + (max(G, gamma[f]) - gamma[f]) * gw[f] for f in range(N + 1)]
        tub = float(OPT.get('twu', 0.0)) * (1.0 if s == 'R' else -1.0)   # optional upper-arm twist bump while passing the vest
        tw_u = [p0['tw_u'] + (p1['tw_u'] - p0['tw_u']) * SM[f] + tub * gw[f] for f in range(N + 1)]
        fb = float(OPT.get('flexadd', 0.0))
        flex = [flex[f] + fb * gw[f] for f in range(N + 1)]
        tb_ = float(OPT.get('tau' + s, 0.0))                             # bend plane bump (- = hand outward) around frame 2
        tbw = [0.0, 0.6, 1.0, 0.6, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        tau = [p0['tau'] + (p1['tau'] - p0['tau']) * SM[f] + tb_ * tbw[f] for f in range(N + 1)]
        arms[s] = dict(beta=beta, flex=flex, gamma=gamma, tau=tau,
                       tw_u=tw_u, tw_e=lerp_list(p0['tw_e'], p1['tw_e'], SM), qh_w=AW, pitch_os=PITCH_OS,
                       fing=FING)
    return dict(N=N, arms=arms, ucw=UCW)


D_I0, P_I0 = fk_of(Q_IDLE0, LOC_IDLE0)
D_V2, P_V2 = fk_of(Q_V2, LOC_V2)
GAZE_I0, GAZE_V2 = gaze_of(D_I0), gaze_of(D_V2)
PRM_GAZE0 = GAZE_I0[0]
log('gaze idle frame 0 %.3f / %.3f, V2 %.4f / %.3f' % (GAZE_I0[0], GAZE_I0[1], GAZE_V2[0], GAZE_V2[1]))


def build_transition(spec, q_start, loc_start, q_end, loc_end, stand_fn, body_fn, head_base_fn, gaze_fn):
    N = spec['N']
    arms = spec['arms']

    def frame(f):
        q, loc = stand_fn(f)
        q = dict(q)
        for n in NON_ARM_LAYER:
            q[n] = body_fn(n, f)
        D, P = fk_of(q, loc, CHAIN_ARMS)
        for s in 'LR':
            a = arms[s]
            prm = {k: a[k][f] for k in ('beta', 'gamma', 'tau', 'flex', 'tw_u', 'tw_e')}
            up, lo, ha = rig.ARM3[s]
            q_ua, q_fa, Du, Df = rig.arm_local(s, prm, D[rig.PARENT[up]])
            qh_base = L.qlerp(a['qh0'], a['qh1'], a['qh_w'][f])
            q[up], q[lo] = q_ua, q_fa
            q[ha] = wrist_q(s, Df, qh_base, a['pitch_os'][f])
            for n in rig.FINGERS[s]:
                q[n] = L.qlerp(q_start[n], q_end[n], a['fing'][f])
        q[HEAD], y = solve_head(q, loc, head_base_fn(f), gaze_fn(f))
        return q, loc
    if OPT.get('_want_frame_fn'):
        return frame
    Q, LOC = compose(N, frame)
    Q, LOC = fix_ends(Q, LOC, q_start, loc_start, q_end, loc_end)
    return Q, LOC


def gamma_search(sp, frame_fn, frames, crit_elb=0.5, gmax=34.0):
    """per frame and side the smallest outward tilt (gamma) with no arm triangle in the gear and the elbow end >= crit_elb mm from it"""
    meter = L.Meter(rig)
    need = {s: {} for s in 'LR'}
    for f in frames:
        for s in 'LR':
            g0 = sp['arms'][s]['gamma'][f]
            g = g0
            while True:
                sp['arms'][s]['gamma'][f] = g
                q, loc = frame_fn(f)
                L.apply_pose(rig, q, loc)
                r = meter.measure()
                if (r['cut_' + s] == 0 and r['elb_up_' + s] >= crit_elb and r['elb_low_' + s] >= crit_elb) or g >= gmax:
                    break
                g += 0.5
            need[s][f] = (g, r['elbow_out_' + s], r['elb_up_' + s], r['arm_up_' + s], r['arm_low_' + s])
            sp['arms'][s]['gamma'][f] = g0
            log('gamma search f%d %s: gamma %.1f (base %.1f) elbow out %.2f cm, elbow end %.1f mm, forearm up %.1f / low %.1f mm' % (
                f, s, g, g0, r['elbow_out_' + s], r['elb_up_' + s], r['arm_up_' + s], r['arm_low_' + s]))
    return need


# ================================================================== Yoru_Aim_Out
def spec_aim_out():
    """V2 -> low ready at frame 4 (elbows 45 deg, barrels tipped 25 deg down to the little-finger side) -> Idle_v2 frame 0 at frame 15"""
    N = 15
    VB1 = [4.5, 9.0, 10.0, 8.0]                                         # frames 0..4: the upper arm drops while the elbow bends
    VB2 = [2.5, 5.0, 8.0, 10.0, 11.0, 10.5, 9.0, 6.5, 3.5, 1.2, 0.3]   # frames 4..15: ease-in-out down to the gear
    FLEX4 = float(OPT.get('flex4', 45.0))
    TIP = float(OPT.get('tip', 25.0))
    C2 = [0.0]
    for v in VB2:
        C2.append(C2[-1] + v)
    C2 = [x / C2[-1] for x in C2]                                      # 0..1 over frames 4..15
    SMO = [L.cubic_ease(f / 15.0) for f in range(N + 1)]
    FING = [0.0] * 9 + [0.0, 0.06, 0.2, 0.42, 0.66, 0.88, 1.0]          # frames 9..15: the hand lets go of the grip as the pistol goes home
    TIPW = [L.cubic_ease(f / 4.0) for f in range(5)] + [1.0 - C2[f - 4] for f in range(5, N + 1)]
    arms = {}
    ADROP = float(OPT.get('adrop', 7.0))                                # the forearm tips this much below its V2 line by frame 4, so the
    for s in 'LR':                                                      # wrist only adds the rest of the 25 deg (wrist bend stays < 35)
        p0, p1 = PRM_V2[s], PRM_IDLE0[s]                                 # from V2 to the idle
        A0 = p0['beta'] + p0['flex']
        A4 = A0 - ADROP
        b4 = A4 - FLEX4
        beta = walk(p0['beta'], b4, VB1)
        flex = [A0 + (A4 - A0) * L.cubic_ease(f / 4.0) - beta[f] for f in range(5)]
        A1 = p1['beta'] + p1['flex']
        for k in range(1, len(C2)):
            c = C2[k]
            beta.append(b4 + (p1['beta'] - b4) * c)
            flex.append(FLEX4 + (p1['flex'] - FLEX4) * c)
        arms[s] = dict(beta=beta, flex=flex, gamma=lerp_list(p0['gamma'], p1['gamma'], SMO), tau=lerp_list(p0['tau'], p1['tau'], SMO),
                       tw_u=lerp_list(p0['tw_u'], p1['tw_u'], SMO), tw_e=lerp_list(p0['tw_e'], p1['tw_e'], SMO),
                       qh_w=[0.0] * 4 + [C2[f - 4] for f in range(4, N + 1)], pitch_os=[-(TIP - ADROP) * w for w in TIPW], fing=FING)
    ua_, ub_ = int(OPT.get('ucw_a', 2)), int(OPT.get('ucw_b', 10))
    ucw = [1.0 - L.cubic_ease((f - ua_) / float(ub_ - ua_)) for f in range(N + 1)]   # upper chest +8 -> 0 (weight towards V2)
    tb_ = float(OPT.get('tauR', 0.0))                                   # right bend plane bump (- = hand outward) where the hand passes the hip pouch
    tbw = [float(x) for x in OPT.get('tauw', '0,0,0,0,0,0,0,0,0,0.3,0.7,1,0.8,0.4,0.1,0').split(',')]
    arms['R']['tau'] = [arms['R']['tau'][f] + tb_ * tbw[f] for f in range(N + 1)]
    return dict(N=N, arms=arms, ucw=ucw)


OPT = dict(KV)
if STEP == 'gsearch_in':
    sp = spec_aim_in()
    for s in 'LR':
        sp['arms'][s]['qh0'], sp['arms'][s]['qh1'] = PRM_IDLE0[s]['qh'], PRM_V2[s]['qh']
    ucw = sp['ucw']
    OPT['_want_frame_fn'] = True
    gz = [GAZE_I0[0] + (GAZE_V2[0] - GAZE_I0[0]) * L.cubic_ease(f / 4.0) for f in range(sp['N'] + 1)]
    ffn = build_transition(sp, Q_IDLE0, LOC_IDLE0, Q_V2, LOC_V2, lambda f: ({n: Q_V2[n] for n in STAND_BONES}, LOC_V2.copy()),
                           lambda n, f: L.qlerp(Q_IDLE0[UC], Q_V2[UC], ucw[f]) if n == UC else Q_V2[n], lambda f: Q_IDLE0[HEAD], lambda f: gz[f])
    need = gamma_search(sp, ffn, range(1, 9), crit_elb=float(KV.get('crit', 0.5)))
    json.dump({s: {str(f): v for f, v in d.items()} for s, d in need.items()},
              open(os.path.join(L.ROOT, 'work', 'Aim', 'Yoru_Aim_s2_gamma_search_in.json'), 'w'), indent=1)
    sys.exit(0)

if STEP == 'sweep_in':
    meter = None
    for combo in KV.get('combos', '').split(';'):
        OPT = dict(kv.split(':') for kv in combo.split(',') if ':' in kv)
        sp = spec_aim_in()
        for s in 'LR':
            sp['arms'][s]['qh0'], sp['arms'][s]['qh1'] = PRM_IDLE0[s]['qh'], PRM_V2[s]['qh']
        ucw = sp['ucw']
        BW = [0.0, 0.55, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.62, 0.22, 0.06, 0.01, 0.0]
        cu, cb, uy = float(OPT.get('clav_up', 0)), float(OPT.get('clav_back', 0)), float(OPT.get('ucy', 0))

        def body_sw(n, f):
            if n == UC:
                return L.qlerp(Q_IDLE0[UC], Q_V2[UC], ucw[f]) @ Quaternion((0.0, 1.0, 0.0), L.deg(uy * BW[f]))
            for s in 'LR':
                if n == rig.CLAV[s]:
                    sx = rig.SX[s]
                    return Q_V2[n] @ Quaternion((0.0, 0.0, 1.0), L.deg(sx * cu * BW[f])) @ Quaternion((0.0, 1.0, 0.0), L.deg(-sx * cb * BW[f]))
            return Q_V2[n]
        Q, LOC = build_transition(sp, Q_IDLE0, LOC_IDLE0, Q_V2, LOC_V2, lambda f: ({n: Q_V2[n] for n in STAND_BONES}, LOC_V2.copy()),
                                  body_sw, lambda f: Q_IDLE0[HEAD],
                                  lambda f: GAZE_I0[0] + (GAZE_V2[0] - GAZE_I0[0]) * L.cubic_ease(f / 4.0))
        D3, P3 = fk_of(Q[4], LOC[4], CHAIN_ARMS)
        log('frame 4 shoulder joints R %s L %s' % (tuple(round(x, 3) for x in P3['J_Bip_R_UpperArm']), tuple(round(x, 3) for x in P3['J_Bip_L_UpperArm'])))
        meter = meter or L.Meter(rig)
        out = []
        for f in range(1, 9):
            L.apply_pose(rig, Q[f], LOC[f])
            r = meter.measure()
            out.append('f%d R e%.1f a%.1f/%.1f c%d eo%.1f | L e%.1f a%.1f/%.1f c%d eo%.1f' % (f, r['elb_up_R'], r['arm_low_R'], r['arm_up_R'], r['cut_R'], r['elbow_out_R'],
                                                                                   r['elb_up_L'], r['arm_low_L'], r['arm_up_L'], r['cut_L'], r['elbow_out_L']))
        st = steps_of(Q)
        log('SWEEP %s | step max %.2f %s f%d' % (combo, st[0][0], st[0][1], st[0][2]))
        for o in out:
            log('     ', o)
    sys.exit(0)

def apply_gamma_need(sp, need, margin, frames):
    """gamma(f) = max(planned, smallest clean tilt + margin) on the searched frames; returns the per-side curves"""
    for s in 'LR':
        g = sp['arms'][s]['gamma']
        for f in frames:
            g[f] = max(g[f], need[s][f][0] + margin)
        log('%s gamma after the vest search: %s' % (s, ' '.join('%.1f' % x for x in g)))


if STEP == 'in':
    # round-1 choices (tested 2026-10-31): right bend plane -10 deg at frame 2 (hand 20 mm off the hip pouch), early chest counter-turn -6 deg
    # (peak frame 3) and +8 deg between frames 4 and 9, shoulders lifted 6 deg while drawing: the smallest elbow tilt that clears the vest
    for k_, v_ in dict(gmax='0', tauR='-10', ucy='-6', clav_up='6', cw='early', ucw_a='4', ucw_b='9').items():
        OPT.setdefault(k_, v_)
    sp = spec_aim_in()
    for s in 'LR':
        sp['arms'][s]['qh0'], sp['arms'][s]['qh1'] = PRM_IDLE0[s]['qh'], PRM_V2[s]['qh']
    N = sp['N']
    stand_fn = lambda f: ({n: Q_V2[n] for n in STAND_BONES}, LOC_V2.copy())
    ucw = sp['ucw']

    BWB = [0.0, 0.55, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.62, 0.22, 0.06, 0.01, 0.0]
    CWB = [0.0, 0.5, 0.9, 1.0, 0.7, 0.3, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]   # counter-turn: early, gone when the right arm passes the vest
    ucy, cup = float(OPT.get('ucy', 0.0)), float(OPT.get('clav_up', 0.0))
    ua_, ub_ = int(OPT.get('ucw_a', 5)), int(OPT.get('ucw_b', 9))
    ucw = [L.cubic_ease((f - ua_) / float(ub_ - ua_)) for f in range(N + 1)]
    cwt = CWB if OPT.get('cw') == 'early' else BWB

    def body_fn(n, f):
        if n == UC:                                                    # +8 deg into the aim; optional small counter-turn (ucy < 0) while drawing
            return L.qlerp(Q_IDLE0[UC], Q_V2[UC], ucw[f]) @ Quaternion((0.0, 1.0, 0.0), L.deg(ucy * cwt[f]))
        for s_ in 'LR':
            if n == rig.CLAV[s_] and cup:
                return Q_V2[n] @ Quaternion((0.0, 0.0, 1.0), L.deg(rig.SX[s_] * cup * BWB[f]))
        return Q_V2[n]                                                 # identical to idle frame 0 outside UC / head / arms
    head_base_fn = lambda f: Q_IDLE0[HEAD]
    gz = [GAZE_I0[0] + (GAZE_V2[0] - GAZE_I0[0]) * L.cubic_ease(f / 4.0) for f in range(N + 1)]
    gaze_fn = lambda f: gz[f]
    OPT['_want_frame_fn'] = True
    ffn = build_transition(sp, Q_IDLE0, LOC_IDLE0, Q_V2, LOC_V2, stand_fn, body_fn, head_base_fn, gaze_fn)
    SEARCH_F = list(range(1, 10))
    need = gamma_search(sp, ffn, SEARCH_F, crit_elb=float(OPT.get('crit', 0.5)))
    apply_gamma_need(sp, need, float(OPT.get('margin', 0.5)), SEARCH_F)
    OPT['_want_frame_fn'] = False
    Q, LOC = build_transition(sp, Q_IDLE0, LOC_IDLE0, Q_V2, LOC_V2, stand_fn, body_fn, head_base_fn, gaze_fn)
    st = steps_of(Q)
    log('largest steps:', [(round(a, 2), n, f) for a, n, f in st[:8]])
    for s in 'RL':
        a = sp['arms'][s]
        log('%s beta %s' % (s, ' '.join('%6.1f' % x for x in a['beta'])))
        log('%s flex %s' % (s, ' '.join('%6.1f' % x for x in a['flex'])))
    rows, meter = measure_all(Q, LOC, 'Aim_In')
    print_table(rows, 'Yoru_Aim_In')
    for s in 'RL':
        log('%s wrist path: %s' % (s, ' '.join('(%.3f %.3f %.3f)' % tuple(r['wrist_' + s]) for r in rows)))
        log('%s muzzle path: %s' % (s, ' '.join('(%.3f %.3f %.3f)' % tuple(r['muzzle_' + s]) for r in rows)))
    if KV.get('render'):
        design_render(Q, LOC, KV['render'], 'in')
    if DESIGN:
        log('DESIGN only, nothing saved')
        sys.exit(0)
    write_clip('Yoru_Aim_In', Q, LOC)
    HOLSTER = {'R': [0, 1], 'L': [0, 1]}                               # frames 0..1: the pistol is in / leaving the holster
    summ = summary(rows, st, 'Aim_In', HOLSTER)
    json.dump(dict(clip='Yoru_Aim_In', frames=N + 1, fps=L.FPS, opts={k: v for k, v in OPT.items() if not k.startswith('_')},
                   gamma_need={s: {str(f): v for f, v in d.items()} for s, d in need.items()}, holster_frames=HOLSTER, summary=summ,
                   params={s: {k: sp['arms'][s][k] for k in ('beta', 'gamma', 'tau', 'flex', 'tw_u', 'tw_e')} for s in 'LR'}, rows=rows),
              open(os.path.join(L.ROOT, 'work', 'Aim', 'Yoru_Aim_s2_in.json'), 'w'), indent=1, default=str)
    save_work('Aim_In fertig: `Yoru_Aim_In` / `_Layer` / `_Stand` (13 Bilder, 60 fps) in `Blender/work/Aim/Yoru_Aim_s2.blend`; Messung (eigene, '
              'vor dem Speichern): Schnitte Arm %d/%d (R/L), Ellbogenende min %.1f/%.1f mm, Ellbogen außen max %.1f/%.1f cm, größter Schritt %.2f° (%s, Bild %d); '
              'Zahlen `Blender/work/Aim/Yoru_Aim_s2_in.json`' % (
                  summ['cut_R'], summ['cut_L'], min(summ['elb_up_R'][0], summ['elb_low_R'][0]), min(summ['elb_up_L'][0], summ['elb_low_L'][0]),
                  summ['elbow_out_max_R'], summ['elbow_out_max_L'], st[0][0], st[0][1], st[0][2]))
    log('DONE in')
    sys.exit(0)


if STEP == 'out':
    # round-1 choices (tested 2026-10-31): upper chest back to 0 within frames 0..4, then a small counter-turn (-2 deg) and a 6 deg shoulder
    # lift while the upper arms pass the vest side (frames 5..13), right bend plane -10 deg around frame 11 (hand past the hip pouch)
    for k_, v_ in dict(gmax='0', ucw_a='0', ucw_b='4', ucy='-2', clav_up='6', tauR='-10', adrop='7', tip='23.5').items():
        OPT.setdefault(k_, v_)
    sp = spec_aim_out()
    for s in 'LR':
        sp['arms'][s]['qh0'], sp['arms'][s]['qh1'] = PRM_V2[s]['qh'], PRM_IDLE0[s]['qh']
    N = sp['N']
    stand_fn = lambda f: ({n: Q_V2[n] for n in STAND_BONES}, LOC_V2.copy())
    ucw = sp['ucw']
    # optional helpers while the upper arms pass the vest side on the way down (as in Aim_In): chest counter-turn and a small shoulder lift
    PW = [float(x) for x in OPT.get('pw', '0,0,0,0,0,0.2,0.5,0.85,1,1,1,0.8,0.45,0.15,0,0').split(',')]
    ucy, cup = float(OPT.get('ucy', 0.0)), float(OPT.get('clav_up', 0.0))

    def body_fn(n, f):
        if n == UC:
            return L.qlerp(Q_IDLE0[UC], Q_V2[UC], ucw[f]) @ Quaternion((0.0, 1.0, 0.0), L.deg(ucy * PW[f]))
        for s_ in 'LR':
            if n == rig.CLAV[s_] and cup:
                return Q_V2[n] @ Quaternion((0.0, 0.0, 1.0), L.deg(rig.SX[s_] * cup * PW[f]))
        return Q_V2[n]
    head_base_fn = lambda f: Q_IDLE0[HEAD]
    gz = [GAZE_V2[0] + (GAZE_I0[0] - GAZE_V2[0]) * L.cubic_ease((f - 11) / 4.0) for f in range(N + 1)]
    gaze_fn = lambda f: gz[f]
    OPT['_want_frame_fn'] = True
    ffn = build_transition(sp, Q_V2, LOC_V2, Q_IDLE0, LOC_IDLE0, stand_fn, body_fn, head_base_fn, gaze_fn)
    SEARCH_F = list(range(1, N))
    need = gamma_search(sp, ffn, SEARCH_F, crit_elb=float(OPT.get('crit', 0.5)))
    apply_gamma_need(sp, need, float(OPT.get('margin', 0.5)), SEARCH_F)
    OPT['_want_frame_fn'] = False
    Q, LOC = build_transition(sp, Q_V2, LOC_V2, Q_IDLE0, LOC_IDLE0, stand_fn, body_fn, head_base_fn, gaze_fn)
    st = steps_of(Q)
    log('largest steps:', [(round(a, 2), n, f) for a, n, f in st[:8]])
    for s in 'RL':
        a = sp['arms'][s]
        log('%s beta %s' % (s, ' '.join('%6.1f' % x for x in a['beta'])))
        log('%s flex %s' % (s, ' '.join('%6.1f' % x for x in a['flex'])))
    rows, meter = measure_all(Q, LOC, 'Aim_Out')
    print_table(rows, 'Yoru_Aim_Out')
    for s in 'RL':
        log('%s wrist path: %s' % (s, ' '.join('(%.3f %.3f %.3f)' % tuple(r['wrist_' + s]) for r in rows)))
        log('%s muzzle path: %s' % (s, ' '.join('(%.3f %.3f %.3f)' % tuple(r['muzzle_' + s]) for r in rows)))
    if KV.get('render'):
        design_render(Q, LOC, KV['render'], 'out')
    if DESIGN:
        log('DESIGN only, nothing saved')
        sys.exit(0)
    write_clip('Yoru_Aim_Out', Q, LOC)
    HOLSTER = {s_: [f for f in range(N + 1) if f >= min([r['frame'] for r in rows if r['frame'] >= 8 and (r['pcut_' + s_] > 0 or r['pis_low_' + s_] < 1.0)] + [N])]
               for s_ in 'LR'}                                          # from the first frame the pistol touches / enters the holster gear
    log('holster frames (pistol limits off): R %s, L %s' % (HOLSTER['R'], HOLSTER['L']))
    summ = summary(rows, st, 'Aim_Out', HOLSTER)
    json.dump(dict(clip='Yoru_Aim_Out', frames=N + 1, fps=L.FPS, opts={k: v for k, v in OPT.items() if not k.startswith('_')},
                   gamma_need={s: {str(f): v for f, v in d.items()} for s, d in need.items()}, holster_frames=HOLSTER, summary=summ,
                   params={s: {k: sp['arms'][s][k] for k in ('beta', 'gamma', 'tau', 'flex', 'tw_u', 'tw_e')} for s in 'LR'}, rows=rows),
              open(os.path.join(L.ROOT, 'work', 'Aim', 'Yoru_Aim_s2_out.json'), 'w'), indent=1, default=str)
    save_work('Aim_Out fertig: `Yoru_Aim_Out` / `_Layer` / `_Stand` (16 Bilder, 60 fps) in `Blender/work/Aim/Yoru_Aim_s2.blend`; Messung (eigene, '
              'vor dem Speichern): Schnitte Arm %d/%d (R/L), Ellbogenende min %.1f/%.1f mm, Ellbogen außen max %.1f/%.1f cm, größter Schritt %.2f° (%s, Bild %d); '
              'Zahlen `Blender/work/Aim/Yoru_Aim_s2_out.json`' % (
                  summ['cut_R'], summ['cut_L'], min(summ['elb_up_R'][0], summ['elb_low_R'][0]), min(summ['elb_up_L'][0], summ['elb_low_L'][0]),
                  summ['elbow_out_max_R'], summ['elbow_out_max_L'], st[0][0], st[0][1], st[0][2]))
    log('DONE out')
    sys.exit(0)


# ================================================================== Yoru_Sprint_To_Aim
if STEP == 'sprint':
    # round-1 choices (tested 2026-10-31): sprint phase 24 (most symmetric hands), chest counter-turn -8 deg and shoulders lifted 6 deg while
    # the upper arms pass the vest (frames 1..8): the elbows never need more tilt than the sprint pose already has; gaze on the crosshair in 2 frames
    for k_, v_ in dict(gmax='0', phase='24', ucy='-8', clav_up='6', gaze_n='2').items():
        OPT.setdefault(k_, v_)
    PH = int(OPT['phase'])
    N = 11
    SPR = L.append_action(L.SPRINT_BLEND, L.SPRINT_ACT)
    spr, _b = L.read_action(SPR, [float(PH + k) for k in range(N + 1)])
    QS = [dict(q) for q, loc in spr]
    LS = [loc.copy() for q, loc in spr]
    NONHUM = [n for n in LAYER_BONES if not (n.startswith('J_Bip_') or n.startswith('J_Adj_'))]
    EYES = [n for n in LAYER_BONES if n.startswith('J_Adj_')]
    log('sprint phase %d: eyes vs idle frame 0: %s deg' % (PH, ', '.join('%s %.3f' % (n, L.qang(QS[0][n], Q_IDLE0[n])) for n in EYES)))
    # the start pose of the clip: the sprint frame PH for every humanoid bone and the lower body; hair, ears, bust, eyes = Idle_v2 frame 0 (rule)
    Q_S0 = dict(QS[0])
    for n in NONHUM + EYES:
        Q_S0[n] = Q_IDLE0[n]
    LOC_S0 = LS[0].copy()
    PRM_S0, D_S0, P_S0 = arm_params_of(Q_S0, LOC_S0)
    GAZE_S0 = gaze_of(D_S0)
    for s in 'RL':
        log('SPRINT%d %s %s' % (PH, s, fmt_p(PRM_S0[s])))
    log('sprint gaze %.2f / %.2f, lean (hips->neck) %.1f' % (GAZE_S0[0], GAZE_S0[1],
                                                             math.degrees(math.atan2((P_S0[NECK] - P_S0[HIPS]).y, (P_S0[NECK] - P_S0[HIPS]).z))))
    WST = [L.cubic_ease(f / float(N)) for f in range(N + 1)]            # stand: the running legs fade into the V2 stand
    WLY = [L.cubic_ease(f / 9.0) for f in range(N + 1)]                  # spine, chest, neck, shoulders: upright by frame 9

    STAND_MODE = OPT.get('stand', 'run')

    def stand_fn(f):
        if STAND_MODE == 'run':                                          # legs, feet, tail keep sprinting (preview only); the pelvis turns upright
            q = {n: QS[f][n] for n in STAND_BONES}
            q[HIPS] = L.qlerp(QS[f][HIPS], Q_V2[HIPS], WST[f])
            return q, LS[f].copy()
        q = {n: L.qlerp(QS[0][n], Q_V2[n], WST[f]) for n in STAND_BONES}  # 'stop': the frame-PH legs settle into the V2 stand
        return q, LS[0].lerp(LOC_V2, WST[f])

    PWS = [float(x) for x in OPT.get('pw', '0,0.4,0.8,1,1,1,0.8,0.5,0.2,0.05,0,0').split(',')]
    ucy, cup = float(OPT.get('ucy', 0.0)), float(OPT.get('clav_up', 0.0))

    def body_fn(n, f):
        if n in NONHUM or n in EYES:
            return Q_V2[n]
        q = L.qlerp(Q_S0[n], Q_V2[n], WLY[f])
        if n == UC and ucy:
            q = q @ Quaternion((0.0, 1.0, 0.0), L.deg(ucy * PWS[f]))
        for s_ in 'LR':
            if n == rig.CLAV[s_] and cup:
                q = q @ Quaternion((0.0, 0.0, 1.0), L.deg(rig.SX[s_] * cup * PWS[f]))
        return q
    head_base_fn = lambda f: L.qlerp(Q_S0[HEAD], Q_V2[HEAD], WLY[f])
    gz = [GAZE_S0[0] + (GAZE_V2[0] - GAZE_S0[0]) * L.cubic_ease(f / float(OPT['gaze_n'])) for f in range(N + 1)]
    gaze_fn = lambda f: gz[f]
    VB = [float(x) for x in OPT.get('vb', '4,9,11.5,12.5,12.5,12.5,11.5,9,6,3,1').split(',')]
    AW = [float(x) for x in OPT.get('aw', '0,0.1,0.3,0.55,0.78,0.93,1,1,1,1,1,1').split(',')]
    SM = [L.cubic_ease(f / 9.0) for f in range(N + 1)]
    arms = {}
    for s in 'LR':
        p0, p1 = PRM_S0[s], PRM_V2[s]
        beta = walk(p0['beta'], p1['beta'], VB)
        A0, A1 = p0['beta'] + p0['flex'], p1['beta'] + p1['flex']
        A = lerp_list(A0, A1, AW)
        arms[s] = dict(beta=beta, flex=[A[f] - beta[f] for f in range(N + 1)], gamma=lerp_list(p0['gamma'], p1['gamma'], SM),
                       tau=lerp_list(p0['tau'], p1['tau'], SM), tw_u=lerp_list(p0['tw_u'], p1['tw_u'], SM), tw_e=lerp_list(p0['tw_e'], p1['tw_e'], SM),
                       qh_w=AW, pitch_os=[0.0] * (N + 1), fing=[1.0] * (N + 1), qh0=p0['qh'], qh1=p1['qh'])
    sp = dict(N=N, arms=arms)
    q_end = dict(Q_V2)
    LOC_END = LOC_V2
    if STAND_MODE == 'run':
        qe, LOC_END = stand_fn(N)
        q_end.update(qe)
    OPT['_want_frame_fn'] = True
    ffn = build_transition(sp, Q_S0, LOC_S0, q_end, LOC_END, stand_fn, body_fn, head_base_fn, gaze_fn)
    SEARCH_F = list(range(1, N))
    need = gamma_search(sp, ffn, SEARCH_F, crit_elb=float(OPT.get('crit', 0.5)))
    apply_gamma_need(sp, need, float(OPT.get('margin', 0.5)), SEARCH_F)
    OPT['_want_frame_fn'] = False
    Q, LOC = build_transition(sp, Q_S0, LOC_S0, q_end, LOC_END, stand_fn, body_fn, head_base_fn, gaze_fn)
    st = steps_of(Q)
    log('largest steps:', [(round(a, 2), n, f) for a, n, f in st[:8]])
    for s in 'RL':
        a = sp['arms'][s]
        log('%s beta %s' % (s, ' '.join('%6.1f' % x for x in a['beta'])))
        log('%s flex %s' % (s, ' '.join('%6.1f' % x for x in a['flex'])))
    rows, meter = measure_all(Q, LOC, 'Sprint_To_Aim')
    print_table(rows, 'Yoru_Sprint_To_Aim')
    for s in 'RL':
        log('%s wrist path: %s' % (s, ' '.join('(%.3f %.3f %.3f)' % tuple(r['wrist_' + s]) for r in rows)))
        log('%s muzzle path: %s' % (s, ' '.join('(%.3f %.3f %.3f)' % tuple(r['muzzle_' + s]) for r in rows)))
    if KV.get('render'):
        design_render(Q, LOC, KV['render'], 'sprint')
    if DESIGN:
        log('DESIGN only, nothing saved')
        sys.exit(0)
    bpy.data.actions.remove(SPR)
    write_clip('Yoru_Sprint_To_Aim', Q, LOC)
    HOLSTER = {'R': [], 'L': []}                                       # the pistols stay in the hands
    summ = summary(rows, st, 'Sprint_To_Aim', HOLSTER)
    json.dump(dict(clip='Yoru_Sprint_To_Aim', frames=N + 1, fps=L.FPS, phase=PH, opts={k: v for k, v in OPT.items() if not k.startswith('_')},
                   gamma_need={s: {str(f): v for f, v in d.items()} for s, d in need.items()}, holster_frames=HOLSTER, summary=summ,
                   start_params={s: {k: v for k, v in PRM_S0[s].items() if k != 'qh'} for s in 'LR'}, start_gaze=GAZE_S0,
                   params={s: {k: sp['arms'][s][k] for k in ('beta', 'gamma', 'tau', 'flex', 'tw_u', 'tw_e')} for s in 'LR'}, rows=rows),
              open(os.path.join(L.ROOT, 'work', 'Aim', 'Yoru_Aim_s2_sprint.json'), 'w'), indent=1, default=str)
    save_work('Sprint_To_Aim fertig: `Yoru_Sprint_To_Aim` / `_Layer` / `_Stand` (12 Bilder, 60 fps, Sprintphase %d) in `Blender/work/Aim/Yoru_Aim_s2.blend`; '
              'Messung (eigene, vor dem Speichern): Schnitte Arm %d/%d (R/L), Ellbogenende min %.1f/%.1f mm, Ellbogen außen max %.1f/%.1f cm, '
              'größter Schritt %.2f° (%s, Bild %d); Zahlen `Blender/work/Aim/Yoru_Aim_s2_sprint.json`' % (
                  PH, summ['cut_R'], summ['cut_L'], min(summ['elb_up_R'][0], summ['elb_low_R'][0]), min(summ['elb_up_L'][0], summ['elb_low_L'][0]),
                  summ['elbow_out_max_R'], summ['elbow_out_max_L'], st[0][0], st[0][1], st[0][2]))
    log('DONE sprint')
    sys.exit(0)
