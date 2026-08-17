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
HOW_TO_PLAY_FILL = (241, 225, 203, 255)

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


COMMAND_ICON_CROPS = {
    "up": (32, 233, 82, 283),
    "down": (32, 289, 82, 339),
    "left": (32, 345, 82, 395),
    "right": (32, 401, 82, 451),
    "a": (32, 458, 82, 508),
    "b": (32, 514, 82, 564),
}


def recolor_labeled_button(template, label, fill):
    button = template.copy()
    pixels = button.load()
    for y in range(button.height):
        for x in range(button.width):
            r, g, b, a = pixels[x, y]
            if a == 0:
                continue

            is_blue_fill = b > 80 and b > r * 1.25 and b > g * 1.15
            is_old_letter = 15 <= x <= 37 and 9 <= y <= 39 and (
                (r > 185 and g > 185 and b > 185) or (r < 48 and g < 48 and b < 58)
            )
            if is_blue_fill or is_old_letter:
                shade = max(.45, min(1.25, b / 205)) if is_blue_fill else .9
                pixels[x, y] = (
                    int(min(255, fill[0] * shade)),
                    int(min(255, fill[1] * shade)),
                    int(min(255, fill[2] * shade)),
                    a,
                )

    draw = ImageDraw.Draw(button)
    # Cover the original B face cleanly while keeping the real border/shadow from the source crop.
    draw.rounded_rectangle((8, 4, 42, 38), radius=3, fill=fill)
    f = font(19 if len(label) <= 2 else 15)
    bbox = draw.textbbox((0, 0), label, font=f, stroke_width=1)
    tx = 25 - (bbox[2] - bbox[0]) / 2 - bbox[0]
    ty = 25 - (bbox[3] - bbox[1]) / 2 - bbox[1] - 4
    draw.text((tx, ty), label, font=f, fill=(255, 248, 232, 255), stroke_width=1, stroke_fill=(0, 0, 0, 210))
    return button


