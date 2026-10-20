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
- Offline key — paste once; no phone-home, no account

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
3. **Do not** put `license.key`, the Ed25519 private key, or any minted key in the zip (zip must be v0.2.0+; v0.1.0 had a forgeable dev secret)
4. Fulfillment (per sale, offline on NERO's machine):
   `python scripts/gen_license.py --private-key <offline private key> --buyer '<getly order id / email>'`
   → send the single `NERO1.…` line to the buyer (Getly message / email). Never send or upload the private key.
5. Screenshots: free watermark vs pro clean (`tests/out/watermark_preview.png` as starting point)

## itch.io (later)

Same zip + same $7 key SKU; link back to Getly if itch payout is slower.

## Status gate before “Buy” goes live

- [ ] Windows zip built on a real Windows machine
- [ ] Double-click exe converts a sample MP4 with watermark
- [ ] Unlock key (minted with the production private key) removes watermark on that machine, same video, one pass (README → "Windows unlock test")
- [x] Production Ed25519 keypair generated; public key embedded (v0.2.0); private key stored offline, not in repo
- [ ] v0.2.0 Windows zip rebuilt by Actions and published as the Release download
- [ ] Private key backed up offline by NERO
- [ ] Getly product created with USDT price $7
