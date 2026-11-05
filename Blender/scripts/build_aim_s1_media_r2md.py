"""
Yoru - AIM SUITE STAGE 1, round 2: appends the section "## Runde 2" (head locked on the crosshair, table before / after) to the Markdown report.
Called by build_aim_s1_media.py with round=2 (not on its own):  append_section(<report .md>, <round-2 report>, <round-1 report>, <loop visibility>,
<video>, <plot>, de).  An older "## Runde 2" section is replaced, the round-1 part above stays as it is.
"""
import os


def append_section(md_path, D2, D1, VL, video, plot, de):
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(md_path)))))   # the repository (md lies in Blender/work/Aim)
    video, plot = os.path.abspath(video), os.path.abspath(plot)
    S2, S1 = D2['summary'], D1['summary']
    hv, hc = S2['head_vs_frame0'], S2.get('head_vs_frame0_compare_round', {})

    def ok(b):
        return 'ja' if b else '**nein**'

    def rg(v, n=2):
        return '%s bis %s' % (de(v[0], n), de(v[1], n))

    def amax(v):
        return max(abs(x) for x in v)

    def ranges(fr):
        out, a = [], None
        for i, f in enumerate(fr):
            if a is None:
                a = f
            if i + 1 == len(fr) or fr[i + 1] != f + 1:
                out.append(str(a) if a == f else '%d–%d' % (a, f))
                a = None
        return out

    def vis(run, s):
        if not VL or run not in VL['runs']:
            return 'nicht gemessen'
        x = VL['runs'][run]['summary'][s]
        rg_ = ranges(x['frames_at_min'])
        frs = ('Bild ' + ', '.join(rg_)) if len(rg_) <= 3 else 'in %d von 361 Bildern' % len(x['frames_at_min'])
        return 'min %d %% (%s), max %d %%, Mittel %d %%' % (round(100 * x['min']), frs, round(100 * x['max']), round(100 * x['mean']))

    r1, l1, r2, l2 = S1['R'], S1['L'], S2['R'], S2['L']
    head_lim = 0.3
    rows = [
        ('Kopf Gier gegen Bild 0', rg(hc.get('yaw_deg', [0, 0])) + '°', rg(hv['yaw_deg'], 3) + '°', '±0,3°', ok(amax(hv['yaw_deg']) <= head_lim)),
        ('Kopf Neigung gegen Bild 0', rg(hc.get('pitch_deg', [0, 0])) + '°', rg(hv['pitch_deg'], 3) + '°', '±0,3°', ok(amax(hv['pitch_deg']) <= head_lim)),
        ('Kopf Roll gegen Bild 0', rg(hc.get('roll_deg', [0, 0])) + '°', rg(hv['roll_deg'], 3) + '°', '±0,3°', ok(amax(hv['roll_deg']) <= head_lim)),
        ('Kopf gesamt (größter Drehwinkel gegen Bild 0)', de(hc.get('total_max_deg', 0), 2) + '°', de(hv['total_max_deg'], 4) + '°', '', ''),
        ('Größter Kopfschritt pro Bild (lokal)', de(S2.get('compare_joint_step_max_head', [0])[0], 3) + '°', de(S2['joint_step_max_head'][0], 3) + '°', '<= 0,5°',
         ok(S2['joint_step_max_head'][0] <= 0.5)),
        ('Größter Gelenkschritt insgesamt', '%s° (%s)' % (de(S1['joint_step_max'][0], 2), S1['joint_step_max'][1]),
         '%s° (%s)' % (de(S2['joint_step_max'][0], 2), S2['joint_step_max'][1]), '<= 15°', ok(S2['joint_step_max'][0] <= 15.0)),
        ('Naht 360 gegen 0 (Gelenke, Mündung)', '%s° / %s mm' % (de(S1['seam_rot_max_deg'], 3), de(S1['seam_joint_max_mm'], 3)),
         '%s° / %s mm' % (de(S2['seam_rot_max_deg'], 3), de(S2['seam_joint_max_mm'], 3)), '0', ok(S2['seam_rot_max_deg'] < 1e-3 and S2['seam_joint_max_mm'] < 1e-3)),
        ('Mündung senkrecht rechts / links', '%s / %s mm' % (de(r1['muzzle_vertical_p2p_mm'], 2), de(l1['muzzle_vertical_p2p_mm'], 2)),
         '%s / %s mm' % (de(r2['muzzle_vertical_p2p_mm'], 2), de(l2['muzzle_vertical_p2p_mm'], 2)), '<= 2,0 mm',
         ok(max(r2['muzzle_vertical_p2p_mm'], l2['muzzle_vertical_p2p_mm']) <= 2.0)),
        ('Mündung 3D rechts / links', '%s / %s mm' % (de(r1['muzzle_3d_max_vs_f0_mm'], 1), de(l1['muzzle_3d_max_vs_f0_mm'], 1)),
         '%s / %s mm' % (de(r2['muzzle_3d_max_vs_f0_mm'], 1), de(l2['muzzle_3d_max_vs_f0_mm'], 1)), 'melden (Gleiten entlang der Schusslinie)', ''),
        ('Ellbogenbeugung rechts / links', '%s / %s°' % (rg(r1['elbow_flex_deg']), rg(l1['elbow_flex_deg'])), '%s / %s°' % (rg(r2['elbow_flex_deg']), rg(l2['elbow_flex_deg'])),
         '13,5 ± 1,6°', ok(min(r2['elbow_flex_deg'][0], l2['elbow_flex_deg'][0]) >= 11.9 and max(r2['elbow_flex_deg'][1], l2['elbow_flex_deg'][1]) <= 15.1)),
        ('Kantung rechts / links', '%s / %s°' % (de(amax(r1['cant_deg']), 2), de(amax(l1['cant_deg']), 2)), '%s / %s°' % (de(amax(r2['cant_deg']), 2), de(amax(l2['cant_deg']), 2)),
         '0°', ok(max(amax(r2['cant_deg']), amax(l2['cant_deg'])) < 0.05)),
        ('Unterarm-Roll / Handgelenk-Roll (größter Betrag)', '%s / %s°' % (de(max(amax(r1['forearm_roll_deg']), amax(l1['forearm_roll_deg'])), 2),
                                                                         de(max(amax(r1['wrist_roll_deg']), amax(l1['wrist_roll_deg'])), 2)),
         '%s / %s°' % (de(max(amax(r2['forearm_roll_deg']), amax(l2['forearm_roll_deg'])), 2), de(max(amax(r2['wrist_roll_deg']), amax(l2['wrist_roll_deg'])), 2)),
         '<= 18° / <= 12°', ok(max(amax(r2['forearm_roll_deg']), amax(l2['forearm_roll_deg'])) <= 18 and max(amax(r2['wrist_roll_deg']), amax(l2['wrist_roll_deg'])) <= 12)),
        ('Abstand Unterarm+Hand / Ellbogenende zum Netz (min)', '%s / %s mm' % (de(min(r1['clear_forearm_hand_min_mm'][0], l1['clear_forearm_hand_min_mm'][0]), 1),
                                                                             de(min(r1['clear_elbow_end_min_mm'][0], l1['clear_elbow_end_min_mm'][0]), 1)),
         '%s / %s mm' % (de(min(r2['clear_forearm_hand_min_mm'][0], l2['clear_forearm_hand_min_mm'][0]), 1), de(min(r2['clear_elbow_end_min_mm'][0], l2['clear_elbow_end_min_mm'][0]), 1)),
         '>= 3 mm', ok(min(r2['clear_forearm_hand_min_mm'][0], l2['clear_forearm_hand_min_mm'][0], r2['clear_elbow_end_min_mm'][0], l2['clear_elbow_end_min_mm'][0]) >= 3.0)),
        ('Sichtbar in der echten Spielkamera, rechts (alle 361 Bilder)', vis('compare', 'R'), vis('this', 'R'), 'Runde 5 (Pose): 46 %', ''),
        ('Sichtbar in der echten Spielkamera, links (alle 361 Bilder)', vis('compare', 'L'), vis('this', 'L'), 'Runde 5 (Pose): 37 %', ''),
    ]
    names = dict(hair_torso='Haar × Rumpf, Hals, Schultern, Weste', hair_bust='Haar × Brust (Büste)', hair_arms='Haar × Arme (ganz)', hair_forearm_hand='Haar × Unterarme und Hände', hair_pistols='Haar × Pistolen',
                 hair_face='Haar × Gesicht', ears_hair='Ohren × Haar', face_chest='Kopf (Gesicht) × Brust und Schultern')
    cs = S2.get('contacts_triangle_pairs', {})
    for k, lab in names.items():
        if k in cs:
            c = cs[k]
            rows.append(('Schnitt-Test %s (Dreieckspaare, größter Wert; Bild 0 = Pose: %d)' % (lab, c['frame0']), str(c.get('max_compare', '-')), str(c['max_this']),
                         'Höchstwert nicht über Runde 1', ok(c['max_this'] <= c.get('max_compare', c['max_this'])) + (
                             '' if c.get('max_increase', 0) <= 0 else '; einzelne Bilder mehr als in Runde 1: bis +%d (Bild %d), mehr in %d, weniger in %d Bildern' % (
                                 c['max_increase'], c['frame_of_max_increase'], c['frames_with_more'], c['frames_with_less']))))
    kd = S2.get('keys_vs_compare_round', {})
    kd_txt = '; '.join('`%s`: %s' % (a, ', '.join('%s (%s)' % (b, de(v, 4) if not isinstance(v, str) else v) for b, v in sorted(d.items())) if d else 'gleich')
                       for a, d in sorted(kd.items()))
    md = ['## Runde 2 (31.10.2026): Kopf auf dem Fadenkreuz gesperrt', '',
          'Entscheidung des Nutzers: Kopf auf das Fadenkreuz sperren; das Gleiten der Hände entlang der Schusslinie bleibt; der Haar-Punkt wird nicht '
          'verfolgt (Haar und Schwanz sind in Unity Federknochen); keine Referenzvideos.', '',
          'Gebaut (`build_aim_s1.py head=lock`): `J_Bip_C_Head` bekommt je Bild die lokale Drehung, die seine Weltdrehung auf der von Bild 0 (Pose V2) hält, '
          'in allen drei Achsen. Hals, Augen, Ohren, Haar und alle anderen Körper-Keys bleiben 1:1 wie in Runde 1. Runde 1 ist gesichert als '
          '`Blender/work/Aim/Yoru_Aim_s1_r1.blend`; in `Yoru_Aim_s1.blend` sind `Yoru_Aim_Idle` und `Yoru_Aim_Idle_Layer` neu gebaut, `_Face` und `_Stand` gleich. '
          'Lokal weicht der Kopf bis %s° vom Kopf aus Runde 1 ab.' % de(S2['offset_constancy_max_deg'].get('J_Bip_C_Head', 0), 2), '',
          '| Messgröße | Runde 1 | Runde 2 | Ziel | erfüllt |', '|---|---|---|---|---|']
    md += ['| %s | %s | %s | %s | %s |' % row for row in rows]
    md += ['', 'Keys gegen Runde 1: %s.' % kd_txt,
           'Körper gegen Idle v2 (alle Knochen außer Armen, Fingern, UpperChest und Head): %s°, Hüftposition %s mm, Gesicht %s; UpperChest konstant %s° '
           '(Schwankung %s°).' % (de(S2['body_vs_idle_max_deg'], 4), de(S2['hips_loc_vs_idle_max_mm'], 4), de(S2['face_vs_idle_max'], 4),
                                   de(S2['offset_upper_chest_yaw_deg'], 2), de(S2['offset_constancy_max_deg'].get('J_Bip_C_UpperChest', 0), 4)),
           'Haar liegt schon in der Pose (Bild 0) auf Schultern, Oberarmen und Büste (Dreieckspaare wie oben), ebenso im Idle v2; Haar am Gesicht und an den '
           'Ohren ist die Kopfhaut unter dem Haar. Durch den gesperrten Kopf kommt nichts Neues hinzu: Haar gegen Unterarme, Hände und Pistolen sowie Gesicht '
           'gegen Brust bleiben bei 0, die Höchstwerte sinken.',
           'Schnitt-Test: Methode der Idle-Runde 7 (Dreieckspaare per BVH-Überlappung des verformten Netzes) an %d Bildern (jedes %d. plus Atem-Extreme), '
           'Bild für Bild gegen Runde 1. Sichtbarkeit: `build_aim_s1_visdiag.py loop=1`, alle 361 Bilder, beide Runden.' % (
               S2['sample_frames']['count'], S2['sample_frames']['step']), '',
           '- Video `%s`, Standbild `%s`, Diagramm `%s` (Runde-1-Dateien bleiben)' % tuple(
               os.path.relpath(x, ROOT).replace('\\', '/') for x in (video, os.path.splitext(video)[0] + '_still_t0.png', plot)),
           '- Zahlen `Blender/work/Aim/Yoru_Aim_s1_r2_report.json`, Sichtbarkeit je Bild `Yoru_Aim_s1_r2_visloop.json`, Löser `Yoru_Aim_s1_r2_solver.json`', '']
    text = open(md_path, encoding='utf-8').read()
    cut = text.find('## Runde 2')
    if cut >= 0:
        text = text[:cut]
    text = text.rstrip('\n') + '\n\n' + '\n'.join(md)
    open(md_path, 'w', encoding='utf-8').write(text)
    print('report section Runde 2 ->', md_path, flush=True)
