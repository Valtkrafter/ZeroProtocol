"""
Yoru - WALK POLISH, round 2: arm motion trace of one walk action (no saving).  Shows what stills hide: kinks, wobble, speed spikes, the
swing plane and the phase between upper arm, elbow, wrist and chest.
Background:
  blender -b --factory-startup <blend> --python build_walk_polish_armtrace.py -- <out json> [action name]
Per frame (0 .. NF, NF = 0 again), right and left arm, in the frame of the upper chest (x = her right, y = forward, z = up; metres from the
shoulder joint): elbow E, wrist W, middle knuckle K.  Angles (deg): upper arm pitch (forward +) and spread (out +), elbow bend (joint to
joint), forearm pitch, wrist bend signed about the elbow axis (hand forward +), elbow direction (where the back of the elbow points seen
from above: 0 = straight back, + = outwards), upper chest yaw and roll against the hips (+ = turned to her left / dipped to her right).
Plot with build_walk_polish_armplot.py.
"""
import bpy, sys, os, math, json
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
ACT = argv[1] if len(argv) > 1 else None
_HERE = r'C:\Users\valen\ZeroProtocol\Blender\scripts'
GLB = r'C:\Users\valen\ZeroProtocol\Blender\work\Yoru_V2.glb'
LIB = {'__name__': 'idle_lib', '__file__': os.path.join(_HERE, 'build_idle_v2_lib.py')}
exec(compile(open(LIB['__file__'], encoding='utf-8').read(), LIB['__file__'], 'exec'), LIB)
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
if ACT:
    arm.animation_data.action = bpy.data.actions[ACT]
    ad = arm.animation_data
    if getattr(ad, 'action_slot', None) is None and len(ad.action.slots):
        ad.action_slot = ad.action.slots[0]
act = arm.animation_data.action
NF = int(round(act.frame_range[1] - act.frame_range[0]))
H = LIB['humanoid_map'](GLB)
pbs = arm.pose.bones


def frame_axes(pb):
    m = pb.matrix.to_3x3().normalized()
    return m.col[0].normalized(), -m.col[2].normalized(), m.col[1].normalized()      # right, forward, up (rest: Y up, Z back)


def body(v, ax):
    return [v.dot(ax[0]), v.dot(ax[1]), v.dot(ax[2])]


res = {'action': act.name, 'NF': NF, 'R': [], 'L': [], 'chest': []}
for f in range(NF + 1):
    scene.frame_set(f)
    ax = frame_axes(pbs[H['upperChest']])
    hx = frame_axes(pbs[H['hips']])
    yaw = math.degrees(math.atan2(-ax[1].dot(hx[0]), ax[1].dot(hx[1])))                # chest forward seen in the hips frame
    roll = math.degrees(math.atan2(ax[0].dot(hx[2]), ax[0].dot(hx[0])))
    wyaw = math.degrees(math.atan2(-ax[1].x, ax[1].y))
    res['chest'].append({'yaw_vs_hips': round(yaw, 2), 'roll_vs_hips': round(roll, 2), 'yaw_world': round(wyaw, 2)})
    for s, side in (('L', 'left'), ('R', 'right')):
        sx = -1.0 if s == 'L' else 1.0
        S, E, W, K = (pbs[H[side + p]].head for p in ('UpperArm', 'LowerArm', 'Hand', 'MiddleProximal'))
        u, fo, ha = (E - S).normalized(), (W - E).normalized(), (K - W).normalized()
        ub, fb = body(u, ax), body(fo, ax)
        h = u.cross(fo)
        h = h.normalized() if h.length > 1e-6 else Vector((sx, 0, 0))
        wr = math.degrees(math.atan2(h.dot(fo.cross(ha)), fo.dot(ha)))
        ru = pbs[H[side + 'UpperArm']].matrix.to_3x3().normalized()
        back = ru @ Vector((0, 0, 1))                                                     # back of the elbow in the rest pose = -Y
        back = back - u * back.dot(u)
        bb = body(back.normalized(), ax)
        res[s].append({'E': [round(x, 4) for x in body(E - S, ax)], 'W': [round(x, 4) for x in body(W - S, ax)],
                       'K': [round(x, 4) for x in body(K - S, ax)],
                       'up_pitch': round(math.degrees(math.atan2(ub[1], -ub[2])), 2),
                       'up_spread': round(math.degrees(math.atan2(sx * ub[0], -ub[2])), 2),
                       'elbow': round(math.degrees(u.angle(fo)), 2),
                       'fore_pitch': round(math.degrees(math.atan2(fb[1], -fb[2])), 2),
                       'wrist': round(wr, 2),
                       'elbow_dir': round(math.degrees(math.atan2(sx * bb[0], -bb[1])), 2)})
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as fh:
    json.dump(res, fh)
print('TRACE', OUT, NF, flush=True)
