"""To-Do list — powered by Google Tasks"""

import tkinter as tk
from tkinter import ttk, messagebox
import json, os, threading, webbrowser
from datetime import datetime
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES   = ['https://www.googleapis.com/auth/tasks']
DATA_DIR = Path(os.environ.get('APPDATA', Path.home())) / 'SantaPet'
DATA_DIR.mkdir(exist_ok=True)
TASKS_FILE = DATA_DIR / 'tasks.json'     # offline cache — read by FloatMenu
TOKEN_FILE = DATA_DIR / 'google_token.json'
CREDS_FILE = DATA_DIR / 'credentials.json'

DARK = {
    'bg':      '#0d1117',
    'panel':   '#161b22',
    'card':    '#21262d',
    'border':  '#30363d',
    'text':    '#e6edf3',
    'subtext': '#8b949e',
    'accent':  '#58a6ff',
    'green':   '#3fb950',
    'red':     '#f85149',
    'done_fg': '#484f58',
}


# ─────────────────────── LOCAL CACHE ─────────────────────────────
# Kept only so FloatMenu can count active tasks without a network call.

class LocalTaskStore:
    def load(self):
        try:
            if TASKS_FILE.exists():
                return json.loads(TASKS_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
        return []

    def _save(self, tasks):
        TASKS_FILE.write_text(
            json.dumps(tasks, indent=2, ensure_ascii=False), encoding='utf-8')

    def mirror(self, tasks):
        """Overwrite cache with the current Google Tasks list."""
        self._save(tasks)


# ─────────────────────── GOOGLE TASKS ────────────────────────────

class GoogleTasksSync:
    def __init__(self):
        self._service  = None
        self._list_id  = None

    def is_configured(self):
        return CREDS_FILE.exists() and GOOGLE_AVAILABLE

    def is_connected(self):
        return self._service is not None

    def connect(self):
        if not GOOGLE_AVAILABLE:
            return False, "Google libraries not installed"
        if not CREDS_FILE.exists():
            return False, f"credentials.json not found at:\n{CREDS_FILE}"
        try:
            creds = None
            if TOKEN_FILE.exists():
                try:
                    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
                except Exception:
                    TOKEN_FILE.unlink(missing_ok=True)
                    creds = None
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            if not creds or not creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
                creds = flow.run_local_server(
                    port=0, open_browser=True,
                    success_message="Santa Pet connected to Google Tasks! You can close this tab.")
                TOKEN_FILE.write_text(creds.to_json())
            self._service = build('tasks', 'v1', credentials=creds)
            lists = self._service.tasklists().list().execute()
            self._list_id = None
            for lst in lists.get('items', []):
                if lst['title'] == 'Santa Pet':
                    self._list_id = lst['id']
                    break
            if not self._list_id:
                new = self._service.tasklists().insert(body={'title': 'Santa Pet'}).execute()
                self._list_id = new['id']
            return True, "Connected to Google Tasks!"
        except Exception as e:
            self._service = None
            self._list_id = None
            err = str(e)
            if 'access_denied' in err.lower():
                return False, "Access denied — check Google account permissions"
            if 'invalid_client' in err.lower():
                return False, "Invalid credentials — re-download credentials.json"
            return False, err[:120]

    def disconnect(self):
        TOKEN_FILE.unlink(missing_ok=True)
        self._service = None
        self._list_id = None

    def fetch_all(self):
        if not self.is_connected():
            return []
        try:
            result = self._service.tasks().list(
                tasklist=self._list_id, showCompleted=True, maxResults=100).execute()
            return result.get('items', [])
        except Exception:
            return []

    def add_task(self, title, note='', due=None):
        body = {'title': title, 'notes': note, 'status': 'needsAction'}
        if due:
            body['due'] = due + 'T00:00:00.000Z'
        result = self._service.tasks().insert(tasklist=self._list_id, body=body).execute()
        return result

    def update_status(self, google_id, title, done):
        body = {
            'id':     google_id,
            'title':  title,
            'status': 'completed' if done else 'needsAction',
        }
        self._service.tasks().update(
            tasklist=self._list_id, task=google_id, body=body).execute()

    def delete_task(self, google_id):
        try:
            self._service.tasks().delete(
                tasklist=self._list_id, task=google_id).execute()
        except Exception:
            pass


# ─────────────────────── TODO WINDOW ─────────────────────────────

def _gt_to_task(gt):
    """Convert a raw Google Tasks item to our display dict."""
    return {
        'id':    gt['id'],
        'title': gt.get('title', '(no title)'),
        'note':  gt.get('notes', ''),
        'due':   gt.get('due', '').replace('T00:00:00.000Z', '') if gt.get('due') else '',
        'done':  gt.get('status') == 'completed',
    }


class TodoWindow:
    def __init__(self, parent, on_remind_cb=None):
        self.parent    = parent
        self.google    = GoogleTasksSync()
        self._cache    = LocalTaskStore()
        self._tasks    = []        # in-memory list from Google Tasks
        self._filter   = 'all'
        self._status_var  = None
        self._stats_var   = None
        self._gtbtn_var   = None

    # ── open ──────────────────────────────────────────────────────
    def show(self):
        if hasattr(self, '_win') and self._win.winfo_exists():
            self._win.lift(); return

        win = tk.Toplevel(self.parent)
        win.title("🎄 Santa's To-Do List")
        win.geometry("460x580")
        win.minsize(380, 380)
        win.attributes('-topmost', True)
        win.configure(bg=DARK['bg'])
        win.protocol('WM_DELETE_WINDOW', win.destroy)
        self._win = win

        self._build_ui(win)

        if self.google.is_connected():
            self._fetch_tasks()
        elif self.google.is_configured():
            self._auto_connect()
        else:
            self._refresh()

    def _auto_connect(self):
        """Silently reconnect using the saved token (no browser needed if token valid)."""
        self._set_status("Connecting to Google Tasks…")
        def work():
            ok, msg = self.google.connect()
            self._win.after(0, lambda: self._after_connect(ok, msg))
        threading.Thread(target=work, daemon=True).start()

    # ── build UI ──────────────────────────────────────────────────
    def _build_ui(self, win):
        # header
        hdr = tk.Frame(win, bg=DARK['panel'], pady=8)
        hdr.pack(fill='x')

        tk.Label(hdr, text="🎄  Santa's To-Do List",
                 font=('Arial', 14, 'bold'),
                 bg=DARK['panel'], fg=DARK['accent']).pack(side='left', padx=12)

        self._gtbtn_var = tk.StringVar()
        self._update_gtbtn_label()
        tk.Button(hdr, textvariable=self._gtbtn_var,
                  font=('Arial', 8), bg=DARK['card'], fg=DARK['text'],
                  relief='flat', padx=8, pady=4, cursor='hand2',
                  command=self._toggle_google).pack(side='right', padx=8)

        # add-task bar
        add_frame = tk.Frame(win, bg=DARK['bg'], pady=6)
        add_frame.pack(fill='x', padx=10)

        self._entry = tk.Entry(add_frame, font=('Arial', 11),
                               bg=DARK['card'], fg=DARK['text'],
                               insertbackground=DARK['text'],
                               relief='flat', bd=0)
        self._entry.pack(side='left', fill='x', expand=True, ipady=7, ipadx=6)
        self._entry.insert(0, 'Add a task…')
        self._entry.configure(fg=DARK['subtext'])
        self._entry.bind('<FocusIn>',  self._entry_focus_in)
        self._entry.bind('<FocusOut>', self._entry_focus_out)
        self._entry.bind('<Return>',   lambda e: self._quick_add())

        tk.Button(add_frame, text='＋ Add',
                  font=('Arial', 10, 'bold'), bg='#238636', fg='white',
                  relief='flat', padx=10, pady=7, cursor='hand2',
                  command=self._quick_add).pack(side='left', padx=(6, 0))

        tk.Button(add_frame, text='↻',
                  font=('Arial', 12), bg=DARK['card'], fg=DARK['accent'],
                  relief='flat', padx=8, pady=7, cursor='hand2',
                  command=self._fetch_tasks).pack(side='left', padx=4)

        # filter tabs
        tabs = tk.Frame(win, bg=DARK['bg'])
        tabs.pack(fill='x', padx=10, pady=(0, 4))
        self._tab_btns = {}
        for key, label in [('all', 'All'), ('active', 'Active'), ('done', 'Done')]:
            b = tk.Button(tabs, text=label, font=('Arial', 9),
                          relief='flat', padx=12, pady=4, cursor='hand2',
                          command=lambda k=key: self._set_filter(k))
            b.pack(side='left', padx=2)
            self._tab_btns[key] = b
        self._style_tabs()

        # status bar
        status_bar = tk.Frame(win, bg=DARK['bg'])
        status_bar.pack(fill='x', padx=10, pady=(0, 4))
        self._status_var = tk.StringVar(value='')
        tk.Label(status_bar, textvariable=self._status_var,
                 font=('Arial', 8), bg=DARK['bg'],
                 fg=DARK['subtext']).pack(side='left')

        # task list
        container = tk.Frame(win, bg=DARK['bg'])
        container.pack(fill='both', expand=True, padx=10, pady=4)

        self._canvas = tk.Canvas(container, bg=DARK['bg'], highlightthickness=0)
        sb = ttk.Scrollbar(container, orient='vertical', command=self._canvas.yview)
        self._list_frame = tk.Frame(self._canvas, bg=DARK['bg'])
        self._list_frame.bind('<Configure>',
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox('all')))
        self._canvas.create_window((0, 0), window=self._list_frame, anchor='nw')
        self._canvas.configure(yscrollcommand=sb.set)
        self._canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        self._canvas.bind_all('<MouseWheel>',
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        # stats footer
        self._stats_var = tk.StringVar(value='')
        tk.Label(win, textvariable=self._stats_var,
                 font=('Arial', 9), bg=DARK['panel'],
                 fg=DARK['subtext'], pady=6).pack(fill='x')

    def _entry_focus_in(self, e):
        if self._entry.get() == 'Add a task…':
            self._entry.delete(0, 'end')
            self._entry.configure(fg=DARK['text'])

    def _entry_focus_out(self, e):
        if not self._entry.get():
            self._entry.insert(0, 'Add a task…')
            self._entry.configure(fg=DARK['subtext'])

    # ── filter ────────────────────────────────────────────────────
    def _set_filter(self, key):
        self._filter = key
        self._style_tabs()
        self._refresh()

    def _style_tabs(self):
        for key, btn in self._tab_btns.items():
            if key == self._filter:
                btn.configure(bg=DARK['accent'], fg='white')
            else:
                btn.configure(bg=DARK['card'], fg=DARK['subtext'])

    # ── fetch from Google Tasks ───────────────────────────────────
    def _fetch_tasks(self):
        if not self.google.is_connected():
            self._refresh()
            return
        self._set_status("Loading from Google Tasks…")
        def work():
            raw = self.google.fetch_all()
            tasks = [_gt_to_task(gt) for gt in raw if gt.get('title')]
            self._win.after(0, lambda: self._after_fetch(tasks))
        threading.Thread(target=work, daemon=True).start()

    def _after_fetch(self, tasks):
        self._tasks = tasks
        # mirror to local cache so FloatMenu can read task count
        cache_fmt = [{'id': t['id'], 'title': t['title'], 'done': t['done']} for t in tasks]
        self._cache.mirror(cache_fmt)
        self._refresh()
        done  = sum(1 for t in tasks if t['done'])
        total = len(tasks)
        self._set_status(f"✅ {total - done} active, {done} done — {datetime.now().strftime('%H:%M')}")

    # ── refresh display ───────────────────────────────────────────
    def _refresh(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        tasks = list(self._tasks)
        if self._filter == 'active':
            tasks = [t for t in tasks if not t['done']]
        elif self._filter == 'done':
            tasks = [t for t in tasks if t['done']]
        tasks.sort(key=lambda t: (t['done'], t.get('title', '')))

        if not tasks:
            if not self.google.is_connected():
                # not connected — show connect prompt
                frm = tk.Frame(self._list_frame, bg=DARK['bg'])
                frm.pack(expand=True, fill='both', pady=40)
                tk.Label(frm, text="🔗  Connect Google Tasks\nto see and manage your tasks",
                         font=('Arial', 11), bg=DARK['bg'],
                         fg=DARK['subtext'], justify='center').pack(pady=10)
                tk.Button(frm, text="Connect Now",
                          font=('Arial', 10, 'bold'), bg=DARK['accent'], fg='white',
                          relief='flat', padx=16, pady=8, cursor='hand2',
                          command=self._toggle_google).pack()
            else:
                tk.Label(self._list_frame, text="No tasks yet — add one above! 🎅",
                         font=('Arial', 11), bg=DARK['bg'],
                         fg=DARK['subtext'], pady=40).pack()
        else:
            for t in tasks:
                self._task_card(t)

        done  = sum(1 for t in self._tasks if t['done'])
        total = len(self._tasks)
        if self._stats_var:
            self._stats_var.set(f"  {done} done  /  {total - done} active  /  {total} total")

    def _task_card(self, task):
        card = tk.Frame(self._list_frame, bg=DARK['card'], padx=10, pady=8)
        card.pack(fill='x', pady=3, padx=2)

        done_var = tk.BooleanVar(value=task['done'])
        tk.Checkbutton(card, variable=done_var,
                       bg=DARK['card'], activebackground=DARK['card'],
                       selectcolor=DARK['panel'],
                       command=lambda t=task, v=done_var: self._toggle(t, v)
                       ).pack(side='left')

        txt = tk.Frame(card, bg=DARK['card'])
        txt.pack(side='left', fill='x', expand=True, padx=6)

        fg   = DARK['done_fg'] if task['done'] else DARK['text']
        font = ('Arial', 10, 'overstrike') if task['done'] else ('Arial', 10, 'bold')
        tk.Label(txt, text=task['title'], font=font,
                 bg=DARK['card'], fg=fg, anchor='w').pack(fill='x')

        meta = []
        if task.get('note'):
            meta.append(f"📝 {task['note'][:50]}")
        if task.get('due'):
            meta.append(f"📅 {task['due']}")
        if meta:
            tk.Label(txt, text='  '.join(meta), font=('Arial', 8),
                     bg=DARK['card'], fg=DARK['subtext'], anchor='w').pack(fill='x')

        btn_frame = tk.Frame(card, bg=DARK['card'])
        btn_frame.pack(side='right')
        tk.Button(btn_frame, text='🗑', font=('Arial', 9),
                  bg=DARK['panel'], fg=DARK['red'], relief='flat',
                  padx=5, pady=2, cursor='hand2',
                  command=lambda t=task: self._delete_task(t)).pack(side='left')

    # ── add task ──────────────────────────────────────────────────
    def _quick_add(self):
        title = self._entry.get().strip()
        if not title or title == 'Add a task…':
            return
        if not self.google.is_connected():
            messagebox.showinfo("Not connected",
                                "Connect Google Tasks first to add tasks.",
                                parent=self._win)
            return
        self._entry.delete(0, 'end')
        self._entry_focus_out(None)
        self._set_status("Adding task…")
        def work():
            try:
                self.google.add_task(title)
                self._win.after(0, self._fetch_tasks)
            except Exception as e:
                self._win.after(0, lambda: self._set_status(f"❌ {str(e)[:60]}"))
        threading.Thread(target=work, daemon=True).start()

    # ── toggle done ───────────────────────────────────────────────
    def _toggle(self, task, var):
        new_done = var.get()
        # optimistic UI update
        for t in self._tasks:
            if t['id'] == task['id']:
                t['done'] = new_done
                break
        self._refresh()
        if not self.google.is_connected():
            return
        def work():
            try:
                self.google.update_status(task['id'], task['title'], new_done)
                self._win.after(500, self._fetch_tasks)
            except Exception as e:
                print(f"Toggle error: {e}")
        threading.Thread(target=work, daemon=True).start()

    # ── delete ────────────────────────────────────────────────────
    def _delete_task(self, task):
        if not messagebox.askyesno("Delete", f'Delete "{task["title"]}"?',
                                   parent=self._win):
            return
        self._tasks = [t for t in self._tasks if t['id'] != task['id']]
        self._refresh()
        if self.google.is_connected():
            threading.Thread(target=self.google.delete_task,
                             args=(task['id'],), daemon=True).start()

    # ── Google connect / disconnect ───────────────────────────────
    def _update_gtbtn_label(self):
        if not self._gtbtn_var:
            return
        if self.google.is_connected():
            self._gtbtn_var.set('🔗 Google: ON')
        elif self.google.is_configured():
            self._gtbtn_var.set('🔗 Connect Google')
        else:
            self._gtbtn_var.set('⚙ Setup Google')

    def _toggle_google(self):
        if self.google.is_connected():
            if messagebox.askyesno("Disconnect", "Disconnect Google Tasks?",
                                   parent=self._win):
                self.google.disconnect()
                self._tasks = []
                self._update_gtbtn_label()
                self._set_status("Disconnected from Google Tasks")
                self._refresh()
        elif self.google.is_configured():
            self._set_status("Connecting…")
            def work():
                ok, msg = self.google.connect()
                self._win.after(0, lambda: self._after_connect(ok, msg))
            threading.Thread(target=work, daemon=True).start()
        else:
            self._show_google_setup()

    def _after_connect(self, ok, msg):
        self._update_gtbtn_label()
        if ok:
            self._fetch_tasks()
        else:
            self._set_status("❌ " + msg[:60])
            self._refresh()

    def _set_status(self, msg):
        if self._status_var:
            self._status_var.set(msg)

    def _show_google_setup(self):
        dlg = tk.Toplevel(self._win)
        dlg.title("⚙️ Google Tasks Setup")
        dlg.geometry("460x360")
        dlg.resizable(False, False)
        dlg.attributes('-topmost', True)
        dlg.configure(bg=DARK['bg'])

        tk.Label(dlg, text="🔗  Connect Google Tasks",
                 font=('Arial', 13, 'bold'), bg=DARK['bg'],
                 fg=DARK['accent']).pack(pady=15)

        instructions = (
            "To sync with Google Tasks:\n\n"
            "1. Go to console.cloud.google.com\n"
            "2. Enable 'Tasks API'\n"
            "3. Credentials → Create → OAuth 2.0 Client ID\n"
            "   • Application type: Desktop app\n"
            "4. Download JSON → rename to  credentials.json\n"
            f"   → save to:  {CREDS_FILE}\n\n"
            "Then click 'Connect' below."
        )
        txt = tk.Text(dlg, font=('Arial', 9), bg=DARK['card'], fg=DARK['text'],
                      relief='flat', padx=10, pady=10, wrap='word', height=10)
        txt.insert('1.0', instructions)
        txt.configure(state='disabled')
        txt.pack(fill='both', expand=True, padx=16, pady=5)

        row = tk.Frame(dlg, bg=DARK['bg'])
        row.pack(pady=10)
        tk.Button(row, text="Open Google Console", font=('Arial', 10),
                  bg=DARK['card'], fg=DARK['accent'], relief='flat',
                  padx=12, pady=6, cursor='hand2',
                  command=lambda: webbrowser.open(
                      'https://console.cloud.google.com/apis/credentials')
                  ).pack(side='left', padx=6)
        tk.Button(row, text="Connect →", font=('Arial', 10, 'bold'),
                  bg='#238636', fg='white', relief='flat',
                  padx=12, pady=6, cursor='hand2',
                  command=lambda: [dlg.destroy(), self._toggle_google()]
                  ).pack(side='left', padx=6)
