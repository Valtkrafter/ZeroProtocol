"""
Yoru - AIM SUITE STAGE 2 (2026-10-31): shared code of build_aim_s2.py and build_aim_s2_check.py (imported, never run on its own).
Rig tables, FK, the arm parametrisation that animates the arms, and the measurements.  The measurements use the same definitions as the
main agent's aim_transition_scan.py: gear polygons of aim_measure.py (vest, torso, thighs, skirt pieces; no hair; alpha-cut polygons dropped),
split ONCE in the pose Yoru_Aim_Pose_V2_full at the belt line z = 1.00 m into LOW (polygon centroid below) and UP; forearm + hand, the elbow end of
the upper arm (t > 0.8 along shoulder -> elbow) and the pistol surface samples against them; forearm / wrist roll against a pure elbow hinge.
Blender: +Y forward (the aim line), her right = +X, up = +Z; the armature and body world matrices are identity.

ARM PARAMETERS (per side s, sx = +1 right / -1 left; angles in degrees):
  beta   the upper arm pitched forward about the lateral axis (0 = hanging, 90 = horizontal forward, < 0 = behind the body)
  gamma  the upper arm tilted outward in the frontal plane before the pitch          ua = Rx(beta) Ry(-sx*gamma) (0, 0, -1)
  tau    turn of the elbow's bend plane about the upper arm (0 = the forearm bends forward / up in the arm's pitch plane, + = elbow outward)
  flex   elbow flexion (0 = straight)                                                fo = ua*cos(flex) + b*sin(flex),  b = Rx Ry Rz(sx*tau) (0, 1, 0)
  tw_u   extra twist of the upper arm about its own axis against the hinge frame (0 in V2)
  tw_e   forearm roll about its own axis against the hinge frame (the S1 / scan definition 'froll', limit 18)
  qh     the hand's local quaternion (the wrist joint), used directly
The elbow joint is K = S + ua*L1, the wrist W = K + fo*L2 (S = shoulder joint from the body FK).
"""
import bpy, math, json, os, sys, time
import numpy as np
from mathutils import Vector, Quaternion, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_point_line

ROOT = r'C:\Users\valen\ZeroProtocol\Blender'
IDLE_BLEND = os.path.join(ROOT, 'Yoru_Idle_v2.blend')
SPRINT_BLEND = os.path.join(ROOT, 'Yoru_Sprint.blend')
AIM_BLEND = os.path.join(ROOT, 'Yoru_Aim.blend')
WORK = os.path.join(ROOT, 'work', 'Aim', 'Yoru_Aim_s2.blend')
PROGRESS = os.path.join(ROOT, 'work', 'Aim', 'Yoru_Aim_s2_progress.md')
SPRINT_ACT = 'Yoru_Sprint_r6_L12'
BELT = 1.00
FPS = 60
T0 = time.time()


def log(*a):
    print('[aim_s2 %6.1fs]' % (time.time() - T0), *a, flush=True)


def progress(line):
    os.makedirs(os.path.dirname(PROGRESS), exist_ok=True)
    new = not os.path.exists(PROGRESS)
    with open(PROGRESS, 'a', encoding='utf-8') as f:
        if new:
            f.write('# Yoru Aim Stufe 2, Runde 1: Fortschritt (eine Zeile je fertigem Schritt)\n\n')
        f.write('- %s %s\n' % (time.strftime('%H:%M'), line))


def deg(x):
    return math.radians(x)


def qang(a, b):
    x = a.rotation_difference(b).angle
    return math.degrees(min(x, 2.0 * math.pi - x))


def fcurves_of(act):
    return [fc for l in act.layers for s in l.strips for cb in s.channelbags for fc in cb.fcurves]


def channelbags_of(act):
    return [cb for l in act.layers for s in l.strips for cb in s.channelbags]


def bone_of(dp):
    return dp.split('"')[1] if dp.startswith('pose.bones["') else None


def frame_rot(dir_v, nrm_v):
    d = Vector(dir_v).normalized()
    n = Vector(nrm_v)
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed().to_quaternion()


