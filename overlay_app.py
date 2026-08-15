#!/usr/bin/env python3
import json, math, re, sys, time, urllib.request
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
ALERT_DIR = BASE / "assets" / "ui" / "alerts"
EMOTE_DIR = BASE / "assets" / "cache" / "twitch_emotes"

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
ALERT_CARD_EFFECTS = {
    "double_votes",
    "speed_round",
    "chaos",
    "anarchy",
    "reverse_controls",
    "king_mode",
}

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
        self.alert_cards = self.load_alert_cards()
        self.emotes = {}
        EMOTE_DIR.mkdir(parents=True, exist_ok=True)

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

    def load_alert_cards(self):
        cards = {}
        if not ALERT_DIR.exists():
            return cards
        for path in ALERT_DIR.glob("*.png"):
            pix = QPixmap(str(path))
            if not pix.isNull():
                cards[path.stem] = pix
        return cards

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

    def screen_elided(self, p, text, width, size=12, bold=False):
        p.setFont(self.screen_font(size, bold))
        return p.fontMetrics().elidedText(str(text), Qt.ElideRight, max(1, int(width)))

    def chat_emote(self, provider, emote_id, url=None):
        provider = re.sub(r"[^a-z0-9_-]", "_", str(provider or "emote").lower())
        emote_id = str(emote_id)
        if not emote_id:
            return None
        key = f"{provider}_{re.sub(r'[^A-Za-z0-9_-]', '_', emote_id)}"
        if key in self.emotes:
            return self.emotes[key]

        path = EMOTE_DIR / f"{key}.bin"
        if not path.exists():
            if not url:
                url = f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/dark/2.0"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "PokemonTwitchChat/1.0"})
                data = urllib.request.urlopen(req, timeout=1.5).read()
                path.write_bytes(data)
            except Exception:
                self.emotes[key] = None
                return None

        pix = QPixmap()
        try:
            ok = pix.loadFromData(path.read_bytes())
        except Exception:
            ok = False
        self.emotes[key] = pix if ok and not pix.isNull() else None
        return self.emotes[key]

    def chat_segments(self, message, emotes):
        message = str(message)
        if not isinstance(emotes, list):
            emotes = []
        segments = []
        cursor = 0
        for emote in sorted(emotes, key=lambda item: int(item.get("start", 0)) if isinstance(item, dict) else 0):
            try:
                start = int(emote.get("start"))
                end = int(emote.get("end"))
            except (AttributeError, TypeError, ValueError):
                continue
            if start < cursor or start < 0 or end < start:
                continue
            if start > cursor:
                segments.append({"type": "text", "text": message[cursor:start]})
            segments.append({"type": "emote", "id": emote.get("id"), "text": message[start:end + 1]})
            cursor = end + 1
        if cursor < len(message):
            segments.append({"type": "text", "text": message[cursor:]})
        return segments or [{"type": "text", "text": message}]

    def text_tokens(self, text):
        return [part for part in re.findall(r"\S+\s*|\s+", str(text)) if part]

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
        p.drawRect(QRectF(1548, 637, 362, 292))
        p.setBrush(QColor("#D69A3B"))
        p.drawRoundedRect(QRectF(1882, 651, 13, 250), 6, 6)
        p.setBrush(QColor("#A26514"))
        arrow = QPolygonF([
            QPointF(1888.5, 915),
            QPointF(1880.5, 904),
            QPointF(1896.5, 904),
        ])
        p.drawPolygon(arrow)
        p.setBrush(QColor("#E09C14"))
        p.drawRect(QRectF(1548, 927, 362, 2))
        p.drawRect(QRectF(1548, 637, 2, 292))
        p.drawRect(QRectF(1908, 637, 2, 292))
        p.setBrush(QColor("#B42B1F"))
        p.drawRect(QRectF(1548, 924, 362, 2))

    def draw_votes(self, p):
        rows = self.state.get("votes", [])[:5]
        progress = max(0.0, min(1.0, float(self.state.get("round_progress", 0.0))))

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

        self.screen_rounded(p, 1588, 224, 274, 14, QColor("#321913"), QColor("#8E261B"), 4, 1)
        if progress > 0:
            self.screen_rounded(p, 1589, 225, max(4, 272 * progress), 12, GOLD, GOLD, 3, 0)

    def draw_chat_legacy(self, p):
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

    def draw_chat(self, p):
        x, y, w, bottom = 1558, 648, 306, 916
        line_h = 19
        emote_size = 18
        gap = 4
        rows = list(reversed(self.state.get("recent_chat", [])))
        if not rows:
            rows = [
                {"username": row.get("username", ""), "message": row.get("command", ""), "subscriber": row.get("subscriber", False)}
                for row in self.state.get("recent_commands", [])
            ]
            rows = list(reversed(rows))
        palette = [
            QColor("#EF4B2F"), QColor("#E9AA17"), QColor("#45B73E"), QColor("#3DC5D9"),
            QColor("#A65ACC"), QColor("#F39E21"), QColor("#38B9D5"), QColor("#EF86B0")
        ]
        if not rows:
            self.screen_text(p, "No chat yet", x, y + 92, w, 22, 14, QColor("#6E7777"), False, Qt.AlignCenter)
            return

        yy = y
        for i, row in enumerate(rows):
            if yy + line_h > bottom:
                break
            name = str(row.get("username", ""))[:14]
            sub = bool(row.get("subscriber"))
            display = ("SUB " if sub else "") + name + ":"
            col = GOLD if sub else palette[sum(ord(ch) for ch in name) % len(palette)]
            label = self.screen_elided(p, display, 118, 12, sub)
            label_w, _ = self.screen_text_size(p, label, 12, sub)
            msg_start_x = x + label_w + 6
            cursor_x = msg_start_x
            max_x = x + w

            self.screen_text(p, label, x, yy, label_w + 2, line_h, 12, col, sub)

            for segment in self.chat_segments(row.get("message", row.get("command", "")), row.get("emotes", [])):
                if segment["type"] == "emote":
                    token_w = emote_size + gap
                    if cursor_x + token_w > max_x:
                        yy += line_h
                        cursor_x = x
                        if yy + line_h > bottom:
                            break
                    pix = self.chat_emote(segment.get("provider"), segment.get("id"), segment.get("url"))
                    if pix:
                        p.drawPixmap(QRectF(cursor_x, yy + 1, emote_size, emote_size), pix, QRectF(0, 0, pix.width(), pix.height()))
                    else:
                        fallback = self.screen_elided(p, segment.get("text", ""), max_x - cursor_x, 12, False)
                        self.screen_text(p, fallback, cursor_x, yy, max_x - cursor_x, line_h, 12, WHITE, False)
                    cursor_x += token_w
                    continue

                for token in self.text_tokens(segment.get("text", "")):
                    token_w, _ = self.screen_text_size(p, token, 12, False)
                    if cursor_x + token_w > max_x and token.strip():
                        yy += line_h
                        cursor_x = x
                        if yy + line_h > bottom:
                            break
                        token = token.lstrip()
                        token_w, _ = self.screen_text_size(p, token, 12, False)
                    if yy + line_h > bottom:
                        break
                    if token_w > max_x - cursor_x:
                        token = self.screen_elided(p, token, max_x - cursor_x, 12, False)
                        token_w, _ = self.screen_text_size(p, token, 12, False)
                    self.screen_text(p, token, cursor_x, yy, token_w + 2, line_h, 12, WHITE, False)
                    cursor_x += token_w

                if yy + line_h > bottom:
                    break

            yy += line_h + 3

    def draw_bottom(self, p):
        st = OV.get("status", {})
        loc = self.state.get("location", st.get("location", "Pallet Town"))
        badges = int(self.state.get("badges", st.get("badges", 2)))
        party = int(self.state.get("party_size", st.get("party_size", 1)))
        party_fainted = self.state.get("party_fainted", [])
        party_species = self.state.get("party_species", [])
        deaths = int(self.state.get("deaths", st.get("deaths", 0)))
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
        total_trainers = int(self.state.get("unique_players", 0))
        total_rounds = int(self.state.get("total_rounds", 0))
        self.screen_text(p, f"TOP: {top_name} Lv.{top_lvl}", 18, 878, 285, 24, 15, WHITE, True, Qt.AlignCenter)
        self.screen_text(p, f"TRAINERS: {total_trainers:,}   ROUNDS: {total_rounds:,}", 18, 908, 285, 24, 14, WHITE, True, Qt.AlignCenter)

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
        text = str(max(0, int(deaths)))
        font_size = 30
        skull_size = 48
        gap = 10
        max_group_w = body[2] - body[0] - 12
        text_w, text_h = self.screen_text_size(p, text, font_size, True)
        while skull_size + gap + text_w > max_group_w and font_size > 18:
            font_size -= 1
            text_w, text_h = self.screen_text_size(p, text, font_size, True)
        while skull_size + gap + text_w > max_group_w and skull_size > 36:
            skull_size -= 2
            text_w, text_h = self.screen_text_size(p, text, font_size, True)
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

    def ease_out_back(self, t):
        t = max(0.0, min(1.0, float(t))) - 1
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * t * t * t + c1 * t * t

    def draw_effect_card_alert(self, p, pix, effect, elapsed, dur, intro, outro, alpha):
        base_w, base_h = 520, 362
        pop = self.ease_out_back(elapsed / .42)
        pulse_rate = 3.8 if effect in ("chaos", "anarchy") else 2.2
        pulse = 1 + math.sin(elapsed * math.pi * pulse_rate) * .012
        scale = (0.84 + .16 * pop) * pulse * (1 - .04 * outro)
        w, h = base_w * scale, base_h * scale
        shake = 0
        if effect == "chaos":
            shake = math.sin(elapsed * 42) * 5 + math.sin(elapsed * 21) * 2
        elif effect == "anarchy":
            shake = math.sin(elapsed * 34) * 3
        x = (SRC_W - w) / 2
        y = 132 + (1 - intro) * -42 + math.sin(elapsed * 3.5) * 2 + shake
        if outro:
            y -= 24 * outro
        target = QRectF(self.tx(x), self.ty(y), self.tw(w), self.th(h))

        p.save()
        p.setOpacity(max(0.0, min(1.0, alpha / 255)))
        glow = {
            "double_votes": QColor(255, 208, 62, 44),
            "speed_round": QColor(68, 176, 255, 50),
            "chaos": QColor(202, 38, 30, 54),
            "anarchy": QColor(255, 83, 18, 52),
            "reverse_controls": QColor(150, 98, 235, 48),
            "king_mode": QColor(255, 191, 38, 52),
        }.get(effect, QColor(255, 83, 18, 42))
        self.rounded(p, x - 10, y + 12, w + 20, h - 8, glow, QColor(255, 167, 32, 80), 10, 1)
        p.drawPixmap(target, pix, QRectF(0, 0, pix.width(), pix.height()))

        p.setClipRect(target)
        shimmer_alpha = int(72 * (alpha / 255) * (.75 + .25 * math.sin(elapsed * 5)))
        shimmer_speed = 420 if effect == "speed_round" else 260 if effect == "reverse_controls" else 220
        shimmer_x = x - 180 + ((elapsed * shimmer_speed) % (w + 360))
        shimmer_color = {
            "speed_round": QColor(170, 230, 255, shimmer_alpha),
            "reverse_controls": QColor(210, 180, 255, shimmer_alpha),
            "chaos": QColor(255, 92, 52, shimmer_alpha),
        }.get(effect, QColor(255, 236, 124, shimmer_alpha))
        band = QPolygonF([
            QPointF(self.tx(shimmer_x), self.ty(y)),
            QPointF(self.tx(shimmer_x + 58), self.ty(y)),
            QPointF(self.tx(shimmer_x + 184), self.ty(y + h)),
            QPointF(self.tx(shimmer_x + 126), self.ty(y + h)),
        ])
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(shimmer_color))
        p.drawPolygon(band)

        if effect == "speed_round":
            p.setPen(QPen(QColor(210, 240, 255, int(alpha * .55)), self.tw(2)))
            for i in range(9):
                yy = y + 82 + i * 19 + math.sin(elapsed * 4 + i) * 5
                xx = x + ((elapsed * 520 + i * 83) % (w + 180)) - 160
                p.drawLine(QPointF(self.tx(xx), self.ty(yy)), QPointF(self.tx(xx + 130), self.ty(yy - 8)))
            p.setPen(Qt.NoPen)

        particle_count = 18 if effect in ("king_mode", "anarchy", "chaos") else 12
        for i in range(particle_count):
            phase = (elapsed * (.28 + i * .017) + i * .137) % 1
            sx = x + 36 + ((i * 37) % max(1, int(w - 72)))
            sy = y + 58 + phase * 168
            drift = math.sin(elapsed * 2.6 + i) * 9
            size = 1.6 + (i % 4) * .45
            if effect == "reverse_controls":
                color = QColor(172, 126 + (i % 3) * 30, 255, int(alpha * (1 - phase) * .72))
            elif effect == "speed_round":
                color = QColor(160, 225, 255, int(alpha * (1 - phase) * .72))
            elif effect == "double_votes":
                color = QColor(255, 220 + (i % 2) * 20, 68, int(alpha * (1 - phase) * .76))
            else:
                color = QColor(255, 186 + (i % 3) * 20, 48, int(alpha * (1 - phase) * .82))
            p.setBrush(QBrush(color))
            p.drawEllipse(QPointF(self.tx(sx + drift), self.ty(sy)), self.tw(size), self.th(size))
        p.restore()

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

        extra = self.event.get("extra", {})
        effect = extra.get("effect")
        if effect in ALERT_CARD_EFFECTS:
            pix = self.alert_cards.get(f"{effect}_card")
            if pix:
                self.draw_effect_card_alert(p, pix, effect, elapsed, dur, intro, outro, alpha)
                return

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
