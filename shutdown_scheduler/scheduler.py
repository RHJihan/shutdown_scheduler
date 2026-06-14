from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Callable, Optional

from .config import Settings


def compute_next_shutdown(settings: Settings, now: datetime) -> datetime:
    """Next datetime at the configured HH:MM. If already passed today, returns tomorrow."""
    target = now.replace(
        hour=settings.shutdown_hour,
        minute=settings.shutdown_minute,
        second=0,
        microsecond=0,
    )
    if target <= now:
        target += timedelta(days=1)
    return target


@dataclass
class SchedulerCallbacks:
    on_warning: Callable[[datetime], None]
    on_shutdown: Callable[[], None]
    on_status_change: Callable[[], None] = lambda: None


class SchedulerService:
    """Background tick loop. Single-threaded state, low CPU (30s ticks).

    Lifecycle:
      - When master toggle is on, `next_at` is set to the next scheduled datetime.
      - Within `warning_minutes` of `next_at`, fires `on_warning` exactly once
        (per pending shutdown).
      - At/after `next_at`, fires `on_shutdown`.
      - After fire/cancel, advances `next_at` by one day.
    """

    _TICK_SECONDS = 30

    def __init__(self, settings_provider: Callable[[], Settings], callbacks: SchedulerCallbacks) -> None:
        self._get_settings = settings_provider
        self._cb = callbacks
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._next_at: Optional[datetime] = None
        self._warned_for: Optional[datetime] = None

    # ---------- lifecycle ----------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.reschedule()
        self._thread = threading.Thread(target=self._run, name="scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    # ---------- query ----------

    @property
    def next_at(self) -> Optional[datetime]:
        with self._lock:
            return self._next_at

    # ---------- mutations ----------

    def reschedule(self) -> None:
        """Recompute next-at from current settings. Call after settings change."""
        with self._lock:
            settings = self._get_settings()
            if settings.enabled:
                self._next_at = compute_next_shutdown(settings, datetime.now())
            else:
                self._next_at = None
            self._warned_for = None
        self._cb.on_status_change()
        self._wake.set()

    def cancel_current(self) -> None:
        """User chose 'cancel': skip to next day's occurrence."""
        with self._lock:
            settings = self._get_settings()
            if not settings.enabled or self._next_at is None:
                return
            self._next_at = self._next_at + timedelta(days=1)
            self._warned_for = None
        self._cb.on_status_change()
        self._wake.set()

    def extend_current(self) -> None:
        """User chose 'extend': push next-at by configured minutes."""
        with self._lock:
            settings = self._get_settings()
            if not settings.enabled or self._next_at is None:
                return
            self._next_at = self._next_at + timedelta(minutes=settings.extension_minutes)
            self._warned_for = None
        self._cb.on_status_change()
        self._wake.set()

    # ---------- internal ----------

    def _run(self) -> None:
        while not self._stop.is_set():
            self._tick()
            self._wake.wait(timeout=self._TICK_SECONDS)
            self._wake.clear()

    def _tick(self) -> None:
        with self._lock:
            settings = self._get_settings()
            if not settings.enabled or self._next_at is None:
                return
            now = datetime.now()
            next_at = self._next_at
            warning_window = timedelta(minutes=settings.warning_minutes)
            should_warn = (
                next_at - now <= warning_window
                and next_at > now
                and self._warned_for != next_at
            )
            should_shutdown = now >= next_at
            warned_target = next_at if should_warn else None

        if should_shutdown:
            self._cb.on_shutdown()
            return

        if should_warn:
            with self._lock:
                self._warned_for = warned_target
            self._cb.on_warning(next_at)
