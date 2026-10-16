"""Puts the blink into Yoru_Walk.blend (run it AFTER build_walk.py; build_walk.py writes a file without the blink).
usage: blender -b --factory-startup <Yoru_Walk.blend> --python build_blink.py -- <out dir ABSOLUTE> [NAME=Yoru_Walk] [SEED=247] [CYCLES=20] [FIRST=<seconds>] [PARAM=value ...]
(NAME=Yoru_Run for the run: the file is saved as Yoru_Run.blend, the blinks go to Yoru_Run_Blink.json and build_blink_Yoru_Run.log)
what it does
  1. the walk becomes endless: every f-curve of the walk action gets a Cycles modifier (key 26 == key 0, period 26 frames), so the timeline can be
     much longer than one gait cycle (CYCLES gait cycles, default 20 = 520 frames = 17.3 s, the preview loops at that length)
  2. the blinks of blink_model.py (seed SEED) are keyed on the shape key Fcl_EYE_Close of the face = the VRM clip "Blink" (one key per frame, straight lines)
  3. Yoru_Blink.json: seed, parameters, every blink, the weight of every frame, measured times  (the game reads the same model, see YoruBlink.cs)
Blink parameters of blink_model.PARAMS can be changed with PARAM=value (e.g. median_interval=2.8).
"""
import bpy, sys, os, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blink_model as bm

argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]
opts = {}
NAME = 'Yoru_Walk'                                      # base name of the blend file: it is saved as NAME + '.blend' (NAME=Yoru_Run for the run)
for a in argv[1:]:
    k, v = a.split('=')
    if k == 'NAME':
        NAME = v
        continue
    opts[k] = float(v)
SEED = int(opts.pop('SEED', 247))
CYCLES = int(opts.pop('CYCLES', 20))
FIRST = opts.pop('FIRST', None)
params = {k: v for k, v in opts.items() if k in bm.PARAMS}
unknown = [k for k in opts if k not in bm.PARAMS]
assert not unknown, 'unknown parameter(s): %s' % unknown

scene = bpy.context.scene
FPS = scene.render.fps
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
face = bpy.data.objects['Face']
sk = face.data.shape_keys
kb = sk.key_blocks['Fcl_EYE_Close']
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print('BLINK:', s)


def action_fcurves(action):
    if hasattr(action, 'fcurves'):
        return list(action.fcurves)
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


# ------------------------------------------------------------------ 1. endless walk
walk = arm.animation_data.action
rng_ = walk.frame_range
PERIOD = int(round(rng_[1] - rng_[0]))
assert rng_[0] == 0 and PERIOD >= 8, rng_
n_mod = 0
for fc in action_fcurves(walk):
    for m in list(fc.modifiers):
        if m.type == 'CYCLES':
            fc.modifiers.remove(m)
    m = fc.modifiers.new('CYCLES')
    m.mode_before = 'REPEAT'
    m.mode_after = 'REPEAT'
    n_mod += 1
# the floor under her moves back at the (slightly wobbling) ground speed: one key per frame, every cycle moves it on by the same stride
floor_mat = bpy.data.materials.get('floor')
n_floor = 0
if floor_mat and floor_mat.node_tree and floor_mat.node_tree.animation_data and floor_mat.node_tree.animation_data.action:
    for fc in action_fcurves(floor_mat.node_tree.animation_data.action):
        for m in list(fc.modifiers):
            if m.type == 'CYCLES':
                fc.modifiers.remove(m)
        m = fc.modifiers.new('CYCLES')
        m.mode_before = 'REPEAT_OFFSET'
        m.mode_after = 'REPEAT_OFFSET'
        n_floor += 1
NFR = PERIOD * CYCLES
scene.frame_start, scene.frame_end = 0, NFR - 1
T = NFR / float(FPS)
log('walk action "%s": %d f-curves are endless now (period %d frames); floor f-curves %d; timeline %d frames = %.3f s' % (walk.name, n_mod, PERIOD, n_floor, NFR, T))

# ------------------------------------------------------------------ 2. blinks -> shape key
sched = bm.schedule(SEED, T, params, first_start=FIRST)
groups = bm.schedule_groups(SEED, T, params, first_start=FIRST)
if sk.animation_data is None:
    sk.animation_data_create()