def draw_how_to_play_commands(frame):
    draw = ImageDraw.Draw(frame)
    source_buttons = {name: frame.crop(box) for name, box in COMMAND_ICON_CROPS.items()}
    source_buttons["start"] = recolor_labeled_button(source_buttons["b"], "ST", (112, 78, 176, 255))
    source_buttons["select"] = recolor_labeled_button(source_buttons["b"], "SEL", (91, 96, 104, 255))

    # Preserve the original How To Play panel art and only repaint the command list.
    draw.rectangle((25, 225, 296, 568), fill=HOW_TO_PLAY_FILL)
    commands = [
        ("up", "!up"), ("down", "!down"),
        ("left", "!left"), ("right", "!right"),
        ("a", "!a"), ("b", "!b"),
        ("start", "!start"), ("select", "!select"),
    ]
    text_f = font(21)
    col_x = [35, 170]
    row_y = [236, 310, 384, 458]
    for i, (button, command) in enumerate(commands):
        cx = col_x[i % 2]
        cy = row_y[i // 2]
        frame.alpha_composite(source_buttons[button], (cx, cy))
        draw.text((cx + 52, cy + 9), command, font=text_f, fill=INK)

    # Update rule copy for instant-control mode while preserving the original stars/dividers.
    rule_f = font(21)
    draw.rectangle((82, 602, 296, 806), fill=HOW_TO_PLAY_FILL)
    rules = [
        ("Commands", "fire instantly!"),
        ("Subscribers", "get x2 credit!"),
        ("Bits activate", "special modes!"),
    ]
    for y, (line1, line2) in zip((610, 682, 754), rules):
        draw.text((88, y), line1, font=rule_f, fill=INK)
        if "x2" in line2:
            draw.text((88, y + 27), "get ", font=rule_f, fill=INK)
            draw.text((132, y + 27), "x2", font=rule_f, fill=INNER_RED)
            draw.text((162, y + 27), "credit!", font=rule_f, fill=INK)
        else:
            draw.text((88, y + 27), line2, font=rule_f, fill=INK)


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

    draw_how_to_play_commands(frame)

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
    def new_icon():
        return Image.new("RGBA", (72, 72), (0, 0, 0, 0))

    def shadow(d):
        d.ellipse((8, 58, 64, 68), fill=(99, 78, 50, 70))

    def save_location(name, image):
        image.save(HUD / f"location_{name}.png")

    house = new_icon()
    d = ImageDraw.Draw(house)
    shadow(d)
    d.rectangle((10, 34, 62, 64), fill=(239, 221, 174, 255), outline=INK, width=3)
    d.polygon([(8, 36), (36, 14), (66, 36)], fill=(220, 64, 38, 255), outline=INK)
    d.polygon([(18, 34), (36, 20), (56, 34)], fill=(255, 103, 55, 255))
    d.rectangle((20, 45, 32, 64), fill=(170, 75, 43, 255), outline=INK, width=2)
    d.rectangle((44, 43, 58, 53), fill=(94, 173, 217, 255), outline=INK, width=2)
    save_location("house", house)

    city = new_icon()
    d = ImageDraw.Draw(city)
    shadow(d)
    d.rectangle((12, 30, 31, 63), fill=(233, 219, 174, 255), outline=INK, width=3)
    d.rectangle((35, 22, 58, 63), fill=(212, 222, 225, 255), outline=INK, width=3)
    d.rectangle((15, 20, 28, 30), fill=(211, 55, 42, 255), outline=INK, width=2)
    d.rectangle((38, 14, 55, 22), fill=(63, 129, 203, 255), outline=INK, width=2)
    for x in (17, 40, 50):
        d.rectangle((x, 36, x + 7, 44), fill=(99, 176, 218, 255), outline=INK, width=1)
    d.rectangle((43, 50, 51, 63), fill=(128, 87, 55, 255), outline=INK, width=1)
    save_location("city", city)

    route = new_icon()
    d = ImageDraw.Draw(route)
    shadow(d)
    d.rectangle((30, 34, 36, 64), fill=(104, 73, 42, 255), outline=INK, width=2)
    d.polygon([(13, 17), (55, 17), (63, 26), (55, 35), (13, 35), (7, 26)], fill=(236, 196, 91, 255), outline=INK)
    d.line((18, 26, 50, 26), fill=(130, 84, 33, 255), width=4)
    d.rectangle((8, 55, 22, 64), fill=(75, 162, 65, 255))
    d.rectangle((50, 53, 65, 64), fill=(75, 162, 65, 255))
    d.line((28, 64, 38, 64), fill=INK, width=3)
    save_location("route", route)

    forest = new_icon()
    d = ImageDraw.Draw(forest)
    shadow(d)
    for cx, cy, scale, color in (
        (21, 42, 1.0, (39, 132, 62, 255)),
        (38, 35, 1.12, (45, 155, 71, 255)),
        (53, 44, 0.9, (34, 116, 57, 255)),
    ):
        d.rectangle((cx - 4, cy + 9, cx + 4, 63), fill=(107, 78, 42, 255), outline=INK, width=1)
        r = int(18 * scale)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color, outline=INK, width=3)
        d.ellipse((cx - r + 6, cy - r + 6, cx - 1, cy - 1), fill=(75, 183, 82, 255))
    save_location("forest", forest)

    cave = new_icon()
    d = ImageDraw.Draw(cave)
    shadow(d)
    d.polygon([(8, 61), (17, 28), (33, 13), (51, 20), (65, 61)], fill=(117, 105, 91, 255), outline=INK)
    d.polygon([(14, 61), (25, 35), (37, 22), (55, 61)], fill=(151, 139, 119, 255))
    d.pieslice((24, 30, 52, 76), 180, 360, fill=(22, 24, 26, 255), outline=INK, width=2)
    d.line((14, 61, 61, 61), fill=INK, width=3)
    d.polygon([(19, 29), (32, 15), (28, 38)], fill=(189, 178, 151, 255))
    save_location("cave", cave)

    gym = new_icon()
    d = ImageDraw.Draw(gym)
    shadow(d)
    d.rectangle((10, 35, 62, 64), fill=(226, 214, 177, 255), outline=INK, width=3)
    d.polygon([(7, 35), (36, 15), (65, 35)], fill=(179, 48, 39, 255), outline=INK)
    d.rectangle((18, 45, 54, 58), fill=(80, 76, 67, 255), outline=INK, width=2)
    d.text((21, 42), "GYM", font=font(13), fill=(255, 245, 202, 255), stroke_width=1, stroke_fill=INK)
    d.rectangle((31, 56, 41, 64), fill=(118, 76, 48, 255), outline=INK, width=1)
    save_location("gym", gym)

    center = new_icon()
    d = ImageDraw.Draw(center)
    shadow(d)
    d.rectangle((10, 32, 62, 64), fill=(248, 240, 219, 255), outline=INK, width=3)
    d.rectangle((14, 22, 58, 35), fill=(210, 45, 37, 255), outline=INK, width=2)
    d.ellipse((26, 10, 46, 30), fill=(248, 248, 242, 255), outline=INK, width=2)
    d.line((31, 20, 41, 20), fill=(210, 45, 37, 255), width=4)
    d.line((36, 15, 36, 25), fill=(210, 45, 37, 255), width=4)
    d.rectangle((30, 48, 42, 64), fill=(95, 147, 199, 255), outline=INK, width=2)
    save_location("center", center)

    mart = new_icon()
    d = ImageDraw.Draw(mart)
    shadow(d)
    d.rectangle((10, 32, 62, 64), fill=(237, 232, 211, 255), outline=INK, width=3)
    d.rectangle((14, 20, 58, 34), fill=(49, 127, 208, 255), outline=INK, width=2)
    d.text((21, 19), "MART", font=font(11), fill=(255, 249, 224, 255), stroke_width=1, stroke_fill=INK)
    d.rectangle((30, 48, 42, 64), fill=(95, 147, 199, 255), outline=INK, width=2)
    d.rectangle((16, 42, 27, 51), fill=(99, 176, 218, 255), outline=INK, width=1)
    d.rectangle((47, 42, 58, 51), fill=(99, 176, 218, 255), outline=INK, width=1)
    save_location("mart", mart)

    water = new_icon()
    d = ImageDraw.Draw(water)
    shadow(d)
    d.rectangle((9, 46, 63, 63), fill=(69, 156, 215, 255), outline=INK, width=2)
    for y in (48, 56):
        d.arc((12, y - 6, 31, y + 6), 0, 180, fill=(166, 222, 245, 255), width=2)
        d.arc((32, y - 6, 51, y + 6), 0, 180, fill=(166, 222, 245, 255), width=2)
    d.polygon([(18, 43), (31, 22), (34, 43)], fill=(235, 238, 230, 255), outline=INK)
    d.polygon([(34, 43), (52, 28), (54, 43)], fill=(215, 54, 41, 255), outline=INK)
    d.rectangle((29, 17, 34, 45), fill=(99, 70, 42, 255), outline=INK, width=1)
    save_location("water", water)

    interior = new_icon()
    d = ImageDraw.Draw(interior)
    shadow(d)
    d.rectangle((16, 16, 56, 64), fill=(180, 115, 68, 255), outline=INK, width=3)
    d.rectangle((22, 23, 50, 64), fill=(121, 76, 48, 255), outline=INK, width=2)
    d.ellipse((43, 42, 49, 48), fill=(245, 198, 74, 255), outline=INK, width=1)
    d.rectangle((20, 12, 52, 18), fill=(205, 157, 82, 255), outline=INK, width=2)
    save_location("interior", interior)

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
