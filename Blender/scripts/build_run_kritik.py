"""Ist / Soll view of the run (the user's 8-point critique of 2026-10-15) on top of the PLAYING stage 1 animation.
Yoru_Run.blend is only read; the result is saved as a COPY (default Blender/work/run/Yoru_Run_Kritik_Stufe1.blend).

usage: blender -b --factory-startup <Yoru_Run.blend> --python build_run_kritik.py -- [out .blend]

What it builds: the measured problems as coloured overlay geometry that follows the animation (baked from the evaluated pose, 37 keys, cycle modifiers),
one "slide" (collection + camera + text) per finding:
  1 fists too high   2 plaster-cast elbows   3 stair climber legs   4 foot twitch at toe off   5 board torso   6 puffed shoulders
  7a tail from above   7b tail from the side   8 hair and ears
Red = the problem as it is, green = the target (the plan), white / yellow / cyan = reference geometry.  All numbers in the texts come from
audit_run_critique.py / audit_run_mesh_motion.py (Blender/work/run/critique_baseline_stage1.txt).
The text is parented to the slide camera (a heads-up display in the 3D view), the geometry is drawn "in front" so it shows through the body.
show_run_kritik_live.py plays the slides one after the other in a normal Blender window, render_run_kritik.py renders stills of them.
The floor of the copy is darkened so that the colours and the text stand out (the original file keeps its floor)."""
import bpy, bmesh, json, math, os, sys, textwrap
from mathutils import Vector, Quaternion, Euler, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = ARGS[0] if ARGS else r'C:\Users\valen\ZeroProtocol\Blender\work\run\Yoru_Run_Kritik_Stufe1.blend'

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
B = arm.data.bones
NF = 36
FR = list(range(NF + 1))                   # key 36 == key 0 (the cycle modifiers repeat 0 .. 36)
LINE_K, DOT_K, LABEL_K = 1.4, 1.25, 1.5    # overlay sizes are given for a full body view; these make them readable in the live window

# ------------------------------------------------------------------ colours
RED = (1.0, 0.16, 0.12, 1.0)
GREEN = (0.15, 0.92, 0.32, 1.0)
YELLOW = (1.0, 0.86, 0.10, 1.0)
CYAN = (0.20, 0.78, 1.0, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
ORANGE = (1.0, 0.55, 0.08, 1.0)
MAGENTA = (1.0, 0.30, 0.90, 1.0)
GREY = (0.78, 0.80, 0.86, 1.0)

# ------------------------------------------------------------------ the sampled pose (world positions; the armature object has an identity transform)
# plus a few vertices of the hair mesh (the visible hair, not only its bones): top of the head, both sides, the back, the lowest point on each side
hair_ob = bpy.data.objects['Hair']
_mw = hair_ob.matrix_world
_rest = [_mw @ v.co for v in hair_ob.data.vertices]
_n = range(len(_rest))
HAIR_IDX = {
    'top': max(_n, key=lambda i: _rest[i].z),
    'left': min(_n, key=lambda i: _rest[i].x if _rest[i].z > 1.25 else 9.0),
    'right': max(_n, key=lambda i: _rest[i].x if _rest[i].z > 1.25 else -9.0),
    'back': min(_n, key=lambda i: _rest[i].y if 1.25 < _rest[i].z < 1.55 else 9.0),
    'low_L': min(_n, key=lambda i: _rest[i].z if _rest[i].x < 0.0 else 9.0),
    'low_R': min(_n, key=lambda i: _rest[i].z if _rest[i].x > 0.0 else 9.0),
}
POSE = {}
HAIRV = {k: [] for k in HAIR_IDX}
for f in FR:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm.evaluated_get(dg)
    for pb in ae.pose.bones:
        POSE.setdefault(pb.name, []).append((pb.head.copy(), pb.tail.copy(), pb.matrix.copy()))
    he = hair_ob.evaluated_get(dg)
    me = he.to_mesh()
    for k, i in HAIR_IDX.items():
        HAIRV[k].append(_mw @ me.vertices[i].co)
    he.to_mesh_clear()


def heads(n):
    return [POSE[n][i][0] for i in FR]


def tails(n):
    return [POSE[n][i][1] for i in FR]


def mats(n):
    return [POSE[n][i][2] for i in FR]


def qangle(q1, q2):
    return math.degrees(2.0 * math.acos(min(1.0, abs(q1.dot(q2)))))


def steps_of(n):
    """world rotation step (deg) of a bone from the previous frame to this one (frame 0 uses frame 35); 37 values, the last equals the first"""
    qs = [POSE[n][i][2].to_quaternion() for i in FR]
    return [qangle(qs[(i - 1) % NF], qs[i % NF]) for i in range(NF)] + [qangle(qs[NF - 1], qs[0])]


HIPS, SPINE, CHEST, UCHEST, NECK, HEAD = 'J_Bip_C_Hips', 'J_Bip_C_Spine', 'J_Bip_C_Chest', 'J_Bip_C_UpperChest', 'J_Bip_C_Neck', 'J_Bip_C_Head'
SIDES = ('R', 'L')


def bn(side, part):
    return 'J_Bip_%s_%s' % (side, part)


# ------------------------------------------------------------------ chin of the face mesh (rest pose), carried by the head bone
def chin_points():
    rest = None
    hb = B[HEAD]
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or 'face' not in ob.name.lower():
            continue
        vg = ob.vertex_groups.get(HEAD)
        if vg is None:
            continue
        for v in ob.data.vertices:
            w = 0.0
            for g in v.groups:
                if g.group == vg.index:
                    w = g.weight
            if w < 0.5:
                continue
            p = ob.matrix_world @ v.co
            if abs(p.x) > 0.045 or p.y < hb.head_local.y + 0.02:
                continue
            if rest is None or p.z < rest.z:
                rest = p.copy()
    if rest is None:
        rest = hb.head_local + Vector((0.0, 0.078, -0.034))
    inv = hb.matrix_local.inverted()
    return [m @ (inv @ rest) for m in mats(HEAD)]


CHIN = chin_points()

# ------------------------------------------------------------------ material, meshes, fonts
MAT = bpy.data.materials.new('KRITIK_emission')
MAT.use_nodes = True
_nt = MAT.node_tree
_nt.nodes.clear()
_out = _nt.nodes.new('ShaderNodeOutputMaterial')
_em = _nt.nodes.new('ShaderNodeEmission')
_oi = _nt.nodes.new('ShaderNodeObjectInfo')
_nt.links.new(_oi.outputs['Color'], _em.inputs['Color'])
_nt.links.new(_em.outputs['Emission'], _out.inputs['Surface'])


def _mesh(kind):
    me = bpy.data.meshes.new('kritik_' + kind)
    bm = bmesh.new()
    if kind == 'cyl':                                    # radius 1, z from 0 to 1
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=8, radius1=1.0, radius2=1.0, depth=1.0)
        bmesh.ops.translate(bm, vec=(0.0, 0.0, 0.5), verts=bm.verts)
    else:
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)
        for fc in bm.faces:
            fc.smooth = True
    bm.to_mesh(me)
    bm.free()
    me.materials.append(MAT)
    return me


