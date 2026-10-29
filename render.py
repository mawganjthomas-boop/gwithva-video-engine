"""Gwithva video engine: storyboard JSON in -> finished 9:16 MP4 out.
Usage: python render.py storyboard.json out_dir
Writes: video.mp4, cover.jpg, sheet.jpg (contact sheet for QC), report.json"""
import json, os, subprocess, sys, pathlib
from playwright.sync_api import sync_playwright
from validate import validate
from audio import render_audio

HERE = pathlib.Path(__file__).resolve().parent
FPS = 30


def main(spec_path, out):
    os.makedirs(out, exist_ok=True)
    spec = json.load(open(spec_path))
    report = {'ok': False, 'problems': []}
    errs = validate(spec)
    if errs:
        report['problems'] = errs; json.dump(report, open(f'{out}/report.json', 'w'), indent=2); print('\n'.join(errs)); return 2
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1080, 'height': 1920})
        pg.goto((HERE / 'template' / 'index.html').as_uri()); pg.wait_for_timeout(500)
        meta = pg.evaluate('spec => init(spec)', spec)
        report.update(total=meta['total'], timeline=meta['timeline'])
        if meta['problems']: report['problems'] += meta['problems']
        if not 19.5 <= meta['total'] <= 26.0: report['problems'].append(f'video length {meta["total"]}s is outside 20-25s; use fewer or more scenes')
        if report['problems']:
            json.dump(report, open(f'{out}/report.json', 'w'), indent=2); print('\n'.join(report['problems'])); b.close(); return 3
        n = int(meta['total'] * FPS)
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'mjpeg', '-i', '-',
                               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                               f'{out}/silent.mp4'], stdin=subprocess.PIPE)
        sheet_ts = [round(meta['total'] * (k + .5) / 12, 2) for k in range(12)]
        cover_t = min(meta['total'] - 1, 2.9)
        for i in range(n):
            t = i / FPS
            pg.evaluate(f'setTime({t})')
            jpg = pg.screenshot(type='jpeg', quality=93)
            ff.stdin.write(jpg)
            if abs(t - cover_t) < .5 / FPS: open(f'{out}/cover.jpg', 'wb').write(jpg)
            for k, st in enumerate(sheet_ts):
                if abs(t - st) < .5 / FPS: open(f'{out}/sheet_{k:02d}.jpg', 'wb').write(jpg)
        ff.stdin.close(); ff.wait(); b.close()
    report['music'] = render_audio(meta, spec, f'{out}/audio.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{out}/silent.mp4', '-i', f'{out}/audio.wav', '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-shortest',
                    '-movflags', '+faststart', f'{out}/video.mp4'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-pattern_type', 'glob', '-i', f'{out}/sheet_*.jpg',
                    '-vf', 'scale=270:480,tile=6x2', '-frames:v', '1', '-q:v', '3', f'{out}/sheet.jpg'], check=True)
    for f in os.listdir(out):
        if f.startswith('sheet_') or f in ('silent.mp4', 'audio.wav'): os.remove(f'{out}/{f}')
    report['ok'] = True; report['bytes'] = os.path.getsize(f'{out}/video.mp4')
    json.dump(report, open(f'{out}/report.json', 'w'), indent=2); print(json.dumps(report)[:400]); return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
