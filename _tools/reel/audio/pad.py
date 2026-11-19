"""Original ambient pad (no samples, no license needed): pad.py out.wav seconds [seed]"""
import sys, numpy as np
from scipy.io import wavfile
out, dur = sys.argv[1], float(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
sr = 48000; t = np.arange(int(sr * dur)) / sr
chords = [[110.0, 164.81, 196.0, 246.94, 329.63], [87.31, 130.81, 174.61, 220.0, 261.63],
          [98.0, 146.83, 196.0, 246.94, 293.66], [73.42, 110.0, 146.83, 174.61, 220.0]]
rng = np.random.default_rng(seed); order = rng.permutation(len(chords))
seg = dur / 2; sig = np.zeros_like(t)
for i in range(2):
    ch = chords[order[i]]; a, b = i * seg, (i + 1) * seg
    env = np.clip((t - a + 1.2) / 1.2, 0, 1) * np.clip((b + 1.2 - t) / 1.2, 0, 1)
    for k, f in enumerate(ch):
        det = 1 + rng.uniform(-0.002, 0.002)
        sig += env * (np.sin(2*np.pi*f*det*t) + 0.3*np.sin(2*np.pi*2*f*det*t + k)) / (1 + 0.4*k)
sig *= 1 + 0.15 * np.sin(2*np.pi*0.25*t)
k = np.ones(64) / 64; sig = np.convolve(sig, k, mode="same")
fade = np.minimum(1, np.minimum(t / 0.8, (dur - t) / 1.2)); sig *= np.clip(fade, 0, 1)
sig = sig / (np.abs(sig).max() + 1e-9) * 0.5
st = np.stack([sig, np.roll(sig, 240)], 1)
wavfile.write(out, sr, (st * 32767).astype(np.int16))
