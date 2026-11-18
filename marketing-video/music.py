"""Synthesizes the Top Notch promo soundtrack (32 s, 120 BPM, D minor).

Every hit is timed to the cues in top-notch-promo.html, so the music and
picture stay locked without any manual editing.

usage: python3 music.py out/top-notch-music.wav
"""
import sys
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
DUR = 32.0
N = int(SR * DUR)
rng = np.random.default_rng(11)

# stereo buses
music = np.zeros((2, N))
drums = np.zeros((2, N))
sfx = np.zeros((2, N))
send = np.zeros((2, N))  # reverb send


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tvec(dur):
    return np.arange(int(dur * SR)) / SR


def filt(x, kind, f, order=2):
    if kind == "bp":
        sos = butter(order, [f[0] / (SR / 2), f[1] / (SR / 2)], btype="band", output="sos")
    else:
        sos = butter(order, f / (SR / 2), btype=kind, output="sos")
    return sosfilt(sos, x)


def place(bus, sig, t0, gain=1.0, pan=0.0, rev=0.0):
    i = int(round(t0 * SR))
    if i >= N or len(sig) == 0:
        return
    if i < 0:
        sig, i = sig[-i:], 0
    j = min(N, i + len(sig))
    s = sig[: j - i] * gain
    a = (pan + 1) * np.pi / 4
    l, r = np.cos(a) * np.sqrt(2), np.sin(a) * np.sqrt(2)
    bus[0, i:j] += s * l
    bus[1, i:j] += s * r
    if rev:
        send[0, i:j] += s * l * rev
        send[1, i:j] += s * r * rev


def env_adsr(n, a, d, s, r, total):
    t = np.arange(n) / SR
    e = np.ones(n) * s
    e[t < a] = t[t < a] / a
    m = (t >= a) & (t < a + d)
    e[m] = 1 - (1 - s) * (t[m] - a) / d
    rel = t > total - r
    e[rel] *= np.clip((total - t[rel]) / r, 0, 1)
    return e


# ---------------------------------------------------------------- instruments
def pad_note(m, dur, bright=7.0, detune=0.0):
    t = tvec(dur)
    f = mtof(m) * 2 ** (detune / 1200)
    sig = np.zeros_like(t)
    for k in range(1, 14):
        if f * k > 9000:
            break
        sig += np.sin(2 * np.pi * f * k * t + k * 0.7) * (1 / k) * np.exp(-k / bright)
    # gentle movement
    sig *= 1 + 0.08 * np.sin(2 * np.pi * 0.35 * t + m)
    return sig * env_adsr(len(t), 0.6, 0.4, 0.85, 1.1, dur)


def pad(chord, t0, dur, gain=0.055):
    for m in chord:
        for dt, pan in ((-6, -0.6), (6, 0.6)):
            place(music, pad_note(m, dur + 1.0, detune=dt), t0, gain, pan, rev=0.45)


def bass_note(m, dur):
    t = tvec(dur)
    f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    x = np.tanh(1.6 * x)
    e = np.minimum(1, t / 0.004) * (0.55 + 0.45 * np.exp(-t * 9))
    e *= np.clip((dur - t) / 0.03, 0, 1)
    return filt(x * e, "low", 900)


def kick(gain=1.0):
    t = tvec(0.55)
    f = 46 + 95 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 6.5)
    click = filt(rng.standard_normal(len(t)), "high", 2500) * np.exp(-t * 400) * 0.35
    return (body + click) * gain


def clap():
    t = tvec(0.35)
    n = rng.standard_normal(len(t))
    e = np.zeros_like(t)
    for off in (0, 0.011, 0.022):
        m = t >= off
        e[m] += np.exp(-(t[m] - off) * (60 if off < 0.02 else 18))
    x = filt(n, "bp", (900, 5200)) * e
    x += np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30) * 0.4
    return x


def hat(open_=False):
    t = tvec(0.25 if open_ else 0.07)
    x = filt(rng.standard_normal(len(t)), "high", 7500)
    return x * np.exp(-t * (14 if open_ else 70))


