from PIL import Image
import random

im = Image.open("avatar.png").convert("RGB").resize((80, 80))
px = list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata())
random.seed(7)
centers = random.sample(px, 5)

def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))

for _ in range(12):
    groups = [[] for _ in centers]
    for p in px:
        best = min(range(5), key=lambda i: dist(p, centers[i]))
        groups[best].append(p)
    new_centers = []
    for i, g in enumerate(groups):
        if g:
            n = len(g)
            new_centers.append(tuple(sum(ch) // n for ch in zip(*g)))
        else:
            new_centers.append(centers[i])
    centers = new_centers

hexes = ["#%02x%02x%02x" % c for c in centers]

def lum(h):
    r, g, b = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

for h in hexes:
    print(h, "lum=%.3f" % lum(h), "vs-white=%.2f" % contrast(h, "#ffffff"), "vs-black=%.2f" % contrast(h, "#000000"))
