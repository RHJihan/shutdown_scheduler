from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from typing import Optional

from .config import JsonSettingsRepository, Settings, SettingsRepository
from .notification import WarningDialog
from .scheduler import SchedulerCallbacks, SchedulerService
from .shutdown_service import ShutdownService, WindowsShutdownService
from .tray import TrayController
from .ui import SettingsWindow


class Application:
    """Composition root. Owns lifetime of all collaborators.

    Threading model:
      - Main thread runs tkinter mainloop with a hidden root window.
      - Scheduler runs on its own daemon thread; touches UI only through
        `root.after(0, ...)` so all Tk work stays on the main thread.
      - pystray runs on its own daemon thread.
    """

    def __init__(
        self,
        start_minimized: bool = False,
        repository: Optional[SettingsRepository] = None,
        shutdown_service: Optional[ShutdownService] = None,
    ) -> None:
        self._start_minimized = start_minimized
        self._repo: SettingsRepository = repository or JsonSettingsRepository()
        self._shutdown_service: ShutdownService = shutdown_service or WindowsShutdownService()

        self._settings_lock = threading.RLock()
        self._settings: Settings = self._repo.load()

        self._root: Optional[tk.Tk] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._scheduler = SchedulerService(
            settings_provider=self._get_settings,
            callbacks=SchedulerCallbacks(
                on_warning=self._on_warning,
                on_shutdown=self._on_shutdown,
                on_status_change=self._on_status_change,
            ),
        )
        self._tray = TrayController(
            settings_provider=self._get_settings,
            on_open_settings=self._open_settings_from_tray,
            on_toggle_enabled=self._toggle_enabled_from_tray,
            on_quit=self._quit_from_tray,
            status_provider=self._status_text,
        )

    # ============ public ============

    def run(self) -> None:
        self._root = tk.Tk()
        self._root.withdraw()  # always start hidden; tray is the entry point.
        # If main window closes, fall back to "stop everything" — but settings
        # is a Toplevel so it won't reach this root by default.
        self._root.protocol("WM_DELETE_WINDOW", self._shutdown_app)

        self._settings_window = SettingsWindow(
            root=self._root,
            settings_provider=self._get_settings,
            on_save=self._handle_settings_save,
            next_shutdown_provider=lambda: self._scheduler.next_at,
        )

        self._scheduler.start()
        self._tray.start()

        if not self._start_minimized:
            self._root.after(50, self._settings_window.show)

        try:
            self._root.mainloop()
        finally:
            self._scheduler.stop()
            self._tray.stop()

    # ============ settings flow ============

    def _get_settings(self) -> Settings:
        with self._settings_lock:
            return self._settings

    def _handle_settings_save(self, new_settings: Settings) -> None:
        with self._settings_lock:
            self._repo.save(new_settings)
            self._settings = new_settings

        self._scheduler.reschedule()
        self._tray.refresh()
        if self._settings_window:
            self._settings_window.refresh_status()

    # ============ scheduler callbacks (called off main thread) ============

    def _on_warning(self, shutdown_at: datetime) -> None:
        if self._root is None:
            return
        self._root.after(0, lambda: self._show_warning(shutdown_at))

    def _on_shutdown(self) -> None:
        # Execute on main thread to keep ordering predictable.
        if self._root is None:
            return
        self._root.after(0, self._do_shutdown)

    def _on_status_change(self) -> None:
        if self._root is None:
            return
        self._root.after(0, self._tray.refresh)
        if self._settings_window:
            self._root.after(0, self._settings_window.refresh_status)

    # ============ main-thread handlers ============

    def _show_warning(self, shutdown_at: datetime) -> None:
        assert self._root is not None
        dialog = WarningDialog(
            root=self._root,
            shutdown_at=shutdown_at,
            extension_minutes=self._get_settings().extension_minutes,
            on_cancel=self._scheduler.cancel_current,
            on_extend=self._scheduler.extend_current,
        )
        dialog.show()

    def _do_shutdown(self) -> None:
        try:
            self._shutdown_service.shutdown_now()
        finally:
            # Advance the schedule so a stale state doesn't re-fire if shutdown is
            # aborted by the OS for some reason.
            self._scheduler.cancel_current()

    # ============ tray handlers ============

    def _open_settings_from_tray(self) -> None:
        if self._root and self._settings_window:
            self._root.after(0, self._settings_window.show)

    def _toggle_enabled_from_tray(self) -> None:
        with self._settings_lock:
            new = self._settings.with_changes(enabled=not self._settings.enabled)
        self._handle_settings_save(new)

    def _quit_from_tray(self) -> None:
        if self._root is not None:
            self._root.after(0, self._shutdown_app)

    def _shutdown_app(self) -> None:
        self._scheduler.stop()
        self._tray.stop()
        if self._root is not None:
            try:
                self._root.destroy()
            except tk.TclError:
                pass

    # ============ status text ============

    def _status_text(self) -> str:
        s = self._get_settings()
        if not s.enabled:
            return "Disabled"
        nxt = self._scheduler.next_at
        if nxt is None:
            return "Enabled"
        return f"Next: {nxt.strftime('%a %H:%M')}"
