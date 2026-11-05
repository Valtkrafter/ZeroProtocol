"""
Yoru - AIM SUITE STAGE 1: what hides the LEFT pistol in the real game camera over the aim-idle loop? (diagnostic only, saves nothing but the JSON)
  blender -b --factory-startup <Blender/work/Aim/Yoru_Aim_s1.blend> --python build_aim_s1_visdiag.py -- <out .json> [frames=0,114,171,222,231,291]
  blender -b --factory-startup <Blender/work/Aim/Yoru_Aim_s1.blend> --python build_aim_s1_visdiag.py -- <out .json> loop=1
          [compare=<blend of an earlier round, e.g. Blender/work/Aim/Yoru_Aim_s1_r1.blend>]
Uses the set-up and the visibility test of build_aim_s1_check.py (game camera 0.35 m right).
Default (round 1): per frame the pose of Yoru_Aim_Idle is applied by hand (action off, NLA muted) and the left pistol's visible share is measured:
as built; with the hair bones of frame 0 (no wind change); with the head turned back about world Z so the gaze yaw is 0 (a head that tracks the aim
line); both; and with the trunk (hips, spine, chest, shoulders, legs) of frame 0 (no body sway).
loop=1 (round 2): the visible share of BOTH pistols in every frame 0..360 as built, for Yoru_Aim_Idle of this file and (compare=) of the earlier
round: per frame, min, max, mean and all frames that reach the minimum.
"""
import bpy, sys, math, json
from mathutils import Vector, Quaternion

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
FRAMES = [int(x) for x in KV.get('frames', '0,114,171,222,231,291').split(',')]
CHECK = r'C:\Users\valen\ZeroProtocol\Blender\scripts\build_aim_s1_check.py'
ns = {'__file__': CHECK}
src = open(CHECK, encoding='utf-8').read().split('# ------------------------------------------------------------------ pass 1: every frame')[0]
_argv = sys.argv
sys.argv = [sys.argv[0], '--', OUT] + (['compare=' + KV['compare']] if KV.get('compare') else [])
exec(compile(src, CHECK, 'exec'), ns)
sys.argv = _argv
scene, arm, PB, MW, KEYED, visibility = ns['scene'], ns['arm'], ns['PB'], ns['MW'], ns['KEYED'], ns['visibility']
ad = arm.animation_data
act = ad.action

if KV.get('loop') == '1':
    scene.frame_set(0)
    _fl, _fr = MW @ PB['J_Bip_L_Foot'].head, MW @ PB['J_Bip_R_Foot'].head
    _feet = Vector((0.5 * (_fl.x + _fr.x), 0.5 * (_fl.y + _fr.y), 0.0))
    _p = math.radians(15.0)
    _cam = Vector((_feet.x + 0.35, _feet.y - 4.4 * math.cos(_p), 1.35 + 4.4 * math.sin(_p)))
    runs = [('this', act)] + ([('compare', ns['CMP']['Yoru_Aim_Idle'])] if 'Yoru_Aim_Idle' in ns['CMP'] else [])
    res = dict(camera='real game camera, 0.35 m right of the pivot, 4.4 m behind, 15 deg down', camera_pos=[round(v, 4) for v in _cam],
               file=bpy.data.filepath, compare=KV.get('compare'), runs={})
    for tag, a in runs:
        ns['use'](a)
        per = {'L': [], 'R': []}
        for f in range(361):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            v = visibility(_cam)
            for s in 'LR':
                per[s].append(round(v[s], 4))
            if f % 60 == 0:
                print('LOOPVIS', tag, f, v, flush=True)
        summ = {}
        for s in 'LR':
            lo, hi = min(per[s]), max(per[s])
            summ[s] = dict(min=lo, max=hi, mean=round(sum(per[s]) / len(per[s]), 4), frames_at_min=[f for f, x in enumerate(per[s]) if x == lo],
                           frames_at_max=[f for f, x in enumerate(per[s]) if x == hi][:12], frame0=per[s][0])
        res['runs'][tag] = dict(action=a.name, summary=summ, per_frame=per)
        print('LOOPVIS SUMMARY', tag, json.dumps(summ), flush=True)
    ns['use'](act)
    json.dump(res, open(OUT, 'w'), indent=1)
    print('wrote', OUT, flush=True)
    raise SystemExit(0)

