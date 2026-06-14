# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

from __future__ import annotations

import subprocess
from typing import Protocol


class ShutdownService(Protocol):
    def shutdown_now(self) -> None: ...
    def abort_pending(self) -> None: ...


class WindowsShutdownService:
    """Thin wrapper over `shutdown.exe`.

    `/s /f /t 0` shuts down immediately and forces running apps to close.
    Without `/f` the shutdown is "graceful": Windows asks each app to close,
    and any app with unsaved work (or one that's slow to respond) can block or
    silently abort the shutdown — which is why a scheduled shutdown can appear
    to do nothing after the countdown ends.
    """

    def shutdown_now(self) -> None:
        subprocess.run(
            ["shutdown", "/s", "/f", "/t", "0"],
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

    def abort_pending(self) -> None:
        subprocess.run(
            ["shutdown", "/a"],
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
