#!/usr/bin/env python3
import json
import sys
import time
from pathlib import Path
from sound_engine import SoundEngine

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
EVENT_PATH = BASE / CFG["overlay"]["event_file"]
STATE_PATH = BASE / CFG["overlay"]["state_file"]
PREVIEW_PATH = BASE / CFG["overlay"].get("effect_preview_file", "overlay_effect_preview.json")
STREAM = CFG.get("stream_system", {})
SOUND = SoundEngine(BASE / "assets" / "sounds", STREAM.get("sound_enabled", True), STREAM.get("sound_volume", 0.35))
EFFECT_DURATIONS = {
    rule["effect"]: float(rule.get("duration_seconds", 60))
    for rule in CFG.get("events", {}).get("cheer_effects", [])
}
EFFECT_SOUNDS = {
    "double_votes": "double_votes.wav",
    "speed_round": "speed_round.wav",
    "chaos": "chaos.wav",
    "reverse_controls": "reverse_controls.wav",
    "king_mode": "gym_win.wav",
}
KIND_SOUNDS = {
    "subscriber": "subscriber.wav",
    "gift_sub": "gift_sub.wav",
    "resub": "subscriber.wav",
}


def send(kind, title, subtitle, extra=None, duration=5):
    extra = extra or {}
    if kind == "world_event" and extra.get("effect"):
        extra.setdefault("user", "TestTrainer")
        extra.setdefault("source", extra["user"])
        extra.setdefault("amount", extra.get("bits", 0))
    payload = {
        "id": time.time_ns(),
        "kind": kind,
        "title": title,
        "subtitle": subtitle,
        "extra": extra,
        "duration": duration,
        "created_at": time.time(),
    }
    tmp = EVENT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(EVENT_PATH)
    if kind == "world_event" and extra.get("effect"):
        preview_effect(extra["effect"], EFFECT_DURATIONS.get(extra["effect"], 60))
    sound = EFFECT_SOUNDS.get(extra.get("effect")) or KIND_SOUNDS.get(kind)
    if sound:
        SOUND.play(sound)
    print("Sent:", title, extra or "")


def read_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_state(state):
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(STATE_PATH)


def read_preview():
    try:
        data = json.loads(PREVIEW_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("active_effects", [])
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def write_preview(active):
    payload = {"active_effects": active}
    tmp = PREVIEW_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.replace(PREVIEW_PATH)


def preview_effect(effect, duration):
    now = time.time()
    active = []
    for item in read_preview():
        item_effect = item.get("effect")
        if item_effect == effect:
            continue
        expires_at = item.get("expires_at")
        if expires_at is not None:
            try:
                if float(expires_at) <= now:
                    continue
            except (TypeError, ValueError):
                continue
        active.append(item)
    active.append({
        "effect": effect,
        "remaining": duration,
        "expires_at": now + duration,
        "source": "TestTrainer",
        "amount": 0,
    })
    write_preview(active)


def clear_effects():
    state = read_state()
    if "active_effects" in state:
        state["active_effects"] = []
        write_state(state)
    write_preview([])
    print("Cleared active effect previews")


MENU = {
    "1": ("subscriber", "NEW TRAINER JOINED!", "TestTrainer subscribed - votes count x2", {}, 5),
    "2": ("gift_sub", "A POKE BALL WAS GIFTED!", "TestTrainer gifted a sub to LuckyViewer", {"recipient": "LuckyViewer"}, 6),
    "3": ("resub", "WELCOME BACK!", "TestTrainer resubscribed for 6 months", {"months": 6}, 5),
    "4": ("world_event", "DOUBLE VOTES", "TestTrainer used 100 Bits - DOUBLE VOTES for 30s", {"bits": 100, "effect": "double_votes"}, 5),
    "5": ("world_event", "SPEED ROUND", "TestTrainer used 500 Bits - SPEED ROUND for 60s", {"bits": 500, "effect": "speed_round"}, 5),
    "6": ("world_event", "CHAOS MODE", "TestTrainer used 1,000 Bits - CHAOS MODE for 60s", {"bits": 1000, "effect": "chaos"}, 5),
    "7": ("world_event", "REVERSE CONTROLS", "TestTrainer used 2,000 Bits - REVERSE CONTROLS for 60s", {"bits": 2000, "effect": "reverse_controls"}, 5),
    "8": ("world_event", "KING MODE", "TestTrainer used 5,000 Bits - KING MODE for 60s", {"bits": 5000, "effect": "king_mode"}, 5),
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
    "reverse": "7",
    "reverse_controls": "7",
    "king": "8",
    "king_mode": "8",
}


def play_all():
    for key in ("1", "2", "3", "4", "5", "6", "7", "8"):
        send(*MENU[key])
        time.sleep(5.7)


def send_arg(arg):
    arg = arg.strip().lower()
    if arg in ("all", "cycle"):
        play_all()
    elif arg in ("clear", "clear_effects", "none"):
        clear_effects()
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
    print("\n1 Sub  2 Gift  3 Resub  4 Double  5 Speed  6 Chaos  7 Reverse  8 King  a All  c Clear  q Quit")
    choice = input("> ").strip().lower()
    if choice == "q":
        break
    if choice == "c":
        clear_effects()
        continue
    if choice == "a":
        play_all()
    elif choice in MENU:
        send(*MENU[choice])