def bell(m, dur=2.6, idx=2.2):
    t = tvec(dur)
    f = mtof(m)
    mod = np.sin(2 * np.pi * f * 3.5 * t) * idx * np.exp(-t * 3)
    x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 2.2)
    x += 0.35 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 4)
    return x * np.minimum(1, t / 0.002)


def pluck(m, dur=1.1):
    t = tvec(dur)
    f = mtof(m)
    x = np.zeros_like(t)
    for k in range(1, 10):
        x += np.sin(2 * np.pi * f * k * t) / k * np.exp(-t * (4 + 2.2 * k))
    return x * np.minimum(1, t / 0.002)


def impact():
    t = tvec(3.0)
    f = 30 + 55 * np.exp(-t * 5)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    boom = filt(rng.standard_normal(len(t)), "low", 380) * np.exp(-t * 5) * 1.4
    crack = filt(rng.standard_normal(len(t)), "high", 3000) * np.exp(-t * 25) * 0.25
    return sub + boom + crack


def stft_sweep(dur, f_from, f_to, width=0.35, curve=2.0):
    """Noise whose band sweeps from f_from to f_to (log), via STFT masking."""
    n = int(dur * SR)
    hop, win = 512, 2048
    x = rng.standard_normal(n + win)
    w = np.hanning(win)
    out = np.zeros(n + win)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    lf = np.log2(np.maximum(freqs, 1))
    for s in range(0, n, hop):
        p = (s / n) ** curve
        c = np.log2(f_from) + (np.log2(f_to) - np.log2(f_from)) * p
        mask = np.exp(-0.5 * ((lf - c) / width) ** 2)
        seg = np.fft.irfft(np.fft.rfft(x[s:s + win] * w) * mask)
        out[s:s + win] += seg * w
    return out[:n] / 1.5


def riser(dur):
    t = tvec(dur)
    noise = stft_sweep(dur, 300, 9000, width=0.5, curve=1.6)
    f = 180 * 2 ** (2.6 * (t / dur) ** 1.7)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    e = (t / dur) ** 2.4
    return (noise + tone) * e


def whoosh(dur=0.7):
    t = tvec(dur)
    x = stft_sweep(dur, 350, 4200, width=0.45, curve=1.0)
    return x * np.sin(np.pi * t / dur) ** 2


def click():
    t = tvec(0.03)
    x = filt(rng.standard_normal(len(t)), "high", 1800) * np.exp(-t * 300)
    x += np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 500) * 0.4
    return x


def tick():
    t = tvec(0.08)
    return np.sin(2 * np.pi * 1650 * t) * np.exp(-t * 90) + np.sin(2 * np.pi * 2900 * t) * np.exp(-t * 140) * 0.4


def buzz(dur=0.16):
    t = tvec(dur)
    x = np.zeros_like(t)
    for m in (50, 51):  # D3 + Eb3, a nasty minor second
        f = mtof(m)
        for k in (1, 3, 5, 7):
            x += np.sin(2 * np.pi * f * k * t) / k
    return filt(x, "low", 1600) * np.minimum(1, t / 0.005) * np.clip((dur - t) / 0.03, 0, 1)


def drone(dur):
    t = tvec(dur)
    x = np.sin(2 * np.pi * mtof(38) * t) + 0.5 * np.sin(2 * np.pi * mtof(45) * t + 1)
    x += 0.25 * np.sin(2 * np.pi * mtof(50) * t + 2) * (1 + 0.5 * np.sin(2 * np.pi * 0.5 * t))
    e = np.minimum(1, t / 2.0) * (0.5 + 0.5 * (t / dur) ** 1.5)
    return x * e


