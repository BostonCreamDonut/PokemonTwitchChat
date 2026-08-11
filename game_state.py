#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent


def load_config():
    return json.loads((BASE / "config.json").read_text(encoding="utf-8"))


def state_path(cfg):
    return BASE / cfg["overlay"].get("game_state_file", "game_state.json")


def default_state(cfg):
    status = cfg["overlay"].get("status", {})
    return {
        "location": status.get("location", "Pallet Town"),
        "badges": int(status.get("badges", 0)),
        "party_size": int(status.get("party_size", 1)),
        "party_fainted": [],
        "party_species": [],
        "deaths": int(status.get("deaths", 0)),
        "objective": status.get("objective", "Start the adventure"),
    }


def clean_state(data, cfg):
    base = default_state(cfg)
    if isinstance(data, dict):
        base.update({k: v for k, v in data.items() if k in base})
    base["location"] = str(base["location"]).strip() or "Unknown"
    base["badges"] = max(0, min(8, int(base["badges"])))
    base["party_size"] = max(0, min(6, int(base["party_size"])))
    fainted = base.get("party_fainted", [])
    if not isinstance(fainted, list):
        fainted = []
    base["party_fainted"] = [bool(value) for value in fainted[:6]]
    species = base.get("party_species", [])
    if not isinstance(species, list):
        species = []
    clean_species = []
    for value in species[:6]:
        try:
            clean_species.append(max(0, int(value)))
        except (TypeError, ValueError):
            clean_species.append(0)
    base["party_species"] = clean_species
    base["deaths"] = max(0, int(base["deaths"]))
    base["objective"] = str(base["objective"]).replace("\\n", "\n").strip() or "Continue the adventure"
    return base


def read_state(cfg=None):
    cfg = cfg or load_config()
    path = state_path(cfg)
    if not path.exists():
        state = default_state(cfg)
        write_state(state, cfg)
        return state
    try:
        return clean_state(json.loads(path.read_text(encoding="utf-8")), cfg)
    except Exception:
        return default_state(cfg)


def write_state(state, cfg=None):
    cfg = cfg or load_config()
    path = state_path(cfg)
    path.parent.mkdir(exist_ok=True)
    clean = clean_state(state, cfg)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(json.dumps(clean, indent=2), encoding="utf-8")
    tmp.replace(path)
    return clean


def update_state(updates, cfg=None):
    cfg = cfg or load_config()
    state = read_state(cfg)
    state.update(updates)
    return write_state(state, cfg)


def parse_int(name, value):
    try:
        return int(value)
    except ValueError:
        raise SystemExit(f"{name} must be a number")


def usage():
    raise SystemExit(
        "Usage:\n"
        "  python game_state.py show\n"
        "  python game_state.py reset\n"
        "  python game_state.py location \"Viridian City\"\n"
        "  python game_state.py badges 1\n"
        "  python game_state.py party 4\n"
        "  python game_state.py deaths 2\n"
        "  python game_state.py death\n"
        "  python game_state.py objective \"Defeat Misty\\nin Cerulean City\""
    )


def main(argv):
    if len(argv) < 2:
        usage()
    cfg = load_config()
    cmd = argv[1].lower()

    if cmd == "show":
        print(json.dumps(read_state(cfg), indent=2))
        return
    if cmd == "reset":
        state = write_state(default_state(cfg), cfg)
        print(json.dumps(state, indent=2))
        return
    if cmd == "death":
        state = read_state(cfg)
        state = update_state({"deaths": int(state.get("deaths", 0)) + 1}, cfg)
        print(json.dumps(state, indent=2))
        return
    if len(argv) < 3:
        usage()

    value = " ".join(argv[2:]).replace("\\n", "\n")
    if cmd == "location":
        updates = {"location": value}
    elif cmd == "badges":
        updates = {"badges": parse_int("badges", value)}
    elif cmd == "party":
        updates = {"party_size": parse_int("party", value)}
    elif cmd == "deaths":
        updates = {"deaths": parse_int("deaths", value)}
    elif cmd == "objective":
        updates = {"objective": value}
    else:
        usage()

    print(json.dumps(update_state(updates, cfg), indent=2))


if __name__ == "__main__":
    main(sys.argv)
