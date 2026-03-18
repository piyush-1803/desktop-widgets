from __future__ import annotations

import json
import math
import os
import sys
import time
import winsound
from pathlib import Path

import tkinter as tk
import win32con
import win32gui
import win32api

BASE_DIR   = Path(__file__).resolve().parent
TASKS_PATH = BASE_DIR / "tasks.json"
PID_PATH   = BASE_DIR / "task_timer.pid"
CHROMA     = "#00FF01"

def open_main_settings():
    import subprocess, sys
    from pathlib import Path
    base = Path(__file__).resolve().parent
    s = base / "settings.exe"
    if s.exists():
        subprocess.Popen([str(s)], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        s = base / "settings.py"
        if s.exists():
            subprocess.Popen([sys.executable, str(s)],
                             creationflags=subprocess.CREATE_NO_WINDOW)


# Default size - bigger
W, H = 320, 360

DEFAULT_TASKS = [
    {"name": "Focus",     "minutes": 25, "emoji": "🍅"},
    {"name": "Break",     "minutes": 5,  "emoji": "☕"},
    {"name": "Exercise",  "minutes": 30, "emoji": "🏃"},
    {"name": "Deep Work", "minutes": 60, "emoji": "💡"},
]

# Neon blue palette
NEON      = "#00B4FF"
NEON2     = "#38CFFF"
NEON_DIM  = "#003D5C"
DONE_COL  = "#00FFB2"
BG        = "#0A0C10"
CARD      = "#0F1218"
DIM       = "#1A1E28"
TEXT      = "#E8EAED"
MUTED     = "#4A5060"
BORDER    = "#1E2330"

TICKS     = 90

def load_tasks():
    try:
        d = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
        if isinstance(d, list) and d: return d
    except Exception: pass
    TASKS_PATH.write_text(json.dumps(DEFAULT_TASKS, indent=2), encoding="utf-8")
    return list(DEFAULT_TASKS)

def save_tasks(t):
    TASKS_PATH.write_text(json.dumps(t, indent=2), encoding="utf-8")

def find_workerw():
    progman = win32gui.FindWindow("Progman", None)
    win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
    ww = None
    def cb(hwnd, _):
        nonlocal ww
        if win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None):
            ww = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
        return True
    win32gui.EnumWindows(cb, 0)
    return ww

def embed(hwnd, ww, x, y, w, h):
    s = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    s |= win32con.WS_CHILD; s &= ~win32con.WS_POPUP
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, s)
    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    ex |= win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0,255,1), 255,
                                        win32con.LWA_COLORKEY | win32con.LWA_ALPHA)
    win32gui.SetParent(hwnd, ww)
    win32gui.SetWindowPos(hwnd, 0, x, y, w, h,
                          win32con.SWP_NOZORDER|win32con.SWP_SHOWWINDOW|win32con.SWP_FRAMECHANGED)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.UpdateWindow(hwnd)

# ── Alert dialog ──────────────────────────────────────────────────────────────
class AlertDialog(tk.Toplevel):
    def __init__(self, parent, task_name):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        outer = tk.Frame(self, bg=NEON, padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        f = tk.Frame(outer, bg=BG)
        f.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Frame(f, bg=BG, height=20).pack()
        tk.Label(f, text="✅", font=("Segoe UI",32), bg=BG).pack()
        tk.Label(f, text="Task Complete!", fg=TEXT, bg=BG,
                 font=("Segoe UI Semibold",14,"bold")).pack(pady=(10,4))
        tk.Label(f, text=f'"{task_name}"', fg=NEON, bg=BG,
                 font=("Segoe UI",11)).pack()
        tk.Label(f, text="Press  ❯  for next task", fg=MUTED,
                 bg=BG, font=("Segoe UI",9)).pack(pady=(8,16))
        tk.Button(f, text="Got it!", bg=NEON, fg="#000000", relief="flat",
                  font=("Segoe UI",10,"bold"), padx=28, pady=9,
                  cursor="hand2", command=self.destroy,
                  activebackground=NEON2).pack(pady=(0,22))
        self.update_idletasks()
        sw,sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw-self.winfo_width())//2}+{(sh-self.winfo_height())//2}")
        f.bind("<ButtonPress-1>", lambda e: setattr(self,'_dx',e.x) or setattr(self,'_dy',e.y))
        f.bind("<B1-Motion>", lambda e: self.geometry(
            f"+{self.winfo_x()+e.x-self._dx}+{self.winfo_y()+e.y-self._dy}"))
    def show(self): self.grab_set(); self.wait_window()

