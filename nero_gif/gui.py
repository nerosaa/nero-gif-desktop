"""tkinter UI — Record screen, Video→GIF, Social GIF, Compress, Unlock (10 languages)."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from . import __app_name__, __version__, i18n, license_check
from .converter import CompressOptions, ConvertError, ConvertOptions, compress_gif, video_to_gif
from .i18n import t
from .paths import find_ffmpeg
from .presets import MB, PRESETS, social_gif
from .recorder import Recorder, Region

WEB_TOOL = "https://nerosaa.github.io/video-to-gif/"
VIDEO_EXT = "*.mp4 *.webm *.mov *.mkv *.m4v *.avi"
_REASONS = {
    "empty key": "lic_reason_empty",
    "bad format": "lic_reason_format",
    "bad signature": "lic_reason_signature",
    "bad payload": "lic_reason_payload",
    "not pro tier": "lic_reason_tier",
}


def fmt_size(n: int) -> str:
    return f"{n / MB:.2f} MB" if n >= 1024 * 1024 else f"{n / 1024:.0f} KB"


def fmt_secs(s: float) -> str:
    s = int(s)
    return f"{s // 60:02d}:{s % 60:02d}"


def license_reason(note: str) -> str:
    return t(_REASONS.get(note, "lic_reason_signature"))


def _enable_dpi_awareness() -> None:
    """So tk coordinates == physical pixels == gdigrab offsets on scaled displays."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:  # noqa: BLE001
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass


