#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

mkdir -p data logs saves

if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  echo "Warning: Wayland session detected. xdotool usually requires X11 for emulator control."
fi

exec python3 main.py
