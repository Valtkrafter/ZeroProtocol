"""Natural blinking for Yoru. ONE model for the Blender preview and for the game (Assets/Scripts/Player/YoruBlink.cs is a line-by-line
port of this file; both read the same numbers and use the same random generator, so the same seed gives the same blinks).

What a human spontaneous blink looks like (literature: Evinger 1991, VanderWerf 2003, Kwon 2013) and what is built in here
(tuned after the user's verdict "seltener (~6 s)" and "knackiger"):
  * the upper lid closes FAST (60 ms), stays shut for a moment (15..40 ms) and opens about TWICE as slowly (1.9 .. 2.3 x the closing time, ~125 ms)
  * the lid speed is bell shaped (starts and ends soft); the opening has a quick start and a soft tail
  * the time between blinks is irregular (log-normal: median 5.2 s, never below 1.6 s, never above 10 s; mean start-to-start about 6 s) - no metronome
  * about 1 in 8 blinks is incomplete (the lid only goes down to 55..85 %), they are a bit shorter
  * about 1 in 7 blinks is a double blink: the second one starts while the lid is still opening (flutter), a little weaker
  * both eyes always close together (VRM clip "Blink" = shape key Fcl_EYE_Close, weight 0..1)

random numbers: mulberry32 (32 bit, the same code in C#), uniform in [0,1); a blink always uses the same number of draws, so a change of one
parameter does not shift the whole sequence.
usage:  python blink_model.py [seed] [seconds]      prints the schedule and the statistics
"""
import math
import sys

PARAMS = dict(
    median_interval=5.2, sigma=0.40, min_interval=1.6, max_interval=10.0,    # time from the END of one blink group to the START of the next (s)
    first_min=1.3, first_max=2.3,                                            # start of the very first blink (s)
    p_partial=0.12, partial_lo=0.55, partial_hi=0.85,
    t_close=0.060, close_spread=0.12,                                        # closing time (s), relative spread (1 sigma, limited to +-25 %)
    open_ratio_lo=1.9, open_ratio_hi=2.3,                                    # opening time = closing time * ratio
    hold_lo=0.015, hold_hi=0.040,                                            # time with the lid fully down (s)
    p_double=0.14, overlap_lo=0.45, overlap_hi=0.75, double_min_onset=0.18,  # the 2nd blink starts after this fraction of the 1st opening (but >= 0.18 s after its start)
    amp2_lo=0.80, amp2_hi=1.00,
    close_warp=0.80, open_warp=1.8,                                          # shape of the lid speed
)

DRAWS_PER_GROUP = 10


