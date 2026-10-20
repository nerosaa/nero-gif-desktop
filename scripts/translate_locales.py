#!/usr/bin/env python3
"""Dev tool: bulk-translate nero_gif/locales/en.json with the MiniMax API.

    MINIMAX_API_KEY=... python3 scripts/translate_locales.py [--only ja,ko] [--force]

The key is read from the environment only and never printed or written.
Output is validated (same keys, same {placeholders}); review by a human / the
unit tests (tests/test_i18n.py) afterwards.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOC = ROOT / "nero_gif" / "locales"
API = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
MODEL = "MiniMax-M2"
TARGETS = {
    "zh-Hans": "Simplified Chinese (mainland China)",
    "zh-Hant": "Traditional Chinese (Taiwan)",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "pt": "Portuguese (Brazil)",
    "de": "German",
    "fr": "French",
    "ru": "Russian",
}
PH = re.compile(r"\{[a-z_]+\}")

PROMPT = """You translate the UI strings of a small Windows desktop app ("NERO Tools GIF Converter":
screen recording, video to GIF, GIF compression, social-media GIF presets, license key unlock).
Translate every VALUE of the JSON object below into {lang}. Rules:
- Keep every key exactly as-is. Output the same number of keys.
- Keep placeholders like {{sec}}, {{size}}, {{path}} exactly (same braces, same names).
- Keep these tokens untranslated: GIF, FPS, ffmpeg, ffmpeg.exe, PATH, README-WINDOWS.txt, NERO1., NERO1.…,
  Pro, X / Twitter, Discord, Reddit, Telegram, WeChat, GitHub, README, MB, px, fps, Esc, ●, ■, ≤, →, \\n.
- Short, natural software-UI wording (button labels short). No explanations.
- Reply with ONLY the JSON object, no markdown fences.

{payload}"""


def call(lang_name: str, src: dict) -> dict:
    key = os.environ.get("MINIMAX_API_KEY")
    if not key:
        sys.exit("MINIMAX_API_KEY not set")
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT.format(
            lang=lang_name, payload=json.dumps(src, ensure_ascii=False, indent=1))}],
        "temperature": 0.2,
        "max_tokens": 16000,
    }
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode("utf-8"))
    text = data["choices"][0]["message"]["content"]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def validate(src: dict, out: dict) -> list[str]:
    errs = []
    for k, v in src.items():
        if k not in out or not isinstance(out[k], str) or not out[k].strip():
            errs.append(f"missing {k}")
            continue
        if sorted(PH.findall(v)) != sorted(PH.findall(out[k])):
            errs.append(f"placeholder mismatch {k}: {out[k]!r}")
    extra = set(out) - set(src)
    if extra:
        errs.append(f"extra keys {sorted(extra)}")
    return errs


def one(code: str, src: dict, force: bool) -> str:
    dest = LOC / f"{code}.json"
    if dest.exists() and not force:
        return f"{code}: exists, skipped"
    last = []
    for attempt in range(3):
        try:
            out = call(TARGETS[code], src)
        except Exception as e:  # noqa: BLE001
            last = [f"api/parse error: {type(e).__name__}: {e}"[:300]]
            print(f"{code}: attempt {attempt + 1} {last[0]}", file=sys.stderr, flush=True)
            continue
        last = validate(src, out)
        if last:
            print(f"{code}: attempt {attempt + 1} rejected: {last[:3]}", file=sys.stderr, flush=True)
        if not last:
            ordered = {k: out[k] for k in src}
            dest.write_text(json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return f"{code}: ok (attempt {attempt + 1})"
    return f"{code}: FAILED {last[:5]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    src = json.loads((LOC / "en.json").read_text(encoding="utf-8"))
    codes = [c for c in TARGETS if not a.only or c in a.only.split(",")]
    with ThreadPoolExecutor(max_workers=9) as ex:
        for line in ex.map(lambda c: one(c, src, a.force), codes):
            print(line, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
