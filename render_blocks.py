"""Gwithva video engine v2 (building blocks): storyboard JSON in -> finished MP4s out.
Called by render.py when the storyboard has "engine": "blocks".
Writes: video.mp4 (9:16), plus video_4x5.mp4 / video_1x1.mp4 crops and video_hook2.mp4 ... when asked,
cover.jpg, sheet.jpg (contact sheet for QC), report.json.

Voiceover: free Piper voices (they run inside GitHub Actions, see voices/). Each line is spoken in a scene,
characters' mouths move with the voice, and captions are burned in. Music is ducked under the voice."""
import json, os, re, shutil, subprocess, sys, pathlib, urllib.request, wave, hashlib
import numpy as np
from playwright.sync_api import sync_playwright
from validate import validate_blocks
from audio import render_audio, SR

HERE = pathlib.Path(__file__).resolve().parent
FPS = 30
TR = .35
VOICE_DIR = HERE / 'voices'
# Piper voice per character (all free, UK English). The narrator defaults to Jenny.
VOICES = {'jenny': 'en_GB-jenny_dioco-medium', 'alba': 'en_GB-alba-medium', 'alan': 'en_GB-alan-medium',
          'northern': 'en_GB-northern_english_male-medium', 'cori': 'en_GB-cori-medium'}
CAST_VOICE = {'kerra': 'jenny', 'amira': 'alba', 'jago': 'northern', 'dev': 'alan', 'tamsin': 'cori', 'ollie': 'alan', 'grace': 'alba'}


def scene_starts(spec):
    t, out = 0.0, []
    for i, s in enumerate(spec['scenes']):
        tr = 'cut' if i == 0 else s.get('transition', 'slide')
        start = 0.0 if i == 0 else (t if tr == 'cut' else t - TR)
        out.append(start); t = start + float(s.get('dur') or 2.5)
    return out


def fetch_media(spec, work):
    """Download photos and clips; turn clips into numbered JPEG frames (headless Chromium can't play H.264)."""
    os.makedirs(work, exist_ok=True); probs = []
    for i, s in enumerate(spec['scenes']):
        for b in s.get('blocks') or []:
            if b.get('kind') != 'image': continue
            src = b.get('src') or ''
            if not src or src.startswith('screen:'): continue
            ext = (re.search(r'\.(jpe?g|png|webp|mp4|mov|m4v|webm)(\?|$)', src, re.I) or [None, 'jpg'])[1].lower()
            local = os.path.join(work, hashlib.md5(src.encode()).hexdigest()[:10] + '.' + ext)
            try:
                if src.startswith('http'):
                    if not os.path.exists(local):
                        req = urllib.request.Request(src, headers={'User-Agent': 'gwithva-video-engine'})
                        open(local, 'wb').write(urllib.request.urlopen(req, timeout=60).read())
                else: local = str((HERE / src).resolve())
            except Exception as e:
                probs.append(f'scene {i + 1}: could not download {src[:80]} ({e})'); continue
            if ext in ('mp4', 'mov', 'm4v', 'webm') or b.get('clip'):
                d = local + '_frames'; os.makedirs(d, exist_ok=True)
                ss = float((b.get('clip') or {}).get('start') or 0); du = float(s.get('dur') or 3) + 1
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(ss), '-t', str(du), '-i', local, '-vf',
                                f'fps={FPS},scale=1080:-2', '-q:v', '3', f'{d}/f_%04d.jpg'], check=True)
                b['frames'] = {'dir': pathlib.Path(d).as_uri(), 'n': len(os.listdir(d))}
            else:
                b['src'] = pathlib.Path(local).as_uri()
    return probs


def synth(text, voice, path):
    """Piper TTS to a wav file. Returns (samples at SR mono float32, duration) or None if Piper isn't available."""
    model = VOICE_DIR / f'{VOICES.get(voice, VOICES["jenny"])}.onnx'
    if not model.exists(): return None
    try:
        from piper import PiperVoice
        v = PiperVoice.load(str(model))
        with wave.open(path, 'wb') as wf:
            if hasattr(v, 'synthesize_wav'): v.synthesize_wav(text, wf)
            else: v.synthesize(text, wf)
    except Exception:
        r = subprocess.run([sys.executable, '-m', 'piper', '-m', str(model), '-f', path], input=text.encode(), capture_output=True)
        if r.returncode: return None
    w = wave.open(path); n = w.getnframes(); sr = w.getframerate()
    x = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float32) / 32768; w.close()
    if w.getnchannels() == 2: x = x.reshape(-1, 2).mean(1)
    if sr != SR: x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    return x, len(x) / SR


