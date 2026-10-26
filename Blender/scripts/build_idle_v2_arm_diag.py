"""
Yoru - IDLE v2, round 6: DIAGNOSIS of the arms (elbows, forearms, hands) in a baked idle file.
usage: blender -b --factory-startup <file .blend> --python build_idle_v2_arm_diag.py -- <out dir> [frames, default 0,90,200] [armature, default Yoru] [tag]
Renders close-ups of the arms (hip to shoulder, orthographic 0.75 m) from five directions: front-left 3/4, front-right 3/4, right side,
left side, back -> <out dir>/<tag>_<dir>_<frame>.png, and prints per arm and frame (lines starting with ARMDIAG):
  flex      elbow flexion (deg, 0 = straight)
  hinge     angle between the bend plane of the elbow (upper arm x forearm) and the hinge axis that the upper-arm bone carries
            (the rest hinge of this rig is world Z in the T-pose: palms down, elbow crease forward).  0 = the elbow bends about its hinge.
  twist     forearm roll against a pure hinge from the upper arm (deg; the rig has no twist bones, so all of it shows at elbow and wrist)
  uarm_rot  internal(+)/external(-) rotation of the upper arm against the plain swing from the T-pose (deg)
  elbow_out how far the elbow is out from the side of the chest (m, from the body centre line, x)
  hand_gap  nearest distance of the visible hand vertices to the visible gear / thigh / torso vertices (m), and the bone of that gear point
"""
import bpy, sys, os, math
from mathutils import Vector, Quaternion, Matrix
from mathutils.kdtree import KDTree

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
FRAMES = [int(x) for x in (argv[1] if len(argv) > 1 else '0,90,200').split(',')]
ARM = argv[2] if len(argv) > 2 else 'Yoru'
TAG = argv[3] if len(argv) > 3 else 'vorher'
os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
L = {}
exec(compile(open(os.path.join(HERE, 'build_idle_v2_lib.py'), encoding='utf-8').read(), os.path.join(HERE, 'build_idle_v2_lib.py'), 'exec'), L)
sc = bpy.context.scene
arm = bpy.data.objects[ARM]
H = L['humanoid_map']()
rig = L['Rig'](arm, H)
nm = rig.nm
bones = arm.data.bones


def D_of(name):
    """world (armature space) rotation of the bone from its rest: D = R_pose * R_rest^-1"""
    return arm.pose.bones[name].matrix.to_quaternion() @ bones[name].matrix_local.to_quaternion().inverted()


def arm_numbers(side):
    sx = -1.0 if side == 'L' else 1.0
    pb = arm.pose.bones
    S, E, Wr = pb[nm(side, 'UpperArm')].head, pb[nm(side, 'LowerArm')].head, pb[nm(side, 'Hand')].head
    du, df = (E - S).normalized(), (Wr - E).normalized()
    flex = math.degrees(du.angle(df))
    Du, Df = D_of(nm(side, 'UpperArm')), D_of(nm(side, 'LowerArm'))
    hinge = Du @ Vector((0.0, 0.0, sx))                      # rest hinge (crease forward, palm down) carried by the upper arm
    bend_n = du.cross(df)
    hinge_err = math.degrees(min(hinge.angle(bend_n), hinge.angle(-bend_n))) if bend_n.length > 1e-6 else 0.0
    # forearm twist: forearm frame against the upper-arm frame turned about the hinge by the flexion
    q_hinge = Quaternion(hinge.normalized(), math.radians(flex) * (1.0 if hinge.dot(bend_n) >= 0 else -1.0))
    Df0 = q_hinge @ Du
    rel = Df0.inverted() @ Df                                 # should be a pure roll about the rest arm axis
    axis_rest = Vector((sx, 0.0, 0.0))
    twist = math.degrees(2.0 * math.atan2(Vector((rel.x, rel.y, rel.z)).dot(axis_rest), rel.w))
    twist = (twist + 180.0) % 360.0 - 180.0
    # upper arm roll against the plain swing from the T-pose direction
    swing = axis_rest.rotation_difference(du)
    relu = swing.inverted() @ Du
    uroll = math.degrees(2.0 * math.atan2(Vector((relu.x, relu.y, relu.z)).dot(axis_rest), relu.w))
    uroll = (uroll + 180.0) % 360.0 - 180.0
    hips = pb[H['hips']].head
    return dict(flex=flex, hinge=hinge_err, twist=twist, uarm_rot=uroll * sx, elbow_out=abs(E.x - hips.x), elbow_y=E.y - hips.y)


