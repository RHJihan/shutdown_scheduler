"""Entry point. Run with `pythonw main.py` for background (no console)."""
from __future__ import annotations

import sys

from shutdown_scheduler.app import Application


def main() -> int:
    start_minimized = "--minimized" in sys.argv
    Application(start_minimized=start_minimized).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
