# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

"""Entry point. Run with `pythonw main.py` to launch without a console window."""
from __future__ import annotations

import sys


def _set_app_user_model_id() -> None:
    """Give Windows an explicit AppUserModelID so the taskbar/notifications use
    our own icon and identity rather than the host Python's."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "RifatHasanJihan.ShutdownScheduler"
        )
    except Exception:
        pass  # Cosmetic only.


def _import_ui_quietly() -> None:
    """Import qfluentwidgets with stdout muted to swallow its one-time promo
    banner, which it unconditionally ``print()``s at import time."""
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        import qfluentwidgets  # noqa: F401


def main() -> int:
    _set_app_user_model_id()
    _import_ui_quietly()

    from shutdown_scheduler.app import Application

    start_minimized = "--minimized" in sys.argv
    Application(start_minimized=start_minimized).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
