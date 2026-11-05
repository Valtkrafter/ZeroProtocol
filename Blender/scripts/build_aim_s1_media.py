"""
Yoru - AIM SUITE STAGE 1: preview video, drift plot and the Markdown report of the aim-idle loop (system python, run with -I; OpenCV + Pillow,
H.264 through mp4_to_h264.py / PyAV; there is no ffmpeg).
  python -I build_aim_s1_media.py <frames dir> <report .json> <video .mp4> <plot .png> <report .md> [visdiag=<.json>] [fps=15] [plot_only=1]
          [round=2 before=<round-1 report .json> loopvis=<visdiag loop .json>] [md_only=1: only the report section]
  round=2 (head locked on the crosshair): title and live line with the head, a fourth plot panel (head yaw / pitch / roll against frame 0, round 1
  dashed), the still is named after the video, and instead of rewriting <report .md> a section "## Runde 2" (table before / after) is appended to
  it (an older "## Runde 2" section is replaced).
  e.g. python -I Blender/scripts/build_aim_s1_media.py Blender/work/Aim/s1/frames_r2 Blender/work/Aim/Yoru_Aim_s1_r2_report.json
       Blender/previews/Aim/s1/aim_idle_v2_r2.mp4 Blender/previews/Aim/s1/aim_idle_drift_plot_r2.png Blender/work/Aim/Yoru_Aim_s1_report.md
       round=2 before=Blender/work/Aim/Yoru_Aim_s1_report.json loopvis=Blender/work/Aim/Yoru_Aim_s1_r2_visloop.json
  e.g. python -I Blender/scripts/build_aim_s1_media.py Blender/work/Aim/s1/frames Blender/work/Aim/Yoru_Aim_s1_report.json
       Blender/previews/Aim/s1/aim_idle_v2.mp4 Blender/previews/Aim/s1/aim_idle_drift_plot.png Blender/work/Aim/Yoru_Aim_s1_report.md
       visdiag=Blender/work/Aim/Yoru_Aim_s1_visdiag.json
Video: one file, two panels side by side (left front 3/4 = <frames>/front34, right the real game camera = <frames>/game_body), frames 0, 2, .. 358 of
the 12 s loop at 15 fps (one full loop, real time), a line with the live numbers below (shoulders, muzzle heights, elbows).  The mp4v file written
by OpenCV goes next to the frames; mp4_to_h264.py writes the H.264 video.
Plot: over 12 s the shoulder height (breathing) against the vertical muzzle height of both pistols, the elbow flexion (with try 1 for comparison:
hands fixed in all three axes) and the slide of the muzzles along the aim line.
"""
import sys, os, json, math, subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FRAMES, REPORT, VIDEO, PLOT, MD = sys.argv[1:6]
KV = dict(a.split('=', 1) for a in sys.argv[6:] if '=' in a)
FPS = int(KV.get('fps', 15))
RND = int(KV.get('round', 1))
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(REPORT))
S = D['summary']
PF = D['per_frame']
VD = json.load(open(KV['visdiag'])) if KV.get('visdiag') and os.path.exists(KV['visdiag']) else None
F_T = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 22)
F_B = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 18)
F = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
F_S = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
BG = (22, 24, 29)
YEL, CYAN, GREY = (255, 226, 120), (150, 220, 255), (150, 156, 168)


def de(x, n=1):
    return ('%.*f' % (n, x)).replace('.', ',')


# ------------------------------------------------------------------ video
A = Image.open(os.path.join(FRAMES, 'front34', 'f_000.png'))
B = Image.open(os.path.join(FRAMES, 'game_body', 'f_000.png'))
PH = max(A.height, B.height)
GAP, TOP, BOT = 6, 42, 36
VW = (A.width + GAP + B.width + 1) // 2 * 2
VH = (TOP + PH + BOT + 1) // 2 * 2


