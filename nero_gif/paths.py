"""Resolve ffmpeg binary and a font usable by drawtext."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory of the frozen exe or the package parent (project root)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Where bundled assets live (PyInstaller _MEIPASS or project root)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return app_dir()


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        d = base / "NERO Tools" / "GIF Converter"
    else:
        d = Path.home() / ".config" / "nero-gif"
    d.mkdir(parents=True, exist_ok=True)
    return d


def find_ffmpeg() -> str:
    """Prefer bundled ffmpeg next to the app, then PATH."""
    candidates = [
        app_dir() / "ffmpeg.exe",
        app_dir() / "ffmpeg",
        app_dir() / "bin" / "ffmpeg.exe",
        app_dir() / "bin" / "ffmpeg",
        app_dir() / "third_party" / "ffmpeg" / "ffmpeg.exe",
        app_dir() / "third_party" / "ffmpeg" / "ffmpeg",
        resource_dir() / "ffmpeg.exe",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise FileNotFoundError(
        "ffmpeg not found. Install ffmpeg and add it to PATH, "
        "or place ffmpeg.exe next to this app (see README)."
    )


def find_font() -> str:
    """Return a TTF path for drawtext watermark."""
    bundled = [
        resource_dir() / "assets" / "DejaVuSans.ttf",
        app_dir() / "assets" / "DejaVuSans.ttf",
        resource_dir() / "assets" / "fonts" / "DejaVuSans.ttf",
    ]
    for b in bundled:
        if b.is_file():
            return str(b)

    win_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    windows = [
        win_fonts / "arial.ttf",
        win_fonts / "Arial.ttf",
        win_fonts / "segoeui.ttf",
        win_fonts / "calibri.ttf",
    ]
    linux = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    ]
    for p in windows + linux:
        if p.is_file():
            return str(p)
    raise FileNotFoundError(
        "No TTF font found for watermark. Place DejaVuSans.ttf in assets/."
    )


def escape_drawtext_path(path: str) -> str:
    """Escape a font path for ffmpeg drawtext on Windows/Unix."""
    # ffmpeg wants forward slashes; escape colon for Windows drive letters
    p = path.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p


def escape_drawtext_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )
