"""
DesktopWidgets - Final Build Script
Packages everything into a single installer exe
"""
import subprocess, sys, glob
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent
DIST_DIR  = BASE_DIR / "dist"
BUILD_TMP = BASE_DIR / "build_tmp"
DIST_DIR.mkdir(exist_ok=True)
BUILD_TMP.mkdir(exist_ok=True)

PYINSTALLER = Path(sys.executable).parent / "Scripts" / "pyinstaller.exe"
if not PYINSTALLER.exists():
    results = glob.glob(str(Path.home() /
        "AppData/Local/Packages/*Python*3.13*/LocalCache/local-packages/Python313/Scripts/pyinstaller.exe"))
    if results:
        PYINSTALLER = Path(results[0])

print(f"PyInstaller: {PYINSTALLER}")

WIDGET_SCRIPTS = [
    "widget_host.py", "weather_widget.py",
    "task_timer.py",  "screentime_widget.py", "settings.py",
]

def build_widget(script):
    name = Path(script).stem
    print(f"  Building {name}...")
    cmd = [
        str(PYINSTALLER), "--onefile", "--noconsole", "--clean",
        f"--name={name}", f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_TMP / name}", f"--specpath={BUILD_TMP}",
        "--hidden-import=win32api", "--hidden-import=win32con",
        "--hidden-import=win32gui", "--hidden-import=win32process",
        "--hidden-import=psutil", "--hidden-import=winreg", script,
    ]
    r = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"  {'OK' if ok else 'FAIL'}: {name}.exe")
    return ok

def build_launcher():
    print("  Building master launcher...")
    add_data = []
    for script in WIDGET_SCRIPTS:
        exe = DIST_DIR / f"{Path(script).stem}.exe"
        if exe.exists():
            add_data += [f"--add-data={exe};."]
    widgets_dir = BASE_DIR / "widgets"
    if widgets_dir.exists():
        add_data += [f"--add-data={widgets_dir};widgets"]
    cmd = [
        str(PYINSTALLER), "--onefile", "--noconsole", "--clean",
        "--name=DesktopWidgets_Setup",
        f"--distpath={DIST_DIR}", f"--workpath={BUILD_TMP / 'launcher'}",
        f"--specpath={BUILD_TMP}",
        "--hidden-import=win32api", "--hidden-import=win32con",
        "--hidden-import=win32gui", "--hidden-import=win32process",
        "--hidden-import=psutil", "--hidden-import=winreg",
        *add_data,
        str(BASE_DIR / "launcher_master.py"),
    ]
    r = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    ok = r.returncode == 0
    print(f"  {'OK' if ok else 'FAIL'}: DesktopWidgets_Setup.exe")
    if not ok:
        print(r.stdout[-800:]); print(r.stderr[-400:])
    return ok

print("\nDesktopWidgets Build System")
print("="*50)
print("Step 1: Building widgets...")
for s in WIDGET_SCRIPTS:
    build_widget(s)
print("\nStep 2: Building master installer...")
build_launcher()
final = DIST_DIR / "DesktopWidgets_Setup.exe"
if final.exists():
    size = final.stat().st_size // (1024*1024)
    print(f"\nDONE: dist/DesktopWidgets_Setup.exe ({size} MB)")
else:
    print("\nBuild failed")
