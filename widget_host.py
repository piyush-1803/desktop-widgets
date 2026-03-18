from __future__ import annotations

import json
import os
import sys
import time
import winreg
from pathlib import Path

import tkinter as tk
import win32con
import win32gui
import win32api

BASE_DIR = Path(__file__).resolve().parent

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

CONFIG_PATH = BASE_DIR / "config.json"
PID_PATH = BASE_DIR / "widget.pid"
APP_NAME = "DesktopWidgets"


def load_config():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"x": 40, "y": 40, "width": 220, "height": 130}


def save_config(x, y, w, h):
    CONFIG_PATH.write_text(
        json.dumps({"x": x, "y": y, "width": w, "height": h}, indent=2),
        encoding="utf-8",
    )


def save_pid():
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")


def add_to_startup():
    try:
        script = str(Path(__file__).resolve())
        exe = str(Path(sys.executable))
        cmd = f'"{exe}" "{script}"'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, cmd)
    except Exception:
        pass


def find_workerw():
    progman = win32gui.FindWindow("Progman", None)
    win32gui.SendMessageTimeout(progman, 0x052C, 0, 0, win32con.SMTO_NORMAL, 1000)
    workerw = None

    def enum_cb(hwnd, _):
        nonlocal workerw
        if win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None):
            workerw = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
        return True

    win32gui.EnumWindows(enum_cb, 0)
    return workerw