# ---------------------------------------------------------------- arrangement
CH = {
    "Dm": [50, 53, 57, 64], "Bb": [46, 50, 53, 60],
    "F": [53, 57, 60, 67], "C": [48, 52, 55, 62],
}
ROOT = {"Dm": 38, "Bb": 34, "F": 41, "C": 36}
PROG = [(8, "Dm"), (10, "Bb"), (12, "F"), (14, "C"), (16, "Dm"), (18, "Bb"),
        (20, "F"), (22, "C"), (24, "Bb"), (26, "Dm"), (28, "Bb"), (30, "F")]


def chord_at(t):
    name = PROG[0][1]
    for s, c in PROG:
        if t >= s:
            name = c
    return name


# --- hook (0-8): drone, clock ticks, typing, error, fix, riser
place(music, drone(8.6), 0, 0.22, 0, rev=0.2)
for b in range(12):
    place(sfx, tick(), b * 0.5, 0.08 if b % 2 else 0.13, -0.3 if b % 2 else 0.3, rev=0.15)
SRC = "The tenant shall pay the rent."
for i, c in enumerate(SRC):
    if c != " ":
        place(sfx, click(), 0.6 + i * 0.04, 0.16 * (0.6 + 0.4 * rng.random()), -0.2 + 0.4 * rng.random())
place(sfx, whoosh(0.5), 2.2, 0.10, 0.4, rev=0.2)          # Arabic line wipes in
place(sfx, buzz(), 3.15, 0.20, 0)                         # mistranslation
place(sfx, buzz(), 3.33, 0.16, 0)
place(sfx, whoosh(0.35), 3.85, 0.12, -0.4)                # strike-through
place(sfx, whoosh(0.6), 4.45, 0.12, 0.4, rev=0.25)        # correct line wipes in
place(sfx, bell(81, 2.2, 1.2), 5.3, 0.12, -0.2, rev=0.5)  # ✓ ding
place(sfx, bell(88, 2.2, 1.0), 5.3, 0.07, 0.2, rev=0.5)
place(sfx, whoosh(0.6), 5.65, 0.12, 0, rev=0.3)           # card blurs away
place(music, pluck(62), 6.2, 0.16, -0.2, rev=0.5)
place(music, pluck(69), 6.65, 0.16, 0.2, rev=0.5)
place(music, pluck(74), 7.05, 0.12, 0, rev=0.5)
place(sfx, riser(2.0), 6.0, 0.20, 0, rev=0.3)

# --- impacts
for t in (8.0, 26.0):
    place(sfx, impact(), t, 0.85, 0, rev=0.35)
    place(drums, kick(1.0), t)

# --- pads
for s, c in PROG:
    pad(CH[c], s, 2.0 if s < 30 else 2.6)

# --- brand reveal sparkles (letters at 8.3 + i*.055)
for i, m in enumerate([74, 77, 81, 84, 86, 89, 93]):
    place(music, bell(m, 1.8, 1.4), 8.35 + i * 0.11, 0.05, -0.6 + i * 0.2, rev=0.6)
place(music, bell(62, 3.0, 0.8), 9.15, 0.10, 0, rev=0.6)
for t, m in ((8.0, 38), (10.0, 34)):                     # sustained sub under the logo
    place(music, bass_note(m, 2.0) * np.exp(-tvec(2.0) * 0.8), t, 0.26)
for t in np.arange(10.0, 12.0, 0.25):                    # soft pulse building into the groove
    place(drums, hat(), t, 0.03 + 0.05 * (t - 10) / 2, 0.2)

# --- groove (12-25.5 and 26-29.5)
def groove(a, b):
    t = a
    while t < b - 1e-6:
        beat = round((t - 12) / 0.5)
        place(drums, kick(0.9), t)
        if beat % 2 == 1:
            place(drums, clap(), t, 0.32, 0.05, rev=0.25)
        place(drums, hat(), t + 0.25, 0.10, 0.3)
        if t >= 16:
            place(drums, hat(), t + 0.125, 0.04, -0.3)
            place(drums, hat(), t + 0.375, 0.04, -0.3)
        # bass: 8ths on the chord root
        root = ROOT[chord_at(t)]
        for k, off in enumerate((0, 0.25)):
            place(music, bass_note(root + (12 if (beat % 4 == 3 and k == 1) else 0), 0.22), t + off, 0.20)
        t += 0.5


