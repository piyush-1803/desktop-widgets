import tkinter as tk
import json
import subprocess
import sys
import os
from pathlib import Path

import sys as _sys
BASE_DIR = Path(_sys.executable).parent if getattr(_sys, "frozen", False) else Path("C:/DesktopWidgets")
WIDGETS_DIR = BASE_DIR / "widgets"
CONFIG_PATH = BASE_DIR / "config.json"
CITY_PATH   = BASE_DIR / "weather_city.txt"

THEMES = {
    "dark": {
        "BG":     "#0D1117", "BG2":    "#161B22", "BG3":    "#1C2128",
        "CARD":   "#21262D", "ACCENT": "#58A6FF", "TEXT":   "#E6EDF3",
        "MUTED":  "#8B949E", "BORDER": "#30363D", "RED":    "#F85149",
        "GREEN":  "#3FB950", "BTN_FG": "#FFFFFF",  "BADGE":  "#388BFD22",
    },
    "light": {
        "BG":     "#F6F8FA", "BG2":    "#FFFFFF",  "BG3":    "#F0F2F4",
        "CARD":   "#FFFFFF",  "ACCENT": "#0969DA", "TEXT":   "#1F2328",
        "MUTED":  "#636C76", "BORDER": "#D0D7DE", "RED":    "#CF222E",
        "GREEN":  "#1A7F37", "BTN_FG": "#FFFFFF",  "BADGE":  "#DDF4FF",
    }
}

WIDGET_INFO = {
    "clock":      {"icon":"🕐","label":"Clock",       "desc":"Time & date on your desktop",  "script":"widget_host.exe",      "exe":"widget_host.exe",      "pid":"widget.pid"},
    "weather":    {"icon":"🌤","label":"Weather",     "desc":"Live weather & 5-day forecast", "script":"weather_widget.exe",   "exe":"weather_widget.exe",   "pid":"weather_widget.pid"},
    "task_timer": {"icon":"⏱","label":"Task Timer",  "desc":"Focus timer with task list",    "script":"task_timer.exe",       "exe":"task_timer.exe",       "pid":"task_timer.pid"},
    "screentime": {"icon":"📱","label":"Screen Time", "desc":"App usage & daily screen time", "script":"screentime_widget.exe","exe":"screentime_widget.exe","pid":"screentime_widget.pid"},
}

def load_config():
    try: return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except: return {}

def save_config(d):
    CONFIG_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")

def is_running(exe_name):
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/FO", "CSV"],
            capture_output=True, text=True)
        return exe_name.lower() in result.stdout.lower()
    except:
        return False

def stop_widget(pid_file, exe_name):
    # Try kill by PID first
    pid_path = BASE_DIR / pid_file
    try:
        pid = int(pid_path.read_text().strip())
        subprocess.run(["taskkill","/f","/pid",str(pid)], capture_output=True)
        pid_path.unlink(missing_ok=True)
    except: pass
    # Always also kill by exe name to be sure
    try:
        subprocess.run(["taskkill","/f","/im", exe_name], capture_output=True)
    except: pass

def start_widget(script):
    exe = BASE_DIR / script
    if exe.exists():
        subprocess.Popen([str(exe)],
                         creationflags=subprocess.CREATE_NO_WINDOW,
                         cwd=str(BASE_DIR))
    else:
        # fallback to python for .py files during development
        py = BASE_DIR / script.replace(".exe", ".py")
        if py.exists():
            subprocess.Popen([sys.executable, str(py)],
                             creationflags=subprocess.CREATE_NO_WINDOW,
                             cwd=str(BASE_DIR))


