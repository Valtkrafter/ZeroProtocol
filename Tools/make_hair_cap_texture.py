"""Builds the under-hair cap texture of Yoru (VRoid exported it in the default brown) in the colours of the hair strands,
with strands that run from the crown down and out, like real hair.

usage: python make_hair_cap_texture.py <old cap png (RGBA, the alpha gives the shape)> <hair strand png> <out png>
The shape (alpha) is taken over unchanged; the colours come from the hair texture (dark / middle / light tones).
"""
import sys
import numpy as np
from PIL import Image

cap_path, hair_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
cap = np.array(Image.open(cap_path).convert('RGBA')).astype(np.float32)
hair = np.array(Image.open(hair_path).convert('RGBA')).astype(np.float32)
H, W = cap.shape[:2]
alpha = cap[..., 3]

# palette from the strand texture: dark = 8th percentile, middle = median, light = 82nd percentile
hm = hair[..., 3] > 127
hr = hair[..., :3][hm]
dark = np.percentile(hr, 8, axis=0) * 0.92          # a little darker: it is the layer UNDER the visible hair
mid = np.percentile(hr, 50, axis=0) * 0.96
light = np.percentile(hr, 82, axis=0)
print('palette dark', dark.round(0), 'mid', mid.round(0), 'light', light.round(0))

rng = np.random.default_rng(7)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
cx, cy = W * 0.5, H * 0.115                            # crown of the cap (top of the silhouette)
dx, dy = xx - cx, yy - cy
r = np.hypot(dx, dy)
rmax = r[alpha > 127].max()
t = np.clip(r / rmax, 0, 1)                            # 0 at the crown, 1 at the far edge
theta = np.arctan2(dx, dy)                             # 0 = straight down


def smooth_noise(n, sigma, seed):
    g = np.random.default_rng(seed).standard_normal(n + 64)
    k = np.exp(-0.5 * (np.arange(-24, 25) / sigma) ** 2)
    k /= k.sum()
    s = np.convolve(g, k, mode='same')[32:32 + n]
    s = (s - s.mean()) / (s.std() + 1e-6)
    return s


def sample_angle(arr, th):
    # periodic lookup of a 1-D array over theta in [-pi, pi]
    n = len(arr)
    x = (th + np.pi) / (2 * np.pi) * n
    i0 = np.floor(x).astype(int) % n
    i1 = (i0 + 1) % n
    f = x - np.floor(x)
    return arr[i0] * (1 - f) + arr[i1] * f


n_bins = 900
coarse = smooth_noise(n_bins, 3.0, 1)                  # broad locks
fine = smooth_noise(n_bins, 1.0, 2)                    # single strands
wave = 0.035 * np.sin(r / 55.0 + 1.3) + 0.02 * np.sin(r / 23.0 + 0.4)   # strands are not ruler straight
th2 = theta + wave
strand = 0.62 * sample_angle(coarse, th2) + 0.38 * sample_angle(fine, th2)

# light from the top, darker at the crown, lighter towards the ends (like the strand texture), strands on top
base = 0.30 + 0.55 * np.clip((t - 0.05) / 0.85, 0, 1) ** 0.9
v = np.clip(base + 0.16 * strand * (0.55 + 0.45 * t), 0, 1)

# map 0..1 through dark -> mid -> light
v3 = v[..., None]
low = (v3 < 0.5)
col = np.where(low, dark + (mid - dark) * (v3 / 0.5), mid + (light - mid) * ((v3 - 0.5) / 0.5))

out = np.zeros((H, W, 4), dtype=np.uint8)
out[..., :3] = np.clip(col, 0, 255).astype(np.uint8)
out[..., 3] = alpha.astype(np.uint8)
# keep colour under the transparent border too (avoids dark fringes when the texture is filtered)
Image.fromarray(out, 'RGBA').save(out_path)
print('wrote', out_path, out.shape, 'mean colour of the opaque part', out[..., :3][alpha > 127].mean(0).round(1))
