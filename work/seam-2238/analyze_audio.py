#!/usr/bin/env python3
"""Spectral flux + RMS around the 22:38 seam in the delivered programme.

Excerpt starts at 1347.0 s programme time; seam per manifest = 1357.105 s.
Hop = 128 samples @ 48 kHz = 2.667 ms, matching the method recorded in
stories/megacut/megacut.json `_needle_drop`.
"""
import numpy as np
import wave

SR = 48000
HOP = 128
WIN = 1024
EXCERPT_START = 1347.0
SEAM = 1357.105

w = wave.open('work/seam-2238/prog-audio.wav', 'rb')
assert w.getframerate() == SR, w.getframerate()
n = w.getnframes()
x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0
t_off = EXCERPT_START

win = np.hanning(WIN)
n_frames = (len(x) - WIN) // HOP + 1
flux = np.zeros(n_frames)
rms = np.zeros(n_frames)
prev = None
for i in range(n_frames):
    seg = x[i*HOP:i*HOP+WIN] * win
    mag = np.abs(np.fft.rfft(seg))
    rms[i] = np.sqrt(np.mean(seg**2))
    if prev is not None:
        d = mag - prev
        flux[i] = np.sum(d[d > 0])
    prev = mag

times = t_off + (np.arange(n_frames) * HOP + WIN/2) / SR
rms_db = 20 * np.log10(rms + 1e-10)

# 1) Top flux peaks in the window seam +/- 1.5 s
mask = (times > SEAM - 1.5) & (times < SEAM + 1.5)
idx = np.argsort(flux[mask])[::-1][:12]
tms = times[mask]; flx = flux[mask]
print("== Top spectral-flux peaks within +/-1.5 s of the manifest seam (1357.105) ==")
for i in sorted(idx):
    print(f"  t={tms[i]:9.3f}  ({tms[i]-SEAM:+.3f} rel seam)  flux={flx[i]:8.1f}")

# 2) RMS profile around the seam, 100 ms bins
print("\n== RMS level, 100 ms bins, seam +/- 1.5 s (dBFS) ==")
for b in np.arange(SEAM - 1.5, SEAM + 1.5, 0.1):
    m = (times >= b) & (times < b + 0.1)
    if m.any():
        print(f"  {b:9.3f} .. {b+0.1:9.3f}   {np.mean(rms_db[m]):7.1f} dB")

# 3) Locate the largest level discontinuity (= hard cut) in the window
d = np.abs(np.diff(rms_db))
mc = (times[:-1] > SEAM - 1.0) & (times[:-1] < SEAM + 1.0)
j = np.argmax(d[mc])
tm = times[:-1][mc]
print(f"\n== Largest RMS step near seam: {d[mc][j]:.1f} dB at t={tm[j]:.3f} ({tm[j]-SEAM:+.3f} rel seam)")

# 4) First big onset AFTER the seam (the needle drop hit)
m2 = (times > SEAM) & (times < SEAM + 1.0)
k = np.argmax(flux[m2])
print(f"== Strongest onset after seam: t={times[m2][k]:.3f} ({times[m2][k]-SEAM:+.3f} rel seam) flux={flux[m2][k]:.1f}")

# 5) Any onset just BEFORE the seam (act VI tail)?
m3 = (times > SEAM - 0.5) & (times <= SEAM)
k3 = np.argmax(flux[m3])
print(f"== Strongest onset in last 0.5 s of act VI: t={times[m3][k3]:.3f} ({times[m3][k3]-SEAM:+.3f}) flux={flux[m3][k3]:.1f}")
print(f"   median flux in that window: {np.median(flux[m3]):.1f}; in the 0.5 s after seam: {np.median(flux[m2]):.1f}")
