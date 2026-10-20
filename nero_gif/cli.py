"""Command-line entry for testing and headless use."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __app_name__, __version__, license_check
from .converter import CompressOptions, ConvertError, ConvertOptions, compress_gif, video_to_gif
from .paths import find_ffmpeg


def _log(msg: str) -> None:
    print(msg, flush=True)


def cmd_status(_: argparse.Namespace) -> int:
    lic = license_check.current_license()
    print(f"{__app_name__} {__version__}")
    try:
        print(f"ffmpeg: {find_ffmpeg()}")
    except FileNotFoundError as e:
        print(f"ffmpeg: MISSING ({e})")
    print(f"tier: {lic.tier} ({lic.note})")
    print(f"free max duration: {license_check.FREE_MAX_SECONDS}s")
    print(f"watermark text: {license_check.WATERMARK_TEXT!r}")
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    opts = ConvertOptions(
        start=args.start,
        duration=args.duration,
        width=args.width,
        fps=args.fps,
        watermark=None,
    )
    if args.force_free:
        opts.watermark = True
    out = Path(args.output) if args.output else Path(args.input).with_suffix(".gif")
    try:
        video_to_gif(args.input, out, opts, log=_log)
    except ConvertError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(out)
    return 0


def cmd_compress(args: argparse.Namespace) -> int:
    opts = CompressOptions(
        scale=args.scale,
        fps=args.fps,
        colors=args.colors,
        watermark=None,
    )
    if args.force_free:
        opts.watermark = True
    out = Path(args.output) if args.output else Path(args.input).with_name(
        Path(args.input).stem + "_compressed.gif"
    )
    try:
        compress_gif(args.input, out, opts, log=_log)
    except ConvertError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(out)
    return 0


def cmd_unlock(args: argparse.Namespace) -> int:
    try:
        dest = license_check.save_key(args.key)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"License saved to {dest}")
    print(license_check.current_license())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nero-gif", description=__app_name__)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="Show license + ffmpeg")
    s.set_defaults(func=cmd_status)

    c = sub.add_parser("convert", help="Video → GIF")
    c.add_argument("input")
    c.add_argument("-o", "--output", default=None)
    c.add_argument("--start", type=float, default=0.0)
    c.add_argument("--duration", type=float, default=5.0)
    c.add_argument("--width", type=int, default=480)
    c.add_argument("--fps", type=int, default=10)
    c.add_argument("--force-free", action="store_true", help="Force watermark")
    c.set_defaults(func=cmd_convert)

    g = sub.add_parser("compress", help="Compress / re-encode GIF")
    g.add_argument("input")
    g.add_argument("-o", "--output", default=None)
    g.add_argument("--scale", type=float, default=0.75)
    g.add_argument("--fps", type=int, default=10)
    g.add_argument("--colors", type=int, default=128)
    g.add_argument("--force-free", action="store_true")
    g.set_defaults(func=cmd_compress)

    u = sub.add_parser("unlock", help="Save a pro license key")
    u.add_argument("key")
    u.set_defaults(func=cmd_unlock)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))
