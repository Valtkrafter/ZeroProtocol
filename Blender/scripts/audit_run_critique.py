"""READ-ONLY (the blend is opened in background and never saved): measures the eight points of the user's critique on Blender/Yoru_Run.blend (stage 1 build).
Everything is printed with the prefix AUDIT.  Frames 0..35 = one gait cycle (36 frames at 60 fps = 0.6 s)."""
import bpy, math, re
from mathutils import Vector, Quaternion

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
scene = bpy.context.scene
B = arm.data.bones
NF = 36
R = {b.name: b.matrix_local.to_quaternion() for b in B}


def has(n):
    return n in B


# ------------------------------------------------------------------ sample the whole cycle once
PB = {}          # name -> list of (head, tail, matrix)
for f in range(NF):
    scene.frame_set(f)
    ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    for pb in ae.pose.bones:
        PB.setdefault(pb.name, []).append((pb.head.copy(), pb.tail.copy(), pb.matrix.copy()))


def P(n, i):
    return PB[n][i % NF][0]


def T(n, i):
    return PB[n][i % NF][1]


def M(n, i):
    return PB[n][i % NF][2]


def stats(label, vals, unit=''):
    mn, mx = min(vals), max(vals)
    print('AUDIT %-62s min %8.2f max %8.2f mean %8.2f p-p %7.2f %s' % (label, mn, mx, sum(vals) / len(vals), mx - mn, unit))


def eul_deg(q):
    e = q.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def qangle(q1, q2):
    d = min(1.0, abs(q1.dot(q2)))
    return math.degrees(2.0 * math.acos(d))


def rotvec(q_from, q_to):
    """world rotation vector (degrees) that turns q_from into q_to"""
    d = q_to @ q_from.inverted()
    if d.w < 0:
        d = Quaternion((-d.w, -d.x, -d.y, -d.z))
    ang = 2.0 * math.acos(min(1.0, d.w))
    s = math.sqrt(max(0.0, 1.0 - d.w * d.w))
    if s < 1e-9:
        return Vector((0, 0, 0))
    return Vector((d.x / s, d.y / s, d.z / s)) * math.degrees(ang)


# ------------------------------------------------------------------ chin of the face mesh (rest pose) carried by the head bone
HEAD = 'J_Bip_C_Head'
chin_rest = None
chin_src = ''
cands = [o for o in bpy.data.objects if o.type == 'MESH' and o.vertex_groups.get(HEAD) is not None]
print('AUDIT meshes with head weights:', [o.name for o in cands])
face_objs = [o for o in cands if 'face' in o.name.lower() and not any(k in o.name.lower() for k in ('eye', 'brow', 'lash', 'mouth', 'tooth', 'iris', 'high', 'white', 'hair'))]
for ob in (face_objs or cands):
    vg = ob.vertex_groups[HEAD]
    hx = B[HEAD].head_local
    for v in ob.data.vertices:
        w = 0.0
        for g in v.groups:
            if g.group == vg.index:
                w = g.weight
        if w < 0.5:
            continue
        p = ob.matrix_world @ v.co
        if abs(p.x) > 0.045 or p.y < hx.y + 0.02:
            continue
        if chin_rest is None or p.z < chin_rest.z:
            chin_rest = p.copy()
            chin_src = ob.name
print('AUDIT chin rest point %s from "%s"; head bone origin %s' % (tuple(round(c, 3) for c in chin_rest), chin_src, tuple(round(c, 3) for c in B[HEAD].head_local)))


def chin(i):
    return M(HEAD, i) @ (B[HEAD].matrix_local.inverted() @ chin_rest)


