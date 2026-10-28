"""To-Do list manager with optional Google Tasks sync"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import threading
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

# Google Tasks imports (graceful fallback if not configured)
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import googleapiclient.errors
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/tasks']
DATA_DIR = Path(os.environ.get('APPDATA', Path.home())) / 'SantaPet'
DATA_DIR.mkdir(exist_ok=True)
TASKS_FILE   = DATA_DIR / 'tasks.json'
TOKEN_FILE   = DATA_DIR / 'google_token.json'
CREDS_FILE   = DATA_DIR / 'google_credentials.json'


# ─────────────────────────── LOCAL STORE ─────────────────────

class LocalTaskStore:
    def load(self):
        if TASKS_FILE.exists():
            try:
                return json.loads(TASKS_FILE.read_text(encoding='utf-8'))
            except Exception:
                pass
        return []

    def save(self, tasks):
        TASKS_FILE.write_text(
            json.dumps(tasks, indent=2, ensure_ascii=False),
            encoding='utf-8')

    def add(self, title, note='', due=None, reminder=None):
        tasks = self.load()
        task = {
            'id':       str(int(datetime.now().timestamp() * 1000)),
            'title':    title,
            'note':     note,
            'due':      due,
            'reminder': reminder,
            'done':     False,
            'created':  datetime.now().isoformat(),
            'synced':   False,
            'google_id': None,
        }
        tasks.append(task)
        self.save(tasks)
        return task

    def toggle(self, task_id):
        tasks = self.load()
        for t in tasks:
            if t['id'] == task_id:
                t['done'] = not t['done']
                t['synced'] = False
        self.save(tasks)

    def delete(self, task_id):
        tasks = [t for t in self.load() if t['id'] != task_id]
        self.save(tasks)

    def update(self, task_id, **kwargs):
        tasks = self.load()
        for t in tasks:
            if t['id'] == task_id:
                t.update(kwargs)
                t['synced'] = False
        self.save(tasks)


# ─────────────────────────── GOOGLE TASKS ────────────────────

class GoogleTasksSync:
    def __init__(self):
        self._service = None
        self._list_id = None

    def is_configured(self):
        return CREDS_FILE.exists() and GOOGLE_AVAILABLE

    def is_connected(self):
        return self._service is not None

    def connect(self):
        if not self.is_configured():
            return False, "No credentials.json found"
        try:
            creds = None
            if TOKEN_FILE.exists():
                creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CREDS_FILE), SCOPES)
                    creds = flow.run_local_server(port=0)
                TOKEN_FILE.write_text(creds.to_json())
            self._service = build('tasks', 'v1', credentials=creds)
            # find or create "Santa Pet" tasklist
            lists = self._service.tasklists().list().execute()
            for lst in lists.get('items', []):
                if lst['title'] == 'Santa Pet':
                    self._list_id = lst['id']
                    break
            if not self._list_id:
                new = self._service.tasklists().insert(
                    body={'title': 'Santa Pet'}).execute()
                self._list_id = new['id']
            return True, "Connected!"
        except Exception as e:
            self._service = None
            return False, str(e)

    def disconnect(self):
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        self._service = None
        self._list_id = None

    def fetch_all(self):
        if not self.is_connected():
            return []
        try:
            result = self._service.tasks().list(
                tasklist=self._list_id,
                showCompleted=True,
                maxResults=100).execute()
            return result.get('items', [])
        except Exception:
            return []

    def push_task(self, task):
        if not self.is_connected():
            return None
        try:
            body = {
                'title':  task['title'],
                'notes':  task.get('note', ''),
                'status': 'completed' if task['done'] else 'needsAction',
            }
            if task.get('due'):
                body['due'] = task['due'] + 'T00:00:00.000Z'
            if task.get('google_id'):
                result = self._service.tasks().update(
                    tasklist=self._list_id,
                    task=task['google_id'],
                    body={**body, 'id': task['google_id']}).execute()
            else:
                result = self._service.tasks().insert(
                    tasklist=self._list_id, body=body).execute()
            return result.get('id')
        except Exception as e:
            print(f"Google push error: {e}")
            return None

    def delete_task(self, google_id):
        if not self.is_connected() or not google_id:
            return
        try:
            self._service.tasks().delete(
                tasklist=self._list_id, task=google_id).execute()
        except Exception:
            pass

    def sync_from_google(self, local_store):
        """Pull from Google and merge into local store"""
        google_tasks = self.fetch_all()
        local = local_store.load()
        local_by_gid = {t['google_id']: t for t in local if t.get('google_id')}

        new_from_google = 0
        for gt in google_tasks:
            gid = gt['id']
            if gid not in local_by_gid:
                # new task from Google — add locally
                task = {
                    'id':       'g_' + gid,
                    'title':    gt.get('title', '(no title)'),
                    'note':     gt.get('notes', ''),
                    'due':      gt.get('due', '').replace('T00:00:00.000Z', '') if gt.get('due') else None,
                    'reminder': None,
                    'done':     gt.get('status') == 'completed',
                    'created':  gt.get('updated', datetime.now().isoformat()),
                    'synced':   True,
                    'google_id': gid,
                }
                local.append(task)
                new_from_google += 1
        local_store.save(local)
        return new_from_google


# ─────────────────────────── REMINDER ENGINE ─────────────────

class ReminderEngine:
    """Background thread that fires reminder callbacks"""

    def __init__(self, local_store, on_remind):
        self._store    = local_store
        self._callback = on_remind
        self._running  = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._running:
            now = datetime.now()
            for task in self._store.load():
                if task['done'] or not task.get('reminder'):
                    continue
                try:
                    remind_at = datetime.fromisoformat(task['reminder'])
                    delta = (remind_at - now).total_seconds()
                    if -60 < delta < 60:           # within 1-min window
                        self._callback(task)
                except Exception:
                    pass
            import time; time.sleep(30)

    def stop(self):
        self._running = False


# ─────────────────────────── TODO WINDOW ─────────────────────

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
    'yellow':  '#d29922',
    'done_fg': '#484f58',
}


class TodoWindow:
    def __init__(self, parent, on_remind_cb=None):
        self.parent      = parent
        self.local       = LocalTaskStore()
        self.google      = GoogleTasksSync()
        self.on_remind   = on_remind_cb
        self._filter     = 'all'   # all / active / done
        self._sync_label = None
        self._reminder_engine = ReminderEngine(self.local, self._fire_reminder)

    def _fire_reminder(self, task):
        if self.on_remind:
            self.on_remind(task)

    # ── open / close ──────────────────────────────────────────
    def show(self):
        if hasattr(self, '_win') and self._win.winfo_exists():
            self._win.lift(); return

        win = tk.Toplevel(self.parent)
        win.title("🎄 Santa's To-Do List")
        win.geometry("480x620")
        win.minsize(400, 400)
        win.attributes('-topmost', True)
        win.configure(bg=DARK['bg'])
        win.protocol('WM_DELETE_WINDOW', win.destroy)
        self._win = win

        self._build_ui(win)
        self._refresh()

    def _build_ui(self, win):
        # ── header ────────────────────────────────────────────
        hdr = tk.Frame(win, bg=DARK['panel'], pady=8)
        hdr.pack(fill='x')

        tk.Label(hdr, text="🎄  Santa's To-Do List",
                 font=('Arial', 14, 'bold'), bg=DARK['panel'],
                 fg=DARK['accent']).pack(side='left', padx=12)

        # Google Tasks connect button
        self._gtbtn_var = tk.StringVar()
        self._update_gtbtn_label()
        self._gtbtn = tk.Button(hdr, textvariable=self._gtbtn_var,
                                font=('Arial', 8), bg=DARK['card'],
                                fg=DARK['text'], relief='flat', padx=8, pady=4,
                                cursor='hand2', command=self._toggle_google)
        self._gtbtn.pack(side='right', padx=8)

        self._sync_label = tk.Label(hdr, text='', font=('Arial', 8),
                                    bg=DARK['panel'], fg=DARK['green'])
        self._sync_label.pack(side='right')

        # ── add task bar ──────────────────────────────────────
        add_frame = tk.Frame(win, bg=DARK['bg'], pady=6)
        add_frame.pack(fill='x', padx=10)

        self._entry = tk.Entry(add_frame, font=('Arial', 11),
                               bg=DARK['card'], fg=DARK['text'],
                               insertbackground=DARK['text'],
                               relief='flat', bd=0)
        self._entry.pack(side='left', fill='x', expand=True,
                         ipady=7, ipadx=6)
        self._entry.insert(0, 'Add a new task…')
        self._entry.configure(fg=DARK['subtext'])
        self._entry.bind('<FocusIn>',  self._entry_focus_in)
        self._entry.bind('<FocusOut>', self._entry_focus_out)
        self._entry.bind('<Return>',   lambda e: self._quick_add())

        tk.Button(add_frame, text='＋ Add',
                  font=('Arial', 10, 'bold'), bg='#238636', fg='white',
                  relief='flat', padx=10, pady=7,
                  cursor='hand2', command=self._quick_add).pack(side='left', padx=(6, 0))

        tk.Button(add_frame, text='📋 Detailed',
                  font=('Arial', 10), bg=DARK['card'], fg=DARK['text'],
                  relief='flat', padx=8, pady=7,
                  cursor='hand2', command=self._detailed_add).pack(side='left', padx=4)

        # ── filter tabs ───────────────────────────────────────
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

        # ── sync bar ──────────────────────────────────────────
        sync_bar = tk.Frame(win, bg=DARK['bg'])
        sync_bar.pack(fill='x', padx=10, pady=(0, 4))
        self._status_var = tk.StringVar(value='')
        tk.Label(sync_bar, textvariable=self._status_var,
                 font=('Arial', 8), bg=DARK['bg'],
                 fg=DARK['subtext']).pack(side='left')
        tk.Button(sync_bar, text='↻ Sync Google',
                  font=('Arial', 8), bg=DARK['card'], fg=DARK['accent'],
                  relief='flat', padx=8, pady=3, cursor='hand2',
                  command=self._do_sync).pack(side='right')

        # ── task list ─────────────────────────────────────────
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

        # mousewheel scroll
        self._canvas.bind_all('<MouseWheel>',
            lambda e: self._canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        # ── bottom stats ──────────────────────────────────────
        self._stats_var = tk.StringVar(value='')
        tk.Label(win, textvariable=self._stats_var,
                 font=('Arial', 9), bg=DARK['panel'],
                 fg=DARK['subtext'], pady=6).pack(fill='x')

    def _entry_focus_in(self, e):
        if self._entry.get() == 'Add a new task…':
            self._entry.delete(0, 'end')
            self._entry.configure(fg=DARK['text'])

    def _entry_focus_out(self, e):
        if not self._entry.get():
            self._entry.insert(0, 'Add a new task…')
            self._entry.configure(fg=DARK['subtext'])

    # ── filter / tab ──────────────────────────────────────────
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

    # ── refresh list ──────────────────────────────────────────
    def _refresh(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

        tasks = self.local.load()
        if self._filter == 'active':
            tasks = [t for t in tasks if not t['done']]
        elif self._filter == 'done':
            tasks = [t for t in tasks if t['done']]

        # sort: undone first, then by created
        tasks.sort(key=lambda t: (t['done'], t.get('created', '')))

        if not tasks:
            tk.Label(self._list_frame,
                     text="No tasks yet — add one above! 🎅",
                     font=('Arial', 11), bg=DARK['bg'],
                     fg=DARK['subtext'], pady=40).pack()
        else:
            for task in tasks:
                self._task_card(task)

        # stats
        all_t = self.local.load()
        done  = sum(1 for t in all_t if t['done'])
        total = len(all_t)
        self._stats_var.set(f"  {done} done  /  {total - done} active  /  {total} total")

    def _task_card(self, task):
        card = tk.Frame(self._list_frame, bg=DARK['card'],
                        padx=10, pady=8, cursor='hand2')
        card.pack(fill='x', pady=3, padx=2)

        # checkbox
        done_var = tk.BooleanVar(value=task['done'])
        cb = tk.Checkbutton(card, variable=done_var,
                            bg=DARK['card'], activebackground=DARK['card'],
                            selectcolor=DARK['panel'],
                            command=lambda tid=task['id'], v=done_var:
                                self._toggle(tid, v))
        cb.pack(side='left')

        # text area
        txt_frame = tk.Frame(card, bg=DARK['card'])
        txt_frame.pack(side='left', fill='x', expand=True, padx=6)

        title_color = DARK['done_fg'] if task['done'] else DARK['text']
        title_font  = ('Arial', 10, 'overstrike') if task['done'] else ('Arial', 10, 'bold')
        tk.Label(txt_frame, text=task['title'],
                 font=title_font, bg=DARK['card'],
                 fg=title_color, anchor='w').pack(fill='x')

        meta_parts = []
        if task.get('note'):
            meta_parts.append(f"📝 {task['note'][:50]}")
        if task.get('due'):
            meta_parts.append(f"📅 Due: {task['due']}")
        if task.get('reminder'):
            try:
                dt = datetime.fromisoformat(task['reminder'])
                meta_parts.append(f"⏰ {dt.strftime('%m/%d %H:%M')}")
            except Exception:
                pass
        if task.get('google_id'):
            meta_parts.append("🔗 Google")

        if meta_parts:
            tk.Label(txt_frame, text='  '.join(meta_parts),
                     font=('Arial', 8), bg=DARK['card'],
                     fg=DARK['subtext'], anchor='w').pack(fill='x')

        # action buttons
        btn_frame = tk.Frame(card, bg=DARK['card'])
        btn_frame.pack(side='right')

        tk.Button(btn_frame, text='✏',
                  font=('Arial', 9), bg=DARK['panel'], fg=DARK['accent'],
                  relief='flat', padx=5, pady=2, cursor='hand2',
                  command=lambda t=task: self._edit_task(t)).pack(side='left', padx=2)
        tk.Button(btn_frame, text='🗑',
                  font=('Arial', 9), bg=DARK['panel'], fg=DARK['red'],
                  relief='flat', padx=5, pady=2, cursor='hand2',
                  command=lambda t=task: self._delete_task(t)).pack(side='left')

    # ── actions ───────────────────────────────────────────────
    def _toggle(self, task_id, var):
        self.local.toggle(task_id)
        if self.google.is_connected():
            threading.Thread(
                target=self._push_one, args=(task_id,), daemon=True).start()
        self._refresh()

    def _push_one(self, task_id):
        tasks = self.local.load()
        for t in tasks:
            if t['id'] == task_id:
                gid = self.google.push_task(t)
                if gid:
                    self.local.update(task_id, google_id=gid, synced=True)
                break

    def _quick_add(self):
        title = self._entry.get().strip()
        if not title or title == 'Add a new task…':
            return
        task = self.local.add(title)
        self._entry.delete(0, 'end')
        self._entry_focus_out(None)
        if self.google.is_connected():
            threading.Thread(
                target=self._push_one, args=(task['id'],), daemon=True).start()
        self._refresh()

    def _detailed_add(self):
        self._task_dialog(None)

    def _edit_task(self, task):
        self._task_dialog(task)

    def _delete_task(self, task):
        if not messagebox.askyesno("Delete", f'Delete "{task["title"]}"?',
                                   parent=self._win):
            return
        if self.google.is_connected() and task.get('google_id'):
            threading.Thread(
                target=self.google.delete_task,
                args=(task['google_id'],), daemon=True).start()
        self.local.delete(task['id'])
        self._refresh()

    def _task_dialog(self, existing=None):
        dlg = tk.Toplevel(self._win)
        dlg.title("✏️ Edit Task" if existing else "➕ New Task")
        dlg.geometry("400x400")
        dlg.resizable(False, False)
        dlg.attributes('-topmost', True)
        dlg.configure(bg=DARK['bg'])

        def lbl(t):
            tk.Label(dlg, text=t, font=('Arial', 9, 'bold'),
                     bg=DARK['bg'], fg=DARK['subtext']).pack(anchor='w', padx=16, pady=(10, 1))

        def entry(var=None, **kw):
            e = tk.Entry(dlg, font=('Arial', 10), bg=DARK['card'],
                         fg=DARK['text'], insertbackground=DARK['text'],
                         relief='flat', bd=0, textvariable=var, **kw)
            e.pack(fill='x', padx=16, ipady=6, ipadx=4)
            return e

        lbl("Title *")
        title_var = tk.StringVar(value=existing['title'] if existing else '')
        entry(title_var)

        lbl("Note / Description")
        note_var = tk.StringVar(value=existing.get('note', '') if existing else '')
        entry(note_var)

        lbl("Due Date (YYYY-MM-DD)  — optional")
        due_var = tk.StringVar(value=existing.get('due', '') if existing else '')
        entry(due_var)

        lbl("Reminder (YYYY-MM-DD HH:MM)  — optional")
        rem_var = tk.StringVar(value='')
        if existing and existing.get('reminder'):
            try:
                dt = datetime.fromisoformat(existing['reminder'])
                rem_var.set(dt.strftime('%Y-%m-%d %H:%M'))
            except Exception:
                pass
        entry(rem_var)

        # quick reminder shortcuts
        shortcuts = tk.Frame(dlg, bg=DARK['bg'])
        shortcuts.pack(fill='x', padx=16, pady=(4, 0))
        tk.Label(shortcuts, text="Quick:", font=('Arial', 8),
                 bg=DARK['bg'], fg=DARK['subtext']).pack(side='left')
        for label, delta in [('30 min', timedelta(minutes=30)),
                              ('1 hr',  timedelta(hours=1)),
                              ('1 day', timedelta(days=1))]:
            tk.Button(shortcuts, text=label, font=('Arial', 8),
                      bg=DARK['card'], fg=DARK['accent'], relief='flat',
                      padx=6, pady=2, cursor='hand2',
                      command=lambda d=delta, v=rem_var:
                          v.set((datetime.now() + d).strftime('%Y-%m-%d %H:%M'))
                      ).pack(side='left', padx=3)

        def save():
            title = title_var.get().strip()
            if not title:
                messagebox.showwarning("Required", "Title can't be empty", parent=dlg)
                return
            note = note_var.get().strip()
            due  = due_var.get().strip() or None
            # parse reminder
            rem_str = rem_var.get().strip()
            reminder = None
            if rem_str:
                try:
                    dt = datetime.strptime(rem_str, '%Y-%m-%d %H:%M')
                    reminder = dt.isoformat()
                except Exception:
                    messagebox.showwarning("Bad format",
                        "Reminder must be YYYY-MM-DD HH:MM", parent=dlg)
                    return

            if existing:
                self.local.update(existing['id'], title=title, note=note,
                                  due=due, reminder=reminder)
                if self.google.is_connected():
                    threading.Thread(
                        target=self._push_one, args=(existing['id'],),
                        daemon=True).start()
            else:
                task = self.local.add(title, note, due, reminder)
                if self.google.is_connected():
                    threading.Thread(
                        target=self._push_one, args=(task['id'],),
                        daemon=True).start()

            dlg.destroy()
            self._refresh()

        tk.Button(dlg, text="💾 Save Task", command=save,
                  font=('Arial', 11, 'bold'), bg='#238636', fg='white',
                  relief='flat', padx=25, pady=8, cursor='hand2').pack(pady=18)

    # ── Google Tasks toggle ───────────────────────────────────
    def _update_gtbtn_label(self):
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
                self._update_gtbtn_label()
                self._set_status("Disconnected from Google Tasks")
        elif self.google.is_configured():
            self._set_status("Connecting…")
            def connect():
                ok, msg = self.google.connect()
                self._win.after(0, lambda: self._after_connect(ok, msg))
            threading.Thread(target=connect, daemon=True).start()
        else:
            self._show_google_setup()

    def _after_connect(self, ok, msg):
        self._update_gtbtn_label()
        if ok:
            self._set_status("✅ " + msg)
            self._do_sync()
        else:
            self._set_status("❌ " + msg[:60])

    def _do_sync(self):
        if not self.google.is_connected():
            self._set_status("Not connected to Google Tasks")
            return
        self._set_status("Syncing…")
        def sync():
            # push local unsync'd tasks
            tasks = self.local.load()
            pushed = 0
            for t in tasks:
                if not t.get('synced'):
                    gid = self.google.push_task(t)
                    if gid:
                        self.local.update(t['id'], google_id=gid, synced=True)
                        pushed += 1
            # pull new tasks from Google
            new = self.google.sync_from_google(self.local)
            self._win.after(0, lambda: self._after_sync(pushed, new))
        threading.Thread(target=sync, daemon=True).start()

    def _after_sync(self, pushed, pulled):
        self._set_status(f"↑ {pushed} pushed  ↓ {pulled} pulled  — {datetime.now().strftime('%H:%M')}")
        self._refresh()

    def _set_status(self, msg):
        if self._status_var:
            self._status_var.set(msg)

    def _show_google_setup(self):
        dlg = tk.Toplevel(self._win)
        dlg.title("⚙️ Google Tasks Setup")
        dlg.geometry("480x380")
        dlg.resizable(False, False)
        dlg.attributes('-topmost', True)
        dlg.configure(bg=DARK['bg'])

        tk.Label(dlg, text="🔗  Connect Google Tasks",
                 font=('Arial', 13, 'bold'), bg=DARK['bg'],
                 fg=DARK['accent']).pack(pady=15)

        instructions = (
            "To sync with Google Tasks:\n\n"
            "1. Go to console.cloud.google.com\n"
            "2. Create a project (or pick one)\n"
            "3. Enable 'Tasks API'\n"
            "4. Credentials → Create → OAuth 2.0 Client ID\n"
            "   • Application type: Desktop app\n"
            "5. Download the JSON → rename to\n"
            f"   credentials.json\n"
            f"   → save it to:\n"
            f"   {CREDS_FILE}\n\n"
            "Then click 'I've done this' below."
        )

        txt = tk.Text(dlg, font=('Arial', 9), bg=DARK['card'], fg=DARK['text'],
                      relief='flat', padx=10, pady=10, wrap='word',
                      height=12, state='normal')
        txt.insert('1.0', instructions)
        txt.configure(state='disabled')
        txt.pack(fill='both', expand=True, padx=16, pady=5)

        btn_row = tk.Frame(dlg, bg=DARK['bg'])
        btn_row.pack(pady=10)

        def open_console():
            webbrowser.open('https://console.cloud.google.com/apis/credentials')
        tk.Button(btn_row, text="Open Google Console",
                  font=('Arial', 10), bg=DARK['card'], fg=DARK['accent'],
                  relief='flat', padx=12, pady=6, cursor='hand2',
                  command=open_console).pack(side='left', padx=6)

        def done():
            dlg.destroy()
            self._toggle_google()
        tk.Button(btn_row, text="I've done this →",
                  font=('Arial', 10, 'bold'), bg='#238636', fg='white',
                  relief='flat', padx=12, pady=6, cursor='hand2',
                  command=done).pack(side='left', padx=6)
