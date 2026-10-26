"""
Yoru - WALK v2, round 1: builds the three swagger variants A / B / C on the stage of build_walk_v2_stage.py and bakes one looping action per
Yoru (29 frames at 30 fps, key 29 == key 0, Cycles modifiers).  The pelvis height per variant and the arm clearance per frame come from
Blender/work/Walk_v2/round1_params.json (written by the background build with --fit; the arm curve is the same in all three variants:
per frame the largest extra abduction any variant needs, so the variants differ only in the swagger).

Background:  blender -b --factory-startup --python build_walk_v2_round1.py -- <out .blend> [--fit]
Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>, encoding='utf-8').read(), ns); ns['build_live']()
"""
import bpy, os, sys, json, time, math

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_walk_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'


def _load(name):
    ns = {'__file__': os.path.join(_HERE, name)}
    exec(compile(open(os.path.join(_HERE, name), encoding='utf-8').read(), os.path.join(_HERE, name), 'exec'), ns)
    return ns


W = _load('build_walk_v2_lib.py')
S = _load('build_walk_v2_stage.py')
L = W['L']
PARAMS = r'C:\Users\valen\ZeroProtocol\Blender\work\Walk_v2\round1_params.json'
# round 1 arm setting (same in every variant): upper arm 12 deg out + the per-frame clearance (the elbow passes outside the belt pouch),
# the forearm comes 6 deg back in (the hand passes close to the holster / thigh, as the resting hands of the idle), swing centre 6 deg
# forward, +-4 deg, elbow 24 .. 34 deg.  (Round 1, first try: forearm 10 deg further out -> hands 55 .. 115 mm off the gear, floating.)
ARM_SET = dict(arm_ab={'R': 12.0, 'L': 12.0}, arm_carry={'R': -6.0, 'L': -6.0}, arm_ab_swing=0.0, arm_carry_swing=0.0, arm_swing0=6.0)


def log(*a):
    print('[walk_v2 round1]', *a, flush=True)


def fit_params(rig):
    W['WALK'].update(ARM_SET)
    z = W['fit_pelvis_all'](rig)
    tester = W['GearTester'](rig)
    geos = W['make_geos'](rig)
    per = {}
    for k in S['KEYS']:
        per[k] = W['fit_arm_extra'](rig, k, tester=tester, geos=geos)
    common = {s: [max(per[k][s][f] for k in S['KEYS']) for f in range(W['NF'])] for s in ('L', 'R')}
    data = dict(z_off=z, arm_extra=common, arm_extra_per_variant=per, arm_set=ARM_SET)
    os.makedirs(os.path.dirname(PARAMS), exist_ok=True)
    json.dump(data, open(PARAMS, 'w'), indent=1)
    return data


def load_params():
    data = json.load(open(PARAMS))
    W['WALK'].update(data['arm_set'])
    W['Z_OFF'].update(data['z_off'])
    for k in S['KEYS']:
        W['ARM_EXTRA'][k] = data['arm_extra']
    return data


def bake_all(arms):
    info = {}
    for k, arm in arms.items():
        info[k] = W['bake_variant'](arm, k)
    return info


def build_stage(clear_defaults=False):
    if clear_defaults:
        S['clear_default_objects']()
    S['make_scroll_floor']()
    arm_a = bpy.data.objects.get('Yoru_Walk_A') or S['import_yoru']('A')
    arms = {'A': arm_a}
    for k in ('B', 'C'):
        arms[k] = S['copy_yoru'](arm_a, k)
    S['make_labels']()
    S['scene_settings']()
    return arms


def build_live():
    """live in the user's Blender: copies B and C, bakes all three, labels, plays in real time"""
    t0 = time.time()
    load_params()
    arms = build_stage()
    info = bake_all(arms)
    bpy.context.scene.frame_set(0)
    S['setup_view']()
    S['play'](True)
    return {k: (v['action'], v['knee_min'], v['reach_deficit_mm'], v['forearm_twist_max']) for k, v in info.items()}, round(time.time() - t0, 1)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    out = argv[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arms = build_stage()
    if '--fit' in argv or not os.path.exists(PARAMS):
        rig = L['Rig'](arms['A'], L['humanoid_map']())
        t0 = time.time()
        data = fit_params(rig)
        log('fitted in %.0f s' % (time.time() - t0), 'z_off', data['z_off'],
            'arm extra', {s: (round(min(v), 1), round(max(v), 1)) for s, v in data['arm_extra'].items()})
    load_params()
    info = bake_all(arms)
    for k, v in info.items():
        log(k, v)
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    log('saved', out)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
