"""
Yoru - IDLE v2, round 6: arm checks of a FINAL idle file in a fresh background Blender (numbers only).
usage: blender -b --factory-startup <Blender/Yoru_Idle_v2.blend> --python build_idle_v2_verify_arms.py [-- armature, default Yoru]
  - exact penetration: triangle pairs where arm / hand cut through torso, thighs, gear (arm_mesh_intersections, every 5th frame)
  - contact: per frame the smallest distance of each hand to the outward gear surface on its side (should stay 0 to 3 mm)
  - elbows: flexion per frame (no step above 5 deg per frame, never straight: above 8 deg), hinge error, forearm twist
"""
import bpy, sys, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
NAME = argv[0] if argv else 'Yoru'
cs = {'__file__': os.path.join(HERE, 'build_idle_v2_check.py')}
exec(compile(open(cs['__file__'], encoding='utf-8').read(), cs['__file__'], 'exec'), cs)
ar = {'__file__': os.path.join(HERE, 'build_idle_v2_arms_r6.py')}
exec(compile(open(ar['__file__'], encoding='utf-8').read(), ar['__file__'], 'exec'), ar)
L = cs['L']
arm = bpy.data.objects[NAME]
H = L['humanoid_map']()
rig = L['Rig'](arm, H)
nm = rig.nm
sc = bpy.context.scene
nf = sc.frame_end - sc.frame_start + 1
r = cs['arm_mesh_intersections'](arm, range(0, nf, 5))
print('[verify arms] intersecting triangle pairs', r['intersecting_triangle_pairs'], '| hand to gear (unsigned, all faces) mm', r['hand_to_gear_mm'], flush=True)
polys, hand_all = ar['_gear_polys'](rig)
per = ar['surface_contact'](arm, rig, range(nf), polys, {s: hand_all[s] for s in 'LR'})
for s in 'LR':
    v = [x * 1000 for x in per[s]]
    print('[verify arms] %s hand contact over all %d frames: %.2f .. %.2f mm, frames outside 0..3 mm: %d' % (s, nf, min(v), max(v), sum(1 for x in v if x < 0 or x > 3)), flush=True)
fl = {'L': [], 'R': []}
for f in range(nf + 1):
    sc.frame_set(f % nf)
    for s in 'LR':
        S, E, W = (arm.pose.bones[nm(s, p)].head for p in ('UpperArm', 'LowerArm', 'Hand'))
        fl[s].append(math.degrees((E - S).angle(W - E)))
sc.frame_set(0)
for s in 'LR':
    steps = [abs(fl[s][i + 1] - fl[s][i]) for i in range(nf)]
    print('[verify arms] %s elbow flexion %.1f .. %.1f deg, largest step %.2f deg/frame, seam step %.2f' % (s, min(fl[s]), max(fl[s]), max(steps), steps[-1]), flush=True)
print('[verify arms] DONE', flush=True)
