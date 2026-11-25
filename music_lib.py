"""Free music library for the blocks engine (see music/library.json).
fetch(): downloads any missing tracks (run in the GitHub workflow; cached between runs).
pick(): chooses a track for the mood, never one of the last few used.
lay(): fits the track to the video (trim or loop with a crossfade, fade out) and returns stereo samples."""
import json, os, re, subprocess, sys, urllib.request, glob, pathlib
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
LIB = HERE / 'music' / 'library.json'
FILES = HERE / 'music' / 'files'
SR = 48000


def tracks(): return json.load(open(LIB))['tracks']


def fetch():
    os.makedirs(FILES, exist_ok=True); ok = 0
    for t in tracks():
        dest = FILES / f"{t['id']}.wav"
        if dest.exists(): ok += 1; continue
        try:
            html = urllib.request.urlopen(urllib.request.Request(t['page'], headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read().decode('utf8', 'ignore')
            m = re.search(r'property="og:audio"\s+content="([^"]+)"', html) or re.search(r'content="([^"]+\.(?:wav|mp3))"', html)
            if not m: print('no audio link on', t['page']); continue
            raw = FILES / f"{t['id']}.src"
            open(raw, 'wb').write(urllib.request.urlopen(urllib.request.Request(m.group(1), headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read())
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(raw), '-ar', str(SR), '-ac', '2', str(dest)], check=True); raw.unlink()
            ok += 1; print('got', t['id'])
        except Exception as e: print('failed', t['id'], e)
    print(f'{ok}/{len(tracks())} tracks ready')


def recent_ids(n=6):
    used = []
    for f in sorted(glob.glob(str(HERE / 'videos' / '*' / 'report.json')))[::-1]:
        try: tid = (json.load(open(f)).get('music') or {}).get('track')
        except Exception: tid = None
        if tid: used.append(tid)
        if len(used) >= n: break
    return used


def pick(mood, seed, want=None):
    ready = [t for t in tracks() if (FILES / f"{t['id']}.wav").exists()]
    if not ready: return None
    if want:
        for t in ready:
            if t['id'] == want: return t
    avoid = recent_ids()
    pool = [t for t in ready if mood in t['moods'] and t['id'] not in avoid] or [t for t in ready if t['id'] not in avoid] or ready
    return pool[seed % len(pool)]


def lay(t, total):
    import wave
    w = wave.open(str(FILES / f"{t['id']}.wav")); x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float32).reshape(-1, 2) / 32768; w.close()
    n = int(total * SR)
    while len(x) < n:  # loop with a 1.5 s crossfade
        cf = int(1.5 * SR); ramp = np.linspace(0, 1, cf)[:, None]
        x = np.concatenate([x[:-cf], x[-cf:] * (1 - ramp) + x[:cf] * ramp, x[cf:]])
    x = x[:n].copy(); fo = int(1.2 * SR); x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    fi = int(.04 * SR); x[:fi] *= np.linspace(0, 1, fi)[:, None]
    return x / max(1e-6, np.abs(x).max())


def credit(t): return f'Music: "{t["title"]}" by BudgetPixel AI ({t["page"]}), CC BY 4.0'


if __name__ == '__main__' and sys.argv[1:] == ['fetch']: fetch()
