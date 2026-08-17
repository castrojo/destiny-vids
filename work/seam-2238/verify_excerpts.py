#!/usr/bin/env python3
"""Verify join-2238 excerpts: audio needle drop + picture cut structure.

Each excerpt is 8.0 s with the seam at 4.000 s, 30 fps, 48 kHz.
Audio: spectral flux (hop 128 @ 48 kHz) + RMS.
Picture: mean luma + inter-frame motion on 320x180 gray.
"""
import subprocess
import sys
import numpy as np

FF = '/home/linuxbrew/.linuxbrew/bin/ffmpeg'
SR, HOP, WIN = 48000, 128, 1024
SEAM = 4.000
FPS = 30.0
W, H = 320, 180

def load(path):
    a = subprocess.run([FF, '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', str(SR),
                        '-f', 's16le', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(a, dtype=np.int16).astype(np.float64) / 32768.0
    v = subprocess.run([FF, '-v', 'error', '-i', path, '-vf', f'scale={W}:{H}',
                        '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True, check=True).stdout
    fr = np.frombuffer(v, dtype=np.uint8)
    nf = fr.size // (W*H)
    return x, fr[:nf*W*H].reshape(nf, H, W).astype(np.float32)

def analyze(name, x, frames):
    print(f'===== {name} =====')
    # audio
    win = np.hanning(WIN)
    nf = (len(x) - WIN) // HOP + 1
    flux = np.zeros(nf)
    prev = None
    for i in range(nf):
        mag = np.abs(np.fft.rfft(x[i*HOP:i*HOP+WIN] * win))
        if prev is not None:
            flux[i] = np.maximum(mag - prev, 0).sum()
        prev = mag
    t = (np.arange(nf) * HOP + WIN/2) / SR
    m = (t > SEAM - 1.0) & (t < SEAM + 1.5)
    idx = np.argsort(flux[m])[::-1][:6]
    print('-- top audio onsets within [-1.0,+1.5] of seam (t rel seam, flux):')
    for i in sorted(idx):
        print(f'   {t[m][i]-SEAM:+8.3f}  {flux[m][i]:8.1f}')
    for lo, hi, lbl in [(-0.5, 0.0, 'act6 last 0.5s'), (0.0, 0.5, 'p4 first 0.5s')]:
        seg = x[int((SEAM+lo)*SR):int((SEAM+hi)*SR)]
        print(f'   RMS {lbl}: {20*np.log10(np.sqrt((seg**2).mean())):6.1f} dBFS')
    # picture
    n = len(frames)
    tf = np.arange(n) / FPS
    mean = frames.mean(axis=(1, 2))
    mot = np.zeros(n)
    mot[1:] = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    m = (tf > SEAM - 1.0) & (tf < SEAM + 1.5)
    idx = np.argsort(mot[m])[::-1][:5]
    print('-- top motion spikes within [-1.0,+1.5] of seam (t rel seam, motion):')
    for i in sorted(idx):
        print(f'   {tf[m][i]-SEAM:+8.3f}  {mot[m][i]:7.2f}')
    # luma just either side of the seam (0.3 s windows)
    for lo, hi, lbl in [(-0.3, 0.0, 'act6 last 0.3s'), (0.0, 0.3, 'p4 first 0.3s')]:
        mm = (tf >= SEAM+lo) & (tf < SEAM+hi)
        print(f'   luma {lbl}: {mean[mm].mean():5.1f} (sd {mean[mm].std():4.1f})')
    # frame straddling the seam
    i0 = int(SEAM * FPS) - 1
    print(f'   frames straddling seam: f{i0} (t={tf[i0]:.3f}, luma {mean[i0]:.1f}) -> f{i0+1} (t={tf[i0+1]:.3f}, luma {mean[i0+1]:.1f}), motion {mot[i0+1]:.2f}')
    print()

for path in sys.argv[1:]:
    x, frames = load(path)
    analyze(path.split('/')[-1], x, frames)
