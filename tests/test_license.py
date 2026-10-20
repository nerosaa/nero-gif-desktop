"""Unit tests for Ed25519 license verification.

Uses a THROWAWAY keypair generated at runtime — no production key material.
Run:  PYTHONPATH=. python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import unittest

from nero_gif import _ed25519, license_check as lc


class LicenseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seed = _ed25519.generate_secret()
        cls.pub = _ed25519.secret_to_public(cls.seed)

    def test_rfc8032_vector1(self) -> None:
        sk = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        self.assertEqual(
            _ed25519.secret_to_public(sk).hex(),
            "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        )
        sig = _ed25519.sign(sk, b"")
        self.assertEqual(
            sig.hex(),
            "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
            "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
        )
        self.assertTrue(_ed25519.verify(_ed25519.secret_to_public(sk), b"", sig))

    def test_valid_key(self) -> None:
        key = lc.make_pro_key(self.seed, buyer="alice@example.com", issued="2026-10-20")
        info = lc.verify_key(key, public_key=self.pub)
        self.assertTrue(info.is_paid, info)
        self.assertEqual(info.payload["e"], "alice@example.com")
        self.assertEqual(info.payload["i"], "2026-10-20")

    def test_throwaway_key_rejected_by_embedded_production_key(self) -> None:
        key = lc.make_pro_key(self.seed, buyer="mallory")
        self.assertFalse(lc.verify_key(key).is_paid)

    def test_tampered_payload_rejected(self) -> None:
        key = lc.make_pro_key(self.seed, buyer="alice")
        pre, body, sig = key.split(".")
        payload = json.loads(lc.b64url_decode(body))
        payload["e"] = "mallory"
        body2 = lc.b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        self.assertFalse(lc.verify_key(f"{pre}.{body2}.{sig}", public_key=self.pub).is_paid)

    def test_tampered_signature_rejected(self) -> None:
        key = lc.make_pro_key(self.seed, buyer="alice")
        pre, body, sig = key.split(".")
        raw = bytearray(lc.b64url_decode(sig))
        raw[10] ^= 0x01
        self.assertFalse(lc.verify_key(f"{pre}.{body}.{lc.b64url(bytes(raw))}", public_key=self.pub).is_paid)

    def test_non_canonical_s_rejected(self) -> None:
        key = lc.make_pro_key(self.seed, buyer="alice")
        pre, body, sig = key.split(".")
        raw = lc.b64url_decode(sig)
        s = int.from_bytes(raw[32:], "little") + _ed25519.L
        if s < 2**256:
            forged = raw[:32] + s.to_bytes(32, "little")
            self.assertFalse(lc.verify_key(f"{pre}.{body}.{lc.b64url(forged)}", public_key=self.pub).is_paid)

    def test_old_hmac_style_key_rejected(self) -> None:
        secret = os.urandom(24)
        payload = {"v": 1, "tier": "pro", "n": "buyer", "iat": 1760000000}
        body = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(
            hmac.new(secret, body.encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        old = f"NERO1.{body}.{sig}"
        self.assertFalse(lc.verify_key(old).is_paid)
        self.assertFalse(lc.verify_key(old, public_key=self.pub).is_paid)

    def test_garbage_rejected(self) -> None:
        for k in ["", "NERO1", "NERO1..", "NERO2.a.b", "NERO1.!!!.???", "x.y.z"]:
            self.assertFalse(lc.verify_key(k).is_paid, k)

    def test_no_bypass_env(self) -> None:
        os.environ["NERO_GIF_PAID"] = "1"
        os.environ["NERO_LICENSE_SECRET"] = "anything"
        try:
            self.assertFalse(lc.verify_key("NERO1.e30.AAAA").is_paid)
            self.assertFalse(hasattr(lc, "force_paid_env"))
        finally:
            del os.environ["NERO_GIF_PAID"], os.environ["NERO_LICENSE_SECRET"]

    def test_private_key_file_roundtrip(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "k.key"
            lc.write_private_key_file(p, self.seed)
            self.assertEqual(oct(p.stat().st_mode & 0o777), "0o600")
            self.assertEqual(lc.read_private_key_file(p), self.seed)


if __name__ == "__main__":
    unittest.main()
