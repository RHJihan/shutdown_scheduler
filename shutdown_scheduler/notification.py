# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Md. Rifat Hasan Jihan

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Callable, Optional


class WarningDialog:
    """Modal warning dialog. Buttons fire callbacks; X button takes no action
    (shutdown will proceed as scheduled). Auto-updates a live countdown."""

    def __init__(
        self,
        root: tk.Tk,
        shutdown_at: datetime,
        extension_minutes: int,
        on_cancel: Callable[[], None],
        on_extend: Callable[[], None],
    ) -> None:
        self._root = root
        self._shutdown_at = shutdown_at
        self._on_cancel = on_cancel
        self._on_extend = on_extend
        self._extension_minutes = extension_minutes
        self._top: Optional[tk.Toplevel] = None
        self._countdown_var: Optional[tk.StringVar] = None
        self._after_id: Optional[str] = None

    def show(self) -> None:
        if self._top is not None and tk.Toplevel.winfo_exists(self._top):
            self._top.lift()
            return

        top = tk.Toplevel(self._root)
        top.title("Shutdown Imminent")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        top.protocol("WM_DELETE_WINDOW", self._close)

        frame = ttk.Frame(top, padding=20)
        frame.grid(row=0, column=0)

        ttk.Label(
            frame,
            text="Your PC will shut down soon.",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        self._countdown_var = tk.StringVar()
        ttk.Label(frame, textvariable=self._countdown_var, font=("Segoe UI", 10)).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 14)
        )

        ttk.Button(frame, text="Cancel shutdown", command=self._cancel).grid(
            row=2, column=0, padx=(0, 8), sticky="ew"
        )
        ttk.Button(
            frame,
            text=f"Extend {self._extension_minutes} min",
            command=self._extend,
        ).grid(row=2, column=1, sticky="ew")

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        self._top = top
        self._center(top)
        self._tick()

    def _center(self, top: tk.Toplevel) -> None:
        top.update_idletasks()
        w, h = top.winfo_width(), top.winfo_height()
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        top.geometry(f"+{(sw - w) // 2}+{(sh - h) // 3}")

    def _tick(self) -> None:
        if self._top is None or self._countdown_var is None:
            return
        remaining = self._shutdown_at - datetime.now()
        secs = max(0, int(remaining.total_seconds()))
        m, s = divmod(secs, 60)
        self._countdown_var.set(
            f"Shutdown scheduled at {self._shutdown_at.strftime('%H:%M')} "
            f"— {m:02d}:{s:02d} remaining."
        )
        if secs <= 0:
            self._close()
            return
        self._after_id = self._top.after(1000, self._tick)

    def _cancel(self) -> None:
        self._close()
        self._on_cancel()

    def _extend(self) -> None:
        self._close()
        self._on_extend()

    def _close(self) -> None:
        if self._after_id and self._top:
            try:
                self._top.after_cancel(self._after_id)
            except tk.TclError:
                pass
        if self._top is not None:
            try:
                self._top.destroy()
            except tk.TclError:
                pass
        self._top = None
