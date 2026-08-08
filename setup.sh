#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
sudo apt update
sudo apt install -y xdotool python3-pyqt5 alsa-utils
echo "Setup complete. Put your Twitch access token in secrets.env, then run ./run.sh"

chmod 600 secrets.env 2>/dev/null || true
echo "Edit secrets.env and paste your Twitch access token, then run ./run.sh"
