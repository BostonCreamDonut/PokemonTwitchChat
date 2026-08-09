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
Current game opening: `x=321`, `y=166`, `width=1207`, `height=770`.

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

## Automatic game status
The overlay does not render the game. OBS should still show mGBA as its own cropped source underneath the overlay. The HUD can update automatically by reading mGBA memory through a Lua script.

1. Start the stream app with `./run.sh`.
2. In mGBA, open `Tools -> Scripting`.
3. Load `scripts/mgba_firered_state_bridge.lua`.

When the bridge is loaded, Location, Badges, Party count, and the badge-based Objective update automatically. This is configured for Pokemon FireRed US v1.0. If the values look wrong, disable `"auto_game_state.enabled"` in `config.json` and use the manual commands below.

Deaths are still manual because FireRed does not have a built-in death counter.

## Manual game status
The overlay reads live game status from `game_state.json`. Manual commands are still useful for deaths or quick corrections:

    python game_state.py location "Viridian City"
    python game_state.py badges 1
    python game_state.py party 4
    python game_state.py death
    python game_state.py deaths 2
    python game_state.py objective "Defeat Misty\nin Cerulean City"

The broadcaster or a mod can also update it from Twitch chat:

    !location Viridian City
    !badges 1
    !party 4
    !death
    !deaths 2
    !objective Defeat Misty in Cerulean City

## Token
Create or edit `secrets.env` locally:

    TWITCH_ACCESS_TOKEN=your_token_here
