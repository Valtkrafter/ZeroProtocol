"""
Yoru - ACTION COMPARE (main agent, saves nothing but the optional JSON).  Written 2026-10-31 for the stage-1 review of Yoru_Aim_Idle.
  blender -b <blend> --python aim_action_compare.py -- <action> [ref=<blend>:<action>] [union=<a>+<b>] [out.json=<path>]
Compares the KEYED CHANNELS of <action> with the reference action (appended from the other blend) at every frame, no pose evaluation:
  per bone: rotation difference in degrees (max and min over the loop: a constant offset has max == min), its axis in bone space and how much the axis moves,
  location difference in mm;  other channels (shape keys, properties): largest value difference;  bones and channels that exist on one side only.
union=A+B: the actions A and B together must carry exactly the channels of <action> with the same values (layer + stand split).
at=first|last|<n>: compare only that frame of <action>, against the same frame number of the reference or against ref_at=<n>.
"""
import bpy, sys, re, math, json
from mathutils import Quaternion, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = REF = UNION = AT = REF_AT = None
acts = []
for a in argv:
    if a.startswith('out.json='):
        OUT = a.split('=', 1)[1]
    elif a.startswith('ref='):
        REF = a.split('=', 1)[1]
    elif a.startswith('at='):
        AT = a.split('=', 1)[1]
    elif a.startswith('ref_at='):
        REF_AT = int(a.split('=', 1)[1])
    elif a.startswith('union='):
        UNION = a.split('=', 1)[1].split('+')
    else:
        acts.append(a)

print('actions in file:', sorted(x.name for x in bpy.data.actions))
ref_act = None
if REF:
    path, name = REF.rsplit(':', 1)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.actions = [name]
    ref_act = dst.actions[0]

BONE = re.compile(r'^pose\.bones\["(.+)"\]\.(rotation_quaternion|rotation_euler|location|scale)$')


def channels(act):
    out = {}
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves:
                    out[(fc.data_path, fc.array_index)] = fc
    return out


def series(chs, frames):
    n = len(frames)
    raw, other = {}, {}
    for (dp, idx), fc in chs.items():
        m = BONE.match(dp)
        if m:
            raw.setdefault(m.group(1), {})[(m.group(2), idx)] = [fc.evaluate(f) for f in frames]
        else:
            other[(dp, idx)] = [fc.evaluate(f) for f in frames]
    one, zero = [1.0] * n, [0.0] * n
    res = {}
    for bn, d in raw.items():
        w = [d.get(('rotation_quaternion', k), one if k == 0 else zero) for k in range(4)]
        loc = [d.get(('location', k), zero) for k in range(3)]
        res[bn] = ([Quaternion((w[0][i], w[1][i], w[2][i], w[3][i])).normalized() for i in range(n)],
                   [Vector((loc[0][i], loc[1][i], loc[2][i])) for i in range(n)])
        if any(k[0] == 'rotation_euler' for k in d):
            print('WARNING: euler channels on', bn, '(ignored)')
    return res, other


def compare(a_ch, b_ch, frames, ref_frames=None):
    sa, oa = series(a_ch, frames)
    sb, ob = series(b_ch, ref_frames or frames)
    res = {'bones': {}, 'only_action': sorted(set(sa) - set(sb)), 'only_ref': sorted(set(sb) - set(sa))}
    for bn in sorted(set(sa) & set(sb)):
        (qa, la), (qb, lb) = sa[bn], sb[bn]
        angs, axes = [], []
        for i in range(len(frames)):
            d = qa[i].rotation_difference(qb[i])
            if d.w < 0:
                d.negate()
            angs.append(math.degrees(d.angle))
            if d.angle > math.radians(0.2):
                axes.append(d.axis.copy())
        spread = max(math.degrees(axes[0].angle(x)) for x in axes) if axes else 0.0
        res['bones'][bn] = {'max_deg': round(max(angs), 4), 'min_deg': round(min(angs), 4),
                            'axis': [round(v, 3) for v in axes[0]] if axes else None,
                            'axis_spread_deg': round(spread, 3),
                            'loc_mm': round(max((la[i] - lb[i]).length for i in range(len(frames))) * 1000, 4)}
    both = set(oa) & set(ob)
    res['other_max'] = round(max((max(abs(x - y) for x, y in zip(oa[k], ob[k])) for k in both), default=0.0), 6)
    res['other_compared'] = len(both)
    res['other_one_side'] = ['%s[%d]' % k for k in sorted(set(oa) ^ set(ob))]
    return res


def region(bn):
    for key, reg in (('Hips', 'hips'), ('Leg', 'leg'), ('Foot', 'leg'), ('Toe', 'leg'), ('Tail', 'tail'), ('J_Sec', 'hair'), ('Ear', 'ear'), ('Eye', 'eye'),
                     ('Spine', 'spine'), ('Chest', 'spine'), ('Neck', 'head'), ('Head', 'head')):
        if key in bn:
            return reg
    return 'arm'


def union_check(act, parts, frames):
    chs = channels(act)
    u, dup, regs = {}, 0, {}
    for p in parts:
        c = channels(bpy.data.actions[p])
        dup += len(set(u) & set(c))
        u.update(c)
        r = {}
        for dp, idx in c:
            m = BONE.match(dp)
            if m:
                r.setdefault(region(m.group(1)), set()).add(m.group(1))
        regs[p] = {k: len(v) for k, v in sorted(r.items())}
    both = set(chs) & set(u)
    return {'channels': len(chs), 'union_channels': len(u), 'missing_in_union': len(set(chs) - set(u)),
            'extra_in_union': len(set(u) - set(chs)), 'in_both_parts': dup, 'bones_per_region': regs,
            'max_abs_diff': round(max((max(abs(chs[k].evaluate(f) - u[k].evaluate(f)) for f in frames) for k in both), default=0.0), 7)}


res = {}
for name in acts:
    act = bpy.data.actions[name]
    f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    frames = list(range(f0, f1 + 1))
    ref_frames = None
    if AT:
        fa = f0 if AT == 'first' else f1 if AT == 'last' else int(AT)
        frames = [fa]
        ref_frames = [REF_AT if REF_AT is not None else fa]
    o = {'frames': len(frames), 'first': f0, 'last': f1}
    if ref_act:
        o['vs_ref'] = compare(channels(act), channels(ref_act), frames, ref_frames)
    if UNION:
        o['union'] = union_check(act, UNION, frames)
    res[name] = o
if OUT:
    json.dump(res, open(OUT, 'w'), indent=1)
for name, o in res.items():
    print('==', name, '(%d frames, %d..%d)' % (o['frames'], o['first'], o['last']))
    r = o.get('vs_ref')
    if r:
        diff = {b: v for b, v in r['bones'].items() if v['max_deg'] > 0.001 or v['loc_mm'] > 0.001}
        print('  bones compared %d, identical (<= 0.001 deg and <= 0.001 mm) %d' % (len(r['bones']), len(r['bones']) - len(diff)))
        for b, v in diff.items():
            print('  %-30s rot %8.4f .. %8.4f deg  axis %s spread %.3f  loc %.4f mm' % (b, v['min_deg'], v['max_deg'], v['axis'], v['axis_spread_deg'], v['loc_mm']))
        print('  only in action:', r['only_action'], ' only in ref:', r['only_ref'])
        print('  other channels: %d compared, max diff %.6f, one side only: %s' % (r['other_compared'], r['other_max'], r['other_one_side']))
    if 'union' in o:
        print('  union:', o['union'])
