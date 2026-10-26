"""
Yoru - IDLE v2, round 5: the chosen face B (kühl-wachsam) built into the 12 s loop.  Body and loop stay EXACTLY as in round 3; only the
face and the ears change:
  - face: ONE action on the face shape keys (Yoru_Idle_v2_Face) = the blink of round 3 (Fcl_EYE_Close, same times) + the B values of
    build_idle_v2_face.py as the base with small offset swings over the 12 s: lids about +-10 %, mouth tension about +-10 % and a touch
    looser on the out-breath, brows +-5 % (hidden by the fringe anyway).  While a blink closes the eyes, the mood keys of the lids fade
    out with it (value x (1 - blink)), so the lids never add up.
  - ears: the B base angle (tips forward) is put IN FRONT of the round 3 ear keys of a copy of the round 3 action: Q = Q_base @ Q_round3
    per frame (Q_base = R^-1 rel_base R, the same composition compute_pose uses), so the follow-through of round 3 stays as it was.
  Everything is periodic in 12 s; frame 360 == frame 0.
Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>).read(), ns); print(ns['bake_face_loop'](bpy.data.objects['Yoru_A2']))
Background:  blender -b <stage .blend> --python build_idle_v2_face_loop.py -- <out .blend> [armature name, default Yoru_A2]
"""
import bpy, sys, os, math
from mathutils import Vector, Quaternion, Euler

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_idle_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'


def _load(name):
    ns = {'__file__': os.path.join(_HERE, name)}
    exec(compile(open(os.path.join(_HERE, name), encoding='utf-8').read(), os.path.join(_HERE, name), 'exec'), ns)
    return ns


R3 = _load('build_idle_v2_loop_r3.py')      # NF, FPS, LOOP, breath, choose_blinks, blink_weights, action_fcurves, _fill
FACE = _load('build_idle_v2_face.py')       # EXPRESSIONS, face_child
L = R3['L']
NF, FPS, LOOP, TAU = R3['NF'], R3['FPS'], R3['LOOP'], 2.0 * math.pi
W = TAU / LOOP
EXPR = FACE['EXPRESSIONS']['B']
LID_KEYS = ('Fcl_EYE_Angry', 'Fcl_EYE_Fun')
MOUTH_KEYS = ('Fcl_MTH_Neutral', 'Fcl_MTH_Close')
# mouth_var 0.10 gave only about +-6 % in all (the out-breath part takes from it); 0.12 gives about +-10 %
P5 = dict(lid_var=0.10, mouth_var=0.12, mouth_out_breath=0.04, brow_var=0.05)


def face_values(t, blink_w, p=P5):
    """shape key values at the time t (s) for B, with the blink weight of this frame"""
    b = R3['breath'](t)
    lid1 = 1.0 + p['lid_var'] * (math.sin(W * t + 0.7) + 0.35 * math.sin(3 * W * t + 2.2)) / 1.35
    lid2 = 1.0 + p['lid_var'] * (math.sin(W * t + 2.4) + 0.30 * math.sin(2 * W * t + 0.9)) / 1.30
    mouth = 1.0 + (p['mouth_var'] - p['mouth_out_breath']) * (math.sin(W * t + 1.3) + 0.30 * math.sin(3 * W * t + 0.4)) / 1.30 \
        - p['mouth_out_breath'] * (1.0 - b)                     # a touch looser while the breath goes out
    brow = 1.0 + p['brow_var'] * math.sin(W * t + 2.1)
    keys = EXPR['keys']
    v = {'Fcl_EYE_Close': blink_w}
    v['Fcl_EYE_Angry'] = keys['Fcl_EYE_Angry'] * lid1 * (1.0 - blink_w)
    v['Fcl_EYE_Fun'] = keys['Fcl_EYE_Fun'] * lid2 * (1.0 - blink_w)
    v['Fcl_MTH_Neutral'] = keys['Fcl_MTH_Neutral'] * mouth
    v['Fcl_MTH_Close'] = keys['Fcl_MTH_Close'] * mouth
    v['Fcl_BRW_Angry'] = keys['Fcl_BRW_Angry'] * brow
    return v


def bake_face_action(face_obj, name='Yoru_Idle_v2_Face'):
    seed, blinks = R3['choose_blinks']()
    w = R3['blink_weights'](blinks)                              # NF + 1 values, w[NF] == w[0] == 0
    vals = [face_values((f % NF) / FPS, w[f]) for f in range(NF + 1)]
    sk = face_obj.data.shape_keys
    if sk.animation_data is None:
        sk.animation_data_create()
    old = sk.animation_data.action
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    sk.animation_data.action = act
    kb = sk.key_blocks
    for k in vals[0]:
        kb[k].value = vals[0][k]
        kb[k].keyframe_insert('value', frame=0)
    fcs = {fc.data_path: fc for fc in R3['action_fcurves'](act)}
    for k in vals[0]:
        R3['_fill'](fcs['key_blocks["%s"].value' % k], [vals[f][k] for f in range(NF + 1)])
    return act, old, seed, [b.start for b in blinks], vals


def ear_base_quats(rig):
    ex, ey = EXPR['ears']
    out = {}
    for side, sx in (('L', -1.0), ('R', 1.0)):
        n = 'J_Opt_%s_CatEar1_01' % side
        if n in rig.bones:
            rel = Euler((math.radians(ex), math.radians(sx * ey), 0.0), 'XYZ').to_quaternion()
            Rq = rig.R[n]
            out[n] = Rq.inverted() @ rel @ Rq
    return out


def make_final_body_action(arm, src_name='Yoru_Idle_v2', new_name='Yoru_Idle_v2_B'):
    """copy of the round 3 action with the B ear base angle in front of the ear keys; every other curve stays bit for bit"""
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    src = bpy.data.actions[src_name]
    act = src.copy()
    act.name = new_name
    act.use_fake_user = True
    fcs = {(fc.data_path, fc.array_index): fc for fc in R3['action_fcurves'](act)}
    for bone, qb in ear_base_quats(rig).items():
        dp = 'pose.bones["%s"].rotation_quaternion' % bone
        curves = [fcs[(dp, i)] for i in range(4)]
        n = len(curves[0].keyframe_points)
        new = []
        for k in range(n):
            q = Quaternion([curves[i].keyframe_points[k].co[1] for i in range(4)])
            new.append(qb @ q)
        for i in range(4):
            cos = []
            for k in range(n):
                cos.extend((curves[i].keyframe_points[k].co[0], new[k][i]))
            curves[i].keyframe_points.foreach_set('co', cos)
            curves[i].update()
    return act


def bake_face_loop(arm):
    face = FACE['face_child'](arm)
    body = make_final_body_action(arm)
    ad = arm.animation_data
    src = ad.action
    ad.action = body
    if hasattr(ad, 'action_slot') and body.slots:
        ad.action_slot = body.slots[0]
    fact, old_face, seed, starts, vals = bake_face_action(face)
    bpy.context.scene.frame_set(0)
    return {'body_action': body.name, 'from': src.name, 'face_action': fact.name, 'old_face_action': old_face.name if old_face else None,
            'blink_seed': seed, 'blinks_s': [round(s, 2) for s in starts],
            'face_at_0': {k: round(v, 3) for k, v in vals[0].items()}, 'face_at_360': {k: round(v, 3) for k, v in vals[NF].items()}}


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    out = argv[0]
    name = argv[1] if len(argv) > 1 else 'Yoru_A2'
    print('[face loop]', bake_face_loop(bpy.data.objects[name]), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
