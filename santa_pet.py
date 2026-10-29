"""Santa Pet 3D — dancing desktop companion"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading, random, os, glob, psutil, shutil, tempfile, math
from datetime import datetime
from todo_manager import TodoWindow

try:
    import sv_ttk
    _HAS_SVTTK = True
except ImportError:
    _HAS_SVTTK = False

try:
    import pywinstyles
    _HAS_PYWINSTYLES = True
except ImportError:
    _HAS_PYWINSTYLES = False

TR = (0, 0, 0, 0)
W, H, CX = 200, 300, 100

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


# ─────────────────────────── SPRITE LOADER ──────────────────

def _load_anim(folder, flip=False):
    """Load PNG sequence from assets/<folder>/, return list of (W×H) RGBA images."""
    d = os.path.join(_ASSETS, folder)
    files = sorted(glob.glob(os.path.join(d, '*.png')),
                   key=lambda p: int(os.path.splitext(os.path.basename(p))[0]))
    frames = []
    for fp in files:
        sprite = Image.open(fp).convert('RGBA')
        if sprite.size == (W, H):
            frame = sprite
        else:
            sw, sh = sprite.size
            frame = Image.new('RGBA', (W, H), TR)
            x = (W - sw) // 2
            y = H - sh
            frame.paste(sprite, (x, y), sprite)
        if flip:
            frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
        frames.append(frame)
    return frames


def _build_anims():
    walk_r = _load_anim('walk')
    walk_l = _load_anim('walk_l')   # pre-flipped folder
    idle   = _load_anim('idle')
    shimmy = _load_anim('jump')
    wave   = _load_anim('slide')
    groove = _load_anim('run')

    return {
        'walk_r': walk_r,
        'walk_l': walk_l,
        'idle':   idle,
        'shimmy': shimmy,
        'wave':   wave,
        'groove': groove,
    }


ANIM = _build_anims()

DANCE_NAMES  = ['shimmy', 'wave', 'groove']
DANCE_QUIPS  = {
    'shimmy': ["🕺 Shimmy!", "Santa shuffle!", "Ho Ho Shake!"],
    'wave':   ["👋 Ho Ho Ho!", "Waving! 🎄", "Hello! 🎅"],
    'groove': ["🎵 Feeling it!", "Jingle boogie! 🔔", "Groovin'! 🎶"],
}


# ─────────────────────────── PC HEALTH ───────────────────────

class PCHealth:
    def show(self, parent):
        win = tk.Toplevel(parent)
        win.title("PC Doctor — Health Report")
        win.geometry("480x580")
        win.resizable(True, True)
        win.attributes('-topmost', True)
        win.configure(bg=BG0)
        _apply_win11(win)
        hdr = tk.Frame(win, bg=BG1, pady=12)
        hdr.pack(fill='x')
        tk.Label(hdr, text="🏥  PC Doctor", font=('Segoe UI Variable', 15, 'bold'),
                 bg=BG1, fg=ACC).pack()
        tk.Label(hdr, text=datetime.now().strftime('%Y-%m-%d  %H:%M:%S'),
                 font=('Segoe UI Variable', 9), bg=BG1, fg=SUB).pack()
        container = tk.Frame(win, bg=BG0)
        container.pack(fill='both', expand=True)
        cv = tk.Canvas(container, bg=BG0, highlightthickness=0)
        sb = ttk.Scrollbar(container, orient='vertical', command=cv.yview)
        frm = tk.Frame(cv, bg=BG0)
        frm.bind('<Configure>', lambda e: cv.configure(scrollregion=cv.bbox('all')))
        cv.create_window((0, 0), window=frm, anchor='nw')
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        def sec(t):
            f = tk.Frame(frm, bg=BG1, pady=6, padx=10)
            f.pack(fill='x', padx=10, pady=(10, 2))
            tk.Label(f, text=t, font=('Segoe UI Variable', 10, 'bold'),
                     bg=BG1, fg=ACC).pack(anchor='w')

        def row(label, val, pct=None):
            f = tk.Frame(frm, bg=BG1, padx=12, pady=6)
            f.pack(fill='x', padx=10, pady=1)
            color = GRN if (pct or 0) < 60 else YEL if (pct or 0) < 85 else RED_C
            tk.Label(f, text=label, font=('Segoe UI Variable', 9), bg=BG1,
                     fg=FG, width=22, anchor='w').grid(row=0, column=0)
            tk.Label(f, text=val, font=('Segoe UI Variable', 9, 'bold'),
                     bg=BG1, fg=color).grid(row=0, column=1, padx=10)
            if pct is not None:
                bar = tk.Canvas(f, width=110, height=6, bg=BOR, highlightthickness=0)
                bar.grid(row=0, column=2, padx=5)
                bar.create_rectangle(0, 0, pct * 1.1, 6, fill=color, width=0)

        sec("⚡ Processor")
        cpu = psutil.cpu_percent(interval=0.3)
        row("CPU Usage", f"{cpu:.1f}%", int(cpu))
        row("Cores / Threads", f"{psutil.cpu_count(False)} / {psutil.cpu_count()}")
        sec("💾 Memory")
        m = psutil.virtual_memory()
        row("RAM Usage", f"{m.percent:.1f}%", int(m.percent))
        row("Available", f"{m.available/2**30:.1f} GB")
        sec("💿 Storage")
        for p2 in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p2.mountpoint)
                row(p2.device, f"{u.percent:.1f}%  ({u.free/2**30:.1f} GB free)", int(u.percent))
            except Exception:
                pass
        sec("🔋 Battery")
        try:
            bat = psutil.sensors_battery()
            if bat:
                row("Charge", f"{bat.percent:.0f}%", int(bat.percent))
                row("Power", "Plugged ⚡" if bat.power_plugged else "Battery 🔋")
            else:
                row("Battery", "Desktop / n/a")
        except Exception:
            row("Battery", "Not available")
        sec("🌐 Network I/O")
        try:
            n = psutil.net_io_counters()
            row("Sent",     f"{n.bytes_sent/2**20:.1f} MB")
            row("Received", f"{n.bytes_recv/2**20:.1f} MB")
        except Exception:
            pass
        sec("⏱ System")
        try:
            up = datetime.now() - datetime.fromtimestamp(psutil.boot_time())
            h, r = divmod(int(up.total_seconds()), 3600)
            row("Uptime",    f"{h}h {r//60}m")
            row("Processes", str(len(psutil.pids())))
        except Exception:
            pass
        _styled_btn(win, "Close", win.destroy, accent=True).pack(pady=12)


# ─────────────────────────── CACHE CLEANER ───────────────────

class CacheCleaner:
    def _locations(self):
        up = os.environ.get('USERPROFILE', os.path.expanduser('~'))
        spots = [
            ('Windows Temp',  os.environ.get('TEMP', tempfile.gettempdir())),
            ('User Temp',     os.path.join(up, 'AppData', 'Local', 'Temp')),
            ('System Temp',   r'C:\Windows\Temp'),
            ('Chrome Cache',  os.path.join(up, 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache')),
            ('Edge Cache',    os.path.join(up, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache')),
            ('Firefox Cache', os.path.join(up, 'AppData', 'Local', 'Mozilla', 'Firefox', 'Profiles')),
            ('Thumbnails',    os.path.join(up, 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer')),
        ]
        return [(n, p) for n, p in spots if os.path.exists(p)]

    @staticmethod
    def _size(path):
        t = 0
        try:
            for rt, _, fs in os.walk(path):
                for f in fs:
                    try: t += os.path.getsize(os.path.join(rt, f))
                    except: pass
        except: pass
        return t

    @staticmethod
    def _fmt(b):
        if b < 2**20:  return f"{b/1024:.0f} KB"
        if b < 2**30:  return f"{b/2**20:.1f} MB"
        return f"{b/2**30:.2f} GB"

    @staticmethod
    def _wipe(path):
        ok = err = 0
        try:
            for item in os.listdir(path):
                fp = os.path.join(path, item)
                try:
                    if os.path.isfile(fp):  os.unlink(fp);          ok += 1
                    elif os.path.isdir(fp): shutil.rmtree(fp, True); ok += 1
                except: err += 1
        except: err += 1
        return ok, err

    def show(self, parent):
        win = tk.Toplevel(parent)
        win.title("🧹 Cache Cleaner")
        win.geometry("520x560")
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.configure(bg=BG0)
        _apply_win11(win)
        hdr = tk.Frame(win, bg=BG1, pady=12)
        hdr.pack(fill='x')
        tk.Label(hdr, text="🧹  Santa's Cache Cleaner",
                 font=('Segoe UI Variable', 14, 'bold'), bg=BG1, fg=ACC).pack()
        lf = tk.Frame(win, bg=BG0)
        lf.pack(fill='both', expand=True, padx=12, pady=8)
        sv = tk.StringVar(value="Scanning…")
        tv = tk.StringVar(value="Total: —")
        tk.Label(win, textvariable=sv, font=('Segoe UI Variable', 9), bg=BG0, fg=SUB).pack()
        tk.Label(win, textvariable=tv, font=('Segoe UI Variable', 12, 'bold'), bg=BG0, fg=GRN).pack(pady=3)
        pg = ttk.Progressbar(win, mode='indeterminate')
        pg.pack(fill='x', padx=16, pady=4)
        pg.start()
        bf = tk.Frame(win, bg=BG0)
        bf.pack(pady=8)
        cb_vars = {}
        clean_btn = _styled_btn(bf, "🧹 Clean Selected", None, danger=True)
        clean_btn.config(state='disabled')
        clean_btn.pack(side='left', padx=6)
        _styled_btn(bf, "Close", win.destroy).pack(side='left', padx=6)

        def scan():
            locs = self._locations()
            total = 0
            for w2 in lf.winfo_children(): w2.destroy()
            cb_vars.clear()
            pg.stop(); pg.config(mode='determinate', value=0)
            for name, path in locs:
                sz = self._size(path); total += sz
                var = tk.BooleanVar(value=True)
                cb_vars[path] = var
                row = tk.Frame(lf, bg=BG1, padx=10, pady=7)
                row.pack(fill='x', pady=2)
                tk.Checkbutton(row, variable=var, bg=BG1,
                               activebackground=BG1, selectcolor=BG2).pack(side='left')
                tk.Label(row, text=name, font=('Segoe UI Variable', 10, 'bold'),
                         bg=BG1, fg=FG, width=22, anchor='w').pack(side='left')
                color = RED_C if sz > 100*2**20 else YEL if sz > 5*2**20 else GRN
                tk.Label(row, text=self._fmt(sz), font=('Segoe UI Variable', 10),
                         bg=BG1, fg=color).pack(side='right', padx=8)
            tv.set(f"Total found: {self._fmt(total)}")
            sv.set(f"{len(locs)} locations scanned")
            clean_btn.config(state='normal')

        def do_clean():
            if not messagebox.askyesno("Confirm", "Delete selected cache files?", parent=win): return
            clean_btn.config(state='disabled')
            pg.config(mode='indeterminate'); pg.start()
            sv.set("Cleaning…")
            def worker():
                tok = terr = 0
                for path, var in cb_vars.items():
                    if var.get() and os.path.exists(path):
                        ok, err = self._wipe(path); tok += ok; terr += err
                win.after(0, lambda: (pg.stop(), sv.set(f"Done — {tok} removed, {terr} skipped"),
                                      tv.set("Re-scan to refresh"),
                                      messagebox.showinfo("Done! 🎉",
                                          f"✅ {tok} items removed\n⚠️ {terr} in use/locked", parent=win)))
            threading.Thread(target=worker, daemon=True).start()

        clean_btn.config(command=do_clean)
        win.after(200, scan)


# ─────────────────────────── WATER POPUP ─────────────────────

class WaterPopup:
    def show(self, parent):
        w = tk.Toplevel(parent)
        w.title("Hydration Reminder")
        cx = w.winfo_screenwidth()//2 - 170
        cy = w.winfo_screenheight()//2 - 120
        w.geometry(f"360x250+{cx}+{cy}")
        w.resizable(False, False)
        w.attributes('-topmost', True)
        w.configure(bg=BG0)
        _apply_win11(w)

        hdr = tk.Frame(w, bg=BG1, pady=14)
        hdr.pack(fill='x')
        tk.Label(hdr, text="💧", font=('Segoe UI Emoji', 40), bg=BG1).pack()
        tk.Label(hdr, text="Time to Drink Water!",
                 font=('Segoe UI Variable', 14, 'bold'), bg=BG1, fg=ACC).pack(pady=(2, 0))

        tk.Frame(w, height=1, bg=BOR).pack(fill='x')
        tk.Label(w, text="Santa says: Stay hydrated! 🥤",
                 font=('Segoe UI Variable', 10), bg=BG0, fg=SUB).pack(pady=14)

        _styled_btn(w, "Thanks Santa! 🎅", w.destroy, accent=True).pack(pady=10)
        w.after(30000, lambda: w.destroy() if w.winfo_exists() else None)


# ─── shared overlay helper ───────────────────────────────────
_CHROMA = '#010101'   # near-black colour key — used as transparent bg

def _make_overlay(parent, w, h, x, y):
    """Create a borderless topmost overlay window with transparent bg."""
    win = tk.Toplevel(parent)
    win.overrideredirect(True)
    win.attributes('-topmost', True)
    win.configure(bg=_CHROMA)
    win.geometry(f"{w}x{h}+{x}+{y}")
    return win

def _apply_chroma(win):
    """Apply chroma-key transparency + click-through to an overlay window."""
    win.update()
    # Visual transparency: tkinter's attribute calls SetLayeredWindowAttributes
    # on the correct TkTopLevel HWND (winfo_id returns TkChild which is wrong for Win32 direct calls)
    win.attributes('-transparentcolor', _CHROMA)
    win.update()
    # Click-through: WS_EX_TRANSPARENT on the parent (TkTopLevel) HWND
    try:
        import ctypes
        GWL_EXSTYLE       = -20
        WS_EX_TRANSPARENT = 0x00000020
        child_hwnd  = win.winfo_id()
        parent_hwnd = ctypes.windll.user32.GetParent(child_hwnd)
        for hwnd in ([parent_hwnd] if parent_hwnd else []) + [child_hwnd]:
            ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_TRANSPARENT)
    except Exception:
        pass


# ─────────────────────────── EXTRA COMPANIONS ────────────────

class SleighFlyby:
    """Santa's sleigh flies across the screen once and disappears."""
    def __init__(self, parent):
        self._parent = parent
        self._active = False

    def fly(self):
        if self._active:
            return
        self._active = True
        sw = self._parent.winfo_screenwidth()
        sh = self._parent.winfo_screenheight()
        y  = sh // 5
        win = _make_overlay(self._parent, 160, 80, -170, y)
        tk.Label(win, text='🛷🦌', font=('Segoe UI Emoji', 44),
                 bg=_CHROMA).pack(pady=4)
        _apply_chroma(win)
        self._move(win, -170, y, sw + 180, step=16)

    def _move(self, win, x, y, end_x, step):
        if not win.winfo_exists():
            self._active = False
            return
        if x > end_x:
            win.destroy()
            self._active = False
            return
        win.geometry(f"160x80+{x}+{y}")
        win.after(22, lambda: self._move(win, x + step, y, end_x, step))


