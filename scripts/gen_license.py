#!/usr/bin/env python3
"""Mint a pro unlock key for a buyer. Run on NERO's machine with the secret set.

  export NERO_LICENSE_SECRET='your-long-random-secret'
  python scripts/gen_license.py --name buyer@email.com
  python scripts/gen_license.py --name alice --days 365
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nero_gif.license_check import make_pro_key, verify_key  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Generate NERO GIF pro license key")
    p.add_argument("--name", required=True, help="Buyer label (email or order id)")
    p.add_argument("--days", type=int, default=None, help="Optional expiry in days")
    args = p.parse_args()
    key = make_pro_key(name=args.name, days=args.days)
    info = verify_key(key)
    assert info.is_paid, info
    print(key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