# ── Task dialog ───────────────────────────────────────────────────────────────
class TaskDialog(tk.Toplevel):
    def __init__(self, parent, title, name="", emoji="⏱", minutes="25"):
        super().__init__(parent)
        self.result = None
        self.overrideredirect(True)
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        outer = tk.Frame(self, bg=NEON, padx=1, pady=1); outer.pack(fill="both",expand=True)
        inn = tk.Frame(outer, bg=BG); inn.pack(fill="both",expand=True,padx=1,pady=1)
        hdr = tk.Frame(inn, bg=CARD, height=48); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text=title, fg=TEXT, bg=CARD,
                 font=("Segoe UI Semibold",13,"bold")).place(x=18,rely=0.5,anchor="w")
        tk.Button(hdr, text="✕", fg=MUTED, bg=CARD, relief="flat",
                  font=("Segoe UI",11), cursor="hand2", command=self.destroy,
                  activebackground=CARD).place(relx=1.0,x=-14,rely=0.5,anchor="e")
        hdr.bind("<ButtonPress-1>", lambda e: setattr(self,'_dx',e.x) or setattr(self,'_dy',e.y))
        hdr.bind("<B1-Motion>", lambda e: self.geometry(
            f"+{self.winfo_x()+e.x-self._dx}+{self.winfo_y()+e.y-self._dy}"))
        body = tk.Frame(inn, bg=BG); body.pack(padx=20,pady=14,fill="x")
        self._vars = []
        for lbl,val in [("Task Name",name),("Emoji",emoji),("Minutes",minutes)]:
            tk.Label(body,text=lbl,fg=MUTED,bg=BG,
                     font=("Segoe UI",9)).pack(anchor="w",pady=(10,3))
            v = tk.StringVar(value=val)
            e = tk.Entry(body,textvariable=v,bg=DIM,fg=TEXT,
                         insertbackground=TEXT,relief="flat",
                         font=("Segoe UI",11),highlightbackground=BORDER,
                         highlightthickness=1)
            e.pack(fill="x",ipady=7); self._vars.append(v)
        btn_row = tk.Frame(inn,bg=BG); btn_row.pack(fill="x",padx=20,pady=(6,18))
        tk.Button(btn_row,text="Cancel",bg=DIM,fg=MUTED,relief="flat",
                  font=("Segoe UI",10),padx=18,pady=7,cursor="hand2",
                  command=self.destroy,activebackground=DIM).pack(side="right",padx=(8,0))
        tk.Button(btn_row,text="Save",bg=NEON,fg="#000000",relief="flat",
                  font=("Segoe UI",10,"bold"),padx=18,pady=7,cursor="hand2",
                  command=self._save,activebackground=NEON2).pack(side="right")
        self.update_idletasks()
        sw,sh = self.winfo_screenwidth(),self.winfo_screenheight()
        self.geometry(f"+{(sw-self.winfo_width())//2}+{(sh-self.winfo_height())//2}")
    def _save(self): self.result=[v.get() for v in self._vars]; self.destroy()
    def ask(self): self.grab_set(); self.wait_window(); return self.result