CYL, SPH = _mesh('cyl'), _mesh('sph')
try:
    FONT_R = bpy.data.fonts.load(r'C:\Windows\Fonts\arial.ttf')
    FONT_B = bpy.data.fonts.load(r'C:\Windows\Fonts\arialbd.ttf')
except Exception as e:                                   # the built-in font has no umlauts / degree sign in every build
    print('font:', e)
    FONT_R = FONT_B = None

COLL_ALL = []                                            # the overlay objects (for the cycle modifiers)
UPV = Vector((0.0, 0.0, 1.0))


# ------------------------------------------------------------------ overlay primitives
def _as_list(v):
    return v if isinstance(v, list) else [v] * len(FR)


def _color_keys(ob, color):
    cols = [tuple(c) for c in color] if isinstance(color, list) else [tuple(color)] * len(FR)
    ob.color = cols[0]
    return cols if len(set(cols)) > 1 else None


def _finish(ob, coll):
    coll.objects.link(ob)
    ob.show_in_front = True                                  # (only honoured by the solid view; the real see-through comes from SHIFT)
    COLL_ALL.append(ob)


# Blender's "In Front" does not work in the material preview, so the overlay is moved towards the camera by SHIFT (along the view axis of the
# slide; the cameras are orthographic, so this does not change where the overlay appears in the picture) and ends up in front of the whole body.
SHIFT = Vector((0.0, 0.0, 0.0))
SHIFT_LEN = 1.0
VIEW_DIR = {'side': Vector((1.0, 0.0, 0.0)), 'front': Vector((0.0, 1.0, 0.0)), 'top': Vector((0.0, 0.0, 1.0))}


def _sh(v):
    return [p + SHIFT for p in v] if isinstance(v, list) else v + SHIFT


def make_line(coll, name, p0, p1, color, radius=0.005):
    """cylinder from p0 to p1 (Vectors or per-frame lists of Vectors); colour RGBA or per-frame list"""
    radius *= LINE_K
    ob = bpy.data.objects.new(name, CYL)
    ob.rotation_mode = 'QUATERNION'
    a, b = _as_list(_sh(p0)), _as_list(_sh(p1))
    animated = isinstance(p0, list) or isinstance(p1, list)
    ckeys = _color_keys(ob, color)
    _finish(ob, coll)
    prev = None
    for i, f in enumerate(FR):
        d = b[i] - a[i]
        ln = d.length
        q = UPV.rotation_difference(d / ln) if ln > 1e-6 else Quaternion((1.0, 0.0, 0.0, 0.0))
        if prev is not None and q.dot(prev) < 0.0:
            q.negate()
        prev = q
        ob.location, ob.rotation_quaternion, ob.scale = a[i], q, (radius, radius, max(ln, 1e-6))
        if animated:
            ob.keyframe_insert('location', frame=f)
            ob.keyframe_insert('rotation_quaternion', frame=f)
            ob.keyframe_insert('scale', frame=f)
        if ckeys is not None:
            ob.color = ckeys[i]
            ob.keyframe_insert('color', frame=f)
        if not animated and ckeys is None:
            break
    return ob


