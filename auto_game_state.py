#!/usr/bin/env python3
import json
import re
import socket
import threading
import time
from pathlib import Path

from game_state import load_config, read_state, update_state

BASE = Path(__file__).resolve().parent

BADGE_OBJECTIVES = [
    "Defeat Brock\nin Pewter City",
    "Defeat Misty\nin Cerulean City",
    "Defeat Lt. Surge\nin Vermilion City",
    "Defeat Erika\nin Celadon City",
    "Defeat Koga\nin Fuchsia City",
    "Defeat Sabrina\nin Saffron City",
    "Defeat Blaine\non Cinnabar Island",
    "Defeat Giovanni\nin Viridian City",
    "Head for\nVictory Road",
]


def load_map_names():
    path = BASE / "assets" / "data" / "pokefirered_map_groups.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for group_idx, group_name in enumerate(data.get("group_order", [])):
        for map_idx, raw_name in enumerate(data.get(group_name, [])):
            out[(group_idx, map_idx)] = clean_map_name(raw_name)
    return out


def clean_map_name(raw):
    name = raw.replace("_", " ")
    name = re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", name)
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    name = re.sub(r"\bPokemon\b", "Pokemon", name)
    name = name.replace("Mt ", "Mt. ")
    name = name.replace("SS Anne", "S.S. Anne")
    name = name.replace("P C", "Pokemon Center")
    name = re.sub(r"\s+", " ", name).strip()
    return name


class AutoGameStateServer:
    def __init__(self, cfg=None, stop_event=None):
        self.cfg = cfg or load_config()
        auto = self.cfg.get("auto_game_state", {})
        self.enabled = bool(auto.get("enabled", False))
        self.host = auto.get("host", "127.0.0.1")
        self.port = int(auto.get("port", 8765))
        self.timeout = float(auto.get("socket_timeout_seconds", 0.5))
        self.last_payload = None
        self.map_names = load_map_names()
        self.stop_event = stop_event or threading.Event()

    def start_thread(self):
        if not self.enabled:
            return None
        thread = threading.Thread(target=self.run, name="auto-game-state", daemon=True)
        thread.start()
        return thread

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(1)
            server.settimeout(self.timeout)
            print(f"Auto game state listening on {self.host}:{self.port}")
            while not self.stop_event.is_set():
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with conn:
                    conn.settimeout(self.timeout)
                    self.handle_connection(conn, addr)

    def handle_connection(self, conn, addr):
        print(f"mGBA state bridge connected from {addr[0]}:{addr[1]}")
        buffer = ""
        while not self.stop_event.is_set():
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="ignore")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                self.handle_line(line.strip())

    def handle_line(self, line):
        if not line:
            return
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return
        state = self.derive_state(payload)
        comparable = json.dumps(state, sort_keys=True)
        if comparable == self.last_payload:
            return
        self.last_payload = comparable
        update_state(state, self.cfg)

    def derive_state(self, payload):
        current = read_state(self.cfg)
        map_group = int(payload.get("map_group", -1))
        map_num = int(payload.get("map_num", -1))
        badges = max(0, min(8, int(payload.get("badges", current.get("badges", 0)))))
        party_size = max(0, min(6, int(payload.get("party_size", current.get("party_size", 1)))))
        location = self.map_names.get((map_group, map_num), current.get("location", "Unknown"))
        objective = current.get("objective", "Begin the adventure")
        if int(current.get("badges", badges)) != badges or objective in BADGE_OBJECTIVES:
            objective = BADGE_OBJECTIVES[badges]
        return {
            "location": location,
            "badges": badges,
            "party_size": party_size,
            "deaths": int(current.get("deaths", 0)),
            "objective": objective,
        }


def main():
    cfg = load_config()
    server = AutoGameStateServer(cfg)
    if not server.enabled:
        print("auto_game_state.enabled is false in config.json")
        return
    try:
        server.run()
    except KeyboardInterrupt:
        server.stop_event.set()


if __name__ == "__main__":
    main()
