"""Santa Pet 3D — dancing desktop companion"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading, random, os, glob, psutil, shutil, tempfile
from datetime import datetime
from todo_manager import TodoWindow

TR = (0, 0, 0, 0)
W, H, CX = 126, 186, 63

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
        sw, sh = sprite.size
        frame = Image.new('RGBA', (W, H), TR)
        x = (W - sw) // 2
        y = H - sh - 2
        frame.paste(sprite, (x, y), sprite)
        if flip:
            frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
        frames.append(frame)
    return frames


def _build_anims():
    walk_r = _load_anim('walk')
    walk_l = _load_anim('walk', flip=True)
    idle   = _load_anim('idle')
    shimmy = _load_anim('jump')
    wave   = _load_anim('slide')
    groove = _load_anim('run')

    base = idle[0] if idle else Image.new('RGBA', (W, H), TR)
    spin_widths = [W, 96, 65, 30, 10, 30, 65, 96]
    spin_frames = []
    for sw in spin_widths:
        if sw == W:
            spin_frames.append(base.copy())
        else:
            sq = base.resize((sw, H), Image.LANCZOS)
            frame = Image.new('RGBA', (W, H), TR)
            frame.paste(sq, ((W - sw) // 2, 0))
            spin_frames.append(frame)

    return {
        'walk_r':       walk_r,
        'walk_l':       walk_l,
        'idle':         idle,
        'shimmy':       shimmy,
        'wave':         wave,
        'groove':       groove,
        '_spin_frames': spin_frames,
    }


ANIM = _build_anims()
SPIN_FRAMES = ANIM.pop('_spin_frames')

DANCE_NAMES  = ['shimmy', 'wave', 'spin', 'groove']
DANCE_QUIPS  = {
    'shimmy': ["🕺 Shimmy!", "Santa shuffle!", "Ho Ho Shake!"],
    'wave':   ["👋 Ho Ho Ho!", "Waving! 🎄", "Hello! 🎅"],
    'spin':   ["🌀 Wheee!", "Round & round!", "Spinning! ⭐"],
    'groove': ["🎵 Feeling it!", "Jingle boogie! 🔔", "Groovin'! 🎶"],
}


# ─────────────────────────── PC HEALTH ───────────────────────

class PCHealth:
    def show(self, parent):
        win = tk.Toplevel(parent)
        win.title("PC Doctor — Health Report")
        win.geometry("460x560")
        win.resizable(True, True)
        win.attributes('-topmost', True)
        win.configure(bg='#0d1117')
        hdr = tk.Frame(win, bg='#161b22', pady=10)
        hdr.pack(fill='x')
        tk.Label(hdr, text="🏥  PC Doctor", font=('Arial', 15, 'bold'),
                 bg='#161b22', fg='#58a6ff').pack()
        tk.Label(hdr, text=datetime.now().strftime('%Y-%m-%d  %H:%M:%S'),
                 font=('Arial', 9), bg='#161b22', fg='#8b949e').pack()
        container = tk.Frame(win, bg='#0d1117')
        container.pack(fill='both', expand=True)
        cv = tk.Canvas(container, bg='#0d1117', highlightthickness=0)
        sb = ttk.Scrollbar(container, orient='vertical', command=cv.yview)
        frm = tk.Frame(cv, bg='#0d1117')
        frm.bind('<Configure>', lambda e: cv.configure(scrollregion=cv.bbox('all')))
        cv.create_window((0, 0), window=frm, anchor='nw')
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        def sec(t):
            f = tk.Frame(frm, bg='#21262d', pady=5, padx=8)
            f.pack(fill='x', padx=8, pady=(8, 2))
            tk.Label(f, text=t, font=('Arial', 10, 'bold'),
                     bg='#21262d', fg='#58a6ff').pack(anchor='w')

        def row(label, val, pct=None):
            f = tk.Frame(frm, bg='#161b22', padx=10, pady=5)
            f.pack(fill='x', padx=8, pady=1)
            color = '#3fb950' if (pct or 0) < 60 else '#d29922' if (pct or 0) < 85 else '#f85149'
            tk.Label(f, text=label, font=('Arial', 9), bg='#161b22',
                     fg='#c9d1d9', width=22, anchor='w').grid(row=0, column=0)
            tk.Label(f, text=val, font=('Arial', 9, 'bold'),
                     bg='#161b22', fg=color).grid(row=0, column=1, padx=10)
            if pct is not None:
                bar = tk.Canvas(f, width=100, height=8, bg='#30363d', highlightthickness=0)
                bar.grid(row=0, column=2, padx=5)
                bar.create_rectangle(0, 0, pct, 8, fill=color, width=0)

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
        tk.Button(win, text="Close", command=win.destroy,
                  bg='#238636', fg='white', font=('Arial', 11, 'bold'),
                  relief='flat', padx=25, pady=7).pack(pady=10)


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
        win.geometry("500x540")
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.configure(bg='#0d1117')
        hdr = tk.Frame(win, bg='#161b22', pady=10)
        hdr.pack(fill='x')
        tk.Label(hdr, text="🧹  Santa's Cache Cleaner",
                 font=('Arial', 14, 'bold'), bg='#161b22', fg='#58a6ff').pack()
        lf = tk.Frame(win, bg='#0d1117')
        lf.pack(fill='both', expand=True, padx=12, pady=8)
        sv = tk.StringVar(value="Scanning…")
        tv = tk.StringVar(value="Total: —")
        tk.Label(win, textvariable=sv, font=('Arial', 9), bg='#0d1117', fg='#8b949e').pack()
        tk.Label(win, textvariable=tv, font=('Arial', 12, 'bold'), bg='#0d1117', fg='#3fb950').pack(pady=3)
        pg = ttk.Progressbar(win, mode='indeterminate')
        pg.pack(fill='x', padx=16, pady=4)
        pg.start()
        bf = tk.Frame(win, bg='#0d1117')
        bf.pack(pady=8)
        cb_vars = {}
        clean_btn = tk.Button(bf, text="🧹 Clean Selected",
                              font=('Arial', 11, 'bold'), bg='#da3633', fg='white',
                              relief='flat', padx=15, pady=7, state='disabled', cursor='hand2')
        clean_btn.pack(side='left', padx=6)
        tk.Button(bf, text="Close", command=win.destroy,
                  font=('Arial', 11), bg='#30363d', fg='white',
                  relief='flat', padx=15, pady=7, cursor='hand2').pack(side='left', padx=6)

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
                row = tk.Frame(lf, bg='#161b22', padx=8, pady=6)
                row.pack(fill='x', pady=2)
                tk.Checkbutton(row, variable=var, bg='#161b22',
                               activebackground='#161b22', selectcolor='#21262d').pack(side='left')
                tk.Label(row, text=name, font=('Arial', 10, 'bold'),
                         bg='#161b22', fg='#e6edf3', width=22, anchor='w').pack(side='left')
                color = '#f85149' if sz > 100*2**20 else '#d29922' if sz > 5*2**20 else '#3fb950'
                tk.Label(row, text=self._fmt(sz), font=('Arial', 10),
                         bg='#161b22', fg=color).pack(side='right', padx=8)
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
        w.geometry(f"340x240+{cx}+{cy}")
        w.resizable(False, False)
        w.attributes('-topmost', True)
        w.configure(bg=BG0)

        # ── header ──────────────────────────────────────────────
        hdr = tk.Frame(w, bg=BG1, pady=14)
        hdr.pack(fill='x')
        tk.Label(hdr, text="💧", font=('Segoe UI Emoji', 40),
                 bg=BG1).pack()
        tk.Label(hdr, text="Time to Drink Water!", font=('Arial', 14, 'bold'),
                 bg=BG1, fg=ACC).pack(pady=(2, 0))

        # ── body ────────────────────────────────────────────────
        tk.Frame(w, height=1, bg=BOR).pack(fill='x')
        tk.Label(w, text="Santa says: Stay hydrated! 🥤",
                 font=('Arial', 10), bg=BG0, fg=SUB).pack(pady=14)

        # ── button ──────────────────────────────────────────────
        btn = tk.Button(w, text="Thanks Santa! 🎅", command=w.destroy,
                        bg='#1f6feb', fg=FG, font=('Arial', 11, 'bold'),
                        relief='flat', padx=24, pady=8, cursor='hand2',
                        activebackground='#388bfd', activeforeground=FG)
        btn.pack(pady=10)
        w.after(30000, lambda: w.destroy() if w.winfo_exists() else None)


# ─────────────────────────── FLOAT MENU ─────────────────────

BG0 = '#0d1117'   # darkest
BG1 = '#161b22'   # panel
BG2 = '#21262d'   # hover
BOR = '#30363d'   # border
FG  = '#e6edf3'
SUB = '#8b949e'
ACC = '#58a6ff'
GRN = '#3fb950'
RED_C = '#f85149'


class FloatMenu:
    """Custom dark floating menu — replaces the OS context menu."""

    def __init__(self, parent):
        self._parent = parent
        self._win    = None

    def show(self, mx, my, sections):
        """
        sections: list of lists of items.
        item tuple: (icon, title, subtitle_or_None, command_or_None, danger_bool=False)
        """
        if self._win and self._win.winfo_exists():
            self._win.destroy()

        win = tk.Toplevel(self._parent)
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        self._win = win

        # border via outer frame
        outer = tk.Frame(win, bg=BOR, padx=1, pady=1)
        outer.pack(expand=True, fill='both')
        body = tk.Frame(outer, bg=BG1, pady=4)
        body.pack(expand=True, fill='both')

        for si, section in enumerate(sections):
            if si > 0:
                tk.Frame(body, height=1, bg=BOR).pack(fill='x', pady=2)
            for item in section:
                self._row(body, item, win)

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
        fg_col = RED_C if danger else FG

        row = tk.Frame(parent, bg=BG1, cursor='hand2' if cmd else 'arrow')
        row.pack(fill='x')

        # icon cell
        ic = tk.Label(row, text=icon, font=('Segoe UI Emoji', 13),
                      bg=BG1, fg=fg_col, width=3, anchor='center')
        ic.pack(side='left', padx=(6, 2), pady=6)

        # text cell
        tf = tk.Frame(row, bg=BG1)
        tf.pack(side='left', fill='x', expand=True, padx=(0, 14))

        tl = tk.Label(tf, text=title, font=('Arial', 10),
                      bg=BG1, fg=fg_col, anchor='w')
        tl.pack(fill='x', pady=(5 if sub else 6, 0))

        sl = None
        if sub:
            sl = tk.Label(tf, text=sub, font=('Arial', 8),
                          bg=BG1, fg=SUB, anchor='w')
            sl.pack(fill='x', pady=(0, 5))

        # collect every widget in the row for hover binding
        all_w = [row, ic, tf, tl] + ([sl] if sl else [])

        def _enter(e, ws=all_w):
            for w in ws:
                try: w.configure(bg=BG2)
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
        self.sx = float(random.randint(150, self.sw - 200))
        self.sy = float(self.sh - 200)
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

        # canvas
        self.canvas = tk.Canvas(self.root, width=W, height=H+24,
                                bg='black', highlightthickness=0)
        self.canvas.pack()
        self._img_id    = self.canvas.create_image(W//2, H//2+12,
                                                   image=self._get_tk_frame())
        self._bub_bg  = None
        self._bub_txt = None

        # bindings
        self.canvas.bind('<Button-1>',        self._on_click)
        self.canvas.bind('<Button-3>',        self._menu)
        self.canvas.bind('<ButtonPress-1>',   self._drag_start)
        self.canvas.bind('<B1-Motion>',       self._drag_move)
        self.canvas.bind('<ButtonRelease-1>', self._drag_end)
        self._dragging = False
        self._dx = self._dy = 0

        # helpers
        self._water       = WaterPopup()
        self._health      = PCHealth()
        self._cleaner     = CacheCleaner()
        self._todo        = TodoWindow(self.root, on_remind_cb=self._task_remind)
        self._float_menu  = FloatMenu(self.root)

        self._place()
        self._tick()
        self._tick_remind()
        self._schedule_quip()

    # ── pre-render all frames ─────────────────────────────────
    def _pre_render(self):
        for key, frames in ANIM.items():
            self._tk_frames[key] = [ImageTk.PhotoImage(f) for f in frames]
        self._tk_frames['spin'] = [ImageTk.PhotoImage(f) for f in SPIN_FRAMES]

    def _get_tk_frame(self):
        return self._tk_frames[self.anim][self.frame_idx % len(self._tk_frames[self.anim])]

    # ── window placement ─────────────────────────────────────
    def _place(self):
        self.root.geometry(f"+{int(self.sx - W//2)}+{int(self.sy - H//2)}")

    # ── main tick ────────────────────────────────────────────
    def _tick(self):
        if not self.paused:
            frames = self._tk_frames[self.anim]
            self.frame_idx = (self.frame_idx + 1) % len(frames)

            # advance dance loop counter
            if self.anim in DANCE_NAMES + ['spin']:
                if self.frame_idx == 0:
                    self.dance_loops += 1
                    if self.dance_loops >= self.dance_loops_goal:
                        self._set_anim('walk_r' if self.dir == 'r' else 'walk_l')

            # walk movement
            elif self.anim in ('walk_r', 'walk_l'):
                if self.dir == 'r':
                    self.sx += self.speed
                    if self.sx > self.sw - 80: self.dir = 'l'; self._set_anim('walk_l')
                else:
                    self.sx -= self.speed
                    if self.sx < 80: self.dir = 'r'; self._set_anim('walk_r')
                self._place()

            self.canvas.itemconfig(self._img_id, image=self._get_tk_frame())

        self.root.after(self.ANIM_DELAY, self._tick)

    def _set_anim(self, name):
        self.anim      = name
        self.frame_idx = 0

    # ── click → dance ────────────────────────────────────────
    def _on_click(self, e):
        if self._dragging: return
        if self.anim in DANCE_NAMES + ['spin']: return   # already dancing

        dance = random.choice(DANCE_NAMES)
        quip  = random.choice(DANCE_QUIPS[dance])
        self._say(quip, 4000)
        self._set_anim(dance if dance != 'spin' else 'spin')
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
        self._bub_bg  = self.canvas.create_rectangle(4, 2, fw-4, 22,
                                                     fill='#ffffc8', outline='#666')
        self._bub_txt = self.canvas.create_text(fw//2, 12, text=text,
                                                font=('Arial', 7, 'bold'), fill='#222')
        self.root.after(ms, self._clear_bubble)

    def _clear_bubble(self):
        for attr in ('_bub_bg', '_bub_txt'):
            _id = getattr(self, attr, None)
            if _id: self.canvas.delete(_id)
            setattr(self, attr, None)

    # ── drag ─────────────────────────────────────────────────
    def _drag_start(self, e):
        self._dragging = False
        self._dx = e.x_root - int(self.sx)
        self._dy = e.y_root - int(self.sy)

    def _drag_move(self, e):
        self._dragging = True
        self.sx = max(40, min(self.sw-40, float(e.x_root - self._dx)))
        self.sy = max(40, min(self.sh-60, float(e.y_root - self._dy)))
        self._place()

    def _drag_end(self, e):
        self._dragging = False

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
        self._say("Paused ⏸" if self.paused else "Let's go! 🎅", 2000)

    def _settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("320x280+{}+{}".format(
            self.sw//2-160, self.sh//2-140))
        win.resizable(False, False)
        win.attributes('-topmost', True)
        win.configure(bg=BG0)

        # ── header ──────────────────────────────────────────────
        hdr = tk.Frame(win, bg=BG1, pady=10)
        hdr.pack(fill='x')
        tk.Label(hdr, text="⚙️  Settings", font=('Arial', 14, 'bold'),
                 bg=BG1, fg=ACC).pack()
        tk.Label(hdr, text="Speed & reminder preferences",
                 font=('Arial', 9), bg=BG1, fg=SUB).pack(pady=(2,0))
        tk.Frame(win, height=1, bg=BOR).pack(fill='x')

        body = tk.Frame(win, bg=BG0, padx=20)
        body.pack(fill='both', expand=True)

        def lbl(t):
            tk.Label(body, text=t, bg=BG0, fg=FG,
                     font=('Arial', 10)).pack(anchor='w', pady=(12, 0))

        lbl("🚶 Walking Speed  (1 = slow · 8 = fast)")
        spd = tk.IntVar(value=self.speed)
        tk.Scale(body, from_=1, to=8, orient='horizontal', variable=spd,
                 bg=BG0, fg=FG, troughcolor=BG2,
                 highlightthickness=0, length=260).pack(fill='x')

        lbl("💧 Water Reminder (minutes)")
        wtr = tk.IntVar(value=self._water_mins)
        tk.Scale(body, from_=5, to=120, orient='horizontal', variable=wtr,
                 bg=BG0, fg=FG, troughcolor=BG2,
                 highlightthickness=0, length=260).pack(fill='x')

        def apply():
            self.speed       = spd.get()
            self._water_mins = wtr.get()
            win.destroy()
            self._say("Settings saved ✅", 2000)

        tk.Frame(win, height=1, bg=BOR).pack(fill='x')
        tk.Button(win, text="Save Settings", command=apply,
                  bg=GRN, fg='white', font=('Arial', 11, 'bold'),
                  relief='flat', padx=24, pady=8, cursor='hand2',
                  activebackground='#56d364', activeforeground='white').pack(pady=14)

    # ── task reminder callback ────────────────────────────────
    def _task_remind(self, task):
        self._say(f"⏰ {task['title'][:22]}", 8000)
        self.root.after(500, lambda: self._show_task_popup(task))

    def _show_task_popup(self, task):
        w = tk.Toplevel(self.root)
        w.title("Task Reminder")
        w.geometry("340x220+{}+{}".format(self.sw//2-170, self.sh//2-110))
        w.resizable(False, False)
        w.attributes('-topmost', True)
        w.configure(bg=BG0)

        hdr = tk.Frame(w, bg=BG1, pady=12)
        hdr.pack(fill='x')
        tk.Label(hdr, text="⏰", font=('Segoe UI Emoji', 32), bg=BG1).pack()
        tk.Label(hdr, text="Task Reminder", font=('Arial', 12, 'bold'),
                 bg=BG1, fg=ACC).pack(pady=(2,0))

        tk.Frame(w, height=1, bg=BOR).pack(fill='x')
        tk.Label(w, text=task['title'], font=('Arial', 13, 'bold'),
                 bg=BG0, fg=FG, wraplength=300).pack(pady=(12,2))
        if task.get('note'):
            tk.Label(w, text=task['note'], font=('Arial', 9),
                     bg=BG0, fg=SUB).pack(pady=2)

        tk.Button(w, text="Got it! ✅", command=w.destroy,
                  bg=GRN, fg='white', font=('Arial', 11, 'bold'),
                  relief='flat', padx=20, pady=7, cursor='hand2',
                  activebackground='#56d364', activeforeground='white').pack(pady=14)
        w.after(60000, lambda: w.destroy() if w.winfo_exists() else None)

    def _quit(self):
        if messagebox.askyesno("Exit", "Close Santa Pet?", parent=self.root):
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    SantaPetApp().run()
