#!/usr/bin/env python3
import json, math, sys, time
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen, QBrush, QPixmap, QPolygonF
from PyQt5.QtWidgets import QApplication, QWidget

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
OV = CFG["overlay"]

STATE = BASE / OV["state_file"]
EVENTS = BASE / OV["event_file"]
BOOT = BASE / OV.get("boot_file", "boot_state.json")
DIALOGUE = BASE / OV.get("dialogue_file", "dialogue_state.json")
FRAME = BASE / OV["reference_frame"]
HUD_DIR = BASE / "assets" / "ui" / "hud"

SRC_W = float(OV.get("source_width", 1672))
SRC_H = float(OV.get("source_height", 941))
CREAM = QColor("#F4E8CD")
CREAM2 = QColor("#F8EFD9")
INK = QColor("#171819")
RED = QColor("#C83725")
ORANGE = QColor("#EFAF18")
GREEN = QColor("#55A936")
BLUE = QColor("#347EC6")
PURPLE = QColor("#7A46B5")
MUTED = QColor("#BEB8AA")
WHITE = QColor("#FFF9EC")
GOLD = QColor("#F5C13D")
DARK = QColor("#0E1214")
DARK2 = QColor("#121617")
FOOTER = QColor("#0A0D0F")
VOTE_COLORS = [RED, ORANGE, GREEN, BLUE, PURPLE]