class Rng:
    """mulberry32"""

    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def next(self):
        self.s = (self.s + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.s
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0


def smoother(u):
    return u * u * u * (u * (u * 6.0 - 15.0) + 10.0)


class Blink:
    __slots__ = ('start', 'amp', 'close', 'hold', 'open')

    def __init__(self, start, amp, close, hold, open_):
        self.start, self.amp, self.close, self.hold, self.open = start, amp, close, hold, open_

    @property
    def end(self):
        return self.start + self.close + self.hold + self.open

    def lid(self, t, p=PARAMS):
        """lid closure 0 (open) .. amp (shut) at the absolute time t"""
        t -= self.start
        if t <= 0.0:
            return 0.0
        if t < self.close:
            return self.amp * smoother((t / self.close) ** p['close_warp'])
        t -= self.close
        if t < self.hold:
            return self.amp
        t -= self.hold
        if t < self.open:
            u = t / self.open
            return self.amp * (1.0 - smoother(1.0 - (1.0 - u) ** p['open_warp']))
        return 0.0

    def as_dict(self):
        return {'start': self.start, 'amp': self.amp, 'close': self.close, 'hold': self.hold, 'open': self.open, 'end': self.end}


class BlinkGenerator:
    """endless stream of blinks; next_group() returns the blinks of one group (1 blink, or 2 for a double blink)"""

    def __init__(self, seed, params=None, first_start=None):
        self.p = dict(PARAMS)
        if params:
            self.p.update(params)
        self.rng = Rng(seed)
        self.t_end = 0.0
        self.first = True
        self.first_start = first_start

    def next_group(self, interval_scale=1.0):
        p, r = self.p, self.rng
        u = [r.next() for _ in range(DRAWS_PER_GROUP)]
        z = math.sqrt(-2.0 * math.log(1.0 - u[0])) * math.cos(2.0 * math.pi * u[1])            # normal(0,1) (Box-Muller)
        if self.first:
            start = self.first_start if self.first_start is not None else p['first_min'] + u[2] * (p['first_max'] - p['first_min'])
            self.first = False
        else:
            iv = math.exp(math.log(p['median_interval']) + p['sigma'] * z) * interval_scale
            start = self.t_end + min(max(iv, p['min_interval']), p['max_interval'])
        partial = u[3] < p['p_partial']
        amp = p['partial_lo'] + u[4] * (p['partial_hi'] - p['partial_lo']) if partial else 1.0
        dur = math.sqrt(amp)                                                                      # weaker blinks are shorter
        z2 = math.sqrt(-2.0 * math.log(1.0 - u[5])) * math.cos(2.0 * math.pi * u[6])
        close = p['t_close'] * (1.0 + min(max(p['close_spread'] * z2, -0.25), 0.25)) * dur
        opn = close * (p['open_ratio_lo'] + u[7] * (p['open_ratio_hi'] - p['open_ratio_lo']))
        hold = (p['hold_lo'] + u[8] * (p['hold_hi'] - p['hold_lo'])) * (1.0 if not partial else 0.3)
        b1 = Blink(start, amp, close, hold, opn)
        group = [b1]
        if u[9] < p['p_double']:
            v = r.next(), r.next()
            s2 = max(start + close + hold + opn * (p['overlap_lo'] + v[0] * (p['overlap_hi'] - p['overlap_lo'])), start + p['double_min_onset'])
            a2 = amp * (p['amp2_lo'] + v[1] * (p['amp2_hi'] - p['amp2_lo']))
            group.append(Blink(s2, a2, close * 0.95, hold * 0.6, opn * 0.9))
        else:
            r.next()
            r.next()
        self.t_end = max(b.end for b in group)
        return group


def schedule_groups(seed, seconds, params=None, margin_end=0.5, first_start=None):
    """the blink groups (1 or 2 blinks each) that start and end inside [0, seconds - margin_end] (a group that would not fit is dropped, then it ends)"""
    gen = BlinkGenerator(seed, params, first_start)
    out = []
    while True:
        g = gen.next_group()
        if max(b.end for b in g) > seconds - margin_end:
            break
        out.append(g)
    return out


def schedule(seed, seconds, params=None, margin_end=0.5, first_start=None):
    return [b for g in schedule_groups(seed, seconds, params, margin_end, first_start) for b in g]


def weight(blinks, t):
    """lid closure at the time t for a list of blinks (the lid that is lowest wins when two blinks overlap)"""
    w = 0.0
    for b in blinks:
        if b.start - 1e-9 <= t <= b.end:
            w = max(w, b.lid(t))
    return w


def stats(seed, seconds=3600.0):
    groups = schedule_groups(seed, seconds)
    bl = [b for g in groups for b in g]
    starts = [b.start for b in bl]
    iv = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
    gstarts = [g[0].start for g in groups]
    giv = [gstarts[i + 1] - gstarts[i] for i in range(len(gstarts) - 1)]
    firsts = [g[0] for g in groups]
    return {'n': len(bl), 'groups': len(groups), 'per_minute': len(bl) / seconds * 60.0,
            'onset_interval_mean': sum(iv) / len(iv), 'onset_interval_min': min(iv), 'onset_interval_max': max(iv),
            'group_interval_mean': sum(giv) / len(giv), 'group_interval_min': min(giv), 'group_interval_max': max(giv),
            'partial_share': sum(1 for b in firsts if b.amp < 0.999) / len(groups), 'double_share': sum(1 for g in groups if len(g) == 2) / len(groups),
            'close_mean': sum(b.close for b in firsts if b.amp > 0.999) / max(1, sum(1 for b in firsts if b.amp > 0.999)),
            'open_mean': sum(b.open for b in firsts if b.amp > 0.999) / max(1, sum(1 for b in firsts if b.amp > 0.999)),
            'hold_mean': sum(b.hold for b in firsts if b.amp > 0.999) / max(1, sum(1 for b in firsts if b.amp > 0.999))}


def measure_times(blink, p=PARAMS, dt=0.0005):
    """10..90 % times of the closing and the opening and the time with the lid above 90 % of its own height (from the sampled curve)"""
    ts = [i * dt for i in range(int((blink.end + 0.1) / dt))]
    ws = [blink.lid(blink.start + t) for t in ts]
    a = blink.amp

    def first(pred):
        for t, w in zip(ts, ws):
            if pred(w):
                return t
        return None

    def last(pred):
        r = None
        for t, w in zip(ts, ws):
            if pred(w):
                r = t
        return r

    c10, c90 = first(lambda w: w >= 0.1 * a), first(lambda w: w >= 0.9 * a)
    o90, o10 = last(lambda w: w >= 0.9 * a), last(lambda w: w >= 0.1 * a)
    h50a, h50b = first(lambda w: w >= 0.5 * a), last(lambda w: w >= 0.5 * a)
    return {'close_10_90': c90 - c10, 'open_90_10': o10 - o90, 'covered_90': o90 - c90, 'width_50': h50b - h50a, 'total': o10 - c10}


if __name__ == '__main__':
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 13.867
    bl = schedule(seed, secs)
    print('seed %d, %.2f s: %d blinks' % (seed, secs, len(bl)))
    for i, b in enumerate(bl):
        m = measure_times(b)
        print('  %2d  start %6.3f s (frame %6.1f)  amp %.2f  close %.3f  hold %.3f  open %.3f   -> 10-90%% close %.3f  open %.3f  shut(>=90%%) %.3f  width50 %.3f' % (
            i, b.start, b.start * 30.0, b.amp, b.close, b.hold, b.open, m['close_10_90'], m['open_90_10'], m['covered_90'], m['width_50']))
    s = stats(seed)
    print('one hour with this seed: %(n)d blinks in %(groups)d groups = %(per_minute).1f blinks per minute; start-to-start of the groups mean %(group_interval_mean).2f s '
          '(min %(group_interval_min).2f, max %(group_interval_max).2f); incomplete %(partial_share).0f%% of the groups, double %(double_share).0f%%; '
          'full blinks: close %(close_mean).3f s, hold %(hold_mean).3f s, open %(open_mean).3f s' % dict(s, partial_share=s['partial_share'] * 100, double_share=s['double_share'] * 100))
