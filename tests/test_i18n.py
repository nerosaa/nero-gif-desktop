"""i18n coverage: every language has every key, same placeholders, all used keys exist."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from nero_gif import i18n

ROOT = Path(__file__).resolve().parent.parent
PH = re.compile(r"\{[a-z_]+\}")


class I18nTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.en = json.loads((i18n.locales_dir() / "en.json").read_text(encoding="utf-8"))

    def test_ten_languages(self) -> None:
        self.assertEqual(len(i18n.LANGUAGES), 10)
        for code in i18n.LANGUAGES:
            self.assertTrue((i18n.locales_dir() / f"{code}.json").is_file(), code)

    def test_every_language_has_every_key(self) -> None:
        for code in i18n.LANGUAGES:
            data = json.loads((i18n.locales_dir() / f"{code}.json").read_text(encoding="utf-8"))
            missing = set(self.en) - set(data)
            extra = set(data) - set(self.en)
            self.assertFalse(missing, f"{code} missing {sorted(missing)}")
            self.assertFalse(extra, f"{code} extra {sorted(extra)}")
            for k, v in self.en.items():
                self.assertTrue(isinstance(data[k], str) and data[k].strip(), f"{code}.{k} empty")
                self.assertEqual(sorted(PH.findall(v)), sorted(PH.findall(data[k])),
                                 f"{code}.{k} placeholders")

    def test_translations_differ_from_english(self) -> None:
        for code in i18n.LANGUAGES:
            if code == "en":
                continue
            data = json.loads((i18n.locales_dir() / f"{code}.json").read_text(encoding="utf-8"))
            same = [k for k in self.en if data[k] == self.en[k]]
            # brand-ish strings (e.g. "GIF", preset names) may stay identical; most must change
            self.assertLess(len(same), len(self.en) * 0.25, f"{code} mostly untranslated: {same}")

    def test_all_keys_used_in_code_exist(self) -> None:
        src = "".join((ROOT / "nero_gif" / f).read_text(encoding="utf-8") for f in ("gui.py",))
        used = set(re.findall(r"""\bt\(\s*["']([a-z0-9_]+)["']""", src))
        used |= {f"preset_{k}" for k in __import__("nero_gif.presets", fromlist=["PRESETS"]).PRESETS}
        used |= set(re.findall(r'"(lic_reason_[a-z]+)"', src))
        missing = used - set(self.en)
        self.assertFalse(missing, f"keys used in gui.py but not in en.json: {sorted(missing)}")

    def test_normalise_os_locales(self) -> None:
        cases = {
            "zh_CN.UTF-8": "zh-Hans", "zh-SG": "zh-Hans", "zh_TW": "zh-Hant", "zh_HK.UTF-8": "zh-Hant",
            "zh-Hant-TW": "zh-Hant", "ja_JP": "ja", "ko_KR.UTF-8": "ko", "pt_BR": "pt",
            "de_DE@euro": "de", "fr_CA": "fr", "ru_RU": "ru", "es_MX": "es", "en_US": "en",
            "C": None, "": None, "xx_YY": None,
        }
        for tag, want in cases.items():
            self.assertEqual(i18n.normalise(tag), want, tag)

    def test_t_formats_and_falls_back(self) -> None:
        i18n.set_language("en")
        self.assertEqual(i18n.t("tier_free", sec=15), "License: FREE — watermark on, max 15s")
        self.assertEqual(i18n.t("no_such_key"), "no_such_key")
        for code in i18n.LANGUAGES:
            i18n.set_language(code)
            self.assertIn("15", i18n.t("tier_free", sec=15))
        i18n.set_language("en")


if __name__ == "__main__":
    unittest.main()