def make_dot(coll, name, p, color, radius=0.03):
    radius *= DOT_K
    ob = bpy.data.objects.new(name, SPH)
    ob.scale = (radius, radius, radius)
    pos = _as_list(_sh(p))
    animated = isinstance(p, list)
    ckeys = _color_keys(ob, color)
    _finish(ob, coll)
    for i, f in enumerate(FR):
        ob.location = pos[i]
        if animated:
            ob.keyframe_insert('location', frame=f)
        if ckeys is not None:
            ob.color = ckeys[i]
            ob.keyframe_insert('color', frame=f)
        if not animated and ckeys is None:
            break
    return ob


def make_polyline(coll, name, pts, color, radius=0.008):
    """pts: list over the frames of a list of points (the same number every frame)"""
    n = len(pts[0])
    for k in range(n - 1):
        make_line(coll, '%s_%d' % (name, k), [pts[i][k] for i in range(len(FR))], [pts[i][k + 1] for i in range(len(FR))], color, radius)


def make_trail(coll, name, points, color, radius=0.004, frame_mats=None):
    """one mesh with a cylinder between neighbouring points; static, or following a per-frame matrix list (the trail then lives in that frame)"""
    radius *= LINE_K
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    if not frame_mats:
        points = _sh(points)
    for p0, p1 in zip(points, points[1:]):
        d = p1 - p0
        ln = d.length
        if ln < 1e-6:
            continue
        q = UPV.rotation_difference(d / ln)
        # the cone is made around its centre: lift it by 0.5 so that it spans z 0 .. 1, then scale, turn and move it onto the segment
        m = Matrix.Translation(p0) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((radius, radius, ln, 1.0)) @ Matrix.Translation((0.0, 0.0, 0.5))
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=1.0, radius2=1.0, depth=1.0, matrix=m)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(MAT)
    ob = bpy.data.objects.new(name, me)
    ob.color = color
    ob.rotation_mode = 'QUATERNION'
    _finish(ob, coll)
    if frame_mats:
        prev = None
        for i, f in enumerate(FR):
            ob.location = frame_mats[i].translation + SHIFT
            q = frame_mats[i].to_quaternion()
            if prev is not None and q.dot(prev) < 0.0:
                q.negate()
            prev = q
            ob.rotation_quaternion = q
            ob.keyframe_insert('location', frame=f)
            ob.keyframe_insert('rotation_quaternion', frame=f)
    return ob


def make_text(coll, name, body, loc, rot, size, color, bold=False, align='LEFT', parent=None):
    """3D text.  loc: Vector (static) or per-frame list (follows a point); rot: Euler; parent: a camera (heads-up display)"""
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = body
    if (FONT_B if bold else FONT_R) is not None:
        cu.font = FONT_B if bold else FONT_R
    cu.size = size
    cu.align_x = align
    cu.align_y = 'CENTER'
    cu.extrude = 0.0
    cu.materials.append(MAT)
    ob = bpy.data.objects.new(name, cu)
    ob.color = color
    ob.rotation_euler = rot
    if parent is not None:
        ob.parent = parent
    animated = isinstance(loc, list)
    _finish(ob, coll)
    pos = _as_list(loc if parent is not None else _sh(loc))     # the heads-up display (parent = camera) stays where it is
    for i, f in enumerate(FR):
        ob.location = pos[i]
        if animated:
            ob.keyframe_insert('location', frame=f)
        else:
            break
    return ob


# ------------------------------------------------------------------ cameras and the heads-up display
D_H = 2.0                                                # the text sits this far in front of its camera
CAMS = bpy.data.collections.new('Kritik_Kameras')
scene.collection.children.link(CAMS)


def make_cam(name, target, width, view):
    """orthographic camera (16:9, `width` metres wide) 10 m away from the target, looking at it from the side (+x), the front (+y) or the top (+z)"""
    cd = bpy.data.cameras.new(name)
    cd.type = 'ORTHO'
    cd.ortho_scale = width
    cd.sensor_fit = 'HORIZONTAL'
    cd.clip_start = 0.1
    cd.clip_end = 100.0
    ob = bpy.data.objects.new(name, cd)
    CAMS.objects.link(ob)
    loc = Vector(target) + VIEW_DIR[view] * 10.0
    ob.location = loc
    if view == 'top':
        ob.rotation_euler = (0.0, 0.0, 0.0)                  # looks down, her forward direction (+y) is up in the picture
    else:
        ob.rotation_euler = (Vector(target) - loc).to_track_quat('-Z', 'Y').to_euler()
    return ob