groove(12.0, 25.5)
groove(26.0, 30.0)
place(drums, hat(True), 25.25, 0.12, 0.2, rev=0.3)

# arpeggio over the services section
pattern = [0, 1, 2, 3, 2, 1, 2, 3]
t = 12.0
while t < 22.0 - 1e-6:
    chord = CH[chord_at(t)]
    step = int(round((t - 12) / 0.25))
    m = chord[pattern[step % 8]] + 12
    place(music, pluck(m, 0.8), t, 0.06, -0.5 if step % 2 else 0.5, rev=0.4)
    t += 0.25

# service transitions + "why us" hits
for t in (14.2, 16.7, 19.2, 21.7):
    place(sfx, whoosh(0.6), t - 0.15, 0.16, -0.5 if int(t) % 2 else 0.5, rev=0.3)
for t, m in ((22.5, 81), (23.5, 84), (24.5, 86)):
    place(music, bell(m, 2.0, 1.6), t, 0.11, 0, rev=0.55)
    place(drums, kick(0.5), t)
place(sfx, riser(1.4), 24.6, 0.22, 0, rev=0.3)

# --- end card
for i, m in enumerate([86, 89, 93, 98]):
    place(music, bell(m, 1.6, 1.2), 26.2 + i * 0.09, 0.04, -0.4 + i * 0.25, rev=0.6)
for m in (65, 69, 72):                                   # CTA pop
    place(music, pluck(m + 12, 1.4), 27.8, 0.09, 0, rev=0.5)
for t in (28.7, 30.6):                                   # shine sweeps
    place(sfx, stft_sweep(0.9, 2500, 11000, width=0.3) * np.hanning(int(0.9 * SR)), t, 0.07, 0.3, rev=0.5)
place(music, bass_note(41, 2.0) * np.exp(-tvec(2.0) * 1.2), 30.0, 0.32)
place(music, bell(77, 3.5, 1.0), 30.0, 0.12, -0.2, rev=0.7)
place(music, bell(84, 3.5, 0.8), 30.0, 0.08, 0.2, rev=0.7)
place(drums, kick(0.8), 30.0)

# ---------------------------------------------------------------- mix
# sidechain the music bus against every kick-bearing beat
duck = np.ones(N)
for s in np.arange(12.0, 30.01, 0.5):
    if 25.5 <= s < 26.0:
        continue
    i = int(s * SR)
    tt = np.arange(min(N - i, int(0.45 * SR))) / SR
    duck[i:i + len(tt)] = np.minimum(duck[i:i + len(tt)], 1 - 0.45 * np.exp(-tt * 9))
music *= duck

# reverb: decaying stereo noise impulse
irn = int(2.6 * SR)
tir = np.arange(irn) / SR
ir = np.stack([filt(rng.standard_normal(irn), "low", 5500) * np.exp(-tir * 2.7) for _ in range(2)])
ir[:, : int(0.018 * SR)] = 0
ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
wet = np.stack([fftconvolve(send[c], ir[c])[:N] for c in range(2)])

mix = music + drums * 0.9 + sfx + wet * 0.55
mix = np.stack([filt(mix[c], "high", 28) for c in range(2)])

# master fade + soft clip + normalize
fade = np.ones(N)
fs, fe = int(30.6 * SR), N
fade[fs:fe] = np.linspace(1, 0, fe - fs) ** 1.5
fade[: int(0.02 * SR)] = np.linspace(0, 1, int(0.02 * SR))
mix *= fade
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.4) / np.tanh(1.4)
mix *= 0.89 / np.max(np.abs(mix))

out = sys.argv[1] if len(sys.argv) > 1 else "out/top-notch-music.wav"
pcm = (mix.T * 32767).astype("<i2")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", out)