class ReindeerDash:
    """A reindeer runs across the screen using an animated PIL sprite."""
    RW, RH   = 200, 120
    STEP     = 16    # px per tick
    TICK_MS  = 18    # ms per tick

    def __init__(self, parent):
        self._parent = parent
        self._frames = []
        d     = os.path.join(_ASSETS, 'reindeer')
        files = sorted(glob.glob(os.path.join(d, '*.png')),
                       key=lambda p: int(os.path.splitext(os.path.basename(p))[0]))
        for fp in files:
            self._frames.append(ImageTk.PhotoImage(Image.open(fp).convert('RGBA')))

    def dash(self):
        if not self._frames or getattr(self, '_active', False):
            return
        self._active = True
        sw = self._parent.winfo_screenwidth()
        sh = self._parent.winfo_screenheight()
        y  = sh - self.RH - 55
        win = _make_overlay(self._parent, self.RW, self.RH, -self.RW - 10, y)
        cv  = tk.Canvas(win, width=self.RW, height=self.RH,
                         bg=_CHROMA, highlightthickness=0)
        cv.pack()
        img_id = cv.create_image(0, 0, anchor='nw', image=self._frames[0])
        _apply_chroma(win)
        self._move(win, cv, img_id, -self.RW - 10, y, sw + self.RW + 20, 0, 0)

    def _move(self, win, cv, img_id, x, y, end_x, fi, tick):
        if not win.winfo_exists():
            self._active = False
            return
        if x > end_x:
            win.destroy()
            self._active = False
            return
        win.geometry(f"{self.RW}x{self.RH}+{x}+{y}")
        if tick % 5 == 0:
            fi = (fi + 1) % len(self._frames)
            cv.itemconfig(img_id, image=self._frames[fi])
        win.after(self.TICK_MS,
                  lambda: self._move(win, cv, img_id, x + self.STEP, y, end_x, fi, tick+1))


