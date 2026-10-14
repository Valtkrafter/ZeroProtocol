"""Seamless tile of vertical hair strands in the colours of Yoru's hair, used by the scalp shell (YoruScalpShell) that covers
the back of the head and the nape under the hair.

usage: python make_hair_strand_tile.py <hair strand png> <out png>
"""
import sys
import numpy as np
from PIL import Image

hair_path, out_path = sys.argv[1], sys.argv[2]
hair = np.array(Image.open(hair_path).convert('RGBA')).astype(np.float32)
hm = hair[..., 3] > 127
hr = hair[..., :3][hm]
dark = np.percentile(hr, 8, axis=0) * 0.94
mid = np.percentile(hr, 50, axis=0) * 0.97
light = np.percentile(hr, 84, axis=0)
print('palette dark', dark.round(0), 'mid', mid.round(0), 'light', light.round(0))

W = H = 256
rng = np.random.default_rng(11)


def wrap_noise(n, sigma, seed):
    g = np.random.default_rng(seed).standard_normal(n)
    # circular gaussian smoothing so the tile closes
    k = np.exp(-0.5 * (np.minimum(np.arange(n), n - np.arange(n)) / sigma) ** 2)
    k /= k.sum()
    s = np.real(np.fft.ifft(np.fft.fft(g) * np.fft.fft(k)))
    return (s - s.mean()) / (s.std() + 1e-6)


x = np.arange(W)
strand = 0.55 * wrap_noise(W, 2.2, 3) + 0.45 * wrap_noise(W, 0.8, 4)            # one value per column
yy = np.arange(H)[:, None].astype(np.float32)
phase = 2 * np.pi * wrap_noise(W, 6.0, 5)[None, :] * 0.15
vert = 0.22 * np.sin(2 * np.pi * yy / H * 1 + phase) + 0.10 * np.sin(2 * np.pi * yy / H * 3 + 2 * phase)   # whole cycles: tiles vertically
v = np.clip(0.50 + 0.17 * strand[None, :] + vert, 0, 1)
v3 = v[..., None]
col = np.where(v3 < 0.5, dark + (mid - dark) * (v3 / 0.5), mid + (light - mid) * ((v3 - 0.5) / 0.5))
out = np.zeros((H, W, 4), dtype=np.uint8)
out[..., :3] = np.clip(col, 0, 255).astype(np.uint8)
out[..., 3] = 255
Image.fromarray(out, 'RGBA').save(out_path)
print('wrote', out_path, 'mean', out[..., :3].reshape(-1, 3).mean(0).round(1))