def hud(coll, cam, n_of, title, subtitle, ist, soll, legend):
    """title (top left), IST column (left, red), SOLL column (right, green), legend (bottom)"""
    rot0 = Euler((0.0, 0.0, 0.0))
    half_w = cam.data.ortho_scale / 2.0
    half_h = half_w * 9.0 / 16.0
    frame_h = 2.0 * half_h

    def put(name, body, u, v, rel, color, bold=False, align='LEFT'):
        make_text(coll, name, body, Vector((u * half_w, v * half_h, -D_H)), rot0, rel * frame_h, color, bold, align, parent=cam)

    put('hud_title', title, -0.97, 0.92, 0.062, WHITE, True)
    put('hud_count', n_of, 0.97, 0.92, 0.040, GREY, False, 'RIGHT')
    put('hud_sub', subtitle, -0.97, 0.80, 0.034, GREY)

    def column(prefix, head, lines, u, color_head, color_line):
        put(prefix + '_head', head, u, 0.64, 0.046, color_head, True)
        v = 0.52
        k = 0
        for ln in lines:
            for piece in textwrap.wrap(ln, 27):
                put('%s_%d' % (prefix, k), piece, u, v, 0.037, color_line)
                v -= 0.098
                k += 1
            v -= 0.03
    column('hud_ist', 'IST', ist, -0.97, RED, (1.0, 0.84, 0.82, 1.0))
    column('hud_soll', 'SOLL (Plan)', soll, 0.40, GREEN, (0.86, 1.0, 0.88, 1.0))
    put('hud_legend', legend, 0.0, -0.93, 0.032, GREY, False, 'CENTER')


LABEL_ROT = {'side': Euler((math.radians(90), 0.0, math.radians(90))),     # the camera stands at +x (her right) and looks along -x: reading direction +y, up +z
             'front': Euler((math.radians(90), 0.0, math.radians(180))),   # the camera stands at +y and looks along -y: reading direction -x
             'top': Euler((0.0, 0.0, 0.0))}


def label(coll, name, body, anchor, view, color, size=0.05, dx=0.0, dy=0.0, dz=0.0, align='LEFT'):
    """a small text next to a (moving) point; dx / dy / dz in world axes"""
    off = Vector((dx, dy, dz))
    loc = [a + off for a in anchor] if isinstance(anchor, list) else anchor + off
    return make_text(coll, name, body, loc, LABEL_ROT[view], size * LABEL_K, color, False, align)


# ------------------------------------------------------------------ common series
CHIN_Z = [c.z for c in CHIN]
UCHEST_Z = [h.z for h in heads(UCHEST)]
SPINE_Z = [h.z for h in heads(SPINE)]
HIPS_P = heads(HIPS)
HIP_MID = [(a + b) * 0.5 for a, b in zip(heads(bn('R', 'UpperLeg')), heads(bn('L', 'UpperLeg')))]
SLIDES = []
TOTAL = 9


def new_slide(key, view, target, width, fps=60, dwell=10.0):
    global SHIFT
    coll = bpy.data.collections.new(key)
    scene.collection.children.link(coll)
    cam = make_cam('cam_' + key, target, width, view)
    SHIFT = VIEW_DIR[view] * SHIFT_LEN                       # everything built from here on moves in front of the body
    SLIDES.append({'name': key, 'camera': cam.name, 'fps': fps, 'dwell': dwell, 'view': view, 'floor': view != 'top'})   # the top view is clearer without the checker floor
    return coll, cam


# ------------------------------------------------------------------ slide 1: fists too high
def slide1():
    coll, cam = new_slide('S1_Faeuste', 'side', (0.0, 0.0, 1.08), 2.9)
    for nm, zs, col, txt in (('chin', CHIN_Z, RED, 'Kinn'), ('chest', UCHEST_Z, GREEN, 'Brust'), ('belly', SPINE_Z, GREEN, 'Bauch')):
        p0 = [Vector((0.0, h.y - 0.28, z)) for h, z in zip(HIPS_P, zs)]
        p1 = [Vector((0.0, h.y + 0.46, z)) for h, z in zip(HIPS_P, zs)]
        make_line(coll, 'S1_line_' + nm, p0, p1, col, 0.005)
        label(coll, 'S1_lab_' + nm, txt, p0, 'side', col, 0.045, dy=-0.03, align='RIGHT')
    for s in SIDES:
        kn = heads(bn(s, 'Middle1'))
        flags = [kn[i].z > UCHEST_Z[i] for i in range(len(FR))]
        print('KRITIK fist above the chest line, side %s: %d of %d frames' % (s, sum(flags[:NF]), NF))
        make_dot(coll, 'S1_fist_' + s, kn, [RED if fl else GREEN for fl in flags], 0.034)
        make_dot(coll, 'S1_wrist_' + s, heads(bn(s, 'Hand')), GREY, 0.018)
    hud(coll, cam, '1 von %d' % TOTAL, 'FÄUSTE ZU HOCH', 'Seitenansicht, Echtzeit',
        ['Die Faust steigt vorn bis 3 cm unter das Kinn.', 'Je Faust liegt sie ein Drittel der Zeit über der Brustlinie.', 'Der Ellbogen ist vorn 101° gebeugt.'],
        ['Fäuste auf Brust- bis Bauchhöhe (zwischen den grünen Linien).', 'Ellbogen vorn nur etwa 70 bis 75° gebeugt.'],
        'Kugel rot = Faust über der Brustlinie, grün = im Soll-Bereich')


