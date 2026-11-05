"""
Yoru - AIM SUITE STAGE 2: checks of the three transitions, measured on the SAVED file (saves nothing but the JSON).
  blender -b --factory-startup C:/Users/valen/ZeroProtocol/Blender/work/Aim/Yoru_Aim_s2.blend --python C:/Users/valen/ZeroProtocol/Blender/scripts/build_aim_s2_check.py
          -- <out .json>
Every frame of Yoru_Aim_In (0..12), Yoru_Sprint_To_Aim (0..11), Yoru_Aim_Out (0..15), each FULL action alone (no NLA):
  clearance per zone (definitions of aim_transition_scan.py / build_aim_s2_lib.Meter: belt line z = 1.00 m fixed in Yoru_Aim_Pose_V2_full;
  forearm + hand, elbow end of the upper arm, pistol), arm / pistol triangle pairs in the gear, pistol against the other pistol / forearm,
  elbow_out, elbow flexion, forearm / wrist roll (hinge definition), wrist bend, barrel yaw / pitch / cant, a ray from the muzzle along the
  barrel against the gear (1.5 m) and against every visible body polygon (3 m), gaze yaw / pitch, trunk lean (hips -> neck).
  Joint steps: largest single-frame change of the local rotation for every keyed bone, split into the layer bones and the stand bones.
  Union: the _Layer and _Stand actions together carry exactly the channels of the full action with the same values (max |diff|).
  End frames against the targets (local rotations of every keyed bone and the hips location): Aim_In 0 / Aim_Out 15 against Idle_v2 frame 0,
  Aim_In 12 / Aim_Out 0 / Sprint_To_Aim 11 (layer bones) against Yoru_Aim_Pose_V2_full, Sprint_To_Aim 0 against Yoru_Sprint_r6_L12 frame 24
  (humanoid bones and the lower body; hair, ears, bust and eyes follow the Idle_v2 frame-0 rule).
  Standing feet (Aim_In, Aim_Out): drift of the toe and foot joints over the clip.  Visible share of each pistol in the real game camera at the
  V2 end frames (and in V2 itself).  The face shape keys (static in the file) against Yoru_Idle_v2_Face frame 0.
"""
import bpy, sys, os, math, json, time
sys.path.insert(0, r'C:\Users\valen\ZeroProtocol\Blender\scripts')
import build_aim_s2_lib as L
from mathutils import Vector, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
CLIPS = [('Yoru_Aim_In', 12), ('Yoru_Sprint_To_Aim', 11), ('Yoru_Aim_Out', 15)]
log = L.log
rig = L.Rig()
scene = rig.scene
ad = rig.arm.animation_data
ad.use_nla = False
PB = rig.PB
LAYER_BONES = sorted({L.bone_of(fc.data_path) for fc in L.fcurves_of(bpy.data.actions['Yoru_Aim_Pose_V2']) if L.bone_of(fc.data_path)})
STAND_BONES = sorted({L.bone_of(fc.data_path) for fc in L.fcurves_of(bpy.data.actions['Yoru_Aim_Pose_V2_Stand']) if L.bone_of(fc.data_path)})
KEYED = LAYER_BONES + STAND_BONES
HUMAN = {n for n in KEYED if n.startswith('J_Bip_') or n.startswith('J_Adj_')}
NONHUM = [n for n in LAYER_BONES if n not in HUMAN]
EYES = [n for n in LAYER_BONES if n.startswith('J_Adj_')]

IDLE = L.append_action(L.IDLE_BLEND, 'Yoru_Idle_v2')
IDLE_FACE = L.append_action(L.IDLE_BLEND, 'Yoru_Idle_v2_Face')
SPR = L.append_action(L.SPRINT_BLEND, L.SPRINT_ACT)
(QI0, LI0), = L.read_action(IDLE, [0.0])[0]
(QV2, LV2), = L.read_action(bpy.data.actions['Yoru_Aim_Pose_V2_full'], [0.0])[0]
(QS24, LS24), = L.read_action(SPR, [24.0])[0]


def keys_of(act, f):
    (q, loc), = L.read_action(act, [float(f)])[0]
    return q, loc