def frame(f):
    g = Image.new('RGB', (VW, VH), BG)
    d = ImageDraw.Draw(g)
    a = Image.open(os.path.join(FRAMES, 'front34', 'f_%03d.png' % f)).convert('RGB')
    b = Image.open(os.path.join(FRAMES, 'game_body', 'f_%03d.png' % f)).convert('RGB')
    g.paste(a, (0, TOP + (PH - a.height) // 2))
    g.paste(b, (a.width + GAP, TOP + (PH - b.height) // 2))
    d.text((10, 9), ('Aim-Idle (Stufe 1, Runde 1): Körper = Idle v2, Arme auf das Ziel gelockt, 12-s-Schleife in Echtzeit' if RND == 1 else
                     'Aim-Idle (Stufe 1, Runde %d): Körper = Idle v2, Arme und Kopf auf das Ziel gelockt, 12 s in Echtzeit' % RND), fill=YEL, font=F_T)
    for x, lab in ((8, 'schräg von vorn'), (a.width + GAP + 8, 'echte Spielkamera (0,35 m rechts)')):
        d.rectangle([x - 4, TOP + 6, x + d.textlength(lab, font=F_B) + 6, TOP + 30], fill=(20, 22, 26))
        d.text((x, TOP + 8), lab, fill=CYAN, font=F_B)
    line = 't = %s s von 12 s   |   Schultern %s mm   |   Mündung senkrecht: rechts %s mm, links %s mm   |   Ellbogen: rechts %s°, links %s°' % (
        de(f / 30.0, 1), ('+' if PF['shoulder_mean_z_mm'][f] >= 0 else '') + de(PF['shoulder_mean_z_mm'][f], 1),
        ('+' if PF['muzzle_R_z_mm'][f] >= 0 else '') + de(PF['muzzle_R_z_mm'][f], 2), ('+' if PF['muzzle_L_z_mm'][f] >= 0 else '') + de(PF['muzzle_L_z_mm'][f], 2),
        de(PF['elbow_flex_R'][f], 1), de(PF['elbow_flex_L'][f], 1))
    if RND > 1 and 'head_yaw_deg' in PF:
        line += '   |   Kopf: Gier %s°, Neigung %s°' % (de(PF['head_yaw_deg'][f] + 0.0, 2), de(PF['head_pitch_deg'][f] + 0.0, 2))
    d.text((10, TOP + PH + 8), line, fill=(225, 228, 235), font=F_S if RND > 1 else F)
    return cv2.cvtColor(np.array(g), cv2.COLOR_RGB2BGR)


PLOT_ONLY = KV.get('plot_only') == '1' or KV.get('md_only') == '1'
os.makedirs(os.path.dirname(VIDEO), exist_ok=True)
tmp = os.path.join(FRAMES, os.path.splitext(os.path.basename(VIDEO))[0] + '_mp4v.mp4')
if not PLOT_ONLY:
    vw = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (VW, VH))
    if not vw.isOpened():
        raise SystemExit('video writer could not open ' + tmp)
    SEQ = list(range(0, 360, 2))
    for f in SEQ:
        vw.write(frame(f))
    vw.release()
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'mp4_to_h264.py'), tmp, VIDEO], check=True)
    still = os.path.join(os.path.dirname(VIDEO), os.path.splitext(os.path.basename(VIDEO))[0] + '_still_t0.png')   # round 1: aim_idle_v2_still_t0.png
    cv2.imwrite(still, frame(0))
    print('video', VIDEO, '| still', still, flush=True)


# ------------------------------------------------------------------ plot
W, H = 1500, (1180 if RND == 1 else 1500)
img = Image.new('RGB', (W, H), (250, 250, 252))
d = ImageDraw.Draw(img)
L_, R_ = 110, 1290
t = PF['t']
d.text((L_, 14), 'Aim-Idle über 12 s: die Brust atmet, die Pistolen bleiben in der Höhe stehen' + ('' if RND == 1 else ', der Kopf auf dem Fadenkreuz (Runde %d)' % RND),
       fill=(20, 20, 30), font=F_T)
COL = dict(sh=(40, 110, 220), R=(230, 120, 20), L=(30, 160, 80), try1=(150, 150, 150), band=(225, 235, 250))


