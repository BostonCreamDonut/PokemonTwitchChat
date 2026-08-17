#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "assets" / "twitch_panels"
ALERTS = BASE / "assets" / "ui" / "alerts"
OUT.mkdir(exist_ok=True)

FONT_DIR = Path("C:/Windows/Fonts")
FONT_BOLD = FONT_DIR / "consolab.ttf"
FONT_REG = FONT_DIR / "consola.ttf"

DARK = (5, 11, 13, 255)
PANEL = (16, 18, 18, 255)
CREAM = (248, 236, 216, 255)
INK = (18, 20, 21, 255)
RED = (205, 40, 25, 255)
RED_DARK = (104, 20, 12, 255)
GOLD = (226, 142, 14, 255)
BLUE = (28, 105, 180, 255)
PURPLE = (102, 63, 170, 255)
GRAY = (80, 88, 96, 255)
GREEN = (62, 137, 64, 255)
ORANGE = (214, 121, 20, 255)
WHITE = (255, 248, 232, 255)


def font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REG
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def rounded(draw, box, fill, outline=RED, width=2, radius=6):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(draw, xy, value, size, fill=INK, bold=False, stroke=False):
    draw.text(
        xy,
        value,
        font=font(size, bold),
        fill=fill,
        stroke_width=1 if stroke else 0,
        stroke_fill=(0, 0, 0, 200),
    )


def centered(draw, box, value, size, fill=WHITE, bold=True):
    f = font(size, bold)
    bbox = draw.textbbox((0, 0), value, font=f, stroke_width=1)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x1, y1, x2, y2 = box
    text(
        draw,
        (x1 + (x2 - x1 - w) / 2 - bbox[0], y1 + (y2 - y1 - h) / 2 - bbox[1] - 1),
        value,
        size,
        fill,
        bold,
        True,
    )


def header(draw, title, width):
    rounded(draw, (5, 5, width - 5, 49), PANEL, RED, 2, 6)
    centered(draw, (5, 5, width - 5, 49), title, 27)


def thumb(name, size=(62, 36)):
    src = Image.open(ALERTS / name).convert("RGBA")
    # Crop away the text panel and keep the illustrated top region.
    w, h = src.size
    crop = src.crop((5, 36, w - 5, int(h * 0.58)))
    crop.thumbnail(size, Image.Resampling.LANCZOS)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.alpha_composite(crop, ((size[0] - crop.width) // 2, (size[1] - crop.height) // 2))
    return out


def card_row(img, y, accent, alert_name, bits, title, body):
    draw = ImageDraw.Draw(img)
    rounded(draw, (13, y, 307, y + 51), CREAM, GOLD, 2, 5)
    rounded(draw, (18, y + 8, 82, y + 43), DARK, accent, 2, 3)
    img.alpha_composite(thumb(alert_name), (19, y + 8))

    rounded(draw, (88, y + 9, 142, y + 28), accent, (34, 19, 14, 255), 1, 3)
    centered(draw, (88, y + 9, 142, y + 28), str(bits), 12)
    text(draw, (148, y + 8), title, 14, INK, True)
    text(draw, (148, y + 30), body, 11, INK)


def build_bits_panel():
    img = Image.new("RGBA", (320, 300), DARK)
    draw = ImageDraw.Draw(img)
    rounded(draw, (3, 3, 317, 297), DARK, RED, 2, 7)
    header(draw, "BITS MODES", 320)

    rows = [
        (62, BLUE, "speed_round_card.png", 250, "SPEED MODE", "Every command fires twice"),
        (118, RED, "chaos_card.png", 500, "CHAOS MODE", "Adds random bonus inputs"),
        (174, PURPLE, "reverse_controls_card.png", 1000, "REVERSE CONTROLS", "Directions are swapped"),
        (230, ORANGE, "king_mode_card.png", 2000, "KING MODE", "Donor controls for 60s"),
    ]
    for row in rows:
        card_row(img, *row)

    rounded(draw, (13, 276, 307, 292), PANEL, GOLD, 1, 4)
    centered(draw, (13, 276, 307, 292), "All modes last 60 seconds", 10, (255, 212, 51, 255), False)
    img.save(OUT / "bits_modes_panel.png")
    return img


def sub_thumb(name, x, y, img):
    draw = ImageDraw.Draw(img)
    rounded(draw, (x, y, x + 84, y + 52), DARK, GOLD, 1, 3)
    src = thumb(name, (76, 42))
    img.alpha_composite(src, (x + 4, y + 5))


def sub_row(draw, y, accent, title, body):
    rounded(draw, (14, y, 306, y + 35), CREAM, GOLD, 1, 4)
    text(draw, (22, y + 5), title, 12, accent, True)
    text(draw, (22, y + 20), body, 11, INK)


def build_sub_panel():
    img = Image.new("RGBA", (320, 280), DARK)
    draw = ImageDraw.Draw(img)
    rounded(draw, (3, 3, 317, 277), DARK, RED, 2, 7)
    header(draw, "SUB PERKS", 320)

    sub_thumb("subscriber_card.png", 17, 75, img)
    sub_thumb("gift_sub_card.png", 118, 75, img)
    sub_thumb("resub_card.png", 219, 75, img)

    sub_row(draw, 148, RED, "SUBSCRIBER", "Commands count x2.")
    sub_row(draw, 188, ORANGE, "GIFTED SUB", "Recipient gets x2 credit.")
    sub_row(draw, 228, GREEN, "RESUB", "Welcome-back alert.")

    rounded(draw, (14, 264, 306, 276), PANEL, GOLD, 1, 3)
    centered(draw, (14, 264, 306, 276), "Automatic from Twitch sub status.", 7, (255, 212, 51, 255), False)
    img.save(OUT / "sub_perks_panel.png")
    return img


def build_preview(bits, subs):
    preview = Image.new("RGBA", (660, 330), (3, 6, 7, 255))
    preview.alpha_composite(bits, (10, 10))
    preview.alpha_composite(subs, (340, 10))
    draw = ImageDraw.Draw(preview)
    text(draw, (10, 316), "Twitch-ready PNG panels: 320px wide, under 1 MB", 11, WHITE)
    preview.save(OUT / "twitch_panels_preview.png")


def main():
    bits = build_bits_panel()
    subs = build_sub_panel()
    build_preview(bits, subs)
    print("rebuilt Twitch panel PNGs")


if __name__ == "__main__":
    main()
