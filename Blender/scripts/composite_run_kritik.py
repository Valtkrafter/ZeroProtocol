"""Puts the overlay pictures B_*.png over the character pictures A_*.png (render_run_kritik.py) and writes <name>.png plus a contact sheet.
usage: python composite_run_kritik.py <dir with A_*.png and B_*.png> [sheet name]"""
import glob, os, sys
from PIL import Image

src = sys.argv[1]
sheet_name = sys.argv[2] if len(sys.argv) > 2 else 'kritik_uebersicht.png'
names = sorted(os.path.basename(p)[2:-4] for p in glob.glob(os.path.join(src, 'A_*.png')))
done = []
for n in names:
    pb = os.path.join(src, 'B_%s.png' % n)
    if not os.path.exists(pb):
        continue
    a = Image.open(os.path.join(src, 'A_%s.png' % n)).convert('RGBA')
    b = Image.open(pb).convert('RGBA')
    im = Image.alpha_composite(a, b).convert('RGB')
    out = os.path.join(src, '%s.png' % n)
    im.save(out)
    done.append((n, im))
    print('wrote', out)
if done:
    cols = 3
    w, h = 800, 450
    rows = (len(done) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w, rows * h), (20, 22, 28))
    for i, (n, im) in enumerate(done):
        sheet.paste(im.resize((w, h), Image.LANCZOS), ((i % cols) * w, (i // cols) * h))
    sheet.save(os.path.join(src, sheet_name))
    print('wrote', os.path.join(src, sheet_name))