class RegionSelector(tk.Toplevel):
    """Translucent full-screen overlay; drag a rectangle, Esc cancels."""

    def __init__(self, master: tk.Misc, on_done: Callable[[Optional[Region]], None]) -> None:
        super().__init__(master)
        self.on_done = on_done
        self.overrideredirect(True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.3)
        except tk.TclError:
            pass
        self.cv = tk.Canvas(self, cursor="crosshair", bg="black", highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        self.cv.create_text(sw // 2, 40, text=t("rec_region_hint"), fill="white",
                            font=("TkDefaultFont", 18, "bold"))
        self._start: Optional[tuple[int, int]] = None
        self._rect: Optional[int] = None
        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.bind("<Escape>", lambda _e: self._finish(None))
        self.focus_force()
        self.grab_set()

    def _press(self, e: tk.Event) -> None:
        self._start = (e.x_root, e.y_root)
        if self._rect:
            self.cv.delete(self._rect)
        self._rect = self.cv.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=3,
                                              fill="white")

    def _drag(self, e: tk.Event) -> None:
        if self._start and self._rect:
            x0 = self._start[0] - self.winfo_rootx()
            y0 = self._start[1] - self.winfo_rooty()
            self.cv.coords(self._rect, x0, y0, e.x, e.y)

    def _release(self, e: tk.Event) -> None:
        if not self._start:
            return
        x0, y0 = self._start
        x, y = min(x0, e.x_root), min(y0, e.y_root)
        w, h = abs(e.x_root - x0), abs(e.y_root - y0)
        self._finish(Region(x, y, w, h) if w >= 16 and h >= 16 else None)

    def _finish(self, region: Optional[Region]) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
        self.on_done(region)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        i18n.init()
        self.title(f"{__app_name__} {__version__}")
        self.minsize(600, 560)
        self.geometry("640x620")

        # shared state survives a language switch (widgets are rebuilt, vars are not)
        self.video_path = tk.StringVar()
        self.gif_path = tk.StringVar()
        self.social_path = tk.StringVar()
        self.start = tk.DoubleVar(value=0.0)
        self.duration = tk.DoubleVar(value=5.0)
        self.width = tk.IntVar(value=480)
        self.fps = tk.IntVar(value=10)
        self.c_scale = tk.DoubleVar(value=0.75)
        self.c_fps = tk.IntVar(value=10)
        self.c_colors = tk.IntVar(value=128)
        self.s_start = tk.DoubleVar(value=0.0)
        self.s_duration = tk.DoubleVar(value=10.0)
        self.s_preset = tk.StringVar(value="discord")
        self.r_mode = tk.StringVar(value="full")
        self.r_x = tk.StringVar(value="0")
        self.r_y = tk.StringVar(value="0")
        self.r_w = tk.StringVar(value="800")
        self.r_h = tk.StringVar(value="600")
        self.r_fps = tk.IntVar(value=12)
        self.r_cursor = tk.BooleanVar(value=True)
        self.r_countdown = tk.IntVar(value=3)
        self.r_output = tk.StringVar(value="standard")
        self.status = tk.StringVar(value=t("app_ready"))
        self.tier = tk.StringVar()
        self.lang_name = tk.StringVar(value=i18n.LANGUAGES[i18n.current()])

        self._busy = False
        self._recorder: Optional[Recorder] = None
        self._rec_win: Optional[tk.Toplevel] = None
        self._tab_index = 0
        self._build()
        self.refresh_tier()

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        pad = {"padx": 10, "pady": 4}
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Button(top, text=t("btn_enter_license"), command=self.unlock_dialog).pack(side="right")
        lang_cb = ttk.Combobox(top, textvariable=self.lang_name, state="readonly", width=11,
                               values=list(i18n.LANGUAGES.values()))
        lang_cb.pack(side="right", padx=6)
        lang_cb.bind("<<ComboboxSelected>>", self._on_language)
        ttk.Label(top, text=t("language")).pack(side="right")
        # tier on its own line so long translations never clip the language box
        ttk.Label(self, textvariable=self.tier, wraplength=600).pack(fill="x", padx=10)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, **pad)
        self._build_record(pad)
        self._build_video(pad)
        self._build_social(pad)
        self._build_compress(pad)
        try:
            self.nb.select(self._tab_index)
        except tk.TclError:
            pass

        bot = ttk.Frame(self)
        bot.pack(fill="x", **pad)
        ttk.Label(bot, textvariable=self.status, wraplength=600).pack(anchor="w")
        ttk.Label(bot, text=t("web_tool_link", url=WEB_TOOL), foreground="#0369a1").pack(
            anchor="w", pady=(6, 0))

    def _free_note(self, parent: tk.Misc, pad: dict) -> None:
        ttk.Label(parent, text=t("free_note", sec=int(license_check.FREE_MAX_SECONDS)),
                  wraplength=580).pack(anchor="w", **pad)

    def _file_row(self, parent: tk.Misc, var: tk.StringVar, cmd: Callable[[], None], pad: dict) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", **pad)
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text=t("btn_browse"), command=cmd).pack(side="left", padx=4)

    def _preset_values(self) -> list[str]:
        return [t(f"preset_{k}") for k in PRESETS]

    def _build_record(self, pad: dict) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text=t("tab_record"))
        area = ttk.LabelFrame(tab, text=t("rec_area"))
        area.pack(fill="x", **pad)
        ttk.Radiobutton(area, text=t("rec_full"), value="full", variable=self.r_mode).grid(
            row=0, column=0, sticky="w", padx=6, pady=3)
        ttk.Radiobutton(area, text=t("rec_region"), value="region", variable=self.r_mode).grid(
            row=1, column=0, sticky="w", padx=6, pady=3)
        for i, (lbl, var) in enumerate((("x", self.r_x), ("y", self.r_y), ("w", self.r_w), ("h", self.r_h))):
            ttk.Label(area, text=lbl).grid(row=1, column=1 + i * 2, sticky="e", padx=(6, 2))
            ttk.Entry(area, textvariable=var, width=6).grid(row=1, column=2 + i * 2, sticky="w")
        ttk.Button(area, text=t("rec_select_region"), command=self.select_region).grid(
            row=1, column=9, padx=8)

        grid = ttk.Frame(tab)
        grid.pack(fill="x", **pad)
        ttk.Label(grid, text=t("label_fps")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(grid, textvariable=self.r_fps, values=(8, 10, 12, 15, 20), width=6,
                     state="readonly").grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(grid, text=t("rec_countdown")).grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(grid, textvariable=self.r_countdown, values=(0, 3, 5), width=6,
                     state="readonly").grid(row=0, column=3, sticky="w", padx=4)
        ttk.Checkbutton(grid, text=t("rec_cursor"), variable=self.r_cursor).grid(
            row=0, column=4, sticky="w", padx=(12, 0))
        ttk.Label(grid, text=t("label_width")).grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(grid, textvariable=self.width, values=(320, 480, 640, 800), width=6,
                     state="readonly").grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(grid, text=t("rec_output")).grid(row=1, column=2, sticky="w", padx=(12, 0))
        outs = [t("rec_output_standard")] + self._preset_values()
        self._rec_out_keys = ["standard"] + list(PRESETS)
        self._rec_out_name = tk.StringVar(value=outs[self._rec_out_keys.index(self.r_output.get())])
        cb = ttk.Combobox(grid, textvariable=self._rec_out_name, values=outs, width=30, state="readonly")
        cb.grid(row=1, column=3, columnspan=2, sticky="w", padx=4)
        cb.bind("<<ComboboxSelected>>",
                lambda _e: self.r_output.set(self._rec_out_keys[outs.index(self._rec_out_name.get())]))

        self._free_note(tab, pad)
        ttk.Button(tab, text=t("rec_start"), command=self.start_recording).pack(anchor="w", **pad)

    def _build_video(self, pad: dict) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text=t("tab_video"))
        self._file_row(tab, self.video_path, self.pick_video, pad)
        grid = ttk.Frame(tab)
        grid.pack(fill="x", **pad)
        ttk.Label(grid, text=t("label_start")).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(grid, from_=0, to=9999, increment=0.5, textvariable=self.start, width=8).grid(
            row=0, column=1, sticky="w", padx=4)
        ttk.Label(grid, text=t("label_duration")).grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Spinbox(grid, from_=0.5, to=9999, increment=0.5, textvariable=self.duration, width=8).grid(
            row=0, column=3, sticky="w", padx=4)
        ttk.Label(grid, text=t("label_width")).grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(grid, textvariable=self.width, values=(320, 480, 640, 800), width=8,
                     state="readonly").grid(row=1, column=1, sticky="w", padx=4)
        ttk.Label(grid, text=t("label_fps")).grid(row=1, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(grid, textvariable=self.fps, values=(5, 8, 10, 12, 15, 20), width=8,
                     state="readonly").grid(row=1, column=3, sticky="w", padx=4)
        self._free_note(tab, pad)
        ttk.Button(tab, text=t("btn_convert"), command=self.do_convert).pack(anchor="w", **pad)

    def _build_social(self, pad: dict) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text=t("tab_social"))
        ttk.Label(tab, text=t("social_title"), font=("TkDefaultFont", 10, "bold"),
                  wraplength=580).pack(anchor="w", **pad)
        ttk.Label(tab, text=t("social_input")).pack(anchor="w", padx=10)
        self._file_row(tab, self.social_path, self.pick_media, pad)
        box = ttk.LabelFrame(tab, text=t("social_preset"))
        box.pack(fill="x", **pad)
        for k in PRESETS:
            ttk.Radiobutton(box, text=t(f"preset_{k}"), value=k, variable=self.s_preset).pack(
                anchor="w", padx=6, pady=1)
        grid = ttk.Frame(tab)
        grid.pack(fill="x", **pad)
        ttk.Label(grid, text=t("label_start")).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(grid, from_=0, to=9999, increment=0.5, textvariable=self.s_start, width=8).grid(
            row=0, column=1, sticky="w", padx=4)
        ttk.Label(grid, text=t("label_duration")).grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Spinbox(grid, from_=0.5, to=9999, increment=0.5, textvariable=self.s_duration, width=8).grid(
            row=0, column=3, sticky="w", padx=4)
        self._free_note(tab, pad)
        ttk.Button(tab, text=t("social_make"), command=self.do_social).pack(anchor="w", **pad)

    def _build_compress(self, pad: dict) -> None:
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text=t("tab_compress"))
        self._file_row(tab, self.gif_path, self.pick_gif, pad)
        grid = ttk.Frame(tab)
        grid.pack(fill="x", **pad)
        ttk.Label(grid, text=t("label_scale")).grid(row=0, column=0, sticky="w")
        ttk.Combobox(grid, textvariable=self.c_scale, values=(1.0, 0.75, 0.5, 0.33), width=8,
                     state="readonly").grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(grid, text=t("label_fps")).grid(row=0, column=2, sticky="w", padx=(12, 0))
        ttk.Combobox(grid, textvariable=self.c_fps, values=(0, 15, 10, 8, 5), width=8,
                     state="readonly").grid(row=0, column=3, sticky="w", padx=4)
        ttk.Label(grid, text=t("label_colors")).grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(grid, textvariable=self.c_colors, values=(256, 128, 64, 32), width=8,
                     state="readonly").grid(row=1, column=1, sticky="w", padx=4)
        ttk.Button(tab, text=t("btn_compress"), command=self.do_compress).pack(anchor="w", **pad)

    def _on_language(self, _e=None) -> None:
        name = self.lang_name.get()
        code = next((c for c, n in i18n.LANGUAGES.items() if n == name), i18n.DEFAULT)
        i18n.set_language(code)
        try:
            i18n.save_language(code)
        except OSError:
            pass
        try:
            self._tab_index = self.nb.index(self.nb.select())
        except tk.TclError:
            self._tab_index = 0
        if not self._busy:
            self.status.set(t("app_ready"))
        self._build()
        self.refresh_tier()

    def refresh_tier(self) -> None:
        lic = license_check.current_license()
        if lic.is_paid:
            buyer = (lic.payload or {}).get("e", "?")
            self.tier.set(t("tier_pro", buyer=buyer))
        else:
            self.tier.set(t("tier_free", sec=int(license_check.FREE_MAX_SECONDS)))

    # --------------------------------------------------------------- pickers
    def pick_video(self) -> None:
        p = filedialog.askopenfilename(title=t("dlg_select_video"),
                                       filetypes=[(t("ft_video"), VIDEO_EXT), (t("ft_all"), "*.*")])
        if p:
            self.video_path.set(p)

    def pick_gif(self) -> None:
        p = filedialog.askopenfilename(title=t("dlg_select_gif"),
                                       filetypes=[(t("ft_gif"), "*.gif"), (t("ft_all"), "*.*")])
        if p:
            self.gif_path.set(p)

    def pick_media(self) -> None:
        p = filedialog.askopenfilename(title=t("dlg_select_media"), filetypes=[
            (t("ft_media"), VIDEO_EXT + " *.gif"), (t("ft_all"), "*.*")])
        if p:
            self.social_path.set(p)

    def _ask_save(self, initial: str, title_key: str = "dlg_save_gif") -> str:
        return filedialog.asksaveasfilename(title=t(title_key), defaultextension=".gif",
                                            filetypes=[(t("ft_gif"), "*.gif")], initialfile=initial)

    # --------------------------------------------------------------- license
    def unlock_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title(t("lic_title"))
        win.grab_set()
        ttk.Label(win, text=t("lic_prompt")).pack(padx=12, pady=8, anchor="w")
        var = tk.StringVar()
        ent = ttk.Entry(win, textvariable=var, width=56)
        ent.pack(padx=12, pady=4)
        ent.focus_set()

        def save() -> None:
            info = license_check.verify_key(var.get())
            if not info.is_paid:
                messagebox.showerror(t("lic_invalid_title"),
                                     t("lic_invalid", reason=license_reason(info.note)), parent=win)
                return
            try:
                license_check.save_key(var.get())
            except (ValueError, OSError) as e:
                messagebox.showerror(t("lic_invalid_title"), t("error_prefix", msg=str(e)), parent=win)
                return
            self.refresh_tier()
            messagebox.showinfo(t("lic_ok_title"), t("lic_ok"), parent=win)
            win.destroy()

        ttk.Button(win, text=t("lic_unlock"), command=save).pack(pady=10)

    # ------------------------------------------------------------------ jobs
    def _guard(self) -> bool:
        if self._busy:
            messagebox.showinfo(t("busy_title"), t("busy"))
            return False
        try:
            find_ffmpeg()
        except FileNotFoundError:
            messagebox.showerror(t("ffmpeg_missing_title"), t("ffmpeg_missing"))
            return False
        return True

    def do_convert(self) -> None:
        if not self._guard():
            return
        src = self.video_path.get().strip()
        if not src:
            messagebox.showwarning(t("no_file_title"), t("no_video"))
            return
        dest = self._ask_save(Path(src).with_suffix(".gif").name)
        if not dest:
            return
        opts = ConvertOptions(start=float(self.start.get()), duration=float(self.duration.get()),
                              width=int(self.width.get()), fps=int(self.fps.get()))
        self._run_job(lambda: video_to_gif(src, dest, opts, log=self._set_status))

    def do_compress(self) -> None:
        if not self._guard():
            return
        src = self.gif_path.get().strip()
        if not src:
            messagebox.showwarning(t("no_file_title"), t("no_gif"))
            return
        dest = self._ask_save(Path(src).stem + "_compressed.gif", "dlg_save_compressed")
        if not dest:
            return
        opts = CompressOptions(scale=float(self.c_scale.get()), fps=int(self.c_fps.get()),
                               colors=int(self.c_colors.get()))
        self._run_job(lambda: compress_gif(src, dest, opts, log=self._set_status))

    def _social_job(self, src: str, dest: str, key: str, start: float, duration: float,
                    screen: bool) -> Callable[[], str]:
        def job() -> str:
            res = social_gif(src, dest, key, start=start, duration=duration,
                             screen_recording=screen, log=self._set_status)
            p = res.final
            if res.fits:
                msg = t("social_result_fit", size=fmt_size(res.size), target=fmt_size(res.preset.max_bytes),
                        width=p.width, fps=p.fps, colors=p.colors, tries=len(res.attempts))
            else:
                msg = t("social_result_over", size=fmt_size(res.size), target=fmt_size(res.preset.max_bytes))
            return f"{res.path}\n\n{msg}"
        return job

    def do_social(self) -> None:
        if not self._guard():
            return
        src = self.social_path.get().strip()
        if not src:
            messagebox.showwarning(t("no_file_title"), t("no_media"))
            return
        key = self.s_preset.get()
        dest = self._ask_save(f"{Path(src).stem}_{key}.gif")
        if not dest:
            return
        self._run_job(self._social_job(src, dest, key, float(self.s_start.get()),
                                       float(self.s_duration.get()), False), raw=True)

    # ------------------------------------------------------------- recording
    def select_region(self) -> None:
        self.withdraw()

        def done(region: Optional[Region]) -> None:
            self.deiconify()
            if region:
                self.r_mode.set("region")
                for var, v in zip((self.r_x, self.r_y, self.r_w, self.r_h),
                                  (region.x, region.y, region.w, region.h)):
                    var.set(str(v))

        self.after(200, lambda: RegionSelector(self, done))

    def _region(self) -> Optional[Region]:
        if self.r_mode.get() == "full":
            return Region(0, 0, self.winfo_screenwidth(), self.winfo_screenheight())
        return Region.parse(",".join(v.get() for v in (self.r_x, self.r_y, self.r_w, self.r_h)))

    def start_recording(self) -> None:
        if not self._guard():
            return
        try:
            region = self._region()
        except ValueError:
            messagebox.showwarning(t("rec_failed"), t("rec_bad_region"))
            return
        if not (sys.platform == "win32" or sys.platform.startswith("linux")):
            messagebox.showerror(t("rec_failed"), t("rec_unsupported"))
            return
        try:
            rec = Recorder(region=region, fps=int(self.r_fps.get()), cursor=bool(self.r_cursor.get()))
        except (ConvertError, FileNotFoundError) as e:
            messagebox.showerror(t("rec_failed"), str(e))
            return
        self._busy = True
        self._recorder = rec
        self.iconify()
        self._countdown(int(self.r_countdown.get()))

    def _countdown(self, n: int) -> None:
        if n <= 0:
            self._begin_capture()
            return
        win = tk.Toplevel(self)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        win.geometry(f"260x140+{sw // 2 - 130}+{sh // 2 - 70}")
        lbl = ttk.Label(win, font=("TkDefaultFont", 40, "bold"), anchor="center")
        lbl.pack(fill="both", expand=True)
        sub = ttk.Label(win, anchor="center")
        sub.pack(fill="x", pady=(0, 10))

        def tick(k: int) -> None:
            if k <= 0:
                win.destroy()
                # let the overlay disappear before the first captured frame
                self.after(250, self._begin_capture)
                return
            lbl.configure(text=str(k))
            sub.configure(text=t("rec_starting_in", n=k))
            self.after(1000, lambda: tick(k - 1))

        tick(n)

    def _begin_capture(self) -> None:
        rec = self._recorder
        assert rec is not None
        try:
            rec.start()
        except ConvertError as e:
            self._busy = False
            self.deiconify()
            messagebox.showerror(t("rec_failed"), str(e))
            return
        # small always-on-top control, bottom-right corner
        win = tk.Toplevel(self)
        win.attributes("-topmost", True)
        win.title(t("tab_record"))
        win.resizable(False, False)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        win.geometry(f"+{sw - 300}+{sh - 140}")
        self._rec_label = tk.StringVar()
        ttk.Label(win, textvariable=self._rec_label, foreground="#dc2626").pack(padx=12, pady=(10, 4))
        ttk.Button(win, text=t("rec_stop"), command=self.stop_recording).pack(padx=12, pady=(0, 10))
        win.protocol("WM_DELETE_WINDOW", self.stop_recording)
        self._rec_win = win
        self._poll_recording()

    def _poll_recording(self) -> None:
        rec = self._recorder
        if rec is None or self._rec_win is None:
            return
        el = fmt_secs(rec.elapsed())
        if rec.max_seconds:
            self._rec_label.set(t("rec_recording_cap", elapsed=el, sec=int(rec.max_seconds)))
        else:
            self._rec_label.set(t("rec_recording", elapsed=el))
        if not rec.running:  # free cap reached (ffmpeg -t) or capture died
            self.stop_recording()
            return
        self.after(250, self._poll_recording)

    def stop_recording(self) -> None:
        rec = self._recorder
        if rec is None or self._rec_win is None:
            return
        win, self._rec_win = self._rec_win, None
        win.destroy()
        secs = rec.elapsed()
        try:
            video = rec.stop()
        except ConvertError as e:
            self._busy = False
            self._recorder = None
            rec.cleanup()
            self.deiconify()
            messagebox.showerror(t("rec_failed"), str(e))
            return
        self.deiconify()
        self.status.set(t("rec_saved_video", sec=int(secs)))
        key = self.r_output.get()
        dest = self._ask_save(f"recording_{key}.gif")
        if not dest:
            self._busy = False
            self._recorder = None
            rec.cleanup()
            self.status.set(t("app_ready"))
            return
        self._busy = False  # _run_job sets it again
        dur = secs + 1.0  # the free 15s clamp is applied inside the converter
        if key == "standard":
            opts = ConvertOptions(start=0.0, duration=dur, width=int(self.width.get()),
                                  fps=int(self.r_fps.get()))
            job: Callable[[], object] = lambda: video_to_gif(video, dest, opts, log=self._set_status)
            raw = False
        else:
            job = self._social_job(str(video), dest, key, 0.0, dur, True)
            raw = True

        def wrapped():
            try:
                return job()
            finally:
                rec.cleanup()
                self._recorder = None

        self._run_job(wrapped, raw=raw)

    # ---------------------------------------------------------------- runner
    def _set_status(self, msg: str) -> None:
        self.after(0, lambda: self.status.set(msg))

    def _run_job(self, fn: Callable[[], object], raw: bool = False) -> None:
        """raw=True: fn returns the full success message; else a path."""
        self._busy = True
        self.status.set(t("working"))

        def worker() -> None:
            try:
                res = fn()
                if raw:
                    msg = str(res)
                else:
                    p = Path(str(res))
                    msg = t("done_saved", path=str(p), size=fmt_size(p.stat().st_size))
                self.after(0, lambda: self._done(True, msg))
            except Exception as e:  # noqa: BLE001
                err = str(e)
                self.after(0, lambda: self._done(False, err))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, ok: bool, msg: str) -> None:
        self._busy = False
        self.status.set(msg.replace("\n\n", " — ") if ok else t("error_prefix", msg=msg))
        if ok:
            messagebox.showinfo(t("done_title"), msg)
        else:
            messagebox.showerror(t("failed_title"), msg)


def run() -> None:
    _enable_dpi_awareness()
    app = App()
    app.mainloop()
