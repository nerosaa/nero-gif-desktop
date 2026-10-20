"""python -m nero_gif [gui|convert|…]"""

from __future__ import annotations

import sys


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("gui", "--gui"):
        from .gui import run

        run()
        return
    from .cli import main as cli_main

    raise SystemExit(cli_main(argv))


if __name__ == "__main__":
    main()