# ------------------------------------------------------------------ slide 2: plaster-cast elbows
def slide2():
    coll, cam = new_slide('S2_Ellbogen', 'side', (0.0, 0.0, 1.08), 2.9)
    for s in SIDES:
        sh, el, wr, kn = heads(bn(s, 'UpperArm')), heads(bn(s, 'LowerArm')), heads(bn(s, 'Hand')), heads(bn(s, 'Middle1'))
        flags = []
        for i in range(len(FR)):
            fo = wr[i] - el[i]
            ang = math.degrees(math.atan2(fo.z, fo.y))
            flags.append(abs(ang) < 25.0 or abs(abs(ang) - 180.0) < 25.0)
        print('KRITIK forearm horizontal, side %s: %d of %d frames' % (s, sum(flags[:NF]), NF))
        make_line(coll, 'S2_upper_' + s, sh, el, YELLOW, 0.008)
        make_line(coll, 'S2_fore_' + s, el, kn, [RED if fl else ORANGE for fl in flags], 0.011)
        make_line(coll, 'S2_plumb_' + s, el, [e - Vector((0.0, 0.0, 0.30)) for e in el], GREEN, 0.004)
        make_dot(coll, 'S2_elbow_' + s, el, WHITE, 0.022)
    hud(coll, cam, '2 von %d' % TOTAL, 'ELLBOGEN WIE EINGEGIPST', 'Seitenansicht, Echtzeit',
        ['Der Ellbogenwinkel pendelt nur zwischen 76° und 103° (Mittel 89°).', 'Im Rückschwung zeigt der Unterarm nur 50° nach unten.', 'Waagerecht (rot) ist er in 36 % der Bilder.'],
        ['Hinten Ellbogen nur 40 bis 48°: der Unterarm hängt fast senkrecht (grüne Linie).', 'Vorn etwa 70 bis 75°.'],
        'Unterarm rot = waagerecht (±25°), orange = sonst; gelb = Oberarm; grün = Senkrechte')


# ------------------------------------------------------------------ slide 3: stair climber legs
def slide3():
    coll, cam = new_slide('S3_Beine', 'side', (0.0, -0.05, 0.62), 3.1)
    for s in SIDES:
        hp_, kp_ = heads(bn(s, 'UpperLeg')), heads(bn(s, 'LowerLeg'))
        ang = [math.degrees(math.atan2((kp_[i] - hp_[i]).y, -(kp_[i] - hp_[i]).z)) for i in range(len(FR))]
        ext = [hp_[i] + (kp_[i] - hp_[i]).normalized() * 0.66 for i in range(len(FR))]
        make_line(coll, 'S3_thigh_' + s, hp_, ext, [RED if a > 55.0 else CYAN for a in ang], 0.009)
        make_dot(coll, 'S3_knee_' + s, kp_, WHITE, 0.026)
    for nm, a, col, txt in (('front', 55.0, GREEN, '+55°'), ('rear', -25.0, GREEN, '-25°'), ('plumb', 0.0, GREY, 'Lot')):
        tip = [c + Vector((0.0, 0.66 * math.sin(math.radians(a)), -0.66 * math.cos(math.radians(a)))) for c in HIP_MID]
        make_line(coll, 'S3_fan_' + nm, HIP_MID, tip, col, 0.0045)
        label(coll, 'S3_lab_' + nm, txt, tip, 'side', col, 0.06, dy=0.04 if a >= 0 else -0.04, dz=-0.02, align='LEFT' if a >= 0 else 'RIGHT')
    hud(coll, cam, '3 von %d' % TOTAL, 'TREPPENSTEIGER-BEINE', 'Seitenansicht, Echtzeit',
        ['Der Oberschenkel geht vorn +68°, hinten nur -12°.', '85 % der Schwingung liegen vor dem Körper.', 'Das Knie steigt bis 13 cm unter die Hüfte und ist beim Absprung noch 26° gebeugt.'],
        ['Vorn +52 bis +55°, hinten -22 bis -25° (die grünen Strahlen).', 'Knie beim Absprung 15 bis 20°.'],
        'Oberschenkel rot = über +55°, cyan = sonst')


