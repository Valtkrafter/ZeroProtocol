"""
Yoru - IDLE v2: checks the FINAL file in a fresh background Blender (numbers only).
usage: blender -b --factory-startup <Blender/Yoru_Idle_v2.blend> --python build_idle_v2_verify.py
  - the file loads; objects, actions (armature and face shape keys), frame range, fps
  - the action runs: the pose and the face keys change over the loop
  - the shape keys exist (expression B + blink) and have curves
  - seam: frame 360 (= next cycle, Cycles modifier) equals frame 0, and the step 359 -> 360 is as small as 0 -> 1 (bones and face keys)
  - icosphere never rendered, its collection excluded, no external paths, textures packed
  - the error checks of build_idle_v2_check.py: foot sliding, joint steps, seam, arm against gear (mesh), tail / legs / soles
"""
import bpy, math, os

log = lambda *a: print('[verify]', *a, flush=True)
sc = bpy.context.scene
arm = bpy.data.objects.get('Yoru')
face = next(c for c in arm.children if c.type == 'MESH' and c.data.shape_keys and 'Fcl_EYE_Close' in c.data.shape_keys.key_blocks)
act = arm.animation_data.action if arm.animation_data else None
fact = face.data.shape_keys.animation_data.action if face.data.shape_keys.animation_data else None
log('file', bpy.data.filepath)
log('objects', sorted(o.name for o in bpy.data.objects), '| actions', sorted(a.name for a in bpy.data.actions))
log('armature action', act.name if act else None, '| face action', fact.name if fact else None, '| fps', sc.render.fps, '| frames', sc.frame_start, sc.frame_end)


def fcurves(a):
    if hasattr(a, 'fcurves'):
        try:
            return list(a.fcurves)
        except Exception:
            pass
    out = []
    for layer in a.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


face_keys = sorted(fc.data_path.split('"')[1] for fc in fcurves(fact))
log('face keys with curves', face_keys, '| all present:', all(k in face.data.shape_keys.key_blocks for k in face_keys))
cyc = all(any(m.type == 'CYCLES' for m in fc.modifiers) for fc in fcurves(act) + fcurves(fact))
log('every curve endless (Cycles):', cyc, '| curves body', len(fcurves(act)), 'face', len(fcurves(fact)))
bones = [fc.data_path.split('"')[1] for fc in fcurves(act) if fc.data_path.endswith('rotation_quaternion') and fc.array_index == 0]


def state(f):
    sc.frame_set(f)
    q = {n: arm.pose.bones[n].rotation_quaternion.copy() for n in bones}
    loc = arm.pose.bones['J_Bip_C_Hips'].location.copy()
    k = {n: face.data.shape_keys.key_blocks[n].value for n in face_keys}
    return q, loc, k


def diff(a, b):
    qa, la, ka = a
    qb, lb, kb = b
    dq = max(min(math.degrees(qa[n].rotation_difference(qb[n]).angle), 360 - math.degrees(qa[n].rotation_difference(qb[n]).angle)) for n in bones)
    return dq, (la - lb).length * 1000.0, max(abs(ka[n] - kb[n]) for n in face_keys)


s0, s1, s180, s359, s360 = state(0), state(1), state(180), state(359), state(360)
log('action runs (frame 0 vs 180): max bone %.2f deg, hips %.2f mm, face key %.3f' % diff(s0, s180))
log('seam: frame 360 vs 0: bone %.4f deg, hips %.4f mm, face %.5f' % diff(s360, s0))
log('seam step 359 -> 360: bone %.3f deg, hips %.3f mm, face %.4f  |  step 0 -> 1: bone %.3f deg, hips %.3f mm, face %.4f' % (diff(s359, s360) + diff(s0, s1)))
sc.frame_set(56)
log('blink at frame 56: EYE_Close %.2f, EYE_Angry %.3f (fades with the blink)' % (face.data.shape_keys.key_blocks['Fcl_EYE_Close'].value, face.data.shape_keys.key_blocks['Fcl_EYE_Angry'].value))
sc.frame_set(0)
log('frame 0 face:', {n.replace('Fcl_', ''): round(face.data.shape_keys.key_blocks[n].value, 3) for n in face_keys})
ico = bpy.data.objects.get('Icosphere')
lc = next((c for c in bpy.context.view_layer.layer_collection.children if c.name == 'glTF_not_exported'), None)
log('icosphere rendered:', (not ico.hide_render) if ico else None, '| its collection excluded:', lc.exclude if lc else None,
    '| external paths:', bpy.utils.blend_paths(absolute=True), '| textures packed:', all(bool(i.packed_file) for i in bpy.data.images if i.source == 'FILE'),
    '| Yoru at', tuple(arm.location))
chk = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_idle_v2_check.py')
cs = {'__file__': chk}
exec(compile(open(chk, encoding='utf-8').read(), chk, 'exec'), cs)
r = cs['check_loop'](arm, nf=360)
log('checks:', {k: r[k] for k in ('max_joint_step_deg', 'seam_pose_diff_deg', 'seam_speed_deg_per_frame', 'foot_slide_mm', 'head_from_mean_max_deg', 'tail_gap_min_mm', 'leg_gap_min_mm', 'sole_min_mm')})
g = cs['arm_gear_check'](arm, frames=range(0, 360, 10))
log('arm against gear (mesh):', {s: (v['forearm_hand_mm'], v['upper_arm_cloth_mm']) for s, v in g.items()})
log('VERIFY DONE')
