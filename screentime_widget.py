from __future__ import annotations
import json, os, sys, time, threading
from pathlib import Path
from datetime import datetime, date
import tkinter as tk
import win32con, win32gui, win32api
import psutil

BASE_DIR   = Path(__file__).resolve().parent
PID_PATH   = BASE_DIR / "screentime_widget.pid"
DATA_PATH  = BASE_DIR / "screentime_data.json"
CHROMA     = "#00FF03"

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

W, H       = 260, 140

# ── Colours ───────────────────────────────────────────────────────────────────
BG      = "#0F1117"
CARD    = "#161A24"
ACCENT  = "#7C6AF7"
ACCENT2 = "#A78BFA"
GREEN   = "#34D399"
YELLOW  = "#FBBF24"
RED     = "#F87171"
TEXT    = "#E8EAED"
MUTED   = "#4A5068"
BORDER  = "#1E2235"

# Top apps to track (add more if you want)
TRACKED = [
    "chrome","firefox","msedge","opera","brave",
    "code","cursor","notepad","notepad++","sublime_text",
    "explorer","winword","excel","powerpnt",
    "discord","slack","teams","zoom","telegram",
    "spotify","vlc","mpc-hc","mpv",
    "python","pythonw","cmd","powershell","windowsterminal",
    "photoshop","illustrator","figma",
]

def load_data():
    try:
        d = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if d.get("date") != str(date.today()):
            # New day - reset
            return {"date": str(date.today()), "total": 0, "apps": {}, "hourly": [0]*24}
        return d
    except Exception:
        return {"date": str(date.today()), "total": 0, "apps": {}, "hourly": [0]*24}

def save_data(d):
    DATA_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")

def get_active_app():
    try:
        import win32process, win32gui as wg
        hwnd = wg.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return proc.name().lower().replace(".exe","")
    except Exception:
        return None

def fmt_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0: return f"{h}h {m}m"
    if m > 0: return f"{m}m"
    return f"{seconds}s"

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
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0,255,3), 255,
        win32con.LWA_COLORKEY | win32con.LWA_ALPHA)
    win32gui.SetParent(hwnd, ww)
    win32gui.SetWindowPos(hwnd, 0, x, y, w, h,
        win32con.SWP_NOZORDER|win32con.SWP_SHOWWINDOW|win32con.SWP_FRAMECHANGED)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.UpdateWindow(hwnd)

