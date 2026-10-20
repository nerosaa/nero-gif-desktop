NERO Tools GIF Converter — Windows x64
======================================

Free build
----------
- Visible watermark: "NERO Tools — free" (bottom-right)
- Max duration: 15 seconds per export
- Record screen → GIF, Video → GIF, Perfect social GIF, GIF compress
- Files stay on your PC

Pro unlock (USD 7)
------------------
- Removes watermark
- Lifts the 15s duration cap
- Offline key (NERO1.…). Open the app → Enter license… → paste once.
- Keys are sent after Getly payment. Do not share your key.
- If the app says "Invalid key: bad signature", copy the whole NERO1.… line
  again (no spaces / line breaks). Keys for version 0.1.0 do not work.

ffmpeg (required)
-----------------
This zip does NOT bundle ffmpeg.exe (see FFMPEG_NOTICE.md).

Install one of:
  winget install ffmpeg
  choco install ffmpeg
  https://ffmpeg.org/download.html  (add to PATH)

Or place ffmpeg.exe next to NeroGifConverter.exe.

How to run
----------
1. Unzip this folder anywhere.
2. Install / place ffmpeg as above.
3. Double-click NeroGifConverter.exe
4. Convert a short clip; free mode adds the watermark.
5. Have a key? Click "Enter license…", paste it, convert the same clip again:
   the watermark is gone. To go back to free, delete license.key next to the
   exe and in %APPDATA%\NERO Tools\GIF Converter\.

What's new in 0.3.0
-------------------
- Record screen: tab "Record screen". Full screen, or Region (click
  "Select region…" and drag, Esc cancels; or type x / y / w / h). Choose FPS,
  cursor on/off and a countdown, press "Start recording". The app minimises;
  press "Stop" in the small window bottom-right. Free: stops at 15 s.
- Perfect social GIF: tab "Social GIF" (or "Make" after recording). Pick
  X / Twitter, Discord, Reddit, Telegram / WeChat sticker or GitHub README;
  the app re-encodes up to 4 times until the file is under the size limit and
  shows the final size.
- Languages: English, 简体中文, 繁體中文, 日本語, 한국어, Español, Português,
  Deutsch, Français, Русский. Picked from Windows automatically; change it with
  the "Language" box top-right (remembered).
- Screen recording records the primary monitor / the area you select. If the
  region is partly outside the screen, ffmpeg refuses it — select again.

Free web tool (no watermark, shorter clips)
-------------------------------------------
https://nerosaa.github.io/video-to-gif/

Support / store
---------------
Getly draft / store notes live in the source repo (GETLY_DRAFT.md).
Listing goes live only after this Windows zip smoke-passes on a real PC.

Not affiliated with ScreenToGif, Kap, or Gifski.
