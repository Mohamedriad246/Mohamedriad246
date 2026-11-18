"""Builds the podcast clip's audio and the visualizer data.

1. cleans the voice recording (ffmpeg: rumble cut, denoise, presence EQ, compression)
2. synthesizes a soft lo-fi bed that ducks under the voice, plus an end sting
3. writes assets/audio-data.js: per-frame loudness + 24 spectrum bands for the waveform

usage: python3 audio.py <voice.m4a|wav> <total_seconds>
"""
import json
import subprocess
import sys
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SRC = sys.argv[1]
TOTAL = float(sys.argv[2]) if len(sys.argv) > 2 else 9.8
SR, FPS = 48000, 30
N = int(TOTAL * SR)
rng = np.random.default_rng(3)


def read_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
        return x.reshape(-1, w.getnchannels()).mean(axis=1)


def write_wav(path, x):
    x = np.atleast_2d(x)
    pcm = (np.clip(x.T, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[0])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- 1. voice
subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", SRC, "-ac", "1", "-ar", str(SR),
    "-af", "highpass=f=75,afftdn=nf=-28:nr=10,"
           "equalizer=f=200:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=3,equalizer=f=9000:t=q:w=1:g=1.5,"
           "acompressor=threshold=-22dB:ratio=3.5:attack=8:release=120:makeup=4dB,"
           "alimiter=limit=0.89",
    "work/voice-clean.wav"], check=True)
voice = read_wav("work/voice-clean.wav")
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]
voice *= 0.85 / (np.abs(voice).max() + 1e-9)


# ---------------------------------------------------------------- 2. music bed
def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def tv(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f):
    return sosfilt(butter(2, f / (SR / 2), output="sos"), x)


def epiano(m, dur):
    t = tv(dur)
    f = mtof(m)
    mod = np.sin(2 * np.pi * f * t) * 1.3 * np.exp(-t * 4)
    x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 1.1)
    x += 0.2 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 3)
    x *= np.minimum(1, t / 0.004) * np.clip((dur - t) / 0.25, 0, 1)
    return x * (1 + 0.15 * np.sin(2 * np.pi * 4.2 * t))  # tremolo


def kick():
    t = tv(0.4)
    return np.sin(2 * np.pi * np.cumsum(48 + 70 * np.exp(-t * 30)) / SR) * np.exp(-t * 8)


def hat():
    t = tv(0.06)
    return sosfilt(butter(2, 8000 / (SR / 2), "high", output="sos"), rng.standard_normal(len(t))) * np.exp(-t * 70)


def bell(m, dur=2.5):
    t = tv(dur)
    f = mtof(m)
    return np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * f * 3.5 * t) * 1.5 * np.exp(-t * 3)) * np.exp(-t * 2.2)


bed = np.zeros((2, N))
rev_send = np.zeros((2, N))


def put(sig, t0, g, pan=0.0, rev=0.3):
    i = int(t0 * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    a = (pan + 1) * np.pi / 4
    for c, k in enumerate((np.cos(a), np.sin(a))):
        bed[c, i:j] += sig[: j - i] * g * k * 1.414
        rev_send[c, i:j] += sig[: j - i] * g * k * 1.414 * rev


BPM = 84
beat = 60 / BPM
chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]  # Fmaj7 Em7 Dm7 Cmaj7
bar = 4 * beat
t = 0.0
k = 0
while t < 7.8:
    for i, m in enumerate(chords[k % 4]):
        put(epiano(m, bar + 0.4), t + i * 0.012, 0.05, -0.4 + i * 0.27)
    put(epiano(chords[k % 4][0] - 24, bar), t, 0.10, 0, rev=0.05)
    for b in range(4):
        tb = t + b * beat
        if tb < 7.8:
            if b in (0, 2):
                put(kick(), tb, 0.22, 0, rev=0)
            put(hat(), tb + beat / 2, 0.035, 0.3, rev=0)
    t += bar
    k += 1
