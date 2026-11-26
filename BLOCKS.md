# Blocks engine: what a video can be made of

No fixed recipes. A storyboard is a list of **scenes**, and each scene is a list of **blocks** placed anywhere on a
1080 × 1920 frame. Positions are percentages: `"at": [x, y]` is the block's centre (characters: their feet).
Only the brand is locked (colours, fonts, logo, character style). Run `python preview.py storyboard.json sheet.jpg`
for a quick contact sheet, `python render.py storyboard.json out` for the full video.

## Storyboard

```json
{"engine": "blocks", "seed": 123456, "music": {"mood": "bright"}, "formats": ["4:5", "1:1"], "loop": true,
 "hooks": [ {alternative scene 1}, {another} ], "short": [1, 4, 8],
 "voice": {"narrator": "jenny", "lines": [{"scene": 1, "at": 0.3, "text": "...", "speaker": "narrator"}]},
 "captions_y": 67,
 "scenes": [{"dur": 3, "bg": "night", "transition": "slide", "camera": {"zoom": [1.08, 1]}, "shake": false, "blocks": [...]}]}
```

- `formats`: extra crops of the same video (`4:5` for feeds, `1:1`). The 9:16 is always made.
- `hooks`: extra versions with a different first scene, for ad testing (video_hook2.mp4, video_hook3.mp4).
- `short`: scene numbers for an 8 to 12 second cut (video_short.mp4).
- `loop`: the last moment fades back into the first frame so the video replays smoothly.
- `voice`: free Piper voices. `speaker` is `narrator` or a character block's `id` (its mouth moves with the voice).
  Voices: narrator `jenny` (default), `alba`, `alan`, `northern`, `cori`; each character has its own voice.
  Captions are burned in automatically. Set `"story": true` on a line that is a character talking in the story
  (not a claim about Gwithva). Scenes stretch automatically if a line is longer than the scene.
  Optional `"speed"` per line (0.8 to 1.2): slower for tired or stressed, faster for excited. Voices are Kokoro
  (British): narrator `kokoro:bf_emma`; characters each have their own. Write Gwithva normally; it is said Gwith-vah.

## Scene

| Field | Values |
|---|---|
| `dur` | 0.8 to 8 seconds |
| `bg` | plain: `cream`, `teal`, `peach`, `terra`, `warm`, `night`, `white` · cartoon rooms: `kitchen`, `living`, `street`, `office`, `night`, `van` |
| `transition` | `slide` (default), `cut`, `zoom`, `whip`, `fade` |
| `camera` | `{"zoom": [from, to], "pan": [[x, y], [x, y]]}` slow push or pan across the scene |
| `shake` | `true` for a short camera shake on entry |

## Blocks (every block: `kind`, `t` = start second in the scene, `until` = optional end second, `at`, `z`)

| kind | Fields | Notes |
|---|---|---|
| `text` | `text` (`\n` for lines, `*word*` = accent colour), `style` `headline`/`big`/`body`/`kicker`/`label`/`number`, `color`, `accent`, `size`, `w`, `in`, `plate` | `in`: `words` (default), `pop`, `rise`, `slam`, `type`, `fade`, `slide-l`, `slide-r`, `drop`, `spin` |
| `character` | `who`, `id`, `pose`, `mood`, `holds`, `size` (% of height, default 40), `flip`, `move` `[{"to": [x, y], "at": 0.5, "dur": 1}]`, `changes` `[{"at": 1.2, "pose": "cheer", "mood": "proud"}]` | cast: cleaners `kerra`, `jago`, `amira`, `dev`; customers `tamsin`, `ollie`, `grace` |
| `prop` | `name`, `size` (% of width), `loop` `bob`/`shake`/`pulse`/`spin`/`float` | phone, bucket, spray, mop, keys, diary, calendar, clock, coffee, laptop, envelope, bell, papers, tick, cross, house, heart, star, sparkle, question, exclaim, lightbulb, sweat, zzz |
| `bubble` | `text`, `kind` `speech`/`think`/`text` (a phone message), `tail` `down-l`/`down-r`/`left`/`right`, `w` | |
| `notifs` | `items` `[{"kind": "msg/call/bell/cal/note/email", "title", "body"}]`, `gap`, `w` | stacks phone notifications |
| `checklist` | `items` (max 28 characters each), `gap` | ticks each item |
| `counter` | `from`, `to`, `prefix`, `suffix`, `dur` | big number counting |
| `app` | `screen` (bookings, diary, messages, share, expenses, overview, invoice, export, jobs) + that screen's sample data (same fields as the v1 engine; always fill it in, or the engine uses its own sample), `w` | the real app, animated, in a phone frame |
| `image` | `src` (`screen:bookings`, or a photo/clip URL from the Photo library), `frame` `phone`/`card`/`circle`/`full`, `zoom` `{"at", "dur", "from": [x, y, scale], "to": [x, y, scale]}` (x and y are 0 to 1, not percent), `clip` `{"start": 2}` | zoom into the part that matters |
| `logo` | `size`, `color` | draws the house-and-arrow mark and the wordmark. Never in the same scene as `cta` (the end card already has the logo; the engine drops it). Use at most once per video, outside the end card |
| `cta` | `button`, `sub`, `y` | the end card; must be in the last scene |
| `arrow` | `from`, `to`, `color` | hand-drawn arrow |
| `circle` | `at`, `w`, `h` | hand-drawn ring to highlight something |
| `burst` | `style` `sparkles`/`confetti`/`stress` | |

Poses: idle, wave, point, pointL, phone, shrug, cheer, facepalm, think, carry, type, stressed, thumbs, present, hips.
Moods: happy, neutral, sad, stressed, shocked, proud, annoyed, thinking, tired.

## Rules the engine checks before rendering

- Every word about Gwithva follows the Fact Sheet (the same banned list as v1). Story lines can be marked `"story": true`.
- Something moves in the first half-second (a block with `t` 0 to 0.2).
- Text, bubbles and the end card sit in the safe zone (x 4-88 %, y 10-80 %) so TikTok and Reels buttons never cover them.
- The last scene holds the `cta` end card. No exclamation marks in on-screen text.
- 3 to 14 scenes, 6 to 45 seconds.
