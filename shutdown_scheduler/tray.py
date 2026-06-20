# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

"""System tray icon with a modern Fluent flyout menu.

Uses Qt's ``QSystemTrayIcon`` for the notification-area icon and QFluentWidgets'
``SystemTrayMenu`` for the right-click flyout, so the menu gets rounded corners,
Fluent icons, hover states and automatic light/dark theming — matching the rest
of the app. Lives entirely on the GUI thread.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QSystemTrayIcon

from qfluentwidgets import Action, FluentIcon as FIF, SystemTrayMenu

from .config import APP_NAME, Settings
from .icon import create_icon


class TrayController(QObject):
    """The notification-area icon and its Fluent context menu."""

    def __init__(
        self,
        settings_provider: Callable[[], Settings],
        on_open_settings: Callable[[], None],
        on_quit: Callable[[], None],
        status_provider: Callable[[], str],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._get_settings = settings_provider
        self._on_open = on_open_settings
        self._on_quit = on_quit
        self._status = status_provider

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(create_icon(self._get_settings().enabled))
        self._tray.setToolTip(self._tooltip())
        self._tray.activated.connect(self._on_activated)
        self._tray.setContextMenu(self._build_menu())

    def start(self) -> None:
        self._tray.show()

    def stop(self) -> None:
        self._tray.hide()

    def refresh(self) -> None:
        """Re-render icon, tooltip and menu after a settings/status change."""
        self._tray.setIcon(create_icon(self._get_settings().enabled))
        self._tray.setToolTip(self._tooltip())
        # Rebuild the menu so the status line reflects new state.
        old = self._tray.contextMenu()
        self._tray.setContextMenu(self._build_menu())
        if old is not None:
            old.deleteLater()

    # ---------- menu ----------

    def _build_menu(self) -> SystemTrayMenu:
        menu = SystemTrayMenu()

        open_action = Action(FIF.SETTING, "Open settings", self)
        open_action.triggered.connect(lambda: self._on_open())
        menu.addAction(open_action)

        menu.addSeparator()

        status_action = Action(self._status(), self)
        status_action.setEnabled(False)
        menu.addAction(status_action)

        menu.addSeparator()

        quit_action = Action(FIF.CLOSE, "Quit", self)
        quit_action.triggered.connect(lambda: self._on_quit())
        menu.addAction(quit_action)

        return menu

    def _tooltip(self) -> str:
        return f"{APP_NAME} — {self._status()}"

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._on_open()
