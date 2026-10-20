"""Offline license unlock — Ed25519 signed token. No phone-home.

Key format:  NERO1.<payload_b64url>.<sig_b64url>
  payload = compact JSON, e.g. {"e":"buyer@email","i":"2026-10-20","tier":"pro","v":2}
  sig     = Ed25519 signature (64 bytes) over the ASCII payload_b64url string.

The app embeds ONLY the public key below. The private key stays offline with
NERO (see scripts/gen_keypair.py / scripts/gen_license.py). There is no
environment-variable, CLI flag, or default-secret bypass in shipped code.
"""

from __future__ import annotations

import base64
import datetime as _dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import _ed25519
from .paths import app_dir, config_dir

# Production verification key (public, safe to ship). Generated 2026-10-20.
PUBLIC_KEY_B64 = "zPe7ZJxycaAjzBThV5BhweDsE5o_UZtWO0lcuF0S4W4"

PREFIX = "NERO1"
PAYLOAD_VERSION = 2
FREE_MAX_SECONDS = 15.0
WATERMARK_TEXT = "NERO Tools — free"
PRIVATE_KEY_HEADER = "NERO-ED25519-PRIVATE-KEY-V1"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(s: str) -> bytes:
    if not s or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in s):
        raise ValueError("bad base64url")
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


def _embedded_public_key() -> bytes:
    return b64url_decode(PUBLIC_KEY_B64)


def verify_key(key: str, public_key: Optional[bytes] = None) -> LicenseInfo:
    """Verify a NERO1 key. `public_key` override exists for unit tests only."""
    key = (key or "").strip()
    if not key:
        return LicenseInfo(False, "free", "empty key")
    parts = key.split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        return LicenseInfo(False, "free", "bad format")
    body, sig_s = parts[1], parts[2]
    try:
        sig = b64url_decode(sig_s)
        pub = public_key if public_key is not None else _embedded_public_key()
    except Exception:
        return LicenseInfo(False, "free", "bad signature")
    if len(sig) != 64 or not _ed25519.verify(pub, body.encode("ascii"), sig):
        return LicenseInfo(False, "free", "bad signature")
    try:
        payload = json.loads(b64url_decode(body).decode("utf-8"))
    except Exception:
        return LicenseInfo(False, "free", "bad payload")
    if not isinstance(payload, dict) or payload.get("tier") != "pro":
        return LicenseInfo(False, "free", "not pro tier", payload if isinstance(payload, dict) else None)
    return LicenseInfo(True, "pro", f"licensed to {payload.get('e', '?')}", payload)


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
    try:
        (app_dir() / "license.key").write_text(key.strip() + "\n", encoding="utf-8")
    except OSError:
        pass
    return dest


def current_license() -> LicenseInfo:
    key = load_stored_key()
    if not key:
        return LicenseInfo(False, "free", "no license file")
    return verify_key(key)


# ---- Minting helpers (used offline by scripts/; need the PRIVATE key) ----

def sign_payload(private_seed: bytes, payload: dict) -> str:
    body = b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = _ed25519.sign(private_seed, body.encode("ascii"))
    return f"{PREFIX}.{body}.{b64url(sig)}"


def make_pro_key(private_seed: bytes, buyer: str, issued: Optional[str] = None) -> str:
    issued = issued or _dt.date.today().isoformat()
    payload = {"v": PAYLOAD_VERSION, "tier": "pro", "e": str(buyer), "i": issued}
    return sign_payload(private_seed, payload)


def write_private_key_file(path: Path, seed: bytes) -> None:
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write(f"{PRIVATE_KEY_HEADER}\n{b64url(seed)}\n")
    os.chmod(path, 0o600)


def read_private_key_file(path: Path) -> bytes:
    lines = Path(path).read_text(encoding="ascii").split()
    if len(lines) != 2 or lines[0] != PRIVATE_KEY_HEADER:
        raise ValueError(f"{path}: not a NERO Ed25519 private key file")
    seed = b64url_decode(lines[1])
    if len(seed) != 32:
        raise ValueError(f"{path}: bad private key length")
    return seed
