# Getly listing draft (do not publish until Windows zip exists)

## Title

NERO Tools GIF Converter for Windows — Video to GIF (Remove Watermark Unlock)

## Short blurb

Turn videos into GIFs on your PC. Free build has a small watermark and a 15s cap. Buy a $7 unlock key to remove the watermark and convert longer clips. Files never leave your computer.

## Price

- Unlock key: **USD 7** (USDT on Getly)
- Free zip: attach as free download or host separately and link from the page

## Long description (paste-ready)

**NERO Tools GIF Converter** is a lightweight Windows app for:

- Video → GIF (start time, duration, width, FPS)
- GIF compress (scale, FPS, palette colors)

**Free version**
- Watermark: “NERO Tools — free” (bottom-right)
- Max duration: 15 seconds per export

**Pro unlock ($7)**
- No watermark
- Unlimited duration (within your PC memory)
- Offline key — paste once; no phone-home

**Requirements**
- Windows 10/11 64-bit
- FFmpeg on PATH, or place `ffmpeg.exe` next to the app ([ffmpeg.org](https://ffmpeg.org/download.html))

**Also free online (no watermark, shorter clips):**  
https://nerosaa.github.io/video-to-gif/

After payment you receive a `NERO1.…` license key by message/email. Open the app → **Enter license…** → paste the key.

Not affiliated with ScreenToGif, Kap, or Gifski.

## Deliverable file list (what to upload when ready)

1. `NERO-Tools-GIF-Converter-windows-x64.zip` — Actions artifact / `scripts/build_windows.ps1` output
   - Contains `NeroGifConverter.exe`, `_internal/` (PyInstaller), `assets/DejaVuSans.ttf` if not internalized
2. Optional: `README-WINDOWS.txt` inside the zip (how to install ffmpeg, how to unlock)
3. **Do not** put `license.key` or `NERO_LICENSE_SECRET` in the zip
4. Fulfillment: generate keys with `scripts/gen_license.py` using production secret; send key text to buyer
5. Screenshots: free watermark vs pro clean (`tests/out/watermark_preview.png` as starting point)

## itch.io (later)

Same zip + same $7 key SKU; link back to Getly if itch payout is slower.

## Status gate before “Buy” goes live

- [ ] Windows zip built on a real Windows machine
- [ ] Double-click exe converts a sample MP4 with watermark
- [ ] Unlock key removes watermark on that machine
- [ ] Production `NERO_LICENSE_SECRET` set and recorded offline by NERO
- [ ] Getly product created with USDT price $7
