import shutil
import subprocess
import time

class InputController:
    def __init__(self, config):
        self.hold = max(0.02, float(config.get("hold_seconds", 0.2)))
        self.activate_mgba = bool(config.get("activate_mgba", False))
        self.mgba_window_name = str(config.get("mgba_window_name", "mGBA"))
        self.xdotool = shutil.which("xdotool")
        self.warned_missing = False
        self.warned_failed = False

    def _run(self, args):
        if not self.xdotool:
            if not self.warned_missing:
                print("Input disabled: xdotool is not installed. Run ./setup.sh on the Raspberry Pi.")
                self.warned_missing = True
            return False
        try:
            completed = subprocess.run([self.xdotool, *args], check=False,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if completed.returncode == 0:
                return True
            if not self.warned_failed:
                print("Input warning: xdotool command failed. Check that mGBA is open and the Pi is using X11.")
                self.warned_failed = True
            return False
        except OSError as e:
            if not self.warned_failed:
                print(f"Input warning: xdotool failed ({e}). On Raspberry Pi OS, use an X11 desktop session for chat controls.")
                self.warned_failed = True
            return False

    def focus_game(self):
        if not self.activate_mgba:
            return True
        return self._run(["search", "--name", self.mgba_window_name, "windowactivate", "--sync"])

    def press(self, key):
        if not self.focus_game():
            return
        if not self._run(["keydown", key]):
            return
        try:
            time.sleep(self.hold)
        finally:
            self._run(["keyup", key])
