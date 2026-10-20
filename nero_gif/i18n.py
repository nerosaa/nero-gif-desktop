"""Tiny i18n: one JSON file per language in nero_gif/locales/.

- `t(key, **kw)` formats the string for the active language (falls back to English).
- Active language: saved choice in settings.json (config_dir), else OS locale, else English.
"""

from __future__ import annotations

import json
import locale
import os
import sys
from pathlib import Path
from typing import Optional

from .paths import config_dir

# code -> native name (order = switcher order)
LANGUAGES: dict[str, str] = {
    "en": "English",
    "zh-Hans": "简体中文",
    "zh-Hant": "繁體中文",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "pt": "Português",
    "de": "Deutsch",
    "fr": "Français",
    "ru": "Русский",
}
DEFAULT = "en"

_cache: dict[str, dict[str, str]] = {}
_active = DEFAULT


def locales_dir() -> Path:
    # Works from source and from PyInstaller (--add-data "nero_gif/locales;nero_gif/locales").
    here = Path(__file__).resolve().parent / "locales"
    if here.is_dir():
        return here
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "nero_gif" / "locales"
    return here


def load(code: str) -> dict[str, str]:
    if code not in _cache:
        path = locales_dir() / f"{code}.json"
        try:
            _cache[code] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache[code] = {}
    return _cache[code]


def normalise(tag: Optional[str]) -> Optional[str]:
    """Map an OS locale tag (zh_CN, zh-TW, pt_BR.UTF-8, ja_JP…) to a supported code."""
    if not tag:
        return None
    t = tag.split(".")[0].split("@")[0].replace("_", "-").lower()
    if not t or t in ("c", "posix"):
        return None
    if t.startswith("zh"):
        if any(x in t for x in ("hant", "-tw", "-hk", "-mo")):
            return "zh-Hant"
        return "zh-Hans"
    base = t.split("-")[0]
    for code in LANGUAGES:
        if code.lower() == base:
            return code
    return None


def detect_os_language() -> str:
    tags: list[Optional[str]] = []
    if sys.platform == "win32":
        try:
            import ctypes

            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            tags.append(locale.windows_locale.get(lcid))
        except Exception:  # noqa: BLE001
            pass
    for env in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(env)
        if v:
            tags.append(v.split(":")[0])
    try:
        tags.append(locale.getlocale()[0])
    except Exception:  # noqa: BLE001
        pass
    for tag in tags:
        code = normalise(tag)
        if code:
            return code
    return DEFAULT


def _settings_path() -> Path:
    return config_dir() / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_language(code: str) -> None:
    if code not in LANGUAGES:
        raise ValueError(f"unsupported language: {code}")
    s = load_settings()
    s["lang"] = code
    _settings_path().write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def init() -> str:
    saved = load_settings().get("lang")
    set_language(saved if saved in LANGUAGES else detect_os_language())
    return _active


def set_language(code: str) -> None:
    global _active
    _active = code if code in LANGUAGES else DEFAULT


def current() -> str:
    return _active


def t(key: str, **kw) -> str:
    s = load(_active).get(key) or load(DEFAULT).get(key) or key
    if kw:
        try:
            return s.format(**kw)
        except (KeyError, IndexError, ValueError):
            return load(DEFAULT).get(key, key).format(**kw)
    return s