class SettingsPanel:
    def __init__(self):
        self.mode = "dark"
        self.c    = THEMES["dark"]

        self.root = tk.Tk()
        self.root.title("DesktopWidgets — Settings")
        self.root.geometry("520x640")
        self.root.resizable(False, False)
        self._apply_titlebar()
        self._build()
        # Refresh status every 2s
        self._refresh_loop()
        self.root.mainloop()

    def _apply_titlebar(self):
        try:
            from ctypes import windll, c_int, byref, sizeof
            self.root.update()
            windll.dwmapi.DwmSetWindowAttribute(
                self.root.winfo_id(), 20,
                byref(c_int(1 if self.mode=="dark" else 0)), sizeof(c_int))
        except: pass

    def _build(self):
        c = self.c
        self.root.configure(bg=c["BG"])
        for w in self.root.winfo_children(): w.destroy()

        # ── Sidebar + Main layout ──
        sidebar = tk.Frame(self.root, bg=c["BG2"], width=160)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        main = tk.Frame(self.root, bg=c["BG"])
        main.pack(side="left", fill="both", expand=True)

        # ── Sidebar ──
        tk.Frame(sidebar, bg=c["BORDER"], height=1).pack(fill="x")

        # App icon + name
        icon_frame = tk.Frame(sidebar, bg=c["BG2"], height=80)
        icon_frame.pack(fill="x"); icon_frame.pack_propagate(False)
        tk.Label(icon_frame, text="⚙️", bg=c["BG2"],
                 font=("Segoe UI",26)).place(relx=0.5,y=24,anchor="n")
        tk.Label(icon_frame, text="Widgets", fg=c["TEXT"], bg=c["BG2"],
                 font=("Segoe UI Semibold",11,"bold")).place(relx=0.5,y=56,anchor="n")

        tk.Frame(sidebar, bg=c["BORDER"], height=1).pack(fill="x")

        # Nav items
        self.nav_btns = {}
        nav_items = [
            ("🧩", "Widgets"),
            ("📍", "Clock"),
            ("🌤", "Weather"),
            ("⏱", "Task Timer"),
            ("⚙", "General"),
        ]
        for icon, label in nav_items:
            btn = tk.Frame(sidebar, bg=c["BG2"], cursor="hand2")
            btn.pack(fill="x")
            tk.Label(btn, text=f"  {icon}  {label}", fg=c["MUTED"], bg=c["BG2"],
                     font=("Segoe UI",10), pady=11, anchor="w").pack(fill="x")
            btn.bind("<Button-1>", lambda e, l=label: self._nav(l))
            for child in btn.winfo_children():
                child.bind("<Button-1>", lambda e, l=label: self._nav(l))
            self.nav_btns[label] = btn

        tk.Frame(sidebar, bg=c["BORDER"], height=1).pack(fill="x", pady=(8,0))

        # Theme toggle in sidebar
        toggle = "☀  Light" if self.mode=="dark" else "🌙  Dark"
        tk.Button(sidebar, text=toggle, bg=c["BG3"], fg=c["MUTED"],
                  relief="flat", font=("Segoe UI",9), pady=8,
                  cursor="hand2", command=self._toggle_theme,
                  activebackground=c["BG3"]).pack(fill="x", padx=12, pady=12)

        # ── Main content ──
        self.content = tk.Frame(main, bg=c["BG"])
        self.content.pack(fill="both", expand=True, padx=0, pady=0)

        self._show_widgets_page()

    def _nav(self, label):
        c = self.c
        # Highlight selected
        for lbl, btn in self.nav_btns.items():
            bg = c["BG3"] if lbl == label else c["BG2"]
            btn.configure(bg=bg)
            for ch in btn.winfo_children():
                ch.configure(bg=bg,
                             fg=c["TEXT"] if lbl==label else c["MUTED"])

        pages = {
            "Widgets":    self._show_widgets_page,
            "Clock":      lambda: self._show_widget_settings("clock"),
            "Weather":    lambda: self._show_widget_settings("weather"),
            "Task Timer": lambda: self._show_widget_settings("task_timer"),
            "General":    self._show_general_page,
        }
        if label in pages: pages[label]()

    def _clear_content(self):
        for w in self.content.winfo_children(): w.destroy()

    def _section(self, parent, title):
        tk.Label(parent, text=title.upper(), fg=self.c["MUTED"], bg=self.c["BG"],
                 font=("Segoe UI",8)).pack(anchor="w", padx=20, pady=(18,6))

    # ── Widgets overview page ─────────────────────────────────────────────────
    def _show_widgets_page(self):
        self._clear_content()
        c = self.c

        # Header
        hdr = tk.Frame(self.content, bg=c["BG"], height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="My Widgets", fg=c["TEXT"], bg=c["BG"],
                 font=("Segoe UI Semibold",16,"bold")).place(x=20,rely=0.5,anchor="w")
        tk.Frame(self.content, bg=c["BORDER"], height=1).pack(fill="x")

        self._section(self.content, "Installed")

        self.widget_rows = {}
        for key, info in WIDGET_INFO.items():
            self._widget_card(self.content, key, info)

        self._section(self.content, "Add More Widgets")
        add_frame = tk.Frame(self.content, bg=c["CARD"],
                             highlightbackground=c["BORDER"], highlightthickness=1)
        add_frame.pack(fill="x", padx=20, pady=(0,4))
        tk.Label(add_frame, text="  +  Drop any .html file into C:/DesktopWidgets/widgets/",
                 fg=c["MUTED"], bg=c["CARD"], font=("Segoe UI",9), pady=12).pack(anchor="w")

        # Status bar
        tk.Frame(self.content, bg=c["BORDER"], height=1).pack(side="bottom", fill="x")
        self.status = tk.Label(self.content, text="Ready", fg=c["MUTED"], bg=c["BG2"],
                               font=("Segoe UI",9), anchor="w", padx=16)
        self.status.pack(side="bottom", fill="x", ipady=7)

    def _widget_card(self, parent, key, info):
        c   = self.c
        running = is_running(info["exe"])

        card = tk.Frame(parent, bg=c["CARD"],
                        highlightbackground=c["BORDER"], highlightthickness=1)
        card.pack(fill="x", padx=20, pady=4)

        inner = tk.Frame(card, bg=c["CARD"])
        inner.pack(fill="x", padx=14, pady=12)

        # Icon
        tk.Label(inner, text=info["icon"], bg=c["CARD"],
                 font=("Segoe UI",20)).grid(row=0,column=0,rowspan=2,padx=(0,14))

        # Label + desc
        tk.Label(inner, text=info["label"], fg=c["TEXT"], bg=c["CARD"],
                 font=("Segoe UI Semibold",12,"bold"), anchor="w").grid(row=0,column=1,sticky="w")
        tk.Label(inner, text=info["desc"], fg=c["MUTED"], bg=c["CARD"],
                 font=("Segoe UI",9), anchor="w").grid(row=1,column=1,sticky="w")

        # Status badge
        badge_bg = c["GREEN"] if running else c["BG3"]
        badge_fg = "#000000" if running else c["MUTED"]
        badge_txt = "● Running" if running else "○ Stopped"
        tk.Label(inner, text=badge_txt, fg=badge_fg, bg=badge_bg,
                 font=("Segoe UI",8), padx=8, pady=3).grid(row=0,column=2,padx=(14,0))

        # Buttons
        btn_frame = tk.Frame(inner, bg=c["CARD"])
        btn_frame.grid(row=1, column=2, padx=(14,0), sticky="e")

        # Always show both Start and Stop
        tk.Button(btn_frame, text="▶", bg=c["GREEN"], fg="#FFFFFF",
                  relief="flat", font=("Segoe UI",8,"bold"),
                  padx=6, pady=3, cursor="hand2",
                  command=lambda k=key: self._start(k),
                  activebackground=c["GREEN"]).pack(side="left", padx=(0,3))
        tk.Button(btn_frame, text="⏹", bg=c["RED"], fg="#FFFFFF",
                  relief="flat", font=("Segoe UI",8,"bold"),
                  padx=6, pady=3, cursor="hand2",
                  command=lambda k=key: self._stop(k),
                  activebackground=c["RED"]).pack(side="left", padx=(0,4))

        tk.Button(btn_frame, text="⚙", bg=c["BG3"], fg=c["MUTED"],
                  relief="flat", font=("Segoe UI",9),
                  padx=6, pady=3, cursor="hand2",
                  command=lambda k=key: self._nav(
                      {"clock":"Clock","weather":"Weather","task_timer":"Task Timer"}[k]),
                  activebackground=c["BG3"]).pack(side="left")

        inner.columnconfigure(1, weight=1)
        self.widget_rows[key] = card

    # ── Per-widget settings page ──────────────────────────────────────────────
    def _show_widget_settings(self, key):
        self._clear_content()
        c    = self.c
        info = WIDGET_INFO[key]

        hdr = tk.Frame(self.content, bg=c["BG"], height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Button(hdr, text="← Back", bg=c["BG"], fg=c["ACCENT"], relief="flat",
                  font=("Segoe UI",10), cursor="hand2",
                  command=self._show_widgets_page,
                  activebackground=c["BG"]).place(x=12,rely=0.5,anchor="w")
        tk.Label(hdr, text=f"{info['icon']}  {info['label']}",
                 fg=c["TEXT"], bg=c["BG"],
                 font=("Segoe UI Semibold",14,"bold")).place(relx=0.5,rely=0.5,anchor="center")
        tk.Frame(self.content, bg=c["BORDER"], height=1).pack(fill="x")

        if key == "clock":
            self._clock_settings()
        elif key == "weather":
            self._weather_settings()
        elif key == "task_timer":
            self._timer_settings()

        # Status + save bar
        tk.Frame(self.content, bg=c["BORDER"], height=1).pack(side="bottom", fill="x")
        self.status = tk.Label(self.content, text="Ready", fg=c["MUTED"], bg=c["BG2"],
                               font=("Segoe UI",9), anchor="w", padx=16)
        self.status.pack(side="bottom", fill="x", ipady=7)

    def _clock_settings(self):
        c   = self.c
        cfg = load_config()
        self._section(self.content, "Position & Size")
        card = tk.Frame(self.content, bg=c["CARD"],
                        highlightbackground=c["BORDER"], highlightthickness=1)
        card.pack(fill="x", padx=20)
        grid = tk.Frame(card, bg=c["CARD"]); grid.pack(padx=16,pady=14,fill="x")

        self._xvar = tk.StringVar(value=str(cfg.get("x",40)))
        self._yvar = tk.StringVar(value=str(cfg.get("y",40)))
        self._wvar = tk.StringVar(value=str(cfg.get("width",220)))
        self._hvar = tk.StringVar(value=str(cfg.get("height",130)))

        for i,(lbl,var) in enumerate([("X",self._xvar),("Y",self._yvar),
                                       ("Width",self._wvar),("Height",self._hvar)]):
            r,col = divmod(i,2)
            tk.Label(grid, text=lbl, fg=c["MUTED"], bg=c["CARD"],
                     font=("Segoe UI",9)).grid(row=r*2,column=col*2,sticky="w",
                                                padx=(0,8),pady=(8,2))
            tk.Entry(grid, textvariable=var, bg=c["BG3"], fg=c["TEXT"],
                     insertbackground=c["TEXT"], relief="flat",
                     font=("Segoe UI",11), width=8,
                     highlightbackground=c["BORDER"],
                     highlightthickness=1).grid(row=r*2+1,column=col*2,
                                                 sticky="ew",padx=(0,24))
        grid.columnconfigure(0,weight=1); grid.columnconfigure(2,weight=1)

        self._section(self.content, "Controls")
        btn_card = tk.Frame(self.content, bg=c["CARD"],
                            highlightbackground=c["BORDER"], highlightthickness=1)
        btn_card.pack(fill="x", padx=20)
        btn_row = tk.Frame(btn_card, bg=c["CARD"])
        btn_row.pack(padx=16, pady=14)
        for txt,bg,cmd in [
            ("💾  Save & Restart", c["ACCENT"], self._save_restart_clock),
            ("▶  Start",           c["GREEN"],  lambda: self._start("clock")),
            ("⏹  Stop",            c["RED"],    lambda: self._stop("clock")),
        ]:
            tk.Button(btn_row, text=txt, bg=bg, fg="#FFFFFF", relief="flat",
                      font=("Segoe UI",10,"bold"), padx=12, pady=7,
                      cursor="hand2", command=cmd,
                      activebackground=bg).pack(side="left", padx=(0,8))

    def _save_restart_clock(self):
        try:
            cfg = load_config()
            cfg["x"] = int(self._xvar.get())
            cfg["y"] = int(self._yvar.get())
            cfg["width"]  = int(self._wvar.get())
            cfg["height"] = int(self._hvar.get())
            save_config(cfg)
            self._stop("clock")
            import time; time.sleep(0.8)
            self._start("clock")
            self.status.config(text="✅ Clock saved & restarted!", fg=self.c["GREEN"])
        except Exception as e:
            self.status.config(text=f"❌ {e}", fg=self.c["RED"])

    def _weather_settings(self):
        c = self.c
        city = CITY_PATH.read_text().strip() if CITY_PATH.exists() else ""
        self._section(self.content, "Location")
        card = tk.Frame(self.content, bg=c["CARD"],
                        highlightbackground=c["BORDER"], highlightthickness=1)
        card.pack(fill="x", padx=20)
        inner = tk.Frame(card, bg=c["CARD"]); inner.pack(padx=16,pady=14,fill="x")
        tk.Label(inner, text="City Name", fg=c["MUTED"], bg=c["CARD"],
                 font=("Segoe UI",9)).pack(anchor="w", pady=(0,4))
        self._city_var = tk.StringVar(value=city)
        tk.Entry(inner, textvariable=self._city_var, bg=c["BG3"], fg=c["TEXT"],
                 insertbackground=c["TEXT"], relief="flat",
                 font=("Segoe UI",12), highlightbackground=c["BORDER"],
                 highlightthickness=1).pack(fill="x", ipady=7)
        tk.Label(inner, text="e.g. Jamshedpur, Mumbai, Delhi, Bangalore",
                 fg=c["MUTED"], bg=c["CARD"],
                 font=("Segoe UI",8)).pack(anchor="w", pady=(4,0))

        self._section(self.content, "Controls")
        btn_card = tk.Frame(self.content, bg=c["CARD"],
                            highlightbackground=c["BORDER"], highlightthickness=1)
        btn_card.pack(fill="x", padx=20)
        btn_row = tk.Frame(btn_card, bg=c["CARD"])
        btn_row.pack(padx=16, pady=14)
        for txt,bg,cmd in [
            ("💾  Save & Restart", c["ACCENT"], self._save_weather),
            ("▶  Start",           c["GREEN"],  lambda: self._start("weather")),
            ("⏹  Stop",            c["RED"],    lambda: self._stop("weather")),
        ]:
            tk.Button(btn_row, text=txt, bg=bg, fg="#FFFFFF", relief="flat",
                      font=("Segoe UI",10,"bold"), padx=12, pady=7,
                      cursor="hand2", command=cmd,
                      activebackground=bg).pack(side="left", padx=(0,8))

    def _save_weather(self):
        city = self._city_var.get().strip()
        if city:
            CITY_PATH.write_text(city)
            self._stop("weather")
            import time; time.sleep(0.8)
            self._start("weather")
            self.status.config(text=f"✅ Weather set to {city}!", fg=self.c["GREEN"])
        else:
            self.status.config(text="❌ Enter a city name", fg=self.c["RED"])

    def _timer_settings(self):
        c = self.c
        self._section(self.content, "About")
        card = tk.Frame(self.content, bg=c["CARD"],
                        highlightbackground=c["BORDER"], highlightthickness=1)
        card.pack(fill="x", padx=20)
        tk.Label(card,
                 text="  Tasks are managed directly inside the widget.\n  Right-click the widget to add tasks.\n  Click the task name to edit it inline.\n  Use 🗑 to delete a task.",
                 fg=c["MUTED"], bg=c["CARD"],
                 font=("Segoe UI",10), justify="left", pady=14).pack(anchor="w")

        self._section(self.content, "Controls")
        btn_card = tk.Frame(self.content, bg=c["CARD"],
                            highlightbackground=c["BORDER"], highlightthickness=1)
        btn_card.pack(fill="x", padx=20)
        btn_row = tk.Frame(btn_card, bg=c["CARD"])
        btn_row.pack(padx=16, pady=14)
        for txt,bg,cmd in [
            ("▶  Start", c["GREEN"], lambda: self._start("task_timer")),
            ("⏹  Stop",  c["RED"],   lambda: self._stop("task_timer")),
        ]:
            tk.Button(btn_row, text=txt, bg=bg, fg="#FFFFFF", relief="flat",
                      font=("Segoe UI",10,"bold"), padx=14, pady=7,
                      cursor="hand2", command=cmd,
                      activebackground=bg).pack(side="left", padx=(0,8))

    # ── General page ──────────────────────────────────────────────────────────
    def _show_general_page(self):
        self._clear_content()
        c = self.c
        hdr = tk.Frame(self.content, bg=c["BG"], height=56)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  General", fg=c["TEXT"], bg=c["BG"],
                 font=("Segoe UI Semibold",14,"bold")).place(x=20,rely=0.5,anchor="w")
        tk.Frame(self.content, bg=c["BORDER"], height=1).pack(fill="x")

        self._section(self.content, "All Widgets")
        card = tk.Frame(self.content, bg=c["CARD"],
                        highlightbackground=c["BORDER"], highlightthickness=1)
        card.pack(fill="x", padx=20)
        btn_row = tk.Frame(card, bg=c["CARD"])
        btn_row.pack(padx=16, pady=14)
        tk.Button(btn_row, text="▶  Start All", bg=c["GREEN"], fg="#FFFFFF",
                  relief="flat", font=("Segoe UI",10,"bold"),
                  padx=14, pady=8, cursor="hand2",
                  command=self._start_all,
                  activebackground=c["GREEN"]).pack(side="left", padx=(0,10))
        tk.Button(btn_row, text="⏹  Stop All", bg=c["RED"], fg="#FFFFFF",
                  relief="flat", font=("Segoe UI",10,"bold"),
                  padx=14, pady=8, cursor="hand2",
                  command=self._stop_all,
                  activebackground=c["RED"]).pack(side="left")

        self._section(self.content, "Startup")
        s_card = tk.Frame(self.content, bg=c["CARD"],
                          highlightbackground=c["BORDER"], highlightthickness=1)
        s_card.pack(fill="x", padx=20)
        tk.Label(s_card,
                 text="  Clock widget auto-starts on Windows login.\n  Run add_startup.py to re-register if needed.",
                 fg=c["MUTED"], bg=c["CARD"],
                 font=("Segoe UI",10), justify="left", pady=14).pack(anchor="w")

        self._section(self.content, "App Info")
        i_card = tk.Frame(self.content, bg=c["CARD"],
                          highlightbackground=c["BORDER"], highlightthickness=1)
        i_card.pack(fill="x", padx=20)
        tk.Label(i_card,
                 text="  DesktopWidgets  v1.0\n  Built with Python + tkinter + Win32\n  Widgets folder: C:/DesktopWidgets/widgets/",
                 fg=c["MUTED"], bg=c["CARD"],
                 font=("Segoe UI",10), justify="left", pady=14).pack(anchor="w")

        tk.Frame(self.content, bg=c["BORDER"], height=1).pack(side="bottom", fill="x")
        self.status = tk.Label(self.content, text="Ready", fg=c["MUTED"], bg=c["BG2"],
                               font=("Segoe UI",9), anchor="w", padx=16)
        self.status.pack(side="bottom", fill="x", ipady=7)

    # ── Controls ──────────────────────────────────────────────────────────────
    def _start(self, key):
        info = WIDGET_INFO[key]
        start_widget(info["script"])
        try: self.status.config(text=f"✅ {info['label']} started!", fg=self.c["GREEN"])
        except: pass

    def _stop(self, key):
        info = WIDGET_INFO[key]
        stop_widget(info["pid"], info["exe"])
        try: self.status.config(text=f"⏹ {info['label']} stopped.", fg=self.c["MUTED"])
        except: pass

    def _start_all(self):
        for key in WIDGET_INFO: self._start(key)
        import time; time.sleep(0.3)
        try: self.status.config(text="✅ All widgets started!", fg=self.c["GREEN"])
        except: pass

    def _stop_all(self):
        for key in WIDGET_INFO: self._stop(key)
        try: self.status.config(text="⏹ All widgets stopped.", fg=self.c["MUTED"])
        except: pass

    def _toggle_theme(self):
        self.mode = "light" if self.mode=="dark" else "dark"
        self.c    = THEMES[self.mode]
        self._apply_titlebar()
        self._build()

    def _refresh_loop(self):
        try:
            # Only refresh if we are on the widgets overview page
            if hasattr(self, 'widget_rows') and self.widget_rows:
                for key, card in self.widget_rows.items():
                    info    = WIDGET_INFO[key]
                    running = is_running(info["exe"])
                    # Find badge label and update it
                    for child in card.winfo_children():
                        for sub in child.winfo_children():
                            try:
                                txt = sub.cget("text")
                                if "Running" in txt or "Stopped" in txt:
                                    sub.config(
                                        text="● Running" if running else "○ Stopped",
                                        fg="#000000" if running else self.c["MUTED"],
                                        bg=self.c["GREEN"] if running else self.c["BG3"],
                                    )
                            except: pass
        except: pass
        self.root.after(2000, self._refresh_loop)


if __name__ == "__main__":
    SettingsPanel()
