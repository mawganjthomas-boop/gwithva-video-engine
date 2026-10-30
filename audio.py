"""Gwithva video engine: sound design + original music.
Everything is synthesised here (no stock audio, no licences). The music is seeded,
so every video gets its own track while keeping the same warm, premium feel."""
import numpy as np, wave
from scipy.signal import butter, lfilter

SR = 48000


class Mix:
    def __init__(self, dur, seed):
        self.N = int(SR * dur); self.L = np.zeros(self.N); self.R = np.zeros(self.N)
        self.rng = np.random.default_rng(seed)

    def add(self, sig, t0, g=1.0, pan=0.0):
        i = int(t0 * SR)
        if i >= self.N or len(sig) == 0: return
        if i < 0: sig = sig[-i:]; i = 0
        sig = sig[: self.N - i]
        self.L[i:i + len(sig)] += sig * g * np.sqrt(.5 * (1 - pan))
        self.R[i:i + len(sig)] += sig * g * np.sqrt(.5 * (1 + pan))


def filt(x, f, kind='low', o=2):
    b, a = butter(o, np.array(f) / (SR / 2), kind); return lfilter(b, a, x)

def env(n, a, d, c=5):
    t = np.arange(n) / SR; return np.minimum(1, t / max(a, 1e-4)) * np.exp(-c * np.maximum(0, t - a) / max(d, 1e-4))

def sine(f, dur, a=.005, d=.3, c=5, harm=()):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.sin(2 * np.pi * f * t)
    for k, g in harm: s += g * np.sin(2 * np.pi * f * k * t)
    return s * env(n, a, d, c)

def bell(f, dur=1.4): return sine(f, dur, .002, dur * .4, 3, harm=((2.76, .25), (5.4, .08)))

def noise(rng, dur): return rng.standard_normal(int(dur * SR))

def tick(rng, f=2200, dur=.05):
    n = int(dur * SR); return filt(rng.standard_normal(n) * env(n, .0005, dur / 3, 6), [f * .6, f * 1.4], 'band') * .9

def whoosh(rng, dur=.5, lo=300, hi=4000, rev=False):
    n = int(dur * SR); x = rng.standard_normal(n); t = np.linspace(0, 1, n); out = np.zeros(n); ch = int(.02 * SR)
    for k in range(0, n, ch):
        p = k / n; f = lo * (hi / lo) ** (p if not rev else 1 - p)
        seg = filt(x[max(0, k - ch):k + ch], [max(60, f * .5), min(20000, f * 1.5)], 'band')
        out[k:k + ch] = seg[-len(out[k:k + ch]):]
    e = np.sin(np.pi * t) ** 1.5
    if rev: e = t ** 2.5 * (1 - np.clip((t - .95) / .05, 0, 1))
    return out * e

def thud(f0=90, dur=.5):
    n = int(dur * SR); t = np.arange(n) / SR; f = f0 * np.exp(-t * 6) + 40
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .003, dur * .5, 4)

def bloop(f0, f1, dur=.16):
    n = int(dur * SR); f = np.linspace(f0, f1, n); return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, dur * .5, 4)

def pad(fs, dur, a=1.0, r=1.2, lfo=.15, cut=2200):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t + i) + .35 * np.sin(2 * np.pi * f * 1.004 * t) for i, f in enumerate(fs)) / len(fs)
    s *= .85 + .15 * np.sin(2 * np.pi * lfo * t)
    return filt(s * np.minimum(1, t / a) * np.minimum(1, np.maximum(0, dur - t) / r), cut)

def kick():
    n = int(.35 * SR); t = np.arange(n) / SR; f = 45 + 110 * np.exp(-t * 30)
    return np.tanh(2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .002, .25, 4))

def clap(rng):
    n = int(.25 * SR); return filt(rng.standard_normal(n), [900, 3500], 'band') * env(n, .003, .09, 5)

