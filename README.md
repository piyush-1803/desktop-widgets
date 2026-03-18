# 🖥️ Desktop Widgets Suite

A personal productivity system built in Python — designed to sit on your desktop and keep you focused, aware, and on track.

Built and launched on **18th March 2026** as part of a personal transformation project at the start of a new chapter.

---

## 🧩 What's Inside

| Widget | File | Description |
|---|---|---|
| Widget Host | `widget_host.py` | Master controller that manages all widgets |
| Weather Widget | `weather_widget.py` | Live local weather display |
| Screen Time Tracker | `screentime_widget.py` | Tracks daily screen usage in real time |
| Task Timer | `task_timer.py` | Focus timer tied to your task list |
| Clock | `widgets/clock.html` | Minimal HTML clock widget |
| Settings | `settings.py` | Central settings panel for all widgets |
| Startup Manager | `add_startup.py` | Adds the suite to Windows startup |
| Launcher | `launcher_master.py` | Single entry point to launch everything |

---

## ⚙️ Tech Stack

- **Python 3.13** — core language
- **Tkinter** — GUI framework for all widgets
- **HTML/CSS** — clock widget
- **JSON** — config and data storage (`config.json`, `tasks.json`, `screentime_data.json`)
- **PyInstaller** — compiled to `.exe` for standalone use

---

## 🚀 How to Run

### Option 1 — Run from source

Make sure Python 3.x is installed, then:

```bash
git clone https://github.com/piyush-1803/desktop-widgets.git
cd desktop-widgets
python widget_host.py
```

### Option 2 — Launch everything at once

```bash
python launcher_master.py
```

### Option 3 — Add to Windows startup

```bash
python add_startup.py
```

---

## 📁 Project Structure

```
DesktopWidgets/
├── widget_host.py          # Master widget controller
├── launcher_master.py      # Single launch entry point
├── screentime_widget.py    # Screen time tracker
├── weather_widget.py       # Weather display
├── task_timer.py           # Focus/task timer
├── settings.py             # Settings panel
├── add_startup.py          # Windows startup manager
├── build.py                # Build script (PyInstaller)
├── config.json             # Global configuration
├── tasks.json              # Task list data
├── screentime_data.json    # Screen time history
├── weather_city.txt        # Saved city for weather
└── widgets/
    └── clock.html          # HTML clock widget
```

---

## 👨‍💻 Author

**Piyush** — [@piyush-1803](https://github.com/piyush-1803)

> *"The best time to start was yesterday. The second best time is today."*

---

## 📌 Status

🟢 Active — being improved as part of ongoing learning in Python and software development.