# ------------------------------------------------------------------ 1+2: ARMS
print('AUDIT ===== ARMS: fist height, forearm direction, elbow, abduction =====')
for side, sn in (('R', 'right'), ('L', 'left')):
    ua, la, ha = 'J_Bip_%s_UpperArm' % side, 'J_Bip_%s_LowerArm' % side, 'J_Bip_%s_Hand' % side
    mid = 'J_Bip_%s_Middle1' % side
    knuckle = [P(mid, i) if has(mid) else (P(ha, i) + T(ha, i)) * 0.5 for i in range(NF)]
    up_pitch, el_flex, fa_dir, fist_vs_chin, fist_vs_sh, wrist_vs_sh, abd, conv, elb_x, hand_x = [], [], [], [], [], [], [], [], [], []
    for i in range(NF):
        sh, el, wr = P(ua, i), P(la, i), P(ha, i)
        u, fo = el - sh, wr - el
        up_pitch.append(math.degrees(math.atan2(u.y, -u.z)))
        el_flex.append(180.0 - math.degrees(math.acos(max(-1, min(1, (-u).normalized().dot(fo.normalized()))))))
        fa_dir.append(math.degrees(math.atan2(fo.z, fo.y)))                       # 0 = horizontal forward, +90 up, -90 down, +-180 backward
        c = chin(i)
        fist_vs_chin.append(1000.0 * (knuckle[i].z - c.z))
        fist_vs_sh.append(1000.0 * (knuckle[i].z - sh.z))
        wrist_vs_sh.append(1000.0 * (wr.z - sh.z))
        sgn = 1.0 if sh.x > 0 else -1.0
        abd.append(math.degrees(math.asin(max(-1, min(1, sgn * u.x / u.length)))))      # + = elbow outward from the shoulder
        conv.append(math.degrees(math.asin(max(-1, min(1, -sgn * fo.x / fo.length)))))  # + = forearm points inward (towards the centre line)
        elb_x.append(1000.0 * sgn * el.x)
        hand_x.append(1000.0 * sgn * wr.x)
    print('AUDIT --- %s arm' % sn)
    stats('upper arm pitch (+ forward)', up_pitch, 'deg')
    stats('elbow flexion', el_flex, 'deg')
    stats('forearm direction (0 horizontal fwd, +90 up, -90 down, 180 back)', fa_dir, 'deg')
    stats('fist (knuckle) height above the CHIN', fist_vs_chin, 'mm')
    stats('fist (knuckle) height above the shoulder joint', fist_vs_sh, 'mm')
    stats('wrist height above the shoulder joint', wrist_vs_sh, 'mm')
    stats('upper arm abduction (+ elbow outward from the shoulder)', abd, 'deg')
    stats('forearm convergence (+ pointing to the centre line)', conv, 'deg')
    stats('elbow lateral position (from the centre line)', elb_x, 'mm')
    stats('wrist lateral position (from the centre line)', hand_x, 'mm')
    near_h = sum(1 for d in fa_dir if abs(d) < 25 or abs(abs(d) - 180) < 25)
    print('AUDIT %s forearm within +-25 deg of horizontal in %d of %d frames (%.0f %%)' % (sn, near_h, NF, 100.0 * near_h / NF))
    i_f, i_b = up_pitch.index(max(up_pitch)), up_pitch.index(min(up_pitch))
    print('AUDIT %s arm furthest FORWARD at frame %d: upper arm %+.1f, elbow %.1f, forearm dir %+.1f, fist %+.0f mm vs chin, %+.0f mm vs shoulder' % (
        sn, i_f, up_pitch[i_f], el_flex[i_f], fa_dir[i_f], fist_vs_chin[i_f], fist_vs_sh[i_f]))
    print('AUDIT %s arm furthest BACK    at frame %d: upper arm %+.1f, elbow %.1f, forearm dir %+.1f, fist %+.0f mm vs chin, %+.0f mm vs shoulder' % (
        sn, i_b, up_pitch[i_b], el_flex[i_b], fa_dir[i_b], fist_vs_chin[i_b], fist_vs_sh[i_b]))
    if side == 'R':
        print('AUDIT right arm frame table: frame | upper arm pitch | elbow flex | forearm dir | fist vs chin mm | elbow x mm | wrist x mm')
        for i in range(NF):
            print('AUDIT RA %2d | %+6.1f | %6.1f | %+7.1f | %+6.0f | %5.0f | %5.0f' % (i, up_pitch[i], el_flex[i], fa_dir[i], fist_vs_chin[i], elb_x[i], hand_x[i]))
