#!/usr/bin/env python3
"""Owner follow-up: (1) is post-seam audio identical across A/B/C (needle-drop
timing), and what changed pre-seam; (2) envelope around B's -0.267 motion bump.
"""
import subprocess
import numpy as np

FFMPEG = "/home/linuxbrew/.linuxbrew/bin/ffmpeg"
SR = 48000
FILES = {
    "A": "renders/review/join-2238-A-asshipped.mp4",
    "B": "renders/review/join-2238-B-picturedissolve.mp4",
    "C": "renders/review/join-2238-C-shotchange.mp4",
}
SEAM = 4.000


def audio(path):
    p = subprocess.run(
        [FFMPEG, "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR),
         "-f", "f32le", "-"],
        capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def xcorr(a, b, max_lag=2400):  # +-50 ms
    a = a - a.mean(); b = b - b.mean()
    best_lag, best_r = 0, -2.0
    for lag in range(-max_lag, max_lag + 1, 1):
        if lag >= 0:
            x, y = a[lag:], b[:len(b) - lag]
        else:
            x, y = a[:lag], b[-lag:]
        n = min(len(x), len(y))
        x, y = x[:n], y[:n]
        d = np.sqrt((x * x).sum() * (y * y).sum())
        if d == 0:
            continue
        r = float((x * y).sum() / d)
        if r > best_r:
            best_r, best_lag = r, lag
    return best_lag, best_r


def coarse_lag(a, b):
    # FFT-based full cross-correlation to find the coarse offset, then refine.
    n = len(a) + len(b)
    nfft = 1 << (n - 1).bit_length()
    A = np.fft.rfft(a, nfft)
    B = np.fft.rfft(b, nfft)
    cc = np.fft.irfft(A * np.conj(B), nfft)
    cc = np.concatenate((cc[-len(b) + 1:], cc[:len(a)]))
    return int(np.argmax(cc)) - (len(b) - 1)


def env(x, win=480):  # 10 ms RMS envelope
    n = len(x) // win
    return np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(axis=1))


au = {k: audio(v) for k, v in FILES.items()}
post = slice(int(4.1 * SR), int(5.5 * SR))   # after seam + needle drop
pre = slice(int(3.3 * SR), int(4.0 * SR))    # run-up into the drop

print("== post-seam (4.1-5.5s) timing vs A ==")
a_post = au["A"][post]
for k in ("B", "C"):
    x = au[k][post]
    lag = coarse_lag(a_post, x)
    fine, r = xcorr(a_post, x[max(lag, 0):] if lag >= 0 else x[:lag])
    total = lag + fine
    print(f"  {k} vs A: lag {total} samples = {total / SR * 1000:+.2f} ms, r = {r:.4f}")

print("\n== post-seam B vs C (same build chain, should be near-identical) ==")
b_post, c_post = au["B"][post], au["C"][post]
lag = coarse_lag(b_post, c_post)
_, r = xcorr(b_post, c_post)
print(f"  lag {lag} samples = {lag / SR * 1000:+.2f} ms, r = {r:.4f}")

print("\n== pre-seam envelope (3.30-4.00s), 10 ms RMS, dBFS ==")
for k in ("A", "B", "C"):
    e = 20 * np.log10(env(au[k][pre]) + 1e-9)
    print(f"  {k}: " + " ".join(f"{v:6.1f}" for v in e))

print("\n== accent check: act-film 431.075 sits at excerpt time 3.970 in A;")
print("   C's act-VI window ends at source 430.980 -> accent absent ==")
for k in ("A", "C"):
    seg = au[k][int(3.90 * SR):int(4.00 * SR)]
    e = 20 * np.log10(env(seg) + 1e-9)
    print(f"  {k} 3.90-4.00: " + " ".join(f"{v:6.1f}" for v in e))

print("\n== B around the -0.267 motion bump (excerpt 3.60-4.00s) ==")
e = 20 * np.log10(env(au["B"][int(3.60 * SR):int(4.00 * SR)]) + 1e-9)
print("  B audio env: " + " ".join(f"{v:6.1f}" for v in e))
print("  (motion bump is picture-only; audio here is act VI's last bar,")
print("   identical to A's same window)")
ea = 20 * np.log10(env(au["A"][int(3.60 * SR):int(4.00 * SR)]) + 1e-9)
print("  A audio env: " + " ".join(f"{v:6.1f}" for v in ea))
