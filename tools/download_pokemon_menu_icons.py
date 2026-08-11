#!/usr/bin/env python3
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "assets" / "ui" / "hud" / "pokemon_icons"
DISPLAY_OUT = BASE / "assets" / "ui" / "hud" / "pokemon_icons_display"
OUT.mkdir(parents=True, exist_ok=True)
DISPLAY_OUT.mkdir(parents=True, exist_ok=True)

SOURCE = "https://archives.bulbagarden.net/wiki/Special:Redirect/file/{dex:03d}MS3.png"


def download_icon(dex):
    path = OUT / f"{dex:03d}.png"
    if path.exists() and path.stat().st_size > 100:
        return "cached"
    url = SOURCE.format(dex=dex)
    req = urllib.request.Request(url, headers={"User-Agent": "PokemonTwitchChat overlay asset cache"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        return f"failed: {exc}"
    if not data.startswith(b"\x89PNG"):
        return "failed: not a png"
    path.write_bytes(data)
    return "downloaded"


def build_display_icon(dex):
    from PIL import Image

    source = OUT / f"{dex:03d}.png"
    dest = DISPLAY_OUT / f"{dex:03d}.png"
    if not source.exists():
        return
    icon = Image.open(source).convert("RGBA")
    bbox = icon.getbbox()
    if not bbox:
        return
    icon = icon.crop(bbox)
    max_size = 48
    scale = min(max_size / icon.width, max_size / icon.height)
    new_size = (max(1, round(icon.width * scale)), max(1, round(icon.height * scale)))
    icon = icon.resize(new_size, Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (52, 52), (0, 0, 0, 0))
    canvas.alpha_composite(icon, ((52 - icon.width) // 2, (52 - icon.height) // 2))
    canvas.save(dest)


def main():
    counts = {"cached": 0, "downloaded": 0, "failed": 0}
    for dex in range(1, 387):
        result = download_icon(dex)
        key = "failed" if result.startswith("failed") else result
        counts[key] = counts.get(key, 0) + 1
        if result.startswith("failed"):
            print(f"{dex:03d}: {result}")
        elif dex % 25 == 0:
            print(f"{dex:03d}: {counts}")
        if not result.startswith("failed"):
            build_display_icon(dex)
        time.sleep(0.03)
    print(counts)


if __name__ == "__main__":
    main()
