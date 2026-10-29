# Gwithva video engine

Turns a storyboard (JSON written by Claude in Make.com) into a finished 9:16 Gwithva ad:
real app screens, locked brand (deep teal #004355, cream #F4F1EA, terracotta #CB6A42, peach #EDA57F,
Playfair Display + Nunito, the house-and-arrow logo), original music and sound design.

**How it runs (nothing to do by hand):**
1. Make scenario **A2-VID WRITER** asks Claude for a storyboard, creates the Notion draft (Status *Generating*) and starts this repo's workflow.
2. The workflow checks the storyboard against the Fact Sheet rules (`validate.py`), renders it (`render.py`), and publishes the video to GitHub Pages.
3. It calls Make (**A2-VID CALLBACK**), which runs a visual QC and puts the video in the Approval Queue as *Draft*.

| File | What it is |
|---|---|
| `template/index.html` | The look. Brand, layouts, animation. Change design here only. |
| `validate.py` | The rules. Banned claims, text lengths, scene order. |
| `audio.py` | Sound effects and music (all synthesised, no licences needed). |
| `render.py` | Storyboard in, `video.mp4` + `cover.jpg` + `sheet.jpg` out. |
| `examples/` | Two sample storyboards. Run the workflow by hand to test them. |
| `videos/` | Finished videos (newest 40 kept). Served at `https://<owner>.github.io/gwithva-video-engine/videos/...` |

Scenes available: `hook` (style `statement` or `pov`), `pileup`, `reveal`, `app` (screens `bookings`, `diary`, `messages`, `share`), `statement`, `payoff`, `cta`.
App screens are captures of the real cleaner app; names, times and messages on them are sample data and every video says "Sample data shown".
