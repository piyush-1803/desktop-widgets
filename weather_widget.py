from __future__ import annotations
import json, os, sys, time, threading, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime
import tkinter as tk
import win32con, win32gui, win32api

BASE_DIR  = Path(__file__).resolve().parent
PID_PATH  = BASE_DIR / "weather_widget.pid"
CITY_PATH = BASE_DIR / "weather_city.txt"
CHROMA    = "#00FF02"

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

W, H      = 320, 200

WTTR = {
    113:("☀️","Clear"),       116:("⛅","Partly Cloudy"),
    119:("☁️","Cloudy"),      122:("☁️","Overcast"),
    143:("🌫","Mist"),         176:("🌦","Light Rain"),
    200:("⛈","Thunderstorm"), 227:("🌨","Snow"),
    248:("🌫","Fog"),          260:("🌫","Fog"),
    263:("🌦","Drizzle"),      266:("🌦","Drizzle"),
    281:("🌧","Sleet"),        293:("🌧","Light Rain"),
    296:("🌧","Light Rain"),   299:("🌧","Rain"),
    302:("🌧","Rain"),         305:("🌧","Heavy Rain"),
    308:("🌧","Heavy Rain"),   311:("🌧","Sleet"),
    317:("🌧","Sleet"),        320:("🌨","Light Snow"),
    323:("❄️","Snow"),         326:("❄️","Snow"),
    329:("❄️","Heavy Snow"),   332:("❄️","Heavy Snow"),
    335:("❄️","Heavy Snow"),   338:("❄️","Heavy Snow"),
    353:("🌦","Rain Shower"),  356:("🌧","Rain Shower"),
    359:("🌧","Heavy Shower"), 362:("🌧","Sleet Shower"),
    368:("🌨","Snow Shower"),  371:("❄️","Heavy Snow"),
    386:("⛈","Thunder Rain"), 389:("⛈","Heavy Thunder"),
    392:("⛈","Thunder Snow"), 395:("❄️","Heavy Snow"),
}

def wmo_info(code):
    return WTTR.get(int(code), ("🌡","Unknown"))

