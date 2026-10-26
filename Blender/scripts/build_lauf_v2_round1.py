"""
Yoru - LAUF v2 (main run on W, NTE reference), round 1: builds the work file.
  1. the gait clip of build_run.py with the NTE timing (Blender/work/Lauf_v2/gen_r1/Yoru_Run.blend, arguments in build_lauf_v2_lib.GEN_ARGS)
     is appended (the gait file is only read), its action is copied to 'Yoru_Lauf_v2'
  2. the arm chains are replaced by the organic arm layer with the NTE angles (build_lauf_v2_lib.ArmLayer, STYLE) and fitted against the
     gear with the exact intersection test (fix_arms, with the bust); face B; Cycles modifiers
  3. 'Alt' = the old sprint (Blender/Yoru_Run.blend, only read, appended) stands next to her for the comparison
  4. one floor lane per character that scrolls with the ground motion of its gait (a planted shoe stays on its tile)
Collections: Lauf_v2_R1 (Lauf_v2_R1_Neu, Lauf_v2_R1_Alt, floors and labels).  Scene 60 fps, frames 0 .. 359 (= 9 x 40 = 10 x 36: both loop).
Background:  blender -b --factory-startup --python build_lauf_v2_round1.py -- <gen .blend> <out .blend> [style json]
"""
import bpy, os, sys, math, json

SCRIPTS = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
ns = {'__file__': os.path.join(SCRIPTS, 'build_lauf_v2_lib.py')}
exec(compile(open(ns['__file__'], encoding='utf-8').read(), ns['__file__'], 'exec'), ns)
LB = ns
ROOT = 'Lauf_v2_R1'
X_NEU, X_ALT = -0.6, 0.6
PLAY_END = 359


def build(gen_blend, style=None):
    log = LB['log']
    root = LB['coll'](ROOT)
    c_neu = LB['coll'](ROOT + '_Neu', root)
    c_alt = LB['coll'](ROOT + '_Alt', root)
    arm, kids = LB['append_character'](gen_blend, c_neu, 'Lauf', X_NEU)
    src = arm.animation_data.action
    act = src.copy()
    act.name = 'Yoru_Lauf_v2'
    act.use_fake_user = True
    slot = getattr(arm.animation_data, 'action_slot', None)
    arm.animation_data.action = act
    if slot is not None and hasattr(arm.animation_data, 'action_slot') and arm.animation_data.action_slot is None:
        arm.animation_data.action_slot = act.slots[0]
    src.use_fake_user = False
    info = {'cycles_added': LB['make_cyclic'](act)}
    style = dict(style or {})
    tail_yaw = style.pop('tail_yaw', 0.0)
    if tail_yaw:
        info['tail_turned_keys'] = LB['turn_tail'](arm, tail_yaw)
    st = dict(LB['STYLE'], **style)
    n, diags = LB['apply_arm_layer'](arm, st)
    el = [d[s]['elbow'] for d in diags for s in 'LR']
    tw = [d[s]['twist'] for d in diags for s in 'LR']
    wr = [d[s]['wrist'] for d in diags for s in 'LR']
    su = [d[s]['swing_u'] for d in diags for s in 'LR']
    info.update(arm_bones=n, elbow=(round(min(el), 1), round(max(el), 1)), forearm_roll=(round(min(tw), 1), round(max(tw), 1)),
                wrist_bend=(round(min(wr), 1), round(max(wr), 1)), upper_arm_swing=(round(min(su), 1), round(max(su), 1)))
    log('arm layer', json.dumps(info))
    info['arm_extra_deg'] = LB['fix_arms'](arm)
    log('gear fit (extra outward turn of the upper arm, deg)', info['arm_extra_deg'])
    info['face'] = LB['face_b'](arm)
    # the old sprint next to her
    alt, akids = LB['append_character'](LB['OLD_RUN'], c_alt, 'Alt', X_ALT)
    aact = alt.animation_data.action
    aact.name = 'Yoru_Run_Alt'
    info['alt_cycles_added'] = LB['make_cyclic'](aact)
    LB['make_lane']('Boden_Lauf_Neu', LB['GAIT_NEU'], -9.0, 0.0, root)
    LB['make_lane']('Boden_Lauf_Alt', LB['GAIT_ALT'], 0.0, 9.0, root)
    LB['make_label']('Label_Lauf_Neu', 'Neu: Lauf W (NTE)', X_NEU, root)
    LB['make_label']('Label_Lauf_Alt', 'Alt: Rennen', X_ALT, root)
    scene = bpy.context.scene
    scene.render.fps = 60
    scene.render.fps_base = 1.0
    scene.frame_start, scene.frame_end = 0, PLAY_END
    try:
        scene.sync_mode = 'FRAME_DROP'
    except Exception:
        pass
    scene.frame_set(0)
    info['meshes'] = [k.name for k in kids] + [k.name for k in akids]
    return info


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    gen, out = argv[0], argv[1]
    style = json.loads(open(argv[2], encoding='utf-8').read()) if len(argv) > 2 else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    info = build(gen, style)
    LB['log']('round1', json.dumps(info))
    bpy.ops.wm.save_as_mainfile(filepath=out)
    LB['log']('saved', out)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
