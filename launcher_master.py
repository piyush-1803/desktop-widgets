"""
DesktopWidgets Master Launcher
- First run: installs everything to C:\DesktopWidgets\
- Every run: starts all widgets silently
- System tray icon: right click to open Settings, restart, quit
"""
import sys, os, shutil, subprocess, time, winreg, threading
from pathlib import Path

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = Path(sys._MEIPASS)
    SELF_EXE   = Path(sys.executable)
else:
    BUNDLE_DIR = Path(__file__).resolve().parent / "dist"
    SELF_EXE   = Path(sys.executable)

INSTALL_DIR = Path("C:/DesktopWidgets")
APP_NAME    = "DesktopWidgets"

WIDGET_EXES = [
    "widget_host.exe",
    "weather_widget.exe",
    "task_timer.exe",
    "screentime_widget.exe",
]

def install():
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    (INSTALL_DIR / "widgets").mkdir(exist_ok=True)
    for name in WIDGET_EXES + ["settings.exe"]:
        src = BUNDLE_DIR / name
        dst = INSTALL_DIR / name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
    widgets_src = BUNDLE_DIR / "widgets"
    if widgets_src.exists():
        for f in widgets_src.iterdir():
            dst = INSTALL_DIR / "widgets" / f.name
            if not dst.exists():
                shutil.copy2(f, dst)
    dst_self = INSTALL_DIR / "DesktopWidgets_Setup.exe"
    if SELF_EXE.exists() and SELF_EXE != dst_self:
        shutil.copy2(SELF_EXE, dst_self)
    return dst_self

def register_startup(exe_path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
    except Exception as e:
        print(f"Startup reg error: {e}")

def start_widgets():
    for name in WIDGET_EXES:
        exe = INSTALL_DIR / name
        if exe.exists():
            subprocess.Popen([str(exe)],
                             creationflags=subprocess.CREATE_NO_WINDOW,
                             cwd=str(INSTALL_DIR))
            time.sleep(0.6)

def stop_widgets():
    for name in WIDGET_EXES:
        subprocess.run(["taskkill","/f","/im",name], capture_output=True)

def open_settings():
    s = INSTALL_DIR / "settings.exe"
    if s.exists():
        subprocess.Popen([str(s)], cwd=str(INSTALL_DIR))

def create_tray_image():
    """Create a simple icon image for the tray."""
    from PIL import Image, ImageDraw
    img  = Image.new("RGBA", (64,64), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    # Dark circle background
    draw.ellipse([2,2,62,62], fill="#161B22", outline="#58A6FF", width=3)
    # W letter
    draw.text((18,18), "W", fill="#58A6FF")
    return img

def run_tray():
    import pystray
    from pystray import MenuItem as Item, Menu

    icon_image = create_tray_image()

    def on_open_settings(icon, item):
        open_settings()

    def on_restart(icon, item):
        stop_widgets()
        time.sleep(1)
        threading.Thread(target=start_widgets, daemon=True).start()

    def on_quit(icon, item):
        stop_widgets()
        icon.stop()
        sys.exit(0)

    menu = Menu(
        Item("⚙  Open Settings",  on_open_settings, default=True),
        Menu.SEPARATOR,
        Item("↺  Restart Widgets", on_restart),
        Item("⏹  Stop All",        lambda icon,item: stop_widgets()),
        Item("▶  Start All",       lambda icon,item: threading.Thread(
                                       target=start_widgets, daemon=True).start()),
        Menu.SEPARATOR,
        Item("✕  Quit",            on_quit),
    )

    icon = pystray.Icon(
        APP_NAME,
        icon_image,
        "DesktopWidgets — Click to open Settings",
        menu
    )
    icon.run()

def show_welcome(is_first_run):
    """Show welcome popup on first run or after install."""
    import tkinter as tk

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#0D1117")

    W, H = 320, 300 if is_first_run else 240
    sw   = root.winfo_screenwidth()
    sh   = root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{sw-W-20}+{sh-H-60}")

    outer = tk.Frame(root, bg="#58A6FF", padx=1, pady=1)
    outer.pack(fill="both", expand=True)
    inner = tk.Frame(outer, bg="#0D1117")
    inner.pack(fill="both", expand=True, padx=1, pady=1)

    tk.Label(inner, text="⚙️  DesktopWidgets", fg="#FFFFFF", bg="#0D1117",
             font=("Segoe UI Semibold",14,"bold"), pady=14).pack()
    tk.Frame(inner, bg="#21262D", height=1).pack(fill="x")

    if is_first_run:
        for txt in ["✅  Installed to C:\\DesktopWidgets\\",
                    "✅  Added to Windows startup",
                    "✅  All widgets launching…"]:
            tk.Label(inner, text=txt, fg="#3FB950", bg="#0D1117",
                     font=("Segoe UI",10), pady=3).pack()
        tk.Label(inner,
                 text="Right-click the tray icon (▲) anytime\nto open Settings or manage widgets.",
                 fg="#8B949E", bg="#0D1117", font=("Segoe UI",9),
                 pady=10, justify="center").pack()
    else:
        tk.Label(inner, text="✅  All widgets started!",
                 fg="#3FB950", bg="#0D1117",
                 font=("Segoe UI",11), pady=10).pack()
        tk.Label(inner,
                 text="Right-click the tray icon (▲)\nto open Settings anytime.",
                 fg="#8B949E", bg="#0D1117", font=("Segoe UI",9),
                 pady=6, justify="center").pack()

    tk.Frame(inner, bg="#21262D", height=1).pack(fill="x")
    btn_row = tk.Frame(inner, bg="#0D1117"); btn_row.pack(pady=12)

    tk.Button(btn_row, text="⚙  Open Settings",
              bg="#58A6FF", fg="#000000", relief="flat",
              font=("Segoe UI",10,"bold"), padx=16, pady=7,
              cursor="hand2", command=lambda:[open_settings(), root.destroy()],
              activebackground="#79C0FF").pack(side="left", padx=(0,8))
    tk.Button(btn_row, text="✕  Close",
              bg="#21262D", fg="#8B949E", relief="flat",
              font=("Segoe UI",10), padx=16, pady=7,
              cursor="hand2", command=root.destroy,
              activebackground="#2D333B").pack(side="left")

    tk.Label(inner, text="v1.0  •  Tray icon (▲) always available",
             fg="#484F58", bg="#0D1117",
             font=("Segoe UI",7)).pack(side="bottom", pady=6)

    def drag_start(e): root._dx,root._dy = e.x,e.y
    def drag_move(e):
        root.geometry(f"+{root.winfo_x()+e.x-root._dx}+{root.winfo_y()+e.y-root._dy}")
    inner.bind("<ButtonPress-1>", drag_start)
    inner.bind("<B1-Motion>",     drag_move)

    root.after(12000, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    is_first = not (INSTALL_DIR / "widget_host.exe").exists()

    if is_first:
        self_path = install()
        register_startup(self_path)

    # Start widgets in background
    threading.Thread(target=start_widgets, daemon=True).start()

    # Show welcome popup
    threading.Thread(target=show_welcome, args=(is_first,), daemon=True).start()

    # Run tray icon (this blocks - keeps app alive)
    run_tray()
