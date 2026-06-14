# Shutdown Scheduler

A lightweight Windows system-tray app that automatically shuts down your PC at a
scheduled time each day. Before the shutdown fires, it shows a warning dialog so
you can cancel or extend the countdown.

## Features

- **Daily scheduled shutdown** at a configurable time (24-hour `HH:MM`).
- **System-tray control** — runs quietly in the background; right-click the tray
  icon to open settings, toggle the schedule on/off, or quit.
- **Pre-shutdown warning dialog** with a live countdown and one-click
  **Cancel** or **Extend** actions.
- **Master enable/disable toggle** so you can arm or disarm the schedule without
  losing your configured time.
- **Atomic JSON settings** persisted to `%APPDATA%\WindowsShutdownScheduler\config.json`,
  with safe fallback to defaults on first run or corruption.
- **Low overhead** — a single background thread ticks every 30 seconds.

## How it works

The app starts hidden and lives entirely in the system tray:

- A background **scheduler** thread computes the next shutdown time and ticks
  every 30 seconds. When the current time is within the warning window it raises
  the warning dialog exactly once; at the scheduled time it triggers shutdown.
- The **warning dialog** lets you cancel the pending shutdown (skips to the next
  day) or extend it by a configurable number of minutes.
- Shutdown is performed via Windows' `shutdown /s /f /t 0`, which forces a clean
  immediate shutdown.

All Tk UI work happens on the main thread; the scheduler and tray run on their
own daemon threads and marshal UI updates back via `root.after(...)`.

## Requirements

- Windows
- Python 3.10+
- Dependencies (see `requirements.txt`):
  - [`pystray`](https://pypi.org/project/pystray/) — system-tray icon
  - [`Pillow`](https://pypi.org/project/Pillow/) — tray icon rendering

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run in the background without a console window:

```bash
pythonw main.py
```

Or run with a console (useful for debugging):

```bash
python main.py
```

Start minimized to the tray (skip opening the settings window):

```bash
pythonw main.py --minimized
```

### Configuration

Open the settings window from the tray icon to set:

| Setting            | Default | Description                                       |
| ------------------ | ------- | ------------------------------------------------- |
| Enable schedule    | off     | Master toggle to arm/disarm scheduled shutdown.   |
| Shutdown time      | 17:30   | Daily shutdown time in 24-hour format.            |
| Warning minutes    | 5       | How long before shutdown the warning appears.     |
| Extension minutes  | 10      | How long the "Extend" button pushes shutdown back.|

## Building a standalone executable

A [PyInstaller](https://pyinstaller.org/) spec file (`ShutdownScheduler.spec`) is
included to build a windowed (no-console) executable:

```bash
pip install pyinstaller
pyinstaller ShutdownScheduler.spec
```

The bundled app is written to `dist/ShutdownScheduler/`.

## Project structure

```
main.py                          Entry point
requirements.txt                 Runtime dependencies
ShutdownScheduler.spec           PyInstaller build spec
shutdown_scheduler/
    app.py                       Composition root; owns app lifetime & threading
    config.py                    Settings model + atomic JSON persistence
    scheduler.py                 Background tick loop / shutdown timing logic
    shutdown_service.py          Windows shutdown.exe wrapper
    tray.py                      System-tray icon and menu
    ui.py                        Settings window
    notification.py              Pre-shutdown warning dialog
    icon.py                      Tray icon rendering
```

## License

MIT
