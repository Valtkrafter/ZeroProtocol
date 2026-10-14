"""Converts Blender/Yoru_<name>_pose.json (world rotation deltas in Blender axes) into the pose-stream format of the
Unity baker (YoruClipBaker): Unity axes, absolute hips position, HumanBodyBones names.

Blender -> Unity: (x, y, z) -> (x, z, y); a rotation quaternion (w, x, y, z) becomes Unity (x=-x, y=-z, z=-y, w=w)
(axis mapped, angle sign flipped because the mapping is a reflection; checked with yaw / pitch / roll examples).

usage: python export_stream.py <pose.json> <stream.json> <clip name> [loop 1/0]
"""
import json, os, sys

src, dst, name = sys.argv[1], sys.argv[2], sys.argv[3]
loop = (sys.argv[4] != '0') if len(sys.argv) > 4 else True
d = json.load(open(src))
hmap = d['humanoid_map']                                       # vrm key -> bone node name
keys = list(hmap)                                              # all humanoid bones present
unity_names = [k[0].upper() + k[1:] for k in keys]             # 'leftUpperArm' -> 'LeftUpperArm'
rest = d['hips_rest']                                          # Blender coords
frames = []
n = d['frames']                                                # includes the last key that repeats the first one: seamless loop
for fr in d['data'][:n]:
    off = fr['hips_world_offset']                              # Blender world displacement
    p = [rest[0] + off[0], rest[2] + off[2], rest[1] + off[1]]
    q = []
    for k in keys:
        w, x, y, z = fr['D'][hmap[k]]
        q.append([-x, -z, -y, w])
    frames.append({'p': p, 'q': q})
os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
json.dump({'name': name, 'source': 'Blender ' + os.path.basename(src), 'fps': d['fps'], 'loop': loop, 'speed': d.get('speed', 0.0),
           'outDir': 'Assets/Animations/Yoru', 'bones': unity_names, 'frames': frames}, open(dst, 'w'))
print('wrote', dst, len(frames), 'frames,', len(keys), 'bones')
