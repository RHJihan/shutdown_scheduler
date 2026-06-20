# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

"""Launch-at-startup management.

Uses the per-user ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run``
registry key, which runs the app at sign-in and needs no administrator rights.
The stored command launches the app minimized so it goes straight to the tray.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional, Protocol

from .config import APP_NAME

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


class AutoStartService(Protocol):
    def is_enabled(self) -> bool: ...
    def apply(self, enabled: bool) -> None: ...


def _launch_command() -> str:
    """Build the command Windows should run at sign-in.

    Frozen (PyInstaller) builds launch the executable directly; source runs use
    ``pythonw.exe`` (no console window) with the entry script. Either way we
    pass ``--minimized`` so the app starts hidden in the tray.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else exe
    script = os.path.abspath(sys.argv[0])
    return f'"{runner}" "{script}" --minimized'


class WindowsAutoStartService:
    """Reads/writes the per-user Run key entry for this app."""

    def __init__(self, name: str = APP_NAME, command: Optional[str] = None) -> None:
        self._name = name
        self._command = command or _launch_command()

    def is_enabled(self) -> bool:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, self._name)
                return bool(value)
        except OSError:
            # Key or value absent (FileNotFoundError) — not registered.
            return False

    def apply(self, enabled: bool) -> None:
        """Make the registry match the desired state (idempotent)."""
        if enabled:
            self._register()
        else:
            self._unregister()

    def _register(self) -> None:
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.SetValueEx(key, self._name, 0, winreg.REG_SZ, self._command)

    def _unregister(self) -> None:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, self._name)
        except OSError:
            pass  # Already absent.


class NullAutoStartService:
    """No-op fallback for non-Windows platforms (or when disabled by injection)."""

    def is_enabled(self) -> bool:
        return False

    def apply(self, enabled: bool) -> None:
        pass


def default_autostart_service() -> AutoStartService:
    if sys.platform.startswith("win"):
        return WindowsAutoStartService()
    return NullAutoStartService()