def aim(rest_dir, rest_nrm, tgt_dir, tgt_nrm):
    return frame_rot(tgt_dir, tgt_nrm) @ frame_rot(rest_dir, rest_nrm).inverted()


def signed_about(q, axis):
    ax, an = q.to_axis_angle()
    a = math.degrees(an) * (1.0 if ax.dot(axis) >= 0 else -1.0)
    return (a + 180.0) % 360.0 - 180.0


def ang(a, b):
    a, b = a.normalized(), b.normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))


# ------------------------------------------------------------------ smooth profiles
def smooth(t):
    """C2 ease (minimum jerk) 0..1"""
    t = min(max(t, 0.0), 1.0)
    return t * t * t * (10.0 - 15.0 * t + 6.0 * t * t)


def cubic_ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def pchip(xs, ys):
    """monotone cubic (Fritsch-Carlson) through (xs, ys); returns f(x).  Zero slope at the ends."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


def hermite(xs, ys, slopes=None):
    """C1 cubic Hermite through (xs, ys); slopes = per key (None = Catmull-Rom style, ends 0)"""
    n = len(xs)
    if slopes is None:
        slopes = [0.0] * n
        for i in range(1, n - 1):
            slopes[i] = (ys[i + 1] - ys[i - 1]) / (xs[i + 1] - xs[i - 1])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        hh = xs[i + 1] - xs[i]
        t = (x - xs[i]) / hh
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * hh * slopes[i] + h01 * ys[i + 1] + h11 * hh * slopes[i + 1]
    return f


def qlerp(a, b, w):
    b = b.copy()
    if a.dot(b) < 0:
        b = -b
    return a.slerp(b, w)


# ------------------------------------------------------------------ the rig
class Rig:
    def __init__(self):
        self.scene = bpy.context.scene
        self.arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        self.body = bpy.data.objects['Body']
        self.face = bpy.data.objects.get('Face')
        self.hair = bpy.data.objects.get('Hair')
        self.bones = self.arm.data.bones
        self.PB = self.arm.pose.bones
        self.R = {b.name: b.matrix_local.to_quaternion() for b in self.bones}
        self.HEAD0 = {b.name: b.head_local.copy() for b in self.bones}
        self.PARENT = {b.name: (b.parent.name if b.parent else None) for b in self.bones}
        order, q = [], [b for b in self.bones if b.parent is None]
        while q:
            b = q.pop(0)
            order.append(b.name)
            q.extend(b.children)
        self.ORDER = order
        self.ARM3 = {s: ['J_Bip_%s_%s' % (s, p) for p in ('UpperArm', 'LowerArm', 'Hand')] for s in 'LR'}
        self.FINGERS = {s: ['J_Bip_%s_%s%d' % (s, f, k) for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Little') for k in (1, 2, 3)
                            if 'J_Bip_%s_%s%d' % (s, f, k) in self.bones] for s in 'LR'}
        self.ARM_BONES = set(self.ARM3['L'] + self.ARM3['R'] + self.FINGERS['L'] + self.FINGERS['R'])
        self.CLAV = {s: 'J_Bip_%s_Shoulder' % s for s in 'LR'}
        self.L1 = {s: (self.HEAD0[self.ARM3[s][1]] - self.HEAD0[self.ARM3[s][0]]).length for s in 'LR'}
        self.L2 = {s: (self.HEAD0[self.ARM3[s][2]] - self.HEAD0[self.ARM3[s][1]]).length for s in 'LR'}
        self.REST_UA = {s: (self.HEAD0[self.ARM3[s][1]] - self.HEAD0[self.ARM3[s][0]]).normalized() for s in 'LR'}
        self.REST_FA = {s: (self.HEAD0[self.ARM3[s][2]] - self.HEAD0[self.ARM3[s][1]]).normalized() for s in 'LR'}
        self.REST_N = Vector((0.0, 0.0, -1.0))
        self.SX = {'L': -1.0, 'R': 1.0}
        self.PIST = {('L' if o.name.endswith('_L') else 'R'): o for o in bpy.data.objects if o.name.startswith('PLATZHALTER_Pistole')}
        self.MUZ_LOCAL = {}
        for s, o in self.PIST.items():
            vs = o.data.vertices
            ymax = max(v.co.y for v in vs)
            front = [v.co.copy() for v in vs if v.co.y > ymax - 1e-4]
            self.MUZ_LOCAL[s] = sum(front, Vector()) / len(front)
        # pistol placement in the hand bone's frame (for pure-python FK of the pistol)
        self.PIST_IN_HAND = {}
        for s, o in self.PIST.items():
            self.PIST_IN_HAND[s] = None

    # ---------------------------------------------------------- FK (S1 / round 5 with the parent-aware hips location)
    def fk(self, qget, locget, names=None):
        D, P = {}, {}
        for n in (names or self.ORDER):
            p = self.PARENT[n]
            Dp = D[p] if p else Quaternion()
            P[n] = self.HEAD0[n].copy() if p is None else P[p] + D[p] @ (self.HEAD0[n] - self.HEAD0[p])
            loc = locget(n)
            if loc is not None:
                P[n] = P[n] + Dp @ (self.R[n] @ loc)
            D[n] = Dp @ (self.R[n] @ qget(n) @ self.R[n].inverted())
        return D, P

    def chain(self, n):
        c = []
        while n is not None:
            c.append(n)
            n = self.PARENT[n]
        return c[::-1]

    # ---------------------------------------------------------- arm parametrisation
    def arm_vectors(self, s, beta, gamma, tau, flex):
        sx = self.SX[s]
        M = Matrix.Rotation(deg(beta), 3, 'X') @ Matrix.Rotation(deg(-sx * gamma), 3, 'Y') @ Matrix.Rotation(deg(sx * tau), 3, 'Z')
        ua = (M @ Vector((0.0, 0.0, -1.0))).normalized()
        b = (M @ Vector((0.0, 1.0, 0.0))).normalized()
        fo = (ua * math.cos(deg(flex)) + b * math.sin(deg(flex))).normalized()
        return ua, fo, b

    def arm_world(self, s, p):
        """p = dict(beta, gamma, tau, flex, tw_u, tw_e) -> Du, Df (world rotation deltas), ua, fo"""
        sx = self.SX[s]
        ua, fo, b = self.arm_vectors(s, p['beta'], p['gamma'], p['tau'], p['flex'])
        cr = ua.cross(fo)
        if cr.length < 1e-9:
            cr = ua.cross(b)
        n = cr.normalized() * (-sx)
        Du = Quaternion(ua, deg(p['tw_u'])) @ aim(self.REST_UA[s], self.REST_N, ua, n)
        Df = Quaternion(fo, deg(p['tw_e'])) @ aim(self.REST_FA[s], self.REST_N, fo, n)
        return Du, Df, ua, fo

    def arm_local(self, s, p, Dp):
        """local quaternions (upper arm, forearm) for the parameters p under the parent (clavicle) world rotation Dp"""
        up, lo, ha = self.ARM3[s]
        Du, Df, ua, fo = self.arm_world(s, p)
        q_ua = self.R[up].inverted() @ Dp.inverted() @ Du @ self.R[up]
        q_fa = self.R[lo].inverted() @ Du.inverted() @ Df @ self.R[lo]
        return q_ua, q_fa, Du, Df

    def decompose(self, s, D, P, qh):
        """arm parameters of a solved pose (D, P from fk); qh = the hand's local quaternion"""
        sx = self.SX[s]
        up, lo, ha = self.ARM3[s]
        S, K, W = P[up], P[lo], P[ha]
        ua, fo = (K - S).normalized(), (W - K).normalized()
        gamma = math.degrees(math.asin(max(-1.0, min(1.0, sx * ua.x))))
        beta = math.degrees(math.atan2(ua.y, -ua.z))
        flex = ang(ua, fo)
        b = (fo - ua * math.cos(deg(flex))).normalized()
        Minv = (Matrix.Rotation(deg(beta), 3, 'X') @ Matrix.Rotation(deg(-sx * gamma), 3, 'Y')).inverted()
        bp = Minv @ b
        tau = math.degrees(math.atan2(-sx * bp.x, bp.y))
        n = ua.cross(fo).normalized() * (-sx)
        Du0 = aim(self.REST_UA[s], self.REST_N, ua, n)
        Df0 = aim(self.REST_FA[s], self.REST_N, fo, n)
        tw_u = signed_about(D[up] @ Du0.inverted(), ua)
        tw_e = signed_about(D[lo] @ Df0.inverted(), fo)
        return dict(beta=beta, gamma=gamma, tau=tau, flex=flex, tw_u=tw_u, tw_e=tw_e, qh=qh.copy())


