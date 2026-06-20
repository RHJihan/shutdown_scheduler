# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

"""Time formatting helpers.

The schedule is *stored* in 24-hour form (`shutdown_hour` 0..23) so persistence
stays unambiguous and locale-independent. The *UI*, however, presents time in
12-hour form with an AM/PM period, which is what most Windows users expect.
These helpers are the single conversion point between the two representations.
"""
from __future__ import annotations

from datetime import datetime

AM = "AM"
PM = "PM"
PERIODS = (AM, PM)


def to_12h(hour24: int, minute: int) -> tuple[int, int, str]:
    """Convert a 24-hour ``(hour, minute)`` to ``(hour12, minute, period)``.

    ``hour12`` is in 1..12 and ``period`` is ``"AM"`` or ``"PM"``.
    """
    period = AM if hour24 < 12 else PM
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12
    return hour12, minute, period


def from_12h(hour12: int, minute: int, period: str) -> tuple[int, int]:
    """Convert a 12-hour ``(hour12, minute, period)`` back to 24-hour."""
    h = hour12 % 12  # 12 -> 0
    if period.upper() == PM:
        h += 12
    return h, minute


def format_12h(hour24: int, minute: int) -> str:
    """Format a 24-hour ``(hour, minute)`` as e.g. ``"5:30 PM"``."""
    hour12, _, period = to_12h(hour24, minute)
    return f"{hour12}:{minute:02d} {period}"


def format_dt_12h(dt: datetime, *, with_day: bool = False) -> str:
    """Format a datetime in 12-hour form, optionally prefixed with the weekday.

    Examples: ``"5:30 PM"`` or ``"Fri 5:30 PM"``.
    """
    body = format_12h(dt.hour, dt.minute)
    return f"{dt.strftime('%a')} {body}" if with_day else body