# end sting under the end card
for i, m in enumerate([65, 69, 72, 76]):
    put(epiano(m, 2.2), 7.85 + i * 0.03, 0.07, -0.3 + i * 0.2, rev=0.5)
put(epiano(41, 2.2), 7.85, 0.12, 0, rev=0.1)
put(bell(84), 7.9, 0.05, 0.2, rev=0.7)
put(bell(88), 8.02, 0.035, -0.2, rev=0.7)

# intro swell
sw = tv(0.5)
put(lp(rng.standard_normal(len(sw)), 3000) * (sw / 0.5) ** 2 * 0.5, 0, 0.12, 0, rev=0.4)

irn = int(2.0 * SR)
ir = np.stack([lp(rng.standard_normal(irn), 5000) * np.exp(-np.arange(irn) / SR * 3) for _ in range(2)])
ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
bed += 0.5 * np.stack([fftconvolve(rev_send[c], ir[c])[:N] for c in range(2)])
bed = np.stack([lp(bed[c], 7000) for c in range(2)])  # lo-fi softness

# duck the bed under the voice
env = np.abs(voice)
win = int(0.08 * SR)
env = np.convolve(env, np.ones(win) / win, mode="same")
env = env / (env.max() + 1e-9)
duck = 1 - 0.75 * np.clip(env * 3, 0, 1)
duck = np.convolve(duck, np.ones(int(0.05 * SR)) / int(0.05 * SR), mode="same")
bed *= duck

mix = np.stack([voice, voice]) + bed * 1.0
fade = np.ones(N)
fade[int((TOTAL - 0.6) * SR):] = np.linspace(1, 0, N - int((TOTAL - 0.6) * SR))
mix *= fade
mix *= 0.89 / (np.abs(mix).max() + 1e-9)
write_wav("work/mix.wav", mix)

# ---------------------------------------------------------------- 3. visualizer data
frames = int(TOTAL * FPS)
hop = SR // FPS
nfft = 4096
bands = np.geomspace(90, 7000, 25)
freqs = np.fft.rfftfreq(nfft, 1 / SR)
win = np.hanning(nfft)
padded = np.pad(voice, (nfft // 2, nfft))
spec, loud = [], []
for f in range(frames):
    c = f * hop + nfft // 2
    seg = padded[c - nfft // 2: c + nfft // 2] * win
    mag = np.abs(np.fft.rfft(seg))
    row = [mag[(freqs >= bands[i]) & (freqs < bands[i + 1])].mean() for i in range(24)]
    spec.append(row)
    loud.append(np.sqrt(np.mean(voice[f * hop:(f + 1) * hop] ** 2)))
spec = 20 * np.log10(np.array(spec) + 1e-6)
spec = np.clip((spec - (spec.max() - 48)) / 48, 0, 1)
loud = 20 * np.log10(np.array(loud) + 1e-6)
loud = np.clip((loud - (loud.max() - 36)) / 36, 0, 1)
# smooth attack/release so bars move like a meter
sm = np.zeros_like(spec)
ls = np.zeros_like(loud)
for f in range(frames):
    prev = sm[f - 1] if f else 0
    sm[f] = np.where(spec[f] > prev, prev + (spec[f] - prev) * 0.75, prev + (spec[f] - prev) * 0.35)
    pl = ls[f - 1] if f else 0
    ls[f] = pl + (loud[f] - pl) * (0.7 if loud[f] > pl else 0.25)
with open("assets/audio-data.js", "w") as fh:
    fh.write("window.AUDIO_DATA=" + json.dumps({
        "fps": FPS, "total": TOTAL,
        "loud": [round(float(v), 3) for v in ls],
        "bands": [[round(float(v), 2) for v in row] for row in sm],
    }, separators=(",", ":")) + ";\n")
print("ok: work/mix.wav + assets/audio-data.js", frames, "frames")
