"""Builds one walk variant in background Blender, renders side / back stills and makes contact sheets.
usage: python run_variant.py <name> <frames, comma separated> [KEY=VALUE ...]
Output goes to Blender/work/variants/<name>/ (never overwrites the real Yoru_Walk files).
"""
import os, subprocess, sys

BLENDER = r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
ROOT = r'C:\Users\valen\ZeroProtocol\Blender'
SCRIPTS = os.path.join(ROOT, 'scripts')
name, frames = sys.argv[1], sys.argv[2]
params = sys.argv[3:]
out = os.path.join(ROOT, 'work', 'variants', name)
os.makedirs(out, exist_ok=True)

log = open(os.path.join(out, 'build.log'), 'w')
subprocess.run([BLENDER, '-b', '--factory-startup', '--python', os.path.join(SCRIPTS, 'build_walk.py'), '--',
                os.path.join(ROOT, 'work', 'Yoru.glb'), out, 'build'] + params, stdout=log, stderr=subprocess.STDOUT, check=False)
log.close()
for line in open(os.path.join(out, 'build.log'), encoding='utf-8', errors='replace'):
    if line.startswith('[walk') and any(k in line for k in ('design', 'knee', 'arm clearance L', 'final', 'tail lift', 'planted', 'lowest', 'swing', 'WARNING', 'stride', 'DONE')):
        print(line.rstrip()[:240])
    if 'Traceback' in line or 'Error' in line:
        print(line.rstrip()[:240])
rlog = open(os.path.join(out, 'render.log'), 'w')
subprocess.run([BLENDER, '-b', '--factory-startup', os.path.join(out, 'Yoru_Walk.blend'), '--python', os.path.join(SCRIPTS, 'render_walk_stills.py'), '--',
                os.path.join(out, 'stills'), frames, 'side,back'], stdout=rlog, stderr=subprocess.STDOUT, check=False)
rlog.close()
n = len(frames.split(','))
subprocess.run([sys.executable, os.path.join(SCRIPTS, 'contact_sheet.py'), os.path.join(out, 'stills'), os.path.join(out, 'sheet_side.png'), 'side', frames, str(min(n, 5)), '80,60,540,720'], check=False)
subprocess.run([sys.executable, os.path.join(SCRIPTS, 'contact_sheet.py'), os.path.join(out, 'stills'), os.path.join(out, 'sheet_back.png'), 'back', frames, str(min(n, 5)), '80,60,540,720'], check=False)
print('variant', name, 'ready:', out)
