"""Social preset size-fit loop (fake encoder, no ffmpeg) + filter builder."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nero_gif.converter import EncodeParams, build_filters
from nero_gif.presets import MAX_TRIES, MB, PRESETS, SocialPreset, fit_loop


def fake_encoder(base_bytes: float, calls: list):
    """Size model ~ width^2 * fps * colors^0.5; writes a dummy file of that size."""

    def enc(p: EncodeParams, tmp: Path) -> int:
        size = int(base_bytes * (p.width / 640) ** 2 * (p.fps / 15) * (p.colors / 256) ** 0.5
                   * (0.8 if p.decimate else 1.0))
        tmp.write_bytes(b"G" * min(size, 4096))  # small on disk; size is what we report
        calls.append((p, size))
        return size

    return enc


class FitLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.out = Path(self.td.name) / "out.gif"

    def tearDown(self) -> None:
        self.td.cleanup()

    def test_every_preset_has_ladder_that_shrinks(self) -> None:
        for key, p in PRESETS.items():
            self.assertGreaterEqual(len(p.ladder), 2, key)
            self.assertLessEqual(len(p.ladder), MAX_TRIES, key)
            for a, b in zip(p.ladder, p.ladder[1:]):
                self.assertGreaterEqual(a.width, b.width, key)
                self.assertGreaterEqual(a.fps, b.fps, key)
                self.assertGreaterEqual(a.colors, b.colors, key)
                self.assertTrue((a.width, a.fps, a.colors) != (b.width, b.fps, b.colors), key)

    def test_targets_under_platform_limits(self) -> None:
        limits = {"x": 15, "discord": 10, "reddit": 20, "sticker": 1, "github": 10}
        for k, lim in limits.items():
            self.assertLess(PRESETS[k].max_bytes, lim * MB, k)

    def test_small_input_fits_first_try(self) -> None:
        calls: list = []
        res = fit_loop(PRESETS["discord"], self.out, fake_encoder(1 * MB, calls))
        self.assertTrue(res.fits)
        self.assertEqual(len(res.attempts), 1)
        self.assertEqual(len(calls), 1)
        self.assertTrue(self.out.is_file())

    def test_steps_down_until_fit(self) -> None:
        calls: list = []
        res = fit_loop(PRESETS["discord"], self.out, fake_encoder(30 * MB, calls))
        self.assertTrue(res.fits)
        self.assertGreater(len(res.attempts), 1)
        self.assertLessEqual(res.size, PRESETS["discord"].max_bytes)
        # stops as soon as it fits
        self.assertTrue(all(a.size > PRESETS["discord"].max_bytes for a in res.attempts[:-1]))
        self.assertEqual(res.final, res.attempts[-1].params)

    def test_gives_up_after_max_tries_keeps_smallest(self) -> None:
        calls: list = []
        res = fit_loop(PRESETS["sticker"], self.out, fake_encoder(500 * MB, calls))
        self.assertFalse(res.fits)
        self.assertEqual(len(calls), MAX_TRIES)
        self.assertEqual(res.size, min(a.size for a in res.attempts))
        self.assertTrue(self.out.is_file())

    def test_force_decimate(self) -> None:
        calls: list = []
        fit_loop(PRESETS["x"], self.out, fake_encoder(1 * MB, calls), force_decimate=True)
        self.assertTrue(calls[0][0].decimate)
        # preset objects are not mutated
        self.assertFalse(PRESETS["x"].ladder[0].decimate)

    def test_max_tries_respected(self) -> None:
        p = SocialPreset("t", "t", 1, tuple(EncodeParams(width=w) for w in (600, 500, 400, 300, 200, 100)))
        calls: list = []
        res = fit_loop(p, self.out, fake_encoder(100 * MB, calls))
        self.assertEqual(len(calls), MAX_TRIES)
        self.assertFalse(res.fits)


class FilterTests(unittest.TestCase):
    def test_filters_contain_palette_and_dither(self) -> None:
        gen, use = build_filters(EncodeParams(width=480, fps=12, colors=128, dither="sierra2_4a",
                                              decimate=True), watermark=False)
        self.assertIn("palettegen=max_colors=128:stats_mode=diff", gen)
        self.assertIn("paletteuse=dither=sierra2_4a", use)
        self.assertIn("mpdecimate", gen)
        self.assertIn("scale='min(iw,480)'", gen)
        self.assertNotIn("drawtext", gen)

    def test_bayer_scale_and_watermark(self) -> None:
        gen, use = build_filters(EncodeParams(dither="bayer", bayer_scale=2), watermark=True)
        self.assertIn("bayer_scale=2", use)
        self.assertIn("drawtext", gen)
        self.assertIn("drawtext", use)


if __name__ == "__main__":
    unittest.main()
