"""
Yoru - AIM SUITE, STEP 0 (2026-10-31): Blender/Yoru_Aim.blend gets ONLY the approved round-5 pose V2, under clean names.
  blender -b --factory-startup <Blender/work/Aim/Yoru_Aim_r5.blend> --python build_aim_s1_pose.py -- <out .blend> [check=<out .json>]
  e.g. ... Blender/work/Aim/Yoru_Aim_r5.blend --python Blender/scripts/build_aim_s1_pose.py -- Blender/Yoru_Aim.blend check=Blender/work/Aim/Yoru_Aim_s1_pose_check.json
Source (round 5): Yoru_Aim_r5_V2 (layer: spine and up incl. arms, fingers, eyes, ears, hair, bust; no hips keys), Yoru_Aim_r5_Stand (hips, legs,
feet, toes, tail = Idle_v2 frame 0, on the NLA track 'Stand'), Yoru_Aim_r5_full_V2 (both).  They are renamed to Yoru_Aim_Pose_V2,
Yoru_Aim_Pose_V2_Stand (NLA track 'Stand' as in round 5) and Yoru_Aim_Pose_V2_full; every other action (the V1 ones cut the bust) is removed.
The pistol placeholders PLATZHALTER_Pistole_L/R stay parented to the hand bones; scene fps 30 (the project rate), frame 0.
Check (the saved file is opened again): Yoru_Aim_Pose_V2_full alone and Yoru_Aim_Pose_V2 over the NLA stand, frame 0, against
Yoru_Aim_r5_full_V2 frame 0 of the source: world rotation of every bone (deg), heads and tails (mm), both pistols (deg, mm), every deformed vertex
of Body, Face and Hair (mm).  Wanted: <= 0.001 deg and <= 0.01 mm.
"""
import bpy, sys, os, math, json
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = os.path.abspath(argv[0])
KV = dict(a.split('=', 1) for a in argv[1:] if '=' in a)
CHECK = KV.get('check')
RENAME = {'Yoru_Aim_r5_V2': 'Yoru_Aim_Pose_V2', 'Yoru_Aim_r5_Stand': 'Yoru_Aim_Pose_V2_Stand', 'Yoru_Aim_r5_full_V2': 'Yoru_Aim_Pose_V2_full'}
SRC = bpy.data.filepath


def log(*a):
    print('[aim_s1_pose]', *a, flush=True)


def armature():
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE')


def use_action(name):
    arm = armature()
    ad = arm.animation_data
    act = bpy.data.actions[name]
    ad.action = act
    if hasattr(ad, 'action_slot') and len(act.slots):
        ad.action_slot = act.slots[0]
    sc = bpy.context.scene
    sc.frame_set(1)
    sc.frame_set(0)
    bpy.context.view_layer.update()


def capture():
    """world rotation + head + tail of every pose bone, pistol matrices, deformed vertices of Body / Face / Hair (plain python / numpy)"""
    arm = armature()
    mw = arm.matrix_world
    bones = {pb.name: ((mw @ pb.matrix).to_quaternion().copy(), (mw @ pb.head).copy(), (mw @ pb.tail).copy()) for pb in arm.pose.bones}
    pist = {o.name: o.matrix_world.copy() for o in bpy.data.objects if o.name.startswith('PLATZHALTER_Pistole')}
    dg = bpy.context.evaluated_depsgraph_get()
    verts = {}
    for name in ('Body', 'Face', 'Hair'):
        ob = bpy.data.objects.get(name)
        if ob is None:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        arr = np.empty(len(me.vertices) * 3, dtype=np.float64)
        me.vertices.foreach_get('co', arr)
        ev.to_mesh_clear()
        arr = arr.reshape(-1, 3) @ np.array(ob.matrix_world.to_3x3()).T + np.array(ob.matrix_world.translation)
        verts[name] = arr
    return dict(bones=bones, pist=pist, verts=verts)


def qang(a, b):
    x = a.rotation_difference(b).angle
    return math.degrees(min(x, 2.0 * math.pi - x))