def hat(rng, o=False):
    n = int((.18 if o else .05) * SR); return filt(rng.standard_normal(n), 7000, 'high') * env(n, .001, (.12 if o else .025), 5)

def pluck(f, dur=.5):
    n = int(dur * SR); t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (3 + k * 2.5)) for k in range(1, 7)) * env(n, .003, dur, 3)

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.sin(2 * np.pi * f * t) + .25 * np.sin(2 * np.pi * 2 * f * t)
    return np.tanh(1.5 * s) * np.minimum(1, t / .01) * np.minimum(1, np.maximum(0, dur - t) / .03)

n2f = lambda m: 440 * 2 ** ((m - 69) / 12)

# Moods: tempo + chord progression (midi roots + voicings). All major-leaning, calm-confident.
MOODS = {
    'warm':    dict(bpm=(98, 106),  prog=[[0, 7, 11, 16], [-3, 4, 7, 12], [-7, 0, 4, 9], [-5, 2, 7, 11]]),   # Imaj7 vi7 IVmaj7 V6
    'bright':  dict(bpm=(108, 116), prog=[[0, 7, 12, 16], [-5, 2, 7, 11], [-3, 4, 9, 12], [-7, 0, 5, 9]]),   # I V vi IV
    'driving': dict(bpm=(112, 120), prog=[[-3, 4, 9, 12], [-7, 0, 5, 9], [0, 7, 12, 16], [-5, 2, 7, 11]]),   # vi IV I V
}


