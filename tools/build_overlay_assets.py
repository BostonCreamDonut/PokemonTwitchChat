#!/usr/bin/env python3
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parents[1]
UI = BASE / "assets" / "ui"
HUD = UI / "hud"
HUD.mkdir(exist_ok=True)

SCREEN_W = 1920
SCREEN_H = 1080

CREAM = (248, 236, 216, 255)
DARK = (6, 12, 14, 255)
FOOTER = (7, 12, 14, 255)
INK = (18, 20, 21, 255)
RED = (104, 20, 12, 255)
RED_DARK = (73, 11, 7, 255)
GOLD = (226, 142, 14, 255)
INNER_RED = (205, 40, 25, 255)

REFERENCE = UI / "reference"
BADGE_REFERENCE = REFERENCE / "fire_red_badges.png"
SKULL_REFERENCE = REFERENCE / "skull_pixel_reference.png"

BOTTOM_BOXES = {
    "location": (12, 936, 306, 1076),
    "badges": (320, 936, 982, 1076),
    "party": (996, 936, 1300, 1076),
    "deaths": (1314, 936, 1450, 1076),
    "objective": (1464, 936, 1908, 1076),
}

GAME_APERTURE = (321, 166, 1528, 936)

FONT_DIR = Path("C:/Windows/Fonts")
HEADER_FONT = FONT_DIR / "consolab.ttf"


def font(size):
    if HEADER_FONT.exists():
        return ImageFont.truetype(str(HEADER_FONT), size)
    return ImageFont.load_default()


def chamfered_rect(draw, box, radius, fill, outline=None, width=1):
    x1, y1, x2, y2 = [round(v) for v in box]
    pts = [
        (x1 + radius, y1), (x2 - radius, y1), (x2, y1 + radius),
        (x2, y2 - radius), (x2 - radius, y2), (x1 + radius, y2),
        (x1, y2 - radius), (x1, y1 + radius),
    ]
    draw.polygon(pts, fill=fill)
    if outline and width:
        for i in range(width):
            pts_i = [
                (x1 + radius + i, y1 + i), (x2 - radius - i, y1 + i),
                (x2 - i, y1 + radius + i), (x2 - i, y2 - radius - i),
                (x2 - radius - i, y2 - i), (x1 + radius + i, y2 - i),
                (x1 + i, y2 - radius - i), (x1 + i, y1 + radius + i),
            ]
            draw.line(pts_i + [pts_i[0]], fill=outline, width=1)


def panel(draw, box, title):
    x1, y1, x2, y2 = box
    chamfered_rect(draw, box, 10, (4, 6, 7, 255), GOLD, 3)
    chamfered_rect(draw, (x1 + 4, y1 + 4, x2 - 4, y2 - 4), 7, CREAM, INNER_RED, 2)
    chamfered_rect(draw, (x1 + 6, y1 + 6, x2 - 6, y1 + 40), 5, RED, None, 0)
    draw.rectangle((x1 + 7, y1 + 23, x2 - 7, y1 + 40), fill=RED_DARK)
    draw.line((x1 + 6, y1 + 42, x2 - 6, y1 + 42), fill=(4, 6, 7, 255), width=2)
    f = font(23)
    bbox = draw.textbbox((0, 0), title.upper(), font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x1 + (x2 - x1 - tw) / 2
    ty = y1 + 9 + (30 - th) / 2
    draw.text((tx + 2, ty + 2), title.upper(), font=f, fill=(0, 0, 0, 190))
    draw.text((tx, ty), title.upper(), font=f, fill=(255, 248, 232, 255))


def make_clean_frame():
    source = UI / "overlay_frame_source.png"
    frame = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(frame)

    # Clear live-value areas so the frame itself is clean even before PyQt paints state.
    draw.rectangle((1549, 219, 1907, 575), fill=CREAM)
    draw.rectangle((1548, 637, 1878, 865), fill=(14, 18, 20, 255))

    # Clear old bottom panel row, old trainer-status area, and old footer contents.
    draw.rectangle((0, 868, SCREEN_W, SCREEN_H), fill=DARK)

    # Shorten live chat visually so the new bottom row can use the lower-right space.
    draw.rectangle((1548, 866, 1915, 936), fill=DARK)
    draw.line((1548, 865, 1910, 865), fill=GOLD, width=3)
    draw.line((1548, 862, 1910, 862), fill=INNER_RED, width=2)

    # The approved source used a checkerboard placeholder in the game area.
    # Cut the full gameplay aperture to alpha 0 so OBS/mGBA shows through.
    draw.rectangle(GAME_APERTURE, fill=(0, 0, 0, 0))

    for title, box in BOTTOM_BOXES.items():
        panel(draw, box, title)

    frame.save(UI / "overlay_frame.png")


def remove_outer_background(icon):
    icon = icon.convert("RGBA")
    w, h = icon.size
    edge = set()
    stack = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
    stack += [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    while stack:
        x, y = stack.pop()
        if (x, y) in edge or not (0 <= x < w and 0 <= y < h):
            continue
        r, g, b, a = icon.getpixel((x, y))
        if a and r < 80 and g < 80 and b < 80:
            continue
        if a and not (r > 236 and g > 236 and b > 236):
            continue
        edge.add((x, y))
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    data = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = icon.getpixel((x, y))
            if (x, y) in edge:
                data.append((0, 0, 0, 0))
            elif r > 246 and g > 246 and b > 246:
                data.append((248, 248, 238, a))
            else:
                data.append((r, g, b, a))
    icon.putdata(data)
    return icon


def extract_components(path, min_pixels):
    ref = Image.open(path).convert("RGBA")
    w, h = ref.size
    mask = set()
    for y in range(h):
        for x in range(w):
            r, g, b, a = ref.getpixel((x, y))
            if a and not (r > 244 and g > 244 and b > 244):
                mask.add((x, y))

    seen = set()
    comps = []
    for start in list(mask):
        if start in seen:
            continue
        q = deque([start])
        seen.add(start)
        xs, ys = [], []
        while q:
            x, y = q.popleft()
            xs.append(x)
            ys.append(y)
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in mask and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))
        if len(xs) >= min_pixels:
            comps.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1))
    return ref, comps


