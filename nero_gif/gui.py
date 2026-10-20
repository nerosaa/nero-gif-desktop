"""English tkinter UI — Video→GIF + Compress + Unlock."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __app_name__, __version__, license_check
from .converter import CompressOptions, ConvertError, ConvertOptions, compress_gif, video_to_gif
from .paths import find_ffmpeg


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{__app_name__} {__version__}")
        self.minsize(520, 480)
        self.geometry("560x560")

        self.video_path = tk.StringVar()
        self.gif_path = tk.StringVar()
        self.start = tk.DoubleVar(value=0.0)
        self.duration = tk.DoubleVar(value=5.0)
        self.width = tk.IntVar(value=480)
        self.fps = tk.IntVar(value=10)
        self.c_scale = tk.DoubleVar(value=0.75)
        self.c_fps = tk.IntVar(value=10)
        self.c_colors = tk.IntVar(value=128)
        self.status = tk.StringVar(value="Ready")
        self.tier = tk.StringVar()

        self._busy = False
        self._build()
        self.refresh_tier()

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 4}
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, textvariable=self.tier).pack(side="left")
        ttk.Button(top, text="Enter license…", command=self.unlock_dialog).pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, **pad)

        # --- Video tab ---
        tab_v = ttk.Frame(nb)
        nb.add(tab_v, text="Video → GIF")
        row = ttk.Frame(tab_v)
        row.pack(fill="x", **pad)
        ttk.Entry(row, textvariable=self.video_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse…", command=self.pick_video).pack(side="left", padx=4)

        grid = ttk.Frame(tab_v)
        grid.pack(fill="x", **pad)
        ttk.Label(grid, text="Start (s)").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(grid, from_=0, to=9999, increment=0.5, textvariable=self.start, width=8).grid(
            row=0, column=1, sticky="w", padx=4
        )
        ttk.Label(grid, text="Duration (s)").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Spinbox(grid, from_=0.5, to=9999, increment=0.5, textvariable=self.duration, width=8).grid(
            row=0, column=3, sticky="w", padx=4
        )
        ttk.Label(grid, text="Width").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(
            grid, textvariable=self.width, values=(320, 480, 640, 800), width=8, state="readonly"
        ).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(grid, text="FPS").grid(row=1, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(
            grid, textvariable=self.fps, values=(5, 8, 10, 12, 15, 20), width=8, state="readonly"
        ).grid(row=1, column=3, sticky="w", padx=4)

        ttk.Label(
            tab_v,
            text=f"Free build: max {int(license_check.FREE_MAX_SECONDS)}s + watermark. "
            "Pro unlock removes watermark and the duration cap.",
            wraplength=500,
        ).pack(anchor="w", **pad)
        ttk.Button(tab_v, text="Convert to GIF", command=self.do_convert).pack(anchor="w", **pad)

        # --- Compress tab ---
        tab_c = ttk.Frame(nb)
        nb.add(tab_c, text="Compress GIF")
        row2 = ttk.Frame(tab_c)
        row2.pack(fill="x", **pad)
        ttk.Entry(row2, textvariable=self.gif_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="Browse…", command=self.pick_gif).pack(side="left", padx=4)

        grid2 = ttk.Frame(tab_c)
        grid2.pack(fill="x", **pad)
        ttk.Label(grid2, text="Scale").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            grid2, textvariable=self.c_scale, values=(1.0, 0.75, 0.5, 0.33), width=8, state="readonly"
        ).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(grid2, text="FPS").grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(
            grid2, textvariable=self.c_fps, values=(0, 15, 10, 8, 5), width=8, state="readonly"
        ).grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(grid2, text="Colors").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(
            grid2, textvariable=self.c_colors, values=(256, 128, 64, 32), width=8, state="readonly"
        ).grid(row=1, column=1, sticky="w", padx=4)

        ttk.Button(tab_c, text="Compress GIF", command=self.do_compress).pack(anchor="w", **pad)

        # Status
        bot = ttk.Frame(self)
        bot.pack(fill="x", **pad)
        ttk.Label(bot, textvariable=self.status, wraplength=520).pack(anchor="w")
        ttk.Label(
            bot,
            text="Free web tool (no watermark): https://nerosaa.github.io/video-to-gif/",
            foreground="#0369a1",
        ).pack(anchor="w", pady=(6, 0))

    def refresh_tier(self) -> None:
        lic = license_check.current_license()
        if lic.is_paid:
            self.tier.set(f"License: PRO — {lic.note}")
        else:
            self.tier.set(f"License: FREE — watermark on, max {int(license_check.FREE_MAX_SECONDS)}s")

    def pick_video(self) -> None:
        p = filedialog.askopenfilename(
            title="Select video",
            filetypes=[
                ("Video", "*.mp4 *.webm *.mov *.mkv *.m4v *.avi"),
                ("All", "*.*"),
            ],
        )
        if p:
            self.video_path.set(p)

    def pick_gif(self) -> None:
        p = filedialog.askopenfilename(
            title="Select GIF",
            filetypes=[("GIF", "*.gif"), ("All", "*.*")],
        )
        if p:
            self.gif_path.set(p)

    def unlock_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title("Enter license key")
        win.grab_set()
        ttk.Label(win, text="Paste your NERO1.… pro key:").pack(padx=12, pady=8, anchor="w")
        var = tk.StringVar()
        ent = ttk.Entry(win, textvariable=var, width=56)
        ent.pack(padx=12, pady=4)
        ent.focus_set()

        def save() -> None:
            try:
                license_check.save_key(var.get())
            except ValueError as e:
                messagebox.showerror("Invalid key", str(e), parent=win)
                return
            self.refresh_tier()
            messagebox.showinfo("Unlocked", "Pro features enabled.", parent=win)
            win.destroy()

        ttk.Button(win, text="Unlock", command=save).pack(pady=10)

    def _guard(self) -> bool:
        if self._busy:
            messagebox.showinfo("Busy", "A conversion is already running.")
            return False
        try:
            find_ffmpeg()
        except FileNotFoundError as e:
            messagebox.showerror("ffmpeg missing", str(e))
            return False
        return True

    def do_convert(self) -> None:
        if not self._guard():
            return
        src = self.video_path.get().strip()
        if not src:
            messagebox.showwarning("No file", "Choose a video file first.")
            return
        dest = filedialog.asksaveasfilename(
            title="Save GIF",
            defaultextension=".gif",
            filetypes=[("GIF", "*.gif")],
            initialfile=Path(src).with_suffix(".gif").name,
        )
        if not dest:
            return
        opts = ConvertOptions(
            start=float(self.start.get()),
            duration=float(self.duration.get()),
            width=int(self.width.get()),
            fps=int(self.fps.get()),
        )
        self._run_job(lambda: video_to_gif(src, dest, opts, log=self._set_status))

    def do_compress(self) -> None:
        if not self._guard():
            return
        src = self.gif_path.get().strip()
        if not src:
            messagebox.showwarning("No file", "Choose a GIF file first.")
            return
        dest = filedialog.asksaveasfilename(
            title="Save compressed GIF",
            defaultextension=".gif",
            filetypes=[("GIF", "*.gif")],
            initialfile=Path(src).stem + "_compressed.gif",
        )
        if not dest:
            return
        opts = CompressOptions(
            scale=float(self.c_scale.get()),
            fps=int(self.c_fps.get()),
            colors=int(self.c_colors.get()),
        )
        self._run_job(lambda: compress_gif(src, dest, opts, log=self._set_status))

    def _set_status(self, msg: str) -> None:
        self.after(0, lambda: self.status.set(msg))

    def _run_job(self, fn) -> None:
        self._busy = True
        self.status.set("Working…")

        def worker() -> None:
            try:
                path = fn()
                self.after(0, lambda: self._done(True, str(path)))
            except ConvertError as e:
                self.after(0, lambda: self._done(False, str(e)))
            except Exception as e:  # noqa: BLE001
                self.after(0, lambda: self._done(False, str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, ok: bool, msg: str) -> None:
        self._busy = False
        self.status.set(msg if ok else f"Error: {msg}")
        if ok:
            messagebox.showinfo("Done", f"Saved:\n{msg}")
        else:
            messagebox.showerror("Failed", msg)


def run() -> None:
    app = App()
    app.mainloop()
