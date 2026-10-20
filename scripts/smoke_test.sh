#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.
# Ensure free mode for smoke (ignore any user license)
rm -f ./license.key
python3 -m nero_gif convert tests/fixtures/sample.mp4 -o tests/out/smoke_free.gif \
  --duration 2 --width 320 --fps 10 --force-free
python3 -m nero_gif convert tests/fixtures/sample.mp4 -o tests/out/smoke_paid.gif \
  --duration 2 --width 320 --fps 10 --force-paid
echo "OK: tests/out/smoke_free.gif and tests/out/smoke_paid.gif"
