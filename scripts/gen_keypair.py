#!/usr/bin/env python3
"""Create an Ed25519 license-signing keypair (run ONCE, offline, on NERO's machine).

  python scripts/gen_keypair.py                       # -> ~/nero-license-private.key
  python scripts/gen_keypair.py --out /path/outside/repo/my.key

* The PRIVATE key is written to a file OUTSIDE the repo (chmod 600) and is
  never printed. Back it up offline. Anyone holding it can mint keys.
* The PUBLIC key is printed: paste it into nero_gif/license_check.py
  (PUBLIC_KEY_B64) and rebuild. Public keys are safe to commit.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nero_gif import _ed25519  # noqa: E402
from nero_gif.license_check import b64url, write_private_key_file  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Ed25519 license keypair")
    ap.add_argument("--out", default=str(Path.home() / "nero-license-private.key"),
                    help="Private key path (must be outside the repo)")
    ap.add_argument("--force", action="store_true", help="Overwrite an existing file")
    args = ap.parse_args()

    out = Path(os.path.expanduser(args.out)).resolve()
    try:
        out.relative_to(ROOT)
        print(f"ERROR: refusing to write private key inside the repo: {out}", file=sys.stderr)
        return 2
    except ValueError:
        pass
    if out.exists() and not args.force:
        print(f"ERROR: {out} already exists (use --force to overwrite)", file=sys.stderr)
        return 2

    seed = _ed25519.generate_secret()
    write_private_key_file(out, seed)
    pub = b64url(_ed25519.secret_to_public(seed))
    print(f"Private key written to: {out} (chmod 600, NOT printed)")
    print(f"PUBLIC_KEY_B64 = \"{pub}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
