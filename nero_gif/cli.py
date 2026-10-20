"""Command-line entry for testing and headless use."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __app_name__, __version__, license_check
from .converter import CompressOptions, ConvertError, ConvertOptions, compress_gif, video_to_gif
from .paths import find_ffmpeg
from .presets import MB, PRESETS, social_gif


for _stream in (sys.stdout, sys.stderr):
    # Windows consoles/CI often use cp1252; never crash on labels like "\u2264".
    try:
        if _stream is not None:
            _stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass


def _log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except (UnicodeEncodeError, ValueError, OSError, AttributeError):
        pass


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


def cmd_presets(_: argparse.Namespace) -> int:
    for k, p in PRESETS.items():
        steps = " | ".join(f"{e.width}px/{e.fps}fps/{e.colors}c" for e in p.ladder)
        print(f"{k:8s} target<={p.max_bytes / MB:.2f}MB  {p.label}  [{steps}]")
    return 0


def cmd_social(args: argparse.Namespace) -> int:
    out = Path(args.output) if args.output else Path(args.input).with_name(
        f"{Path(args.input).stem}_{args.preset}.gif")
    try:
        res = social_gif(args.input, out, args.preset, start=args.start, duration=args.duration,
                         screen_recording=args.screen, watermark=True if args.force_free else None,
                         log=_log)
    except ConvertError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    f = res.final
    print(f"{out}\nsize={res.size} bytes ({res.size / MB:.2f} MB) target={res.preset.max_bytes} "
          f"fits={res.fits} tries={len(res.attempts)} final={f.width}px/{f.fps}fps/{f.colors}c/{f.dither}")
    return 0 if res.fits else 2


def cmd_record(args: argparse.Namespace) -> int:
    import time

    from .recorder import Recorder, Region

    try:
        region = Region.parse(args.region) if args.region else None
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    try:
        rec = Recorder(region=region, fps=args.fps, cursor=not args.no_cursor)
    except (ConvertError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if args.countdown:
        for i in range(int(args.countdown), 0, -1):
            print(f"recording in {i}…", flush=True)
            time.sleep(1)
    try:
        rec.start()
        print(f"recording ({' '.join(rec.cmd[5:-1])}) — Ctrl+C to stop", flush=True)
        try:
            while rec.running and rec.elapsed() < args.seconds:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        secs = rec.elapsed()
        video = rec.stop()
        out = Path(args.output)
        if args.preset:
            res = social_gif(video, out, args.preset, duration=secs + 1, screen_recording=True,
                             watermark=True if args.force_free else None, log=_log)
            print(f"size={res.size} fits={res.fits}")
        else:
            opts = ConvertOptions(duration=secs + 1, width=args.width, fps=args.fps,
                                  watermark=True if args.force_free else None)
            video_to_gif(video, out, opts, log=_log)
    except ConvertError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    finally:
        rec.cleanup()
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

    pr = sub.add_parser("presets", help="List social presets")
    pr.set_defaults(func=cmd_presets)

    so = sub.add_parser("social", help="Perfect social GIF (auto size-fit)")
    so.add_argument("input")
    so.add_argument("--preset", required=True, choices=list(PRESETS))
    so.add_argument("-o", "--output", default=None)
    so.add_argument("--start", type=float, default=0.0)
    so.add_argument("--duration", type=float, default=None)
    so.add_argument("--screen", action="store_true", help="Input is a screen recording (mpdecimate)")
    so.add_argument("--force-free", action="store_true")
    so.set_defaults(func=cmd_social)

    r = sub.add_parser("record", help="Record screen → GIF (gdigrab on Windows, x11grab on Linux)")
    r.add_argument("-o", "--output", required=True)
    r.add_argument("--region", default=None, help="x,y,w,h (default: full screen)")
    r.add_argument("--seconds", type=float, default=5.0, help="Stop after N seconds (free max 15)")
    r.add_argument("--fps", type=int, default=12)
    r.add_argument("--width", type=int, default=480)
    r.add_argument("--countdown", type=int, default=0)
    r.add_argument("--no-cursor", action="store_true")
    r.add_argument("--preset", default=None, choices=list(PRESETS))
    r.add_argument("--force-free", action="store_true")
    r.set_defaults(func=cmd_record)

    u = sub.add_parser("unlock", help="Save a pro license key")
    u.add_argument("key")
    u.set_defaults(func=cmd_unlock)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))
