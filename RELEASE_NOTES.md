# Release notes — NERO Tools GIF Converter

## 0.3.0 — screen recording, social presets, 10 languages

- **Record screen → GIF** (new first tab). Full screen or a region (drag to select,
  or type x / y / w / h), FPS, optional mouse cursor, 0/3/5 s countdown, small
  always-on-top **Stop** window. Windows uses ffmpeg `gdigrab`; stop is clean
  (`q` sent to ffmpeg). Then straight to a standard GIF or a social preset.
  Free tier: recording stops automatically at 15 s and the GIF is watermarked.
- **Perfect social GIF** (new tab, also selectable after recording). One click,
  auto size-fit: palettegen `stats_mode=diff` + paletteuse (`sierra2_4a` first,
  then `bayer`), `mpdecimate` on later steps / screen recordings, up to 4 tries
  stepping width / fps / colors down until the file fits. Final size shown.

  | Preset | Target | Ladder (width / fps / colors) |
  |--------|--------|-------------------------------|
  | X / Twitter | ≤ 14.5 MB (limit 15 MB) | 640/15/256 → 560/12/192 → 480/10/128 → 400/8/96 |
  | Discord (free accounts) | ≤ 9.5 MB (limit 10 MB) | 480/15/256 → 480/12/160 → 400/10/128 → 320/8/96 |
  | Reddit | ≤ 19 MB | 640/15/256 → 560/12/192 → 480/10/128 → 400/8/96 |
  | Telegram / WeChat sticker | ≤ 0.95 MB | 320/12/128 → 280/10/96 → 240/8/64 → 200/6/48 |
  | GitHub README | ≤ 9.5 MB (limit 10 MB) | 800/12/256 → 720/10/192 → 640/10/128 → 480/8/96 |

  Never upscales (`scale='min(iw,W)'`). Works on video **or** GIF input.
- **10 UI languages**: English, 简体中文, 繁體中文, 日本語, 한국어, Español,
  Português, Deutsch, Français, Русский. Auto-detected from the OS UI language,
  switcher top-right, choice saved in `%APPDATA%\NERO Tools\GIF Converter\settings.json`.
  License dialog and error messages are translated too (raw ffmpeg output stays English).
- CLI: `presets`, `social INPUT --preset KEY`, `record -o OUT.gif [--region x,y,w,h] [--seconds N] [--preset KEY]`.
- Free-tier 15 s cap now also applies to **Compress GIF** (it was missed in 0.2.0).
- Per-monitor DPI awareness on Windows, so region coordinates match screen pixels.
- ffmpeg console windows are hidden in the windowed exe.
- Licensing unchanged (Ed25519, same public key). 0.2.0 keys keep working.
- New tests: `tests/test_presets.py`, `tests/test_i18n.py`, `tests/test_recorder.py`.
- Translations were drafted with `scripts/translate_locales.py` (MiniMax API, key from env only) and checked by tests
  (all keys, same placeholders) plus a manual read-through.

## 0.2.0 — license hardening (required before selling)

- **Ed25519 license keys.** The app now embeds only a public key; keys are
  signed offline with NERO's private key. Pulling strings out of the exe no
  longer lets anyone mint keys.
- **Removed** the public default HMAC secret, `NERO_GIF_PAID=1`, `--force-paid`,
  `--watermark 0` and the CLI `genkey` command. No bypass ships.
- **0.1.0 keys are rejected** (0.1.0 was never sold; no buyers affected).
- New: `scripts/gen_keypair.py`, `scripts/gen_license.py --private-key … --buyer …`,
  `tests/test_license.py`, `scripts/wm_check.py`, `third_party/ED25519_NOTICE.md`.
- Key format unchanged on the outside: `NERO1.<payload>.<sig>` (base64url);
  payload `{"e":buyer,"i":issued_date,"tier":"pro","v":2}`.

## 0.1.0 (superseded — do not sell)

## What this release is

Windows desktop MVP: Video → GIF + GIF compress.  
Free = watermark + 15s cap. Pro unlock (USD 7) removes watermark and the cap.  
Offline Ed25519-signed license (0.2.0+) — no phone-home.

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

Mint keys **only** on NERO’s machine with the offline Ed25519 private key:

```bash
python scripts/gen_license.py --private-key ~/nero-license-private.key --buyer 'getly-order-id / buyer@email'
```

The private key NEVER goes in the repo, workflow YAML, artifact zip, logs, or any group chat.
The public key embedded in `nero_gif/license_check.py` is safe to publish.
No test/dev override ships in 0.2.0; unit tests use a throwaway keypair generated at runtime.

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
- The Ed25519 private key or any buyer keys