# ------------------------------------------------------------------ slide 4: foot twitch at toe off (a quarter of the speed)
def slide4():
    coll, cam = new_slide('S4_Fuss', 'side', (0.0, 0.0, 0.45), 2.6, fps=15, dwell=14.0)
    for s in SIDES:
        kn, an, tb, tt = heads(bn(s, 'LowerLeg')), heads(bn(s, 'Foot')), heads(bn(s, 'ToeBase')), tails(bn(s, 'ToeBase'))
        st_sh, st_ft = steps_of(bn(s, 'LowerLeg')), steps_of(bn(s, 'Foot'))
        fl_sh = [st_sh[i] > 8.0 or st_sh[(i + 1) % NF] > 8.0 for i in range(len(FR))]
        fl_ft = [st_ft[i] > 8.0 or st_ft[(i + 1) % NF] > 8.0 for i in range(len(FR))]
        make_line(coll, 'S4_shank_' + s, kn, an, [RED if x else CYAN for x in fl_sh], 0.011)
        make_line(coll, 'S4_foot_' + s, an, tb, [RED if x else CYAN for x in fl_ft], 0.011)
        make_line(coll, 'S4_toe_' + s, tb, tt, [RED if x else CYAN for x in fl_ft], 0.008)
        make_dot(coll, 'S4_knee_' + s, kn, WHITE, 0.024)
        make_dot(coll, 'S4_ankle_' + s, an, [RED if x else WHITE for x in fl_ft], 0.024)
    # the right leg at frame 7 (white) and frame 8 (red): the jump at toe off
    kn7, an7, tb7 = heads(bn('R', 'LowerLeg'))[7], heads(bn('R', 'Foot'))[7], heads(bn('R', 'ToeBase'))[7]
    kn8, an8, tb8 = heads(bn('R', 'LowerLeg'))[8], heads(bn('R', 'Foot'))[8], heads(bn('R', 'ToeBase'))[8]
    for nm, a, b, c, col in (('7', kn7, an7, tb7, WHITE), ('8', kn8, an8, tb8, RED)):
        make_line(coll, 'S4_ghost_shank_' + nm, a, b, col, 0.004)
        make_line(coll, 'S4_ghost_foot_' + nm, b, c, col, 0.004)
    label(coll, 'S4_lab_7', 'Bild 7', tb7, 'side', WHITE, 0.05, dy=-0.10, dz=0.02, align='RIGHT')
    label(coll, 'S4_lab_8', 'Bild 8', tb8, 'side', RED, 0.05, dy=-0.10, dz=-0.05, align='RIGHT')
    # the path of the right ankle, one dot per frame: the gaps show the speed
    an_r = heads(bn('R', 'Foot'))
    st = steps_of(bn('R', 'Foot'))
    for i in range(NF):
        make_dot(coll, 'S4_path_%02d' % i, an_r[i], RED if st[i] > 8.0 else YELLOW, 0.010)
    hud(coll, cam, '4 von %d' % TOTAL, 'FUSS-ZUCKEN BEIM ABSPRUNG', 'Seitenansicht, ZEITLUPE 1/4 nur für diese Folie',
        ['Absprung, Bild 7 zu 8: Das Knie dreht von -9,3° auf +9,4° pro Bild um, der Fuß springt 18,6° in einem Bild.', 'Aufsetzen: Das Knie springt von 15° auf 34,5°, der Unterschenkel 15,6° in einem Bild.'],
        ['Kein Knochen über 8° pro Bild, die Änderung unter 6°.', 'Die Ferse rollt weich ab, der Fuß schwingt gleitend nach vorn.'],
        'rot = Sprung über 8° pro Bild; gelbe Punkte = rechter Knöchel, ein Punkt je Bild')


# ------------------------------------------------------------------ slide 5: board torso
def slide5():
    coll, cam = new_slide('S5_Rumpf', 'side', (0.0, 0.0, 1.10), 2.7)
    chain = [HIPS, SPINE, CHEST, UCHEST, NECK, HEAD]
    pts = [[POSE[n][i][0] for n in chain] + [POSE[HEAD][i][1]] for i in range(len(FR))]
    make_polyline(coll, 'S5_spine', pts, YELLOW, 0.012)
    for k, n in enumerate(chain):
        make_dot(coll, 'S5_joint_%d' % k, heads(n), WHITE, 0.024)
    make_dot(coll, 'S5_headtop', tails(HEAD), CYAN, 0.03)
    make_line(coll, 'S5_plumb', HIPS_P, [h + Vector((0.0, 0.0, 0.64)) for h in HIPS_P], GREY, 0.004)
    for a in (16.0, 18.0):
        tip = [h + Vector((0.0, 0.64 * math.sin(math.radians(a)), 0.64 * math.cos(math.radians(a)))) for h in HIPS_P]
        make_line(coll, 'S5_soll_%d' % int(a), HIPS_P, tip, GREEN, 0.0045)
    hud(coll, cam, '5 von %d' % TOTAL, 'STEIFES BRETT ALS OBERKÖRPER', 'Seitenansicht, Echtzeit',
        ['Die Neigung ist fest 12° (nur ±1°).', 'Die Wirbelgelenke nicken nur 1 bis 2°.', 'Der Kopf sitzt mit 0,0° starr am Hals.', 'Gedreht wird nur in einem Gelenk (±11°).'],
        ['Neigung 16 bis 18° (grüne Strahlen).', 'Jedes Wirbelgelenk nickt 1 bis 1,5° mit Zeitversatz und neigt sich 2 bis 3° zur Seite.', 'Der Kopf macht 15 bis 20 % mit.'],
        'gelb = Rumpflinie Hüfte bis Kopf (Ist 12°), weiß = Lot, grün = Soll 16 bis 18°')