# ------------------------------------------------------------------ actions: read keys
def read_action(act, frames):
    """per frame: {bone: local quaternion}, hips location (or None)"""
    FC = {(fc.data_path, fc.array_index): fc for fc in fcurves_of(act)}
    bones = sorted({bone_of(dp) for dp, _ in FC if bone_of(dp)})
    out = []
    for f in frames:
        q = {}
        for n in bones:
            dp = 'pose.bones["%s"].rotation_quaternion' % n
            if (dp, 0) in FC:
                q[n] = Quaternion([FC[(dp, i)].evaluate(f) for i in range(4)]).normalized()
        dpl = 'pose.bones["J_Bip_C_Hips"].location'
        loc = Vector([FC[(dpl, i)].evaluate(f) for i in range(3)]) if (dpl, 0) in FC else None
        out.append((q, loc))
    return out, bones


def append_action(path, name):
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.actions = [name]
    return dst.actions[0]


# ------------------------------------------------------------------ measurement (same definitions as aim_transition_scan.py)
class Meter:
    def __init__(self, rig, zone_action='Yoru_Aim_Pose_V2_full'):
        self.rig = rig
        body = rig.body
        me = body.data
        imgs = {}
        for mi, m in enumerate(me.materials):
            if m is None or not m.node_tree:
                continue
            for n_ in m.node_tree.nodes:
                if n_.type == 'TEX_IMAGE' and n_.image:
                    w_, h_ = n_.image.size
                    imgs[mi] = (np.array(n_.image.pixels[:], dtype=np.float32).reshape(h_, w_, 4)[:, :, 3], w_, h_)
                    break
        uv = me.uv_layers.active.data
        inv = set()
        for poly in me.polygons:
            im = imgs.get(poly.material_index)
            if im is None:
                continue
            px, w_, h_ = im
            a_ = sum(px[int(min(max(uv[li].uv[1], 0.0), 0.9999) * h_), int(min(max(uv[li].uv[0], 0.0), 0.9999) * w_)] for li in poly.loop_indices)
            if a_ / len(poly.loop_indices) < 0.3:
                inv.add(poly.index)
        self.INV = inv
        vgn = {vg.index: vg.name for vg in body.vertex_groups}
        dom = [vgn.get(max(v.groups, key=lambda g: g.weight).group, '') if v.groups else '' for v in me.vertices]
        self.DOM = dom
        VIS = [False] * len(me.vertices)
        for p in me.polygons:
            if p.index not in inv:
                for v_ in p.vertices:
                    VIS[v_] = True
        SOLID = {'J_Bip_C_Hips', 'J_Bip_C_Spine', 'J_Bip_C_Chest', 'J_Bip_C_UpperChest', 'J_Bip_L_UpperLeg', 'J_Bip_R_UpperLeg',
                 'J_Bip_L_LowerLeg', 'J_Bip_R_LowerLeg'}
        self.GEAR = [list(p.vertices) for p in me.polygons
                     if p.index not in inv and all(VIS[v_] and (dom[v_] in SOLID or (dom[v_].startswith('J_Sec_') and 'Hair' not in dom[v_])) for v_ in p.vertices)]
        self.ALLVIS = [list(p.vertices) for p in me.polygons if p.index not in inv]
        self.ARM_PARTS = {}
        for s in 'LR':
            hand_set = {'J_Bip_%s_Hand' % s} | {'J_Bip_%s_%s%s' % (s, f_, p_) for f_ in ('Index', 'Middle', 'Ring', 'Little', 'Thumb')
                                                for p_ in ('Proximal', 'Intermediate', 'Distal')}
            for part, bset in (('UpperArm', {'J_Bip_%s_UpperArm' % s}), ('LowerArm', {'J_Bip_%s_LowerArm' % s}), ('Hand', hand_set)):
                self.ARM_PARTS[(s, part)] = [list(p.vertices) for p in me.polygons if p.index not in inv and all(dom[v_] in bset and VIS[v_] for v_ in p.vertices)]
        self.NV = len(me.vertices)
        # zones, fixed once in the zone pose (frame 0 of the action, no NLA)
        ad = rig.arm.animation_data
        keep = (ad.action, getattr(ad, 'action_slot', None), ad.use_nla)
        ad.use_nla = False
        set_action(rig.arm, bpy.data.actions[zone_action])
        rig.scene.frame_set(1)
        rig.scene.frame_set(0)
        bpy.context.view_layer.update()
        co0 = self.body_coords()
        self.LOW = [pl for pl in self.GEAR if sum(co0[v].z for v in pl) / len(pl) < BELT]
        self.UP = [pl for pl in self.GEAR if sum(co0[v].z for v in pl) / len(pl) >= BELT]
        ad.action = keep[0]
        if keep[0] is not None and keep[1] is not None:
            ad.action_slot = keep[1]
        ad.use_nla = keep[2]
        log('meter: gear %d polygons (low %d, up %d, belt %.2f m), arm parts %s' % (len(self.GEAR), len(self.LOW), len(self.UP), BELT,
                                                                                   {'%s%s' % k: len(v) for k, v in self.ARM_PARTS.items()}))

    def body_coords(self):
        dg = bpy.context.evaluated_depsgraph_get()
        ev = self.rig.body.evaluated_get(dg)
        me = ev.to_mesh()
        arr = np.empty(self.NV * 3, dtype=np.float64)
        me.vertices.foreach_get('co', arr)
        ev.to_mesh_clear()
        return [Vector(c) for c in arr.reshape(self.NV, 3)]

    def pistol_geometry(self, s):
        ob = self.rig.PIST[s]
        mwp = ob.matrix_world
        co = [mwp @ v.co for v in ob.data.vertices]
        polys = [list(p.vertices) for p in ob.data.polygons]
        samples = list(co)
        for p in ob.data.polygons:
            vs = [co[i] for i in p.vertices]
            if len(vs) != 4:
                continue
            for a_ in (0.125, 0.375, 0.625, 0.875):
                for b_ in (0.125, 0.375, 0.625, 0.875):
                    samples.append(vs[0].lerp(vs[1], a_).lerp(vs[3].lerp(vs[2], a_), b_))
        return co, polys, samples

    @staticmethod
    def nearest_min(bvh, pts, where=None):
        if bvh is None:
            return 99.9
        m = 99.9
        for q in pts:
            h = bvh.find_nearest(q, 0.5)
            if h[0] is not None and h[3] < m:
                m = h[3]
                if where is not None:
                    where[:] = [q.copy(), h[0].copy()]
        return m

    def rolls(self, s):
        rig = self.rig
        PB = rig.PB
        sx = rig.SX[s]
        up, lo, ha = rig.ARM3[s]
        ua_j, la_j, hd_j = PB[up].head, PB[lo].head, PB[ha].head
        ua, fo = (la_j - ua_j).normalized(), (hd_j - la_j).normalized()
        cr = ua.cross(fo)
        if cr.length < 1e-6:
            return 0.0, 0.0
        n_ = cr.normalized() * (-sx)
        Df = PB[lo].matrix.to_quaternion() @ rig.R[lo].inverted()
        Dh = PB[ha].matrix.to_quaternion() @ rig.R[ha].inverted()
        Df0 = frame_rot(fo, n_) @ frame_rot(rig.REST_FA[s], rig.REST_N).inverted()
        tw_e = signed_about(Df @ Df0.inverted(), fo)
        hdir = (Dh @ rig.REST_FA[s]).normalized()
        tw = signed_about(Dh @ (fo.rotation_difference(hdir) @ Df0).inverted(), hdir)
        return tw_e, tw - tw_e

    def measure(self, pistol_in_holster=None):
        """the current evaluated pose -> dict of numbers (the scan's columns + extras)"""
        rig = self.rig
        PB = rig.PB
        co = self.body_coords()
        g_all = BVHTree.FromPolygons(co, self.GEAR, all_triangles=False)
        g_low = BVHTree.FromPolygons(co, self.LOW, all_triangles=False)
        g_up = BVHTree.FromPolygons(co, self.UP, all_triangles=False)
        g_vis = BVHTree.FromPolygons(co, self.ALLVIS, all_triangles=False)
        r = {}
        hp = PB['J_Bip_C_Head']
        dq = hp.matrix.to_quaternion() @ hp.bone.matrix_local.to_quaternion().inverted()
        fw = (dq @ Vector((0.0, 1.0, 0.0))).normalized()
        r['head_yaw'] = math.degrees(math.atan2(fw.x, fw.y))
        r['head_pitch'] = math.degrees(math.asin(max(-1.0, min(1.0, fw.z))))
        hips, neck = PB['J_Bip_C_Hips'].head, PB['J_Bip_C_Neck'].head
        r['lean'] = math.degrees(math.atan2((neck - hips).y, (neck - hips).z))
        pg = {s: self.pistol_geometry(s) for s in rig.PIST}
        pbv = {s: BVHTree.FromPolygons(g[0], g[1], all_triangles=False) for s, g in pg.items()}
        abv = {}
        for s in 'RL':
            sx = rig.SX[s]
            up, lo, ha = rig.ARM3[s]
            ua, la, hd = PB[up].head, PB[lo].head, PB[ha].head
            elb = [pl for pl in self.ARM_PARTS[(s, 'UpperArm')] if intersect_point_line(co[pl[0]], ua, la)[1] > 0.8]
            fa = self.ARM_PARTS[(s, 'LowerArm')] + self.ARM_PARTS[(s, 'Hand')]
            fa_pts = [co[v] for v in sorted({v for pl in fa for v in pl})]
            el_pts = [co[v] for v in sorted({v for pl in elb for v in pl})]
            tb = BVHTree.FromPolygons(co, fa + elb, all_triangles=False)
            abv[s] = BVHTree.FromPolygons(co, fa, all_triangles=False)
            ov = tb.overlap(g_all)
            r['cut_' + s] = len(ov)
            if ov:
                cpts = [sum((co[v] for v in self.GEAR[j]), Vector()) / len(self.GEAR[j]) for i, j in ov]
                r['cut_at_' + s] = [round(sum(c[k] for c in cpts) / len(cpts), 3) for k in range(3)]
            for key, bvh, pts in (('arm_low', g_low, fa_pts), ('arm_up', g_up, fa_pts), ('elb_low', g_low, el_pts), ('elb_up', g_up, el_pts)):
                w = []
                r['%s_%s' % (key, s)] = 1000 * self.nearest_min(bvh, pts, w)
                if w:
                    r['%s_at_%s' % (key, s)] = [round(x, 3) for x in w[1]]
            r['elbow_out_' + s] = (la.x - ua.x) * sx * 100
            r['flex_' + s] = 180.0 - ang(ua - la, hd - la)
            fr_, wr_ = self.rolls(s)
            r['froll_' + s], r['wroll_' + s] = fr_, wr_
            po = rig.PIST[s]
            mwp = po.matrix_world
            barrel = (mwp.to_3x3() @ Vector((0, 1, 0))).normalized()
            top = (mwp.to_3x3() @ Vector((0, 0, 1))).normalized()
            muzzle = mwp @ rig.MUZ_LOCAL[s]
            r['muzzle_' + s] = list(muzzle)
            r['grip_' + s] = list(mwp.translation)
            r['wrist_' + s] = list(hd)
            r['elbow_' + s] = list(la)
            r['shoulder_' + s] = list(ua)
            r['barrel_' + s] = list(barrel)
            r['barrel_yaw_' + s] = math.degrees(math.atan2(barrel.x * sx, barrel.y))
            r['barrel_pitch_' + s] = math.degrees(math.asin(max(-1.0, min(1.0, barrel.z))))
            r['wbend_' + s] = ang(hd - la, barrel)
            up_ref = Vector((0, 0, 1)) - barrel * barrel.z
            r['cant_' + s] = math.degrees(math.atan2(barrel.dot(up_ref.normalized().cross(top)), up_ref.normalized().dot(top))) * sx if up_ref.length > 1e-6 else 0.0
            r['pcut_' + s] = len(pbv[s].overlap(g_all))
            r['pis_low_' + s] = 1000 * self.nearest_min(g_low, pg[s][2])
            r['pis_up_' + s] = 1000 * self.nearest_min(g_up, pg[s][2])
            hit = g_all.ray_cast(muzzle, barrel, 1.5)
            r['self_hit_' + s] = 1 if hit[0] is not None else 0
            hit2 = g_vis.ray_cast(muzzle + barrel * 0.002, barrel, 3.0)          # stricter: every visible body polygon (arms, feet, hands) within 3 m
            r['self_hit_any_' + s] = 1 if hit2[0] is not None else 0
            r['self_hit_any_dist_' + s] = hit2[3] if hit2[0] is not None else None
        for s, o in (('L', 'R'), ('R', 'L')):
            n = len(pbv[s].overlap(pbv[o])) + len(pbv[s].overlap(abv[o]))
            r['pother_' + s] = n
        return r