# hand-to-gear distance on the evaluated mesh
body = rig.body
vis = L['visible_vertices'](body)
dom = L['vertex_groups_by_bone'](rig)
solid_bones = {H['hips'], H['spine'], H['chest'], H['upperChest'], H['leftUpperLeg'], H['rightUpperLeg']}
hand_bones = {}
for side in ('L', 'R'):
    s = {nm(side, 'Hand')}
    for fn in ('Index', 'Middle', 'Ring', 'Little'):
        for part in ('Proximal', 'Intermediate', 'Distal'):
            s.add(nm(side, fn + part))
    for part in ('ThumbProximal', 'ThumbIntermediate', 'ThumbDistal'):
        s.add(nm(side, part))
    hand_bones[side] = s


def hand_gap(co):
    solid = [i for i, n in enumerate(dom) if vis[i] and (n in solid_bones or (n.startswith('J_Sec_') and 'Hair' not in n))]
    kd = KDTree(len(solid))
    for k, i in enumerate(solid):
        kd.insert(co[i], k)
    kd.balance()
    out = {}
    for side in ('L', 'R'):
        best = (9.0, None)
        for i, n in enumerate(dom):
            if vis[i] and n in hand_bones[side]:
                _, k, d = kd.find(co[i])
                if d < best[0]:
                    best = (d, dom[solid[k]])
        out[side] = best
    return out


for f in FRAMES:
    sc.frame_set(f)
    co = L['evaluated_coords'](body)
    hg = hand_gap(co)
    for side in ('L', 'R'):
        a = arm_numbers(side)
        print('ARMDIAG %s frame %3d %s  flex %5.1f  hinge %4.1f  twist %6.1f  uarm_rot %6.1f  elbow_out %.3f  elbow_y %+.3f  hand_gap %.3f (%s)' % (
            TAG, f, side, a['flex'], a['hinge'], a['twist'], a['uarm_rot'], a['elbow_out'], a['elbow_y'], hg[side][0], hg[side][1]), flush=True)

# ---------------------------------------------------------------- close-up renders
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 480, 560
sc.eevee.taa_render_samples = 16
sun = bpy.data.lights.new('s_diag', 'SUN'); sun.energy = 3.5
so = bpy.data.objects.new('s_diag', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(55), 0, math.radians(35))
world = bpy.data.worlds.new('w_diag'); world.use_nodes = True
next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND').inputs['Color'].default_value = (0.20, 0.23, 0.30, 1.0)
sc.world = world
keep = set([arm.name] + [c.name for c in arm.children] + ['Boden'])
for o in bpy.data.objects:
    if o.name.startswith(('Icosphere', 'Label_')) or (o.type in ('MESH', 'FONT', 'CURVE') and o.name not in keep):
        o.hide_render = True                      # only this Yoru (a stage file holds several)
d = bpy.data.cameras.new('c_diag'); d.type = 'ORTHO'; d.ortho_scale = 0.75; d.clip_end = 50
cam = bpy.data.objects.new('c_diag', d); sc.collection.objects.link(cam); sc.camera = cam


def look(eye, target):
    fwd = (target - eye).normalized()
    right = fwd.cross(Vector((0.0, 0.0, 1.0))).normalized()
    up = right.cross(fwd).normalized()
    cam.matrix_world = Matrix((right, up, -fwd)).transposed().to_4x4()
    cam.location = eye


DIRS = {'vornlinks': Vector((-math.sin(math.radians(35)), math.cos(math.radians(35)), 0.05)),
        'vornrechts': Vector((math.sin(math.radians(35)), math.cos(math.radians(35)), 0.05)),
        'seiterechts': Vector((1.0, 0.0, 0.03)), 'seitelinks': Vector((-1.0, 0.0, 0.03)), 'ruecken': Vector((0.0, -1.0, 0.05))}
base = arm.matrix_world.translation.copy()
for f in FRAMES:
    sc.frame_set(f)
    M = arm.matrix_world
    hips = M @ arm.pose.bones[H['hips']].head
    for key, dv in DIRS.items():
        # fixed points relative to the pelvis (not the elbow, which moves when the arm changes): the before / after pictures match
        if key in ('vornlinks', 'seitelinks'):
            tgt = hips + Vector((-0.14, 0.0, 0.12))
        elif key in ('vornrechts', 'seiterechts'):
            tgt = hips + Vector((0.14, 0.0, 0.12))
        else:
            tgt = hips + Vector((0.0, 0.0, 0.12))
        look(tgt + dv.normalized() * 4.0, tgt)
        sc.render.filepath = os.path.join(OUT, '%s_%s_%03d.png' % (TAG, key, f))
        bpy.ops.render.render(write_still=True)
print('ARMDIAG DONE')
