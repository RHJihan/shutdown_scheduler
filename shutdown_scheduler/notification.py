# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

"""Imminent-shutdown warning — a focused, always-on-top Fluent dialog.

Shows a live countdown plus Cancel / Extend actions. Built on the same
``FluentWidget`` base as the settings page so it shares the native Windows 11
look and correct light/dark theming. Closing it via the title bar takes no
action; the shutdown proceeds as scheduled.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from qfluentwidgets import (
    BodyLabel,
    CaptionLabel,
    DisplayLabel,
    FluentIcon as FIF,
    IconWidget,
    InfoBarIcon,
    PrimaryPushButton,
    PushButton,
    SubtitleLabel,
)
from qfluentwidgets.window.fluent_window import FluentWidget

from .icon import app_icon
from .timefmt import format_12h

_TITLE_BAR_H = 48
_MUTED_LIGHT = QColor(0, 0, 0, 150)
_MUTED_DARK = QColor(255, 255, 255, 150)


class WarningDialog(FluentWidget):
    """Always-on-top warning with a live countdown."""

    def __init__(
        self,
        shutdown_at: datetime,
        extension_minutes: int,
        on_cancel: Callable[[], None],
        on_extend: Callable[[], None],
    ) -> None:
        super().__init__()
        self._shutdown_at = shutdown_at
        self._extension_minutes = extension_minutes
        self._on_cancel = on_cancel
        self._on_extend = on_extend

        self.setWindowTitle("Shutdown imminent")
        self.setWindowIcon(app_icon())
        self.setFixedWidth(400)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.titleBar.minBtn.hide()
        self.titleBar.maxBtn.hide()

        # Clean solid Fluent surface (no Mica wallpaper bleed-through).
        self.setMicaEffectEnabled(False)
        self.setCustomBackgroundColor(QColor(243, 243, 243), QColor(32, 32, 32))

        self._build_ui()
        self.resize(self.sizeHint())

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def show_dialog(self) -> None:
        self._tick()
        self._center()
        self.show()
        self.raise_()
        self.activateWindow()
        self._timer.start()

    # ---------- construction ----------

    def _build_ui(self) -> None:
        body = QVBoxLayout(self)
        body.setContentsMargins(28, _TITLE_BAR_H + 12, 28, 28)
        body.setSpacing(0)

        heading = QHBoxLayout()
        heading.setSpacing(12)
        warn = IconWidget(InfoBarIcon.WARNING, self)
        warn.setFixedSize(24, 24)
        heading.addWidget(warn, 0, Qt.AlignVCenter)
        heading.addWidget(
            SubtitleLabel("Your PC will shut down soon"), 1, Qt.AlignVCenter
        )
        body.addLayout(heading)

        self._detail = CaptionLabel(
            f"Scheduled for "
            f"{format_12h(self._shutdown_at.hour, self._shutdown_at.minute)}."
        )
        self._detail.setTextColor(_MUTED_LIGHT, _MUTED_DARK)
        body.addSpacing(6)
        body.addWidget(self._detail)

        self._countdown = DisplayLabel("00:00")
        body.addSpacing(14)
        body.addWidget(self._countdown, 0, Qt.AlignHCenter)
        body.addSpacing(22)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        cancel = PushButton("Cancel shutdown")
        cancel.clicked.connect(self._cancel)
        extend = PrimaryPushButton(
            FIF.HISTORY, f"Extend {self._extension_minutes} min"
        )
        extend.clicked.connect(self._extend)
        buttons.addWidget(cancel, 1)
        buttons.addWidget(extend, 1)
        body.addLayout(buttons)

    # ---------- behavior ----------

    def _tick(self) -> None:
        remaining = self._shutdown_at - datetime.now()
        secs = max(0, int(remaining.total_seconds()))
        m, s = divmod(secs, 60)
        self._countdown.setText(f"{m:02d}:{s:02d}")
        if secs <= 0:
            self._close()

    def _cancel(self) -> None:
        self._close()
        self._on_cancel()

    def _extend(self) -> None:
        self._close()
        self._on_extend()

    def _close(self) -> None:
        self._timer.stop()
        self.close()
        self.deleteLater()

    def _center(self) -> None:
        handle = self.windowHandle()
        screen = self.screen() or (handle.screen() if handle else None)
        if screen is None:
            return
        geo = screen.availableGeometry()
        size = self.sizeHint()
        x = geo.x() + (geo.width() - size.width()) // 2
        y = geo.y() + (geo.height() - size.height()) // 3
        self.move(x, y)

    def closeEvent(self, e) -> None:
        # X = take no action; shutdown proceeds as scheduled.
        self._timer.stop()
        super().closeEvent(e)
