import subprocess, time

class InputController:
    def __init__(self, config):
        self.hold = max(0.02, float(config.get("hold_seconds", 0.2)))

    def press(self, key):
        subprocess.run(["xdotool","keydown",key], check=False)
        try:
            time.sleep(self.hold)
        finally:
            subprocess.run(["xdotool","keyup",key], check=False)
