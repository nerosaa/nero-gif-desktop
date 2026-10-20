"""Screen recording → temp video → GIF.

Windows: ffmpeg gdigrab (`-f gdigrab -offset_x X -offset_y Y -video_size WxH -i desktop`).
Linux:   ffmpeg x11grab (`-f x11grab -video_size WxH -i :0.0+X,Y`) — used for tests.
Stop is clean: we write 'q' to ffmpeg's stdin so the container is finalised.
Free tier: recording is hard-capped at FREE_MAX_SECONDS via `-t`, and the GIF
step adds the watermark (license rules live in converter/license_check).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import license_check
from .converter import ConvertError, _popen_flags
from .paths import find_ffmpeg


@dataclass(frozen=True)
class Region:
    x: int
    y: int
    w: int
    h: int

    def normalised(self) -> "Region":
        """Even width/height (yuv420p/x264 need it), min 16px.

        x/y may be negative on Windows (monitor left of / above the primary).
        """
        w = max(16, int(self.w)) // 2 * 2
        h = max(16, int(self.h)) // 2 * 2
        return Region(int(self.x), int(self.y), w, h)

    @staticmethod
    def parse(text: str) -> "Region":
        """Parse "x,y,w,h" (also accepts spaces / 'x')."""
        parts = [p for p in text.replace("x", ",").replace(" ", ",").split(",") if p.strip()]
        if len(parts) != 4:
            raise ValueError("region must be x,y,w,h")
        x, y, w, h = (int(float(p)) for p in parts)
        if w <= 0 or h <= 0:
            raise ValueError("region width/height must be > 0")
        return Region(x, y, w, h)


def pick_encoder(ffmpeg: str) -> list[str]:
    """Fast intermediate codec: libx264 ultrafast if present, else lossless ffv1."""
    try:
        out = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True,
                             text=True, errors="replace", timeout=20, **_popen_flags()).stdout
    except Exception:  # noqa: BLE001
        out = ""
    if "libx264" in out:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p"]
    return ["-c:v", "ffv1"]


def build_capture_cmd(
    ffmpeg: str,
    out: Path,
    *,
    region: Optional[Region] = None,
    fps: int = 15,
    cursor: bool = True,
    max_seconds: Optional[float] = None,
    platform: Optional[str] = None,
    display: Optional[str] = None,
    encoder: Optional[list[str]] = None,
) -> list[str]:
    """Build the ffmpeg capture command. Pure function (unit-tested)."""
    plat = platform or sys.platform
    fps = max(1, min(60, int(fps)))
    enc = encoder if encoder is not None else ["-c:v", "ffv1"]
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    if plat == "win32":
        cmd += ["-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "1" if cursor else "0"]
        if region is not None:
            r = region.normalised()
            cmd += ["-offset_x", str(r.x), "-offset_y", str(r.y), "-video_size", f"{r.w}x{r.h}"]
        cmd += ["-i", "desktop"]
    elif plat.startswith("linux"):
        disp = display or os.environ.get("DISPLAY") or ":0"
        cmd += ["-f", "x11grab", "-framerate", str(fps), "-draw_mouse", "1" if cursor else "0"]
        if region is not None:
            r = region.normalised()
            cmd += ["-video_size", f"{r.w}x{r.h}", "-i", f"{disp}+{max(0, r.x)},{max(0, r.y)}"]
        else:
            cmd += ["-i", disp]
    else:
        raise ConvertError(f"Screen recording is not supported on {plat} yet")
    if max_seconds is not None:
        cmd += ["-t", f"{float(max_seconds):g}"]
    # full-screen captures can be odd-sized; crop to even for yuv420p
    cmd += ["-vf", "crop=trunc(iw/2)*2:trunc(ih/2)*2", *enc, str(out)]
    return cmd


class Recorder:
    """Start/stop wrapper around an ffmpeg capture process."""

    def __init__(
        self,
        region: Optional[Region] = None,
        fps: int = 15,
        cursor: bool = True,
        out_dir: Optional[Path] = None,
    ) -> None:
        self.region = region
        self.fps = fps
        self.cursor = cursor
        self.paid = license_check.current_license().is_paid
        self.max_seconds = None if self.paid else license_check.FREE_MAX_SECONDS
        self._dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="nero-rec-"))
        self.ffmpeg = find_ffmpeg()
        enc = pick_encoder(self.ffmpeg)
        ext = ".mp4" if "libx264" in enc else ".mkv"
        self.path = self._dir / f"recording{ext}"
        self.cmd = build_capture_cmd(
            self.ffmpeg, self.path, region=region, fps=fps, cursor=cursor,
            max_seconds=self.max_seconds, encoder=enc,
        )
        self.proc: Optional[subprocess.Popen] = None
        self.started_at = 0.0

    def start(self) -> None:
        self.proc = subprocess.Popen(
            self.cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, **_popen_flags(),
        )
        self.started_at = time.monotonic()
        time.sleep(0.3)
        if self.proc.poll() is not None:
            err = (self.proc.stderr.read() or b"").decode("utf-8", "replace") if self.proc.stderr else ""
            raise ConvertError(f"screen capture failed to start:\n{err.strip()[-800:]}")

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def elapsed(self) -> float:
        return time.monotonic() - self.started_at if self.started_at else 0.0

    def stop(self, timeout: float = 15.0) -> Path:
        """Send 'q' so ffmpeg finalises the file; fall back to terminate/kill."""
        if self.proc is None:
            raise ConvertError("recording was not started")
        if self.proc.poll() is None:
            try:
                assert self.proc.stdin is not None
                self.proc.stdin.write(b"q")
                self.proc.stdin.flush()
                self.proc.stdin.close()
            except (BrokenPipeError, OSError, AssertionError):
                pass
            try:
                self.proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait()
        err = ""
        if self.proc.stderr:
            try:
                err = self.proc.stderr.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                err = ""
            finally:
                self.proc.stderr.close()
        if not self.path.is_file() or self.path.stat().st_size < 256:
            raise ConvertError(f"recording is empty:\n{err.strip()[-800:]}")
        return self.path

    def cleanup(self) -> None:
        try:
            for p in self._dir.iterdir():
                p.unlink()
            self._dir.rmdir()
        except OSError:
            pass