class ChristmasTree:
    """A stationary Christmas tree using a real rendered PNG image."""

    _STAR_CX = 140   # star x within the 280×400 image
    _STAR_CY = 26    # star y within the 280×400 image

    def __init__(self, parent):
        self._parent  = parent
        self._win     = None
        self._canvas  = None
        self._active  = False
        self._tk_img  = None
        self._glow_id = None

        tree_path = os.path.join(_ASSETS, 'christmas_tree.png')
        if os.path.exists(tree_path):
            self._pil   = Image.open(tree_path).convert('RGBA')
            self._tw, self._th = self._pil.size
        else:
            self._pil   = None
            self._tw, self._th = 120, 180

    @property
    def active(self):
        return self._active

    def toggle(self):
        self.remove() if self._active else self.place()

    def place(self):
        if self._active:
            return
        self._active = True
        sw = self._parent.winfo_screenwidth()
        sh = self._parent.winfo_screenheight()
        x  = sw - self._tw - 8
        y  = sh - self._th - 45   # above taskbar

        win = _make_overlay(self._parent, self._tw, self._th, x, y)
        self._win    = win
        self._canvas = tk.Canvas(win, width=self._tw, height=self._th,
                                  bg=_CHROMA, highlightthickness=0)
        self._canvas.pack()

        if self._pil:
            self._tk_img = ImageTk.PhotoImage(self._pil)
            self._canvas.create_image(0, 0, anchor='nw', image=self._tk_img)

        _apply_chroma(win)
        self._twinkle()

    def remove(self):
        self._active = False
        if self._win and self._win.winfo_exists():
            self._win.destroy()
        self._win = self._canvas = self._glow_id = None

    def _twinkle(self):
        if not self._active or not self._canvas or not self._win.winfo_exists():
            return
        if self._glow_id:
            self._canvas.delete(self._glow_id)
        # draw an animated glowing aura around the star
        r   = random.randint(10, 18)
        col = random.choice(['#ffe066', '#fff4a0', '#ffd700', '#fffbe0'])
        self._glow_id = self._canvas.create_oval(
            self._STAR_CX - r, self._STAR_CY - r,
            self._STAR_CX + r, self._STAR_CY + r,
            outline=col, width=2, fill='')
        self._canvas.tag_raise(self._glow_id)
        self._win.after(random.randint(300, 900), self._twinkle)


