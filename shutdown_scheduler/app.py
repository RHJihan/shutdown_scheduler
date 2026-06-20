# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

from __future__ import annotations

import sys
import threading
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from .autostart import AutoStartService, default_autostart_service
from .config import JsonSettingsRepository, Settings, SettingsRepository
from .icon import app_icon
from .notification import WarningDialog
from .scheduler import SchedulerCallbacks, SchedulerService
from .shutdown_service import ShutdownService, WindowsShutdownService
from .theme import ThemeManager
from .timefmt import format_dt_12h
from .tray import TrayController
from .ui import SettingsWindow


class _SchedulerBridge(QObject):
    """Marshals scheduler callbacks (fired on the scheduler thread) onto the GUI
    thread via queued signal connections."""

    warning = Signal(object)  # datetime
    shutdown = Signal()
    statusChanged = Signal()


class Application:
    """Composition root. Owns lifetime of all collaborators.

    Threading model:
      - Main thread runs the Qt event loop.
      - Scheduler runs on its own daemon thread; it touches the UI only by
        emitting ``_SchedulerBridge`` signals, which Qt delivers (queued) on the
        GUI thread.
      - The tray icon lives on the GUI thread (Qt's QSystemTrayIcon).
    """

    def __init__(
        self,
        start_minimized: bool = False,
        repository: Optional[SettingsRepository] = None,
        shutdown_service: Optional[ShutdownService] = None,
        autostart_service: Optional[AutoStartService] = None,
    ) -> None:
        self._start_minimized = start_minimized
        self._repo: SettingsRepository = repository or JsonSettingsRepository()
        self._shutdown_service: ShutdownService = shutdown_service or WindowsShutdownService()
        self._autostart: AutoStartService = autostart_service or default_autostart_service()

        self._settings_lock = threading.RLock()
        self._settings: Settings = self._repo.load()

        self._qt: Optional[QApplication] = None
        self._theme: Optional[ThemeManager] = None
        self._bridge: Optional[_SchedulerBridge] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._scheduler = SchedulerService(
            settings_provider=self._get_settings,
            callbacks=SchedulerCallbacks(
                on_warning=self._on_warning,
                on_shutdown=self._on_shutdown,
                on_status_change=self._on_status_change,
            ),
        )
        self._tray: Optional[TrayController] = None

    # ============ public ============

    def run(self) -> None:
        self._qt = QApplication(sys.argv)
        # Pin a point-sized base font (Segoe UI Variable is the Windows 11 system
        # font; Segoe UI is the universal fallback). Some Windows sessions hand Qt
        # a pixel-sized default font whose pointSize() is -1, which makes Qt emit
        # "QFont::setPointSize: Point size <= 0" warnings; a positive point size
        # avoids that and keeps typography consistent.
        base_font = QFont()
        base_font.setFamilies(["Segoe UI Variable", "Segoe UI"])
        base_font.setPointSize(9)
        self._qt.setFont(base_font)
        # The app lives in the tray; closing the settings window must not quit.
        self._qt.setQuitOnLastWindowClosed(False)
        self._qt.setWindowIcon(app_icon())

        # Apply the Fluent theme + Windows accent, and follow the OS light/dark.
        self._theme = ThemeManager()
        self._theme.apply()
        self._theme.start_following_os()

        self._bridge = _SchedulerBridge()
        self._bridge.warning.connect(self._show_warning)
        self._bridge.shutdown.connect(self._do_shutdown)
        self._bridge.statusChanged.connect(self._on_status_change_main)

        self._settings_window = SettingsWindow(
            settings_provider=self._get_settings,
            on_save=self._handle_settings_save,
            next_shutdown_provider=lambda: self._scheduler.next_at,
        )

        self._tray = TrayController(
            settings_provider=self._get_settings,
            on_open_settings=self._open_settings,
            on_quit=self._shutdown_app,
            status_provider=self._status_text,
        )
        # Repaint the tray icon whenever the OS theme flips.
        self._theme.themeChanged.connect(lambda _dark: self._tray.refresh())

        # Reconcile the OS auto-start entry with the saved preference (also
        # refreshes the stored launch path in case the app was moved).
        try:
            self._autostart.apply(self._get_settings().start_with_windows)
        except Exception:
            pass  # Auto-start is best-effort; never block app launch.

        self._scheduler.start()
        self._tray.start()

        if not self._start_minimized:
            self._open_settings()

        try:
            self._qt.exec()
        finally:
            self._scheduler.stop()
            self._theme.stop()

    # ============ settings flow ============

    def _get_settings(self) -> Settings:
        with self._settings_lock:
            return self._settings

    def _handle_settings_save(self, new_settings: Settings) -> None:
        with self._settings_lock:
            self._repo.save(new_settings)
            self._settings = new_settings

        try:
            self._autostart.apply(new_settings.start_with_windows)
        except Exception:
            pass  # Persisted regardless; auto-start is best-effort.

        self._scheduler.reschedule()
        if self._tray:
            self._tray.refresh()
        if self._settings_window:
            self._settings_window.refresh_status()

    # ============ scheduler callbacks (called off the main thread) ============

    def _on_warning(self, shutdown_at: datetime) -> None:
        if self._bridge is not None:
            self._bridge.warning.emit(shutdown_at)

    def _on_shutdown(self) -> None:
        if self._bridge is not None:
            self._bridge.shutdown.emit()

    def _on_status_change(self) -> None:
        if self._bridge is not None:
            self._bridge.statusChanged.emit()

    # ============ main-thread handlers ============

    def _on_status_change_main(self) -> None:
        if self._tray:
            self._tray.refresh()
        if self._settings_window:
            self._settings_window.refresh_status()

    def _show_warning(self, shutdown_at: datetime) -> None:
        dialog = WarningDialog(
            shutdown_at=shutdown_at,
            extension_minutes=self._get_settings().extension_minutes,
            on_cancel=self._scheduler.cancel_current,
            on_extend=self._scheduler.extend_current,
        )
        # Keep a reference so it isn't garbage-collected while shown.
        self._warning_dialog = dialog
        dialog.show_dialog()

    def _do_shutdown(self) -> None:
        try:
            self._shutdown_service.shutdown_now()
        finally:
            # Advance the schedule so a stale state doesn't re-fire if shutdown
            # is aborted by the OS for some reason.
            self._scheduler.cancel_current()

    # ============ tray handlers ============

    def _open_settings(self) -> None:
        if self._settings_window:
            self._settings_window.show_window()

    def _shutdown_app(self) -> None:
        self._scheduler.stop()
        if self._theme:
            self._theme.stop()
        if self._tray:
            self._tray.stop()
        if self._qt is not None:
            self._qt.quit()

    # ============ status text ============

    def _status_text(self) -> str:
        s = self._get_settings()
        if not s.enabled:
            return "Disabled"
        nxt = self._scheduler.next_at
        if nxt is None:
            return "Enabled"
        return f"Next: {format_dt_12h(nxt, with_day=True)}"
