# NERO Tools — GIF Converter (Windows desktop)

Desktop app in 10 languages: **Record screen → GIF**, **Video → GIF**, **Perfect social GIF**
(auto size-fit for X / Discord / Reddit / Telegram-WeChat stickers / GitHub README) and **GIF compress**.  
Free build adds a visible watermark (`NERO Tools — free`) and caps duration at **15 seconds**.  
A pro **license key** (Ed25519-signed) removes the watermark and lifts the duration cap. Offline check only (no phone-home).

Free web tool (no watermark): https://nerosaa.github.io/video-to-gif/

We do **not** wrap or resell ScreenToGif, Kap, or Gifski.

## Requirements

- Python 3.10+ (for source runs)
- **ffmpeg** on PATH (or `ffmpeg.exe` next to the app). See `third_party/FFMPEG_NOTICE.md`.
- Font: `assets/DejaVuSans.ttf` (bundled) for the watermark

## Quick test on Linux (this box)

```bash
cd /workspace/nero-gif-desktop
export PYTHONPATH=.

python3 -m nero_gif status
python3 -m unittest discover -s tests -v      # license tests (throwaway keypair)

# Free / watermarked
python3 -m nero_gif convert tests/fixtures/sample.mp4 \
  -o tests/out/free_wm.gif --duration 2 --width 320 --fps 10

# Social presets (auto size-fit, max 4 tries; exit 2 = still over target)
python3 -m nero_gif presets
python3 -m nero_gif social tests/fixtures/sample.mp4 --preset discord -o tests/out/discord.gif

# Screen recording (x11grab on Linux, gdigrab on Windows)
python3 -m nero_gif record -o tests/out/rec.gif --region 0,0,640,400 --seconds 3 --preset sticker

# Compress
python3 -m nero_gif compress tests/out/free_wm.gif \
  -o tests/out/compressed.gif --scale 0.75 --fps 8 --colors 64

# Full smoke: free=watermark, valid key=clean, tampered key=rejected
NERO_SMOKE_KEY_FILE=/path/to/a/minted-key.txt scripts/smoke_test.sh
```

There is **no** watermark bypass: `--force-paid`, `--watermark 0`, `NERO_GIF_PAID=1`
and the old default HMAC secret were removed in 0.2.0. Clean output requires a
valid Ed25519-signed key. (`--force-free` still exists to force a watermark.)

GUI (needs a display + tkinter):

```bash
PYTHONPATH=. python3 -m nero_gif gui
```

## Features (0.3.0)

- **Record screen**: full screen or region (drag-select or x/y/w/h), FPS, cursor on/off,
  countdown, Stop window. ffmpeg `gdigrab` on Windows (`-offset_x -offset_y -video_size -i desktop`),
  `x11grab` on Linux; stopped cleanly by sending `q` to ffmpeg. Code: `nero_gif/recorder.py`.
- **Perfect social GIF**: presets in `nero_gif/presets.py`; two-pass palettegen
  (`stats_mode=diff`) / paletteuse (`sierra2_4a` / `bayer`), `mpdecimate` where it helps,
  up to 4 encodes stepping width/fps/colors down until the target size fits.
- **i18n**: `nero_gif/i18n.py` + `nero_gif/locales/<code>.json` (en, zh-Hans, zh-Hant, ja, ko,
  es, pt, de, fr, ru). Add a string: put it in `en.json`, then run
  `MINIMAX_API_KEY=… python3 scripts/translate_locales.py --force` (or edit by hand);
  `tests/test_i18n.py` fails if any language misses a key or a `{placeholder}`.
- Free tier rules apply everywhere (recording, social, compress): watermark + 15 s.

## Licensing (Ed25519, offline)

Key format: `NERO1.<payload>.<signature>` (base64url).
Payload is compact JSON, e.g. `{"e":"buyer@email","i":"2026-10-20","tier":"pro","v":2}`;
signature is Ed25519 over the payload string.

- The app embeds **only the public key** (`PUBLIC_KEY_B64` in `nero_gif/license_check.py`).
  Extracting it from the exe does not let anyone mint keys.
