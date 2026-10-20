"""Video → GIF, GIF compress and social-preset encodes via system/bundled ffmpeg."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import license_check
from .paths import escape_drawtext_path, escape_drawtext_text, find_ffmpeg, find_font

ProgressCb = Optional[Callable[[str], None]]

DITHERS = ("bayer", "sierra2_4a", "floyd_steinberg", "none")


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


@dataclass
class EncodeParams:
    """One concrete GIF encode (used by the social-preset fit loop)."""

    width: int = 480          # max width; never upscales
    fps: int = 10
    colors: int = 256
    dither: str = "bayer"      # see DITHERS
    bayer_scale: int = 3
    decimate: bool = False     # mpdecimate: drop near-duplicate frames (screen recordings)


class ConvertError(RuntimeError):
    pass


def _popen_flags() -> dict:
    # Hide the console window of ffmpeg when launched from the windowed exe.
    if sys.platform == "win32":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def _run(cmd: list[str], log: ProgressCb = None) -> None:
    if log:
        log(" ".join(cmd[:6]) + (" …" if len(cmd) > 6 else ""))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **_popen_flags(),
        )
    except FileNotFoundError as e:
        raise ConvertError(str(e)) from e
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        tail = "\n".join(err.splitlines()[-12:])
        raise ConvertError(f"ffmpeg failed ({proc.returncode}):\n{tail}")


def _want_watermark(explicit: Optional[bool]) -> bool:
    """Watermark is mandatory unless a valid pro license is installed.

    `explicit=True` can force a watermark (e.g. previews); `explicit=False`
    is ignored without a valid license — there is no free bypass.
    """
    paid = license_check.current_license().is_paid
    if explicit is True:
        return True
    return not paid


def _clamp_duration(duration: float, paid: bool) -> float:
    if paid:
        return max(0.1, float(duration))
    return max(0.1, min(float(duration), license_check.FREE_MAX_SECONDS))


def _wm_filter(enabled: bool) -> str:
    if not enabled:
        return ""
    font = escape_drawtext_path(find_font())
    text = escape_drawtext_text(license_check.WATERMARK_TEXT)
    # Readable bottom-right watermark (min font size so tiny stickers stay legible)
    return (
        f"drawtext=fontfile='{font}':text='{text}':fontsize='max(10,h*0.045)':"
        f"fontcolor=white@0.9:borderw=2:bordercolor=black@0.55:"
        f"x=w-tw-6:y=h-th-6"
    )


def build_filters(p: EncodeParams, watermark: bool) -> tuple[str, str]:
    """Return (palettegen_vf, paletteuse_lavfi) for one encode."""
    fps = max(1, min(50, int(p.fps)))
    width = max(32, int(p.width))
    colors = max(2, min(256, int(p.colors)))
    dither = p.dither if p.dither in DITHERS else "bayer"
    parts = [f"fps={fps}"]
    if p.decimate:
        parts.append("mpdecimate=hi=768:lo=320:frac=0.5")
    # never upscale; keep aspect; even-ish height not required for GIF
    parts.append(f"scale='min(iw,{width})':-1:flags=lanczos")
    wm = _wm_filter(watermark)
    if wm:
        parts.append(wm)
    chain = ",".join(parts)
    gen = f"{chain},palettegen=max_colors={colors}:stats_mode=diff"
    use = f"paletteuse=dither={dither}"
    if dither == "bayer":
        use += f":bayer_scale={max(0, min(5, int(p.bayer_scale)))}"
    use += ":diff_mode=rectangle"
    lavfi = f"{chain}[x];[x][1:v]{use}"
    return gen, lavfi


def encode_gif(
    inp: Path,
    out: Path,
    params: EncodeParams,
    *,
    start: float = 0.0,
    duration: Optional[float] = None,
    watermark: bool = True,
    log: ProgressCb = None,
) -> Path:
    """Two-pass palettegen/paletteuse encode. Caller decides watermark/duration."""
    ffmpeg = find_ffmpeg()
    gen_vf, lavfi = build_filters(params, watermark)
    trim: list[str] = []
    if start and start > 0:
        trim += ["-ss", str(start)]
    if duration is not None:
        trim += ["-t", str(duration)]
    vsync = ["-fps_mode", "vfr"] if params.decimate else []
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nero-gif-") as td:
        palette = Path(td) / "palette.png"
        _run([ffmpeg, "-y", *trim, "-i", str(inp), "-vf", gen_vf, "-frames:v", "1",
              "-update", "1", str(palette)], log)
        _run([ffmpeg, "-y", *trim, "-i", str(inp), "-i", str(palette),
              "-lavfi", lavfi, *vsync, "-loop", "0", str(out)], log)
    if not out.is_file() or out.stat().st_size < 32:
        raise ConvertError("Output GIF missing or empty")
    return out


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

    paid = license_check.current_license().is_paid
    use_wm = _want_watermark(opts.watermark)
    duration = _clamp_duration(opts.duration, paid)
    width = max(64, int(opts.width))
    fps = max(1, min(30, int(opts.fps)))
    start = max(0.0, float(opts.start))

    params = EncodeParams(width=width, fps=fps, colors=256, dither="bayer", bayer_scale=5)
    encode_gif(inp, out, params, start=start, duration=duration, watermark=use_wm, log=log)
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

    paid = license_check.current_license().is_paid
    use_wm = _want_watermark(opts.watermark)
    scale = float(opts.scale)
    if scale <= 0 or scale > 1.5:
        raise ConvertError("scale must be between 0 and 1.5")
    colors = max(2, min(256, int(opts.colors)))
    fps = int(opts.fps)
    # Free tier: the 15s cap also applies to GIF re-encodes.
    duration = None if paid else license_check.FREE_MAX_SECONDS

    parts = [f"scale=iw*{scale}:-1:flags=lanczos"]
    if fps > 0:
        parts.insert(0, f"fps={fps}")
    wm = _wm_filter(use_wm)
    if wm:
        parts.append(wm)
    vf = ",".join(parts)
    trim = ["-t", str(duration)] if duration else []

    ffmpeg = find_ffmpeg()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nero-gif-c-") as td:
        palette = Path(td) / "palette.png"
        _run(
            [
                ffmpeg, "-y", *trim, "-i", str(inp),
                "-vf", f"{vf},palettegen=max_colors={colors}:stats_mode=diff",
                "-frames:v", "1", "-update", "1",
                str(palette),
            ],
            log,
        )
        filt = f"{vf}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5"
        _run(
            [
                ffmpeg, "-y", *trim,
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
