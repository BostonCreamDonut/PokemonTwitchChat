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
    "3": ("world_event", "DOUBLE VOTES", "TestTrainer used 100 Bits - DOUBLE VOTES for 30s", {"bits": 100, "effect": "double_votes"}, 5),
    "4": ("world_event", "SPEED ROUND", "TestTrainer used 500 Bits - SPEED ROUND for 60s", {"bits": 500, "effect": "speed_round"}, 5),
    "5": ("world_event", "CHAOS MODE", "TestTrainer used 1,000 Bits - CHAOS MODE for 60s", {"bits": 1000, "effect": "chaos"}, 5),
    "6": ("world_event", "ANARCHY MODE", "TestTrainer used 1,500 Bits - ANARCHY MODE for 60s", {"bits": 1500, "effect": "anarchy"}, 5),
    "7": ("world_event", "REVERSE CONTROLS", "TestTrainer used 2,000 Bits - REVERSE CONTROLS for 60s", {"bits": 2000, "effect": "reverse_controls"}, 5),
    "8": ("world_event", "KING MODE", "TestTrainer used 5,000 Bits - KING MODE for 60s", {"bits": 5000, "effect": "king_mode"}, 5),
}

ALIASES = {
    "double": "3",
    "double_votes": "3",
    "speed": "4",
    "speed_round": "4",
    "chaos": "5",
    "anarchy": "6",
    "reverse": "7",
    "reverse_controls": "7",
    "king": "8",
    "king_mode": "8",
}


def play_all():
    for key in ("3", "4", "5", "6", "7", "8"):
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
    print("\n1 Sub  2 Gift Sub  3 Double  4 Speed  5 Chaos  6 Anarchy  7 Reverse  8 King  a All  q Quit")
    choice = input("> ").strip().lower()
    if choice == "q":
        break
    if choice == "a":
        play_all()
    elif choice in MENU:
        send(*MENU[choice])
