import json, time
from pathlib import Path

class EventEngine:
    def __init__(self, base, config, sound_engine):
        self.base = Path(base)
        self.cfg = config
        self.sound = sound_engine
        ov = config["overlay"]
        self.event_path = self.base / ov["event_file"]
        self.dialogue_path = self.base / ov.get("dialogue_file","dialogue_state.json")
        self.boot_path = self.base / ov.get("boot_file","boot_state.json")

    def _atomic(self, path, payload):
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)

    def alert(self, kind, title, subtitle="", extra=None, duration=4.0, sound=None):
        payload={
            "id":time.time_ns(),"kind":kind,"title":title,"subtitle":subtitle,
            "extra":extra or {},"duration":float(duration),"created_at":time.time()
        }
        self._atomic(self.event_path,payload)
        if sound:
            self.sound.play(sound)

    def dialogue(self, speaker, text, duration=None, portrait=""):
        payload={
            "id":time.time_ns(),"speaker":speaker,"text":text,"portrait":portrait,
            "duration":float(duration or self.cfg["stream_system"]["npc_dialogue_seconds"]),
            "created_at":time.time()
        }
        self._atomic(self.dialogue_path,payload)
        self.sound.play("dialogue.wav")

    def boot(self, step, detail="", done=False):
        self._atomic(self.boot_path,{
            "id":time.time_ns(),"step":step,"detail":detail,
            "done":bool(done),"created_at":time.time()
        })
