"""
Yoru - IDLE v2, round 7: compares the body action of a final idle file with the one of an earlier final file (curves changed per group:
hair, ears, tail, other; largest step per frame per group; seam) and the face action (must be identical).
usage: blender -b --factory-startup <Blender/Yoru_Idle_v2.blend> --python build_idle_v2_verify_r7.py -- <earlier final .blend>
The earlier actions are appended into this session only (nothing is saved).
"""
import bpy, sys, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
OLD = sys.argv[sys.argv.index('--') + 1]
dy = {'__file__': os.path.join(HERE, 'build_idle_v2_dynamics_r7.py')}
exec(compile(open(dy['__file__'], encoding='utf-8').read(), dy['__file__'], 'exec'), dy)
before = set(a.name for a in bpy.data.actions)
with bpy.data.libraries.load(OLD, link=False) as (src, dst):
    dst.actions = [n for n in src.actions if n in ('Yoru_Idle_v2', 'Yoru_Idle_v2_Face')]
new_names = [a.name for a in bpy.data.actions if a.name not in before]
old_body = next(n for n in new_names if n.startswith('Yoru_Idle_v2') and 'Face' not in n)
old_face = next(n for n in new_names if 'Face' in n)
r = dy['compare_actions']('Yoru_Idle_v2', old_body)
print('[verify r7] body action vs earlier final:', r, flush=True)
A = {(fc.data_path, fc.array_index): fc for fc in dy['_fcurves'](bpy.data.actions['Yoru_Idle_v2_Face'])}
B = {(fc.data_path, fc.array_index): fc for fc in dy['_fcurves'](bpy.data.actions[old_face])}
same = all(abs(A[k].keyframe_points[i].co[1] - B[k].keyframe_points[i].co[1]) < 1e-9 for k in A for i in range(len(A[k].keyframe_points)))
print('[verify r7] face action identical to the earlier final:', same, '| curves', len(A), flush=True)
print('[verify r7] DONE', flush=True)
