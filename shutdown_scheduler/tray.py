# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

from __future__ import annotations

import threading
from typing import Callable, Optional

import pystray
from pystray import MenuItem

from .config import APP_NAME, Settings
from .icon import create_tray_image


class TrayController:
    """System tray icon. Runs pystray on its own thread so the main thread is
    free for tkinter's mainloop."""

    def __init__(
        self,
        settings_provider: Callable[[], Settings],
        on_open_settings: Callable[[], None],
        on_toggle_enabled: Callable[[], None],
        on_quit: Callable[[], None],
        status_provider: Callable[[], str],
    ) -> None:
        self._get_settings = settings_provider
        self._on_open = on_open_settings
        self._on_toggle = on_toggle_enabled
        self._on_quit = on_quit
        self._status = status_provider
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._icon = pystray.Icon(
            APP_NAME,
            icon=create_tray_image(self._get_settings().enabled),
            title=self._tooltip(),
            menu=self._build_menu(),
        )
        self._thread = threading.Thread(target=self._icon.run, name="tray", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass

    def refresh(self) -> None:
        """Re-render icon, tooltip, and menu (call after settings/status change)."""
        if self._icon is None:
            return
        try:
            self._icon.icon = create_tray_image(self._get_settings().enabled)
            self._icon.title = self._tooltip()
            self._icon.menu = self._build_menu()
            self._icon.update_menu()
        except Exception:
            pass

    # ---------- menu wiring ----------

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            MenuItem("Open Settings", self._handle_open, default=True),
            MenuItem(
                "Enabled",
                self._handle_toggle,
                checked=lambda _item: self._get_settings().enabled,
            ),
            pystray.Menu.SEPARATOR,
            MenuItem(lambda _item: self._status(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            MenuItem("Quit", self._handle_quit),
        )

    def _tooltip(self) -> str:
        return f"{APP_NAME} — {self._status()}"

    def _handle_open(self, _icon, _item) -> None:
        self._on_open()

    def _handle_toggle(self, _icon, _item) -> None:
        self._on_toggle()

    def _handle_quit(self, _icon, _item) -> None:
        self._on_quit()
