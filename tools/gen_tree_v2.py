"""Generate an improved 3D Christmas tree using scan-line gradient shading."""
import math, random
from PIL import Image, ImageDraw, ImageFilter

TW, TH = 280, 400
cx = TW // 2

def draw_ornament(draw, ox, oy, r, col):
    draw.ellipse([ox-r, oy-r+2, ox+r, oy+r+2], fill=(0,0,0,50))
    draw.ellipse([ox-r, oy-r, ox+r, oy+r], fill=col)
    draw.ellipse([ox-r//3-2, oy-r//3-2, ox-r//3+3, oy-r//3+3],
                 fill=(255, 255, 255, 170))
    draw.rectangle([ox-2, oy-r-5, ox+2, oy-r], fill=(100, 68, 22, 220))

def draw_pine_layer(img_draw, img, layer_cx, top_y, half_w, height, light_side='right'):
    """Scan-line rendered pine layer with gradient shading."""
    for yi in range(height):
        t = yi / max(height - 1, 1)
        # Current width at this scan line
        w = max(1, int(half_w * t))

        # Base green changes per row for subtle gradient
        g_base = int(105 - t * 18)   # slightly darker lower
        r_base = int(22 + t * 8)

        for xi in range(-w, w + 1):
            # Normalised position: -1=left edge, 0=centre, +1=right edge
            xn = xi / max(w, 1)

            # diffuse shading: lit from upper-right
            diffuse  = 1.0 - 0.35 * abs(xn)           # bright centre
            shadow_l = 0.70 if xn < -0.4 else 1.0     # left shadow
            hilight  = 1.15 if xn > 0.2 else 1.0      # right highlight
            factor   = diffuse * shadow_l * hilight
            factor   = max(0.45, min(1.25, factor))

            r = max(0, min(255, int(r_base * factor)))
            g = max(0, min(255, int(g_base * factor)))
            b = max(0, min(255, int(25 * factor)))
            img_draw.point([layer_cx + xi, top_y + yi], fill=(r, g, b, 255))

    # Snow cap on top of this layer
    snow_h = max(3, height // 7)
    for yi in range(snow_h * 2):
        t2    = yi / max(snow_h * 2 - 1, 1)
        sw    = max(1, int(half_w * (t2 * 0.6)))
        alpha = int(200 * (1 - t2 * 0.4))
        img_draw.line([layer_cx - sw, top_y + yi, layer_cx + sw, top_y + yi],
                      fill=(230, 238, 255, alpha))


# ── Build tree ───────────────────────────────────────────────────────────────
tree = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
draw = ImageDraw.Draw(tree)

layers    = 5
trunk_h   = 38
trunk_w   = 24
tree_h    = TH - trunk_h - 12

layer_heights = [int(tree_h * (0.18 + 0.06 * i)) for i in range(layers)]
s = sum(layer_heights)
layer_heights = [int(h * tree_h / s) for h in layer_heights]

widths = [int(TW * (0.25 + 0.14 * i)) for i in range(layers)]

layer_tops = []
y = 6
for i in range(layers):
    layer_tops.append((y, widths[i], layer_heights[i]))
    y += int(layer_heights[i] * 0.68)

# Draw trunk first
ty = TH - trunk_h - 2
draw.rectangle([cx - trunk_w//2, ty, cx + trunk_w//2, TH - 3],
               fill=(85, 50, 18, 255))
draw.rectangle([cx - trunk_w//2 + 4, ty, cx - trunk_w//2 + 8, TH - 3],
               fill=(125, 78, 30, 255))

# Draw pine layers (bottom to top so top paints over lower)
for i in reversed(range(layers)):
    top_y, lw, lh = layer_tops[i]
    draw_pine_layer(draw, tree, cx, top_y, lw // 2, lh)

# ── Ornaments ────────────────────────────────────────────────────────────────
rng = random.Random(7)
ORN_COLS = [
    (215, 35,  35,  245),
    (235, 175,  0,  245),
    (25,  115, 200, 245),
    (175, 25,  175, 245),
    (235,  95,  10, 245),
    (15,  155,  75, 230),
]
for i in range(layers):
    top_y, lw, lh = layer_tops[i]
    for _ in range(2 + i):
        fx = rng.uniform(0.20, 0.80)
        fy = rng.uniform(0.38, 0.88)
        ox = int(cx - lw/2 + fx * lw)
        oy = int(top_y + fy * lh)
        r  = 5 + i
        draw_ornament(draw, ox, oy, r, rng.choice(ORN_COLS))

# ── String lights ─────────────────────────────────────────────────────────────
LIGHT_COLS = [
    (255, 50,  50,  235),
    (255, 215,  0,  235),
    (50,  200, 255, 235),
    (140, 255,  50, 235),
    (255, 130,   0, 235),
]
for i in range(layers):
    top_y, lw, lh = layer_tops[i]
    n = 4 + i * 2
    for j in range(n):
        t    = j / max(n - 1, 1)
        side = 1 if j % 2 == 0 else -1
        frac = t * 0.76 + 0.12
        lx   = int(cx + side * (lw // 2) * frac)
        ly   = int(top_y + lh * 0.87)
        lc   = LIGHT_COLS[j % len(LIGHT_COLS)]
        # glow halo
        draw.ellipse([lx-5, ly-5, lx+5, ly+5], fill=(lc[0], lc[1], lc[2], 55))
        draw.ellipse([lx-2, ly-2, lx+2, ly+2], fill=lc)
        # small reflection
        draw.ellipse([lx-1, ly-2, lx+1, ly-1], fill=(255, 255, 255, 160))

# ── Star on top ──────────────────────────────────────────────────────────────
scx, scy = cx, layer_tops[0][0] - 12
sr  = 20
pts = []
for k in range(10):
    ang = math.pi / 5 * k - math.pi / 2
    r   = sr if k % 2 == 0 else sr // 2
    pts.extend([scx + r * math.cos(ang), scy + r * math.sin(ang)])

# Glow behind star
glow = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
gd   = ImageDraw.Draw(glow)
gd.polygon(pts, fill=(255, 240, 100, 90))
glow = glow.filter(ImageFilter.GaussianBlur(radius=12))
tree = Image.alpha_composite(glow, tree)
draw = ImageDraw.Draw(tree)

draw.polygon(pts, fill=(255, 215, 0, 255))
# Star centre shine
draw.ellipse([scx-5, scy-5, scx+5, scy+5], fill=(255, 255, 200, 255))

# ── Ground shadow ─────────────────────────────────────────────────────────────
shadow = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
sd     = ImageDraw.Draw(shadow)
sd.ellipse([cx - 65, TH - 16, cx + 65, TH - 3], fill=(0, 0, 0, 65))
shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
final  = Image.alpha_composite(shadow, tree)

final.save(r'C:\Users\joell\santa-pet\assets\christmas_tree.png')
print(f'Improved tree saved: {final.size}')
