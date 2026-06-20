# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

"""Settings window — a compact, native-feeling Windows 11 settings page.

Built on QFluentWidgets' ``FluentWidget`` (Mica backdrop, Fluent title bar,
correct light/dark surfaces). The body uses the same vocabulary as the Windows
Settings app: a page heading, grouped setting cards with icons, real toggle
switches, and a 12-hour time picker.

Pure presentation — all scheduling/persistence logic lives elsewhere and is
reached only through the injected callbacks.
"""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from PySide6.QtCore import QTime, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from qfluentwidgets import (
    AMTimePicker,
    BodyLabel,
    CaptionLabel,
    FluentIcon as FIF,
    IconWidget,
    InfoBar,
    InfoBarIcon,
    InfoBarPosition,
    PrimaryPushButton,
    PushButton,
    SpinBox,
    StrongBodyLabel,
    SwitchSettingCard,
    TitleLabel,
    isDarkTheme,
)
from qfluentwidgets.window.fluent_window import FluentWidget

from .config import Settings
from .icon import app_icon
from .timefmt import format_dt_12h

_TITLE_BAR_H = 48

# Fluent "text-secondary" — muted captions in light / dark.
_MUTED_LIGHT = QColor(0, 0, 0, 150)
_MUTED_DARK = QColor(255, 255, 255, 150)


def _muted(label: CaptionLabel) -> CaptionLabel:
    label.setTextColor(_MUTED_LIGHT, _MUTED_DARK)
    return label


