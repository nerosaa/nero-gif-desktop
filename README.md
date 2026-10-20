# NERO Tools — GIF Converter (Windows desktop MVP)

English desktop app: **Video → GIF** and **GIF compress**.  
Free build adds a visible watermark (`NERO Tools — free`) and caps duration at **15 seconds**.  
A pro **license key** removes the watermark and lifts the duration cap. Offline check only (no phone-home).

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

# Free / watermarked
python3 -m nero_gif convert tests/fixtures/sample.mp4 \
  -o tests/out/free_wm.gif --duration 2 --width 320 --fps 10 --force-free

# Paid / clean (CLI force, or unlock a key)
python3 -m nero_gif convert tests/fixtures/sample.mp4 \
  -o tests/out/paid_clean.gif --duration 2 --width 320 --fps 10 --force-paid

# Compress
python3 -m nero_gif compress tests/out/paid_clean.gif \
  -o tests/out/compressed.gif --scale 0.75 --fps 8 --colors 64 --force-paid

# Or: env override without a key file
NERO_GIF_PAID=1 python3 -m nero_gif convert tests/fixtures/sample.mp4 -o tests/out/env_paid.gif --duration 2
```

GUI (needs a display + tkinter):

```bash
PYTHONPATH=. python3 -m nero_gif gui
```

## Unlock (pro)

1. Set a long secret **only on NERO’s machine** (never commit it):

   ```bash
   export NERO_LICENSE_SECRET='replace-with-long-random-string'
   ```

2. Mint a key after a Getly sale:

   ```bash
   python3 scripts/gen_license.py --name 'getly-order-123@buyer'
   # or: PYTHONPATH=. python3 -m nero_gif genkey --name buyer@email
   ```

3. Buyer pastes the `NERO1.…` key in the app (**Enter license…**) or drops a `license.key` file next to the exe / in `%APPDATA%\NERO Tools\GIF Converter\`.

Dev default secret is `DEV-ONLY-CHANGE-ME-NERO-GIF-2026` — **change before selling**.

Test override: `NERO_GIF_PAID=1` (no key file).

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

- **Never** put `NERO_LICENSE_SECRET` or real `NERO1.…` keys in the repo, workflow env, logs, or group chat. Placeholder docs only; production secret stays with NERO offline/DM.
- **Do not** publish Getly until the Windows zip smoke-passes on a real Windows PC (`GETLY_DRAFT.md`).

### Wine / cross-build note

Wine+PyInstaller on Linux is fragile and not used for the ship path. Prefer Actions `windows-latest`. Conversion logic is verified on Linux with system ffmpeg.

## Project layout

```
nero_gif/           # app package (converter, license, cli, gui)
assets/             # DejaVuSans.ttf for drawtext watermark
scripts/            # gen_license.py, build_windows.ps1, smoke_test.sh
third_party/        # FFMPEG_NOTICE.md (+ optional ffmpeg binaries later)
tests/fixtures/     # sample.mp4
PRODUCT.md          # pricing + Getly notes
GETLY_DRAFT.md      # product page copy + deliverable file list
RELEASE_NOTES.md    # artifact download + free vs unlock
UPLOAD_MANIFEST.txt # files for browser upload to new repo
.github/workflows/  # Build Windows (Actions → zip artifact)
```

## License

MIT for this app’s source. FFmpeg and DejaVu have their own licenses.