# shoulder width in the front view
sw_rest = 2000.0 * abs(B['J_Bip_R_UpperArm'].head_local.x)
print('AUDIT shoulder joint distance in rest %.0f mm' % sw_rest)
for side in ('R', 'L'):
    n = 'J_Bip_%s_Shoulder' % side
    es = [eul_deg(M(n, i).to_quaternion() @ R[n].inverted()) for i in range(NF)]
    stats('%s shoulder (clavicle) bone world pitch (X)' % side, [e[0] for e in es], 'deg')
    stats('%s shoulder (clavicle) bone world yaw (Z)' % side, [e[2] for e in es], 'deg')
    stats('%s shoulder (clavicle) bone world roll (Y)' % side, [e[1] for e in es], 'deg')
    uc = 'J_Bip_C_UpperChest' if has('J_Bip_C_UpperChest') else 'J_Bip_C_Chest'
    rest_l = B[uc].matrix_local.inverted() @ B['J_Bip_%s_UpperArm' % side].head_local
    dl = [(M(uc, i).inverted() @ P('J_Bip_%s_UpperArm' % side, i)) - rest_l for i in range(NF)]
    stats('%s shoulder joint vs rest in the chest frame: lateral' % side, [1000 * v.x for v in dl], 'mm')
    stats('%s shoulder joint vs rest in the chest frame: vertical (local Y)' % side, [1000 * v.y for v in dl], 'mm')
    stats('%s shoulder joint vs rest in the chest frame: fore-aft (local Z)' % side, [1000 * v.z for v in dl], 'mm')

# ------------------------------------------------------------------ 3+4: LEGS
print('AUDIT ===== LEGS =====')
for side in ('R',):
    hip, knee, ank, toe = ['J_Bip_%s_%s' % (side, s) for s in ('UpperLeg', 'LowerLeg', 'Foot', 'ToeBase')]
    thigh, kfl, kneeh, ay, shank_ang = [], [], [], [], []
    for i in range(NF):
        h, k, a = P(hip, i), P(knee, i), P(ank, i)
        th = k - h
        thigh.append(math.degrees(math.atan2(th.y, -th.z)))
        sh = k - a
        shank_ang.append(math.degrees(math.atan2(sh.y, sh.z)))
        kfl.append(180.0 - math.degrees(math.acos(max(-1, min(1, (h - k).normalized().dot((a - k).normalized()))))))
        kneeh.append(1000.0 * (k.z - h.z))
        ay.append(1000.0 * (a.y - h.y))
    stats('thigh pitch (+ knee forward)', thigh, 'deg')
    stats('knee flexion', kfl, 'deg')
    stats('knee height relative to the hip joint (negative = below)', kneeh, 'mm')
    stats('ankle fore-aft position relative to the hip joint', ay, 'mm')
    fw = max(thigh)
    bk = -min(thigh)
    print('AUDIT thigh excursion front %.1f deg, back %.1f deg -> %.0f %% of the swing of the thigh is in FRONT of the vertical' % (fw, bk, 100.0 * fw / (fw + bk)))
    st = [abs(kfl[(i + 1) % NF] - kfl[i]) for i in range(NF)]
    st2 = [abs((kfl[(i + 1) % NF] - kfl[i]) - (kfl[i] - kfl[i - 1])) for i in range(NF)]
    print('AUDIT knee flexion: max step %.1f deg/frame (at frame %d), max change of the step %.1f deg/frame (at frame %d)' % (max(st), st.index(max(st)), max(st2), st2.index(max(st2))))
    sst = [abs(shank_ang[(i + 1) % NF] - shank_ang[i]) for i in range(NF)]
    print('AUDIT shank angle: max step %.1f deg/frame at frame %d' % (max(sst), sst.index(max(sst))))
    print('AUDIT right leg table: frame | thigh | knee flex | knee step | shank angle')
    for i in range(NF):
        print('AUDIT RL %2d | %+6.1f | %6.1f | %+6.1f | %+6.1f' % (i, thigh[i], kfl[i], kfl[(i + 1) % NF] - kfl[i], shank_ang[i]))

