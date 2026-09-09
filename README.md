# The Late Shift — podcast-style talking host

A single-file web page that stages a **podcast host in a studio booth** who
actually *talks*. Type or pick a script, hit **Go Live**, and a stylized
presenter delivers it at the mic — lip-syncing to real speech, with an
**ON AIR** neon sign, a live VU waveform, a running timecode, and a
teleprompter that highlights each word as it's spoken.

## Run it

Just open `podcast-studio.html` in a browser (Chrome, Edge, or Safari) — no
build step, no server, no accounts. It uses the browser's built-in
Web Speech voice for audio, so nothing is uploaded anywhere.

Or host it: because it's a self-contained file, dropping it on GitHub Pages
or any static host works as-is.

## Controls

- **Script** — edit the text freely, or load a segment (Cold Open, Welcome
  Back, Hot Take, Interview Q, Sign-Off).
- **Voice** — pick any voice your device/browser offers.
- **Pace / Tone** — adjust speaking rate and pitch.
- **Go Live** — start the broadcast (Space bar also toggles it). Hit it again
  to stop.

If a browser can't synthesize speech, the host still performs the script
silently with the teleprompter.

## Note

This is an animated, stylized presenter — not a photorealistic AI video of a
real person. It renders and speaks entirely in the browser.