def envelope(x):
    hop = SR // FPS; n = len(x) // hop
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) for i in range(n)]) if n else np.zeros(0)
    if e.size and e.max() > 0: e = np.clip(e / (np.percentile(e, 95) + 1e-6), 0, 1)
    return [round(float(v), 3) for v in e]


def build_voice(spec, work, probs):
    """Synthesise every voice line, stretch scenes that are too short for their lines, and return the timing."""
    vs = spec.get('voice') or {}
    lines = vs.get('lines') or []
    if not lines: return None, None
    narrator = vs.get('narrator', 'jenny')
    speakers = {b.get('id'): b.get('who') for s in spec['scenes'] for b in s.get('blocks') or [] if b.get('kind') == 'character' and b.get('id')}
    audio, real = [], True
    for k, ln in enumerate(lines):
        sp = ln.get('speaker', 'narrator')
        voice = ln.get('voice') or (CAST_VOICE.get(speakers.get(sp), 'jenny') if sp != 'narrator' else narrator)
        r = synth(ln['text'], voice, os.path.join(work, f'line{k}.wav'))
        if r is None:  # no voice models here (e.g. a local test): timed placeholder so captions and lip-sync still work
            real = False; dur = max(.8, len(ln['text'].split()) * .36)
            tt = np.arange(int(dur * SR)) / SR; x = (np.sin(2 * np.pi * 3.2 * tt) ** 2 * .3).astype(np.float32)
        else: x, dur = r
        audio.append((x, dur))
    # make each scene long enough for the lines spoken in it
    for _ in range(3):
        starts = scene_starts(spec); changed = False
        for k, ln in enumerate(lines):
            si = ln['scene'] - 1; s = spec['scenes'][si]
            need = float(ln.get('at') or 0) + audio[k][1] + .25
            if need > float(s.get('dur') or 2.5): s['dur'] = round(need, 2); changed = True
        if not changed: break
    starts = scene_starts(spec); out = []
    for k, ln in enumerate(lines):
        st = starts[ln['scene'] - 1] + float(ln.get('at') or 0)
        out.append({'text': ln['text'], 'speaker': ln.get('speaker', 'narrator'), 'start': round(st, 3), 'end': round(st + audio[k][1], 3),
                    'env': envelope(audio[k][0]), 'caption': ln.get('caption', True)})
    if not real: probs.append('note: voice models not installed here, so the voiceover is a silent placeholder (fine for a layout test)')
    return {'lines': out}, (audio, real)


def mix_voice(music_wav, voice, audio, out_wav, total):
    w = wave.open(music_wav); n = w.getnframes(); m = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float32).reshape(-1, 2) / 32768; w.close()
    v = np.zeros(len(m), np.float32)
    if voice and audio and audio[1]:
        for ln, (x, _) in zip(voice['lines'], audio[0]):
            i = int(ln['start'] * SR); j = min(len(v), i + len(x)); v[i:j] += x[:j - i]
    duck = np.ones(len(m), np.float32)
    if np.abs(v).max() > 0:
        env = np.convolve(np.abs(v), np.ones(int(.12 * SR)) / int(.12 * SR), 'same')
        duck = 1 - .6 * np.clip(env / (env.max() * .25 + 1e-6), 0, 1)
        v = v / np.abs(v).max() * .9
    mix = m * duck[:, None] + v[:, None]
    mix *= .95 / max(1e-6, np.abs(mix).max())
    w = wave.open(out_wav, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes()); w.close()


def render_one(pg, spec, voice, out, name, want_sheet):
    meta = pg.evaluate('([s, v]) => init(s, v)', [spec, voice])
    if meta['problems']: return meta, meta['problems']
    n = int(meta['total'] * FPS)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'mjpeg', '-i', '-',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                           f'{out}/{name}_silent.mp4'], stdin=subprocess.PIPE)
    sheet_ts = []
    if want_sheet:  # QC frames: one late frame per scene (fully built), first second only once
        for x in meta['timeline']: sheet_ts.append(round(x['start'] + max(.6, x['dur'] * .8), 2))
        sheet_ts = sorted(set(sheet_ts))[:12]
        while len(sheet_ts) < 12: sheet_ts.append(round(meta['total'] * (len(sheet_ts) + .5) / 13, 2)); sheet_ts = sorted(set(sheet_ts))
    cover_t = min(meta['total'] - 1, 1.6)
    for i in range(n):
        t = i / FPS
        pg.evaluate(f'setTime({t})')
        jpg = pg.screenshot(type='jpeg', quality=94)
        ff.stdin.write(jpg)
        if want_sheet:
            if abs(t - cover_t) < .5 / FPS: open(f'{out}/cover.jpg', 'wb').write(jpg)
            for k, st in enumerate(sheet_ts):
                if abs(t - st) < .5 / FPS: open(f'{out}/sheet_{k:02d}.jpg', 'wb').write(jpg)
    ff.stdin.close(); ff.wait()
    return meta, []