def compare(ref, got):
    rot = max((qang(ref['bones'][n][0], got['bones'][n][0]), n) for n in ref['bones'])
    pos = max((max((ref['bones'][n][1] - got['bones'][n][1]).length, (ref['bones'][n][2] - got['bones'][n][2]).length) * 1000.0, n)
              for n in ref['bones'])
    pr = max(qang(ref['pist'][k].to_quaternion(), got['pist'][k].to_quaternion()) for k in ref['pist'])
    pp = max((ref['pist'][k].translation - got['pist'][k].translation).length * 1000.0 for k in ref['pist'])
    vv = max(float(np.abs(ref['verts'][k] - got['verts'][k]).max()) * 1000.0 for k in ref['verts'])
    return dict(bone_rot_max_deg=round(rot[0], 6), bone_rot_worst=rot[1], bone_pos_max_mm=round(pos[0], 6), bone_pos_worst=pos[1],
                pistol_rot_max_deg=round(pr, 6), pistol_pos_max_mm=round(pp, 6), vertex_max_mm=round(vv, 6),
                ok=bool(rot[0] <= 0.001 and pos[0] <= 0.01 and pr <= 0.001 and pp <= 0.01 and vv <= 0.01))


# ------------------------------------------------------------------ 1. reference: round-5 V2 full action, frame 0, in the source file
use_action('Yoru_Aim_r5_full_V2')
REF = capture()
log('reference captured from', SRC, '| bones', len(REF['bones']), '| pistols', sorted(REF['pist']), '| verts',
    {k: len(v) for k, v in REF['verts'].items()})

# ------------------------------------------------------------------ 2. rename, drop the rest
before = sorted(a.name for a in bpy.data.actions)
use_action('Yoru_Aim_r5_V2')                                         # the active action must not be one that is removed
for old, new in RENAME.items():
    bpy.data.actions[old].name = new
removed = []
for a in list(bpy.data.actions):
    if a.name not in RENAME.values():
        removed.append(a.name)
        bpy.data.actions.remove(a)
arm = armature()
ad = arm.animation_data
for trk in ad.nla_tracks:
    for st in trk.strips:
        if st.action is not None:
            st.name = st.action.name
for a in bpy.data.actions:
    a.use_fake_user = True
use_action('Yoru_Aim_Pose_V2')                                       # the file opens on the layer over the NLA stand
sc = bpy.context.scene
sc.render.fps, sc.render.fps_base = 30, 1.0
sc.frame_start, sc.frame_end = 0, 1
sc.frame_set(0)
log('actions before', before)
log('removed', removed, '| now', sorted(a.name for a in bpy.data.actions))
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=OUT)
log('saved', OUT)

# ------------------------------------------------------------------ 3. open the saved file again and compare
bpy.ops.wm.open_mainfile(filepath=OUT)
arm = armature()
ad = arm.animation_data
nla = [(t.name, t.mute, [(s.name, s.action.name if s.action else None, s.extrapolation, s.blend_type, s.influence if s.use_animated_influence else 1.0)
                         for s in t.strips]) for t in ad.nla_tracks]
pistols = {o.name: (o.parent.name if o.parent else None, o.parent_type, o.parent_bone) for o in bpy.data.objects if o.name.startswith('PLATZHALTER_Pistole')}
active = (ad.action.name if ad.action else None, ad.action_slot.identifier if getattr(ad, 'action_slot', None) else None)
use_action('Yoru_Aim_Pose_V2_full')
A = compare(REF, capture())
use_action('Yoru_Aim_Pose_V2')
B = compare(REF, capture())
res = dict(source=SRC, out=OUT, actions_before=before, removed=removed, actions_after=sorted(a.name for a in bpy.data.actions), active_on_open=active,
           nla=nla, pistols=pistols, fps=bpy.context.scene.render.fps,
           full_vs_r5_full_V2_frame0=A, layer_plus_nla_stand_vs_r5_full_V2_frame0=B)
log('CHECK', json.dumps(res, indent=1))
if CHECK:
    json.dump(res, open(CHECK, 'w'), indent=1)
    log('wrote', CHECK)
log('DONE', 'OK' if (A['ok'] and B['ok']) else 'MISMATCH')