def embed_to_desktop(hwnd, workerw, x, y, w, h):
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style |= win32con.WS_CHILD
    style &= ~win32con.WS_POPUP
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    ex |= win32con.WS_EX_LAYERED
    ex |= win32con.WS_EX_TOOLWINDOW
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex)

    CHROMA = win32api.RGB(0, 255, 0)
    win32gui.SetLayeredWindowAttributes(hwnd, CHROMA, 255,
                                        win32con.LWA_COLORKEY | win32con.LWA_ALPHA)
    win32gui.SetParent(hwnd, workerw)
    win32gui.SetWindowPos(hwnd, 0, x, y, w, h,
                          win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.UpdateWindow(hwnd)


class ClockWidget:
    CHROMA = "#00FF00"

    def __init__(self):
        cfg = load_config()
        self.x = cfg["x"]
        self.y = cfg["y"]
        self.w = cfg["width"]
        self.h = cfg["height"]

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.w}x{self.h}+{self.x}+{self.y}")
        self.root.configure(bg=self.CHROMA)
        self.root.attributes("-transparentcolor", self.CHROMA)

        self._build_ui()
        self._setup_drag()

        self.root.update()
        hwnd = self.root.winfo_id()
        workerw = find_workerw()
        if workerw:
            embed_to_desktop(hwnd, workerw, self.x, self.y, self.w, self.h)

        save_pid()
        add_to_startup()
        self._tick()
        self.root.mainloop()

    def _build_ui(self):
        # Use canvas for fully rounded corners
        self.cv = tk.Canvas(self.root, width=self.w, height=self.h,
                            bg=self.CHROMA, highlightthickness=0)
        self.cv.place(x=0, y=0)

        r = 28  # large radius = very round corners
        w, h = self.w, self.h
        pts = [r,0, w-r,0, w,0, w,r, w,h-r, w,h,
               w-r,h, r,h, 0,h, 0,h-r, 0,r, 0,0]
        self.cv.create_polygon(pts, smooth=True,
                               fill="#181A20", outline="#2A2D37", width=1)

        # Invisible frame for widget placement (same size, transparent bg trick)
        self.frame = tk.Frame(self.root, bg="#181A20")
        self.frame.place(x=8, y=8, width=self.w-16, height=self.h-16)

        # Close button
        self.close_btn = tk.Label(self.frame, text="✕", fg="#FFFFFF",
                                  bg="#FF4444", font=("Segoe UI", 8, "bold"),
                                  width=2, cursor="hand2")
        self.close_btn.place(relx=1.0, x=0, y=0, anchor="ne")
        self.close_btn.place_forget()

        # Time (12hr)
        self.time_label = tk.Label(self.frame, text="--:--",
                                   fg="#F5F6F8", bg="#181A20",
                                   font=("Segoe UI Semibold", 28, "bold"))
        self.time_label.place(relx=0.44, rely=0.38, anchor="center")

        # Seconds
        self.sec_label = tk.Label(self.frame, text="--",
                                  fg="#6EE7FF", bg="#181A20",
                                  font=("Segoe UI", 10))
        self.sec_label.place(relx=0.80, rely=0.28, anchor="center")

        # AM/PM label
        self.ampm_label = tk.Label(self.frame, text="AM",
                                   fg="#6EE7FF", bg="#181A20",
                                   font=("Segoe UI Semibold", 9, "bold"))
        self.ampm_label.place(relx=0.80, rely=0.46, anchor="center")

        # Date
        self.date_label = tk.Label(self.frame, text="---",
                                   fg="#C4C6CF", bg="#181A20",
                                   font=("Segoe UI", 10))
        self.date_label.place(relx=0.5, rely=0.75, anchor="center")

        for widget in [self.cv, self.frame, self.time_label,
                       self.sec_label, self.ampm_label, self.date_label]:
            widget.bind("<Enter>", self._show_close)
            widget.bind("<Leave>", self._hide_close)

        self.close_btn.bind("<Enter>", self._show_close)
        self.close_btn.bind("<Leave>", self._hide_close)
        self.close_btn.bind("<Button-1>", lambda e: self._quit())

        # Gear icon - opens main settings
        self.gear_btn = tk.Label(self.frame, text="⚙", fg="#6EE7FF",
                                 bg="#181A20", font=("Segoe UI", 9),
                                 cursor="hand2")
        self.gear_btn.place(x=6, y=4)
        self.gear_btn.bind("<Enter>", self._show_close)
        self.gear_btn.bind("<Leave>", self._hide_close)
        self.gear_btn.bind("<Button-1>", lambda e: open_main_settings())

    def _show_close(self, e=None):
        self.close_btn.place(relx=1.0, x=-4, y=4, anchor="ne")

    def _hide_close(self, e=None):
        try:
            x = self.frame.winfo_pointerx() - self.frame.winfo_rootx()
            y = self.frame.winfo_pointery() - self.frame.winfo_rooty()
            if 0 <= x <= self.frame.winfo_width() and 0 <= y <= self.frame.winfo_height():
                return
        except Exception:
            pass
        self.close_btn.place_forget()

    def _open_settings(self):
        import subprocess
        s = BASE_DIR / "settings.exe"
        if s.exists():
            subprocess.Popen([str(s)], cwd=str(BASE_DIR))
        else:
            subprocess.Popen([sys.executable, str(BASE_DIR / "settings.py")],
                             cwd=str(BASE_DIR))

    def _open_settings(self):
        s = BASE_DIR / "settings.exe"
        if s.exists():
            subprocess.Popen([str(s)], cwd=str(BASE_DIR))
        else:
            s2 = BASE_DIR / "settings.py"
            if s2.exists():
                subprocess.Popen([sys.executable, str(s2)], cwd=str(BASE_DIR))

    def _quit(self):
        try:
            PID_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)

    def _open_settings(self):
        import subprocess
        s = BASE_DIR / "settings.exe"
        if s.exists():
            subprocess.Popen([str(s)], cwd=str(BASE_DIR))
        else:
            s2 = BASE_DIR / "settings.py"
            if s2.exists():
                subprocess.Popen([sys.executable, str(s2)], cwd=str(BASE_DIR))

    def _setup_drag(self):
        self._dx = 0
        self._dy = 0
        for widget in [self.cv, self.frame, self.time_label,
                       self.sec_label, self.ampm_label, self.date_label]:
            widget.bind("<ButtonPress-1>", self._press)
            widget.bind("<B1-Motion>", self._drag)
            widget.bind("<ButtonRelease-1>", self._release)

    def _press(self, e):
        self._dx = e.x
        self._dy = e.y

    def _drag(self, e):
        self.x = self.root.winfo_x() + e.x - self._dx
        self.y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{self.x}+{self.y}")

    def _release(self, e):
        save_config(self.x, self.y, self.w, self.h)

    def _tick(self):
        now = time.localtime()
        hour12 = now.tm_hour % 12 or 12
        ampm   = "AM" if now.tm_hour < 12 else "PM"
        self.time_label.config(text=f"{hour12:02d}:{now.tm_min:02d}")
        self.sec_label.config(text=f"{now.tm_sec:02d}")
        self.ampm_label.config(text=ampm)
        self.date_label.config(text=time.strftime("%a  •  %d %b %Y", now))
        self.root.after(250, self._tick)


if __name__ == "__main__":
    ClockWidget()
