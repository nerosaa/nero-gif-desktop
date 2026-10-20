#!/usr/bin/env bash
# Linux smoke: unit tests + free (watermarked) + optional real-key (clean),
# tampered key (rejected) and garbage key (rejected).
#
#   scripts/smoke_test.sh                         # unit tests + free only
#   NERO_SMOKE_KEY_FILE=/path/key.txt scripts/smoke_test.sh   # + paid checks
#
# Paid checks run in a throwaway copy with a throwaway HOME, so no license.key
# is ever written into this repo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
SRC=tests/fixtures/sample.mp4
ARGS=(--duration 2 --width 320 --fps 10)

echo "== unit tests (throwaway keypair)"
python3 -m unittest discover -s tests -q

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp -a "$ROOT/nero_gif" "$ROOT/assets" "$WORK/"
mkdir -p "$WORK/home" "$WORK/out"
run() { (cd "$WORK" && HOME="$WORK/home" PYTHONPATH="$WORK" python3 -m nero_gif "$@"); }
lic() { mkdir -p "$WORK/home/.config/nero-gif"; printf '%s\n' "$1" > "$WORK/home/.config/nero-gif/license.key"; }

echo "== free (no key) -> watermark"
run status | grep -q "tier: free"
run convert "$ROOT/$SRC" -o "$WORK/out/free.gif" "${ARGS[@]}" >/dev/null
python3 scripts/wm_check.py "$WORK/out/free.gif" "$SRC" --expect wm

echo "== env bypass attempt (NERO_GIF_PAID=1, no key) -> still watermark"
(cd "$WORK" && HOME="$WORK/home" PYTHONPATH="$WORK" NERO_GIF_PAID=1 python3 -m nero_gif convert "$ROOT/$SRC" -o "$WORK/out/env.gif" "${ARGS[@]}" >/dev/null)
python3 scripts/wm_check.py "$WORK/out/env.gif" "$SRC" --expect wm

echo "== --force-paid flag removed"
if run convert "$ROOT/$SRC" -o "$WORK/out/fp.gif" --force-paid "${ARGS[@]}" >/dev/null 2>&1; then
  echo "FAIL: --force-paid accepted"; exit 1; fi
echo "ok: --force-paid rejected by argparse"

if [[ -n "${NERO_SMOKE_KEY_FILE:-}" ]]; then
  KEY="$(tr -d '\r\n' < "$NERO_SMOKE_KEY_FILE")"
  echo "== valid key -> clean"
  lic "$KEY"
  run status | grep -q "tier: pro"
  run convert "$ROOT/$SRC" -o "$WORK/out/pro.gif" "${ARGS[@]}" >/dev/null
  python3 scripts/wm_check.py "$WORK/out/pro.gif" "$SRC" --expect clean

  echo "== tampered key (payload edited) -> rejected + watermark"
  PRE="${KEY%%.*}"; REST="${KEY#*.}"; BODY="${REST%%.*}"; SIG="${REST#*.}"
  BODY2="$(python3 - "$BODY" <<'PY'
import sys, json, base64
b = sys.argv[1]; p = json.loads(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)))
p["e"] = "someone-else"
print(base64.urlsafe_b64encode(json.dumps(p, separators=(",", ":"), sort_keys=True).encode()).rstrip(b"=").decode())
PY
)"
  lic "$PRE.$BODY2.$SIG"
  run status | grep -q "tier: free (bad signature)"
  run convert "$ROOT/$SRC" -o "$WORK/out/tamper.gif" "${ARGS[@]}" >/dev/null
  python3 scripts/wm_check.py "$WORK/out/tamper.gif" "$SRC" --expect wm
  (cd "$WORK" && HOME="$WORK/home" PYTHONPATH="$WORK" python3 -m nero_gif unlock "$PRE.$BODY2.$SIG" >/dev/null 2>&1) \
    && { echo "FAIL: unlock accepted tampered key"; exit 1; }
  echo "ok: unlock rejects tampered key"

  echo "== tampered key (signature bit flip) -> rejected"
  SIG2="$(python3 -c "import sys,base64;s=sys.argv[1];r=bytearray(base64.urlsafe_b64decode(s+'='*(-len(s)%4)));r[3]^=1;print(base64.urlsafe_b64encode(bytes(r)).rstrip(b'=').decode())" "$SIG")"
  lic "$PRE.$BODY.$SIG2"
  run status | grep -q "tier: free (bad signature)"
  echo "ok"
fi

if [[ -n "${NERO_SMOKE_OLD_KEY_FILE:-}" ]]; then
  echo "== old v0.1.0 HMAC key -> rejected + watermark"
  lic "$(tr -d '\r\n' < "$NERO_SMOKE_OLD_KEY_FILE")"
  run status | grep -q "tier: free (bad signature)"
  run convert "$ROOT/$SRC" -o "$WORK/out/old.gif" "${ARGS[@]}" >/dev/null
  python3 scripts/wm_check.py "$WORK/out/old.gif" "$SRC" --expect wm
fi

echo "SMOKE OK"
