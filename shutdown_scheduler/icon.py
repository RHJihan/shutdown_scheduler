# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

"""Tray / window icon rendering.

A modern Fluent power tile: a rounded-rectangle plate with a knocked-out power
glyph. Rendered with Qt so it stays crisp at any DPI and needs no image assets.
The plate is the Windows accent color when the schedule is armed and a neutral
gray when disabled, so it reads clearly on both light and dark taskbars.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from .theme import system_accent_color

_SIZE = 256  # rendered large; Qt downscales smoothly for the tray.
_DISABLED_FILL = QColor(120, 120, 120)
_GLYPH = QColor(255, 255, 255)


def _render(fill: QColor) -> QPixmap:
    pm = QPixmap(_SIZE, _SIZE)
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    painter.setRenderHints(
        QPainter.Antialiasing | QPainter.SmoothPixmapTransform
    )

    s = _SIZE
    margin = s * 0.06
    radius = s * 0.24

    # Rounded tile.
    painter.setPen(Qt.NoPen)
    painter.setBrush(fill)
    painter.drawRoundedRect(
        QRectF(margin, margin, s - 2 * margin, s - 2 * margin), radius, radius
    )

    # Power glyph: a ring open at the top with a vertical bar through the gap.
    cx = cy = s / 2
    r = s * 0.22
    width = s * 0.075

    pen = QPen(_GLYPH, width, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    # Qt angles are in 1/16 degree, counter-clockwise from 3 o'clock.
    # Draw the arc leaving a ~70deg gap centered at the top (12 o'clock).
    rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
    start_angle = int((90 - 35) * 16)
    span_angle = -int((360 - 70) * 16)
    painter.drawArc(rect, start_angle, span_angle)

    # Vertical bar.
    bar = QPainterPath()
    bar.moveTo(cx, cy - r * 1.28)
    bar.lineTo(cx, cy - r * 0.10)
    painter.drawPath(bar)

    painter.end()
    return pm


def create_icon(enabled: bool) -> QIcon:
    """Accent-filled tile when ``enabled``, neutral gray when not."""
    fill = system_accent_color() if enabled else _DISABLED_FILL
    return QIcon(_render(fill))


def app_icon() -> QIcon:
    """The window / taskbar icon (always the accent tile)."""
    return QIcon(_render(system_accent_color()))
