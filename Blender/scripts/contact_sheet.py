"""Contact sheet of still frames:  python contact_sheet.py <dir> <sheet.png> <view> <frames, comma separated> [columns] [crop x0,y0,x1,y1]
Every picture gets its frame number in the corner.  Needs Pillow (system python, not Blender)."""
import sys, os
from PIL import Image, ImageDraw

d, out, view = sys.argv[1], sys.argv[2], sys.argv[3]
frames = [int(x) for x in sys.argv[4].split(',')]
cols = int(sys.argv[5]) if len(sys.argv) > 5 else min(len(frames), 6)
crop = tuple(int(x) for x in sys.argv[6].split(',')) if len(sys.argv) > 6 else None
ims = []
for f in frames:
    im = Image.open(os.path.join(d, '%s_%03d.png' % (view, f))).convert('RGB')
    if crop:
        im = im.crop(crop)
    ImageDraw.Draw(im).text((8, 6), 'frame %d' % f, fill=(255, 255, 255))
    ims.append(im)
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (w * cols, h * rows))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
print(sheet.size)
