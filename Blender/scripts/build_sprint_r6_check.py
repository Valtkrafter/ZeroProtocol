"""
Yoru - SPRINT LEAN CORRECTION r6: error checks of the actions in Yoru_Sprint_r6.blend against r5 P2 (saves nothing but the JSON).
  blender -b --factory-startup <Yoru_Sprint_r6.blend> --python build_sprint_r6_check.py -- <gait json> <out json> <ref action> <action> [<action> ...]
Per action (the last key repeats the first one):
  seam_deg            largest rotation difference frame 0 / frame NF of every keyed bone (humanoid and the rest)
  step_humanoid       largest rotation step of a humanoid bone between two frames (deg, armature space) and which bone
  step_other          the same for the non-humanoid bones (hair, bust, ears, tail: preview only)
  toe_slip_mm         planted toe joint (ToeBase head) in the ground frame over the stance (0 .. stance share of each foot), largest drift
  feet_vs_ref_mm      largest distance of the Foot / ToeBase joints to the reference action on the same frame (world, in place)
  hips_vs_ref_mm      the same for the hips joint
  knee_to / knee_sw   knee flexion of the right leg at toe off (stance share) and its swing maximum (deg)
World axes: +Y forward, -X = her left, +Z up.
"""
import bpy, sys, math, json, struct

argv = sys.argv[sys.argv.index('--') + 1:]
GAIT, OUT, REF, ACTS = argv[0], argv[1], argv[2], argv[3:]
GLB = r'C:\Users\valen\ZeroProtocol\Blender\work\Yoru_V2.glb'
scene = bpy.context.scene
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
ad = arm.animation_data
for o in bpy.data.objects:
    if o.type == 'MESH':
        o.hide_viewport = True
with open(GLB, 'rb') as f:
    f.read(12)
    clen, _ = struct.unpack('<II', f.read(8))
    js = json.loads(f.read(clen).decode('utf-8'))
HUM = {js['nodes'][h['node']]['name'] for h in js['extensions']['VRM']['humanoid']['humanBones']}
g = json.load(open(GAIT))
FPS = 60.0
sv = g['speed_variation']
A_, B_ = sv['amplitude'], sv['stance_share']


def use(name):
    ad.action = bpy.data.actions[name]
    if getattr(ad, 'action_slot', None) is None and len(ad.action.slots):
        ad.action_slot = ad.action.slots[0]
    fr = ad.action.frame_range
    return int(round(fr[0])), int(round(fr[1]))


def ground(t, nf):
    """how far the ground has moved back under the in-place sprint at frame t (m), as build_sprint_r1_render.py"""
    vt = g['speed'] * nf / FPS
    n, r = divmod(t, nf)
    phi = r / float(nf)
    k = int(math.floor(phi / 0.5 + 1e-12))
    q = phi - 0.5 * k
    di = k * (2.0 * B_ / math.pi) + (B_ / math.pi) * (1.0 - math.cos(math.pi * q / B_)) if q < B_ else (k + 1) * (2.0 * B_ / math.pi)
    return n * vt + vt * (phi * (1.0 + A_ * 4.0 * B_ / math.pi) - A_ * di)


def sample(name):
    f0, f1 = use(name)
    rows = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        pb = arm.pose.bones
        mw = arm.matrix_world
        rows.append({'q': {b.name: (mw @ b.matrix).to_quaternion() for b in pb},
                     'p': {n: mw @ pb[n].head for n in ('J_Bip_C_Hips', 'J_Bip_L_Foot', 'J_Bip_R_Foot', 'J_Bip_L_ToeBase', 'J_Bip_R_ToeBase',
                                                        'J_Bip_R_UpperLeg', 'J_Bip_R_LowerLeg')}})
    return rows


def adeg(a, b):
    x = math.degrees(a.rotation_difference(b).angle)
    return min(x, 360.0 - x)


def knee(r):
    h, k, a = r['p']['J_Bip_R_UpperLeg'], r['p']['J_Bip_R_LowerLeg'], r['p']['J_Bip_R_Foot']
    return 180.0 - math.degrees((h - k).angle(a - k))


ref = sample(REF)
res = {}
for name in [REF] + ACTS:
    rows = sample(name)
    nf = len(rows) - 1
    bones = list(rows[0]['q'])
    seam = max(adeg(rows[0]['q'][b], rows[nf]['q'][b]) for b in bones)
    st = {True: (0.0, ''), False: (0.0, '')}
    for j in range(nf):
        for b in bones:
            a_ = adeg(rows[j]['q'][b], rows[j + 1]['q'][b])
            k_ = b in HUM
            if a_ > st[k_][0]:
                st[k_] = (a_, '%s %d->%d' % (b, j, j + 1))
    slip = 0.0
    for side, f_td in (('R', 0), ('L', nf // 2)):
        n_st = int(math.floor(B_ * nf + 1e-6))
        pts = []
        for j in range(f_td, f_td + n_st + 1):
            p_ = rows[j % nf]['p']['J_Bip_%s_ToeBase' % side].copy()
            p_.y += ground(j, nf)
            pts.append(p_)
        slip = max(slip, max((p_ - pts[0]).length for p_ in pts))
    feet = max((rows[j]['p'][n] - ref[j]['p'][n]).length for j in range(nf) for n in ('J_Bip_L_Foot', 'J_Bip_R_Foot', 'J_Bip_L_ToeBase', 'J_Bip_R_ToeBase'))
    hips = max((rows[j]['p']['J_Bip_C_Hips'] - ref[j]['p']['J_Bip_C_Hips']).length for j in range(nf))
    kn = [knee(rows[j]) for j in range(nf)]
    k_to = knee(rows[int(round(B_ * nf))])
    res[name] = {'frames': nf, 'seam_deg': round(seam, 4), 'step_humanoid': [round(st[True][0], 2), st[True][1]],
                 'step_other': [round(st[False][0], 2), st[False][1]], 'toe_slip_mm': round(1000.0 * slip, 2),
                 'feet_vs_ref_mm': round(1000.0 * feet, 1), 'hips_vs_ref_mm': round(1000.0 * hips, 1),
                 'knee_to_frame8': round(k_to, 1), 'knee_sw_max': round(max(kn), 1)}
    print('CHECK', name, res[name], flush=True)
json.dump(res, open(OUT, 'w'), indent=1)
print('WROTE', OUT)
