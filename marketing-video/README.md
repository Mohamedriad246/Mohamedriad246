# Top Notch — promo video

A 32-second bilingual (Arabic-first, English support) promo for Top Notch
Translation & Localization, in two cuts:

| File | Size | For |
|---|---|---|
| `out/top-notch-promo-16x9.mp4` | 1920×1080 | YouTube, LinkedIn, website, presentations |
| `out/top-notch-promo-9x16.mp4` | 1080×1920 | Instagram/Facebook Reels & Stories, TikTok, WhatsApp Status |
| `out/top-notch-thumbnail-*.jpg` | — | cover images / thumbnails |

## Storyboard

| Time | Scene |
|---|---|
| 0–8 s | **Hook** — a lease clause: *"The tenant **shall** pay the rent."* A literal translation (يجوز = *may*) is flagged red, then corrected to يلتزم (*shall*). Headline: بين «يجوز» و«يلتزم»… قضية كاملة. |
| 8–12 s | **Brand reveal** — TOP NOTCH · للترجمة والتوطين · Translation & Localization |
| 12–22 s | **Services** — Legal (GCC court judgments, contracts, memos) · Technical (oil & gas, energy, engineering) · Business · Localization |
| 22–26 s | **Why us** — دقّة Precision · سرّية Confidentiality · التزام On-time delivery |
| 26–32 s | **End card** — كل كلمة… في مكانها الصحيح. / *Every word, top notch.* · Request a quote |

## How it's made

Everything is code, so edits are cheap:

- `top-notch-promo.html` — the animation. Every element's timing is in a
  `data-a="animation duration start"` attribute. Open it in a browser and
  press play to preview with music.
- `music.py` — synthesizes the soundtrack (120 BPM, D minor), with hits
  timed to the same cues as the picture.
- `render.cjs` — captures the page frame-by-frame with Playwright and
  encodes it with ffmpeg.

```bash
python3 music.py out/top-notch-music.wav                       # needs numpy + scipy
node render.cjs landscape out/video-landscape.mp4              # needs playwright + ffmpeg
node render.cjs portrait  out/video-portrait.mp4
ffmpeg -i out/video-landscape.mp4 -i out/top-notch-music.wav -map 0:v -map 1:a -c:v copy \
  -af loudnorm=I=-14:TP=-1.5:LRA=11 -ar 48000 -c:a aac -b:a 192k -movflags +faststart \
  -shortest out/top-notch-promo-16x9.mp4
```

Fonts in `fonts/` (IBM Plex Sans Arabic, Amiri, Manrope, Fraunces) are under
the SIL Open Font License.

The speech-bubble "A | ع" mark is a placeholder emblem — swap in the official
logo when available.
