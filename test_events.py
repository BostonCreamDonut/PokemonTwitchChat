#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
EVENT_PATH = BASE / CFG["overlay"]["event_file"]


def send(kind, title, subtitle, extra=None, duration=5):
    payload = {
        "id": time.time_ns(),
        "kind": kind,
        "title": title,
        "subtitle": subtitle,
        "extra": extra or {},
        "duration": duration,
        "created_at": time.time(),
    }
    tmp = EVENT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(EVENT_PATH)
    print("Sent:", title, extra or "")


MENU = {
    "1": ("subscriber", "NEW TRAINER JOINED!", "TestTrainer subscribed - votes count x2", {}, 5),
    "2": ("gift_sub", "A POKE BALL WAS GIFTED!", "TestTrainer gifted a sub to LuckyViewer", {"recipient": "LuckyViewer"}, 6),
    "3": ("resub", "WELCOME BACK!", "TestTrainer resubscribed for 6 months", {"months": 6}, 5),
    "4": ("world_event", "DOUBLE VOTES", "TestTrainer used 100 Bits - DOUBLE VOTES for 30s", {"bits": 100, "effect": "double_votes"}, 5),
    "5": ("world_event", "SPEED ROUND", "TestTrainer used 500 Bits - SPEED ROUND for 60s", {"bits": 500, "effect": "speed_round"}, 5),
    "6": ("world_event", "CHAOS MODE", "TestTrainer used 1,000 Bits - CHAOS MODE for 60s", {"bits": 1000, "effect": "chaos"}, 5),
    "7": ("world_event", "ANARCHY MODE", "TestTrainer used 1,500 Bits - ANARCHY MODE for 60s", {"bits": 1500, "effect": "anarchy"}, 5),
    "8": ("world_event", "REVERSE CONTROLS", "TestTrainer used 2,000 Bits - REVERSE CONTROLS for 60s", {"bits": 2000, "effect": "reverse_controls"}, 5),
    "9": ("world_event", "KING MODE", "TestTrainer used 5,000 Bits - KING MODE for 60s", {"bits": 5000, "effect": "king_mode"}, 5),
}

ALIASES = {
    "sub": "1",
    "gift": "2",
    "gift_sub": "2",
    "resub": "3",
    "double": "4",
    "double_votes": "4",
    "speed": "5",
    "speed_round": "5",
    "chaos": "6",
    "anarchy": "7",
    "reverse": "8",
    "reverse_controls": "8",
    "king": "9",
    "king_mode": "9",
}


def play_all():
    for key in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
        send(*MENU[key])
        time.sleep(5.7)


def send_arg(arg):
    arg = arg.strip().lower()
    if arg in ("all", "cycle"):
        play_all()
    elif arg in MENU:
        send(*MENU[arg])
    elif arg in ALIASES:
        send(*MENU[ALIASES[arg]])
    else:
        raise SystemExit(f"Unknown test event: {arg}")


if len(sys.argv) > 1:
    send_arg(sys.argv[1])
    raise SystemExit

while True:
    print("\n1 Sub  2 Gift  3 Resub  4 Double  5 Speed  6 Chaos  7 Anarchy  8 Reverse  9 King  a All  q Quit")
    choice = input("> ").strip().lower()
    if choice == "q":
        break
    if choice == "a":
        play_all()
    elif choice in MENU:
        send(*MENU[choice])
