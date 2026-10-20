"""One-click "Perfect social GIF" presets with an auto size-fit loop.

Each preset has a byte target and up to MAX_TRIES encode ladders. The loop
encodes, checks the file size and steps down fps / width / colors until the
GIF fits (or the ladder is exhausted, in which case the smallest result is
kept and reported as not fitting). Free-tier rules still apply: watermark and
15s cap come from license_check, not from the preset.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import license_check
from .converter import (
    ConvertError,
    EncodeParams,
    ProgressCb,
    _clamp_duration,
    _want_watermark,
    encode_gif,
)

MAX_TRIES = 4
MB = 1024 * 1024


@dataclass(frozen=True)
class SocialPreset:
    key: str
    label: str              # English fallback; GUI uses i18n key f"preset_{key}"
    max_bytes: int
    ladder: tuple[EncodeParams, ...] = field(default_factory=tuple)


def _p(w: int, fps: int, colors: int, dither: str = "bayer", bs: int = 3, dec: bool = False) -> EncodeParams:
    return EncodeParams(width=w, fps=fps, colors=colors, dither=dither, bayer_scale=bs, decimate=dec)


# Targets are kept a bit under the platform limits so uploads never bounce.
PRESETS: dict[str, SocialPreset] = {
    p.key: p
    for p in (
        SocialPreset(
            "x", "X / Twitter (≤15 MB)", int(14.5 * MB),
            (_p(640, 15, 256, "sierra2_4a"), _p(560, 12, 192, "bayer", 4),
             _p(480, 10, 128, "bayer", 3, True), _p(400, 8, 96, "bayer", 2, True)),
        ),
        SocialPreset(
            "discord", "Discord (≤10 MB, free)", int(9.5 * MB),
            (_p(480, 15, 256, "sierra2_4a"), _p(480, 12, 160, "bayer", 4),
             _p(400, 10, 128, "bayer", 3, True), _p(320, 8, 96, "bayer", 2, True)),
        ),
        SocialPreset(
            "reddit", "Reddit (≤20 MB)", int(19 * MB),
            (_p(640, 15, 256, "sierra2_4a"), _p(560, 12, 192, "bayer", 4),
             _p(480, 10, 128, "bayer", 3, True), _p(400, 8, 96, "bayer", 2, True)),
        ),
        SocialPreset(
            "sticker", "Telegram / WeChat sticker (≤1 MB)", int(0.95 * MB),
            (_p(320, 12, 128, "bayer", 3), _p(280, 10, 96, "bayer", 2, True),
             _p(240, 8, 64, "bayer", 2, True), _p(200, 6, 48, "bayer", 1, True)),
        ),
        SocialPreset(
            "github", "GitHub README (≤10 MB)", int(9.5 * MB),
            (_p(800, 12, 256, "sierra2_4a"), _p(720, 10, 192, "bayer", 4),
             _p(640, 10, 128, "bayer", 3, True), _p(480, 8, 96, "bayer", 2, True)),
        ),
    )
}


@dataclass
class FitAttempt:
    params: EncodeParams
    size: int


@dataclass
class FitResult:
    path: Path
    size: int
    fits: bool
    preset: SocialPreset
    attempts: list[FitAttempt]
    final: EncodeParams


Encoder = Callable[[EncodeParams, Path], int]  # encode into path, return bytes


def fit_loop(
    preset: SocialPreset,
    out: Path,
    encoder: Encoder,
    *,
    force_decimate: bool = False,
    log: ProgressCb = None,
    max_tries: int = MAX_TRIES,
) -> FitResult:
    """Run the preset ladder until the output fits `preset.max_bytes`.

    `encoder(params, tmp_path) -> size` does the real work (ffmpeg) or is a
    fake in unit tests. The best (smallest, or first fitting) GIF ends up at
    `out`.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    attempts: list[FitAttempt] = []
    best_tmp: Optional[Path] = None
    best_size = None
    best_params: Optional[EncodeParams] = None
    with tempfile.TemporaryDirectory(prefix="nero-fit-") as td:
        for i, base in enumerate(preset.ladder[:max_tries]):
            params = EncodeParams(**{**base.__dict__})
            if force_decimate:
                params.decimate = True
            tmp = Path(td) / f"try{i}.gif"
            size = int(encoder(params, tmp))
            attempts.append(FitAttempt(params, size))
            if log:
                log(f"try {i + 1}/{min(max_tries, len(preset.ladder))}: {params.width}px "
                    f"{params.fps}fps {params.colors}c {params.dither} -> {size} bytes")
            if best_size is None or size < best_size or size <= preset.max_bytes:
                best_size, best_tmp, best_params = size, tmp, params
            if size <= preset.max_bytes:
                break
        if best_tmp is None or best_size is None or best_params is None:
            raise ConvertError("preset has no encode steps")
        if best_tmp.exists():
            shutil.copyfile(best_tmp, out)
        fits = best_size <= preset.max_bytes
    return FitResult(out, best_size, fits, preset, attempts, best_params)


def social_gif(
    input_path: str | Path,
    output_path: str | Path,
    preset_key: str,
    *,
    start: float = 0.0,
    duration: Optional[float] = None,
    screen_recording: bool = False,
    watermark: Optional[bool] = None,
    log: ProgressCb = None,
) -> FitResult:
    """Encode `input_path` (video or GIF) with a social preset, auto-fitting size."""
    if preset_key not in PRESETS:
        raise ConvertError(f"Unknown preset: {preset_key}")
    preset = PRESETS[preset_key]
    inp = Path(input_path)
    if not inp.is_file():
        raise ConvertError(f"Input not found: {inp}")
    paid = license_check.current_license().is_paid
    use_wm = _want_watermark(watermark)
    dur = None if (duration is None and paid) else _clamp_duration(
        duration if duration is not None else license_check.FREE_MAX_SECONDS, paid)
    start = max(0.0, float(start))

    def enc(params: EncodeParams, tmp: Path) -> int:
        encode_gif(inp, tmp, params, start=start, duration=dur, watermark=use_wm, log=None)
        return os.path.getsize(tmp)

    res = fit_loop(preset, Path(output_path), enc, force_decimate=screen_recording, log=log)
    if log:
        state = "fits" if res.fits else "still over target (smallest kept)"
        log(f"{preset.label}: {res.size / MB:.2f} MB, {state}")
    return res