# ─────────────────────────── GIFT DROP ──────────────────────

class GiftDrop:
    """Spawns a gift window at Santa's position that fades out."""
    GIFTS  = ['🎁', '🎀', '⭐', '🍬', '🔔']
    FADE_STEPS = 20
    FADE_MS    = 60

    def __init__(self, parent):
        self._parent = parent

    def drop(self, sx, sy):
        cx = int(sx) - 18
        cy = int(sy) - 18
        win = _make_overlay(self._parent, 36, 36, cx, cy)
        tk.Label(win, text=random.choice(self.GIFTS),
                 font=('Segoe UI Emoji', 22), bg=_CHROMA).pack()
        _apply_chroma(win)
        self._float_up(win, cy, self.FADE_STEPS)

    def _float_up(self, win, y, steps):
        if steps <= 0 or not win.winfo_exists():
            if win.winfo_exists():
                win.destroy()
            return
        alpha = steps / self.FADE_STEPS
        try:
            win.attributes('-alpha', alpha)
            geo = win.geometry()
            size_pos = geo.split('+')
            x = int(size_pos[1])
            win.geometry(f"{size_pos[0]}+{x}+{int(y) - 1}")
        except Exception:
            pass
        win.after(self.FADE_MS, lambda: self._float_up(win, y - 1, steps - 1))


# ─────────────────────────── SNOW OVERLAY ───────────────────

