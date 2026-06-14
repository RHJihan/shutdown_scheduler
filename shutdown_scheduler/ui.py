from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Callable, Optional

from .config import Settings


class SettingsWindow:
    """Single-window settings UI. Hidden by default; opened via tray."""

    def __init__(
        self,
        root: tk.Tk,
        settings_provider: Callable[[], Settings],
        on_save: Callable[[Settings], None],
        next_shutdown_provider: Callable[[], Optional[datetime]],
    ) -> None:
        self._root = root
        self._get_settings = settings_provider
        self._on_save = on_save
        self._get_next = next_shutdown_provider
        self._top: Optional[tk.Toplevel] = None
        self._status_var: Optional[tk.StringVar] = None
        self._status_after_id: Optional[str] = None

        self._enabled_var = tk.BooleanVar()
        self._hour_var = tk.StringVar()
        self._minute_var = tk.StringVar()

    def show(self) -> None:
        if self._top is not None and tk.Toplevel.winfo_exists(self._top):
            self._top.lift()
            self._top.focus_force()
            return

        top = tk.Toplevel(self._root)
        top.title("Shutdown Scheduler")
        top.resizable(False, False)
        top.protocol("WM_DELETE_WINDOW", self._close)

        frame = ttk.Frame(top, padding=18)
        frame.grid(row=0, column=0)

        # --- Master toggle ---
        ttk.Checkbutton(
            frame,
            text="Enable scheduled shutdown",
            variable=self._enabled_var,
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 12))

        # --- Time pickers ---
        ttk.Label(frame, text="Shutdown time:").grid(row=1, column=0, sticky="w")
        hour_box = ttk.Spinbox(
            frame, from_=0, to=23, width=4, textvariable=self._hour_var, format="%02.0f"
        )
        hour_box.grid(row=1, column=1, sticky="w", padx=(8, 2))
        ttk.Label(frame, text=":").grid(row=1, column=2)
        minute_box = ttk.Spinbox(
            frame, from_=0, to=59, width=4, textvariable=self._minute_var, format="%02.0f"
        )
        minute_box.grid(row=1, column=3, sticky="w", padx=(2, 0))

        ttk.Label(frame, text="(24-hour format)", foreground="#666").grid(
            row=2, column=1, columnspan=3, sticky="w", pady=(2, 14)
        )

        # --- Status ---
        self._status_var = tk.StringVar()
        ttk.Separator(frame).grid(row=3, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        ttk.Label(frame, textvariable=self._status_var, foreground="#333").grid(
            row=4, column=0, columnspan=4, sticky="w"
        )

        # --- Buttons ---
        btns = ttk.Frame(frame)
        btns.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(16, 0))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="Save", command=self._save).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(btns, text="Close", command=self._close).grid(row=0, column=2)

        self._top = top
        self._load_from_settings()
        self._refresh_status()
        self._center(top)
        top.focus_force()

    def refresh_status(self) -> None:
        if self._top is not None and tk.Toplevel.winfo_exists(self._top):
            self._refresh_status()

    # ---------- internal ----------

    def _load_from_settings(self) -> None:
        s = self._get_settings()
        self._enabled_var.set(s.enabled)
        self._hour_var.set(f"{s.shutdown_hour:02d}")
        self._minute_var.set(f"{s.shutdown_minute:02d}")

    def _save(self) -> None:
        try:
            hour = int(self._hour_var.get())
            minute = int(self._minute_var.get())
        except ValueError:
            messagebox.showerror("Invalid time", "Hour and minute must be numbers.", parent=self._top)
            return

        try:
            new_settings = self._get_settings().with_changes(
                enabled=bool(self._enabled_var.get()),
                shutdown_hour=hour,
                shutdown_minute=minute,
            ).validate()
        except ValueError as e:
            messagebox.showerror("Invalid settings", str(e), parent=self._top)
            return

        try:
            self._on_save(new_settings)
        except Exception as e:  # surface persistence errors
            messagebox.showerror("Could not save", str(e), parent=self._top)
            return

        self._refresh_status()

    def _refresh_status(self) -> None:
        if self._status_var is None or self._top is None:
            return
        s = self._get_settings()
        if not s.enabled:
            self._status_var.set("Status: disabled (master toggle is off).")
        else:
            nxt = self._get_next()
            if nxt is None:
                self._status_var.set("Status: enabled. Next shutdown pending…")
            else:
                self._status_var.set(
                    f"Status: enabled. Next shutdown {nxt.strftime('%a %d %b, %H:%M')}."
                )
        # Refresh status once per minute while window is open.
        if self._status_after_id:
            try:
                self._top.after_cancel(self._status_after_id)
            except tk.TclError:
                pass
        self._status_after_id = self._top.after(60_000, self._refresh_status)

    def _center(self, top: tk.Toplevel) -> None:
        top.update_idletasks()
        w, h = top.winfo_width(), top.winfo_height()
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        top.geometry(f"+{(sw - w) // 2}+{(sh - h) // 3}")

    def _close(self) -> None:
        if self._status_after_id and self._top:
            try:
                self._top.after_cancel(self._status_after_id)
            except tk.TclError:
                pass
        self._status_after_id = None
        if self._top is not None:
            try:
                self._top.destroy()
            except tk.TclError:
                pass
        self._top = None