# ------------------------------------------------------------------ slide 6: puffed shoulders (front view)
def slide6():
    coll, cam = new_slide('S6_Schultern', 'front', (0.0, 0.0, 1.10), 2.3)
    for sg, tag in ((1.0, 'p'), (-1.0, 'm')):
        make_line(coll, 'S6_edge_' + tag, Vector((sg * 0.152, 0.03, 0.86)), Vector((sg * 0.152, 0.03, 1.42)), GREY, 0.004)
        make_line(coll, 'S6_soll_' + tag, Vector((sg * 0.170, 0.03, 0.86)), Vector((sg * 0.170, 0.03, 1.42)), GREEN, 0.004)
        make_line(coll, 'S6_extent_' + tag, Vector((sg * 0.238, 0.03, 0.86)), Vector((sg * 0.238, 0.03, 1.42)), RED, 0.004)
    for s in SIDES:
        sh, el, wr = heads(bn(s, 'UpperArm')), heads(bn(s, 'LowerArm')), heads(bn(s, 'Hand'))
        out_fore = [abs(wr[i].x) > abs(el[i].x) for i in range(len(FR))]
        make_line(coll, 'S6_upper_' + s, sh, el, YELLOW, 0.009)
        make_line(coll, 'S6_fore_' + s, el, wr, [RED if o else GREEN for o in out_fore], 0.011)
        make_dot(coll, 'S6_elbow_' + s, el, [RED if abs(p.x) > 0.17 else GREEN for p in el], 0.03)
        make_dot(coll, 'S6_wrist_' + s, wr, [RED if abs(p.x) > 0.13 else GREEN for p in wr], 0.026)
        make_dot(coll, 'S6_shoulder_' + s, sh, WHITE, 0.022)
    hud(coll, cam, '6 von %d' % TOTAL, 'AUFGEPLUSTERTE SCHULTERN', 'Frontansicht, Echtzeit',
        ['Die Oberarme stehen 17 bis 27° vom Körper ab (Mittel 23°).', 'Die Unterarme zeigen 3 bis 9° nach außen.', 'Die Arme ragen im Schnitt 8,4 cm über die Rumpfkante.', 'Die Schultern bewegen sich nur ±4 mm mit.'],
        ['Oberarme nur 10 bis 12° vom Körper, Unterarme 10 bis 12° nach innen.', 'Hände vor der Brust, schmale Silhouette.', 'Die Schulterblätter gehen mit.'],
        'Linien: grau = Rumpfkante 15 cm, grün = Soll-Breite 17 cm (Vorschlag), rot = äußerste Armkante 24 cm.  Rot = außerhalb')


# ------------------------------------------------------------------ slides 7a / 7b: the tail
def tail_data():
    names = ['J_Opt_C_CatTail%d_01' % j for j in range(1, 7)]
    chain = [heads(n) for n in names] + [heads('J_Opt_C_CatTail8_end_01')]
    pts = [[c[i] for c in chain] for i in range(len(FR))]
    tip = chain[-1]
    seg = [(chain[k + 1][0] - chain[k][0]).length for k in range(len(chain) - 1)]
    return pts, tip, seg


def slide7(view):
    key = 'S7a_Schwanz_oben' if view == 'top' else 'S7b_Schwanz_seite'
    if view == 'top':
        coll, cam = new_slide(key, 'top', (0.0, -0.20, 0.0), 2.8)
    else:
        coll, cam = new_slide(key, 'side', (0.0, -0.22, 0.98), 2.5)
    pts, tip, seg = tail_data()
    make_polyline(coll, 'S7_tail', pts, CYAN, 0.014)
    make_dot(coll, 'S7_tip', tip, RED, 0.034)
    make_trail(coll, 'S7_trail', tip[:NF] + [tip[0]], MAGENTA, 0.006)
    if view == 'top':
        make_line(coll, 'S7_centre', Vector((0.0, -0.80, 1.0)), Vector((0.0, 0.10, 1.0)), GREY, 0.004)
    else:
        angs = [28.0, 22.0, 14.0, 6.0, 0.0, -5.0]
        soll = []
        for i in range(len(FR)):
            p = pts[i][0].copy()
            line = [p.copy()]
            for a, ln in zip(angs, seg):
                p = p + Vector((0.0, -math.cos(math.radians(a)) * ln, math.sin(math.radians(a)) * ln))
                line.append(p.copy())
            soll.append(line)
        make_polyline(coll, 'S7_soll', soll, GREEN, 0.011)
        label(coll, 'S7_lab_soll', 'Soll-Bogen', [s[-1] for s in soll], 'side', GREEN, 0.05, dy=-0.05, dz=0.07, align='RIGHT')
        label(coll, 'S7_lab_ist', 'Ist', tip, 'side', CYAN, 0.05, dy=-0.05, dz=-0.05, align='RIGHT')
        label(coll, 'S7_lab_trail', 'Spur der Spitze', tip, 'side', MAGENTA, 0.045, dy=-0.05, dz=-0.14, align='RIGHT')
    hud(coll, cam, ('7a von %d' if view == 'top' else '7b von %d') % TOTAL, 'ANTENNEN-SCHWANZ', 'Draufsicht, Echtzeit' if view == 'top' else 'Seitenansicht, Echtzeit',
        ['Die Spitze bleibt immer 41 bis 44 cm hinter der Hüfte (±1,2 cm).', 'Von oben pendelt sie ±8 cm seitlich wie ein Metronom.', 'Die Form ist ein flaches J ohne Bogen.'],
        ['Bogen nach oben: +25 bis +32° an der Basis, zur Spitze abflachend.', 'Eine Welle läuft zur Spitze, Seiten- und Höhenausschlag wachsen von 2° auf 10 bis 12°.'],
        'cyan = Schwanz, rot = Spitze, magenta = Spur der Spitze über einen Zyklus' + (', weiß = Mittellinie' if view == 'top' else ', grün = Soll-Bogen'))


