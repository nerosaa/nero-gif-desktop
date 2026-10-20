# FFmpeg license notice

This app shells out to **FFmpeg** to encode GIFs. We do **not** ship ScreenToGif, Kap, or Gifski.

## Recommended distribution (default)

- **Do not bundle** FFmpeg inside the zip for the first Getly listing if you want the simplest license story.
- Document: buyers install FFmpeg from https://ffmpeg.org/download.html (or `winget install ffmpeg` / `choco install ffmpeg`) and ensure `ffmpeg.exe` is on PATH.
- Our app also looks for `ffmpeg.exe` next to `NeroGifConverter.exe`.

## Optional: bundle FFmpeg binaries

If you later place official Windows builds under `third_party/ffmpeg/`:

1. Keep the FFmpeg build’s own `LICENSE`, `COPYING*`, and `README` files in that folder.
2. Most static Windows builds of FFmpeg are **GPL**. Shipping them means your distribution must comply with GPL (provide corresponding source / offer for the FFmpeg build you ship). This app’s own Python code stays separate; the GPL applies to the FFmpeg binary you redistribute.
3. Prefer an **LGPL** FFmpeg build if you can obtain one that still supports the filters you need (`fps`, `scale`, `palettegen`, `paletteuse`, `drawtext`).
4. Never strip license files from a bundled FFmpeg folder.

## This repository

- Source code of NERO Tools GIF Converter: see project LICENSE (MIT intended).
- Bundled font `assets/DejaVuSans.ttf`: Bitstream Vera / DejaVu fonts license (see fonts.debian.org / dejavu-fonts).