class SnowOverlay:
    """Fullscreen 3D snow overlay with PIL-rendered crystal sprites."""
    MAX_FLAKES = 120
    TICK_MS    = 30
    N_SIZES    = 8    # discrete depth buckets
    N_ROTS     = 6    # rotation variants (0°–50°, hex-symmetry means 60° repeats)

    def __init__(self, parent):
        self._parent  = parent
        self._win     = None
        self._canvas  = None
        self._flakes  = []
        self._active  = False
        self._sw = self._sh = 0
        self._sprites = {}   # (size_idx, rot_idx) -> ImageTk.PhotoImage

    @property
    def active(self):
        return self._active

    def toggle(self):
        self.stop() if self._active else self.start()

    # ── sprite generation ────────────────────────────────────
    def _build_sprites(self):
        """Pre-render crystalline snowflake sprites at all sizes × rotations."""
        from PIL import Image as PILImage, ImageDraw as PILDraw, ImageFilter as PILFilter
        sprites = {}
        for si in range(self.N_SIZES):
            z      = si / max(self.N_SIZES - 1, 1)   # 0=far 1=near
            radius = 2.5 + z * 13.5                   # 2.5 → 16 px
            # colour: cool ice-blue for far, bright white for near
            cr = int(160 + z * 95)
            cg = int(185 + z * 70)
            cb = 255
            alpha = int(70 + z * 185)

            for ri in range(self.N_ROTS):
                base_ang = math.pi / self.N_ROTS * ri
                pad  = max(6, int(radius * 0.4))
                size = int(radius * 2) * 2 + pad * 2 + 4
                img  = PILImage.new('RGBA', (size, size), (0, 0, 0, 0))
                draw = PILDraw.Draw(img)
                cx = cy = size // 2
                col  = (cr, cg, cb, alpha)
                lw   = max(1, int(radius * 0.14))

                for arm in range(6):
                    ang = base_ang + math.pi / 3 * arm
                    ex  = cx + radius * math.cos(ang)
                    ey  = cy + radius * math.sin(ang)
                    draw.line([(cx, cy), (ex, ey)], fill=col, width=lw)
                    # two pairs of side branches per arm
                    if radius >= 5:
                        for frac, blen in [(0.38, 0.30), (0.68, 0.22)]:
                            bx = cx + radius * frac * math.cos(ang)
                            by = cy + radius * frac * math.sin(ang)
                            bl = radius * blen
                            for side in (-1, 1):
                                ba = ang + side * math.pi / 3
                                draw.line(
                                    [(int(bx), int(by)),
                                     (int(bx + bl * math.cos(ba)),
                                      int(by + bl * math.sin(ba)))],
                                    fill=col, width=max(1, lw - 1)
                                )
                        # tiny tip cap
                        tip_col = (255, 255, 255, min(255, alpha + 40))
                        draw.ellipse([ex-2, ey-2, ex+2, ey+2], fill=tip_col)

                # centre hex dot
                cc = max(2, int(radius * 0.18))
                draw.ellipse([cx-cc, cy-cc, cx+cc, cy+cc],
                             fill=(255, 255, 255, min(255, alpha + 60)))

                # soft glow halo on closer flakes
                if z > 0.5:
                    glow_alpha = int(alpha * 0.45)
                    glow_img   = PILImage.new('RGBA', (size, size), (0, 0, 0, 0))
                    gdraw      = PILDraw.Draw(glow_img)
                    gcol       = (cr, cg, cb, glow_alpha)
                    for arm in range(6):
                        ang = base_ang + math.pi / 3 * arm
                        gx  = cx + radius * 1.05 * math.cos(ang)
                        gy  = cy + radius * 1.05 * math.sin(ang)
                        gdraw.line([(cx, cy), (int(gx), int(gy))],
                                   fill=gcol, width=lw + 3)
                    glow_blur  = glow_img.filter(PILFilter.GaussianBlur(radius=3))
                    composed   = PILImage.alpha_composite(glow_blur, img)
                    img        = composed

                sprites[(si, ri)] = ImageTk.PhotoImage(img)
        return sprites

    # ── lifecycle ─────────────────────────────────────────────
    def start(self):
        if self._active:
            return
        self._active = True
        self._sw = self._parent.winfo_screenwidth()
        self._sh = self._parent.winfo_screenheight()

        # Build sprites first (this may take ~0.3 s; do it before showing window)
        self._sprites = self._build_sprites()

        # Create window OFF-SCREEN so transparency is applied invisibly (no black flash)
        self._win = _make_overlay(self._parent, self._sw, self._sh,
                                   -self._sw - 10, 0)
        self._win.protocol('WM_DELETE_WINDOW', lambda: None)
        self._canvas = tk.Canvas(self._win, width=self._sw, height=self._sh,
                                  bg=_CHROMA, highlightthickness=0)
        self._canvas.pack()
        _apply_chroma(self._win)                          # transparency while off-screen
        self._win.geometry(f"{self._sw}x{self._sh}+0+0") # slide on-screen — already transparent
        self._win.update()

        self._flakes = sorted(
            [self._new_flake(anywhere=True) for _ in range(self.MAX_FLAKES)],
            key=lambda f: f['z']
        )
        self._tick()

    def stop(self):
        self._active = False
        if self._win and self._win.winfo_exists():
            self._win.destroy()
        self._win = self._canvas = None
        self._flakes = []
        self._sprites = {}

    # ── helpers ───────────────────────────────────────────────
    def _new_flake(self, anywhere=False):
        z = random.random()
        return {
            'x':       random.uniform(0, self._sw),
            'y':       random.uniform(0, self._sh) if anywhere
                       else random.uniform(-80, -4),
            'z':       z,
            'speed':   0.4 + z * 2.8,
            'drift':   random.uniform(-0.5, 0.5) * (0.4 + z),
            'wobble':  random.uniform(0, math.tau),
            'wspeed':  random.uniform(0.015, 0.05),
            'si':      min(int(z * self.N_SIZES), self.N_SIZES - 1),
            'ri':      random.randrange(self.N_ROTS),
            'rspeed':  random.choice([-1, 1]) * random.uniform(0.003, 0.012),
        }

    def _tick(self):
        if not self._active or not self._canvas:
            return
        cv = self._canvas
        cv.delete('snow')

        for f in self._flakes:
            f['wobble'] += f['wspeed']
            f['y']      += f['speed']
            f['x']      += f['drift'] + math.sin(f['wobble']) * 0.6 * (0.3 + f['z'])
            # slowly rotate through sprite variants for gentle spin feel
            f['_rot_acc'] = f.get('_rot_acc', 0.0) + f['rspeed']
            if abs(f['_rot_acc']) >= 1.0:
                f['ri'] = (f['ri'] + int(f['_rot_acc'])) % self.N_ROTS
                f['_rot_acc'] = 0.0

            if f['y'] > self._sh + 20:
                f.update(self._new_flake())
            if   f['x'] < -20:          f['x'] = self._sw + 10
            elif f['x'] > self._sw + 20: f['x'] = -10

            photo = self._sprites.get((f['si'], f['ri']))
            if photo:
                cv.create_image(int(f['x']), int(f['y']), image=photo, tags='snow')

        self._win.after(self.TICK_MS, self._tick)


# ─────────────────────────── WIN11 STYLE HELPERS & PALETTE ──

def _apply_win11(win, style='mica'):
    """Apply Windows 11 Mica/Acrylic effect + dark title bar."""
    if _HAS_PYWINSTYLES:
        try:
            pywinstyles.apply_style(win, style)
        except Exception:
            pass

def _styled_btn(parent, text, command, danger=False, accent=False, **kw):
    """Win11-style flat button."""
    if accent:
        bg, fg, hbg = ACC, '#ffffff', '#1a8ee8'
    elif danger:
        bg, fg, hbg = RED_C, '#ffffff', '#e03030'
    else:
        bg, fg, hbg = BG2, FG, '#484848'
    btn = tk.Button(parent, text=text, command=command,
                    bg=bg, fg=fg, font=('Segoe UI Variable', 10),
                    relief='flat', activebackground=hbg, activeforeground=fg,
                    cursor='hand2', padx=16, pady=6, **kw)
    return btn


# Christmas Night palette
BG0   = '#111820'   # midnight background
BG1   = '#1a2535'   # card / panel
BG2   = '#243048'   # hover
BOR   = '#2d3d58'   # border
FG    = '#f0f4ff'   # near-white
SUB   = '#7a90b0'   # subtitle blue-grey
ACC   = '#c0392b'   # Christmas red
GRN   = '#27ae60'   # Christmas green
RED_C = '#e74c3c'   # danger red
YEL   = '#f0a030'   # Christmas gold
_GOLD = '#f0c040'   # star gold


