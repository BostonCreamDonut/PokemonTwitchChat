# TwitchPokemon-v16

This version implements the latest approved overlay art into the project.

## Key changes
- Uses the latest approved Charizard / title / Pikachu banner.
- True **1920×1080** overlay frame.
- The **game window is genuinely transparent** so OBS can place mGBA under it.
- No permanent Professor Oak / NPC dialogue box.
- No permanent Trainer Status box.
- Current Round, Live Chat, bottom HUD, and footer are aligned to the approved image.

## OBS setup
Use a 1920×1080 base canvas.

Recommended source order:
1. Twitch Plays Pokemon Overlay
2. mGBA Window Capture

The mGBA source should be placed underneath the overlay so it shows through the transparent game opening.

## Token
Edit `secrets.env` directly:

    TWITCH_ACCESS_TOKEN=your_token_here
