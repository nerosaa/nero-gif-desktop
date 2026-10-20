"""Video → GIF and GIF compress via system/bundled ffmpeg."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import license_check
from .paths import escape_drawtext_path, escape_drawtext_text, find_ffmpeg, find_font

ProgressCb = Optional[Callable[[str], None]]


@dataclass
class ConvertOptions:
    start: float = 0.0
    duration: float = 5.0
    width: int = 480
    fps: int = 10
    watermark: Optional[bool] = None  # None = auto from license


@dataclass
class CompressOptions:
    scale: float = 0.75
    fps: int = 10  # 0 = keep
    colors: int = 128
    watermark: Optional[bool] = None


class ConvertError(RuntimeError):
    pass


def _run(cmd: list[str], log: ProgressCb = None) -> None:
    if log:
        log(" ".join(cmd[:6]) + (" …" if len(cmd) > 6 else ""))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise ConvertError(str(e)) from e
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        tail = "\n".join(err.splitlines()[-12:])
        raise ConvertError(f"ffmpeg failed ({proc.returncode}):\n{tail}")


def _want_watermark(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return explicit
    return not license_check.current_license().is_paid


def _clamp_duration(duration: float, paid: bool) -> float:
    if paid:
        return max(0.1, float(duration))
    return max(0.1, min(float(duration), license_check.FREE_MAX_SECONDS))


def _wm_filter(enabled: bool) -> str:
    if not enabled:
        return ""
    font = escape_drawtext_path(find_font())
    text = escape_drawtext_text(license_check.WATERMARK_TEXT)
    # Readable bottom-right watermark
    return (
        f"drawtext=fontfile='{font}':text='{text}':fontsize=h*0.045:"
        f"fontcolor=white@0.9:borderw=2:bordercolor=black@0.55:"
        f"x=w-tw-10:y=h-th-10"
    )


def video_to_gif(
    input_path: str | Path,
    output_path: str | Path,
    opts: ConvertOptions | None = None,
    log: ProgressCb = None,
) -> Path:
    opts = opts or ConvertOptions()
    inp = Path(input_path)
    out = Path(output_path)
    if not inp.is_file():
        raise ConvertError(f"Input not found: {inp}")

    lic = license_check.current_license()
    paid = lic.is_paid
    use_wm = _want_watermark(opts.watermark)
    duration = _clamp_duration(opts.duration, paid)
    width = max(64, int(opts.width))
    fps = max(1, min(30, int(opts.fps)))
    start = max(0.0, float(opts.start))

    ffmpeg = find_ffmpeg()
    base_vf = f"fps={fps},scale={width}:-1:flags=lanczos"
    wm = _wm_filter(use_wm)
    vf_chain = f"{base_vf},{wm}" if wm else base_vf

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nero-gif-") as td:
        palette = Path(td) / "palette.png"
        # Pass 1: palette
        _run(
            [
                ffmpeg, "-y",
                "-ss", str(start),
                "-t", str(duration),
                "-i", str(inp),
                "-vf", f"{vf_chain},palettegen=stats_mode=diff",
                str(palette),
            ],
            log,
        )
        # Pass 2: encode with palette
        filt = f"{vf_chain}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5"
        _run(
            [
                ffmpeg, "-y",
                "-ss", str(start),
                "-t", str(duration),
                "-i", str(inp),
                "-i", str(palette),
                "-lavfi", filt,
                "-loop", "0",
                str(out),
            ],
            log,
        )

    if not out.is_file() or out.stat().st_size < 32:
        raise ConvertError("Output GIF missing or empty")
    if log:
        mode = "paid (no watermark)" if not use_wm else "free (watermarked)"
        log(f"Wrote {out} ({out.stat().st_size} bytes) [{mode}, {duration}s]")
    return out


def compress_gif(
    input_path: str | Path,
    output_path: str | Path,
    opts: CompressOptions | None = None,
    log: ProgressCb = None,
) -> Path:
    opts = opts or CompressOptions()
    inp = Path(input_path)
    out = Path(output_path)
    if not inp.is_file():
        raise ConvertError(f"Input not found: {inp}")

    use_wm = _want_watermark(opts.watermark)
    scale = float(opts.scale)
    if scale <= 0 or scale > 1.5:
        raise ConvertError("scale must be between 0 and 1.5")
    colors = max(2, min(256, int(opts.colors)))
    fps = int(opts.fps)

    parts = [f"scale=iw*{scale}:-1:flags=lanczos"]
    if fps > 0:
        parts.insert(0, f"fps={fps}")
    wm = _wm_filter(use_wm)
    if wm:
        parts.append(wm)
    vf = ",".join(parts)

    ffmpeg = find_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nero-gif-c-") as td:
        palette = Path(td) / "palette.png"
        _run(
            [
                ffmpeg, "-y", "-i", str(inp),
                "-vf", f"{vf},palettegen=max_colors={colors}:stats_mode=diff",
                str(palette),
            ],
            log,
        )
        filt = f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5"
        _run(
            [
                ffmpeg, "-y",
                "-i", str(inp),
                "-i", str(palette),
                "-lavfi", filt,
                "-loop", "0",
                str(out),
            ],
            log,
        )

    if not out.is_file() or out.stat().st_size < 32:
        raise ConvertError("Output GIF missing or empty")
    if log:
        log(f"Compressed → {out} ({out.stat().st_size} bytes)")
    return out