def render_audio(meta, spec, out_path):
    seed = int(spec.get('seed', 7)) & 0xffffffff
    mood = (spec.get('music') or {}).get('mood', 'warm')
    M = MOODS.get(mood, MOODS['warm'])
    rng = np.random.default_rng(seed)
    total = meta['total']; mx = Mix(total, seed); r = mx.rng
    tl = meta['timeline']; get = lambda typ: [x for x in tl if x['type'] == typ]

    # ---------------- sound effects from on-screen cues ----------------
    for c in meta['cues']:
        t, ty = c['t'], c['type']
        if ty == 'hum':
            n = int(2.2 * SR); mx.add(thud(55, 2.2) * np.linspace(0, 1, n) ** 2, t, .22)
        elif ty == 'tick': mx.add(tick(r, 1800 + r.uniform(0, 600), .04), t, .16, r.uniform(-.4, .4))
        elif ty == 'thud': mx.add(thud(95, .7), t, .9); mx.add(filt(noise(r, .25), 1500) * env(int(.25 * SR), .002, .08, 5), t, .3)
        elif ty == 'swish': mx.add(whoosh(r, .45, 800, 6000), t, .1)
        elif ty in ('whoosh', 'swipe'): mx.add(whoosh(r, .5 if ty == 'whoosh' else .45, 250, 5000), t - .05, .3 if ty == 'whoosh' else .2)
        elif ty == 'drone':
            d = c.get('dur', 4.9); n = int(d * SR); tt = np.arange(n) / SR
            dr = np.sign(np.sin(2 * np.pi * 98 * tt)) * .5 + np.sin(2 * np.pi * 103.6 * tt) + np.sin(2 * np.pi * 146.8 * tt) * .5
            dr = filt(dr, 500) * np.linspace(.15, 1, n) ** 1.5 * (1 + .3 * np.sin(2 * np.pi * (2 + tt * 1.2) * tt))
            dr[-int(.25 * SR):] *= np.linspace(1, 0, int(.25 * SR)); mx.add(dr, t, .09)
            k, step = t + .15, .5
            while k < t + d - .4: mx.add(tick(r, 3200, .03), k, .09, .4); k += step; step = max(.16, step * .9)
        elif ty == 'blip': mx.add(sine(700 + 90 * (c.get('i', 0) % 5), .18, .002, .06, 5, harm=((2, .3),)), t, .15, -.5 + (c.get('i', 0) % 4) * .33)
        elif ty == 'clash': mx.add(sine(196, .25, .003, .12, 4, harm=((2, .4),)), t, .26); mx.add(sine(185, .25, .003, .12, 4, harm=((2, .4),)), t + .12, .26)
        elif ty == 'notif':
            k = c.get('kind', 'msg'); p = -.6 + (c.get('i', 0) % 5) * .3
            if k == 'call':
                n = int(.38 * SR); tt = np.arange(n) / SR
                mx.add(np.sin(2 * np.pi * 165 * tt) * (.5 + .5 * np.sign(np.sin(2 * np.pi * 14 * tt))) * env(n, .01, .3, 1.5), t, .18, p)
            elif k == 'bell': mx.add(bell(1046, .6), t, .11, p)
            elif k == 'cal': mx.add(np.concatenate([sine(1568, .08, .002, .04, 4), sine(1175, .2, .002, .1, 4)]), t, .13, p)
            elif k in ('note', 'email'): mx.add(sine(880, .25, .002, .1, 4), t, .11, p)
            else: mx.add(np.concatenate([sine(1318, .09, .002, .05, 4), sine(1760, .25, .002, .12, 4)]), t, .15, p)
        elif ty == 'thump': mx.add(thud(75, .35), t, .33)
        elif ty == 'suck': mx.add(whoosh(r, .55, 200, 3000, rev=True), t - .1, .38)
        elif ty == 'boom': mx.add(thud(60, 1.2), t, .5); mx.add(whoosh(r, 1.2, 2000, 9000), t, .05)
        elif ty == 'sparkle': mx.add(bell(1046, 2.0), t, .09, -.2)
        elif ty == 'bell2': mx.add(bell(1568, 2.0), t, .06, .2)
        elif ty == 'flick': mx.add(whoosh(r, .25, 1500, 6000), t, .06, r.uniform(-.3, .3))
        elif ty == 'shutter': mx.add(tick(r, 4200, .03), t, .4); mx.add(filt(noise(r, .12), 5000) * env(int(.12 * SR), .001, .05, 5), t + .03, .22)
        elif ty == 'tap': mx.add(tick(r, 2600, .03), t, .45)
        elif ty == 'success': mx.add(np.concatenate([sine(1046, .1, .002, .05, 4), sine(1568, .45, .002, .2, 4)]), t, .24)
        elif ty == 'pop': mx.add(sine(784, .2, .002, .08, 5, harm=((2, .3),)), t, .14)
        elif ty == 'bloop': mx.add(bloop(500, 900), t, .3, -.3)
        elif ty == 'key': mx.add(tick(r, 2800 + r.uniform(-300, 300), .025), t + r.uniform(-.008, .008), .17, .1)
        elif ty == 'send': mx.add(whoosh(r, .25, 1000, 8000), t, .1, .3); mx.add(bloop(700, 1100), t + .1, .26, .3)
        elif ty == 'note1': mx.add(sine(196, 1.6, .004, .7, 3, harm=((2, .35), (3, .12))), t, .28, -.1)
        elif ty == 'note2': mx.add(sine(261.6, 1.6, .004, .7, 3, harm=((2, .35), (3, .12))), t, .28, .1)
        elif ty == 'shimmer': mx.add(whoosh(r, .8, 3000, 10000), t, .04)
        elif ty == 'chimes':
            for i, f in enumerate([1046.5, 1318.5, 1568.0, 2093.0]): mx.add(bell(f, 1.6), t + i * .09, .08, -.3 + i * .2)
    sfx = np.stack([mx.L, mx.R], 1)

    # ---------------- music ----------------
    mu = Mix(total, seed + 1); r2 = mu.rng
    bpm = r2.uniform(*M['bpm']); B = 60 / bpm; bar = 4 * B
    key = int(r2.choice([0, 2, -3, 5, -2]))  # transpose
    prog = M['prog']
    root = 48 + key
    groove_start = (get('reveal') or get('appgroup') or [{'start': 3.4}])[0]['start'] + (.3 if get('reveal') else 0)
    payoff = (get('payoff') or [None])[0]; cta = (get('cta') or [None])[0]
    groove_end = payoff['start'] - .05 if payoff else (cta['start'] if cta else total - 2)
    pile = (get('pileup') or [None])[0]
    # intro pulse
    for k in range(int(groove_start / B)):
        t = k * B; mu.add(bass(n2f(root - 12), B * .5) * np.linspace(.3, 1, int(B * .5 * SR)), t, .09 * (.4 + .6 * t / max(1, groove_start)))
    if pile:  # tension under the admin pile-up
        t = pile['start'] + .1; k = 0
        while t < groove_start - .2:
            m = root - 12 + (0 if (k // 8) % 2 == 0 else 1)
            mu.add(filt(bass(n2f(m), B * .45), 300 + 600 * (t - pile['start']) / 5), t, .19)
            if k % 2: mu.add(hat(r2), t, .05, .3)
            if k % 4 == 0: mu.add(kick(), t, .24)
            t += B / 2; k += 1
        mu.add(pad([n2f(root + m) for m in [0, 3, 7, 10]], groove_start - pile['start'], 1.5, .3), pile['start'], .08)
        mu.add(filt(noise(r2, .55), 4000, 'high') * np.linspace(0, 1, int(.55 * SR)) ** 3, groove_start - .55, .08)
    t = groove_start; bi = 0
    while t < groove_end:
        ch = prog[bi % 4]
        mu.add(pad([n2f(root + 12 + m) for m in ch], min(bar, groove_end - t + .3), .05, .2), t, .07)
        for q in range(8):
            tq = t + q * B / 2
            if tq >= groove_end: break
            if q in (0, 3, 5): mu.add(bass(n2f(root - 12 + ch[0]), B * .42), tq, .2)
            if q % 2: mu.add(hat(r2, q == 7), tq, .045, .35)
            if q in (0, 4): mu.add(kick(), tq, .3)
            if q in (2, 6) and bi >= 1: mu.add(clap(r2), tq, .06, -.1)
            if q in (1, 2, 4, 6, 7): mu.add(pluck(n2f(root + 24 + ch[(q * 3) % 4]), .4), tq, .055, -.4 + .1 * q)
        t += bar; bi += 1
    if payoff:
        p0 = payoff['start']
        mu.add(pad([n2f(root + 12 + m) for m in prog[2]], 1.2, .05, .3), p0 + .1, .1)
        mu.add(pad([n2f(root + 12 + m) for m in prog[3]], 1.4, .05, .4), p0 + 1.05, .1)
        for tq, m in [(p0 + .35, prog[2][0]), (p0 + 1.05, prog[3][0])]: mu.add(kick(), tq, .3); mu.add(bass(n2f(root - 12 + m), .9), tq, .2)
    if cta:
        c0 = cta['start']
        mu.add(pad([n2f(root + 12 + m) for m in prog[0]] + [n2f(root + 28)], total - c0, .05, 1.4), c0, .08)
        mu.add(bass(n2f(root - 12), 1.2), c0, .22); mu.add(kick(), c0, .3)
        for i, m in enumerate([24, 28, 31, 36]): mu.add(pluck(n2f(root + m), 1.2), c0 + .95 + i * .09, .07, -.3 + i * .2)
    mus = np.stack([mu.L, mu.R], 1)
    if np.abs(mus).max() > 0: mus = mus / np.abs(mus).max() * .55
    if np.abs(sfx).max() > 0: sfx = sfx / np.abs(sfx).max() * .85
    mix = sfx * .8 + mus
    fo = int(.7 * SR); mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
    mix = np.tanh(mix * 1.3) / np.tanh(1.3); mix *= .89 / max(1e-6, np.abs(mix).max())
    w = wave.open(out_path, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes()); w.close()
    return {'bpm': round(bpm, 1), 'mood': mood, 'key_shift': key}
