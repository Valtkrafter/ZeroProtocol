"""Picture sheet of the face expressions (build_idle_v2_face.py render): columns Neutral, A, B, C; rows: close-up from the front (85 mm),
close-up three-quarter (85 mm), and the normal idle still 'vorn schräg' at its ORIGINAL pixel size (what reaches the player from a normal
distance).  Optionally also a finding picture of the eyes.
usage: python build_idle_v2_face_sheet.py <faces dir with N/ A/ B/ C/> <out sheet png> [eye close-up png] [out eye finding png]
Needs Pillow (system python)."""
import sys, os
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
eye_src = sys.argv[3] if len(sys.argv) > 3 else None
eye_out = sys.argv[4] if len(sys.argv) > 4 else None
KEYS = ('N', 'A', 'B', 'C')
HEAD = {'N': ('Neutral (jetzt)', 'alle Ausdruck-Keys 0', ''),
        'A': ('A  ruhig-selbstsicher', 'Oberlider leicht gesenkt,', 'kleines geschlossenes Lächeln'),
        'B': ('B  kühl-wachsam', 'Augen fokussiert schmaler,', 'Mund gerade, Ohren nach vorn'),
        'C': ('C  sanft', 'Augen weich,', 'wärmeres geschlossenes Lächeln')}
ROWS = (('face_front', 'Nahaufnahme vorn (85 mm)'), ('face_34', 'Dreiviertel vorn (85 mm)'), ('front34', 'Idle-Bild vorn schräg, Originalgröße'))


def font(size, bold=False):
    for n in (('arialbd.ttf',) if bold else ('arial.ttf',)):
        p = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', n)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


F_H, F_S, F_R, F_T = font(22, True), font(15), font(16, True), font(15)
CW, CH = 320, 320
LEFT, TOP = 34, 104
sheet = Image.new('RGB', (LEFT + CW * 4, TOP + CH * 3), (22, 24, 29))
d = ImageDraw.Draw(sheet)
d.text((10, 8), 'Yoru Idle v2, Runde 4: Gesichtsausdruck (nur Gesicht, Körper unverändert; Farbdarstellung AgX mit mehr Kontrast)',
       font=F_T, fill=(200, 205, 215))
for ci, k in enumerate(KEYS):
    x0 = LEFT + ci * CW
    t, s1, s2 = HEAD[k]
    d.text((x0 + 10, 36), t, font=F_H, fill=(255, 226, 120))
    d.text((x0 + 10, 64), s1, font=F_S, fill=(215, 218, 225))
    d.text((x0 + 10, 82), s2, font=F_S, fill=(215, 218, 225))
    for ri, (view, _) in enumerate(ROWS):
        im = Image.open(os.path.join(src, k, view + '.png')).convert('RGB')
        y0 = TOP + ri * CH
        if view in ('face_front', 'face_34'):
            im = im.crop((110, 100, 490, 480)).resize((CW, CH), Image.LANCZOS)
            sheet.paste(im, (x0, y0))
        else:
            cell = Image.new('RGB', (CW, CH), (40, 44, 52))
            crop = im.crop((160, 40, 160 + CW, 40 + CH))           # 1:1, no scaling: the size she has in the idle still
            cell.paste(crop, (0, 0))
            sheet.paste(cell, (x0, y0))
for ri, (_, lab) in enumerate(ROWS):
    tw = int(d.textlength(lab, font=F_R))
    tmp = Image.new('RGB', (tw + 8, 24), (22, 24, 29))
    ImageDraw.Draw(tmp).text((4, 1), lab, font=F_R, fill=(200, 205, 215))
    tmp = tmp.rotate(90, expand=True)
    sheet.paste(tmp, (5, TOP + ri * CH + CH // 2 - tmp.size[1] // 2))
for ci in range(1, 4):
    d.line([(LEFT + ci * CW, 30), (LEFT + ci * CW, sheet.height)], fill=(22, 24, 29), width=3)
for ri in range(1, 3):
    d.line([(0, TOP + ri * CH), (sheet.width, TOP + ri * CH)], fill=(22, 24, 29), width=3)
sheet.save(out)
print('sheet', out, sheet.size)

if eye_src and eye_out:
    eye = Image.open(eye_src).convert('RGB')                       # 900 x 450 close-up of both eyes (200 mm)
    far = Image.open(os.path.join(src, 'N', 'front34.png')).convert('RGB').crop((250, 95, 340, 165)).resize((360, 280), Image.NEAREST)
    W = eye.width + far.width + 30
    pic = Image.new('RGB', (W, eye.height + 120), (22, 24, 29))
    pic.paste(eye, (0, 70))
    pic.paste(far, (eye.width + 30, 70))
    dd = ImageDraw.Draw(pic)
    dd.text((10, 8), 'Befund Augen (Modell, nicht geändert): Glanzlichter sind da (weiße Punkte und Sternchen), Pupille als Katzenschlitz,', font=F_T, fill=(255, 226, 120))
    dd.text((10, 30), 'aber die Iris ist sehr hell (fast weiß-lila) und setzt sich kaum vom Augenweiß ab. Rechts: Augen im Idle-Bild, 4-fach vergrößert.', font=F_T, fill=(255, 226, 120))
    dd.text((10, eye.height + 80), 'Links: beide Augen aus 0,85 m (200 mm). Ergebnis: aus normaler Entfernung wirkt der Blick leer; eine dunklere oder stärker gesättigte Iris wäre ein Eingriff ins Modell.', font=F_S, fill=(215, 218, 225))
    pic.save(eye_out)
    print('eyes', eye_out, pic.size)