- The **private key** lives offline with NERO, never in this repo, the zip, CI, or chat.
- Verification is pure Python (`nero_gif/_ed25519.py`, adapted from RFC 8032 §6,
  BSD-2-Clause — see `third_party/ED25519_NOTICE.md`). No native deps for PyInstaller.
- Keys from 0.1.0 (HMAC) are **not** accepted.

### One-time: create a keypair (already done for production)

```bash
python3 scripts/gen_keypair.py --out ~/nero-license-private.key   # chmod 600, not printed
# prints PUBLIC_KEY_B64 = "…"  -> paste into nero_gif/license_check.py, rebuild
```

The script refuses to write inside the repo. Back the private key up offline.
If it is ever lost, generate a new pair and ship a new build (old keys stop working).

### After each Getly sale: mint a key

```bash
python3 scripts/gen_license.py --private-key ~/nero-license-private.key \
  --buyer 'getly-order-123 / buyer@email' [--out key.txt]
```

`gen_license.py` refuses to output a key that does not verify against the app's
embedded public key. Send the `NERO1.…` line to the buyer.

Buyer pastes it in the app (**Enter license…**) or drops a `license.key` file next to the exe /
in `%APPDATA%\NERO Tools\GIF Converter\`.

### Windows unlock test (one pass: free → key)

1. Unzip, put `ffmpeg.exe` next to `NeroGifConverter.exe`, double-click the exe.
   Title bar area shows **License: FREE**. Convert any short video → GIF has the
   `NERO Tools — free` watermark bottom-right.
2. Click **Enter license…**, paste a minted test key → "Pro features enabled";
   header shows **License: PRO — licensed to …**.
3. Convert the **same** video again → GIF has **no** watermark (and > 15 s is allowed).
   Optional: edit one character of the key and paste → "Invalid key: bad signature".

To reset to free afterwards, delete `license.key` next to the exe and in
`%APPDATA%\NERO Tools\GIF Converter\`.

## Build Windows .exe

### Preferred: GitHub Actions

Workflow: `.github/workflows/build-windows.yml` (runs on `windows-latest`).

1. Push this tree to a **new** public repo `nerosaa/nero-gif-desktop` (see `UPLOAD_MANIFEST.txt` — do not assume the repo exists until created).
2. Actions → **Build Windows** → download artifact **NERO-Tools-GIF-Converter-windows-x64**.
3. Zip name inside: `NERO-Tools-GIF-Converter-windows-x64.zip` (exe + README + FFMPEG_NOTICE; buyers need `ffmpeg.exe` on PATH or beside the app).

Details: `RELEASE_NOTES.md`.

### Manual (Windows PC)

```powershell
cd nero-gif-desktop
.\scripts\build_windows.ps1
```

Produces `dist\NeroGifConverter\` and `NERO-Tools-GIF-Converter-windows-x64.zip`.

### Secrets / Getly

- **Never** put the Ed25519 private key or real `NERO1.…` buyer keys in the repo, workflow env, logs, zip, or group chat. The public key in `license_check.py` is safe to publish.
- **Do not** publish Getly until the Windows zip smoke-passes on a real Windows PC (`GETLY_DRAFT.md`).

### Wine / cross-build note

Wine+PyInstaller on Linux is fragile and not used for the ship path. Prefer Actions `windows-latest`. Conversion logic is verified on Linux with system ffmpeg.

## Project layout

```
nero_gif/           # app package (converter, license, cli, gui)
assets/             # DejaVuSans.ttf for drawtext watermark
scripts/            # gen_keypair.py, gen_license.py, build_windows.ps1, smoke_test.sh, wm_check.py
third_party/        # FFMPEG_NOTICE.md, ED25519_NOTICE.md
tests/              # test_license.py, fixtures/sample.mp4
PRODUCT.md          # pricing + Getly notes
GETLY_DRAFT.md      # product page copy + deliverable file list
RELEASE_NOTES.md    # artifact download + free vs unlock
UPLOAD_MANIFEST.txt # files for browser upload to new repo
.github/workflows/  # Build Windows (Actions → zip artifact)
```

## License

MIT for this app’s source. `nero_gif/_ed25519.py` is BSD-2-Clause (RFC 8032 code component). FFmpeg and DejaVu have their own licenses.
