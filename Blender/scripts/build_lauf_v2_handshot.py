"""Lauf v2: close-up of both hands at given frames (camera aims at the hand bone, from outside-front and from the front), for checking the fist.
usage: blender -b --factory-startup <work .blend> --python build_lauf_v2_handshot.py -- <out png> <frames e.g. 0,20> [armature]"""
import bpy, sys, os, math
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUT, FR = argv[0], [int(x) for x in argv[1].split(',')]
AN = argv[2] if len(argv) > 2 else 'Yoru_Lauf'
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 360
sun = bpy.data.objects.new('sun_h', bpy.data.lights.new('sun_h', 'SUN'))
sun.data.energy = 3.5
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(55), 0, math.radians(35))
w = bpy.data.worlds.new('wh'); w.use_nodes = True
next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND').inputs['Color'].default_value = (0.20, 0.23, 0.30, 1)
scene.world = w
arm = bpy.data.objects[AN]
for o in bpy.data.objects:
    if o.type == 'MESH' and o.parent is not None and o.parent != arm:
        o.hide_render = True
cd = bpy.data.cameras.new('hc'); cd.lens = 85
cam = bpy.data.objects.new('hc', cd); scene.collection.objects.link(cam); scene.camera = cam
tgt = bpy.data.objects.new('ht', None); scene.collection.objects.link(tgt)
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
tiles = []
for f in FR:
    scene.frame_set(f)
    for side, sx in (('L', -1.0), ('R', 1.0)):
        pb = arm.pose.bones['J_Bip_%s_Hand' % side]
        p = arm.matrix_world @ pb.head
        for d in (Vector((sx * 0.8, 0.5, 0.15)), Vector((sx * 0.15, 0.95, 0.1))):
            tgt.location = p + Vector((0, 0.04, 0))
            cam.location = p + d.normalized() * 0.75
            fn = os.path.join(os.path.dirname(OUT), '_h_%d_%s_%d.png' % (f, side, len(tiles)))
            scene.render.filepath = fn
            bpy.ops.render.render(write_still=True)
            tiles.append(fn)
print('HANDS', ';'.join(tiles))
