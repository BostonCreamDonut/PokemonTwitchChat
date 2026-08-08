#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

mkdir -p data logs saves

if [ ! -f secrets.env ] && [ -f secrets.env.example ]; then
  cp secrets.env.example secrets.env
fi

sudo apt update
sudo apt install -y xdotool python3-pyqt5 alsa-utils

chmod 600 secrets.env 2>/dev/null || true

if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  echo "Warning: this project sends emulator keys with xdotool, which needs an X11 desktop session."
  echo "If chat votes do not move the game, switch Raspberry Pi OS from Wayland to X11 in raspi-config."
fi

echo "Setup complete. Edit secrets.env with your Twitch access token, start mGBA, then run ./run.sh"