def finish_audio(meta, spec, voice, vaudio, out, name):
    render_audio(meta, spec, f'{out}/{name}_music.wav')
    mix_voice(f'{out}/{name}_music.wav', voice, vaudio, f'{out}/{name}_audio.wav', meta['total'])
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{out}/{name}_silent.mp4', '-i', f'{out}/{name}_audio.wav', '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-shortest',
                    '-movflags', '+faststart', f'{out}/{name}.mp4'], check=True)
    for f in (f'{name}_silent.mp4', f'{name}_music.wav', f'{name}_audio.wav'): os.remove(f'{out}/{f}')


def crops(out, name, formats):
    made = []
    for f in formats:
        if f == '4:5': vf, tag = 'crop=1080:1350:0:285', '4x5'
        elif f == '1:1': vf, tag = 'crop=1080:1080:0:420', '1x1'
        else: continue
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{out}/{name}.mp4', '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17',
                        '-c:a', 'copy', '-movflags', '+faststart', f'{out}/{name}_{tag}.mp4'], check=True)
        made.append(f'{name}_{tag}.mp4')
    return made


def main_blocks(spec, out):
    os.makedirs(out, exist_ok=True)
    report = {'ok': False, 'engine': 'blocks', 'problems': [], 'notes': []}
    errs = validate_blocks(spec)
    if errs:
        report['problems'] = errs; json.dump(report, open(f'{out}/report.json', 'w'), indent=2); print('\n'.join(errs)); return 2
    work = os.path.join(out, '_work')
    report['problems'] += fetch_media(spec, work)
    notes = []
    voice, vaudio = build_voice(spec, work, notes)
    report['notes'] += notes
    if report['problems']:
        json.dump(report, open(f'{out}/report.json', 'w'), indent=2); print('\n'.join(report['problems'])); return 3
    variants = [('video', spec)]
    for k, hook in enumerate(spec.get('hooks') or [], start=2):  # extra opening scenes for ad testing
        alt = json.loads(json.dumps(spec)); alt['scenes'][0] = hook; alt.pop('hooks', None); variants.append((f'video_hook{k}', alt))
    if spec.get('short'):  # a short cut: the scene numbers to keep (8 to 12 seconds)
        alt = json.loads(json.dumps(spec)); keep = [i - 1 for i in spec['short']]
        alt['scenes'] = [alt['scenes'][i] for i in keep]; alt.pop('hooks', None)
        if alt.get('voice'):
            remap = {old + 1: new + 1 for new, old in enumerate(keep)}
            alt['voice']['lines'] = [dict(l, scene=remap[l['scene']]) for l in alt['voice']['lines'] if l['scene'] in remap]
        variants.append(('video_short', alt))
    files = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--allow-file-access-from-files', '--disable-web-security'])
        pg = b.new_page(viewport={'width': 1080, 'height': 1920})
        for k, (name, sp) in enumerate(variants):
            pg.goto((HERE / 'template' / 'blocks.html').as_uri()); pg.wait_for_timeout(300)
            v, va = (voice, vaudio) if k == 0 else build_voice(sp, work, [])
            meta, probs = render_one(pg, sp, v, out, name, want_sheet=(k == 0))
            if probs:
                report['problems'] += [f'{name}: {x}' for x in probs]
                if k == 0: json.dump(report, open(f'{out}/report.json', 'w'), indent=2); print('\n'.join(report['problems'])); b.close(); return 3
                continue
            finish_audio(meta, sp, v, va, out, name)
            files.append(f'{name}.mp4'); files += crops(out, name, spec.get('formats') or [])
            if k == 0: report.update(total=meta['total'], timeline=meta['timeline'])
        b.close()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-pattern_type', 'glob', '-i', f'{out}/sheet_*.jpg',
                    '-vf', 'scale=270:480,tile=6x2', '-frames:v', '1', '-q:v', '3', f'{out}/sheet.jpg'], check=True)
    for f in os.listdir(out):
        if f.startswith('sheet_'): os.remove(f'{out}/{f}')
    shutil.rmtree(work, ignore_errors=True)
    report['ok'] = True; report['files'] = files; report['bytes'] = os.path.getsize(f'{out}/video.mp4')
    json.dump(report, open(f'{out}/report.json', 'w'), indent=2); print(json.dumps(report)[:600]); return 0
