# Shutdown Scheduler

A lightweight Windows system-tray app that automatically shuts down your PC at a
scheduled time each day. Before the shutdown fires, it shows a warning dialog so
you can cancel or extend the countdown.

## Features

- **Native Windows 11 look** — a genuine Fluent / WinUI 3 interface built on
  PySide6 + QFluentWidgets: Mica backdrops, rounded setting cards, real toggle
  switches, and a Fluent tray flyout. It **automatically follows the OS
  light/dark theme** and picks up your **Windows accent color**.
- **Daily scheduled shutdown** at a configurable time, picked in a familiar
  **12-hour clock with AM/PM**.
- **Start with Windows** — an in-app toggle that registers the app to launch
  (minimized to the tray) at sign-in, via the per-user registry `Run` key (no
  administrator rights required).
- **System-tray control** — runs quietly in the background; the tray flyout
  shows the next scheduled shutdown and lets you open settings or quit
  (left-click the icon to open settings directly).
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

All Qt UI work happens on the main thread. The scheduler runs on its own daemon
thread and marshals UI updates back to the GUI thread via queued Qt signals; the
tray icon lives on the GUI thread.

## Requirements

- Windows
- Python 3.10+
- Dependencies (see `requirements.txt`):
  - [`PySide6`](https://pypi.org/project/PySide6/) — Qt 6 GUI toolkit
  - [`PySide6-Fluent-Widgets`](https://pypi.org/project/PySide6-Fluent-Widgets/) —
    Fluent / WinUI 3 widgets, theming, and the system-tray flyout

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

| Setting            | Default  | Description                                       |
| ------------------ | -------- | ------------------------------------------------- |
| Enable schedule    | off      | Master toggle to arm/disarm scheduled shutdown.   |
| Start with Windows | off      | Launch the app (in the tray) automatically at sign-in. |
| Shutdown time      | 5:30 PM  | Daily shutdown time (12-hour clock with AM/PM).   |
| Warning minutes    | 5        | How long before shutdown the warning appears (1–60).   |
| Extension minutes  | 10       | How long the "Extend" button pushes shutdown back (1–180).|

The shutdown time is shown in the UI on a 12-hour clock; it is stored
internally in 24-hour form so the configuration file stays unambiguous.

## Building a standalone executable

A [PyInstaller](https://pyinstaller.org/) spec file (`ShutdownScheduler.spec`) is
included to build a windowed (no-console) executable.

### One-folder build (recommended)

The included spec uses `COLLECT`, which produces a **one-folder** build: a
directory containing `ShutdownScheduler.exe` alongside its dependencies. This
starts faster than a one-file build and is the default:

```bash
pip install pyinstaller
pyinstaller ShutdownScheduler.spec
```

The bundled app is written to `dist/ShutdownScheduler/`. Run it via
`dist/ShutdownScheduler/ShutdownScheduler.exe`, and distribute the whole
`ShutdownScheduler` folder (the `.exe` needs the sibling files to run).

Using the spec file is recommended because it collects the QFluentWidgets and
qframelesswindow data files (stylesheets, icons, fonts) the themed UI needs at
runtime. If you build straight from `main.py`, pass those collection flags
yourself:

```bash
pyinstaller --windowed --onedir --name ShutdownScheduler \
  --collect-all qfluentwidgets --collect-all qframelesswindow main.py
```

(`--onedir` is PyInstaller's default, so it can be omitted.)

### One-file build (single .exe)

To instead produce a single self-contained `dist/ShutdownScheduler.exe` (slower
to start, since it unpacks to a temp dir on each launch):

```bash
pyinstaller --windowed --onefile --name ShutdownScheduler \
  --collect-all qfluentwidgets --collect-all qframelesswindow main.py
```

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
    autostart.py                 Launch-at-sign-in via the registry Run key
    theme.py                     Fluent theming, accent color + OS light/dark following
    timefmt.py                   12-hour ⇄ 24-hour time conversion helpers
    tray.py                      System-tray icon and Fluent flyout menu
    ui.py                        Settings window (Fluent)
    notification.py              Pre-shutdown warning dialog (Fluent)
    icon.py                      Tray / window icon rendering (Qt)
```

## License

ShutdownScheduler is released under the **GNU General Public License v3.0**. See the [`LICENSE`](LICENSE) file for the full text.

```text
SPDX-License-Identifier: GPL-3.0-only
```

GPL-3.0 is a strong copyleft license: you are free to use, study, share, and modify ShutdownScheduler, but **any distributed derivative must also be released under GPL-3.0 with source available, and must preserve attribution.** It cannot be incorporated into closed-source/proprietary software.

```text
ShutdownScheduler — Windows system-tray app that automatically shuts down your PC at a
scheduled time each day.
Copyright (C) 2026 Md. Rifat Hasan Jihan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```