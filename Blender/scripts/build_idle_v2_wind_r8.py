"""
Yoru - IDLE v2, round 8: ONLY a stronger wind in the hair (the user: "etwas mehr Wind").  The action of round 7 is copied; only the
hair curves are recomputed as Q = Q_round6 @ Q_wind8 (the round 6 hair = round 3 follow-through without wind).  Ears, tail, body, arms,
face and blink stay bit for bit; the times of the gusts stay.
Wind (round 7 -> round 8): steady lean at the strand tip 3.8 -> 6.3 deg, the waves from the root to the tip x1.3, the gusts larger; the
fringe and the strands on the left shoulder get relatively less (the fringe moves about as much as before, the eyes stay free).
Live (MCP):  ns = {'__file__': <this file>}; exec(open(<this file>).read(), ns); print(ns['bake_wind'](bpy.data.objects['Yoru_A2']))
Background:  blender -b <stage .blend> --python build_idle_v2_wind_r8.py -- <out .blend> [armature, default Yoru_A2]
"""
import bpy, sys, os, math
from mathutils import Vector, Quaternion

_HERE = os.path.dirname(os.path.abspath(globals().get('__file__', r'C:\Users\valen\ZeroProtocol\Blender\scripts\x.py')))
if not os.path.exists(os.path.join(_HERE, 'build_idle_v2_lib.py')):
    _HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
DY = {'__file__': os.path.join(_HERE, 'build_idle_v2_dynamics_r7.py')}
exec(compile(open(DY['__file__'], encoding='utf-8').read(), DY['__file__'], 'exec'), DY)
L, NF, FPS = DY['L'], DY['NF'], DY['FPS']

P8 = dict(DY['P7'])
P8.update(
    wind_base=6.3,                                               # round 7: 3.8 (>= the sum of the waves: never upwind)
    wind_waves=((3.0, 2.6, 0.0), (2.4, 1.7, 0.7), (1.5, 0.9, 1.9)),   # round 7: 2.0 / 1.2 / 0.6
    wind_gusts=((3.9, 1.1, 6.3), (9.3, 0.9, 7.0)),               # round 7: 2.2 / 1.6; same times
    # during a gust the waves calm down (a gust holds the strands out more steadily): without this the second gust fell into a wave
    # trough of the long strands and did not show (its peak stayed at 10 deg even with +6 deg)
    gust_wave_damp=0.6,
    tip_flutter=(1.0, 0.8),                                      # round 7: 0.7
    # chain 1 (the front lock on her right) hangs in front of the chest: the wind to her left pushed it across chest and neck in the second
    # gust (up to 21 more triangle pairs), so it gets little wind; chain 2 likewise
    chain_gain={1: 0.3, 2: 0.25, 3: 0.55, 4: 1.0, 5: 1.0, 6: 1.0, 7: 0.25, 8: 0.25, 9: 0.15, 10: 0.15, 11: 0.15, 12: 0.15,
                13: 0.25, 14: 0.25, 15: 0.3, 16: 0.3, 17: 0.3, 18: 1.0, 19: 1.0, 20: 0.3, 21: 0.3},
    # round 7: 1 0.6, 2 0.4, 3 0.7, fringe 9..12 0.25, 7/8/13/14 0.35, top 0.35 (relatively less now, so the fringe and the strands on the
    # left shoulder move about as much as before while the long strands get the full stronger wind)
)


def wind_deg_r8(t, phase, depth, p=P8):
    """deflection at the strand tip in degrees: steady lean + travelling waves (calmer during a gust) + gusts; never upwind"""
    TAU = 2.0 * math.pi
    gust = 0.0
    env = 0.0
    for centre, half, extra in p['wind_gusts']:
        b = DY['bump'](t - p['wind_depth_delay'] * depth, centre, half)
        gust += extra * b
        env = max(env, b)
    waves = 0.0
    for period, amp, ph in p['wind_waves']:
        waves += amp * math.sin(TAU * t / period - phase * (period / 3.0) ** -0.3 + ph)
    v = p['wind_base'] + waves * (1.0 - p.get('gust_wave_damp', 0.0) * env) + gust
    return max(v, 0.0)


