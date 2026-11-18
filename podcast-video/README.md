# Podcast clip from photos + a voice note

Turns a few still photos and a short voice recording into a podcast-style
clip: the speaker is cut out and placed in a virtual studio (wood-slat wall,
neon, desk, boom-arm mic), the edit cuts between camera angles on the pauses
in the recording, and a gold spectrum visualizer follows the voice. Outputs
9:16 (Reels/TikTok) and 16:9.

Photos, voice and renders are git-ignored on purpose (this repo is public).

```bash
# 1. cut out the person (MediaPipe selfie_multiclass model + GrabCut refinement)
python3 cutout.py work/selfie_multiclass.tflite <photo> assets/front.png
# 2. clean the voice, synthesize the music bed, build visualizer data
python3 audio.py <voice.m4a> 9.8
# 3. render and add the audio
node render.cjs portrait out/video-portrait.mp4
ffmpeg -i out/video-portrait.mp4 -i work/mix.wav -map 0:v -map 1:a -c:v copy \
  -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:a aac -b:a 192k -shortest out/podcast-clip-9x16.mp4
```

Captions: add `assets/captions.js` with
`window.CAPTIONS=[{w:'word',s:0.40,e:0.72}, …]` (seconds) and re-render.

The face is a still photo — there is no lip-sync.