def get_theme(code, temp):
    hour    = datetime.now().hour
    is_night = hour >= 20 or hour < 6
    is_dawn  = 6 <= hour < 8
    is_dusk  = 17 <= hour < 20
    month   = datetime.now().month
    c       = int(code)

    if month in (12, 1, 2):   season = "winter"
    elif month in (3, 4, 5):  season = "spring"
    elif month in (6, 7, 8):  season = "summer"
    else:                      season = "autumn"

    if is_night:
        if c in (113,):
            return {"top":"#0A0E1A","bot":"#1A2340","text":"#E8F4FF",
                    "sub":"#8AADCC","card":"#1E2A3A","accent":"#4A90D9",
                    "label":"Clear Night","emoji":"🌙"}
        return    {"top":"#080C16","bot":"#141C2E","text":"#D0E8FF",
                   "sub":"#6A8AAA","card":"#1A2A3A","accent":"#3A70A9",
                   "label":"Night","emoji":"🌙"}

    if is_dawn:
        return    {"top":"#1A0A2E","bot":"#E05A20","text":"#FFE0C0",
                   "sub":"#FFAA80","card":"#1E2A3A","accent":"#FF7A30",
                   "label":"Dawn","emoji":"🌅"}

    if is_dusk:
        return    {"top":"#1A0E3A","bot":"#C04818","text":"#FFD0A0",
                   "sub":"#FF9060","card":"#1E2A3A","accent":"#E06828",
                   "label":"Dusk","emoji":"🌇"}

    if c == 113:
        if season == "summer":
            return {"top":"#0078D4","bot":"#38B0FF","text":"#FFFFFF",
                    "sub":"#CCEEFF","card":"#1E3A5A","accent":"#FFD700",
                    "label":"Sunny","emoji":"☀️"}
        if season == "winter":
            return {"top":"#2A4A6A","bot":"#5A8AAA","text":"#FFFFFF",
                    "sub":"#AACCEE","card":"#1E2A3A","accent":"#AADDFF",
                    "label":"Clear & Cold","emoji":"🌤"}
        if season == "spring":
            return {"top":"#1A7ABF","bot":"#5AC0FF","text":"#FFFFFF",
                    "sub":"#DDEEFF","card":"#1A3A6A","accent":"#90EE90",
                    "label":"Clear","emoji":"☀️"}
        return    {"top":"#1565C0","bot":"#42A5F5","text":"#FFFFFF",
                   "sub":"#BBDDFF","card":"#1A3A6A","accent":"#FFD700",
                   "label":"Clear","emoji":"☀️"}

    if c <= 116:
        return    {"top":"#1A5A9A","bot":"#4A90D4","text":"#FFFFFF",
                   "sub":"#CCE0FF","card":"#1E2A3A","accent":"#FFE080",
                   "label":"Partly Cloudy","emoji":"⛅"}

    if c <= 122:
        return    {"top":"#3A4A5A","bot":"#6A7A8A","text":"#EEEEFF",
                   "sub":"#AABBCC","card":"#2A3A4A","accent":"#AABBCC",
                   "label":"Overcast","emoji":"☁️"}

    if c in (248,260,143):
        return    {"top":"#4A5A6A","bot":"#8A9AAA","text":"#F0F8FF",
                   "sub":"#BBCCDD","card":"#2A3A4A","accent":"#CCDDEE",
                   "label":"Foggy","emoji":"🌫"}

    if c in (263,266,293,296):
        return    {"top":"#1A3060","bot":"#3A6090","text":"#E0F0FF",
                   "sub":"#88AACC","card":"#2A3A4A","accent":"#88BBEE",
                   "label":"Drizzle","emoji":"🌦"}

    if c in (299,302,305,308,353,356,359):
        return    {"top":"#0D1E3A","bot":"#1A3A5A","text":"#D0E8FF",
                   "sub":"#6699BB","card":"#1A2A3A","accent":"#4A80B0",
                   "label":"Rainy","emoji":"🌧"}

    if c >= 386:
        return    {"top":"#0A0A1A","bot":"#1A1A3A","text":"#D0D8FF",
                   "sub":"#6060AA","card":"#181828","accent":"#8080FF",
                   "label":"Thunderstorm","emoji":"⛈"}

    if c >= 320:
        return    {"top":"#2A3A5A","bot":"#6A8AAA","text":"#FFFFFF",
                   "sub":"#CCDEFF","card":"#1E2A3A","accent":"#AADDFF",
                   "label":"Snowing","emoji":"❄️"}

    return        {"top":"#1565C0","bot":"#42A5F5","text":"#FFFFFF",
                   "sub":"#BBDDFF","card":"#1A3A6A","accent":"#FFD700",
                   "label":"","emoji":"🌡"}

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
    win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(0,255,2), 255,
        win32con.LWA_COLORKEY | win32con.LWA_ALPHA)
    win32gui.SetParent(hwnd, ww)
    win32gui.SetWindowPos(hwnd, 0, x, y, w, h,
        win32con.SWP_NOZORDER|win32con.SWP_SHOWWINDOW|win32con.SWP_FRAMECHANGED)
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.UpdateWindow(hwnd)

