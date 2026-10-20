"""Screen-capture command builder (gdigrab / x11grab) — no display needed."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from nero_gif.recorder import Region, build_capture_cmd


class RegionTests(unittest.TestCase):
    def test_parse(self) -> None:
        self.assertEqual(Region.parse("10,20,300,200"), Region(10, 20, 300, 200))
        self.assertEqual(Region.parse(" 10 20 300 200 "), Region(10, 20, 300, 200))
        for bad in ("1,2,3", "a,b,c,d", "0,0,0,10", "0,0,10,-5"):
            with self.assertRaises(ValueError):
                Region.parse(bad)

    def test_normalised_even(self) -> None:
        r = Region(-1920, 5, 401, 301).normalised()
        self.assertEqual((r.x, r.y, r.w, r.h), (-1920, 5, 400, 300))
        self.assertEqual(Region(0, 0, 3, 3).normalised().w, 16)


class CaptureCmdTests(unittest.TestCase):
    def test_gdigrab_region(self) -> None:
        cmd = build_capture_cmd("ffmpeg.exe", Path("o.mp4"), region=Region(100, 50, 641, 480),
                                fps=12, cursor=False, max_seconds=15, platform="win32",
                                encoder=["-c:v", "libx264"])
        s = " ".join(cmd)
        self.assertIn("-f gdigrab -framerate 12 -draw_mouse 0", s)
        self.assertIn("-offset_x 100 -offset_y 50 -video_size 640x480 -i desktop", s)
        self.assertIn("-t 15", s)
        self.assertEqual(cmd[-1], "o.mp4")
        # options must come before -i desktop
        self.assertLess(cmd.index("-offset_x"), cmd.index("desktop"))

    def test_gdigrab_full_cursor_no_cap(self) -> None:
        cmd = build_capture_cmd("ffmpeg.exe", Path("o.mkv"), platform="win32")
        self.assertIn("desktop", cmd)
        self.assertNotIn("-offset_x", cmd)
        self.assertNotIn("-t", cmd)
        self.assertEqual(cmd[cmd.index("-draw_mouse") + 1], "1")

    def test_x11grab(self) -> None:
        cmd = build_capture_cmd("ffmpeg", Path("o.mkv"), region=Region(10, 20, 200, 100),
                                platform="linux", display=":1")
        s = " ".join(cmd)
        self.assertIn("-f x11grab", s)
        self.assertIn("-video_size 200x100 -i :1+10,20", s)

    def test_unsupported(self) -> None:
        from nero_gif.converter import ConvertError

        with self.assertRaises(ConvertError):
            build_capture_cmd("ffmpeg", Path("o.mkv"), platform="darwin")


@unittest.skipUnless(sys.platform.startswith("linux") and os.environ.get("DISPLAY")
                     and shutil.which("ffmpeg"), "needs Linux X display + ffmpeg")
class X11LiveTests(unittest.TestCase):
    def test_record_and_stop_with_q(self) -> None:
        from nero_gif.recorder import Recorder

        with tempfile.TemporaryDirectory() as td:
            rec = Recorder(Region(0, 0, 320, 240), fps=10, out_dir=Path(td))
            rec.start()
            time.sleep(1.5)
            p = rec.stop()
            self.assertGreater(p.stat().st_size, 256)
            self.assertEqual(rec.proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
