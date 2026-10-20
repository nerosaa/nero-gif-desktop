#!/usr/bin/env python3
"""Mint a pro unlock key for a buyer (offline, on NERO's machine).

  python scripts/gen_license.py --private-key ~/nero-license-private.key --buyer buyer@email.com
  python scripts/gen_license.py --private-key PATH --buyer getly-order-123 --out key.txt

The key is checked against the PUBLIC key embedded in the app before output,
so a mismatched private key fails loudly instead of producing a dud key.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nero_gif.license_check import make_pro_key, read_private_key_file, verify_key  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate NERO GIF pro license key")
    ap.add_argument("--private-key", required=True, help="Path to Ed25519 private key file")
    ap.add_argument("--buyer", required=True, help="Buyer email or Getly order id")
    ap.add_argument("--issued", default=None, help="Issue date YYYY-MM-DD (default: today)")
    ap.add_argument("--out", default=None, help="Write key to this file (chmod 600) instead of stdout")
    args = ap.parse_args()

    seed = read_private_key_file(Path(os.path.expanduser(args.private_key)))
    key = make_pro_key(seed, buyer=args.buyer, issued=args.issued)
    info = verify_key(key)  # embedded production public key
    if not info.is_paid:
        print(f"ERROR: minted key does not verify with the app's embedded public key ({info.note}).\n"
              "Wrong private key, or PUBLIC_KEY_B64 not updated?", file=sys.stderr)
        return 1
    if args.out:
        out = Path(os.path.expanduser(args.out))
        out.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(key + "\n")
        os.chmod(out, 0o600)
        print(f"Key for {args.buyer!r} written to {out}")
    else:
        print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
