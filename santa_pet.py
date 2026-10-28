"""Santa Pet - Desktop Companion with PC Health Tools"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageTk
import threading
import time
import random
import os
import sys
import psutil
import shutil
import tempfile
from datetime import datetime
import math


# ─────────────────────────── SPRITE ───────────────────────────

class SantaSprite:
    W, H = 24, 42   # pixel-art grid
    SCALE = 3

    C = {
        'red':    (204,  0,  0, 255),
        'dred':   (150,  0,  0, 255),
        'white':  (255,255,255, 255),
        'skin':   (255,200,160, 255),
        'dskin':  (230,170,130, 255),
        'black':  ( 20, 20, 20, 255),
        'gold':   (255,215,  0, 255),
        'pink':   (255,150,150, 255),
        'tr':     (  0,  0,  0,   0),
    }

    def _px(self, draw, x, y, color):
        s = self.SCALE
        draw.rectangle([x*s, y*s, x*s+s-1, y*s+s-1], fill=color)

    def _draw_frame(self, frame: int, direction: str = 'right') -> Image.Image:
        w = self.W * self.SCALE
        h = self.H * self.SCALE
        img = Image.new('RGBA', (w, h), self.C['tr'])
        d = ImageDraw.Draw(img)
        p = lambda x, y, c: self._px(d, x, y, self.C[c])

        # walking cycle offsets
        cycle = frame % 4
        lleg = [0, 2, 0, -2][cycle]   # left leg x-shift
        rleg = [0, -2, 0, 2][cycle]   # right leg x-shift
        larm = [1, 0, -1, 0][cycle]   # left arm y-shift
        rarm = [-1, 0, 1, 0][cycle]

        # ── BOOTS ──────────────────────────────────────────────
        for x in range(5 + lleg, 10 + lleg):
            for y in range(38, 42): p(x, y, 'black')
        for x in range(14 + rleg, 19 + rleg):
            for y in range(38, 42): p(x, y, 'black')
        # boot highlight
        for x in [6+lleg, 15+rleg]:
            p(x, 38, 'white') if 0 <= x < self.W else None

        # ── LEGS ───────────────────────────────────────────────
        for y in range(28, 39):
            for x in range(6 + lleg, 10 + lleg):
                if 0 <= x < self.W: p(x, y, 'red')
            for x in range(14 + rleg, 18 + rleg):
                if 0 <= x < self.W: p(x, y, 'red')

        # ── COAT BODY ──────────────────────────────────────────
        for y in range(16, 29):
            for x in range(4, 20): p(x, y, 'red')
        # coat bottom white trim
        for x in range(4, 20):
            p(x, 27, 'white'); p(x, 28, 'white')
        # coat shadow
        for x in range(4, 20):
            p(x, 16, 'dred')

        # ── BELT ───────────────────────────────────────────────
        for x in range(4, 20):
            p(x, 22, 'black'); p(x, 23, 'black')
        for x in range(10, 14):
            p(x, 22, 'gold'); p(x, 23, 'gold')

        # ── BUTTONS ────────────────────────────────────────────
        p(11, 18, 'white'); p(11, 20, 'white')

        # ── ARMS ───────────────────────────────────────────────
        # left arm
        for y in range(17 + larm, 23 + larm):
            for x in range(1, 5): p(x, y, 'red')
        # left cuff
        for x in range(1, 5):
            p(x, 22 + larm, 'white'); p(x, 23 + larm, 'white')

        # right arm
        for y in range(17 + rarm, 23 + rarm):
            for x in range(19, 23): p(x, y, 'red')
        # right cuff
        for x in range(19, 23):
            p(x, 22 + rarm, 'white'); p(x, 23 + rarm, 'white')

        # ── HEAD ───────────────────────────────────────────────
        for y in range(9, 17):
            xl = 6 if y in (9, 16) else 5
            xr = 17 if y in (9, 16) else 18
            for x in range(xl, xr): p(x, y, 'skin')
        # ear tones
        p(5, 12, 'dskin'); p(5, 13, 'dskin')
        p(18, 12, 'dskin'); p(18, 13, 'dskin')

        # ── BEARD ──────────────────────────────────────────────
        for x in range(5, 19):
            p(x, 14, 'white'); p(x, 15, 'white'); p(x, 16, 'white')
        for x in range(6, 18):
            p(x, 13, 'white')
        # mustache
        for x in range(8, 16): p(x, 12, 'white')
        p(8, 12, 'skin'); p(15, 12, 'skin')

        # ── EYES ───────────────────────────────────────────────
        p(8,  10, 'black'); p(15, 10, 'black')
        p(9,  10, 'white')                        # shine

        # ── NOSE ───────────────────────────────────────────────
        p(11, 11, 'pink'); p(12, 11, 'pink')

        # ── CHEEKS ─────────────────────────────────────────────
        p(7, 12, 'pink'); p(16, 12, 'pink')

        # ── HAT BRIM ───────────────────────────────────────────
        for x in range(4, 20):
            p(x, 8, 'white'); p(x, 9, 'white')

        # ── HAT BODY ───────────────────────────────────────────
        rows = [(5,18),(6,17),(7,16),(8,15),(9,14),(10,13)]
        for i, (xl, xr) in enumerate(rows):
            for x in range(xl, xr): p(x, i+2, 'red')

        # ── POM-POM ────────────────────────────────────────────
        p(10, 0, 'white'); p(11, 0, 'white'); p(12, 0, 'white')
        p(10, 1, 'white'); p(11, 1, 'white'); p(12, 1, 'white')

        if direction == 'left':
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        return img

    def get_frames(self):
        frames = {'right': [], 'left': []}
        for i in range(4):
            frames['right'].append(self._draw_frame(i, 'right'))
            frames['left'].append(self._draw_frame(i, 'left'))
        return frames


# ─────────────────────────── WATER POPUP ─────────────────────

class WaterPopup:
    def show(self, parent):
        w = tk.Toplevel(parent)
        w.title("Stay Hydrated!")
        w.geometry("320x200+{}+{}".format(
            w.winfo_screenwidth()//2 - 160,
            w.winfo_screenheight()//2 - 100))
        w.resizable(False, False)
        w.attributes('-topmost', True)
        w.configure(bg='#0a3d62')

        tk.Label(w, text="💧", font=('Segoe UI Emoji', 44),
                 bg='#0a3d62').pack(pady=(15, 2))
        tk.Label(w, text="Time to drink water!", font=('Arial', 14, 'bold'),
                 bg='#0a3d62', fg='#ffffff').pack()
        tk.Label(w, text="Your body needs it — have a glass now 🥤",
                 font=('Arial', 10), bg='#0a3d62', fg='#74b9ff').pack(pady=4)
        tk.Button(w, text="Thanks Santa! 🎅", command=w.destroy,
                  bg='#ffffff', fg='#0a3d62', font=('Arial', 11, 'bold'),
                  relief='flat', padx=20, pady=6, cursor='hand2').pack(pady=12)
        w.after(30000, lambda: w.destroy() if w.winfo_exists() else None)


# ─────────────────────────── PC HEALTH ───────────────────────

class PCHealth:
    def show(self, parent):
        win = tk.Toplevel(parent)
        win.title("PC Doctor — Health Report")
        win.geometry("460x560")
        win.resizable(True, True)
        win.attributes('-topmost', True)
        win.configure(bg='#0d1117')

        # header
        hdr = tk.Frame(win, bg='#161b22', pady=10)
        hdr.pack(fill='x')
        tk.Label(hdr, text="🏥  PC Doctor", font=('Arial', 15, 'bold'),
                 bg='#161b22', fg='#58a6ff').pack()
        tk.Label(hdr, text=datetime.now().strftime('%Y-%m-%d  %H:%M:%S'),
                 font=('Arial', 9), bg='#161b22', fg='#8b949e').pack()

        # scrollable body
        container = tk.Frame(win, bg='#0d1117')
        container.pack(fill='both', expand=True)
        cv = tk.Canvas(container, bg='#0d1117', highlightthickness=0)
        sb = ttk.Scrollbar(container, orient='vertical', command=cv.yview)
        frame = tk.Frame(cv, bg='#0d1117')
        frame.bind('<Configure>', lambda e: cv.configure(scrollregion=cv.bbox('all')))
        cv.create_window((0, 0), window=frame, anchor='nw')
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        def section(title):
            f = tk.Frame(frame, bg='#21262d', pady=5, padx=8)
            f.pack(fill='x', padx=8, pady=(8, 2))
            tk.Label(f, text=title, font=('Arial', 10, 'bold'),
                     bg='#21262d', fg='#58a6ff').pack(anchor='w')

        def row(label, val, pct=None):
            f = tk.Frame(frame, bg='#161b22', padx=10, pady=5)
            f.pack(fill='x', padx=8, pady=1)
            tk.Label(f, text=label, font=('Arial', 9),
                     bg='#161b22', fg='#c9d1d9', width=22, anchor='w').grid(row=0, column=0)
            color = '#3fb950' if (pct or 0) < 60 else '#d29922' if (pct or 0) < 85 else '#f85149'
            tk.Label(f, text=val, font=('Arial', 9, 'bold'),
                     bg='#161b22', fg=color).grid(row=0, column=1, padx=10)
            if pct is not None:
                bar = tk.Canvas(f, width=100, height=8, bg='#30363d',
                                highlightthickness=0)
                bar.grid(row=0, column=2, padx=5)
                bar.create_rectangle(0, 0, pct, 8, fill=color, width=0)

        # ── CPU
        section("⚡ Processor")
        cpu_pct = psutil.cpu_percent(interval=0.3)
        cores = psutil.cpu_count(logical=False)
        threads = psutil.cpu_count()
        freq = psutil.cpu_freq()
        row("CPU Usage", f"{cpu_pct:.1f}%", int(cpu_pct))
        row("Cores / Threads", f"{cores} / {threads}")
        if freq:
            row("Frequency", f"{freq.current:.0f} MHz")

        # ── Memory
        section("💾 Memory (RAM)")
        m = psutil.virtual_memory()
        row("Usage", f"{m.percent:.1f}%", int(m.percent))
        row("Used / Total", f"{m.used/2**30:.1f} / {m.total/2**30:.1f} GB")
        row("Available", f"{m.available/2**30:.1f} GB")

        # ── Disk
        section("💿 Storage")
        for part in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(part.mountpoint)
                row(part.device, f"{u.percent:.1f}%  ({u.free/2**30:.1f} GB free)", int(u.percent))
            except Exception:
                pass

        # ── Battery
        section("🔋 Battery")
        try:
            bat = psutil.sensors_battery()
            if bat:
                row("Charge", f"{bat.percent:.0f}%", int(bat.percent))
                row("Power", "Plugged in ⚡" if bat.power_plugged else "On battery 🔋")
            else:
                row("Battery", "No battery / Desktop")
        except Exception:
            row("Battery", "Not available")

        # ── Network
        section("🌐 Network I/O")
        try:
            n = psutil.net_io_counters()
            row("Sent", f"{n.bytes_sent/2**20:.1f} MB")
            row("Received", f"{n.bytes_recv/2**20:.1f} MB")
        except Exception:
            pass

        # ── Uptime
        section("⏱ System")
        try:
            boot = psutil.boot_time()
            up = datetime.now() - datetime.fromtimestamp(boot)
            h, rem = divmod(int(up.total_seconds()), 3600)
            row("Uptime", f"{h}h {rem//60}m")
            row("Processes", str(len(psutil.pids())))
        except Exception:
            pass

        tk.Button(win, text="Close", command=win.destroy,
                  bg='#238636', fg='white', font=('Arial', 11, 'bold'),
                  relief='flat', padx=25, pady=7).pack(pady=10)


# ─────────────────────────── CACHE CLEANER ───────────────────

class CacheCleaner:
    def _locations(self):
        up = os.environ.get('USERPROFILE', os.path.expanduser('~'))
        spots = [
            ('Windows Temp',      os.environ.get('TEMP', tempfile.gettempdir())),
            ('User AppData Temp', os.path.join(up, 'AppData', 'Local', 'Temp')),
            ('System32 Temp',     r'C:\Windows\Temp'),
            ('Chrome Cache',      os.path.join(up, 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache')),
            ('Edge Cache',        os.path.join(up, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache')),
            ('Firefox Cache',     os.path.join(up, 'AppData', 'Local', 'Mozilla', 'Firefox', 'Profiles')),
            ('Thumbnail Cache',   os.path.join(up, 'AppData', 'Local', 'Microsoft', 'Windows', 'Explorer')),
        ]
        return [(n, p) for n, p in spots if os.path.exists(p)]

    @staticmethod
    def _dir_size(path):
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    try: total += os.path.getsize(os.path.join(root, f))
                    except: pass
        except: pass
        return total

    @staticmethod
    def _fmt(b):
        if b < 1024: return f"{b} B"
        if b < 2**20: return f"{b/1024:.1f} KB"
        if b < 2**30: return f"{b/2**20:.1f} MB"
        return f"{b/2**30:.2f} GB"

    @staticmethod
    def _clean_dir(path):
        ok = err = 0
        try:
            for item in os.listdir(path):
                fp = os.path.join(path, item)
                try:
                    if os.path.isfile(fp): os.unlink(fp); ok += 1
                    elif os.path.isdir(fp): shutil.rmtree(fp, ignore_errors=True); ok += 1
                except: err += 1
        except: err += 1
        return ok, err

    def show(self, parent):
        win = tk.Toplevel(parent)
        win.title("🧹 Santa's Cache Cleaner")
        win.geometry("520x560")
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.configure(bg='#0d1117')

        # header
        hdr = tk.Frame(win, bg='#161b22', pady=10)
        hdr.pack(fill='x')
        tk.Label(hdr, text="🧹  Santa's Cache Cleaner", font=('Arial', 14, 'bold'),
                 bg='#161b22', fg='#58a6ff').pack()
        tk.Label(hdr, text="Free up space by removing junk files",
                 font=('Arial', 9), bg='#161b22', fg='#8b949e').pack()

        # list frame
        lf = tk.Frame(win, bg='#0d1117')
        lf.pack(fill='both', expand=True, padx=12, pady=8)

        status_var = tk.StringVar(value="Scanning...")
        total_var  = tk.StringVar(value="Total: —")

        tk.Label(win, textvariable=status_var, font=('Arial', 9),
                 bg='#0d1117', fg='#8b949e').pack()
        tk.Label(win, textvariable=total_var, font=('Arial', 12, 'bold'),
                 bg='#0d1117', fg='#3fb950').pack(pady=3)

        prog = ttk.Progressbar(win, mode='indeterminate')
        prog.pack(fill='x', padx=16, pady=4)
        prog.start()

        check_vars = {}

        btn_frame = tk.Frame(win, bg='#0d1117')
        btn_frame.pack(pady=8)
        clean_btn = tk.Button(btn_frame, text="🧹 Clean Selected",
                              font=('Arial', 11, 'bold'), bg='#da3633', fg='white',
                              relief='flat', padx=15, pady=7, state='disabled',
                              cursor='hand2')
        clean_btn.pack(side='left', padx=6)
        tk.Button(btn_frame, text="Close", command=win.destroy,
                  font=('Arial', 11), bg='#30363d', fg='white',
                  relief='flat', padx=15, pady=7, cursor='hand2').pack(side='left', padx=6)

        def scan():
            locs = self._locations()
            total = 0
            for w2 in lf.winfo_children(): w2.destroy()
            check_vars.clear()
            prog.stop()
            prog.config(mode='determinate', value=0)

            for name, path in locs:
                sz = self._dir_size(path)
                total += sz
                var = tk.BooleanVar(value=True)
                check_vars[path] = var
                row = tk.Frame(lf, bg='#161b22', padx=8, pady=6)
                row.pack(fill='x', pady=2)
                tk.Checkbutton(row, variable=var, bg='#161b22',
                               activebackground='#161b22',
                               selectcolor='#21262d').pack(side='left')
                tk.Label(row, text=name, font=('Arial', 10, 'bold'),
                         bg='#161b22', fg='#e6edf3', width=22, anchor='w').pack(side='left')
                color = '#f85149' if sz > 100*2**20 else '#d29922' if sz > 5*2**20 else '#3fb950'
                tk.Label(row, text=self._fmt(sz), font=('Arial', 10),
                         bg='#161b22', fg=color).pack(side='right', padx=8)

            total_var.set(f"Total junk found: {self._fmt(total)}")
            status_var.set(f"{len(locs)} cache locations found")
            clean_btn.config(state='normal')

        def do_clean():
            if not messagebox.askyesno("Confirm Clean",
                "Delete selected cache files?\nRunning apps may recreate them.", parent=win):
                return
            clean_btn.config(state='disabled')
            prog.config(mode='indeterminate'); prog.start()
            status_var.set("Cleaning…")

            def worker():
                tot_ok = tot_err = 0
                for path, var in check_vars.items():
                    if var.get() and os.path.exists(path):
                        ok, err = self._clean_dir(path)
                        tot_ok += ok; tot_err += err
                win.after(0, lambda: done(tot_ok, tot_err))

            def done(ok, err):
                prog.stop(); prog.config(mode='determinate', value=100)
                status_var.set(f"Done — {ok} items removed  ({err} skipped/in use)")
                total_var.set("Scan again to update sizes")
                messagebox.showinfo("All Clean! 🎉",
                    f"✅ Removed {ok} items\n⚠️ {err} files were in use or locked",
                    parent=win)

            threading.Thread(target=worker, daemon=True).start()

        clean_btn.config(command=do_clean)
        win.after(200, scan)


# ─────────────────────────── SETTINGS ────────────────────────

class Settings:
    def __init__(self):
        self.speed       = 2
        self.water_mins  = 30
        self.scale       = 3


# ─────────────────────────── MAIN APP ────────────────────────

class SantaPetApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Santa Pet")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'black')
        self.root.configure(bg='black')
        self.root.resizable(False, False)

        self.cfg = Settings()
        self.sw  = self.root.winfo_screenwidth()
        self.sh  = self.root.winfo_screenheight()

        # position
        self.x = float(random.randint(100, self.sw - 200))
        self.y = float(self.sh - 160)
        self.dir = random.choice(['left', 'right'])

        # animation state
        self.frame_idx = 0
        self.paused    = False
        self.idle      = False
        self._idle_ticker = 0

        # reminders
        self.last_water = datetime.now()

        # build sprites
        sprite = SantaSprite()
        raw    = sprite.get_frames()
        self.frames = {
            d: [ImageTk.PhotoImage(f) for f in raw[d]]
            for d in ('left', 'right')
        }
        fw = raw['right'][0].width
        fh = raw['right'][0].height

        # canvas (slightly taller for speech bubble row)
        cw, ch = fw, fh + 24
        self.canvas = tk.Canvas(self.root, width=cw, height=ch,
                                bg='black', highlightthickness=0)
        self.canvas.pack()

        self.img_id     = self.canvas.create_image(fw//2, ch//2 + 8,
                                                   image=self.frames['right'][0])
        self.bubble_bg  = None
        self.bubble_txt = None

        # drag
        self._dx = self._dy = 0
        self.canvas.bind('<ButtonPress-1>',   self._drag_start)
        self.canvas.bind('<B1-Motion>',       self._drag_move)
        self.canvas.bind('<ButtonRelease-1>', self._drag_end)
        self.canvas.bind('<Button-3>',        self._menu)
        self._dragging = False

        # helpers
        self._water   = WaterPopup()
        self._health  = PCHealth()
        self._cleaner = CacheCleaner()

        self._place()
        self._tick_anim()
        self._tick_remind()
        self._tick_speech()

    # ── window position ───────────────────────────────────────
    def _place(self):
        fw = self.frames['right'][0].width()
        fh = self.frames['right'][0].height()
        ch = fh + 24
        wx = int(self.x - fw // 2)
        wy = int(self.y - ch // 2)
        self.root.geometry(f"+{wx}+{wy}")

    # ── animation tick ────────────────────────────────────────
    def _tick_anim(self):
        if not self.paused:
            self.frame_idx = (self.frame_idx + 1) % 4
            self.canvas.itemconfig(self.img_id,
                                   image=self.frames[self.dir][self.frame_idx])
            if not self.idle:
                step = self.cfg.speed
                if self.dir == 'right':
                    self.x += step
                    if self.x > self.sw - 80: self.dir = 'left'
                else:
                    self.x -= step
                    if self.x < 80: self.dir = 'right'
                self._place()

            self._idle_ticker += 1
            if self._idle_ticker >= 80:
                self._idle_ticker = 0
                if not self.idle and random.random() < 0.08:
                    self.idle = True
                    delay = random.randint(2000, 6000)
                    self.root.after(delay, self._end_idle)

        self.root.after(130, self._tick_anim)

    def _end_idle(self):
        self.idle = False

    # ── reminders tick ────────────────────────────────────────
    def _tick_remind(self):
        mins = (datetime.now() - self.last_water).total_seconds() / 60
        if mins >= self.cfg.water_mins:
            self.last_water = datetime.now()
            self._say("💧 Drink water!", 6000)
            self.root.after(800, lambda: self._water.show(self.root))
        self.root.after(60_000, self._tick_remind)

    # ── random speech ─────────────────────────────────────────
    def _tick_speech(self):
        quips = [
            "Ho Ho Ho! 🎅", "Stay healthy! 💪", "Drink water! 💧",
            "Right-click me!", "Merry day! 🎄", "You're doing great! ⭐",
            "Need help? Click! 🖱", "Jingle bells! 🔔",
        ]
        if random.random() < 0.35:
            self._say(random.choice(quips), 3000)
        self.root.after(random.randint(90_000, 240_000), self._tick_speech)

    # ── speech bubble ─────────────────────────────────────────
    def _say(self, text, ms=3000):
        self._clear_bubble()
        fw = self.canvas.winfo_width()
        self.bubble_bg  = self.canvas.create_rectangle(
            4, 2, fw - 4, 22, fill='#ffffc8', outline='#666666')
        self.bubble_txt = self.canvas.create_text(
            fw // 2, 12, text=text, font=('Arial', 7, 'bold'), fill='#222222')
        self.root.after(ms, self._clear_bubble)

    def _clear_bubble(self):
        for attr in ('bubble_bg', 'bubble_txt'):
            _id = getattr(self, attr, None)
            if _id: self.canvas.delete(_id)
            setattr(self, attr, None)

    # ── drag ──────────────────────────────────────────────────
    def _drag_start(self, e):
        self._dx = e.x_root - int(self.x)
        self._dy = e.y_root - int(self.y)
        self._dragging = False

    def _drag_move(self, e):
        self._dragging = True
        self.x = float(e.x_root - self._dx)
        self.y = float(e.y_root - self._dy)
        # clamp
        self.x = max(40, min(self.sw - 40, self.x))
        self.y = max(40, min(self.sh - 60, self.y))
        self._place()

    def _drag_end(self, e):
        if not self._dragging:
            self._say(random.choice(["Hi there! 👋", "Ho Ho! 🎅", "Right-click for menu!"]), 2000)

    # ── context menu ─────────────────────────────────────────
    def _menu(self, e):
        m = tk.Menu(self.root, tearoff=0, bg='#161b22', fg='#e6edf3',
                    activebackground='#21262d', activeforeground='#58a6ff',
                    font=('Arial', 10))
        m.add_command(label="💧  Water Reminder",  command=lambda: self._water.show(self.root))
        m.add_command(label="🏥  PC Health Check", command=lambda: self._health.show(self.root))
        m.add_command(label="🧹  Clean Cache",     command=lambda: self._cleaner.show(self.root))
        m.add_separator()
        lbl = "▶  Resume" if self.paused else "⏸  Pause"
        m.add_command(label=lbl, command=self._toggle_pause)
        m.add_command(label="⚙️  Settings",        command=self._settings)
        m.add_separator()
        m.add_command(label="❌  Exit",            command=self._quit)
        m.tk_popup(e.x_root, e.y_root)

    def _toggle_pause(self):
        self.paused = not self.paused
        self._say("Paused ⏸" if self.paused else "Let's go! 🏃", 2000)

    def _settings(self):
        win = tk.Toplevel(self.root)
        win.title("⚙️ Settings")
        win.geometry("300+{}+{}".format(
            self.root.winfo_screenwidth()//2 - 150,
            self.root.winfo_screenheight()//2 - 130))
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.configure(bg='#0d1117')

        def lbl(t): tk.Label(win, text=t, bg='#0d1117', fg='#c9d1d9',
                              font=('Arial', 10)).pack(pady=(10, 0))

        lbl("Walking Speed  (1 = slow, 8 = fast)")
        spd = tk.IntVar(value=self.cfg.speed)
        tk.Scale(win, from_=1, to=8, orient='horizontal', variable=spd,
                 bg='#0d1117', fg='#c9d1d9', troughcolor='#21262d',
                 highlightthickness=0, length=220).pack()

        lbl("Water Reminder Interval (minutes)")
        wtr = tk.IntVar(value=self.cfg.water_mins)
        tk.Scale(win, from_=5, to=120, orient='horizontal', variable=wtr,
                 bg='#0d1117', fg='#c9d1d9', troughcolor='#21262d',
                 highlightthickness=0, length=220).pack()

        def apply():
            self.cfg.speed      = spd.get()
            self.cfg.water_mins = wtr.get()
            win.destroy()
            self._say("Settings saved ✅", 2000)

        tk.Button(win, text="Save", command=apply,
                  bg='#238636', fg='white', font=('Arial', 11, 'bold'),
                  relief='flat', padx=30, pady=7, cursor='hand2').pack(pady=18)

    def _quit(self):
        if messagebox.askyesno("Exit", "Close Santa Pet?", parent=self.root):
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    SantaPetApp().run()