LABELS = {
    "!up":"UP","!down":"DOWN","!left":"LEFT","!right":"RIGHT",
    "!a":"A","!b":"B","!l":"L","!r":"R","!start":"START","!select":"SELECT"
}

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.state = {}
        self.event = None
        self.event_id = None
        self.event_start = 0
        self.dialogue = None
        self.dialogue_id = None
        self.dialogue_start = 0
        self.boot = None
        self.frame = QPixmap(str(FRAME))
        if self.frame.isNull():
            raise SystemExit(f"Overlay frame not found or unreadable: {FRAME}")

        self.screen_w = int(OV.get("screen_width", self.frame.width()))
        self.screen_h = int(OV.get("screen_height", self.frame.height()))
        if self.frame.width() != self.screen_w or self.frame.height() != self.screen_h:
            self.frame = self.frame.scaled(self.screen_w, self.screen_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.sx = self.screen_w / SRC_W
        self.sy = self.screen_h / SRC_H
        self.font_family = self.pick_font()
        self.hud = self.load_hud()

        self.setWindowTitle("Twitch Plays Pokemon Overlay")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.resize(self.screen_w, self.screen_h)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(max(20, int(1000 / int(OV.get("refresh_hz", 30)))))

    def tx(self, x): return x * self.sx
    def ty(self, y): return y * self.sy
    def tw(self, w): return w * self.sx
    def th(self, h): return h * self.sy

    def avg_scale(self):
        return (self.sx + self.sy) / 2

    def pick_font(self):
        available = set(QFontDatabase().families())
        for name in ("DejaVu Sans Condensed", "Arial Narrow", "Arial", "Liberation Sans"):
            if name in available:
                return name
        return QApplication.font().family()

    def load_hud(self):
        sprites = {}
        if not HUD_DIR.exists():
            return sprites
        for path in HUD_DIR.rglob("*.png"):
            pix = QPixmap(str(path))
            if not pix.isNull():
                if path.parent.name == "pokemon_icons_display":
                    sprites[f"pokemon_{path.stem}"] = pix
                elif path.parent.name == "pokemon_icons":
                    sprites.setdefault(f"pokemon_{path.stem}", pix)
                else:
                    sprites[path.stem] = pix
        return sprites

    def read_json(self, path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def poll(self):
        s = self.read_json(STATE)
        if s:
            self.state = s

        e = self.read_json(EVENTS)
        if e and e.get("id") != self.event_id:
            self.event = e
            self.event_id = e.get("id")
            self.event_start = time.monotonic()

        d = self.read_json(DIALOGUE)
        if d and d.get("id") != self.dialogue_id:
            self.dialogue = d
            self.dialogue_id = d.get("id")
            self.dialogue_start = time.monotonic()

        b = self.read_json(BOOT)
        if b:
            self.boot = b

        self.update()

    def font(self, size, bold=False):
        f = QFont(self.font_family, max(1, int(round(size * self.avg_scale()))))
        f.setBold(bold)
        f.setStyleHint(QFont.SansSerif)
        return f

    def screen_font(self, size, bold=False):
        f = QFont(self.font_family, max(1, int(round(size))))
        f.setBold(bold)
        f.setStyleHint(QFont.SansSerif)
        return f

    def text(self, p, t, x, y, w, h, size=12, color=INK, bold=False, align=Qt.AlignLeft | Qt.AlignVCenter):
        p.setFont(self.font(size, bold))
        p.setPen(color)
        p.drawText(QRectF(self.tx(x), self.ty(y), self.tw(w), self.th(h)), align, str(t))

    def sprite(self, p, name, x, y, w, h):
        pix = self.hud.get(name)
        if not pix:
            return False
        target = QRectF(self.tx(x), self.ty(y), self.tw(w), self.th(h))
        source = QRectF(0, 0, pix.width(), pix.height())
        p.drawPixmap(target, pix, source)
        return True

    def screen_sprite(self, p, name, x, y, w, h, opacity=1.0):
        pix = self.hud.get(name)
        if not pix:
            return False
        target = QRectF(float(x), float(y), float(w), float(h))
        source = QRectF(0, 0, pix.width(), pix.height())
        if opacity < 1.0:
            p.save()
            p.setOpacity(max(0.0, min(1.0, float(opacity))))
        p.drawPixmap(target, pix, source)
        if opacity < 1.0:
            p.restore()
        return True

    def screen_text(self, p, t, x, y, w, h, size=12, color=INK, bold=False, align=Qt.AlignLeft | Qt.AlignVCenter):
        p.setFont(self.screen_font(size, bold))
        p.setPen(color)
        p.drawText(QRectF(float(x), float(y), float(w), float(h)), align, str(t))

    def screen_text_size(self, p, t, size=12, bold=False):
        p.setFont(self.screen_font(size, bold))
        metrics = p.fontMetrics()
        return metrics.horizontalAdvance(str(t)), metrics.height()

    def screen_rounded(self, p, x, y, w, h, fill, border=RED, r=6, bw=2):
        p.setPen(QPen(border, max(1, int(round(bw)))))
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(QRectF(float(x), float(y), float(w), float(h)), float(r), float(r))

    def rounded(self, p, x, y, w, h, fill, border=RED, r=6, bw=2):
        p.setPen(QPen(border, max(1, bw * self.avg_scale())))
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(QRectF(self.tx(x), self.ty(y), self.tw(w), self.th(h)), r * self.sx, r * self.sy)

    def ellipse(self, p, cx, cy, rx, ry=None, pen=None, brush=None):
        if ry is None:
            ry = rx
        if pen is not None:
            p.setPen(pen)
        if brush is not None:
            p.setBrush(brush)
        p.drawEllipse(QPointF(self.tx(cx), self.ty(cy)), self.tw(rx), self.th(ry))

    def pokeball(self, p, cx, cy, r):
        penw = max(1, int(round(r * 0.08 * self.avg_scale())))
        p.setPen(QPen(QColor("#111"), penw))
        p.setBrush(RED)
        self.ellipse(p, cx, cy, r)
        p.setBrush(WHITE)
        p.drawPie(QRectF(self.tx(cx-r), self.ty(cy-r), self.tw(2*r), self.th(2*r)), 180*16, 180*16)
        p.setBrush(QColor("#111"))
        p.drawRect(QRectF(self.tx(cx-r), self.ty(cy-1.8), self.tw(2*r), self.th(3.6)))
        p.setBrush(WHITE)
        self.ellipse(p, cx, cy, r * 0.27)

    def clear_live_values(self, p):
        p.setPen(Qt.NoPen)

        # Current Round body (below header)
        p.setBrush(CREAM2)
        p.drawRect(QRectF(1549, 219, 358, 356))

        # Live Chat body
        p.setBrush(DARK)
        p.drawRect(QRectF(1548, 637, 330, 226))

    def draw_votes(self, p):
        rows = self.state.get("votes", [])[:5]
        rem = float(self.state.get("time_remaining", 3.0))

        if not rows:
            self.screen_text(p, "Waiting for votes...", 1564, 355, 310, 24, 14, QColor("#68645D"), False, Qt.AlignCenter)

        yy = 250
        for i, row in enumerate(rows):
            pct = float(row.get("percent", 0))
            wt = int(row.get("weighted_votes", 0))
            cmd = LABELS.get(row.get("command"), row.get("command", "")).upper()
            col = VOTE_COLORS[i % len(VOTE_COLORS)]

            self.screen_rounded(p, 1570, yy, 32, 32, col, QColor("#222"), 4, 2)
            sym = {"UP": "^", "DOWN": "v", "LEFT": "<", "RIGHT": ">"}.get(cmd, cmd[:1])
            self.screen_text(p, sym, 1570, yy, 32, 32, 18, WHITE, True, Qt.AlignCenter)
            self.screen_text(p, cmd, 1617, yy, 75, 32, 16, INK, True)

            bx, by, bw, bh = 1695, yy + 7, 112, 18
            self.screen_rounded(p, bx, by, bw, bh, QColor("#E3D8C2"), QColor("#C7B99F"), 3, 1)
            if pct > 0:
                self.screen_rounded(p, bx, by, max(3, bw * pct / 100), bh, col, col, 3, 0)

            self.screen_text(p, f"{pct:.0f}%", 1817, yy - 1, 70, 18, 16, INK, True, Qt.AlignRight | Qt.AlignVCenter)
            self.screen_text(p, f"({wt})", 1817, yy + 17, 70, 16, 13, INK, True, Qt.AlignRight | Qt.AlignVCenter)
            yy += 58

        self.screen_text(p, f"Total Weighted Votes: {int(self.state.get('round_weighted_vote_count', 0))}",
                         1575, 542, 310, 24, 14, INK, True, Qt.AlignCenter)

        self.screen_rounded(p, 1700, 196, 52, 24, QColor("#B53022"), QColor("#8E261B"), 4, 1)
        self.screen_text(p, f"{rem:.1f}s", 1700, 196, 52, 24, 12, WHITE, True, Qt.AlignCenter)

    def draw_chat(self, p):
        yy = 555
        rows = list(reversed(self.state.get("recent_commands", [])))[:9]
        palette = [
            QColor("#EF4B2F"), QColor("#E9AA17"), QColor("#45B73E"), QColor("#3DC5D9"),
            QColor("#A65ACC"), QColor("#F39E21"), QColor("#38B9D5"), QColor("#EF86B0")
        ]
        for row in rows:
            name = str(row.get("username", ""))[:16]
            sub = bool(row.get("subscriber"))
            display = ("★ " if sub else "") + name
            col = GOLD if sub else palette[(hash(name) & 0x7fffffff) % len(palette)]
            self.text(p, display + ":", 1338, yy, 145, 20, 8, col, sub)
            self.text(p, row.get("command", ""), 1488, yy, 90, 20, 8, WHITE, True)
            yy += 24

    def draw_bottom(self, p):
        st = OV.get("status", {})
        loc = self.state.get("location", st.get("location", "Pallet Town"))
        badges = int(self.state.get("badges", st.get("badges", 2)))
        party = int(self.state.get("party_size", st.get("party_size", 3)))
        party_fainted = self.state.get("party_fainted", [])
        party_species = self.state.get("party_species", [])
        deaths = int(self.state.get("deaths", st.get("deaths", 3)))
        objective = self.state.get("objective", st.get("objective", "Defeat Brock\nin Pewter City"))

        self.draw_location_panel(p, loc)
        self.draw_badges_panel(p, badges)
        self.draw_party_panel(p, party, party_fainted, party_species)
        self.draw_deaths_panel(p, deaths)
        self.draw_objective_panel(p, objective)

        # Side stats, kept out of the center gameplay space.
        top = self.state.get("top_trainers", [])
        top_name = str(top[0]["username"] if top else "pikafan23")[:16]
        top_lvl = top[0]["level"] if top else 38
        total_trainers = int(self.state.get("unique_players", 1248))
        longest_streak = int(self.state.get("longest_streak", 27))
        self.screen_text(p, f"TOP: {top_name} Lv.{top_lvl}", 18, 878, 285, 24, 15, WHITE, True, Qt.AlignCenter)
        self.screen_text(p, f"STREAK: {longest_streak}", 18, 908, 285, 24, 15, WHITE, True, Qt.AlignCenter)
        self.screen_text(p, f"TRAINERS: {total_trainers:,}", 1558, 893, 330, 24, 15, WHITE, True, Qt.AlignCenter)

    def draw_location_panel(self, p, loc):
        body = (22, 984, 296, 1066)
        icon_w, icon_h = 60, 60
        text = str(loc)
        icon_name = self.location_icon_name(text)
        font_size = 26
        gap = 14
        max_text_w = body[2] - body[0] - icon_w - gap - 16
        text_w, text_h = self.screen_text_size(p, text, font_size, True)
        while text_w > max_text_w and font_size > 16:
            font_size -= 1
            text_w, text_h = self.screen_text_size(p, text, font_size, True)
        if text_w > max_text_w:
            while text and self.screen_text_size(p, text + "...", font_size, True)[0] > max_text_w:
                text = text[:-1].rstrip()
            text = text + "..."
            text_w, text_h = self.screen_text_size(p, text, font_size, True)
        group_w = icon_w + gap + text_w
        x = body[0] + (body[2] - body[0] - group_w) / 2
        cy = body[1] + (body[3] - body[1]) / 2
        if not self.screen_sprite(p, icon_name, x, cy - icon_h / 2, icon_w, icon_h):
            self.screen_sprite(p, "location_house", x, cy - icon_h / 2, icon_w, icon_h)
        self.screen_text(p, text, x + icon_w + gap, cy - text_h / 2 - 2, text_w + 8, text_h + 8, font_size, INK, True)

    def location_icon_name(self, location):
        name = str(location).lower()
        compact = name.replace(".", "").replace("'", "")
        if any(word in compact for word in ("pokemon center", "poke center")):
            return "location_center"
        if any(word in compact for word in ("mart", "department store")):
            return "location_mart"
        if "gym" in compact:
            return "location_gym"
        if any(word in compact for word in ("forest", "berry forest", "pattern bush")):
            return "location_forest"
        if any(word in compact for word in ("cave", "mt moon", "rock tunnel", "seafoam", "victory road", "diglett", "ember spa")):
            return "location_cave"
        if any(word in compact for word in ("route", "road", "path", "bridge", "cape")):
            return "location_route"
        if any(word in compact for word in ("sea", "island", "isle", "water", "ferry", "ship", "ss anne", "harbor", "port")):
            return "location_water"
        if any(word in compact for word in ("house", "lab", "room", "floor", "tower", "mansion", "hideout", "building", "gate")):
            return "location_interior"
        if any(word in compact for word in ("city", "town", "plateau")):
            return "location_city"
        return "location_house"

    def draw_badges_panel(self, p, badges):
        count = max(0, min(8, int(badges)))
        body = (330, 984, 972, 1066)
        size = 52
        gap = 18
        group_w = 8 * size + 7 * gap
        x0 = body[0] + (body[2] - body[0] - group_w) / 2
        y0 = body[1] + (body[3] - body[1] - size) / 2
        for i in range(8):
            name = f"badge_{i}" if i < count else f"badge_{i}_locked"
            if not self.screen_sprite(p, name, x0 + i * (size + gap), y0, size, size):
                self.screen_sprite(p, f"badge_{i}", x0 + i * (size + gap), y0, size, size)

    def draw_party_panel(self, p, party, party_fainted=None, party_species=None):
        count = max(0, min(6, int(party)))
        party_fainted = party_fainted if isinstance(party_fainted, list) else []
        party_species = party_species if isinstance(party_species, list) else []
        body = (1006, 984, 1290, 1066)
        size = 52
        gap = -7
        group_w = 6 * size + 5 * gap
        x0 = body[0] + (body[2] - body[0] - group_w) / 2
        y0 = body[1] + (body[3] - body[1] - size) / 2
        for i in range(6):
            name = "party_empty"
            if i < count:
                species = self.species_to_dex(party_species[i]) if i < len(party_species) else 0
                name = f"pokemon_{species:03d}" if species else "party_pokeball"
            opacity = 0.35 if i < count and i < len(party_fainted) and party_fainted[i] else 1.0
            if not self.screen_sprite(p, name, x0 + i * (size + gap), y0, size, size, opacity):
                fallback = "party_pokeball" if i < count else "party_empty"
                self.screen_sprite(p, fallback, x0 + i * (size + gap), y0, size, size, opacity)

    def species_to_dex(self, species):
        try:
            species = int(species)
        except (TypeError, ValueError):
            return 0
        if 1 <= species <= 251:
            return species
        if 252 <= species <= 276:
            return 201
        if 277 <= species <= 411:
            return species - 25
        return 0

    def draw_deaths_panel(self, p, deaths):
        body = (1324, 984, 1440, 1066)
        text = str(deaths)
        font_size = 30
        text_w, text_h = self.screen_text_size(p, text, font_size, True)
        skull_size = 48
        gap = 14
        group_w = skull_size + gap + text_w
        x = body[0] + (body[2] - body[0] - group_w) / 2
        cy = body[1] + (body[3] - body[1]) / 2
        self.screen_sprite(p, "skull_reference", x, cy - skull_size / 2, skull_size, skull_size)
        self.screen_text(p, text, x + skull_size + gap, cy - text_h / 2 - 2, text_w + 8, text_h + 8, font_size, INK, True)

    def draw_objective_panel(self, p, objective):
        body = (1474, 984, 1898, 1066)
        text = str(objective)
        font_size = 24
        lines = text.splitlines() or [text]
        widths = [self.screen_text_size(p, line, font_size, True)[0] for line in lines]
        _, line_h = self.screen_text_size(p, "Ag", font_size, True)
        text_w = max(widths) if widths else 0
        text_h = len(lines) * line_h
        icon_size = 50
        gap = 20
        group_w = icon_size + gap + text_w
        x = body[0] + (body[2] - body[0] - group_w) / 2
        cy = body[1] + (body[3] - body[1]) / 2
        self.screen_sprite(p, "objective_flag", x, cy - icon_size / 2, icon_size, icon_size)
        self.screen_text(p, text, x + icon_size + gap, cy - text_h / 2 - 2, text_w + 8, text_h + 8, font_size, INK, True)

    def draw_active_effects(self, p):
        effects = self.state.get("active_effects", [])
        if not effects:
            return
        self.draw_effect_timer(p, effects[0])
        x, y, w = 280, 585, 205
        h = min(125, 42 + 40 * len(effects[:2]))
        self.rounded(p, x, y, w, h, QColor("#111516", 238), RED, 6, 2)
        self.text(p, "ACTIVE EFFECTS", x + 8, y + 3, w - 16, 20, 8, CREAM, True, Qt.AlignCenter)
        yy = y + 28
        for ef in effects[:2]:
            self.text(p, "◆", x + 10, yy, 20, 20, 10, GOLD, True, Qt.AlignCenter)
            self.text(p, ef.get("effect", "").replace("_", " ").upper(), x + 34, yy, w - 44, 16, 8, WHITE, True)
            self.text(p, f"{float(ef.get('remaining', 0)):.0f}s", x + 34, yy + 15, 50, 14, 8, CREAM, True)
            yy += 38

    def draw_effect_timer(self, p, effect):
        label = effect.get("effect", "").replace("_", " ").upper() or "ACTIVE EFFECT"
        remaining = max(0, float(effect.get("remaining", 0)))
        self.rounded(p, 1150, 155, 168, 58, QColor("#111516", 240), ORANGE, 4, 2)
        bolt = QPolygonF([
            QPointF(self.tx(1168), self.ty(164)),
            QPointF(self.tx(1156), self.ty(186)),
            QPointF(self.tx(1167), self.ty(184)),
            QPointF(self.tx(1160), self.ty(205)),
            QPointF(self.tx(1182), self.ty(176)),
            QPointF(self.tx(1170), self.ty(178)),
        ])
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(GOLD))
        p.drawPolygon(bolt)
        self.text(p, label, 1190, 164, 104, 19, 8, WHITE, True, Qt.AlignCenter)
        self.text(p, f"{remaining:04.1f}s" if remaining < 10 else f"{remaining:05.1f}s",
                  1190, 184, 104, 20, 11, WHITE, True, Qt.AlignCenter)

    def draw_alert(self, p):
        if not self.event:
            return
        dur = float(self.event.get("duration", 4))
        elapsed = time.monotonic() - self.event_start
        if elapsed >= dur:
            self.event = None
            return

        intro = min(1, elapsed / .28)
        outro = max(0, (elapsed - (dur - .4)) / .4)
        alpha = int(255 * intro * (1 - outro))
        bounce = math.sin(min(1, elapsed / .4) * math.pi) * 7

        w, h = 510, 102
        x, y = 542, 168 + (1 - intro) * -35 + bounce
        kind = self.event.get("kind", "")
        if kind == "subscriber":
            border = QColor(198, 55, 37, alpha); fill = QColor(250, 244, 226, alpha); title = QColor(183, 48, 37, alpha)
        elif kind == "gift_sub":
            border = QColor(224, 157, 26, alpha); fill = QColor(250, 244, 226, alpha); title = QColor(154, 97, 15, alpha)
        else:
            border = QColor(198, 55, 37, alpha); fill = QColor(250, 244, 226, alpha); title = QColor(183, 48, 37, alpha)

        self.rounded(p, x, y, w, h, fill, border, 8, 3)
        self.pokeball(p, x + 56, y + 51, 26)
        self.text(p, self.event.get("title", ""), x + 104, y + 10, w - 118, 26, 14, title, True)
        self.text(p, self.event.get("subtitle", ""), x + 104, y + 36, w - 118, 30, 9, QColor(25, 25, 25, alpha), True)
        extra = self.event.get("extra", {})
        if kind == "subscriber":
            kicker = "Votes now count x2!"
        elif extra.get("effect"):
            kicker = "WORLD EVENT - " + extra["effect"].replace("_", " ").upper()
        else:
            kicker = "TRAINER EVENT"
        self.text(p, kicker, x + 104, y + 72, w - 118, 18, 9, title, True)

    def draw_dialogue(self, p):
        # intentionally disabled; user chose not to keep Professor Oak / NPC box
        return

    def draw_boot(self, p):
        if not self.boot or self.boot.get("done"):
            return
        g = OV["game_rect"]
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(9, 12, 13, 235))
        p.drawRoundedRect(QRectF(g["x"], g["y"], g["width"], g["height"]), 7, 7)
        self.screen_text(p, "TWITCH PLAYS POKEMON", g["x"], g["y"] + 230, g["width"], 52, 22, CREAM, True, Qt.AlignCenter)
        self.screen_text(p, self.boot.get("step", ""), g["x"], g["y"] + 300, g["width"], 34, 14, GOLD, True, Qt.AlignCenter)
        self.screen_text(p, self.boot.get("detail", ""), g["x"], g["y"] + 340, g["width"], 26, 9, MUTED, False, Qt.AlignCenter)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPixmap(0, 0, self.frame)

        self.clear_live_values(p)
        self.draw_votes(p)
        self.draw_chat(p)
        self.draw_bottom(p)
        self.draw_active_effects(p)
        self.draw_alert(p)
        self.draw_dialogue(p)
        self.draw_boot(p)

def main():
    app = QApplication(sys.argv)
    w = Overlay()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
