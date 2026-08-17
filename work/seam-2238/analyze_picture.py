#!/usr/bin/env python3
"""Picture seam metrics: mean luma, luma variance, inter-frame motion."""
import numpy as np

W, H = 320, 180
FPS = 60000/1001
START = 1353.0
SEAM = 1357.105

raw = np.fromfile('work/seam-2238/prog-frames.gray', dtype=np.uint8)
nf = raw.size // (W*H)
frames = raw[:nf*W*H].reshape(nf, H, W).astype(np.float32)

t = START + np.arange(nf) / FPS
mean = frames.mean(axis=(1,2))
var = frames.var(axis=(1,2))
mot = np.zeros(nf)
mot[1:] = np.abs(np.diff(frames, axis=0)).mean(axis=(1,2))

# 1) The exact cut point: biggest motion spikes in seam +/- 1.0 s
m = (t > SEAM - 1.0) & (t < SEAM + 1.0)
idx = np.argsort(mot[m])[::-1][:8]
print("== Largest inter-frame diffs within +/-1.0 s of manifest seam ==")
for i in sorted(idx):
    print(f"  t={t[m][i]:9.3f} ({t[m][i]-SEAM:+.3f})  motion={mot[m][i]:7.2f}")

# 2) Profile at 100 ms bins: mean luma / variance / mean motion
print("\n== 100 ms bins: luma mean | luma var | motion ==")
for b in np.arange(SEAM - 2.0, SEAM + 2.0, 0.1):
    mm = (t >= b) & (t < b + 0.1)
    if mm.any():
        print(f"  {b:9.2f}  {mean[mm].mean():6.1f}  {var[mm].mean():7.1f}  {mot[mm].mean():6.2f}")

# 3) Side-by-side summary of the 2 s either side
for name, mm in [('act VI last 2s', (t >= SEAM-2.0) & (t < SEAM)),
                 ('perfume4 first 2s', (t >= SEAM) & (t < SEAM+2.0))]:
    print(f"\n{name}: luma {mean[mm].mean():.1f} (sd {mean[mm].std():.1f}), "
          f"var {var[mm].mean():.0f}, motion {mot[mm].mean():.2f} (sd {mot[mm].std():.2f})")
