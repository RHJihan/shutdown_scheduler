# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

"""Theming for the Qt UI.

The UI is built on PySide6 + QFluentWidgets, which renders a genuine Windows 11
(WinUI 3 / Fluent) look — Mica backdrops, themed cards, real toggle switches and
correct light/dark surfaces. This module is thin: it picks up the user's Windows
accent color, applies the ``AUTO`` theme (which follows the OS), and live-tracks
OS light/dark changes so every window repaints instantly.

All Qt work happens on the GUI thread. ``SystemThemeListener`` runs on its own
QThread and emits a queued signal, so the re-apply lands on the GUI thread.
"""
from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from qfluentwidgets import (
    SystemThemeListener,
    Theme,
    isDarkTheme,
    setTheme,
    setThemeColor,
)

# Windows 11 default accent (used when the system accent can't be read).
_DEFAULT_ACCENT = "#0067C0"


def system_accent_color() -> QColor:
    """Return the user's Windows accent color, falling back to the Win11 default.

    Reads ``HKCU\\Software\\Microsoft\\Windows\\DWM\\AccentColor``, a DWORD stored
    as ``0xAABBGGRR``. Matching the OS accent is what makes the app feel native.
    """
    if sys.platform.startswith("win"):
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM"
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AccentColor")
            r = value & 0xFF
            g = (value >> 8) & 0xFF
            b = (value >> 16) & 0xFF
            return QColor(r, g, b)
        except OSError:
            pass
    return QColor(_DEFAULT_ACCENT)


class ThemeManager(QObject):
    """Owns the application theme.

    - Applies the Windows accent color and the ``AUTO`` (follow-OS) theme.
    - Live-tracks OS light/dark changes and re-applies, repainting all windows.
    - Emits :attr:`themeChanged` (with ``is_dark``) so non-Qt-styled surfaces —
      e.g. the tray icon — can repaint to match.
    """

    themeChanged = Signal(bool)  # is_dark

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._listener: Optional[SystemThemeListener] = None

    @property
    def is_dark(self) -> bool:
        return isDarkTheme()

    def apply(self) -> None:
        """Apply the accent + follow-OS theme. Call once at startup."""
        setThemeColor(system_accent_color(), lazy=True)
        setTheme(Theme.AUTO, lazy=False)

    def start_following_os(self) -> None:
        """Begin live-tracking OS light/dark changes."""
        if self._listener is not None:
            return
        self._listener = SystemThemeListener(self)
        self._listener.systemThemeChanged.connect(self._on_os_change)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.terminate()
                self._listener.deleteLater()
            except Exception:
                pass
            self._listener = None

    # ---------- internal ----------

    def _on_os_change(self) -> None:
        # Re-applying AUTO re-reads the OS mode and repaints every styled widget;
        # also refresh the accent in case the user changed it.
        setThemeColor(system_accent_color(), lazy=True)
        setTheme(Theme.AUTO, lazy=False)
        self.themeChanged.emit(isDarkTheme())