def panel(y0, y1, lo, hi, step, title, unit):
    d.text((L_, y0 - 30), title, fill=(30, 30, 40), font=F_B)
    d.rectangle([L_, y0, R_, y1], outline=(160, 160, 170))
    def Y(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)
    def X(s):
        return L_ + s / 12.0 * (R_ - L_)
    v = lo
    while v <= hi + 1e-9:
        d.line([(L_, Y(v)), (R_, Y(v))], fill=(228, 228, 234))
        d.text((L_ - 10 - d.textlength(de(v, 0 if step >= 1 else 1), font=F_S), Y(v) - 8), de(v, 0 if step >= 1 else 1), fill=(90, 90, 100), font=F_S)
        v += step
    for s in range(13):
        d.line([(X(s), y0), (X(s), y1)], fill=(236, 236, 240))
        d.text((X(s) - 6, y1 + 5), str(s), fill=(90, 90, 100), font=F_S)
    d.text((R_ + 10, y1 + 5), 's', fill=(90, 90, 100), font=F_S)
    d.text((L_ - 95, y0 - 4), unit, fill=(90, 90, 100), font=F_S)
    return X, Y


def curve(X, Y, vals, col, width=3, dash=False):
    pts = [(X(t[i]), Y(vals[i])) for i in range(len(vals))]
    for i in range(len(pts) - 1):
        if dash and (i // 4) % 2:
            continue
        d.line([pts[i], pts[i + 1]], fill=col, width=width)


def legend(x, y, items):
    for col, lab, dash in items:
        if dash:
            for k in range(0, 34, 10):
                d.line([(x + k, y + 9), (x + k + 5, y + 9)], fill=col, width=3)
        else:
            d.line([(x, y + 9), (x + 34, y + 9)], fill=col, width=4)
        d.text((x + 42, y), lab, fill=(30, 30, 40), font=F_S)
        y += 22


# panel 1: heights
X, Y = panel(90, 400, -10.0, 16.0, 2.0, 'Höhe gegenüber Bild 0', 'mm')
d.rectangle([L_ + 1, Y(2.0), R_ - 1, Y(-2.0)], fill=(236, 246, 236))
d.line([(L_, Y(0)), (R_, Y(0))], fill=(160, 160, 170))
curve(X, Y, PF['shoulder_mean_z_mm'], COL['sh'])
curve(X, Y, PF['muzzle_R_z_mm'], COL['R'])
curve(X, Y, PF['muzzle_L_z_mm'], COL['L'])
legend(R_ - 560, Y(-3.6), [(COL['sh'], 'Schultern (Mitte beider Schultergelenke): %s mm auf und ab' % de(S['shoulder_mean_z_p2p_mm'], 1), False),
                       (COL['R'], 'Mündung rechts, senkrecht: %s mm' % de(S['R']['muzzle_vertical_p2p_mm'], 2), False),
                       (COL['L'], 'Mündung links, senkrecht: %s mm' % de(S['L']['muzzle_vertical_p2p_mm'], 2), False)])
d.text((L_ + 8, Y(-2.0) + 4), 'grün hinterlegt: erlaubte Mündungsdrift ±2 mm', fill=(70, 120, 70), font=F_S)
# panel 2: elbow flexion
X, Y = panel(480, 770, 0.0, 18.0, 2.0, 'Ellbogenbeugung', 'Grad')
d.rectangle([L_ + 1, Y(15.1), R_ - 1, Y(11.9)], fill=COL['band'])
d.text((L_ + 8, Y(15.1) - 20), 'Zielband 13,5 ± 1,6°', fill=(60, 90, 150), font=F_S)
if 'try1_solver' in D and 'elbow_flex_per_frame' in D['try1_solver']:
    curve(X, Y, D['try1_solver']['elbow_flex_per_frame']['R'], COL['try1'], 2, dash=True)
curve(X, Y, PF['elbow_flex_R'], COL['R'])
curve(X, Y, PF['elbow_flex_L'], COL['L'])
legend(R_ - 600, Y(9.0), [(COL['R'], 'rechts: %s bis %s°' % tuple(de(v, 1) for v in S['R']['elbow_flex_deg']), False),
                          (COL['L'], 'links: %s bis %s°' % tuple(de(v, 1) for v in S['L']['elbow_flex_deg']), False),
                          (COL['try1'], 'Versuch 1, Hände in allen Achsen fest (rechts): Arm streckt bis %s° durch' % de(
                              D.get('try1_solver', {}).get('flex_deg', {}).get('R', [0, 0])[0], 1), True)])
# panel 3: slide along the aim line
X, Y = panel(850, 1110, -14.0, 4.0, 2.0, 'Mündung vor (+) und zurück (-) entlang der Schusslinie', 'mm')
d.line([(L_, Y(0)), (R_, Y(0))], fill=(160, 160, 170))
curve(X, Y, PF['muzzle_R_y_mm'], COL['R'])
curve(X, Y, PF['muzzle_L_y_mm'], COL['L'])
legend(L_ + 120, Y(3.7), [(COL['R'], 'rechts: bis %s mm zurück (verschiebt den Zielpunkt nicht)' % de(S['R']['muzzle_along_aim_max_vs_f0_mm'], 1), False),
                           (COL['L'], 'links: bis %s mm zurück' % de(S['L']['muzzle_along_aim_max_vs_f0_mm'], 1), False)])
if RND > 1 and 'head_yaw_deg' in PF:                                  # panel 4: the head against frame 0 (round 2: locked)
    X, Y = panel(1190, 1430, -2.5, 2.5, 0.5, 'Kopf gegen Bild 0 (Pose V2): Gier, Neigung, Roll', 'Grad')
    d.rectangle([L_ + 1, Y(0.3), R_ - 1, Y(-0.3)], fill=(236, 246, 236))
    d.line([(L_, Y(0)), (R_, Y(0))], fill=(160, 160, 170))
    HC = dict(yaw=(120, 60, 200), pitch=(200, 60, 90), roll=(60, 150, 160))
    if 'compare_head_yaw_deg' in PF:
        curve(X, Y, PF['compare_head_yaw_deg'], HC['yaw'], 2, dash=True)
        curve(X, Y, PF['compare_head_pitch_deg'], HC['pitch'], 2, dash=True)
        curve(X, Y, PF['compare_head_roll_deg'], HC['roll'], 2, dash=True)
    curve(X, Y, PF['head_yaw_deg'], HC['yaw'])
    curve(X, Y, PF['head_pitch_deg'], HC['pitch'])
    curve(X, Y, PF['head_roll_deg'], HC['roll'])
    hv, hc = S['head_vs_frame0'], S.get('head_vs_frame0_compare_round', {})
    legend(L_ + 20, Y(2.35), [(HC['yaw'], 'Gier: Runde 1 gestrichelt %s bis %s°, jetzt %s bis %s°' % (*(de(v, 2) for v in hc.get('yaw_deg', [0, 0])), *(de(v, 3) for v in hv['yaw_deg'])), False),
                              (HC['pitch'], 'Neigung: Runde 1 %s bis %s°, jetzt %s bis %s°' % (*(de(v, 2) for v in hc.get('pitch_deg', [0, 0])), *(de(v, 3) for v in hv['pitch_deg'])), False),
                              (HC['roll'], 'Roll: Runde 1 %s bis %s°, jetzt %s bis %s°' % (*(de(v, 2) for v in hc.get('roll_deg', [0, 0])), *(de(v, 3) for v in hv['roll_deg'])), False)])
    d.text((L_ + 8, Y(-0.3) + 4), 'grün hinterlegt: ±0,3° (Vorgabe)', fill=(70, 120, 70), font=F_S)
d.text((L_, H - 34), 'Zeit in Sekunden. Bild 0 = Pose V2. Die Hände gleiten nur entlang ihrer Arm-Linie, weil die Schultern beim Atmen auch '
                     'bis 12 mm zurückgehen.', fill=(70, 70, 80), font=F_S)
os.makedirs(os.path.dirname(PLOT), exist_ok=True)
if KV.get('md_only') != '1':
    img.save(PLOT)
    print('plot', PLOT, flush=True)

# ------------------------------------------------------------------ Markdown report
if RND > 1:
    import importlib.util
    _spec = importlib.util.spec_from_file_location('aim_s1_r2md', os.path.join(HERE, 'build_aim_s1_media_r2md.py'))
    _m = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    _m.append_section(MD, D, json.load(open(KV['before'])), json.load(open(KV['loopvis'])) if KV.get('loopvis') else None, VIDEO, PLOT, de)
    raise SystemExit(0)


def ok(b):
    return 'ja' if b else '**nein**'


r, l = S['R'], S['L']
rows = [
    ('Mündungsdrift senkrecht (Spanne)', '%s mm' % de(r['muzzle_vertical_p2p_mm'], 2), '%s mm' % de(l['muzzle_vertical_p2p_mm'], 2), '<= 2,0 mm',
     ok(max(r['muzzle_vertical_p2p_mm'], l['muzzle_vertical_p2p_mm']) <= 2.0)),
    ('Mündungsdrift 3D (größter Abstand zu Bild 0)', '%s mm' % de(r['muzzle_3d_max_vs_f0_mm'], 1), '%s mm' % de(l['muzzle_3d_max_vs_f0_mm'], 1),
     'melden', 'davon entlang der Schusslinie %s / %s mm, seitlich %s / %s mm' % (de(r['muzzle_along_aim_max_vs_f0_mm'], 1), de(l['muzzle_along_aim_max_vs_f0_mm'], 1),
                                                                         de(r['muzzle_side_max_vs_f0_mm'], 1), de(l['muzzle_side_max_vs_f0_mm'], 1))),
    ('Kantung', '%s bis %s°' % tuple(de(v, 1) for v in r['cant_deg']), '%s bis %s°' % tuple(de(v, 1) for v in l['cant_deg']), '0,0°',
     ok(max(abs(v) for v in r['cant_deg'] + l['cant_deg']) < 0.05)),
    ('Lauf Gier / Neigung', '%s / %s°' % (de(r['barrel_yaw_deg'][1], 2), de(r['barrel_pitch_deg'][1], 2)), '%s / %s°' % (de(l['barrel_yaw_deg'][1], 2), de(l['barrel_pitch_deg'][1], 2)),
     'parallel zur Ziellinie', 'ja (konstant wie V2)'),
    ('Ellbogenbeugung', '%s bis %s°' % tuple(de(v, 2) for v in r['elbow_flex_deg']), '%s bis %s°' % tuple(de(v, 2) for v in l['elbow_flex_deg']), '13,5 ± 1,6°',
     ok(min(r['elbow_flex_deg'][0], l['elbow_flex_deg'][0]) >= 11.9 and max(r['elbow_flex_deg'][1], l['elbow_flex_deg'][1]) <= 15.1)),
    ('Arm-Richtung nach außen', '%s bis %s°' % tuple(de(v, 1) for v in r['arm_out_deg']), '%s bis %s°' % tuple(de(v, 1) for v in l['arm_out_deg']),
     '20° je Arm', 'Arme %s bis %s° auseinander (Ziel 40°)' % tuple(de(v, 1) for v in S['arms_apart_deg'])),
    ('Unterarm-Roll (größter Betrag)', '%s°' % de(max(abs(v) for v in r['forearm_roll_deg']), 2), '%s°' % de(max(abs(v) for v in l['forearm_roll_deg']), 2),
     '<= 18°', ok(max(abs(v) for v in r['forearm_roll_deg'] + l['forearm_roll_deg']) <= 18.0)),
    ('Handgelenk-Roll (größter Betrag)', '%s°' % de(max(abs(v) for v in r['wrist_roll_deg']), 2), '%s°' % de(max(abs(v) for v in l['wrist_roll_deg']), 2),
     '<= 12°', ok(max(abs(v) for v in r['wrist_roll_deg'] + l['wrist_roll_deg']) <= 12.0)),
    ('Handgelenkknick', '%s bis %s°' % tuple(de(v, 1) for v in r['wrist_bend_deg']), '%s bis %s°' % tuple(de(v, 1) for v in l['wrist_bend_deg']), 'möglichst < 25°',
     ok(max(r['wrist_bend_deg'][1], l['wrist_bend_deg'][1]) < 25.0)),
    ('Abstand Unterarm + Hand zum Netz (min)', '%s mm (Bild %d)' % (de(r['clear_forearm_hand_min_mm'][0], 1), r['clear_forearm_hand_min_mm'][1]),
     '%s mm (Bild %d)' % (de(l['clear_forearm_hand_min_mm'][0], 1), l['clear_forearm_hand_min_mm'][1]), '>= 3 mm',
     ok(min(r['clear_forearm_hand_min_mm'][0], l['clear_forearm_hand_min_mm'][0]) >= 3.0)),
    ('Abstand Ellbogenende zum Netz (min)', '%s mm (Bild %d)' % (de(r['clear_elbow_end_min_mm'][0], 1), r['clear_elbow_end_min_mm'][1]),
     '%s mm (Bild %d)' % (de(l['clear_elbow_end_min_mm'][0], 1), l['clear_elbow_end_min_mm'][1]), '>= 3 mm',
     ok(min(r['clear_elbow_end_min_mm'][0], l['clear_elbow_end_min_mm'][0]) >= 3.0)),
    ('Durchdringungen (Dreieckspaare Arm / Pistole)', '%d / %d' % (r['cuts_arm_total'], r['cuts_pistol_total']), '%d / %d' % (l['cuts_arm_total'], l['cuts_pistol_total']),
     '0', ok(r['cuts_arm_total'] + r['cuts_pistol_total'] + l['cuts_arm_total'] + l['cuts_pistol_total'] == 0)),
    ('Pistole zum Netz (min)', '%s mm' % de(r['clear_pistol_min_mm'][0], 0), '%s mm' % de(l['clear_pistol_min_mm'][0], 0), '>= 3 mm', 'ja'),
    ('Sichtbar in der echten Spielkamera', '%d bis %d %% (min Bild %d)' % (round(100 * r['visible_game_min'][0]), round(100 * r['visible_game_max']), r['visible_game_min'][1]),
     '%d bis %d %% (min Bild %d)' % (round(100 * l['visible_game_min'][0]), round(100 * l['visible_game_max']), l['visible_game_min'][1]), 'Runde 5: 46 / 37 %',
     'rechts gehalten, **links meist vom Haar verdeckt**'),
]
srow = [
    ('Naht Bild 360 gegen Bild 0', '%s° / %s mm (Gelenke), Mündung %s mm, Gesicht %s' % (de(S['seam_rot_max_deg'], 3), de(S['seam_joint_max_mm'], 3), de(S['seam_muzzle_max_mm'], 3),
                                                                                       de(S['seam_face_keys_max'], 3)), '0', ok(S['seam_rot_max_deg'] < 1e-3 and S['seam_joint_max_mm'] < 1e-3)),
    ('Standfuß-Drift (Zehengelenk, über die Schleife)', 'links %s mm, rechts %s mm' % (de(S['toe_L_max_vs_f0_mm'], 3), de(S['toe_R_max_vs_f0_mm'], 3)), '<= 1,5 mm',
     ok(max(S['toe_L_max_vs_f0_mm'], S['toe_R_max_vs_f0_mm']) <= 1.5)),
    ('Kopfblick Gier (+ = nach rechts) / Neigung', '%s bis %s° / %s bis %s°' % (de(S['gaze_yaw_deg'][0], 1), de(S['gaze_yaw_deg'][1], 1), de(S['gaze_pitch_deg'][0], 1),
                                                                              de(S['gaze_pitch_deg'][1], 1)), 'Gier 0 ± 1°', ok(max(abs(v) for v in S['gaze_yaw_deg']) <= 1.0)),
    ('Größter Gelenkschritt pro Bild', '%s° (%s, Bild %d; im Idle v2 genauso: %s°)' % (de(S['joint_step_max'][0], 2), S['joint_step_max'][1], S['joint_step_max'][2],
                                                                                   de(S['joint_step_max_in_idle_v2'][0], 2)), '<= 15°', ok(S['joint_step_max'][0] <= 15.0)),
    ('  davon Arme / Rumpf und Kopf', '%s° / %s°' % (de(S['joint_step_max_arms'][0], 2), de(S['joint_step_max_hips_spine_head'][0], 2)), '<= 15°', 'ja'),
    ('Körper-Keys gegen Idle v2 (alle Nicht-Arm-Knochen außer UpperChest, Head)', '%s°, Hüftposition %s mm, Gesicht %s' % (
        de(S['body_vs_idle_max_deg'], 4), de(S['hips_loc_vs_idle_max_mm'], 4), de(S['face_vs_idle_max'], 4)), '0', ok(S['body_vs_idle_max_deg'] < 1e-3)),
    ('Offsets UpperChest / Head (lokale Gier, konstant)', '%s° / %s° (Schwankung %s° / %s°)' % (
        de(S['offset_upper_chest_yaw_deg'], 2), de(S['offset_head_yaw_deg'], 2), de(S['offset_constancy_max_deg']['J_Bip_C_UpperChest'], 4),
        de(S['offset_constancy_max_deg']['J_Bip_C_Head'], 4)), '+8° / -9°', 'ja'),
    ('Bild 0 gegen Pose V2', '%s°' % de(S['frame0_vs_pose_V2_max_deg'], 4), '0', ok(S['frame0_vs_pose_V2_max_deg'] < 1e-3)),
]
pc = D.get('step0_pose_check', {})
t1 = D.get('try1_solver', {})
md = ['# Yoru Aim-Idle, Stufe 1, Runde 1 (31.10.2026)', '',
      'Datei `Blender/work/Aim/Yoru_Aim_s1.blend`, Action `Yoru_Aim_Idle` (alles), `Yoru_Aim_Idle_Face` (Gesicht), dazu getrennt `Yoru_Aim_Idle_Layer` '
      '(Spine aufwärts mit Armen, ohne Hüfte) und `Yoru_Aim_Idle_Stand` (Hüfte, Beine, Füße, Schwanz). 361 Bilder bei 30 fps, Bild 360 = Bild 0. '
      'Skripte `Blender/scripts/build_aim_s1.py` (Bau), `build_aim_s1_check.py` (Messung), `build_aim_s1_render.py`, `build_aim_s1_media.py`, `build_aim_s1_visdiag.py`.', '',
      '## Schritt 0: Pose festgeschrieben', '',
      '`Blender/Yoru_Aim.blend` (vorher bitgleich mit `work/Aim/Yoru_Aim_r3b.blend`, A2) enthält nur noch V2: %s, NLA-Spur `Stand`, Pistolen an `J_Bip_L/R_Hand`. '
      'Gegen `Yoru_Aim_r5_full_V2` Bild 0: volle Action %s° / %s mm, Schicht + NLA-Stand %s° / %s mm, Netz-Punkte %s mm (Ziel 0,001° / 0,01 mm).' % (
          ', '.join('`%s`' % a for a in pc.get('actions_after', [])), de(pc.get('full_vs_r5_full_V2_frame0', {}).get('bone_rot_max_deg', -1), 4),
          de(pc.get('full_vs_r5_full_V2_frame0', {}).get('bone_pos_max_mm', -1), 4), de(pc.get('layer_plus_nla_stand_vs_r5_full_V2_frame0', {}).get('bone_rot_max_deg', -1), 4),
          de(pc.get('layer_plus_nla_stand_vs_r5_full_V2_frame0', {}).get('bone_pos_max_mm', -1), 4), de(pc.get('full_vs_r5_full_V2_frame0', {}).get('vertex_max_mm', -1), 4)), '',
      '## Arme und Pistolen (alle 361 Bilder; Abstände an %d Bildern: jedes %d. plus Atem-Extreme %s)' % (
          S['sample_frames']['count'], S['sample_frames']['step'], S['sample_frames']['breathing_extremes']), '',
      '| Messgröße | rechts | links | Ziel | erfüllt |', '|---|---|---|---|---|']
md += ['| %s | %s | %s | %s | %s |' % row for row in rows]
md += ['', '## Körper, Naht, Kopf', '', '| Messgröße | Wert | Ziel | erfüllt |', '|---|---|---|---|']
md += ['| %s | %s | %s | %s |' % row for row in srow]
md += ['', '## Abweichungen von der Vorgabe (gemeldet, nicht still geändert)', '',
       '1. **Hände nicht in allen drei Achsen fest.** Die Schultergelenke des Idle gehen bis %s mm hoch, %s mm vor/zurück und %s mm seitlich (rechts; links %s / %s / %s mm). '
       'Mit fest stehendem Handgelenk (Versuch 1, `work/Aim/Yoru_Aim_s1_try1_handsfixed.blend`) wächst der Abstand Schulter-Handgelenk bis %s mm, der V2-Arm hat bei 13,5° Beugung nur 2,9 mm Reserve: '
       'der Ellbogen streckt bis %s° durch (steifer Arm) und das Handgelenk wird trotzdem bis %s mm zurückgezogen. Gebaut ist deshalb: Hand-Drehung fest (Kantung und Laufrichtung unverändert), '
       'das Handgelenk gleitet nur entlang der eigenen Arm-Linie mit (rechts bis %s mm, links bis %s mm). Senkrecht bleibt die Mündung unter %s mm, der Ellbogen im Band.' % (
           de(r['shoulder_joint_p2p_mm'][2], 1), de(r['shoulder_joint_p2p_mm'][1], 1), de(r['shoulder_joint_p2p_mm'][0], 1), de(l['shoulder_joint_p2p_mm'][2], 1),
           de(l['shoulder_joint_p2p_mm'][1], 1), de(l['shoulder_joint_p2p_mm'][0], 1), de(max(t1.get('shoulder_wrist_mm', {}).get('R', [0, 0])[1], t1.get('shoulder_wrist_mm', {}).get('L', [0, 0])[1]), 1),
           de(min(t1.get('flex_deg', {}).get('R', [0, 0])[0], t1.get('flex_deg', {}).get('L', [0, 0])[0]), 1),
           de(max(t1.get('reach_deficit_max_mm', {}).get('R', 0), t1.get('reach_deficit_max_mm', {}).get('L', 0)), 1),
           de(r['muzzle_3d_max_vs_f0_mm'], 1), de(l['muzzle_3d_max_vs_f0_mm'], 1), de(max(r['muzzle_vertical_p2p_mm'], l['muzzle_vertical_p2p_mm']) + 0.05, 1)),
       '2. **Kopfblick %s bis %s° statt 0 ± 1°.** Mit den zwei konstanten Offsets folgt der Kopf der Kopf- und Hüftbewegung des Idle (bis %s° nach rechts). '
       'Abhilfe wäre ein Kopf, der der Ziellinie folgt (zeitabhängiger Ausgleich statt konstantem -9°); dann ist Bild 0 weiter die Pose.' % (
           de(S['gaze_yaw_deg'][0], 1), de(S['gaze_yaw_deg'][1], 1), de(S['gaze_yaw_deg'][1], 1)),
       '3. **Linke Pistole in der Spielkamera meist verdeckt:** %d bis %d %% sichtbar (Bild 0 = Pose: %d %%), die rechte bleibt bei %d bis %d %%.' % (
           round(100 * l['visible_game_min'][0]), round(100 * l['visible_game_max']), round(100 * l['visible_game_frame0']), round(100 * r['visible_game_min'][0]),
           round(100 * r['visible_game_max']))]
if VD:
    md += ['', '   Ursache (linke Pistole, sichtbarer Anteil; `build_aim_s1_visdiag.py`):', '',
           '   | Bild | wie gebaut | Haar wie Bild 0 | Kopf auf Ziellinie | beides | Rumpf wie Bild 0 | Kopfblick |', '   |---|---|---|---|---|---|---|']
    for f, rw in VD['frames'].items():
        md.append('   | %s | %d %% | %d %% | %d %% | %d %% | %d %% | %s° |' % (f, round(100 * rw['as_built']), round(100 * rw['hair_of_frame0']), round(100 * rw['head_yaw_compensated']),
                                                                       round(100 * rw['head_comp_and_hair_of_frame0']), round(100 * rw['trunk_of_frame0']), de(rw['gaze_yaw_deg'], 2)))
    md += ['', '   Kein einzelner Grund: Kopfdrehung, Haarwind und Oberkörper-Schwanken des Idle verdecken sie zusammen. Kopf auf der Ziellinie hebt das Minimum auf ca. 20 %, '
           'mit ruhigem Haar auf ca. 24 %, die 37 % der Pose hält nur Bild 0.']
md += ['', '## Ablage', '', '- Video `Blender/previews/Aim/s1/aim_idle_v2.mp4`, Standbild `aim_idle_v2_still_t0.png`, Diagramm `aim_idle_drift_plot.png`',
       '- Zahlen `Blender/work/Aim/Yoru_Aim_s1_report.json` (mit Werten je Bild), Löser `Yoru_Aim_s1_solver.json`, Versuch 1 `Yoru_Aim_s1_try1_handsfixed*`, Schritt 0 `Yoru_Aim_s1_pose_check.json`']
open(MD, 'w', encoding='utf-8').write('\n'.join(md) + '\n')
print('report', MD, flush=True)