class SettingsWindow(FluentWidget):
    """Single-page settings window. Hidden by default; opened from the tray."""

    def __init__(
        self,
        settings_provider: Callable[[], Settings],
        on_save: Callable[[Settings], None],
        next_shutdown_provider: Callable[[], Optional[datetime]],
    ) -> None:
        super().__init__()
        self._get_settings = settings_provider
        self._on_save = on_save
        self._get_next = next_shutdown_provider

        self.setWindowTitle("Shutdown Scheduler")
        self.setWindowIcon(app_icon())
        self.titleBar.maxBtn.hide()  # fixed-size page; no maximize.

        # Use a clean solid Fluent surface rather than Mica — Mica blends the
        # desktop wallpaper through the window, which can tint the background.
        self.setMicaEffectEnabled(False)
        self.setCustomBackgroundColor(QColor(243, 243, 243), QColor(32, 32, 32))

        # Theme-aware card chrome must be repainted on light/dark flips.
        self._card_restylers: list[Callable[[], None]] = []

        self._build_ui()
        self._load_from_settings()

        # Refresh the live status line once a minute while open.
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(60_000)
        self._status_timer.timeout.connect(self._refresh_status)

        self._sized = False
        self.setMinimumWidth(500)

    # ---------- public ----------

    def show_window(self) -> None:
        self._load_from_settings()
        self._refresh_status()
        self._center()
        self.show()
        self.raise_()
        self.activateWindow()
        self._status_timer.start()

    def refresh_status(self) -> None:
        if self.isVisible():
            self._refresh_status()

    # ---------- construction ----------

    def _build_ui(self) -> None:
        body = QVBoxLayout(self)
        body.setContentsMargins(24, _TITLE_BAR_H + 8, 24, 24)
        body.setSpacing(0)

        # --- Page heading ---
        body.addWidget(TitleLabel("Shutdown Scheduler"))
        body.addSpacing(2)
        body.addWidget(
            _muted(CaptionLabel(
                "Automatically power off your PC at the same time each day."
            ))
        )
        body.addSpacing(20)

        # --- General ---
        body.addWidget(StrongBodyLabel("General"))
        body.addSpacing(8)

        self._enabled_card = SwitchSettingCard(
            FIF.POWER_BUTTON,
            "Scheduled shutdown",
            "Off — schedule is disabled",
        )
        self._enabled_card.checkedChanged.connect(self._on_enabled_toggled)
        body.addWidget(self._enabled_card)
        body.addSpacing(6)

        self._autostart_card = SwitchSettingCard(
            FIF.PLAY,
            "Start with Windows",
            "Off — start it manually",
        )
        self._autostart_card.checkedChanged.connect(self._on_autostart_toggled)
        body.addWidget(self._autostart_card)
        body.addSpacing(20)

        # --- Schedule ---
        body.addWidget(StrongBodyLabel("Schedule"))
        body.addSpacing(8)
        body.addWidget(self._build_time_card())
        body.addSpacing(6)
        body.addWidget(self._build_warning_card())
        body.addSpacing(6)
        body.addWidget(self._build_extension_card())
        body.addSpacing(20)

        # --- Status + actions ---
        footer = QHBoxLayout()
        footer.setSpacing(8)
        self._status_icon = IconWidget(InfoBarIcon.INFORMATION, self)
        self._status_icon.setFixedSize(16, 16)
        self._status_label = _muted(CaptionLabel(""))
        footer.addWidget(self._status_icon)
        footer.addSpacing(2)
        footer.addWidget(self._status_label)
        footer.addStretch(1)

        close_btn = PushButton("Close")
        close_btn.clicked.connect(self.close)
        save_btn = PrimaryPushButton("Save")
        save_btn.clicked.connect(self._save)
        footer.addWidget(close_btn)
        footer.addWidget(save_btn)
        body.addLayout(footer)

    def _build_control_card(
        self,
        object_name: str,
        icon: FIF,
        title: str,
        subtitle: str,
        control: QWidget,
    ) -> QWidget:
        """A setting card matching SwitchSettingCard's look, with a custom
        control (time picker, spin box) on the trailing edge."""
        card = QWidget(self)
        card.setObjectName(object_name)
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setFixedHeight(70)

        row = QHBoxLayout(card)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(16)

        icon_widget = IconWidget(icon, card)
        icon_widget.setFixedSize(16, 16)

        text = QVBoxLayout()
        text.setSpacing(0)
        text.addWidget(BodyLabel(title))
        text.addWidget(_muted(CaptionLabel(subtitle)))

        row.addWidget(icon_widget)
        row.addLayout(text)
        row.addStretch(1)
        row.addWidget(control)

        card.setStyleSheet(_card_qss(object_name))
        self._card_restylers.append(
            lambda: card.setStyleSheet(_card_qss(object_name))
        )
        return card

    def _build_time_card(self) -> QWidget:
        self._time_picker = AMTimePicker(self)
        return self._build_control_card(
            "timeCard",
            FIF.STOP_WATCH,
            "Shutdown time",
            "Repeats daily · 12-hour clock",
            self._time_picker,
        )

    def _build_warning_card(self) -> QWidget:
        self._warning_spin = SpinBox(self)
        self._warning_spin.setRange(1, 60)
        self._warning_spin.setSuffix("")
        self._warning_spin.setFixedWidth(125)
        return self._build_control_card(
            "warningCard",
            FIF.RINGER,
            "Warning time",
            "How long before shutdown to show the countdown",
            self._warning_spin,
        )

    def _build_extension_card(self) -> QWidget:
        self._extension_spin = SpinBox(self)
        self._extension_spin.setRange(1, 180)
        self._extension_spin.setSuffix("")
        self._extension_spin.setFixedWidth(125)
        return self._build_control_card(
            "extensionCard",
            FIF.HISTORY,
            "Extension time",
            "How much “Extend” adds when you postpone a shutdown",
            self._extension_spin,
        )

    # ---------- data binding ----------

    def _load_from_settings(self) -> None:
        s = self._get_settings()
        self._enabled_card.setChecked(s.enabled)
        self._autostart_card.setChecked(s.start_with_windows)
        self._on_enabled_toggled(s.enabled)
        self._on_autostart_toggled(s.start_with_windows)
        self._time_picker.setTime(QTime(s.shutdown_hour, s.shutdown_minute))
        self._warning_spin.setValue(s.warning_minutes)
        self._extension_spin.setValue(s.extension_minutes)

    def _on_enabled_toggled(self, checked: bool) -> None:
        self._enabled_card.setContent(
            "On — armed for daily shutdown"
            if checked
            else "Off — schedule is disabled"
        )

    def _on_autostart_toggled(self, checked: bool) -> None:
        self._autostart_card.setContent(
            "On — launches at Windows sign-in"
            if checked
            else "Off — start it manually"
        )

    def _save(self) -> None:
        t = self._time_picker.getTime()
        try:
            new_settings = (
                self._get_settings()
                .with_changes(
                    enabled=self._enabled_card.isChecked(),
                    shutdown_hour=t.hour(),
                    shutdown_minute=t.minute(),
                    warning_minutes=self._warning_spin.value(),
                    extension_minutes=self._extension_spin.value(),
                    start_with_windows=self._autostart_card.isChecked(),
                )
                .validate()
            )
        except ValueError as e:
            self._toast_error("Invalid settings", str(e))
            return

        try:
            self._on_save(new_settings)
        except Exception as e:  # surface persistence errors
            self._toast_error("Could not save", str(e))
            return

        self._refresh_status()
        InfoBar.success(
            "Saved", "Your schedule has been updated.", parent=self,
            position=InfoBarPosition.TOP, duration=2500, isClosable=False,
        )

    def _toast_error(self, title: str, msg: str) -> None:
        InfoBar.error(
            title, msg, parent=self,
            position=InfoBarPosition.TOP, duration=4000,
        )

    def _refresh_status(self) -> None:
        s = self._get_settings()
        if not s.enabled:
            self._status_label.setText("Disabled — no shutdown scheduled.")
            return
        nxt = self._get_next()
        if nxt is None:
            self._status_label.setText("Enabled — next shutdown pending…")
        else:
            self._status_label.setText(
                f"Next shutdown: {format_dt_12h(nxt, with_day=True)}"
            )

    # ---------- window behavior ----------

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

    def showEvent(self, e) -> None:
        super().showEvent(e)
        # Once the layout is realized, the window sizeHint reliably accounts for
        # the time picker's hard 240px minimum width. Lock the width to it so
        # the AM/PM column is never clipped, whatever the font size or DPI.
        if not self._sized:
            self._sized = True
            self.setFixedWidth(max(500, self.sizeHint().width()))
            self.resize(self.width(), self.sizeHint().height())
            self._center()

    def closeEvent(self, e) -> None:
        # Closing just hides the page; the app lives in the tray.
        self._status_timer.stop()
        e.ignore()
        self.hide()

    def _onThemeChangedFinished(self) -> None:  # extend base Mica handling
        super()._onThemeChangedFinished()
        for restyle in self._card_restylers:
            restyle()


def _card_qss(object_name: str) -> str:
    """Card chrome matching SwitchSettingCard's painted look, theme-aware."""
    if isDarkTheme():
        bg, border = "rgba(255,255,255,0.051)", "rgba(0,0,0,0.196)"
    else:
        bg, border = "rgba(255,255,255,0.667)", "rgba(0,0,0,0.075)"
    return (
        f"#{object_name}{{background:{bg};border:1px solid {border};"
        f"border-radius:6px;}}"
    )
