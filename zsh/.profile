# Login environment. greetd sources ~/.profile before exec'ing sway
# (its source_profile default), so everything started from the desktop
# inherits these.

# rmpc talks to MPD over its Unix socket (local-file operations like
# `addyt` are refused over TCP). The socket lives in this user's runtime
# dir, whose path depends on the uid, and rmpc's config.ron can't expand
# variables -- so it's given here instead of hardcoded there.
export MPD_HOST="${MPD_HOST:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/mpd/socket}"
