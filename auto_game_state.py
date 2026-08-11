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
    if raw.startswith("BattleColosseum"):
        return "Battle Col."
    if raw == "TradeCenter":
        return "Trade Center"
    if raw == "RecordCorner":
        return "Record Corner"
    if raw == "UnionRoom":
        return "Union Room"

    name = raw.replace("_", " ")
    name = re.sub(r"(?<=[a-z])(?=[A-Z0-9])", " ", name)
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    name = re.sub(r"\bPokemon\b", "Pokemon", name)
    name = name.replace("Players House", "House")
    name = name.replace("Rivals House", "Rival House")
    name = name.replace("Professor Oaks Lab", "Oak's Lab")
    name = name.replace("Mt ", "Mt. ")
    name = name.replace("SS Anne", "S.S. Anne")
    name = name.replace("Pokemon Center 1 F", "Pokemon Center")
    name = name.replace("Pokemon Center 2 F", "Pokemon Center")
    name = name.replace("P C", "Pokemon Center")
    name = name.replace(" 1 F", "")
    name = name.replace(" 2 F", "")
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
        print(
            "Game state:",
            f"{state['location']} | badges={state['badges']} party={state['party_size']}",
            f"species={state.get('party_species', [])}",
            f"raw={payload}",
        )

    def derive_state(self, payload):
        current = read_state(self.cfg)
        map_group, map_num = self.best_map_candidate(payload, current)
        badges = max(0, min(8, int(payload.get("badges", current.get("badges", 0)))))
        party_size = self.best_party_size(payload, current)
        party_fainted = self.party_fainted(payload, party_size, current)
        party_species = self.party_species(payload, party_size, current)
        location = self.map_names.get((map_group, map_num), current.get("location", "Unknown"))
        objective = current.get("objective", "Begin the adventure")
        if int(current.get("badges", badges)) != badges or objective in BADGE_OBJECTIVES:
            objective = BADGE_OBJECTIVES[badges]
        return {
            "location": location,
            "badges": badges,
            "party_size": party_size,
            "party_fainted": party_fainted,
            "party_species": party_species,
            "deaths": int(current.get("deaths", 0)),
            "objective": objective,
        }

    def best_map_candidate(self, payload, current):
        candidates = []
        for group_key, num_key in (
            ("ptr_map_group", "ptr_map_num"),
            ("map_group", "map_num"),
            ("fixed_map_group", "fixed_map_num"),
        ):
            try:
                group = int(payload.get(group_key, -1))
                num = int(payload.get(num_key, -1))
            except (TypeError, ValueError):
                continue
            if (group, num) in self.map_names:
                candidates.append((group, num))

        non_link = [candidate for candidate in candidates if candidate[0] != 0]
        if non_link:
            return non_link[0]
        if candidates:
            current_location = str(current.get("location", ""))
            if current_location and current_location not in ("Unknown", "Battle Col."):
                return (-1, -1)
            return candidates[0]
        return (-1, -1)

    def best_party_size(self, payload, current):
        current_size = max(0, min(6, int(current.get("party_size", 1))))
        candidates = []
        for key in ("global_party_size", "party_size", "ptr_party_size", "fixed_party_size"):
            try:
                value = int(payload.get(key, -1))
            except (TypeError, ValueError):
                continue
            if 0 <= value <= 6:
                candidates.append(value)

        positive = [value for value in candidates if value > 0]
        if positive:
            return positive[0]
        if current_size > 0:
            return current_size
        if candidates:
            return candidates[0]
        return current_size

    def party_fainted(self, payload, party_size, current):
        hp_values = payload.get("party_hp")
        if not isinstance(hp_values, list):
            return list(current.get("party_fainted", []))[:party_size]
        fainted = []
        for value in hp_values[:party_size]:
            try:
                fainted.append(int(value) <= 0)
            except (TypeError, ValueError):
                fainted.append(False)
        return fainted

    def party_species(self, payload, party_size, current):
        species_values = payload.get("party_species")
        if not isinstance(species_values, list):
            return list(current.get("party_species", []))[:party_size]
        species = []
        for value in species_values[:party_size]:
            try:
                species.append(max(0, int(value)))
            except (TypeError, ValueError):
                species.append(0)
        return species


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
