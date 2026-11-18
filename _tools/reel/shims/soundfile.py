"""Minimal stand-in for the soundfile package (read/write WAV via scipy), used only where pip is unavailable."""
import numpy as np
from scipy.io import wavfile

def write(path, data, samplerate, subtype=None, **kw):
    a = np.asarray(data)
    if a.dtype.kind == "f":
        a = (np.clip(a, -1, 1) * 32767).astype(np.int16)
    wavfile.write(str(path), int(samplerate), a)

def read(path, dtype="float64", always_2d=False, **kw):
    sr, a = wavfile.read(str(path))
    if a.dtype.kind == "i":
        a = a.astype(dtype) / np.iinfo(a.dtype).max
    elif a.dtype.kind == "u":
        a = (a.astype(dtype) - 128) / 128
    else:
        a = a.astype(dtype)
    if always_2d and a.ndim == 1:
        a = a[:, None]
    return a, sr

class SoundFile:
    def __init__(self, path, *a, **k):
        self.data, self.samplerate = read(path)
        self.frames = len(self.data); self.channels = 1 if self.data.ndim == 1 else self.data.shape[1]
    def __enter__(self): return self
    def __exit__(self, *a): pass

def info(path):
    d, sr = read(path)
    class I: pass
    i = I(); i.samplerate = sr; i.frames = len(d); i.duration = len(d) / sr; i.channels = 1 if d.ndim == 1 else d.shape[1]
    return i