# ------------------------------------------------------------------ per-bone world rotation steps (all bones) and their change
print('AUDIT ===== BONE JUMPS (world rotation, degrees per frame at 60 fps) =====')
hum = [n for n in PB if n.startswith('J_Bip_')]
sec = [n for n in PB if not n.startswith('J_Bip_')]
rows = []
for n in PB:
    qs = [M(n, i).to_quaternion() for i in range(NF)]
    steps = [qangle(qs[i], qs[(i + 1) % NF]) for i in range(NF)]
    rv = [rotvec(qs[i], qs[(i + 1) % NF]) for i in range(NF)]
    chg = [(rv[i] - rv[i - 1]).length for i in range(NF)]
    rows.append((n, max(steps), steps.index(max(steps)), max(chg), chg.index(max(chg))))
for label, group in (('HUMANOID', hum), ('SECONDARY (hair, tail, ears, bust)', sec)):
    sub = [r for r in rows if r[0] in group]
    print('AUDIT %s: bones with a step > 8 deg/frame: %d of %d; with a velocity change > 6 deg/frame: %d' % (
        label, sum(1 for r in sub if r[1] > 8.0), len(sub), sum(1 for r in sub if r[3] > 6.0)))
    for r in sorted(sub, key=lambda r: -r[1])[:8]:
        print('AUDIT   top step      %-26s step %5.1f deg/frame at frame %2d | velocity change %5.1f at frame %2d' % (r[0], r[1], r[2], r[3], r[4]))
    for r in sorted(sub, key=lambda r: -r[3])[:6]:
        print('AUDIT   top vel.change %-26s step %5.1f deg/frame at frame %2d | velocity change %5.1f at frame %2d' % (r[0], r[1], r[2], r[3], r[4]))

# ------------------------------------------------------------------ 5: TORSO (how much the spine really moves)
print('AUDIT ===== TORSO: bend of every spine joint against its parent (rest corrected), degrees =====')
chain = ['J_Bip_C_Hips', 'J_Bip_C_Spine', 'J_Bip_C_Chest', 'J_Bip_C_UpperChest', 'J_Bip_C_Neck', 'J_Bip_C_Head']
chain = [n for n in chain if has(n)]
for a, b in zip(chain, chain[1:]):
    rel_rest = R[a].inverted() @ R[b]
    es = []
    for i in range(NF):
        rel = M(a, i).to_quaternion().inverted() @ M(b, i).to_quaternion()
        es.append(eul_deg(rel_rest.inverted() @ rel))
    stats('%s -> %s bend pitch (X, negative = forward)' % (a[6:], b[6:]), [e[0] for e in es], 'deg')
    stats('%s -> %s bend yaw (local Y = twist about the spine)' % (a[6:], b[6:]), [e[1] for e in es], 'deg')
    stats('%s -> %s bend roll (local Z, side bend)' % (a[6:], b[6:]), [e[2] for e in es], 'deg')
tot = [eul_deg(M('J_Bip_C_UpperChest' if has('J_Bip_C_UpperChest') else 'J_Bip_C_Chest', i).to_quaternion() @ R['J_Bip_C_UpperChest' if has('J_Bip_C_UpperChest') else 'J_Bip_C_Chest'].inverted()) for i in range(NF)]
stats('UpperChest total world pitch (lean)', [e[0] for e in tot], 'deg')
stats('UpperChest total world yaw', [e[2] for e in tot], 'deg')
hz = [1000.0 * P('J_Bip_C_Hips', i).z for i in range(NF)]
stats('hips height', hz, 'mm')
hd = [1000.0 * P('J_Bip_C_Head', i).z for i in range(NF)]
stats('head bone height', hd, 'mm')