DY['wind_deg'] = wind_deg_r8          # hair_wind_rel of round 7 looks wind_deg up in its own namespace: the round 8 version is used


def bake_wind(arm, r7_name='Yoru_Idle_v2', r6_name='Yoru_Idle_v2_r6', new_name='Yoru_Idle_v2_r8', p=P8):
    H = L['humanoid_map']()
    rig = L['Rig'](arm, H)
    src = bpy.data.actions[r7_name]
    base = bpy.data.actions[r6_name]
    if bpy.data.actions.get(new_name):
        bpy.data.actions[new_name].name = new_name + '_previous'
    act = src.copy()
    act.name = new_name
    act.use_fake_user = True
    fn = {(fc.data_path, fc.array_index): fc for fc in DY['_fcurves'](act)}
    fb = {(fc.data_path, fc.array_index): fc for fc in DY['_fcurves'](base)}
    lay = DY['hair_layout'](rig)
    R = rig.R
    hair = sorted(lay.keys())
    series = {n: [] for n in hair}
    for f in range(NF + 1):
        t = (f % NF) / FPS
        wr = DY['hair_wind_rel'](lay, t, p)
        for n in hair:
            dp = 'pose.bones["%s"].rotation_quaternion' % n
            q = Quaternion([fb[(dp, i)].keyframe_points[f].co[1] for i in range(4)])
            if n in wr:
                q = q @ (R[n].inverted() @ wr[n] @ R[n])
            series[n].append(q)
    for n, seq in series.items():
        prev = None
        fixed = []
        for q in seq:
            if prev is not None and prev.dot(q) < 0.0:
                q = -q
            fixed.append(q)
            prev = q
        dp = 'pose.bones["%s"].rotation_quaternion' % n
        for i in range(4):
            cos = []
            for f in range(NF + 1):
                cos.extend((float(f), float(fixed[f][i])))
            fn[(dp, i)].keyframe_points.foreach_set('co', cos)
            fn[(dp, i)].update()
    ad = arm.animation_data
    ad.action = act
    if hasattr(ad, 'action_slot') and act.slots:
        ad.action_slot = act.slots[0]
    bpy.context.scene.frame_set(0)
    return {'action': act.name, 'hair_bones': len(hair)}


def wind_range(rig, p=P8, chain=18):
    """tip deflection (deg) of a long strand over the loop (min, max)"""
    lay = DY['hair_layout'](rig)
    name = max((n for n, h in lay.items() if h['chain'] == chain), key=lambda n: lay[n]['depth'])
    h = lay[name]
    wg = Vector(p['wind_dir']).normalized()
    phase = p['wind_depth_phase'] * h['depth'] + p['wind_space_phase'] * h['root'].dot(wg)
    w = [wind_deg_r8(f / FPS, phase, h['depth'], p) if 'gust_wave_damp' in p else DY['bump'] and _wind_r7(f / FPS, phase, h['depth'], p)
         for f in range(NF)]
    return min(w), max(w), w


def _wind_r7(t, phase, depth, p):
    """the round 7 formula (for comparisons)"""
    TAU = 2.0 * math.pi
    v = p['wind_base']
    for period, amp, ph in p['wind_waves']:
        v += amp * math.sin(TAU * t / period - phase * (period / 3.0) ** -0.3 + ph)
    for centre, half, extra in p['wind_gusts']:
        v += extra * DY['bump'](t - p['wind_depth_delay'] * depth, centre, half)
    return max(v, 0.0)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    out = argv[0]
    name = argv[1] if len(argv) > 1 else 'Yoru_A2'
    print('[wind r8]', bake_wind(bpy.data.objects[name]), flush=True)
    print('[wind r8]', DY['compare_actions']('Yoru_Idle_v2_r8', 'Yoru_Idle_v2'), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)


if bpy.app.background and '--' in sys.argv and globals().get('__name__') == '__main__':
    main()