def set_action(arm, act):
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    if act is not None and hasattr(ad, 'action_slot') and len(act.slots):
        ad.action_slot = act.slots[0]


def apply_pose(rig, q, hips_loc):
    """set local rotations (and the hips location) directly on the pose bones, no action"""
    ad = rig.arm.animation_data
    if ad is not None:
        ad.action = None
        ad.use_nla = False
    for n, v in q.items():
        pb = rig.PB[n]
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = v
    if hips_loc is not None:
        rig.PB['J_Bip_C_Hips'].location = hips_loc
    bpy.context.view_layer.update()


def visibility(rig, meter, cam_pos):
    """share of the camera-facing pistol surface that no Body / Face / Hair triangle hides (build_aim_r5.py / build_aim_s1_check.py)"""
    occ_v, occ_p = [], []
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in (rig.body, rig.face, rig.hair):
        if ob is None:
            continue
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(occ_v)
        occ_v += [ob.matrix_world @ v.co for v in me.vertices]
        occ_p += [[base + i for i in p.vertices] for p in me.polygons if not (ob is rig.body and p.index in meter.INV)]
        ev.to_mesh_clear()
    occ = BVHTree.FromPolygons(occ_v, occ_p, all_triangles=False)
    out = {}
    for s in 'LR':
        pco, ppolys, _ = meter.pistol_geometry(s)
        n_all = n_vis = 0
        for fi, pl in enumerate(ppolys):
            vs = [pco[i] for i in pl]
            ctr = sum(vs, Vector()) / 4.0
            bctr = sum(pco[8 * (fi // 6):8 * (fi // 6) + 8], Vector()) / 8.0
            nrm = (vs[1] - vs[0]).cross(vs[2] - vs[0]).normalized()
            if nrm.dot(ctr - bctr) < 0:
                nrm = -nrm
            if nrm.dot(cam_pos - ctr) <= 0:
                continue
            for a_ in (0.2, 0.5, 0.8):
                for b_ in (0.2, 0.5, 0.8):
                    s_ = vs[0].lerp(vs[1], a_).lerp(vs[3].lerp(vs[2], a_), b_)
                    d_ = s_ - cam_pos
                    n_all += 1
                    if occ.ray_cast(cam_pos, d_.normalized(), d_.length - 0.002)[0] is None:
                        n_vis += 1
        out[s] = n_vis / max(n_all, 1)
    return out


def game_cam_pos(feet_mid):
    p = deg(15.0)
    return Vector((feet_mid.x + 0.35, feet_mid.y - 4.4 * math.cos(p), 1.35 + 4.4 * math.sin(p)))
