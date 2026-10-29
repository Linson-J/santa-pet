"""Extract and install new Santa sprites at 200x300."""
import zipfile, io, os, sys
sys.path.insert(0, r'C:\Users\joell\santa-pet')
from PIL import Image

TARGET_W, TARGET_H = 200, 300
ZIP_PATH = r'C:\Users\joell\santa-pet\assets\santa_3d.zip'

ANIM_MAP = {
    'Walk':  'walk',
    'Idle':  'idle',
    'Jump':  'jump',
    'Run':   'run',
    'Slide': 'slide',
}

def crop_and_resize(img_rgba, tw, th):
    bbox = img_rgba.getbbox()
    if not bbox:
        return Image.new('RGBA', (tw, th), (0,0,0,0))
    content = img_rgba.crop(bbox)
    cw, ch  = content.size
    scale   = min(tw / cw, th / ch)
    nw, nh  = int(cw * scale), int(ch * scale)
    resized = content.resize((nw, nh), Image.LANCZOS)
    frame   = Image.new('RGBA', (tw, th), (0,0,0,0))
    ox      = (tw - nw) // 2
    oy      = th - nh
    frame.paste(resized, (ox, oy))
    return frame

with zipfile.ZipFile(ZIP_PATH) as z:
    for anim_name, folder in ANIM_MAP.items():
        out_dir = rf'C:\Users\joell\santa-pet\assets\{folder}'
        os.makedirs(out_dir, exist_ok=True)
        frames = sorted(
            [n for n in z.namelist() if n.startswith(f'png/{anim_name} (')],
            key=lambda n: int(n.split('(')[1].split(')')[0])
        )
        print(f'{anim_name} -> {folder}: {len(frames)} frames')
        for i, fname in enumerate(frames, 1):
            data  = z.read(fname)
            img   = Image.open(io.BytesIO(data)).convert('RGBA')
            frame = crop_and_resize(img, TARGET_W, TARGET_H)
            frame.save(rf'{out_dir}\{i}.png')

        # Also make flipped walk for walk_l
        if anim_name == 'Walk':
            out_dir_l = r'C:\Users\joell\santa-pet\assets\walk_l'
            os.makedirs(out_dir_l, exist_ok=True)
            for i, fname in enumerate(frames, 1):
                data  = z.read(fname)
                img   = Image.open(io.BytesIO(data)).convert('RGBA')
                img   = img.transpose(Image.FLIP_LEFT_RIGHT)
                frame = crop_and_resize(img, TARGET_W, TARGET_H)
                frame.save(rf'{out_dir_l}\{i}.png')
            print(f'Walk (flipped) -> walk_l: {len(frames)} frames')

print('All sprites installed!')
