# mpd

The actual player/backend for the music setup -- nāda (github.com/Theyashsawarkar/nada, replacing rmpc)
is only ever the UI on top of this. Replaced termusic entirely (see
`docs/ARCHITECTURE.md` for the full story of why) rather than patching
around its one real problem (a broken search feature) forever.

Runs as `mpd.service`, a real `systemd --user` unit shipped by the
`mpd` package itself (confirmed directly:
`/usr/lib/systemd/user/mpd.service` exists in the package -- no unit
file needed in this repo, just `systemctl --user enable --now
mpd.service` once). `mpd.conf` is the only file this package tracks.

## Why this over termusic's own approach

termusic bundled its own player *and* its own (broken) search into one
binary. Splitting those apart -- a dedicated player daemon (MPD, one of
the most mature pieces of music-playing infrastructure that exists) +
a separate script for search (`music-search.py`, `scripts/` package)
-- means the player itself was never the fragile part to begin with.
MPD doesn't scrape or call out to any third-party API at all; it just
plays whatever's already a real file in `music_directory`.

## Real behavior confirmed, not assumed

- `auto_update "yes"` -- MPD has a genuine filesystem watcher, unlike
  termusic (confirmed by reading termusic's own source: no watcher
  existed there at all, library scanning only ever happened at
  startup). Verified directly here too, not just trusted from the
  option's name: dropped a file into `~/Music` with zero clients
  connected and watched MPD's own log pick it up and index it within
  seconds, completely unprompted.
- `playlist_directory` explicitly set (`~/.local/share/mpd/playlists`,
  real user content, not runtime state) -- without it, MPD logs
  "Stored playlists are disabled" on every attempt rmpc's own playlist
  features make; confirmed by watching that exact line appear in a live
  test, then confirming it stopped once this was set.
- `audio_output { type "pulse" }` -- confirmed this machine's actual
  audio stack first (`pactl info`: "Server Name: PulseAudio (on
  PipeWire ...)") rather than guessing a backend; PipeWire's own
  PulseAudio-compatible socket is the same one every other pactl-based
  script in this repo already talks to.

## What's tracked here, and what isn't

Only `mpd.conf`. `db_file`/`state_file`/`sticker_file` all point at
`~/.local/state/mpd/` -- real runtime state (a scanned index, playback
position, song ratings), not configuration, same line this repo draws
everywhere else (`~/.local/state/notification-mode/`, and previously
termusic's own database files before it was removed).
