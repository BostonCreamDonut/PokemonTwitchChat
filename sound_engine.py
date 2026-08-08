import subprocess
from pathlib import Path

class SoundEngine:
    def __init__(self, base_dir, enabled=True, volume=0.35):
        self.base = Path(base_dir)
        self.enabled = bool(enabled)
        self.volume = max(0.0, min(1.0, float(volume)))

    def play(self, name):
        if not self.enabled:
            return
        path = self.base / name
        if not path.exists():
            return
        # aplay is lightweight and standard on Raspberry Pi OS/ALSA setups.
        try:
            subprocess.Popen(
                ["aplay", "-q", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except OSError:
            return