class ScreenTimeWidget:
    def __init__(self):
        self.data      = load_data()
        self.view      = "main"   # main | apps
        self._dx = self._dy = 0
        self._last_tick = time.time()

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{W}x{H}+700+60")
        self.root.configure(bg=CHROMA)
        self.root.attributes("-transparentcolor", CHROMA)

        self.cv = tk.Canvas(self.root, width=W, height=H,
                            bg=CHROMA, highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<ButtonPress-1>",  self._press)
        self.cv.bind("<B1-Motion>",      self._drag)
        self.cv.bind("<Button-3>",       self._toggle_view)

        self._draw()
        self.root.update()
        ww = find_workerw()
        if ww: embed(self.root.winfo_id(), ww, 700, 60, W, H)
        PID_PATH.write_text(str(os.getpid()), encoding="utf-8")

        # Background tracker thread
        threading.Thread(target=self._tracker, daemon=True).start()
        self._refresh()
        self.root.mainloop()

    # ── tracker runs every second in background ───────────────────────────────
    def _tracker(self):
        while True:
            try:
                now   = date.today()
                # New day reset
                if self.data.get("date") != str(now):
                    self.data = {"date": str(now), "total": 0,
                                 "apps": {}, "hourly": [0]*24}

                self.data["total"] = self.data.get("total", 0) + 1
                hour = datetime.now().hour
                self.data["hourly"][hour] = self.data["hourly"].get(hour, 0) + 1 \
                    if isinstance(self.data["hourly"], dict) \
                    else self.data["hourly"][hour] + 1

                app = get_active_app()
                if app:
                    # Check if it's a tracked or any notable app
                    key = app[:20]
                    self.data["apps"][key] = self.data["apps"].get(key, 0) + 1

                # Save every 30 seconds
                if self.data["total"] % 30 == 0:
                    save_data(self.data)

            except Exception:
                pass
            time.sleep(1)

    def _refresh(self):
        self._draw()
        self.root.after(5000, self._refresh)  # redraw every 5s

    # ── drawing ───────────────────────────────────────────────────────────────
    def _rrect(self, x1, y1, x2, y2, r=22, **kw):
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
             x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        self.cv.create_polygon(pts, smooth=True, **kw)

    def _bar(self, x, y, w, h, ratio, bg, fg):
        self.cv.create_rectangle(x, y, x+w, y+h, fill=bg, outline="")
        filled = max(2, int(w * min(ratio, 1.0)))
        self.cv.create_rectangle(x, y, x+filled, y+h, fill=fg, outline="")

    def _draw(self):
        if self.view == "apps":
            self._draw_apps()
        else:
            self._draw_main()

    def _draw_main(self):
        cv = self.cv; cv.delete("all")
        d  = self.data

        # Card
        self._rrect(5,5,W-5,H-5,r=26, fill=CARD, outline=BORDER, width=1)

        # Header
        cv.create_text(16, 20, text="📱 Screen Time",
                       fill=TEXT, font=("Segoe UI Semibold",10,"bold"), anchor="w")
        cv.create_text(W-46, 20, text="⚙", fill=MUTED,
                       font=("Segoe UI",10), tags="main_settings")
        cv.create_text(W-28, 20, text="≡", fill=MUTED,
                       font=("Segoe UI",13), tags="toggle")
        cv.create_text(W-12, 20, text="✕", fill=MUTED,
                       font=("Segoe UI",9), tags="close")

        # Today total
        total    = d.get("total", 0)
        total_str = fmt_time(total)
        cv.create_text(16, 46, text=total_str,
                       fill=ACCENT2, font=("Segoe UI Semibold",22,"bold"), anchor="w")
        cv.create_text(16, 66, text="Today's screen time",
                       fill=MUTED, font=("Segoe UI",8), anchor="w")

        # Daily bar (based on 8hr = 100%)
        bar_ratio = total / (8 * 3600)
        bar_col   = GREEN if bar_ratio < 0.6 else YELLOW if bar_ratio < 0.9 else RED
        self._bar(16, 76, W-32, 5, bar_ratio, "#1E2235", bar_col)

        # Hourly mini graph
        hourly = d.get("hourly", [0]*24)
        max_h  = max(hourly) if max(hourly) > 0 else 1
        bar_w  = (W - 32) / 24
        graph_y = H - 28
        graph_h = 18

        for i, val in enumerate(hourly):
            bh  = int((val / max_h) * graph_h)
            x   = 16 + i * bar_w
            col = ACCENT if i == datetime.now().hour else MUTED
            if bh > 0:
                self.cv.create_rectangle(
                    x+1, graph_y + (graph_h - bh),
                    x + bar_w - 1, graph_y + graph_h,
                    fill=col, outline="")

        # Hour labels
        cv.create_text(16, H-8, text="12AM",
                       fill=MUTED, font=("Segoe UI",6), anchor="w")
        cv.create_text(W//2, H-8, text="12PM",
                       fill=MUTED, font=("Segoe UI",6), anchor="center")
        cv.create_text(W-16, H-8, text="11PM",
                       fill=MUTED, font=("Segoe UI",6), anchor="e")

        # Top app
        apps = d.get("apps", {})
        if apps:
            top_app = max(apps, key=apps.get)
            top_time = fmt_time(apps[top_app])
            cv.create_text(W-16, 46, text=f"📌 {top_app[:12]}",
                           fill=TEXT, font=("Segoe UI",8), anchor="e")
            cv.create_text(W-16, 58, text=top_time,
                           fill=ACCENT, font=("Segoe UI Semibold",8,"bold"), anchor="e")

        cv.create_text(W//2, H-8, text="right click → apps",
                       fill="#222233", font=("Segoe UI",6))

        cv.tag_bind("main_settings", "<Button-1>", lambda e: self._open_settings())
        cv.tag_bind("toggle",        "<Button-1>", lambda e: self._toggle_view())
        cv.tag_bind("close",         "<Button-1>", lambda e: self._quit())
        cv.tag_bind("main_settings", "<Button-1>", lambda e: open_main_settings())

    def _draw_apps(self):
        cv = self.cv; cv.delete("all")
        d  = self.data

        # Bigger height for apps view
        self.root.geometry(f"{W}x{200}+{self.root.winfo_x()}+{self.root.winfo_y()}")
        self.cv.config(height=200)
        self._rrect(5,5,W-5,195,r=26, fill=CARD, outline=BORDER, width=1)

        cv.create_text(16, 20, text="📱 App Usage — Today",
                       fill=TEXT, font=("Segoe UI Semibold",10,"bold"), anchor="w")
        cv.create_text(W-28, 20, text="←", fill=MUTED,
                       font=("Segoe UI",12), tags="toggle")
        cv.create_text(W-12, 20, text="✕", fill=MUTED,
                       font=("Segoe UI",9), tags="close")

        apps = d.get("apps", {})
        if not apps:
            cv.create_text(W//2, 100, text="No app data yet…",
                           fill=MUTED, font=("Segoe UI",10))
        else:
            # Top 5 apps
            sorted_apps = sorted(apps.items(), key=lambda x: x[1], reverse=True)[:5]
            max_val     = sorted_apps[0][1] if sorted_apps else 1

            for i, (app, secs) in enumerate(sorted_apps):
                y     = 42 + i * 30
                ratio = secs / max_val
                col   = [ACCENT, ACCENT2, GREEN, YELLOW, RED][i % 5]

                # App name
                cv.create_text(16, y+7, text=app[:16],
                               fill=TEXT, font=("Segoe UI",9), anchor="w")
                # Time
                cv.create_text(W-16, y+7, text=fmt_time(secs),
                               fill=col, font=("Segoe UI Semibold",9,"bold"), anchor="e")
                # Bar
                self._bar(16, y+16, W-32, 4, ratio, "#1E2235", col)

        cv.tag_bind("main_settings", "<Button-1>", lambda e: self._open_settings())
        cv.tag_bind("toggle",        "<Button-1>", lambda e: self._toggle_view())
        cv.tag_bind("close",         "<Button-1>", lambda e: self._quit())
        cv.tag_bind("main_settings", "<Button-1>", lambda e: open_main_settings())

    def _toggle_view(self, e=None):
        if self.view == "main":
            self.view = "apps"
        else:
            self.view = "main"
            self.root.geometry(f"{W}x{H}+{self.root.winfo_x()}+{self.root.winfo_y()}")
            self.cv.config(height=H)
        self._draw()

    def _open_settings(self):
        s = BASE_DIR / "settings.exe"
        if s.exists():
            subprocess.Popen([str(s)], cwd=str(BASE_DIR))
        else:
            s2 = BASE_DIR / "settings.py"
            if s2.exists():
                subprocess.Popen([sys.executable, str(s2)], cwd=str(BASE_DIR))

    def _quit(self):
        save_data(self.data)
        try: PID_PATH.unlink(missing_ok=True)
        except: pass
        self.root.destroy(); sys.exit(0)

    def _press(self, e): self._dx, self._dy = e.x, e.y
    def _drag(self, e):
        self.root.geometry(
            f"+{self.root.winfo_x()+e.x-self._dx}+{self.root.winfo_y()+e.y-self._dy}")

if __name__ == "__main__":
    screentime_widget = ScreenTimeWidget()
