"""Offline license unlock (HMAC signed token). No phone-home."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .paths import app_dir, config_dir

# Replace at build/release time via env NERO_LICENSE_SECRET (keep private).
_DEFAULT_DEV_SECRET = "DEV-ONLY-CHANGE-ME-NERO-GIF-2026"
PREFIX = "NERO1"
FREE_MAX_SECONDS = 15.0
WATERMARK_TEXT = "NERO Tools — free"


def _secret() -> bytes:
    return os.environ.get("NERO_LICENSE_SECRET", _DEFAULT_DEV_SECRET).encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


@dataclass(frozen=True)
class LicenseInfo:
    valid: bool
    tier: str  # "free" | "pro"
    note: str = ""
    payload: Optional[dict] = None

    @property
    def is_paid(self) -> bool:
        return self.valid and self.tier == "pro"


def sign_payload(payload: dict) -> str:
    """Create a license key string from a payload dict."""
    body = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = _b64url(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{PREFIX}.{body}.{sig}"


def verify_key(key: str) -> LicenseInfo:
    key = (key or "").strip()
    if not key:
        return LicenseInfo(False, "free", "empty key")
    parts = key.split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        return LicenseInfo(False, "free", "bad format")
    body, sig = parts[1], parts[2]
    expect = _b64url(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expect, sig):
        return LicenseInfo(False, "free", "bad signature")
    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except Exception:
        return LicenseInfo(False, "free", "bad payload")
    if payload.get("tier") != "pro":
        return LicenseInfo(False, "free", "not pro tier", payload)
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        return LicenseInfo(False, "free", "expired", payload)
    return LicenseInfo(True, "pro", "ok", payload)


def license_paths() -> list[Path]:
    return [
        Path.cwd() / "license.key",
        app_dir() / "license.key",
        config_dir() / "license.key",
    ]


def load_stored_key() -> Optional[str]:
    for p in license_paths():
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8").strip()
                if text:
                    return text
            except OSError:
                continue
    return None


def save_key(key: str) -> Path:
    info = verify_key(key)
    if not info.is_paid:
        raise ValueError(f"Invalid license: {info.note}")
    dest = config_dir() / "license.key"
    dest.write_text(key.strip() + "\n", encoding="utf-8")
    # Also drop a copy next to the app for portable use
    try:
        (app_dir() / "license.key").write_text(key.strip() + "\n", encoding="utf-8")
    except OSError:
        pass
    return dest


def force_paid_env() -> bool:
    """Dev/test override: NERO_GIF_PAID=1 skips watermark without a key file."""
    return os.environ.get("NERO_GIF_PAID", "").strip() in ("1", "true", "TRUE", "yes")


def current_license() -> LicenseInfo:
    if force_paid_env():
        return LicenseInfo(True, "pro", "env NERO_GIF_PAID=1")
    key = load_stored_key()
    if not key:
        return LicenseInfo(False, "free", "no license file")
    return verify_key(key)


def make_pro_key(name: str = "buyer", days: Optional[int] = None) -> str:
    """Helper for NERO to mint keys (also exposed via scripts/gen_license.py)."""
    payload = {
        "v": 1,
        "tier": "pro",
        "n": name,
        "iat": int(time.time()),
    }
    if days is not None:
        payload["exp"] = int(time.time()) + int(days) * 86400
    return sign_payload(payload)