def fetch_weather(city):
    try:
        # FIXED: use urllib.parse.quote instead of urllib.request.quote
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent":"curl/7.68.0"})
        # FIXED: increased timeout from 8 to 15 for slower connections
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        # Handle both response formats: with or without "data" wrapper
        root     = data.get("data", data)
        cur      = root["current_condition"][0]
        days_raw = root["weather"]
        days     = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        forecast = []
        for day in days_raw[:5]:
            d = datetime.strptime(day["date"], "%Y-%m-%d")
            forecast.append({
                "day":  days[d.weekday()],
                "code": int(day["hourly"][4]["weatherCode"]),
                "hi":   round(float(day["maxtempC"])),
                "lo":   round(float(day["mintempC"])),
            })
        return {
            "city":     city,
            "temp":     int(cur["temp_C"]),
            "feels":    int(cur["FeelsLikeC"]),
            "code":     int(cur["weatherCode"]),
            "humidity": int(cur["humidity"]),
            "wind":     int(cur["windspeedKmph"]),
            "desc":     cur["weatherDesc"][0]["value"],
            "forecast": forecast,
            "updated":  time.strftime("%H:%M"),
        }
    except Exception as e:
        return {"error": str(e)}

def lerp_color(c1, c2, t):
    r1,g1,b1 = int(c1[1:3],16),int(c1[3:5],16),int(c1[5:7],16)
    r2,g2,b2 = int(c2[1:3],16),int(c2[3:5],16),int(c2[5:7],16)
    r = int(r1+(r2-r1)*t)
    g = int(g1+(g2-g1)*t)
    b = int(b1+(b2-b1)*t)
    return f"#{r:02x}{g:02x}{b:02x}"

class CityDialog(tk.Toplevel):
    def __init__(self, parent, current=""):
        super().__init__(parent)
        self.result = None
        self.overrideredirect(True)
        self.configure(bg="#0D1117")
        self.attributes("-topmost", True)
        outer = tk.Frame(self, bg="#1565C0", padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        inn = tk.Frame(outer, bg="#0D1117")
        inn.pack(fill="both", expand=True, padx=1, pady=1)
        hdr = tk.Frame(inn, bg="#161B22", height=46)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="📌  Set Your City", fg="#FFFFFF", bg="#161B22",
                 font=("Segoe UI Semibold",12,"bold")).place(x=14,rely=0.5,anchor="w")
        tk.Button(hdr, text="✖", fg="#666666", bg="#161B22", relief="flat",
                  cursor="hand2", command=self.destroy,
                  activebackground="#161B22").place(relx=1.0,x=-12,rely=0.5,anchor="e")
        hdr.bind("<ButtonPress-1>", lambda e: setattr(self,"_dx",e.x) or setattr(self,"_dy",e.y))
        hdr.bind("<B1-Motion>", lambda e: self.geometry(
            f"+{self.winfo_x()+e.x-self._dx}+{self.winfo_y()+e.y-self._dy}"))
        body = tk.Frame(inn, bg="#0D1117"); body.pack(padx=18,pady=14,fill="x")
        tk.Label(body, text="Enter your city  (e.g. Ranchi, Delhi, Mumbai)",
                 fg="#8B949E", bg="#0D1117", font=("Segoe UI",9),
                 wraplength=240).pack(anchor="w",pady=(0,6))
        self._var = tk.StringVar(value=current)
        e = tk.Entry(body, textvariable=self._var, bg="#161B22", fg="#FFFFFF",
                     insertbackground="#FFFFFF", relief="flat",
                     font=("Segoe UI",12), highlightbackground="#1565C0",
                     highlightthickness=1)
        e.pack(fill="x",ipady=8); e.bind("<Return>",lambda ev:self._save()); e.focus_set()
        btn = tk.Frame(inn,bg="#0D1117"); btn.pack(fill="x",padx=18,pady=(4,16))
        tk.Button(btn,text="Save",bg="#1565C0",fg="#FFFFFF",relief="flat",
                  font=("Segoe UI",10,"bold"),padx=20,pady=7,cursor="hand2",
                  command=self._save,activebackground="#1976D2").pack(side="right")
        self.update_idletasks()
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        self.geometry(f"+{(sw-self.winfo_width())//2}+{(sh-self.winfo_height())//2}")
    def _save(self): self.result=self._var.get().strip(); self.destroy()
    def ask(self): self.grab_set(); self.wait_window(); return self.result

