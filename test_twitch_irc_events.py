#!/usr/bin/env python3
import argparse
import json
import sys
import time
from pathlib import Path

import main as app_main
from twitch_irc import TwitchIRCClient

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
PREVIEW_PATH = BASE / CFG["overlay"].get("effect_preview_file", "overlay_effect_preview.json")

EFFECT_BITS = {
    "speed": 250,
    "speed_round": 250,
    "chaos": 500,
    "reverse": 1000,
    "reverse_controls": 1000,
    "king": 2000,
    "king_mode": 2000,
}


def write_preview(app):
    now = time.time()
    active = []
    for item in app.active_effects():
        remaining = float(item.get("remaining", 0))
        if remaining <= 0:
            continue
        copied = dict(item)
        copied["expires_at"] = now + remaining
        active.append(copied)
    tmp = PREVIEW_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({"active_effects": active}), encoding="utf-8")
    tmp.replace(PREVIEW_PATH)


def tag_string(tags):
    return ";".join(f"{key}={value}" for key, value in tags.items())


def fake_app(no_sound=False):
    # Avoid network emote fetches; this test is about Twitch IRC event tags.
    app_main.App.start_third_party_emote_load = lambda self, room_id=None: None
    app = app_main.App("offline-test-token")
    app.sound.enabled = not no_sound
    app.chat.connected = True
    return app


def dispatch_privmsg(app, line):
    tags, payload = TwitchIRCClient._split(line)
    prefix, rest = payload.split(" PRIVMSG ", 1)
    user = prefix.lstrip(":").split("!", 1)[0]
    _, msg = rest.split(" :", 1)
    app.on_message(user, msg, tags)
    return tags


def dispatch_usernotice(app, line):
    tags, _payload = TwitchIRCClient._split(line)
    app.on_notice(tags)
    return tags


def simulate_bits(app, bits, user):
    channel = CFG["twitch"]["channel"].lower()
    login = user.lower()
    msg = f"cheer{bits} no-money IRC tag test"
    tags = {
        "badge-info": "",
        "badges": "",
        "bits": str(bits),
        "color": "#F5C13D",
        "display-name": user,
        "emotes": "",
        "mod": "0",
        "room-id": "123456",
        "subscriber": "0",
        "tmi-sent-ts": str(int(time.time() * 1000)),
    }
    line = f"@{tag_string(tags)} :{login}!{login}@{login}.tmi.twitch.tv PRIVMSG #{channel} :{msg}"
    parsed = dispatch_privmsg(app, line)
    write_preview(app)
    print(f"Simulated Twitch IRC PRIVMSG with bits={parsed.get('bits')} from {user}")


def simulate_notice(app, kind, user):
    channel = CFG["twitch"]["channel"].lower()
    login = user.lower()
    tags = {
        "badge-info": "subscriber/6",
        "badges": "subscriber/6",
        "color": "#55A936",
        "display-name": user,
        "emotes": "",
        "mod": "0",
        "room-id": "123456",
        "subscriber": "1",
        "tmi-sent-ts": str(int(time.time() * 1000)),
    }
    message = ""
    if kind == "sub":
        tags.update({
            "msg-id": "sub",
            "msg-param-cumulative-months": "1",
        })
        message = f"{user} subscribed!"
    elif kind == "resub":
        tags.update({
            "msg-id": "resub",
            "msg-param-cumulative-months": "6",
        })
        message = f"{user} resubscribed for 6 months!"
    elif kind == "gift":
        tags.update({
            "msg-id": "subgift",
            "msg-param-recipient-display-name": "LuckyViewer",
        })
        message = f"{user} gifted a sub to LuckyViewer!"
    elif kind == "mysterygift":
        tags.update({
            "msg-id": "submysterygift",
            "msg-param-mass-gift-count": "5",
        })
        message = f"{user} gifted 5 subs!"
    else:
        raise SystemExit(f"Unknown USERNOTICE kind: {kind}")

    line = f"@{tag_string(tags)} :{login}!{login}@{login}.tmi.twitch.tv USERNOTICE #{channel} :{message}"
    parsed = dispatch_usernotice(app, line)
    print(f"Simulated Twitch IRC USERNOTICE msg-id={parsed.get('msg-id')} from {user}")


def clear_preview():
    tmp = PREVIEW_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps({"active_effects": []}), encoding="utf-8")
    tmp.replace(PREVIEW_PATH)
    print("Cleared simulated active effect preview")


def main():
    parser = argparse.ArgumentParser(
        description="No-money Twitch IRC event test. Uses fake IRC tags, then calls the real app callbacks."
    )
    parser.add_argument("event", help="speed, chaos, reverse, king, bits, sub, resub, gift, mysterygift, all, clear")
    parser.add_argument("amount", nargs="?", type=int, help="Bit amount when event is 'bits'")
    parser.add_argument("--user", default="TestTrainer", help="Display name to put in fake Twitch tags")
    parser.add_argument("--no-sound", action="store_true", help="Do not play alert sounds")
    args = parser.parse_args()

    event = args.event.lower()
    if event == "clear":
        clear_preview()
        return

    app = fake_app(no_sound=args.no_sound)
    if event == "all":
        for name in ("speed", "chaos", "reverse", "king", "sub", "gift", "resub"):
            if name in EFFECT_BITS:
                simulate_bits(app, EFFECT_BITS[name], args.user)
            else:
                simulate_notice(app, name, args.user)
            time.sleep(1.0)
        return

    if event == "bits":
        if args.amount is None:
            raise SystemExit("Usage: python test_twitch_irc_events.py bits 500")
        simulate_bits(app, args.amount, args.user)
    elif event in EFFECT_BITS:
        simulate_bits(app, EFFECT_BITS[event], args.user)
    elif event in {"sub", "resub", "gift", "mysterygift"}:
        simulate_notice(app, event, args.user)
    else:
        raise SystemExit(f"Unknown event: {event}")


if __name__ == "__main__":
    try:
        main()
    finally:
        app_main.STOP.set()
