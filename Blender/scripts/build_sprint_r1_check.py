"""
Yoru - NEW SPRINT, round 1: error checks of the arm paths (numbers only, saves nothing).
  blender -b --factory-startup <Yoru_Sprint_r1.blend> --python build_sprint_r1_check.py -- [actions, default all Yoru_Sprint_r1_*]
Per action and side: path of the grip centre (pistol origin) and of the elbow in the frame of the upper chest over one cycle: extent along the
main axis, across it (how much the path circles: a loop = flutter), sideways (x) range, and the wrist / elbow / upper arm twist per frame
(largest change of the hand's roll against the forearm: a jump = a visible twist).  Blender axes: +Y forward, her left = -X, up = +Z.
"""
import bpy, sys, math
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
acts = argv[0].split(',') if argv else sorted(a.name for a in bpy.data.actions if a.name.startswith('Yoru_Sprint_r1_') and a.name != 'Yoru_Sprint_r1_work')
pist = {s: bpy.data.objects.get('PLATZHALTER_Pistole_' + s) for s in 'LR'}


def pca(pts):
    a = np.array(pts)
    a = a - a.mean(axis=0)
    u, s, vt = np.linalg.svd(a, full_matrices=False)
    proj = a @ vt.T
    ext = proj.max(axis=0) - proj.min(axis=0)
    return ext[0] * 1000.0, ext[1] * 1000.0, vt[0]


for an in acts:
    arm.animation_data.action = bpy.data.actions[an]
    if getattr(arm.animation_data, 'action_slot', None) is None and len(arm.animation_data.action.slots):
        arm.animation_data.action_slot = arm.animation_data.action.slots[0]
    grip = {'L': [], 'R': []}
    elbow = {'L': [], 'R': []}
    roll = {'L': [], 'R': []}
    for f in range(36):
        scene.frame_set(f)
        pb = arm.pose.bones
        mc = arm.matrix_world @ pb['J_Bip_C_UpperChest'].matrix
        inv = mc.inverted()
        for s in 'LR':
            sx = 1.0 if s == 'R' else -1.0
            if pist[s]:
                grip[s].append(tuple(inv @ pist[s].matrix_world.translation))
            elbow[s].append(tuple(inv @ (arm.matrix_world @ pb['J_Bip_%s_LowerArm' % s].head)))
            # roll of the hand against the forearm about the forearm axis (the twist the skin has to take at the wrist)
            fa = (pb['J_Bip_%s_Hand' % s].head - pb['J_Bip_%s_LowerArm' % s].head).normalized()
            q_f = pb['J_Bip_%s_LowerArm' % s].matrix.to_quaternion()
            q_h = pb['J_Bip_%s_Hand' % s].matrix.to_quaternion()
            d = q_h @ q_f.inverted()
            ax, ang = d.to_axis_angle()
            roll[s].append(math.degrees(ang) * ax.dot(fa))
    for s in 'LR':
        g1, g2, gax = pca(grip[s]) if grip[s] else (0, 0, Vector())
        e1, e2, eax = pca(elbow[s])
        gx = [p[0] for p in grip[s]] or [0]
        r = roll[s]
        dr = max(abs(r[(i + 1) % 36] - r[i]) for i in range(36))
        print('PATHS %s %s: grip path %.0f mm along, %.0f mm across (main axis y %.2f z %.2f), sideways %.0f mm | elbow path %.0f along, %.0f across | '
              'hand roll against forearm %.1f..%.1f deg, largest step %.2f deg/frame' % (
                  an, s, g1, g2, gax[1], gax[2], 1000 * (max(gx) - min(gx)), e1, e2, min(r), max(r), dr), flush=True)