for t in ad.nla_tracks:
    t.mute = True                                                    # else the NLA stand takes over when the action is switched off
scene.frame_set(0)
fl, fr_ = MW @ PB['J_Bip_L_Foot'].head, MW @ PB['J_Bip_R_Foot'].head
FEET = Vector((0.5 * (fl.x + fr_.x), 0.5 * (fl.y + fr_.y), 0.0))
p = math.radians(15.0)
CAM = Vector((FEET.x + 0.35, FEET.y - 4.4 * math.cos(p), 1.35 + 4.4 * math.sin(p)))
HAIR = [n for n in KEYED if 'Hair' in n]
TRUNK = [n for n in KEYED if (n.startswith('J_Bip_C_') and n != 'J_Bip_C_Head') or any(k in n for k in ('UpperLeg', 'LowerLeg', '_Foot', 'Shoulder'))]


def capture(f):
    ad.action = act
    if len(act.slots):
        ad.action_slot = act.slots[0]
    scene.frame_set(f)
    return {n: PB[n].rotation_quaternion.copy() for n in KEYED}, PB['J_Bip_C_Hips'].location.copy()


def apply(q, loc):
    ad.action = None
    for n, v in q.items():
        PB[n].rotation_quaternion = v
    PB['J_Bip_C_Hips'].location = loc
    bpy.context.view_layer.update()


def gaze():
    hp = PB['J_Bip_C_Head']
    dq = hp.matrix.to_quaternion() @ hp.bone.matrix_local.to_quaternion().inverted()
    fw = (dq @ Vector((0, 1, 0))).normalized()
    return math.degrees(math.atan2(fw.x, fw.y))


Q0, LOC0 = capture(0)
out = {}
for f in FRAMES:
    q, loc = capture(f)
    row = {}
    apply(q, loc)
    row['as_built'] = round(visibility(CAM)['L'], 3)
    g = gaze()
    qh = dict(q)
    qh.update({n: Q0[n] for n in HAIR})
    apply(qh, loc)
    row['hair_of_frame0'] = round(visibility(CAM)['L'], 3)
    hb = PB['J_Bip_C_Head']
    Rr = hb.bone.matrix_local.to_quaternion()
    Dp = hb.parent.matrix.to_quaternion() @ hb.parent.bone.matrix_local.to_quaternion().inverted()
    qc = dict(q)
    qc['J_Bip_C_Head'] = Rr.inverted() @ Dp.inverted() @ Quaternion((0, 0, 1), math.radians(g)) @ Dp @ Rr @ q['J_Bip_C_Head']
    apply(qc, loc)
    row['gaze_after_head_comp'] = round(gaze(), 3)
    row['head_yaw_compensated'] = round(visibility(CAM)['L'], 3)
    qb = dict(qc)
    qb.update({n: Q0[n] for n in HAIR})
    apply(qb, loc)
    row['head_comp_and_hair_of_frame0'] = round(visibility(CAM)['L'], 3)
    qs = dict(q)
    qs.update({n: Q0[n] for n in TRUNK})
    apply(qs, LOC0)
    row['trunk_of_frame0'] = round(visibility(CAM)['L'], 3)
    row['gaze_yaw_deg'] = round(g, 2)
    out[str(f)] = row
    print('VISDIAG', f, json.dumps(row), flush=True)
json.dump(dict(camera='game 0.35 m right', pistol='L', frames=out), open(OUT, 'w'), indent=1)
print('wrote', OUT, flush=True)
