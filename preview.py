"""Quick look at a blocks storyboard without rendering the whole video.
Usage: python preview.py storyboard.json out.jpg [frames]
Saves a contact sheet of stills (default: two per scene)."""
import json, os, sys, pathlib, subprocess, tempfile
from playwright.sync_api import sync_playwright
from render_blocks import fetch_media, build_voice

HERE = pathlib.Path(__file__).resolve().parent


def main(spec_path, out_path, per_scene=2):
    spec = json.load(open(spec_path)); tmp = tempfile.mkdtemp()
    fetch_media(spec, tmp); voice, _ = build_voice(spec, tmp, [])
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--allow-file-access-from-files', '--disable-web-security'])
        pg = b.new_page(viewport={'width': 1080, 'height': 1920})
        pg.goto((HERE / 'template' / 'blocks.html').as_uri()); pg.wait_for_timeout(300)
        meta = pg.evaluate('([s, v]) => init(s, v)', [spec, voice])
        print(json.dumps({'total': meta['total'], 'problems': meta['problems']}))
        ts = []
        for x in meta['timeline']:
            for k in range(per_scene): ts.append(round(x['start'] + x['dur'] * (k + 1) / (per_scene + .3), 2))
        for i, t in enumerate(ts):
            pg.evaluate(f'setTime({t})'); pg.screenshot(path=f'{tmp}/s_{i:03d}.jpg', type='jpeg', quality=85)
        b.close()
    cols = min(8, len(ts))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-pattern_type', 'glob', '-i', f'{tmp}/s_*.jpg', '-vf',
                    f'scale=270:480,tile={cols}x{(len(ts) + cols - 1) // cols}', '-frames:v', '1', '-q:v', '3', out_path], check=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2)
