# LYRA Reel tools

- `make_reel.py spec.json out.mp4 [--music bed.mp3 --music-license bed.license.json]`: brand scenes to a 1080x1920 MP4 (30 fps, 48 kHz, about -14 LUFS) with Earshot sound effects on the cuts and a license log next to the video.
- `openverse.py "query" folder`: a CC0 / public-domain music bed from Openverse (CC BY only with `--allow-by`, credited in the caption). Never NC, ND or SA.
- Needs: ffmpeg, Playwright with Chromium, numpy and scipy, and Earshot (MIT): `git clone --depth 1 https://github.com/Leonxlnx/earshot /tmp/earshot`. If `soundfile` is not installed, `shims/` is used automatically.