# ------------------------------------------------------------------ slide 8: hair and ears
def slide8():
    coll, cam = new_slide('S8_Haare', 'side', (0.0, -0.05, 1.40), 1.7)
    head_m = mats(HEAD)
    head_inv = [m.inverted() for m in head_m]
    tips = [('Ohr_L', heads('J_Opt_L_CatEar2_end_01'), WHITE), ('Ohr_R', heads('J_Opt_R_CatEar2_end_01'), WHITE)]    # the head of the end bone is the visible ear tip
    for k, series in HAIR_IDX.items():
        tips.append(('Haar_' + k, HAIRV[k], YELLOW if k.startswith('low') else WHITE))
    for nm, series, col in tips:
        loc = [head_inv[i] @ series[i] for i in range(len(FR))]
        make_trail(coll, 'S8_trail_' + nm, loc[:NF] + [loc[0]], CYAN, 0.0025, frame_mats=head_m)
        make_dot(coll, 'S8_dot_' + nm, series, col, 0.011)
    a0, a1 = Vector((0.25, 0.28, 1.72)), Vector((0.25, -0.22, 1.72))
    make_line(coll, 'S8_wind', a0, a1, GREEN, 0.007)
    for sgn in (1.0, -1.0):
        make_line(coll, 'S8_windhead_%d' % int(sgn), a1, a1 + Vector((0.0, 0.07, sgn * 0.04)), GREEN, 0.007)
    label(coll, 'S8_lab_wind', 'Fahrtwind (fehlt)', Vector((0.25, 0.03, 1.78)), 'side', GREEN, 0.04, align='CENTER')
    hud(coll, cam, '8 von %d' % TOTAL, 'LEBLOSE HAARE UND OHREN', 'Seitenansicht, Echtzeit',
        ['Die Haarmasse bewegt sich gegen den Kopf nur 2 mm (Median).', 'Nur die Enden der langen Strähnen schwingen (bis 7 cm), im Mittel liegen sie genau an der Ruhelage.', 'Die Ohrspitzen bewegen sich ±1,5 cm (etwa ±10°).'],
        ['Fahrtwind drückt Haare und Ohren nach hinten (grüner Pfeil).', 'Jeder Schritt gibt ihnen einen Stoß.'],
        'weiß = Ohrspitzen und Haarmasse, gelb = Enden der langen Strähnen, cyan = ihre Spur relativ zum Kopf über einen Zyklus')


slide1()
slide2()
slide3()
slide4()
slide5()
slide6()
slide7('top')
slide7('side')
slide8()


# ------------------------------------------------------------------ interpolation + cycle modifiers on every overlay object
def fcurves_of(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
        return out


for ob in COLL_ALL:
    ad = ob.animation_data
    if ad is None or ad.action is None:
        continue
    for fc in fcurves_of(ad.action):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT' if fc.data_path == 'color' else 'LINEAR'
        fc.modifiers.new('CYCLES')

# ------------------------------------------------------------------ scene settings, a darker floor (copy only) and the first slide
fm = bpy.data.materials.get('floor')
if fm is not None and fm.node_tree is not None:
    for nd in fm.node_tree.nodes:
        if nd.type == 'TEX_CHECKER':
            nd.inputs['Color1'].default_value = (0.115, 0.125, 0.155, 1.0)
            nd.inputs['Color2'].default_value = (0.065, 0.072, 0.092, 1.0)
world = bpy.data.worlds.new('KritikWelt')
world.use_nodes = True
next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND').inputs['Color'].default_value = (0.045, 0.047, 0.055, 1.0)
scene.world = world
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 1600, 900
scene.render.fps, scene.render.fps_base = 60, 1.0
scene.view_settings.view_transform = 'Standard'
scene['kritik'] = json.dumps(SLIDES)
lc = bpy.context.view_layer.layer_collection
for i, sd in enumerate(SLIDES):
    lc.children[sd['name']].hide_viewport = (i != 0)
    bpy.data.collections[sd['name']].hide_render = (i != 0)
scene.camera = bpy.data.objects[SLIDES[0]['camera']]
scene.frame_set(0)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
print('KRITIK saved', OUT, 'slides', len(SLIDES), 'overlay objects', len(COLL_ALL))