class FloatMenu:
    """Christmas-themed floating menu."""

    _SEC_LABELS = ['REMINDERS & TOOLS', 'CHRISTMAS MAGIC', 'CONTROLS', '']

    def __init__(self, parent):
        self._parent = parent
        self._win    = None

    def show(self, mx, my, sections):
        if self._win and self._win.winfo_exists():
            self._win.destroy()

        win = tk.Toplevel(self._parent)
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        win.configure(bg=BOR)
        self._win = win
        _apply_win11(win, 'acrylic')

        # outer border frame
        outer = tk.Frame(win, bg=BOR, padx=1, pady=1)
        outer.pack(expand=True, fill='both')

        # ── Christmas header ──────────────────────────────────
        hdr = tk.Frame(outer, bg='#8b1a1a', pady=10)
        hdr.pack(fill='x')
        tk.Label(hdr, text='🎅  SANTA PET',
                 font=('Segoe UI Variable', 12, 'bold'),
                 bg='#8b1a1a', fg='#ffffff').pack()
        tk.Label(hdr, text='Christmas Desktop Buddy',
                 font=('Segoe UI Variable', 8),
                 bg='#8b1a1a', fg='#ffaaaa').pack(pady=(1, 0))

        # thin gold separator under header
        tk.Frame(outer, height=2, bg=_GOLD).pack(fill='x')

        body = tk.Frame(outer, bg=BG1, pady=2)
        body.pack(expand=True, fill='both')

        for si, section in enumerate(sections):
            lbl_text = self._SEC_LABELS[si] if si < len(self._SEC_LABELS) else ''
            if lbl_text:
                lf = tk.Frame(body, bg=BG1)
                lf.pack(fill='x', padx=8, pady=(6, 0))
                tk.Label(lf, text=lbl_text,
                         font=('Segoe UI Variable', 7, 'bold'),
                         bg=BG1, fg=SUB).pack(side='left')
                tk.Frame(lf, height=1, bg=BOR).pack(side='left', fill='x',
                                                     expand=True, padx=(6, 0))
            for item in section:
                self._row(body, item, win)
            if si < len(sections) - 1:
                tk.Frame(body, height=1, bg=BOR).pack(fill='x', padx=4, pady=2)

        # position — keep inside screen
        win.update_idletasks()
        mw = win.winfo_reqwidth()
        mh = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = min(mx, sw - mw - 6)
        y = min(my, sh - mh - 6)
        win.geometry(f"+{x}+{y}")

        win.bind('<FocusOut>', lambda e: self._safe_destroy())
        win.bind('<Escape>',   lambda e: self._safe_destroy())
        win.focus_set()

    def _safe_destroy(self):
        if self._win and self._win.winfo_exists():
            self._win.destroy()

    def _row(self, parent, item, win):
        icon, title, sub, cmd, *rest = tuple(item) + (None,) * (5 - len(item))
        danger = bool(rest[0]) if rest else False
        fg_col = '#ff6b6b' if danger else FG
        hov_bg = '#2a1515' if danger else BG2

        row = tk.Frame(parent, bg=BG1, cursor='hand2' if cmd else 'arrow')
        row.pack(fill='x', padx=2)

        ic = tk.Label(row, text=icon, font=('Segoe UI Emoji', 13),
                      bg=BG1, fg=fg_col, width=3, anchor='center')
        ic.pack(side='left', padx=(8, 2), pady=(5 if sub else 7, 5 if sub else 7))

        tf = tk.Frame(row, bg=BG1)
        tf.pack(side='left', fill='x', expand=True, padx=(0, 16))

        tl = tk.Label(tf, text=title, font=('Segoe UI Variable', 10),
                      bg=BG1, fg=fg_col, anchor='w')
        tl.pack(fill='x', pady=(5 if sub else 0, 0))

        sl = None
        if sub:
            sl = tk.Label(tf, text=sub, font=('Segoe UI Variable', 8),
                          bg=BG1, fg=SUB, anchor='w')
            sl.pack(fill='x', pady=(1, 4))

        all_w = [row, ic, tf, tl] + ([sl] if sl else [])

        def _enter(e, ws=all_w, hb=hov_bg):
            for w in ws:
                try: w.configure(bg=hb)
                except: pass
        def _leave(e, ws=all_w):
            for w in ws:
                try: w.configure(bg=BG1)
                except: pass

        for w in all_w:
            w.bind('<Enter>', _enter)
            w.bind('<Leave>', _leave)

        if cmd:
            def _click(e, c=cmd):
                self._safe_destroy()
                c()
            for w in all_w:
                w.bind('<Button-1>', _click)


# ─────────────────────────── MAIN APP ────────────────────────