def make_badge_assets():
    if not BADGE_REFERENCE.exists():
        return
    ref, comps = extract_components(BADGE_REFERENCE, 2000)
    boxes = sorted(comps, key=lambda b: (b[1] // max(1, ref.height // 3), b[0]))[:8]
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        pad = 8
        badge = ref.crop((max(0, x1 - pad), max(0, y1 - pad), min(ref.width, x2 + pad), min(ref.height, y2 + pad)))
        badge = remove_outer_background(badge)
        badge.save(HUD / f"badge_{i}.png")

        locked = badge.convert("RGBA")
        data = []
        for r, g, b, a in locked.getdata():
            if a == 0:
                data.append((0, 0, 0, 0))
            else:
                lum = int(0.299 * r + 0.587 * g + 0.114 * b)
                tone = max(30, min(95, int(lum * 0.32)))
                data.append((tone, max(25, tone - 8), max(20, tone - 17), int(a * 0.72)))
        locked.putdata(data)
        locked.save(HUD / f"badge_{i}_locked.png")


def make_skull_asset():
    if not SKULL_REFERENCE.exists():
        return
    ref, comps = extract_components(SKULL_REFERENCE, 20)
    dark = []
    for y in range(ref.height):
        for x in range(ref.width):
            r, g, b, a = ref.getpixel((x, y))
            if a and r < 90 and g < 90 and b < 90:
                dark.append((x, y))
    if not dark:
        return
    x1 = max(0, min(x for x, _ in dark) - 2)
    y1 = max(0, min(y for _, y in dark) - 2)
    x2 = min(ref.width, max(x for x, _ in dark) + 3)
    y2 = min(ref.height, max(y for _, y in dark) + 3)
    skull = remove_outer_background(ref.crop((x1, y1, x2, y2)))
    skull.save(HUD / "skull_reference.png")


def make_misc_icons():
    house = Image.new("RGBA", (72, 72), (0, 0, 0, 0))
    d = ImageDraw.Draw(house)
    d.rectangle((6, 54, 66, 66), fill=(37, 138, 50, 255))
    d.rectangle((10, 34, 62, 64), fill=(239, 221, 174, 255), outline=INK, width=3)
    d.polygon([(8, 36), (36, 14), (66, 36)], fill=(220, 64, 38, 255), outline=INK)
    d.polygon([(18, 34), (36, 20), (56, 34)], fill=(255, 103, 55, 255))
    d.rectangle((20, 45, 32, 64), fill=(170, 75, 43, 255), outline=INK, width=2)
    d.rectangle((44, 43, 58, 53), fill=(94, 173, 217, 255), outline=INK, width=2)
    house.save(HUD / "location_house.png")

    flag = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(flag)
    d.rectangle((11, 5, 15, 43), fill=(47, 42, 29, 255))
    d.rectangle((6, 41, 29, 45), fill=(47, 42, 29, 255))
    d.polygon([(15, 7), (42, 15), (15, 27)], fill=(226, 43, 30, 255), outline=(45, 20, 15, 255))
    d.polygon([(17, 9), (32, 15), (17, 21)], fill=(255, 76, 48, 255))
    d.rectangle((7, 3, 17, 11), fill=(238, 211, 66, 255), outline=(45, 38, 12, 255))
    flag.save(HUD / "objective_flag.png")

    ball = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(ball)
    d.ellipse((6, 34, 42, 43), fill=(151, 111, 56, 70))
    d.ellipse((8, 8, 40, 40), fill=(14, 14, 14, 255))
    d.pieslice((12, 12, 36, 36), 180, 360, fill=(222, 34, 25, 255))
    d.pieslice((12, 12, 36, 36), 0, 180, fill=(248, 246, 235, 255))
    d.rectangle((12, 22, 36, 26), fill=(14, 14, 14, 255))
    d.ellipse((18, 18, 30, 30), fill=(14, 14, 14, 255))
    d.ellipse((22, 22, 26, 26), fill=(248, 246, 235, 255))
    ball.save(HUD / "party_pokeball.png")

    empty = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(empty)
    d.ellipse((6, 34, 42, 43), fill=(151, 111, 56, 55))
    d.ellipse((12, 12, 36, 36), fill=(24, 21, 18, 255))
    d.pieslice((14, 14, 34, 34), 120, 300, fill=(52, 44, 33, 255))
    d.pieslice((15, 14, 34, 34), 300, 120, fill=(69, 58, 44, 255))
    empty.save(HUD / "party_empty.png")


def make_hud_sprites():
    make_badge_assets()
    make_skull_asset()
    make_misc_icons()


if __name__ == "__main__":
    make_clean_frame()
    make_hud_sprites()
    print("rebuilt overlay_frame.png and HUD sprites")
