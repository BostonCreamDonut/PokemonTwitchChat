# TwitchPokemon-v16

This version implements the latest approved overlay art into the project.

## Key changes
- Uses the latest approved Charizard / title / Pikachu banner.
- True **1920x1080** overlay frame.
- The **game window is genuinely transparent** so OBS can place mGBA under it.
- No permanent Professor Oak / NPC dialogue box.
- No permanent Trainer Status box.
- Current Round, Live Chat, bottom HUD, and footer are aligned to the approved image.

## OBS setup
Use a 1920x1080 base canvas.

Recommended source order:
1. Twitch Plays Pokemon Overlay
2. mGBA Window Capture

The mGBA source should be placed underneath the overlay so it shows through the transparent game opening.

## Raspberry Pi run order
On the Pi, pull the repo and run:

    chmod +x setup.sh run.sh
    ./setup.sh

Create `secrets.env` from the example and add the Twitch OAuth token for the bot account:

    cp secrets.env.example secrets.env
    nano secrets.env

Then start mGBA, load the Pokemon ROM/save, and run:

    ./run.sh

If chat commands appear in the overlay but the game does not move, check these first:
- Raspberry Pi OS should be using an X11 desktop session. `xdotool` usually will not control mGBA under Wayland.
- If you want the bot to focus mGBA before every keypress, set `input.activate_mgba` to `true` in `config.json`.
- Make sure `input.mgba_window_name` matches the emulator window title, usually `mGBA`.

## HUD images
The bottom Location, Badges, Party, Deaths, and Objective panels are drawn into `assets/ui/overlay_frame.png`, then `overlay_app.py` paints the centered live values on top. Runtime sprites live in `assets/ui/hud/`.
`assets/ui/overlay_frame_source.png` is the preserved approved frame; `assets/ui/reference/` stores the badge and skull source references. `tools/build_overlay_assets.py` regenerates the cleaned frame and HUD sprites from those repo-local files.

Badge icons are stored as `badge_0.png` through `badge_7.png`. Unearned badges use the matching dimmed sprites, `badge_0_locked.png` through `badge_7_locked.png`.

To rebuild the polished frame and sprite set:

    python tools/build_overlay_assets.py

## Token
Create or edit `secrets.env` locally:

    TWITCH_ACCESS_TOKEN=your_token_here
