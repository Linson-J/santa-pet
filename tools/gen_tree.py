"""Generate a beautiful 3D-style Christmas tree PNG."""
import math, random
from PIL import Image, ImageDraw, ImageFilter

TW, TH = 260, 380

def draw_ornament(draw, cx, cy, r, col):
    draw.ellipse([cx-r, cy-r+2, cx+r, cy+r+2], fill=(0,0,0,40))
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=col)
    hr = max(2, r//3)
    hx, hy = cx - r//3, cy - r//3
    draw.ellipse([hx-hr, hy-hr, hx+hr, hy+hr], fill=(255,255,255,160))
    draw.rectangle([cx-2, cy-r-4, cx+2, cy-r], fill=(100,70,30,220))

cx      = TW // 2
trunk_h = 35
trunk_w = 22
layers  = 5

total_tree_h = TH - trunk_h - 12
layer_heights = [int(total_tree_h * 0.20 * (1 + 0.12*i)) for i in range(layers)]
s = sum(layer_heights)
layer_heights = [int(h * total_tree_h / s) for h in layer_heights]
widths = [int(TW * (0.28 + 0.14*i)) for i in range(layers)]

layer_tops = []
y = 8
for i in range(layers):
    lh = layer_heights[i]
    lw = widths[i]
    layer_tops.append((y, lw, lh))
    y += int(lh * 0.68)

tree = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
draw = ImageDraw.Draw(tree)

# Trunk
ty = TH - trunk_h - 2
draw.rectangle([cx - trunk_w//2, ty, cx + trunk_w//2, TH-4], fill=(90, 55, 20, 255))
draw.rectangle([cx - trunk_w//2 + 3, ty, cx - trunk_w//2 + 6, TH-4], fill=(130, 80, 30, 255))

# Pine layers (bottom to top so upper ones paint over lower)
for i in reversed(range(layers)):
    top_y, lw, lh = layer_tops[i]
    half_w = lw // 2
    dark_g  = (18,  65,  22, 255)
    mid_g   = (35, 115,  40, 255)
    light_g = (55, 150,  58, 255)

    draw.polygon([(cx, top_y), (cx-half_w, top_y+lh), (cx+half_w, top_y+lh)], fill=mid_g)

    draw.polygon([
        (cx, top_y),
        (cx-half_w, top_y+lh),
        (cx-half_w//2, top_y+lh),
        (cx-half_w//3, top_y+lh//2)
    ], fill=dark_g)

    draw.polygon([
        (cx, top_y),
        (cx+half_w//3, top_y+lh//2),
        (cx+half_w, top_y+lh),
        (cx+half_w*2//3, top_y+lh)
    ], fill=(28, 90, 32, 255))

    draw.polygon([
        (cx-2, top_y+2),
        (cx-half_w//5, top_y+lh//2),
        (cx+half_w//5, top_y+lh//2),
        (cx+2, top_y+2)
    ], fill=light_g)

    snow_d = max(4, lh//7)
    draw.polygon([
        (cx-3, top_y),
        (cx-half_w, top_y+snow_d*2+4),
        (cx+half_w, top_y+snow_d*2+4),
        (cx+3, top_y)
    ], fill=(225, 235, 255, 200))
    draw.line([(cx-2, top_y+1), (cx+half_w//2, top_y+snow_d+1)], fill=(255,255,255,160), width=2)

# Ornaments
rng = random.Random(42)
ornament_colors = [
    (220, 40,  40,  240),
    (240, 180,  0,  240),
    (30,  120, 200, 240),
    (180, 30,  180, 240),
    (240, 100,  10, 240),
    (20,  160,  80, 230),
]
for i in range(layers):
    top_y, lw, lh = layer_tops[i]
    for _ in range(2 + i):
        frac_x = rng.uniform(0.22, 0.78)
        frac_y = rng.uniform(0.40, 0.85)
        ox = int(cx - lw/2 + frac_x * lw)
        oy = int(top_y + frac_y * lh)
        r  = 5 + i
        draw_ornament(draw, ox, oy, r, rng.choice(ornament_colors))

# Lights
light_cols = [(255,50,50,230),(255,220,0,230),(50,200,255,230),(150,255,50,230),(255,130,0,230)]
for i in range(layers):
    top_y, lw, lh = layer_tops[i]
    n_lights = 4 + i * 2
    for j in range(n_lights):
        t    = j / max(n_lights-1, 1)
        side = 1 if j % 2 == 0 else -1
        frac = t * 0.78 + 0.11
        lx   = int(cx + side * (lw//2) * frac)
        ly   = int(top_y + lh * 0.88)
        lc   = light_cols[j % len(light_cols)]
        draw.ellipse([lx-4, ly-4, lx+4, ly+4], fill=(lc[0],lc[1],lc[2],60))
        draw.ellipse([lx-2, ly-2, lx+2, ly+2], fill=lc)

# Star on top
star_cx, star_cy = cx, layer_tops[0][0] - 10
star_r  = 18
star_pts = []
for k in range(10):
    angle = math.pi/5 * k - math.pi/2
    r     = star_r if k%2==0 else star_r//2
    star_pts.extend([star_cx + r*math.cos(angle), star_cy + r*math.sin(angle)])

star_glow = Image.new('RGBA', (TW, TH), (0,0,0,0))
sg = ImageDraw.Draw(star_glow)
sg.polygon(star_pts, fill=(255,240,100,80))
star_glow = star_glow.filter(ImageFilter.GaussianBlur(radius=9))
tree = Image.alpha_composite(star_glow, tree)
draw = ImageDraw.Draw(tree)
draw.polygon(star_pts, fill=(255, 220, 0, 255))
draw.ellipse([star_cx-4, star_cy-4, star_cx+4, star_cy+4], fill=(255,255,200,255))

# Ground shadow
shadow = Image.new('RGBA', (TW, TH), (0,0,0,0))
sh = ImageDraw.Draw(shadow)
sh.ellipse([cx-58, TH-16, cx+58, TH-4], fill=(0,0,0,60))
shadow = shadow.filter(ImageFilter.GaussianBlur(radius=9))
final_tree = Image.alpha_composite(shadow, tree)

final_tree.save(r'C:\Users\joell\santa-pet\assets\christmas_tree.png')
print(f'Christmas tree saved: {final_tree.size}')
