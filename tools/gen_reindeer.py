"""Generate a 4-frame cartoon reindeer running sprite (200x120 RGBA)."""
import os, math
from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = r'C:\Users\joell\santa-pet\assets\reindeer'
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 200, 120

# ── helpers ──────────────────────────────────────────────────────────────────
BROWN_DARK  = (100, 55, 15, 255)
BROWN_MID   = (155, 88, 28, 255)
BROWN_LIGHT = (195, 125, 55, 255)
BROWN_TIP   = (210, 145, 70, 255)
ANTLER      = (110, 65, 18, 255)
NOSE_RED    = (210, 35, 35, 255)
NOSE_HI     = (255, 110, 110, 180)
EYE_COL     = (18, 12, 8, 255)
EYE_HI      = (255, 255, 255, 220)
HOOF        = (45, 28, 10, 255)
BELLY       = (185, 145, 80, 255)
TAIL_COL    = (230, 210, 185, 255)

def ellipse(draw, cx, cy, rx, ry, fill, outline=None):
    draw.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=fill, outline=outline)

def leg(draw, x1, y1, x2, y2, w=6):
    draw.line([(x1, y1), (x2, y2)], fill=BROWN_MID, width=w)
    ellipse(draw, x2, y2, 5, 3, HOOF)

def antler(draw, bx, by):
    # Main stem
    draw.line([(bx, by), (bx-4, by-22)], fill=ANTLER, width=4)
    # Branch 1
    draw.line([(bx-2, by-14), (bx-14, by-22)], fill=ANTLER, width=3)
    draw.line([(bx-14, by-22), (bx-18, by-18)], fill=ANTLER, width=2)
    # Branch 2
    draw.line([(bx-3, by-18), (bx-6, by-28)], fill=ANTLER, width=3)
    draw.line([(bx-6, by-28), (bx-10, by-25)], fill=ANTLER, width=2)
    # Tip
    draw.line([(bx-4, by-22), (bx+2, by-28)], fill=ANTLER, width=3)

def harness(draw, bx, by):
    # Red collar/harness
    draw.line([(bx+8, by-18), (bx+20, by-14), (bx+28, by-8)], fill=(200,35,35,220), width=4)
    # Gold bell
    ellipse(draw, bx+20, by-14, 5, 5, (220, 185, 0, 255))
    ellipse(draw, bx+20, by-14, 3, 3, (255, 230, 80, 200))

# Leg positions for 4-frame gallop cycle
# (front-left, front-right, back-left, back-right)
# Each leg = (x_offset, y_length) from body bottom
GAITS = [
    # frame 0: stride open - front right/back left forward, others back
    [(-35, 40, -28, 55), (-18, 42, -8, 60), (10, 42, 20, 60), (28, 38, 22, 54)],
    # frame 1: gathering - legs coming in
    [(-33, 42, -30, 57), (-15, 44, -12, 60), (8, 44, 12, 60), (26, 40, 24, 56)],
    # frame 2: stride open reversed - front left/back right forward
    [(-30, 42, -22, 60), (-22, 40, -14, 56), (14, 40, 24, 56), (20, 42, 28, 60)],
    # frame 3: gathering other side
    [(-32, 42, -26, 58), (-20, 42, -16, 58), (12, 42, 18, 58), (22, 42, 26, 58)],
]

def draw_frame(fi):
    img  = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Body centre
    bx, by = 90, 62

    # ── legs (draw behind body) ──────────────────────────────
    gait = GAITS[fi]
    for (ox1, oy1, ox2, oy2) in gait:
        leg(draw, bx+ox1, by+oy1, bx+ox2, by+oy2)

    # ── tail ────────────────────────────────────────────────
    ellipse(draw, bx-50, by+5, 10, 7, TAIL_COL)
    ellipse(draw, bx-50, by+4, 6, 5, (245, 235, 220, 255))

    # ── body (shadow layer) ──────────────────────────────────
    ellipse(draw, bx, by+4, 52, 26, (70, 38, 10, 120))
    # body main
    ellipse(draw, bx, by, 52, 26, BROWN_MID)
    # body top highlight
    ellipse(draw, bx+4, by-12, 38, 12, BROWN_LIGHT)
    # belly lighter
    ellipse(draw, bx, by+14, 40, 10, BELLY)

    # ── neck ────────────────────────────────────────────────
    pts = [(bx+30, by-18), (bx+44, by-22), (bx+52, by+6), (bx+38, by+4)]
    draw.polygon(pts, fill=BROWN_MID)
    # neck highlight
    pts2 = [(bx+34, by-18), (bx+45, by-22), (bx+50, by-6), (bx+38, by-8)]
    draw.polygon(pts2, fill=BROWN_LIGHT)

    # ── head ────────────────────────────────────────────────
    hx, hy = bx+62, by-30
    ellipse(draw, hx, hy, 18, 14, BROWN_MID)
    ellipse(draw, hx-2, hy-6, 14, 8, BROWN_LIGHT)  # forehead highlight

    # snout
    ellipse(draw, hx+12, hy+4, 9, 7, BROWN_DARK)
    # Rudolph nose!
    ellipse(draw, hx+19, hy+5, 7, 6, NOSE_RED)
    ellipse(draw, hx+18, hy+3, 3, 2, NOSE_HI)    # shine

    # ear
    pts_ear = [(hx-8, hy-13), (hx-2, hy-22), (hx+6, hy-14)]
    draw.polygon(pts_ear, fill=BROWN_MID)
    draw.polygon([(hx-5, hy-13), (hx, hy-20), (hx+4, hy-14)],
                 fill=(200, 145, 80, 200))

    # eye
    ellipse(draw, hx+3, hy-4, 5, 5, EYE_COL)
    ellipse(draw, hx+4, hy-6, 2, 2, EYE_HI)

    # ── antlers ─────────────────────────────────────────────
    antler(draw, hx-4, hy-13)

    # ── harness / bell ──────────────────────────────────────
    harness(draw, bx, by)

    # ── glow on nose ────────────────────────────────────────
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    gd.ellipse([hx+12, hy-1, hx+26, hy+11], fill=(255, 40, 40, 70))
    glow_b = glow.filter(ImageFilter.GaussianBlur(radius=5))
    img = Image.alpha_composite(glow_b, img)

    return img

for fi in range(4):
    frame = draw_frame(fi)
    frame.save(rf'{OUT_DIR}\{fi+1}.png')
    print(f'Frame {fi+1} saved: {frame.size}')

print('Reindeer sprites done!')