class WeatherWidget:
    def __init__(self):
        self.data  = None
        self.city  = ""
        self._dx = self._dy = 0
        if CITY_PATH.exists():
            self.city = CITY_PATH.read_text().strip()
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{W}x{H}+380+60")
        self.root.configure(bg=CHROMA)
        self.root.attributes("-transparentcolor", CHROMA)
        self.cv = tk.Canvas(self.root, width=W, height=H,
                            bg=CHROMA, highlightthickness=0)
        self.cv.pack()
        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>",     self._move)
        self._draw_loading()
        self.root.update()
        ww = find_workerw()
        if ww: embed(self.root.winfo_id(), ww, 380, 60, W, H)
        PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
        if self.city:
            threading.Thread(target=self._bg_fetch, daemon=True).start()
        else:
            self.root.after(300, self._ask_city)
        self._schedule_theme_refresh()
        self.root.mainloop()

    def _schedule_theme_refresh(self):
        if self.data and "error" not in self.data:
            self._draw()
        self.root.after(60_000, self._schedule_theme_refresh)

    def _bg_fetch(self):
        result = fetch_weather(self.city)
        self.data = result
        self.root.after(0, self._draw)
        self.root.after(600_000, lambda: threading.Thread(
            target=self._bg_fetch, daemon=True).start())

    def _rrect(self, x1, y1, x2, y2, r=20, **kw):
        pts=[x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
             x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
        self.cv.create_polygon(pts, smooth=True, **kw)

    def _gradient(self, c1, c2, x0, y0, x1, y1, steps=40):
        for i in range(steps):
            t   = i / steps
            col = lerp_color(c1, c2, t)
            y   = y0 + (y1-y0)*t
            self.cv.create_line(x0, y, x1, y, fill=col)

    def _draw_loading(self):
        cv=self.cv; cv.delete("all")
        self._gradient("#1565C0","#42A5F5",5,5,W-5,H-5)
        self._rrect(5,5,W-5,H-5,r=22,fill="",outline="#1976D2",width=1)
        cv.create_text(W//2,H//2-14,text="⛅",font=("Segoe UI",30))
        cv.create_text(W//2,H//2+18,text="Loading weather…",
                       fill="#CCEEFF",font=("Segoe UI",10))
        cv.create_text(W-16,18,text="✖",fill="#AAAACC",
                       font=("Segoe UI",10),tags="close")
        cv.tag_bind("close","<Button-1>",lambda e:self._quit())

    def _draw(self):
        if not self.data: self._draw_loading(); return
        if "error" in self.data:
            cv=self.cv; cv.delete("all")
            self._rrect(5,5,W-5,H-5,r=22,fill="#0A0E1A",outline="#222244",width=1)
            cv.create_text(W//2,H//2-16,text="⚠️",font=("Segoe UI",26))
            cv.create_text(W//2,H//2+12,text="Could not load weather",
                           fill="#EE8888",font=("Segoe UI",10))
            cv.create_text(W//2,H//2+30,text=str(self.data["error"])[:36],
                           fill="#885555",font=("Segoe UI",8))
            cv.create_text(W//2,H//2+52,text="📌 Click to change city",
                           fill="#5599FF",font=("Segoe UI",9),tags="change")
            cv.create_text(W-16,18,text="✖",fill="#AAAACC",
                           font=("Segoe UI",10),tags="close")
            cv.tag_bind("change","<Button-1>",lambda e:self._ask_city())
            cv.tag_bind("close","<Button-1>",lambda e:self._quit())
            return

        d  = self.data
        th = get_theme(d["code"], d["temp"])
        cv = self.cv; cv.delete("all")

        self._gradient(th["top"], th["bot"], 6, 6, W-6, H-6, steps=H-12)
        self._rrect(5,5,W-5,H-5,r=22,fill="",outline=th["top"],width=1)

        cv.create_oval(16, 30, 92, 106,
                       fill=th["card"] if th["card"] != "#334455" else "#445566",
                       outline="#AAAACC", width=1)
        cv.create_text(56, 70, text=wmo_info(d["code"])[0],
                       font=("Segoe UI",42))

        cv.create_text(54, 130, text=f"{d['temp']}°",
                       fill=th["text"], font=("Segoe UI Semibold",32,"bold"))

        desc = d.get("desc","")[:14]
        cv.create_text(54, 155, text=desc,
                       fill=th["sub"], font=("Segoe UI",9))

        cv.create_line(118, 20, 118, H-20, fill=th["sub"], width=1)

        city_disp = d["city"][:18]
        cv.create_text(W//2+60, 22, text=city_disp,
                       fill=th["text"], font=("Segoe UI Semibold",11,"bold"),
                       anchor="center")

        date_str = datetime.now().strftime("%A, %b %d")
        cv.create_text(W//2+60, 38, text=date_str,
                       fill=th["sub"], font=("Segoe UI",8), anchor="center")

        fc_y  = 62
        fc_x0 = 128
        cw    = (W - fc_x0 - 10) // 5

        for i, day in enumerate(d["forecast"][:5]):
            x    = fc_x0 + cw*i + cw//2
            di,_ = wmo_info(day["code"])
            label = "Now" if i==0 else day["day"]
            cv.create_text(x, fc_y,    text=label,
                           fill=th["sub"] if i>0 else th["text"],
                           font=("Segoe UI",7,"bold" if i==0 else "normal"))
            cv.create_text(x, fc_y+16, text=di, font=("Segoe UI",13))
            cv.create_text(x, fc_y+34, text=f"{day['hi']}°",
                           fill=th["text"], font=("Segoe UI Semibold",9,"bold"))
            cv.create_text(x, fc_y+47, text=f"{day['lo']}°",
                           fill=th["sub"], font=("Segoe UI",8))

        strip_y = H - 36
        cv.create_line(128, strip_y-4, W-8, strip_y-4,
                       fill=th["sub"], width=1)

        stats = [
            ("💧", f"{d['humidity']}%"),
            ("💨", f"{d['wind']}km/h"),
            ("🌡", f"{d['feels']}°"),
        ]
        sw = (W - 128 - 10) // 3
        for i,(icon,val) in enumerate(stats):
            x = 128 + sw*i + sw//2
            cv.create_text(x, strip_y+2,  text=f"{icon} {val}",
                           fill=th["sub"], font=("Segoe UI",8))

        cv.create_text(W-14, 14, text="✖", fill=th["sub"],
                       font=("Segoe UI",9), tags="close")
        cv.create_text(W-30, 14, text="✎", fill=th["sub"],
                       font=("Segoe UI",9), tags="change")

        cv.create_text(8, H-6, text=f"↻ {d['updated']}",
                       fill=th["sub"], font=("Segoe UI",7), anchor="w")

        cv.tag_bind("close","<Button-1>",lambda e:self._quit())
        cv.tag_bind("change","<Button-1>",lambda e:self._ask_city())

    def _ask_city(self):
        self.root.attributes("-topmost", True)
        dlg  = CityDialog(self.root, self.city)
        city = dlg.ask()
        self.root.attributes("-topmost", False)
        if city:
            self.city = city
            CITY_PATH.write_text(city)
            self.data = None
            self._draw_loading()
            threading.Thread(target=self._bg_fetch, daemon=True).start()

    def _quit(self):
        try: PID_PATH.unlink(missing_ok=True)
        except: pass
        self.root.destroy(); sys.exit(0)

    def _press(self, e): self._dx,self._dy = e.x,e.y
    def _move(self, e):
        self.root.geometry(
            f"+{self.root.winfo_x()+e.x-self._dx}+{self.root.winfo_y()+e.y-self._dy}")

if __name__ == "__main__":
    WeatherWidget()
