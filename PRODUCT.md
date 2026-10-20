# Product sheet — NERO Tools GIF Converter

## Positioning

- **Free web**: https://nerosaa.github.io/video-to-gif/ — no watermark, browser-only, duration-limited UX.
- **Desktop (this product)**: Windows app; free zip is watermarked + 15s cap; **$7** pro unlock (range $4.9–$9) removes watermark + unlimited length.

Do not list on Getly until the Windows zip is built and smoke-tested on a real Windows machine.

## Suggested price

| SKU | Price | What buyer gets |
|-----|-------|-----------------|
| Free download | $0 | Watermarked GIF Converter zip (needs ffmpeg on PATH) |
| Pro unlock key | **$7** (or $9 if positioned with email support) | `NERO1.…` key — no watermark, no 15s cap |
| itch.io later | same | Mirror listing after Getly |

USDT checkout via Getly store: https://www.getly.store/store/nero-tools-mvb64f1s

## Feature bullets (storefront)

- Convert MP4 / WebM / MOV → GIF on your PC (files stay local)
- Compress GIFs (scale, fps, colors)
- Free: readable watermark “NERO Tools — free” (bottom-right) + 15s max clip
- Pro: remove watermark + unlimited duration (within RAM/ffmpeg limits)
- Offline license unlock — no account login spam
- English UI

## Watermark screenshot instruction

1. Convert any short clip with free mode (`--force-free` or no license).
2. Open `tests/out/free_wm.gif` (or the buyer-facing sample) and grab a mid frame where the bottom-right text is readable.
3. Example preview already generated on the build box: `tests/out/watermark_preview.png`.
4. On the Getly page, show **side-by-side**: free (watermark) vs pro (clean).

## Competitive note (honest)

We are **not** ScreenToGif / Kap / Gifski. We are a small ffmpeg-based converter with a clear free→pro watermark upsell, aimed at people who hate logos on free GIF tools.