if sk.animation_data.action:
    old = sk.animation_data.action
    sk.animation_data.action = None
    bpy.data.actions.remove(old)
act = bpy.data.actions.new('Yoru_Blink')
act.use_fake_user = True
sk.animation_data.action = act
frames_w = [0.0] * NFR
for f in range(NFR):
    frames_w[f] = bm.weight(sched, f / float(FPS))
keyed = set([0, NFR - 1])
for b in sched:
    f0 = max(0, int(math.floor(b.start * FPS)) - 1)
    f1 = min(NFR - 1, int(math.ceil(b.end * FPS)) + 1)
    keyed.update(range(f0, f1 + 1))
for f in sorted(keyed):
    kb.value = frames_w[f]
    kb.keyframe_insert('value', frame=f)
n_lin = 0
for fc in action_fcurves(act):
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'
        n_lin += 1
kb.value = 0.0
log('seed %d: %d blinks in %d groups, %d keys on Fcl_EYE_Close (straight lines)' % (SEED, len(sched), len(groups), n_lin))

# ------------------------------------------------------------------ 3. check: the keyed shape key follows the model; the walk is endless; stills 0..period-1 are unaffected
worst = 0.0
for f in list(range(0, NFR, 1)):
    scene.frame_set(f)
    worst = max(worst, abs(kb.value - frames_w[f]))
log('shape key value on all %d frames follows the model to %.2e' % (NFR, worst))
head = 'J_Bip_C_Head'
worst_pos = 0.0
for f in (0, 3, 9, 17, 25):
    scene.frame_set(f)
    p0 = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones[head].head.copy()
    for c in (1, 7, CYCLES - 1):
        scene.frame_set(f + c * PERIOD)
        p1 = arm.evaluated_get(bpy.context.evaluated_depsgraph_get()).pose.bones[head].head.copy()
        worst_pos = max(worst_pos, (p1 - p0).length)
log('head position after 1, 7 and %d more gait cycles equals the first cycle to %.3f mm' % (CYCLES - 1, worst_pos * 1000.0))
first_blink_frame = min((b.start for b in sched)) * FPS
log('first blink starts at frame %.1f (frames 0..%d, which the still renders use, stay open: max weight there %.3f)' % (
    first_blink_frame, PERIOD - 1, max(frames_w[:PERIOD])))
scene.frame_set(0)

# ------------------------------------------------------------------ 4. data for the game and for the videos
meas = [bm.measure_times(b) for b in sched]
data = {'seed': SEED, 'fps': FPS, 'frames': NFR, 'seconds': T, 'gait_period_frames': PERIOD, 'shape_key': 'Fcl_EYE_Close', 'vrm_clip': 'Blink',
        'params': dict(bm.PARAMS, **params), 'first_start': FIRST,
        'groups': [[b.as_dict() for b in g] for g in groups],
        'blinks': [dict(b.as_dict(), **{'close_10_90': m['close_10_90'], 'open_90_10': m['open_90_10'], 'shut_90': m['covered_90'], 'width_50': m['width_50']})
                   for b, m in zip(sched, meas)],
        'weights_per_frame': frames_w,
        'hour_statistics': bm.stats(SEED)}
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'Yoru_Blink.json' if NAME == 'Yoru_Walk' else NAME + '_Blink.json'), 'w') as fh:
    json.dump(data, fh, indent=1)
for i, (b, m) in enumerate(zip(sched, meas)):
    log('blink %d: start %.3f s (frame %.1f)  amp %.2f  close %.3f  hold %.3f  open %.3f | 10-90%% close %.3f s, open %.3f s, width at 50%% %.3f s' % (
        i, b.start, b.start * FPS, b.amp, b.close, b.hold, b.open, m['close_10_90'], m['open_90_10'], m['width_50']))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + '.blend'))
with open(os.path.join(OUT, 'build_blink.log' if NAME == 'Yoru_Walk' else 'build_blink_%s.log' % NAME), 'w') as fh:
    fh.write('\n'.join(LOG) + '\n')
log('saved', os.path.join(OUT, NAME + '.blend'))