class SantaPetApp:
    ANIM_DELAY = 120    # ms per frame

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Santa Pet")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'black')
        self.root.configure(bg='black')

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()

        # position
        self.sx = float(random.randint(200, self.sw - 240))
        self.sy = float(self.sh - H // 2 - 55)
        self.dir = random.choice(['l', 'r'])
        self.speed = 2

        # animation state machine
        self.anim      = 'walk_r'   # current animation key
        self.frame_idx = 0
        self.dance_loops      = 0
        self.dance_loops_goal = 0
        self.paused = False

        # reminders
        self._last_water = datetime.now()
        self._water_mins = 30

        # render sprite frames
        self._tk_frames = {}
        self._pre_render()

        # canvas — speech bubble strip is 28px above the sprite
        self.canvas = tk.Canvas(self.root, width=W, height=H+28,
                                bg='black', highlightthickness=0)
        self.canvas.pack()
        self._img_id = self.canvas.create_image(W//2, H//2 + 14,
                                                image=self._get_tk_frame())
        self._bub_bg  = None
        self._bub_txt = None

        # bindings — press starts drag tracking, release decides click vs drag
        self.canvas.bind('<Button-3>',        self._menu)
        self.canvas.bind('<ButtonPress-1>',   self._on_press)
        self.canvas.bind('<B1-Motion>',       self._drag_move)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)
        self._dragged = False
        self._dx = self._dy = 0

        # helpers
        self._water       = WaterPopup()
        self._health      = PCHealth()
        self._cleaner     = CacheCleaner()
        self._todo        = TodoWindow(self.root, on_remind_cb=self._task_remind)
        self._float_menu  = FloatMenu(self.root)
        self._snow        = SnowOverlay(self.root)
        self._gift        = GiftDrop(self.root)
        self._gift_ticks  = 0
        self._gift_every  = random.randint(180, 360)  # frames between drops
        self._sleigh      = SleighFlyby(self.root)
        self._reindeer    = ReindeerDash(self.root)
        self._tree        = ChristmasTree(self.root)

        self._place()
        self._tick()
        self._tick_remind()
        self._schedule_quip()

    # ── pre-render all frames ─────────────────────────────────
    def _pre_render(self):
        for key, frames in ANIM.items():
            self._tk_frames[key] = [ImageTk.PhotoImage(f) for f in frames]

    def _get_tk_frame(self):
        return self._tk_frames[self.anim][self.frame_idx % len(self._tk_frames[self.anim])]

    # ── window placement ─────────────────────────────────────
    def _place(self):
        self.root.geometry(f"+{int(self.sx - W//2)}+{int(self.sy - H//2)}")

    # ── main tick ────────────────────────────────────────────
    def _tick(self):
        frames = self._tk_frames[self.anim]
        self.frame_idx = (self.frame_idx + 1) % len(frames)

        if not self.paused:
            # advance dance loop counter
            if self.anim in DANCE_NAMES:
                if self.frame_idx == 0:
                    self.dance_loops += 1
                    if self.dance_loops >= self.dance_loops_goal:
                        self._set_anim('walk_r' if self.dir == 'r' else 'walk_l')

            # walk movement
            elif self.anim in ('walk_r', 'walk_l'):
                if self.dir == 'r':
                    self.sx += self.speed
                    if self.sx > self.sw - 120: self.dir = 'l'; self._set_anim('walk_l')
                else:
                    self.sx -= self.speed
                    if self.sx < 120: self.dir = 'r'; self._set_anim('walk_r')
                self._place()
                # random gift drop while walking
                self._gift_ticks += 1
                if self._gift_ticks >= self._gift_every:
                    self._gift_ticks = 0
                    self._gift_every = random.randint(180, 360)
                    self._gift.drop(self.sx, self.sy)

        self.canvas.itemconfig(self._img_id, image=self._get_tk_frame())
        self.root.after(self.ANIM_DELAY, self._tick)

    def _set_anim(self, name):
        self.anim      = name
        self.frame_idx = 0

    # ── press / drag / release ───────────────────────────────
    def _on_press(self, e):
        self._dragged = False
        self._dx = e.x_root - int(self.sx)
        self._dy = e.y_root - int(self.sy)

    def _on_release(self, e):
        if not self._dragged:
            self._trigger_dance()
        self._dragged = False

    def _trigger_dance(self):
        if self.anim in DANCE_NAMES:
            return
        if self.paused:
            return
        dance = random.choice(DANCE_NAMES)
        self._say(random.choice(DANCE_QUIPS[dance]), 4000)
        self._set_anim(dance)
        self.dance_loops      = 0
        self.dance_loops_goal = random.randint(2, 3)

    # ── reminders ────────────────────────────────────────────
    def _tick_remind(self):
        mins = (datetime.now() - self._last_water).total_seconds() / 60
        if mins >= self._water_mins:
            self._last_water = datetime.now()
            self._say("💧 Drink water!", 6000)
            self.root.after(800, lambda: self._water.show(self.root))
        self.root.after(60_000, self._tick_remind)

    def _schedule_quip(self):
        quips = ["Ho Ho Ho! 🎅", "Right-click me! 🖱",
                 "Feeling jolly! 🎄", "Click to dance! 💃",
                 "Stay healthy! 💪", "Jingle bells! 🔔"]
        if random.random() < 0.4:
            self._say(random.choice(quips), 3000)
        self.root.after(random.randint(90_000, 200_000), self._schedule_quip)

    # ── speech bubble ────────────────────────────────────────
    def _say(self, text, ms=3000):
        self._clear_bubble()
        fw = self.canvas.winfo_width() or W
        self._bub_bg  = self.canvas.create_rectangle(
            4, 2, fw-4, 26,
            fill='#1a2535', outline=_GOLD, width=1)
        self._bub_txt = self.canvas.create_text(
            fw//2, 14, text=text,
            font=('Segoe UI Variable', 8, 'bold'), fill='#ffe0a0')
        self.root.after(ms, self._clear_bubble)

    def _clear_bubble(self):
        for attr in ('_bub_bg', '_bub_txt'):
            _id = getattr(self, attr, None)
            if _id: self.canvas.delete(_id)
            setattr(self, attr, None)

    # ── drag ─────────────────────────────────────────────────
    def _drag_move(self, e):
        self._dragged = True
        self.sx = max(120, min(self.sw-120, float(e.x_root - self._dx)))
        self.sy = max(80,  min(self.sh-80,  float(e.y_root - self._dy)))
        self._place()

    # ── context menu ─────────────────────────────────────────
    def _menu(self, e):
        # live stats for subtitles
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory().percent
            health_sub = f"CPU {cpu:.0f}%  ·  RAM {ram:.0f}%"
        except Exception:
            health_sub = "Live health report"

        # task count — prefer live Google Tasks cache, fall back to local
        try:
            tasks = self._todo._tasks if self._todo._tasks else self._todo._cache.load()
            active = sum(1 for t in tasks if not t['done'])
            task_sub = f"{active} active task{'s' if active != 1 else ''}"
        except Exception:
            task_sub = "Manage your tasks"

        # Google Tasks status
        gt = self._todo.google
        if gt.is_connected():
            gt_sub, gt_cmd = "● Connected — tap to disconnect", self._gtasks_disconnect
        elif gt.is_configured():
            gt_sub, gt_cmd = "○ Tap to connect", self._gtasks_connect
        else:
            gt_sub, gt_cmd = "○ Setup credentials to enable", self._gtasks_setup

        pause_icon  = "▶" if self.paused else "⏸"
        pause_title = "Resume Walking" if self.paused else "Pause Walking"
        snow_icon  = "🌤" if self._snow.active else "❄️"
        snow_title = "Stop Snow" if self._snow.active else "Let it Snow!"
        tree_icon  = "🗑" if self._tree.active else "🎄"
        tree_title = "Remove Tree" if self._tree.active else "Place Christmas Tree"

        sections = [
            [
                ("💧", "Water Reminder",  f"Remind every {self._water_mins} min",
                 lambda: self._water.show(self.root)),
                ("🏥", "PC Health Check", health_sub,
                 lambda: self._health.show(self.root)),
                ("🧹", "Clean Cache",     "Scan & remove junk files",
                 lambda: self._cleaner.show(self.root)),
                ("📋", "To-Do List",      task_sub,
                 self._todo.show),
                ("🔗", "Google Tasks",    gt_sub,
                 gt_cmd),
            ],
            [
                (snow_icon,  snow_title,       "Falling snowflakes overlay",  self._snow.toggle),
                (tree_icon,  tree_title,        "Stationary tree in corner",   self._tree.toggle),
                ("🛷",       "Sleigh Fly-by",  "Santa's sleigh crosses screen", self._sleigh.fly),
                ("🦌",       "Reindeer Dash",  "Reindeer runs across screen",   self._reindeer.dash),
            ],
            [
                (pause_icon, pause_title, None, self._toggle_pause),
                ("⚙️",       "Settings",  "Speed & reminder interval", self._settings),
            ],
            [
                ("❌", "Exit", None, self._quit, True),
            ],
        ]
        self._float_menu.show(e.x_root, e.y_root, sections)

    # ── Google Tasks quick-connect ────────────────────────────
    def _gtasks_connect(self):
        self._say("Connecting Google Tasks… 🔗", 4000)
        def _work():
            ok, msg = self._todo.google.connect()
            self.root.after(0, lambda: self._say(
                "Google Tasks connected! ✅" if ok else f"❌ {msg[:35]}", 5000))
        threading.Thread(target=_work, daemon=True).start()

    def _gtasks_disconnect(self):
        self._todo.google.disconnect()
        self._say("Disconnected from Google Tasks", 3000)

    def _gtasks_setup(self):
        # Open the todo window which has the full setup flow
        self._todo.show()
        self.root.after(300, lambda: self._todo._show_google_setup()
                        if hasattr(self._todo, '_show_google_setup') else None)

    def _toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self._set_anim('idle')
            self._say("Paused ⏸", 2000)
        else:
            self._set_anim('walk_r' if self.dir == 'r' else 'walk_l')
            self._say("Let's go! 🎅", 2000)

    def _settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("340x300+{}+{}".format(
            self.sw//2-170, self.sh//2-150))
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.configure(bg=BG0)
        _apply_win11(win)

        hdr = tk.Frame(win, bg=BG1, pady=12)
        hdr.pack(fill='x')
        tk.Label(hdr, text="⚙️  Settings",
                 font=('Segoe UI Variable', 14, 'bold'), bg=BG1, fg=ACC).pack()
        tk.Label(hdr, text="Speed & reminder preferences",
                 font=('Segoe UI Variable', 9), bg=BG1, fg=SUB).pack(pady=(2, 0))
        tk.Frame(win, height=1, bg=BOR).pack(fill='x')

        body = tk.Frame(win, bg=BG0, padx=22)
        body.pack(fill='both', expand=True)

        def lbl(t):
            tk.Label(body, text=t, bg=BG0, fg=FG,
                     font=('Segoe UI Variable', 10)).pack(anchor='w', pady=(14, 0))

        lbl("🚶 Walking Speed  (1 = slow · 8 = fast)")
        spd = tk.IntVar(value=self.speed)
        tk.Scale(body, from_=1, to=8, orient='horizontal', variable=spd,
                 bg=BG0, fg=FG, troughcolor=BOR, activebackground=ACC,
                 highlightthickness=0, length=280, sliderlength=18).pack(fill='x')

        lbl("💧 Water Reminder (minutes)")
        wtr = tk.IntVar(value=self._water_mins)
        tk.Scale(body, from_=5, to=120, orient='horizontal', variable=wtr,
                 bg=BG0, fg=FG, troughcolor=BOR, activebackground=ACC,
                 highlightthickness=0, length=280, sliderlength=18).pack(fill='x')

        def apply():
            self.speed       = spd.get()
            self._water_mins = wtr.get()
            win.destroy()
            self._say("Settings saved ✅", 2000)

        tk.Frame(win, height=1, bg=BOR).pack(fill='x')
        _styled_btn(win, "Save Settings", apply, accent=True).pack(pady=14)

    # ── task reminder callback ────────────────────────────────
    def _task_remind(self, task):
        self._say(f"⏰ {task['title'][:22]}", 8000)
        self.root.after(500, lambda: self._show_task_popup(task))

    def _show_task_popup(self, task):
        w = tk.Toplevel(self.root)
        w.title("Task Reminder")
        w.geometry("360x230+{}+{}".format(self.sw//2-180, self.sh//2-115))
        w.resizable(False, False)
        w.attributes('-topmost', True)
        w.configure(bg=BG0)
        _apply_win11(w)

        hdr = tk.Frame(w, bg=BG1, pady=12)
        hdr.pack(fill='x')
        tk.Label(hdr, text="⏰", font=('Segoe UI Emoji', 32), bg=BG1).pack()
        tk.Label(hdr, text="Task Reminder",
                 font=('Segoe UI Variable', 12, 'bold'), bg=BG1, fg=ACC).pack(pady=(2, 0))

        tk.Frame(w, height=1, bg=BOR).pack(fill='x')
        tk.Label(w, text=task['title'],
                 font=('Segoe UI Variable', 13, 'bold'),
                 bg=BG0, fg=FG, wraplength=320).pack(pady=(12, 2))
        if task.get('note'):
            tk.Label(w, text=task['note'],
                     font=('Segoe UI Variable', 9), bg=BG0, fg=SUB).pack(pady=2)

        _styled_btn(w, "Got it! ✅", w.destroy, accent=True).pack(pady=14)
        w.after(60000, lambda: w.destroy() if w.winfo_exists() else None)

    def _quit(self):
        if messagebox.askyesno("Exit", "Close Santa Pet?", parent=self.root):
            self.root.destroy()

    def run(self):
        if _HAS_SVTTK:
            sv_ttk.set_theme('dark')
        self.root.mainloop()


if __name__ == '__main__':
    SantaPetApp().run()
