#!/usr/bin/env python3
import json, math, sys, time
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
OV = CFG["overlay"]

STATE = BASE / OV["state_file"]
EVENTS = BASE / OV["event_file"]
BOOT = BASE / OV.get("boot_file", "boot_state.json")
DIALOGUE = BASE / OV.get("dialogue_file", "dialogue_state.json")
FRAME = BASE / OV["reference_frame"]

SRC_W = float(OV.get("source_width", 1672))
SRC_H = float(OV.get("source_height", 941))
SX = float(OV.get("scale_x", 1.0))
SY = float(OV.get("scale_y", 1.0))

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

        self.setWindowTitle("Twitch Plays Pokemon Overlay")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.resize(int(OV.get("screen_width", 1920)), int(OV.get("screen_height", 1080)))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(max(20, int(1000 / int(OV.get("refresh_hz", 30)))))

    def tx(self, x): return x * SX
    def ty(self, y): return y * SY
    def tw(self, w): return w * SX
    def th(self, h): return h * SY

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
        f = QFont("DejaVu Sans Condensed", max(1, int(round(size * ((SX + SY) / 2)))))
        f.setBold(bold)
        return f

    def text(self, p, t, x, y, w, h, size=12, color=INK, bold=False, align=Qt.AlignLeft | Qt.AlignVCenter):
        p.setFont(self.font(size, bold))
        p.setPen(color)
        p.drawText(QRectF(self.tx(x), self.ty(y), self.tw(w), self.th(h)), align, str(t))

    def rounded(self, p, x, y, w, h, fill, border=RED, r=6, bw=2):
        p.setPen(QPen(border, max(1, bw * ((SX + SY) / 2))))
        p.setBrush(QBrush(fill))
        p.drawRoundedRect(QRectF(self.tx(x), self.ty(y), self.tw(w), self.th(h)), r * SX, r * SY)

    def ellipse(self, p, cx, cy, rx, ry=None, pen=None, brush=None):
        if ry is None:
            ry = rx
        if pen is not None:
            p.setPen(pen)
        if brush is not None:
            p.setBrush(brush)
        p.drawEllipse(QPointF(self.tx(cx), self.ty(cy)), self.tw(rx), self.th(ry))

    def pokeball(self, p, cx, cy, r):
        penw = max(1, int(round(r * 0.08 * ((SX + SY) / 2))))
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
        p.drawRect(QRectF(self.tx(1327), self.ty(183), self.tw(296), self.th(319)))

        # Live Chat body
        p.setBrush(DARK)
        p.drawRect(QRectF(self.tx(1327), self.ty(537), self.tw(296), self.th(266)))

        # Bottom HUD bodies (keep headers visible)
        p.setBrush(CREAM2)
        p.drawRect(QRectF(self.tx(6), self.ty(817), self.tw(265), self.th(74)))      # location
        p.drawRect(QRectF(self.tx(275), self.ty(817), self.tw(338), self.th(74)))    # badges
        p.drawRect(QRectF(self.tx(617), self.ty(817), self.tw(308), self.th(74)))    # party
        p.drawRect(QRectF(self.tx(929), self.ty(817), self.tw(126), self.th(74)))    # deaths
        p.drawRect(QRectF(self.tx(1061), self.ty(817), self.tw(252), self.th(74)))   # objective

        # Footer strip
        p.setBrush(FOOTER)
        p.drawRect(QRectF(self.tx(6), self.ty(904), self.tw(1608), self.th(31)))

    def draw_votes(self, p):
        rows = self.state.get("votes", [])[:5]
        rem = float(self.state.get("time_remaining", 3.0))

        yy = 205
        if not rows:
            self.text(p, "Waiting for votes…", 1340, 240, 230, 22, 10, QColor("#68645D"))

        for i, row in enumerate(rows):
            pct = float(row.get("percent", 0))
            wt = int(row.get("weighted_votes", 0))
            cmd = LABELS.get(row.get("command"), row.get("command", "")).upper()
            col = VOTE_COLORS[i % len(VOTE_COLORS)]

            self.rounded(p, 1340, yy, 28, 28, col, QColor("#222"), 4, 2)
            sym = {"UP":"↑","DOWN":"↓","LEFT":"←","RIGHT":"→"}.get(cmd, cmd[:1])
            self.text(p, sym, 1340, yy, 28, 28, 14, WHITE, True, Qt.AlignCenter)
            self.text(p, cmd, 1380, yy, 65, 28, 10, INK, True)

            bx, by, bw, bh = 1450, yy + 5, 78, 16
            self.rounded(p, bx, by, bw, bh, QColor("#E3D8C2"), QColor("#C7B99F"), 3, 1)
            if pct > 0:
                self.rounded(p, bx, by, max(3, bw * pct / 100), bh, col, col, 3, 0)

            self.text(p, f"{pct:.0f}%", 1545, yy-1, 55, 16, 10, INK, True, Qt.AlignRight | Qt.AlignVCenter)
            self.text(p, f"({wt})", 1545, yy+13, 55, 14, 8, INK, True, Qt.AlignRight | Qt.AlignVCenter)
            yy += 54

        self.text(p, f"Total Weighted Votes: {int(self.state.get('round_weighted_vote_count', 0))}",
                  1352, 462, 235, 22, 9, INK, True, Qt.AlignCenter)

        self.rounded(p, 1480, 167, 46, 21, QColor("#B53022"), QColor("#8E261B"), 4, 1)
        self.text(p, f"{rem:.1f}s", 1481, 167, 44, 21, 8, WHITE, True, Qt.AlignCenter)

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
        deaths = int(self.state.get("deaths", st.get("deaths", 3)))
        objective = self.state.get("objective", st.get("objective", "Defeat Brock\nin Pewter City"))

        # Location
        self.text(p, "🏠", 18, 840, 36, 40, 16, WHITE, False, Qt.AlignCenter)
        self.text(p, loc, 54, 835, 190, 45, 13, INK, True)

        # Badges
        badge_xs = [285, 331, 377, 423, 469, 515]
        for i, bx in enumerate(badge_xs):
            filled = i < badges
            if filled:
                # Alternate silver/blue for first two sample badges, then brown filled tokens
                fill = QColor("#B6B6B6") if i == 0 else (QColor("#4AB1E8") if i == 1 else QColor("#6B5138"))
                outline = QColor("#5E4934")
            else:
                fill = QColor("#5B4633")
                outline = QColor("#463628")
            p.setPen(QPen(outline, max(1, int(round(2 * ((SX + SY) / 2))))))
            p.setBrush(fill)
            self.ellipse(p, bx, 853, 15)

        # Party
        for i in range(6):
            cx = 648 + i * 44
            if i < party:
                self.pokeball(p, cx, 853, 14)
            else:
                p.setPen(QPen(QColor("#423B32"), max(1, int(round(2 * ((SX + SY) / 2))))))
                p.setBrush(QColor("#3D2E21"))
                self.ellipse(p, cx, 853, 14)

        # Deaths
        self.text(p, "☠", 950, 838, 32, 38, 16, INK, True, Qt.AlignCenter)
        self.text(p, deaths, 990, 836, 40, 40, 18, INK, True, Qt.AlignLeft | Qt.AlignVCenter)

        # Objective
        self.text(p, "⚑", 1080, 835, 34, 40, 18, RED, True, Qt.AlignCenter)
        self.text(p, objective, 1120, 830, 170, 48, 11, INK, True)

        # Footer
        top = self.state.get("top_trainers", [])
        top_name = top[0]["username"] if top else "pikafan23"
        top_lvl = top[0]["level"] if top else 38
        total_trainers = int(self.state.get("unique_players", 1248))
        longest_streak = int(self.state.get("longest_streak", 27))
        gym_badges = int(st.get("gym_badges_earned", 2))

        self.text(p, f"🏆 TOP TRAINER: {top_name} (Lv. {top_lvl})", 18, 909, 350, 22, 8, WHITE, True)
        self.text(p, f"🔥 LONGEST STREAK: {longest_streak}", 390, 909, 240, 22, 8, WHITE, True)
        self.text(p, f"⭐ TOTAL TRAINERS: {total_trainers:,}", 680, 909, 265, 22, 8, WHITE, True)
        self.text(p, f"🔮 GYM BADGES EARNED: {gym_badges}", 1040, 909, 310, 22, 8, WHITE, True)
        self.text(p, "!trainer for your card", 1418, 909, 180, 22, 8, GOLD, True, Qt.AlignRight | Qt.AlignVCenter)

    def draw_active_effects(self, p):
        effects = self.state.get("active_effects", [])
        if not effects:
            return
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
            kicker = "Votes now count ×2!"
        elif extra.get("effect"):
            kicker = "WORLD EVENT • " + extra["effect"].replace("_", " ").upper()
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
        self.text(p, "TWITCH PLAYS POKÉMON", g["x"] / SX, g["y"] / SY + 200, g["width"] / SX, 44, 22, CREAM, True, Qt.AlignCenter)
        self.text(p, self.boot.get("step", ""), g["x"] / SX, g["y"] / SY + 260, g["width"] / SX, 28, 14, GOLD, True, Qt.AlignCenter)
        self.text(p, self.boot.get("detail", ""), g["x"] / SX, g["y"] / SY + 300, g["width"] / SX, 22, 9, MUTED, False, Qt.AlignCenter)

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

app = QApplication(sys.argv)
w = Overlay()
w.show()
sys.exit(app.exec_())