# ── Main widget ───────────────────────────────────────────────────────────────
class TaskTimerWidget:
    MIN_W, MIN_H = 240, 270
    RESIZE_GRIP  = 14   # px corner grip area

    def __init__(self):
        self.tasks       = load_tasks()
        self.idx         = 0
        self.running     = False
        self.done        = False
        self._remaining  = 0
        self._total      = 0
        self._edit_mode  = False
        self.w           = W
        self.h           = H
        self._drag_x = self._drag_y = 0
        self._resize_mode = False

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.w}x{self.h}+60+180")
        self.root.configure(bg=CHROMA)
        self.root.attributes("-transparentcolor", CHROMA)
        self.root.minsize(self.MIN_W, self.MIN_H)

        self.cv = tk.Canvas(self.root, width=self.w, height=self.h,
                            bg=CHROMA, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        # Inline name editor
        self._name_var = tk.StringVar()
        self._name_entry = tk.Entry(
            self.root, textvariable=self._name_var,
            bg=DIM, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=("Segoe UI Semibold",12,"bold"),
            justify="center", highlightbackground=NEON,
            highlightthickness=1, bd=0)
        self._name_entry.bind("<Return>",   self._commit_name)
        self._name_entry.bind("<Escape>",   self._cancel_edit)
        self._name_entry.bind("<FocusOut>", self._commit_name)

        if self.tasks: self._load_task()
        self._draw()
        self._bind()

        self.root.update()
        ww = find_workerw()
        if ww: embed(self.root.winfo_id(), ww, 60, 180, self.w, self.h)
        PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
        self._tick()
        self.root.mainloop()

    # ── layout helpers ────────────────────────────────────────────────────────
    @property
    def cx(self): return self.w // 2
    @property
    def cy(self): return int(self.h * 0.50)
    @property
    def r_ticks(self): return int(min(self.w, self.h) * 0.30)

    def _load_task(self):
        t = self.tasks[self.idx]
        self._total     = t["minutes"] * 60
        self._remaining = self._total
        self.running = self.done = self._edit_mode = False

    def _cur(self): return self.tasks[self.idx] if self.tasks else None

    # ── draw ─────────────────────────────────────────────────────────────────
    def _draw(self):
        cv = self.cv
        cv.config(width=self.w, height=self.h)
        cv.delete("all")
        self._name_entry.place_forget()

        cx, cy, rt = self.cx, self.cy, self.r_ticks
        col = DONE_COL if self.done else NEON

        # Card background
        self._rrect(5, 5, self.w-5, self.h-5, r=24,
                    fill=CARD, outline=BORDER, width=1)

        # Resize grip hint (bottom-right)
        for i in range(3):
            o = 6 + i*5
            cv.create_line(self.w-5, self.h-5-o, self.w-5-o, self.h-5,
                           fill=MUTED, width=1)

        # ── empty state ──
        if not self.tasks:
            cv.create_text(cx, cy-16, text="No tasks yet", fill=MUTED,
                           font=("Segoe UI",13))
            self._pill(cx, cy+28, 130, 36, NEON, "+ Add Task",
                       "add_empty", fg="#000000")
            cv.create_text(self.w-16, 24, text="✕", fill=MUTED,
                           font=("Segoe UI",10), tags="close_btn")
            cv.tag_bind("add_empty", "<Button-1>", lambda e: self._add_task())
            cv.tag_bind("close_btn", "<Button-1>", lambda e: self._quit())
            return

        t = self._cur()

        # ── header ──
        cv.create_text(cx-46, 28, text=t.get("emoji","⏱"),
                       font=("Segoe UI",13), fill=TEXT)

        if not self._edit_mode:
            name = t["name"][:16]
            cv.create_text(cx-28, 28, text=name, fill=TEXT,
                           font=("Segoe UI Semibold",12,"bold"),
                           anchor="w", tags="title_click")
            cv.tag_bind("title_click", "<Button-1>", lambda e: self._start_edit())

        # Trash + Close
        cv.create_text(self.w-60, 28, text="⚙", fill=MUTED,
                       font=("Segoe UI",10), tags="main_settings")
        cv.create_text(self.w-38, 28, text="🗑", fill=MUTED,
                       font=("Segoe UI",11), tags="trash_btn")
        cv.create_text(self.w-16, 28, text="✕", fill=MUTED,
                       font=("Segoe UI",10), tags="close_btn")

        # ── tick ring ──
        ratio     = self._remaining / self._total if self._total else 0
        lit_ticks = int(TICKS * ratio)

        for i in range(TICKS):
            angle_deg = 90 - (360 / TICKS) * i
            angle_rad = math.radians(angle_deg)
            tick_len  = 11 if i % 5 == 0 else 6
            r_out     = rt
            r_inn     = rt - tick_len

            x1 = cx + r_out * math.cos(angle_rad)
            y1 = cy - r_out * math.sin(angle_rad)
            x2 = cx + r_inn * math.cos(angle_rad)
            y2 = cy - r_inn * math.sin(angle_rad)

            if i < lit_ticks:
                # Glow gradient: brighter ticks near the leading edge
                frac = i / max(lit_ticks, 1)
                tick_col = NEON2 if frac > 0.85 else NEON if frac > 0.4 else NEON_DIM
                tick_col = DONE_COL if self.done else tick_col
                width = 2 if i % 5 == 0 else 1
            else:
                tick_col = DIM
                width = 1

            cv.create_line(x1,y1,x2,y2, fill=tick_col, width=width, capstyle="round")

        # Inner mask
        ir = rt - 16
        cv.create_oval(cx-ir,cy-ir,cx+ir,cy+ir, fill=CARD, outline="")

        # Neon glow ring (subtle)
        cv.create_oval(cx-ir-1,cy-ir-1,cx+ir+1,cy+ir+1,
                       outline=NEON_DIM, width=1)

        # ── time ──
        mins = self._remaining // 60
        secs = self._remaining % 60
        time_size = max(18, int(rt * 0.38))
        cv.create_text(cx, cy-8,
                       text=f"{mins:02d}:{secs:02d}",
                       fill=col if self.done else TEXT,
                       font=("Segoe UI Semibold", time_size, "bold"))

        sublabel = "DONE ✓" if self.done else (
            "RUNNING" if self.running else
            "PAUSED"  if self._remaining < self._total else
            t["name"].upper()[:10])
        cv.create_text(cx, cy+int(rt*0.32), text=sublabel,
                       fill=col if self.done else MUTED,
                       font=("Segoe UI", 8))

        # ── nav arrows ──
        cv.create_text(18, cy, text="❮", fill=MUTED,
                       font=("Segoe UI",16), tags="prev")
        cv.create_text(self.w-18, cy, text="❯", fill=MUTED,
                       font=("Segoe UI",16), tags="next")

        # ── play/pause pill ──
        sp_text = "⏸  Pause" if self.running else ("↺  Reset" if self.done else "▶  Start")
        sp_col  = NEON if not self.done else DONE_COL
        self._pill(cx, self.h-46, 130, 34, DIM, sp_text,
                   "sp_btn", fg=sp_col, font=("Segoe UI",10,"bold"))

        # ── dot indicators ──
        n  = min(len(self.tasks), 9)
        x0 = cx - (n-1)*9
        for i in range(n):
            dc = col if i == self.idx % n else DIM
            cv.create_oval(x0+i*18-4, self.h-16, x0+i*18+4, self.h-8,
                           fill=dc, outline="")

        # ── right click hint ──
        cv.create_text(cx, self.h-28, text="right click to add task",
                       fill="#2A2A3A", font=("Segoe UI",7))

        # ── bindings ──
        cv.tag_bind("prev",          "<Button-1>", lambda e: self._prev())
        cv.tag_bind("next",          "<Button-1>", lambda e: self._next())
        cv.tag_bind("sp_btn",        "<Button-1>", lambda e: self._toggle())
        cv.tag_bind("trash_btn",     "<Button-1>", lambda e: self._delete_task())
        cv.tag_bind("close_btn",     "<Button-1>", lambda e: self._quit())
        cv.tag_bind("main_settings", "<Button-1>", lambda e: self._open_settings())

    def _pill(self, cx, cy, w, h, bg, text, tag, fg="#FFF", font=("Segoe UI",10,"bold")):
        r=h//2; x0=cx-w//2; y0=cy-h//2; x1=cx+w//2; y1=cy+h//2
        self.cv.create_arc(x0,y0,x0+h,y1, start=90, extent=180, fill=bg, outline=bg)
        self.cv.create_arc(x1-h,y0,x1,y1, start=270, extent=180, fill=bg, outline=bg)
        self.cv.create_rectangle(x0+r,y0,x1-r,y1, fill=bg, outline=bg)
        self.cv.create_text(cx,cy, text=text, fill=fg, font=font, tags=tag)

    def _rrect(self, x1,y1,x2,y2,r=20,**kw):
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
             x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        self.cv.create_polygon(pts, smooth=True, **kw)

    # ── inline edit ───────────────────────────────────────────────────────────
    def _start_edit(self):
        t = self._cur()
        self._name_var.set(t["name"])
        self._edit_mode = True
        self._name_entry.place(x=self.cx-70, y=16, width=140, height=26)
        self._name_entry.focus_set()
        self._name_entry.select_range(0, "end")

    def _commit_name(self, e=None):
        name = self._name_var.get().strip()
        if name and self.tasks:
            self.tasks[self.idx]["name"] = name
            save_tasks(self.tasks)
        self._edit_mode = False
        self._draw()

    def _cancel_edit(self, e=None):
        self._edit_mode = False; self._draw()

    # ── task ops ─────────────────────────────────────────────────────────────
    def _add_task(self):
        dlg = TaskDialog(self.root, "+ New Task")
        res = dlg.ask()
        if not res: return
        try:
            self.tasks.append({"name": res[0].strip() or "New Task",
                                "emoji": res[1].strip() or "⏱",
                                "minutes": max(1,int(res[2]))})
            save_tasks(self.tasks)
            self.idx = len(self.tasks)-1
            self._load_task(); self._draw()
        except Exception: pass

    def _delete_task(self):
        if not self.tasks: return
        self.tasks.pop(self.idx)
        save_tasks(self.tasks)
        if self.tasks:
            self.idx = min(self.idx, len(self.tasks)-1)
            self._load_task()
        self._draw()

    def _toggle(self):
        if self.done: self._load_task(); self._draw(); return
        self.running = not self.running; self._draw()

    def _prev(self):
        if not self.tasks: return
        self.idx = (self.idx-1) % len(self.tasks)
        self._load_task(); self._draw()

    def _next(self):
        if not self.tasks: return
        self.idx = (self.idx+1) % len(self.tasks)
        self._load_task(); self._draw()

    def _alert(self):
        try:
            for _ in range(3): winsound.Beep(880,250); time.sleep(0.12)
        except Exception: pass
        AlertDialog(self.root, self._cur()["name"]).show()

    def _open_settings(self):
        s = BASE_DIR / "settings.exe"
        if s.exists():
            subprocess.Popen([str(s)], cwd=str(BASE_DIR))
        else:
            s2 = BASE_DIR / "settings.py"
            if s2.exists():
                subprocess.Popen([sys.executable, str(s2)], cwd=str(BASE_DIR))

    def _quit(self):
        try: PID_PATH.unlink(missing_ok=True)
        except Exception: pass
        self.root.destroy(); sys.exit(0)

    # ── drag + resize ─────────────────────────────────────────────────────────
    def _bind(self):
        self.cv.bind("<ButtonPress-1>",   self._press)
        self.cv.bind("<B1-Motion>",        self._motion)
        self.cv.bind("<ButtonRelease-1>",  self._release)
        self.cv.bind("<Button-3>",         lambda e: self._add_task())
        self.cv.bind("<Motion>",           self._hover_cursor)

    def _in_grip(self, x, y):
        g = self.RESIZE_GRIP
        return x > self.w - g and y > self.h - g

    def _hover_cursor(self, e):
        self.cv.config(cursor="size_nw_se" if self._in_grip(e.x, e.y) else "")

    def _press(self, e):
        self._resize_mode = self._in_grip(e.x, e.y)
        self._drag_x, self._drag_y = e.x, e.y
        self._start_w, self._start_h = self.w, self.h

    def _motion(self, e):
        if self._resize_mode:
            nw = max(self.MIN_W, self._start_w + e.x - self._drag_x)
            nh = max(self.MIN_H, self._start_h + e.y - self._drag_y)
            self.w, self.h = int(nw), int(nh)
            self.root.geometry(f"{self.w}x{self.h}")
            self._draw()
        else:
            x = self.root.winfo_x() + e.x - self._drag_x
            y = self.root.winfo_y() + e.y - self._drag_y
            self.root.geometry(f"{self.w}x{self.h}+{x}+{y}")

    def _release(self, e):
        self._resize_mode = False

    # ── tick ─────────────────────────────────────────────────────────────────
    def _tick(self):
        if self.running and not self.done:
            if self._remaining > 0: self._remaining -= 1
            if self._remaining == 0:
                self.running=False; self.done=True
                self._draw()
                self.root.after(200, self._alert)
                self.root.after(300, self._tick)
                return
        self._draw()
        self.root.after(1000, self._tick)


if __name__ == "__main__":
    TaskTimerWidget()
