# Release notes — NERO Tools GIF Converter 0.1.0

## What this release is

Windows desktop MVP: Video → GIF + GIF compress.  
Free = watermark + 15s cap. Pro unlock (USD 7) removes watermark and the cap.  
Offline HMAC license only — no phone-home.

Free web tool (no watermark): https://nerosaa.github.io/video-to-gif/

## How to download the Actions artifact

1. Open the GitHub repo `nerosaa/nero-gif-desktop` (create it first if it does not exist yet — see `UPLOAD_MANIFEST.txt`).
2. Go to **Actions** → workflow **Build Windows** → latest successful run.
3. Download artifact **NERO-Tools-GIF-Converter-windows-x64** (zip inside: `NERO-Tools-GIF-Converter-windows-x64.zip`).
4. Unzip on a Windows 10/11 x64 PC, install or place `ffmpeg.exe`, double-click `NeroGifConverter.exe`.

Manual rebuild on a Windows machine:

```powershell
.\scripts\build_windows.ps1
```

## Free vs USD 7 unlock

| Mode | Watermark | Duration |
|------|-----------|----------|
| Free (no key) | Yes — `NERO Tools — free` | Max 15s |
| Pro (`NERO1.…` key) | No | Unlimited (within PC/ffmpeg limits) |

Mint keys **only** on NERO’s machine with a private secret:

```bash
# Secret stays with NERO (DM / offline). NEVER commit, NEVER put in Actions env/logs/group chat.
export NERO_LICENSE_SECRET='replace-with-long-random-string'   # placeholder only in docs
python scripts/gen_license.py --name 'getly-order-id@buyer'
```

Dev default secret in source is for local testing only — **change before selling**.  
Do not put production `NERO_LICENSE_SECRET` or real keys in the repo, workflow YAML, artifact zip, or any group-facing text.

Test override (dev only): `NERO_GIF_PAID=1`.

## Free web tool

https://nerosaa.github.io/video-to-gif/

## Getly

Do **not** publish the Getly product until the Windows zip smoke-passes on a real Windows PC.  
Paste-ready copy + deliverable checklist: `GETLY_DRAFT.md`. Product sheet: `PRODUCT.md`.

## FFmpeg

Buyers need `ffmpeg` on PATH or `ffmpeg.exe` beside the exe. See `third_party/FFMPEG_NOTICE.md` / `FFMPEG_NOTICE.md` inside the zip.

## Not included

- ScreenToGif / Kap / Gifski (we do not wrap or resell them)
- Bundled ffmpeg binary (first listing keeps license story simple)
- Production license secret or buyer keys