# ------------------------------------------------------------------ 7: TAIL
print('AUDIT ===== TAIL =====')
tn = ['J_Opt_C_CatTail%d_01' % j for j in range(1, 9)]
tn = [n for n in tn if has(n)]
tip = tn[-1]
tipx = [1000.0 * (P(tip, i).x) for i in range(NF)]
tipz = [1000.0 * (P(tip, i).z - P('J_Bip_C_Hips', i).z) for i in range(NF)]
tipy = [1000.0 * (P(tip, i).y - P('J_Bip_C_Hips', i).y) for i in range(NF)]
stats('tail tip sideways (x, top view)', tipx, 'mm')
stats('tail tip height relative to the hips', tipz, 'mm')
stats('tail tip behind the hips (y)', tipy, 'mm')
for j in range(len(tn) - 1):
    n, n2 = tn[j], tn[j + 1]
    ab, lat = [], []
    for i in range(NF):
        d = P(n2, i) - P(n, i)
        ab.append(math.degrees(math.atan2(d.z, -d.y)))
        lat.append(math.degrees(math.atan2(d.x, -d.y)))
    stats('tail segment %d direction above horizontal (+ = up)' % (j + 1), ab, 'deg')
    stats('tail segment %d sideways angle (top view)' % (j + 1), lat, 'deg')

# ------------------------------------------------------------------ 8: HAIR, EARS, BUST (secondary motion)
print('AUDIT ===== HAIR / EARS / BUST: motion of the tips in the head frame (hair, ears) or chest frame (bust) =====')
chains = {}
for n in PB:
    if n.startswith('J_Sec_Hair') or 'CatEar' in n or 'Bust' in n:
        key = re.sub(r'(\d+)_(\d+)$', r'\1', n) if n.startswith('J_Sec_Hair') else re.sub(r'\d+(_\d+)?$', '', n)
        chains.setdefault(key, []).append(n)
frame_of = {'hair': 'J_Bip_C_Head', 'ear': 'J_Bip_C_Head', 'bust': 'J_Bip_C_UpperChest' if has('J_Bip_C_UpperChest') else 'J_Bip_C_Chest'}
summary = []
for key, names in sorted(chains.items()):
    names = sorted(names)
    last = names[-1]
    kind = 'bust' if 'Bust' in key else ('ear' if 'CatEar' in key else 'hair')
    fr = frame_of[kind]
    pts = [M(fr, i).inverted() @ T(last, i) for i in range(NF)]
    c = sum(pts, Vector()) / NF
    rest_pt = B[fr].matrix_local.inverted() @ B[last].tail_local
    ext = max((p - c).length for p in pts) * 1000.0
    px = [1000 * p.x for p in pts]
    py = [1000 * p.y for p in pts]
    pz = [1000 * p.z for p in pts]
    offs = (c - rest_pt).length * 1000.0
    ln = (B[last].tail_local - B[names[0]].head_local).length * 1000.0
    summary.append((kind, key, len(names), ln, ext, max(px) - min(px), max(py) - min(py), max(pz) - min(pz), offs))
for kind in ('hair', 'ear', 'bust'):
    print('AUDIT %s chains: name | bones | chain length mm | max distance from the mean tip position mm | p-p x | p-p y | p-p z | mean offset from the rest tip mm' % kind)
    for s in [s for s in summary if s[0] == kind]:
        print('AUDIT   %-26s %2d | %5.0f | %5.1f | %5.1f | %5.1f | %5.1f | %5.1f' % s[1:])
    sub = [s for s in summary if s[0] == kind]
    if sub:
        print('AUDIT %s: mean of the max distance %.1f mm, largest %.1f mm' % (kind, sum(s[4] for s in sub) / len(sub), max(s[4] for s in sub)))
print('AUDIT done')
