# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Protocol


APP_NAME = "WindowsShutdownScheduler"


def _default_config_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / APP_NAME / "config.json"


@dataclass(frozen=True)
class Settings:
    enabled: bool = False
    shutdown_hour: int = 17
    shutdown_minute: int = 30
    warning_minutes: int = 5
    extension_minutes: int = 10
    start_with_windows: bool = False

    def with_changes(self, **changes) -> "Settings":
        return replace(self, **changes)

    def validate(self) -> "Settings":
        if not 0 <= self.shutdown_hour <= 23:
            raise ValueError("shutdown_hour must be 0..23")
        if not 0 <= self.shutdown_minute <= 59:
            raise ValueError("shutdown_minute must be 0..59")
        if self.warning_minutes < 1:
            raise ValueError("warning_minutes must be >= 1")
        if self.extension_minutes < 1:
            raise ValueError("extension_minutes must be >= 1")
        return self


class SettingsRepository(Protocol):
    def load(self) -> Settings: ...
    def save(self, settings: Settings) -> None: ...


class JsonSettingsRepository:
    """Atomic JSON persistence. Falls back to defaults on first run or corruption."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _default_config_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> Settings:
        if not self._path.exists():
            return Settings()
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return Settings()
        known = {f for f in Settings.__dataclass_fields__}
        filtered = {k: v for k, v in raw.items() if k in known}
        try:
            return Settings(**filtered).validate()
        except (TypeError, ValueError):
            return Settings()

    def save(self, settings: Settings) -> None:
        settings.validate()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a tempfile in the same dir, then atomic replace.
        fd, tmp = tempfile.mkstemp(dir=str(self._path.parent), prefix=".cfg-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(asdict(settings), f, indent=2)
            os.replace(tmp, self._path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