def compare(q, loc, qt, lt, bones):
    worst = max(((L.qang(q[n], qt[n]), n) for n in bones), default=(0.0, ''))
    dl = (loc - lt).length * 1000.0 if (loc is not None and lt is not None) else 0.0
    return dict(max_deg=round(worst[0], 6), bone=worst[1], hips_loc_mm=round(dl, 6))


meter = L.Meter(rig)
FEET = None
res = dict(date='2026-10-31', stage=2, round=1, file=bpy.data.filepath, belt_m=L.BELT, clips={})
for name, N in CLIPS:
    act = bpy.data.actions[name]
    lay, sta = bpy.data.actions[name + '_Layer'], bpy.data.actions[name + '_Stand']
    fr = act.frame_range
    assert int(fr[0]) == 0 and int(fr[1]) == N, (name, tuple(fr))
    # union: layer + stand == full
    ch = {(fc.data_path, fc.array_index): fc for fc in L.fcurves_of(act)}
    un = {}
    dup = 0
    for a in (lay, sta):
        c = {(fc.data_path, fc.array_index): fc for fc in L.fcurves_of(a)}
        dup += len(set(un) & set(c))
        un.update(c)
    udiff = max(abs(ch[k].evaluate(f) - un[k].evaluate(f)) for k in set(ch) & set(un) for f in range(N + 1))
    union = dict(channels=len(ch), union_channels=len(un), missing=len(set(ch) - set(un)), extra=len(set(un) - set(ch)), in_both=dup,
                 max_abs_diff=udiff, layer_has_hips=any(L.bone_of(fc.data_path) == 'J_Bip_C_Hips' for fc in L.fcurves_of(lay)),
                 channel_types=sorted({fc.data_path.split('.')[-1] for fc in L.fcurves_of(act)}))
    # keys per frame
    Q, LOC = [], []
    for f in range(N + 1):
        q, loc = keys_of(act, f)
        Q.append(q)
        LOC.append(loc)
    steps = []
    for f in range(1, N + 1):
        for n in KEYED:
            steps.append((L.qang(Q[f - 1][n], Q[f][n]), n, f))
    steps.sort(reverse=True)
    st_layer = [x for x in steps if x[1] in LAYER_BONES]
    st_stand = [x for x in steps if x[1] in STAND_BONES]
    st_arm = [x for x in steps if x[1] in rig.ARM_BONES]
    # end frames
    ends = {}
    if name == 'Yoru_Aim_In':
        ends['frame0_vs_idle_v2_frame0'] = compare(Q[0], LOC[0], QI0, LI0, KEYED)
        ends['frame12_vs_V2'] = compare(Q[N], LOC[N], QV2, LV2, KEYED)
    elif name == 'Yoru_Aim_Out':
        ends['frame0_vs_V2'] = compare(Q[0], LOC[0], QV2, LV2, KEYED)
        ends['frame15_vs_idle_v2_frame0'] = compare(Q[N], LOC[N], QI0, LI0, KEYED)
    else:
        ends['frame11_layer_vs_V2'] = compare(Q[N], None, QV2, None, LAYER_BONES)
        hum = [n for n in KEYED if n in HUMAN and n not in EYES]
        ends['frame0_vs_sprint_f24_humanoid_and_stand'] = compare(Q[0], LOC[0], QS24, LS24, sorted(set(hum) | set(STAND_BONES)))
        ends['frame0_eyes_vs_sprint_f24'] = compare(Q[0], None, QS24, None, EYES)
        ends['frame0_hair_ears_bust_vs_idle_frame0'] = compare(Q[0], None, QI0, None, NONHUM)
        ends['frame11_hips_rotation_vs_V2_deg'] = round(L.qang(Q[N]['J_Bip_C_Hips'], QV2['J_Bip_C_Hips']), 6)
        ends['stand_legs_vs_sprint'] = max(L.qang(Q[f][n], keys_of(SPR, 24 + f)[0][n]) for f in range(N + 1) for n in STAND_BONES if n != 'J_Bip_C_Hips')
    # per-frame mesh measurements through the saved action
    L.set_action(rig.arm, act)
    rows = []
    toes = {s: [] for s in 'LR'}
    for f in range(N + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        r = meter.measure()
        r['frame'] = f
        for s in 'LR':
            toes[s].append((PB['J_Bip_%s_ToeBase' % s].head.copy(), PB['J_Bip_%s_Foot' % s].head.copy()))
            up, lo, ha = rig.ARM3[s]
            r['flex_' + s] = L.ang(PB[up].head - PB[lo].head, PB[ha].head - PB[lo].head)
            r['flex_' + s] = 180.0 - r['flex_' + s]
        rows.append(r)
    drift = {s: round(1000 * max(max((t - toes[s][0][0]).length, (fo - toes[s][0][1]).length) for t, fo in toes[s]), 4) for s in 'LR'}
    # visibility in the real game camera at the V2 end frame
    vis = {}
    endf = N if name != 'Yoru_Aim_Out' else 0
    scene.frame_set(endf)
    bpy.context.view_layer.update()
    if FEET is None:
        L.set_action(rig.arm, bpy.data.actions['Yoru_Aim_Pose_V2_full'])
        scene.frame_set(1)
        scene.frame_set(0)
        bpy.context.view_layer.update()
        fl, fr_ = PB['J_Bip_L_Foot'].head, PB['J_Bip_R_Foot'].head
        FEET = Vector((0.5 * (fl.x + fr_.x), 0.5 * (fl.y + fr_.y), 0.0))
        res['V2_visible_game'] = {s: round(v, 3) for s, v in L.visibility(rig, meter, L.game_cam_pos(FEET)).items()}
        L.set_action(rig.arm, act)
        scene.frame_set(endf)
        bpy.context.view_layer.update()
    vis = {s: round(v, 3) for s, v in L.visibility(rig, meter, L.game_cam_pos(FEET)).items()}
    clip = dict(frames=N + 1, fps=scene.render.fps, union=union, ends=ends, foot_drift_mm=drift, visible_game_end_frame=dict(frame=endf, **vis),
                step_max_all=[round(steps[0][0], 3), steps[0][1], steps[0][2]], step_max_layer=[round(st_layer[0][0], 3), st_layer[0][1], st_layer[0][2]],
                step_max_stand=[round(st_stand[0][0], 3), st_stand[0][1], st_stand[0][2]], step_max_arms=[round(st_arm[0][0], 3), st_arm[0][1], st_arm[0][2]],
                step_top_layer=[[round(a, 2), n, f] for a, n, f in st_layer[:6]], step_top_stand=[[round(a, 2), n, f] for a, n, f in st_stand[:4]],
                step_per_frame_layer_max=[round(max(a for a, n, f in st_layer if f == k), 3) for k in range(1, N + 1)],
                rows=rows)
    res['clips'][name] = clip
    log('%s: union %s | ends %s | steps all %s layer %s stand %s | feet %s | visible end %s' % (
        name, {k: union[k] for k in ('missing', 'extra', 'in_both', 'max_abs_diff', 'layer_has_hips')}, json.dumps(ends), clip['step_max_all'],
        clip['step_max_layer'], clip['step_max_stand'], drift, clip['visible_game_end_frame']))
# face shape keys (static) against the idle face at frame 0
sk = rig.face.data.shape_keys
fdev = max((abs(sk.key_blocks[fc.data_path.split('"')[1]].value - fc.evaluate(0.0)), fc.data_path) for fc in L.fcurves_of(IDLE_FACE))
res['face_vs_idle_face_frame0'] = dict(max_abs=round(fdev[0], 6), key=fdev[1], face_action_in_file=(sk.animation_data.action.name if sk.animation_data and sk.animation_data.action else None))
res['scene'] = dict(fps=scene.render.fps, fps_base=scene.render.fps_base)
res['ik_constraints'] = sum(1 for pb in PB for c in pb.constraints)
json.dump(res, open(OUT, 'w'), indent=1, default=lambda o: list(o) if hasattr(o, '__len__') else str(o))
log('face', res['face_vs_idle_face_frame0'], '| V2 visible', res.get('V2_visible_game'), '| constraints', res['ik_constraints'], '| fps', res['scene'])
log('wrote', OUT)
